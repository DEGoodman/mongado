"""LLM client abstraction: local Ollama or hosted APIs (Groq/Gemini).

Provides a single client surface for all AI generation and embedding calls.
Which backend handles *generation* is decided per-call by the "llm_use_api"
runtime feature flag (admin UI). Which backend handles *embeddings* is a
startup-level setting (EMBEDDING_PROVIDER), because query embeddings must
match the model tag stored with precomputed embeddings in Neo4j and
embedding_sync only reconciles model changes at startup.

Architecture:
- ApiLLMClient: OpenAI-compatible chat completions with a provider fallback
  chain (Groq primary, Gemini fallback). Configured via GROQ_API_KEY /
  GEMINI_API_KEY; a provider without a key is simply skipped. Embeddings go
  through Gemini's /embeddings endpoint (Groq hosts no embedding models).
- RoutingLLMClient: delegates each call to Ollama or the API chain based on
  the feature flag (generation) or EMBEDDING_PROVIDER (embeddings). This is
  what routers receive via dependencies.get_llm().
"""

import json
import logging
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from config import get_settings
from core import ai as ai_core
from ollama_client import OllamaClient, get_ollama_client
from utils import calculate_content_hash

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
        # Embeddings are served by Gemini only (Groq hosts no embedding models)
        self.embed_provider = next((p for p in self.providers if p.name == "gemini"), None)
        self.embed_model = settings.gemini_embed_model
        # Embedding cache: {content_hash: embedding_vector}, mirrors OllamaClient
        self.embedding_cache: dict[str, list[float]] = {}
        if self.providers:
            logger.info(
                "API LLM client configured with providers: %s",
                ", ".join(f"{p.name} ({p.model})" for p in self.providers),
            )

    def is_available(self) -> bool:
        """Check if at least one API provider is configured."""
        return bool(self.providers)

    def embeddings_available(self) -> bool:
        """Check if embedding generation is possible (requires Gemini)."""
        return self.embed_provider is not None

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
        timeout: float | None = None,
    ) -> str | None:
        """Generate a completion, trying each provider in order.

        Args:
            prompt: The full prompt text
            role: "chat" or "structured" (accepted for interface parity with
                OllamaClient; hosted models handle both with one model)
            num_ctx: Ignored for API providers (hosted context windows are large)
            max_tokens: Response length cap (defaults to settings)
            timeout: Per-provider timeout override. Interactive callers should
                pass a short value: the default is sized for long generations,
                and a hung primary provider otherwise delays the fallback by
                the full timeout before the secondary is even tried.

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
                    timeout=timeout or self.timeout,
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
        if context == "embedding":
            return self.embeddings_available(), self.embed_model
        model = self.providers[0].model if self.providers else ""
        return self.is_available(), model

    # --- embeddings ----------------------------------------------------------

    def generate_embedding(self, text: str, use_cache: bool = True) -> list[float] | None:
        """Generate an embedding via Gemini's OpenAI-compatible endpoint.

        Fails fast (no retries): interactive callers shouldn't stall on 429s.
        Batch callers that need eventual completion retry with backoff at
        their own level (see embedding_sync).
        """
        import httpx

        if self.embed_provider is None:
            logger.debug("No embedding-capable API provider configured")
            return None

        if use_cache:
            content_hash = calculate_content_hash(text)
            if content_hash in self.embedding_cache:
                logger.debug("Using cached embedding for content")
                return self.embedding_cache[content_hash]

        try:
            response = httpx.post(
                f"{self.embed_provider.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.embed_provider.api_key}"},
                json={"model": self.embed_model, "input": text},
                timeout=self.timeout,
            )
            response.raise_for_status()
            embedding: list[float] = response.json()["data"][0]["embedding"]
            if use_cache:
                self.embedding_cache[calculate_content_hash(text)] = embedding
            return embedding
        except Exception as e:
            logger.error("Failed to generate embedding via %s: %s", self.embed_provider.name, e)
            return None

    def semantic_search(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Semantic search, embedding documents on the fly (cached per content)."""
        query_embedding = self.generate_embedding(query, use_cache=False)
        if not query_embedding:
            return []

        documents_with_embeddings = []
        for doc in documents:
            doc_embedding = self.generate_embedding(doc.get("content", ""), use_cache=True)
            if doc_embedding:
                documents_with_embeddings.append({**doc, "embedding": doc_embedding})

        ranked = ai_core.rank_documents_by_similarity(
            query_embedding, documents_with_embeddings, top_k
        )
        # Strip the transient embeddings added above (parity with OllamaClient)
        return [{k: v for k, v in doc.items() if k != "embedding"} for doc in ranked]

    def semantic_search_with_precomputed_embeddings(
        self, query: str, documents_with_embeddings: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Semantic search against precomputed embeddings (only embeds the query)."""
        query_embedding = self.generate_embedding(query, use_cache=False)
        if not query_embedding:
            logger.warning("Failed to generate query embedding")
            return []
        return ai_core.rank_documents_by_similarity(
            query_embedding, documents_with_embeddings, top_k
        )

    def clear_cache(self) -> int:
        """Clear the embedding cache, returning the number of entries removed."""
        count = len(self.embedding_cache)
        self.embedding_cache.clear()
        return count


class RoutingLLMClient:
    """Routes LLM calls to Ollama or hosted APIs based on configuration.

    - Generation (generate, ask_question, summarize, streaming): API chain
      when the "llm_use_api" flag is on and providers are configured,
      otherwise Ollama.
    - Embeddings and semantic search: the EMBEDDING_PROVIDER setting ("api"
      routes to Gemini, anything else stays on Ollama). Startup-level, not a
      runtime flag: query embeddings must match the model tag stored with
      precomputed embeddings in Neo4j, and embedding_sync only reconciles
      model changes at startup.
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

    def _embedding_backend(self) -> Any:
        if get_settings().embedding_provider == "api" and self.api.embeddings_available():
            return self.api
        return self.ollama

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
        """Whether embedding generation is possible on the embedding backend.

        Distinct from is_available(): generation can be healthy while the
        embedding backend (and therefore semantic search) is down.
        """
        available: bool = self._embedding_backend().embeddings_available()
        return available

    def has_gpu(self) -> bool:
        """Hosted APIs are treated as accelerated; Ollama reports its own state."""
        if self._use_api():
            return True
        return self.ollama.has_gpu()

    def warmup(self, context: str = "chat") -> tuple[bool, str]:
        """Warm up the backend that will serve the given context."""
        if context == "embedding":
            backend = self._embedding_backend()
        else:
            backend = self._generation_backend()
        result: tuple[bool, str] = backend.warmup(context=context)
        return result

    # --- embeddings / search (routed by EMBEDDING_PROVIDER) -----------------

    @property
    def model(self) -> str:
        """Embedding model tag used when storing embeddings.

        Changing this tag makes embedding_sync regenerate the corpus at the
        next startup (model-change detection).
        """
        backend = self._embedding_backend()
        if backend is self.api:
            return self.api.embed_model
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
        result: list[float] | None = self._embedding_backend().generate_embedding(
            text, use_cache=use_cache
        )
        return result

    def semantic_search(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = self._embedding_backend().semantic_search(
            query, documents, top_k
        )
        return results

    def semantic_search_with_precomputed_embeddings(
        self, query: str, documents_with_embeddings: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = (
            self._embedding_backend().semantic_search_with_precomputed_embeddings(
                query, documents_with_embeddings, top_k
            )
        )
        return results

    def clear_cache(self) -> int:
        return self.ollama.clear_cache() + self.api.clear_cache()


_llm_client: RoutingLLMClient | None = None


def get_llm_client() -> RoutingLLMClient:
    """Get the global routing LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = RoutingLLMClient(get_ollama_client(), ApiLLMClient())
    return _llm_client
