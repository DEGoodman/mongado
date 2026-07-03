"""LLM client abstraction: local Ollama or hosted APIs (Groq/Gemini).

Provides a single client surface for all AI generation and embedding calls.
Which backend handles *generation* is decided per-call by the "llm_use_api"
runtime feature flag (admin UI). Embeddings and semantic search always use
Ollama so stored embeddings in Neo4j stay consistent with query embeddings.

Architecture:
- ApiLLMClient: OpenAI-compatible chat completions with a provider fallback
  chain (Groq primary, Gemini fallback). Configured via GROQ_API_KEY /
  GEMINI_API_KEY; a provider without a key is simply skipped.
- RoutingLLMClient: delegates each call to Ollama or the API chain based on
  the feature flag. This is what routers receive via dependencies.get_llm().
"""

import json
import logging
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from config import get_settings
from core import ai as ai_core
from ollama_client import OllamaClient, get_ollama_client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ApiProvider:
    """A hosted OpenAI-compatible inference provider."""

    name: str
    base_url: str
    api_key: str
    model: str


def _build_providers() -> list[ApiProvider]:
    """Build the provider chain from settings (order = fallback priority)."""
    settings = get_settings()
    providers = []
    if settings.groq_api_key:
        providers.append(
            ApiProvider(
                name="groq",
                base_url=settings.groq_base_url,
                api_key=settings.groq_api_key,
                model=settings.groq_model,
            )
        )
    if settings.gemini_api_key:
        providers.append(
            ApiProvider(
                name="gemini",
                base_url=settings.gemini_base_url,
                api_key=settings.gemini_api_key,
                model=settings.gemini_model,
            )
        )
    return providers


class ApiLLMClient:
    """LLM generation via hosted OpenAI-compatible APIs with fallback chain."""

    def __init__(self, providers: list[ApiProvider] | None = None) -> None:
        settings = get_settings()
        self.providers = _build_providers() if providers is None else providers
        self.timeout = settings.llm_api_timeout
        self.default_max_tokens = settings.llm_api_max_tokens
        if self.providers:
            logger.info(
                "API LLM client configured with providers: %s",
                ", ".join(f"{p.name} ({p.model})" for p in self.providers),
            )

    def is_available(self) -> bool:
        """Check if at least one API provider is configured."""
        return bool(self.providers)

    def _request_body(
        self, provider: ApiProvider, prompt: str, max_tokens: int | None, stream: bool
    ) -> dict[str, Any]:
        return {
            "model": provider.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or self.default_max_tokens,
            "stream": stream,
        }

    def generate(
        self,
        prompt: str,
        *,
        role: str = "chat",
        num_ctx: int | None = None,
        max_tokens: int | None = None,
    ) -> str | None:
        """Generate a completion, trying each provider in order.

        Args:
            prompt: The full prompt text
            role: "chat" or "structured" (accepted for interface parity with
                OllamaClient; hosted models handle both with one model)
            num_ctx: Ignored for API providers (hosted context windows are large)
            max_tokens: Response length cap (defaults to settings)

        Returns:
            Generated text, or None if all providers failed
        """
        import httpx

        for provider in self.providers:
            try:
                response = httpx.post(
                    f"{provider.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    json=self._request_body(provider, prompt, max_tokens, stream=False),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices") or []
                message = choices[0].get("message", {}) if choices else {}
                content: str | None = message.get("content")
                if content:
                    logger.debug("Generated %d chars via %s", len(content), provider.name)
                    return content
                # e.g. Gemini spends the whole max_tokens budget on internal
                # reasoning and returns finish_reason=length with no content
                logger.warning(
                    "Empty completion from %s (finish_reason=%s), trying next provider",
                    provider.name,
                    choices[0].get("finish_reason") if choices else "n/a",
                )
            except Exception as e:
                logger.warning("Provider %s failed (%s), trying next provider", provider.name, e)
        logger.error("All API providers failed for generation")
        return None

    def generate_stream(
        self,
        prompt: str,
        *,
        role: str = "chat",
        num_ctx: int | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str]:
        """Stream a completion as text chunks, with provider fallback.

        Falls back to the next provider only if the current one fails before
        yielding any content (a mid-stream failure ends the stream).
        """
        import httpx

        for provider in self.providers:
            yielded = False
            try:
                with httpx.stream(
                    "POST",
                    f"{provider.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    json=self._request_body(provider, prompt, max_tokens, stream=True),
                    timeout=self.timeout,
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line[len("data: ") :].strip()
                        if payload == "[DONE]":
                            return
                        try:
                            chunk = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices") or []
                        delta = choices[0].get("delta", {}) if choices else {}
                        content = delta.get("content")
                        if content:
                            yielded = True
                            yield content
                return
            except Exception as e:
                if yielded:
                    logger.error("Provider %s failed mid-stream: %s", provider.name, e)
                    return
                logger.warning("Provider %s failed (%s), trying next provider", provider.name, e)
        logger.error("All API providers failed for streaming generation")

    def ask_question(
        self,
        question: str,
        context_documents: list[dict[str, Any]],
        allow_general_knowledge: bool = True,
    ) -> str | None:
        """Answer a question with document context (RAG)."""
        prompt = ai_core.build_qa_prompt(question, context_documents, allow_general_knowledge)
        return self.generate(prompt, role="chat")

    def summarize_article(self, content: str) -> str | None:
        """Generate a 2-3 sentence summary of article content."""
        prompt = ai_core.build_summary_prompt(content, content_type="article")
        return self.generate(prompt, role="chat", max_tokens=256)

    def warmup(self, context: str = "chat") -> tuple[bool, str]:
        """No-op: hosted APIs need no warmup."""
        model = self.providers[0].model if self.providers else ""
        return self.is_available(), model


class RoutingLLMClient:
    """Routes LLM calls to Ollama or hosted APIs based on the runtime flag.

    - Generation (generate, ask_question, summarize, streaming): API chain
      when the "llm_use_api" flag is on and providers are configured,
      otherwise Ollama.
    - Embeddings and semantic search: always Ollama, so query embeddings
      match the precomputed embeddings stored in Neo4j.
    """

    def __init__(self, ollama: OllamaClient, api: ApiLLMClient) -> None:
        self.ollama = ollama
        self.api = api

    # --- routing -----------------------------------------------------------

    def _use_api(self) -> bool:
        if not self.api.is_available():
            return False
        # Imported here to avoid a circular import at module load time
        from feature_flags import get_feature_flags

        return get_feature_flags().is_enabled("llm_use_api")

    def _generation_backend(self) -> Any:
        return self.api if self._use_api() else self.ollama

    @property
    def active_provider(self) -> str:
        """Name of the backend currently serving generation requests."""
        if self._use_api():
            return " -> ".join(p.name for p in self.api.providers)
        return "ollama"

    # --- generation (routed) ----------------------------------------------

    def generate(self, prompt: str, **kwargs: Any) -> str | None:
        result: str | None = self._generation_backend().generate(prompt, **kwargs)
        return result

    def generate_stream(self, prompt: str, **kwargs: Any) -> Generator[str]:
        yield from self._generation_backend().generate_stream(prompt, **kwargs)

    def ask_question(
        self,
        question: str,
        context_documents: list[dict[str, Any]],
        allow_general_knowledge: bool = True,
    ) -> str | None:
        result: str | None = self._generation_backend().ask_question(
            question, context_documents, allow_general_knowledge
        )
        return result

    def summarize_article(self, content: str) -> str | None:
        result: str | None = self._generation_backend().summarize_article(content)
        return result

    def is_available(self) -> bool:
        """Whether generation is currently possible."""
        available: bool = self._generation_backend().is_available()
        return available

    def embeddings_available(self) -> bool:
        """Whether embedding generation is possible (always requires Ollama).

        Distinct from is_available(): in API mode generation can be healthy
        while Ollama (and therefore semantic search) is down.
        """
        return self.ollama.is_available()

    def has_gpu(self) -> bool:
        """Hosted APIs are treated as accelerated; Ollama reports its own state."""
        if self._use_api():
            return True
        return self.ollama.has_gpu()

    def warmup(self, context: str = "chat") -> tuple[bool, str]:
        """Warm up the backend that will serve the given context."""
        if context == "embedding":
            return self.ollama.warmup(context=context)
        result: tuple[bool, str] = self._generation_backend().warmup(context=context)
        return result

    # --- embeddings / search (always Ollama) --------------------------------

    @property
    def model(self) -> str:
        """Embedding model tag used when storing embeddings (Ollama's)."""
        return self.ollama.model

    @property
    def chat_model(self) -> str:
        if self._use_api():
            return self.api.providers[0].model
        return self.ollama.chat_model

    @property
    def structured_model(self) -> str:
        if self._use_api():
            return self.api.providers[0].model
        return self.ollama.structured_model

    def generate_embedding(self, text: str, use_cache: bool = True) -> list[float] | None:
        return self.ollama.generate_embedding(text, use_cache=use_cache)

    def semantic_search(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        return self.ollama.semantic_search(query, documents, top_k)

    def semantic_search_with_precomputed_embeddings(
        self, query: str, documents_with_embeddings: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        return self.ollama.semantic_search_with_precomputed_embeddings(
            query, documents_with_embeddings, top_k
        )

    def clear_cache(self) -> int:
        return self.ollama.clear_cache()


_llm_client: RoutingLLMClient | None = None


def get_llm_client() -> RoutingLLMClient:
    """Get the global routing LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = RoutingLLMClient(get_ollama_client(), ApiLLMClient())
    return _llm_client
