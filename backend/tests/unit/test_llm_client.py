"""Unit tests for the LLM client abstraction (API providers + routing)."""

from typing import Any
from unittest.mock import MagicMock

import pytest

import llm_client as llm_module
from llm_client import ApiLLMClient, ApiProvider, RoutingLLMClient

GROQ = ApiProvider(
    name="groq",
    base_url="https://api.groq.com/openai/v1",
    api_key="test-groq-key",
    model="llama-3.1-8b-instant",
)
GEMINI = ApiProvider(
    name="gemini",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai",
    api_key="test-gemini-key",
    model="gemini-flash-latest",
)


def _completion_response(content: str) -> MagicMock:
    """Build a mock httpx response with an OpenAI-compatible completion."""
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"choices": [{"message": {"content": content}}]}
    return response


def _embedding_response(embedding: list[float]) -> MagicMock:
    """Build a mock httpx response with an OpenAI-compatible embedding."""
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"data": [{"embedding": embedding}]}
    return response


# ============================================================================
# ApiLLMClient
# ============================================================================


class TestApiLLMClient:
    def test_not_available_without_providers(self) -> None:
        client = ApiLLMClient(providers=[])
        assert client.is_available() is False

    def test_available_with_providers(self) -> None:
        client = ApiLLMClient(providers=[GROQ])
        assert client.is_available() is True

    def test_generate_returns_none_without_providers(self) -> None:
        client = ApiLLMClient(providers=[])
        assert client.generate("hello") is None

    def test_generate_uses_first_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict[str, Any]] = []

        def mock_post(url: str, **kwargs: Any) -> MagicMock:
            calls.append({"url": url, **kwargs})
            return _completion_response("hello from groq")

        monkeypatch.setattr("httpx.post", mock_post)
        client = ApiLLMClient(providers=[GROQ, GEMINI])

        assert client.generate("test prompt") == "hello from groq"
        assert len(calls) == 1
        assert calls[0]["url"].startswith(GROQ.base_url)
        assert calls[0]["headers"]["Authorization"] == "Bearer test-groq-key"
        assert calls[0]["json"]["model"] == GROQ.model
        assert calls[0]["json"]["messages"] == [{"role": "user", "content": "test prompt"}]

    def test_generate_falls_back_to_next_provider(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def mock_post(url: str, **kwargs: Any) -> MagicMock:
            if GROQ.base_url in url:
                raise ConnectionError("groq down")
            return _completion_response("hello from gemini")

        monkeypatch.setattr("httpx.post", mock_post)
        client = ApiLLMClient(providers=[GROQ, GEMINI])

        assert client.generate("test prompt") == "hello from gemini"

    def test_generate_returns_none_when_all_providers_fail(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def mock_post(url: str, **kwargs: Any) -> MagicMock:
            raise ConnectionError("all down")

        monkeypatch.setattr("httpx.post", mock_post)
        client = ApiLLMClient(providers=[GROQ, GEMINI])

        assert client.generate("test prompt") is None

    def test_generate_stream_parses_sse(self, monkeypatch: pytest.MonkeyPatch) -> None:
        sse_lines = [
            'data: {"choices": [{"delta": {"content": "Hel"}}]}',
            "",
            'data: {"choices": [{"delta": {"content": "lo"}}]}',
            "data: [DONE]",
        ]

        stream_response = MagicMock()
        stream_response.raise_for_status.return_value = None
        stream_response.iter_lines.return_value = iter(sse_lines)
        stream_cm = MagicMock()
        stream_cm.__enter__.return_value = stream_response
        stream_cm.__exit__.return_value = False

        monkeypatch.setattr("httpx.stream", lambda *a, **kw: stream_cm)
        client = ApiLLMClient(providers=[GROQ])

        assert list(client.generate_stream("test prompt")) == ["Hel", "lo"]

    def test_warmup_is_noop(self) -> None:
        client = ApiLLMClient(providers=[GROQ])
        success, model = client.warmup()
        assert success is True
        assert model == GROQ.model

    def test_embeddings_require_gemini(self) -> None:
        assert ApiLLMClient(providers=[GROQ]).embeddings_available() is False
        assert ApiLLMClient(providers=[GROQ, GEMINI]).embeddings_available() is True

    def test_generate_embedding_none_without_gemini(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[str] = []
        monkeypatch.setattr("httpx.post", lambda url, **kw: calls.append(url))
        client = ApiLLMClient(providers=[GROQ])
        assert client.generate_embedding("text") is None
        assert calls == []

    def test_generate_embedding_posts_to_gemini(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict[str, Any]] = []

        def mock_post(url: str, **kwargs: Any) -> MagicMock:
            calls.append({"url": url, **kwargs})
            return _embedding_response([0.1, 0.2, 0.3])

        monkeypatch.setattr("httpx.post", mock_post)
        client = ApiLLMClient(providers=[GROQ, GEMINI])

        assert client.generate_embedding("some text") == [0.1, 0.2, 0.3]
        assert len(calls) == 1
        assert calls[0]["url"] == f"{GEMINI.base_url}/embeddings"
        assert calls[0]["headers"]["Authorization"] == "Bearer test-gemini-key"
        assert calls[0]["json"] == {"model": client.embed_model, "input": "some text"}

    def test_generate_embedding_caches_by_content(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[str] = []

        def mock_post(url: str, **kwargs: Any) -> MagicMock:
            calls.append(url)
            return _embedding_response([0.5])

        monkeypatch.setattr("httpx.post", mock_post)
        client = ApiLLMClient(providers=[GEMINI])

        assert client.generate_embedding("same text") == [0.5]
        assert client.generate_embedding("same text") == [0.5]
        assert len(calls) == 1
        assert client.clear_cache() == 1
        client.generate_embedding("same text")
        assert len(calls) == 2

    def test_generate_embedding_returns_none_on_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def mock_post(url: str, **kwargs: Any) -> MagicMock:
            raise ConnectionError("gemini down")

        monkeypatch.setattr("httpx.post", mock_post)
        client = ApiLLMClient(providers=[GEMINI])
        assert client.generate_embedding("text") is None

    def test_precomputed_search_ranks_by_similarity(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("httpx.post", lambda url, **kw: _embedding_response([1.0, 0.0]))
        client = ApiLLMClient(providers=[GEMINI])
        docs = [
            {"id": "orthogonal", "embedding": [0.0, 1.0]},
            {"id": "aligned", "embedding": [1.0, 0.0]},
        ]

        results = client.semantic_search_with_precomputed_embeddings("query", docs, top_k=2)
        assert [doc["id"] for doc in results] == ["aligned", "orthogonal"]
        assert results[0]["score"] == pytest.approx(1.0)

    def test_semantic_search_embeds_documents(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("httpx.post", lambda url, **kw: _embedding_response([1.0, 0.0]))
        client = ApiLLMClient(providers=[GEMINI])
        docs = [{"id": "a", "content": "doc a"}, {"id": "b", "content": "doc b"}]

        results = client.semantic_search("query", docs, top_k=1)
        assert len(results) == 1
        # Transient embeddings are stripped from results
        assert "embedding" not in results[0]

    def test_embedding_warmup_reports_embed_model(self) -> None:
        client = ApiLLMClient(providers=[GROQ, GEMINI])
        success, model = client.warmup(context="embedding")
        assert success is True
        assert model == client.embed_model

        no_gemini = ApiLLMClient(providers=[GROQ])
        success, _ = no_gemini.warmup(context="embedding")
        assert success is False


# ============================================================================
# RoutingLLMClient
# ============================================================================


class MockBackend:
    """Minimal generation backend recording which methods were called."""

    def __init__(self, name: str, available: bool = True) -> None:
        self.name = name
        self._available = available
        self.calls: list[str] = []
        # Ollama-surface attributes used by routing
        self.model = f"{name}-model"
        self.chat_model = f"{name}-chat"
        self.structured_model = f"{name}-structured"
        self.embed_model = f"{name}-embed"
        self.providers = [GROQ]

    def is_available(self) -> bool:
        return self._available

    def embeddings_available(self) -> bool:
        return self._available

    def has_gpu(self) -> bool:
        self.calls.append("has_gpu")
        return False

    def generate(self, prompt: str, **kwargs: Any) -> str:
        self.calls.append("generate")
        return f"answer from {self.name}"

    def generate_stream(self, prompt: str, **kwargs: Any) -> Any:
        self.calls.append("generate_stream")
        yield self.name

    def ask_question(self, question: str, docs: Any, allow_general_knowledge: bool = True) -> str:
        self.calls.append("ask_question")
        return f"answer from {self.name}"

    def summarize_article(self, content: str) -> str:
        self.calls.append("summarize_article")
        return f"summary from {self.name}"

    def warmup(self, context: str = "chat") -> tuple[bool, str]:
        self.calls.append("warmup")
        return True, f"{self.name}-model"

    def generate_embedding(self, text: str, use_cache: bool = True) -> list[float]:
        self.calls.append("generate_embedding")
        return [0.1, 0.2]

    def semantic_search(self, query: str, docs: Any, top_k: int = 5) -> list[Any]:
        self.calls.append("semantic_search")
        return []

    def semantic_search_with_precomputed_embeddings(
        self, query: str, docs: Any, top_k: int = 5
    ) -> list[Any]:
        self.calls.append("semantic_search_precomputed")
        return []

    def clear_cache(self) -> int:
        self.calls.append("clear_cache")
        return 0


@pytest.fixture
def flag_state(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    """Control the llm_use_api flag seen by RoutingLLMClient."""
    state = {"llm_use_api": False}

    mock_flags = MagicMock()
    mock_flags.is_enabled.side_effect = lambda name: state.get(name, False)
    monkeypatch.setattr("feature_flags.get_feature_flags", lambda: mock_flags)
    return state


@pytest.fixture
def embedding_provider(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Control the embedding_provider setting seen by RoutingLLMClient."""
    state = {"embedding_provider": "ollama"}

    def mock_settings() -> MagicMock:
        settings = MagicMock()
        settings.embedding_provider = state["embedding_provider"]
        return settings

    monkeypatch.setattr(llm_module, "get_settings", mock_settings)
    return state


class TestRoutingLLMClient:
    def _make(
        self, api_available: bool = True
    ) -> tuple[RoutingLLMClient, MockBackend, MockBackend]:
        ollama = MockBackend("ollama")
        api = MockBackend("api", available=api_available)
        return RoutingLLMClient(ollama, api), ollama, api  # type: ignore[arg-type]

    def test_generation_uses_ollama_when_flag_off(self, flag_state: dict[str, bool]) -> None:
        routing, ollama, api = self._make()
        assert routing.generate("hi") == "answer from ollama"
        assert routing.ask_question("q", []) == "answer from ollama"
        assert api.calls == []

    def test_generation_uses_api_when_flag_on(self, flag_state: dict[str, bool]) -> None:
        flag_state["llm_use_api"] = True
        routing, ollama, api = self._make()
        assert routing.generate("hi") == "answer from api"
        assert routing.summarize_article("content") == "summary from api"
        assert list(routing.generate_stream("hi")) == ["api"]
        assert ollama.calls == []

    def test_flag_on_without_api_keys_falls_back_to_ollama(
        self, flag_state: dict[str, bool]
    ) -> None:
        flag_state["llm_use_api"] = True
        routing, ollama, api = self._make(api_available=False)
        assert routing.generate("hi") == "answer from ollama"
        assert api.calls == []

    def test_embeddings_default_to_ollama(
        self, flag_state: dict[str, bool], embedding_provider: dict[str, str]
    ) -> None:
        # The generation flag must not affect embedding routing
        flag_state["llm_use_api"] = True
        routing, ollama, api = self._make()
        routing.generate_embedding("text")
        routing.semantic_search("q", [])
        routing.semantic_search_with_precomputed_embeddings("q", [])
        assert "generate_embedding" in ollama.calls
        assert "semantic_search" in ollama.calls
        assert "semantic_search_precomputed" in ollama.calls
        assert api.calls == []

    def test_embeddings_route_to_api_when_provider_api(
        self, flag_state: dict[str, bool], embedding_provider: dict[str, str]
    ) -> None:
        embedding_provider["embedding_provider"] = "api"
        routing, ollama, api = self._make()
        routing.generate_embedding("text")
        routing.semantic_search("q", [])
        routing.semantic_search_with_precomputed_embeddings("q", [])
        assert "generate_embedding" in api.calls
        assert "semantic_search" in api.calls
        assert "semantic_search_precomputed" in api.calls
        assert ollama.calls == []

    def test_embedding_provider_api_falls_back_to_ollama_without_gemini(
        self, flag_state: dict[str, bool], embedding_provider: dict[str, str]
    ) -> None:
        embedding_provider["embedding_provider"] = "api"
        routing, ollama, api = self._make(api_available=False)
        routing.generate_embedding("text")
        assert "generate_embedding" in ollama.calls
        assert api.calls == []

    def test_embedding_warmup_follows_provider(
        self, flag_state: dict[str, bool], embedding_provider: dict[str, str]
    ) -> None:
        routing, ollama, api = self._make()
        routing.warmup(context="embedding")
        assert ollama.calls == ["warmup"]
        assert api.calls == []

        embedding_provider["embedding_provider"] = "api"
        routing.warmup(context="embedding")
        assert api.calls == ["warmup"]

    def test_has_gpu_true_in_api_mode(self, flag_state: dict[str, bool]) -> None:
        flag_state["llm_use_api"] = True
        routing, ollama, api = self._make()
        assert routing.has_gpu() is True

    def test_active_provider_names(self, flag_state: dict[str, bool]) -> None:
        routing, _, _ = self._make()
        assert routing.active_provider == "ollama"
        flag_state["llm_use_api"] = True
        assert routing.active_provider == "groq"

    def test_embedding_model_tag_follows_provider(
        self, flag_state: dict[str, bool], embedding_provider: dict[str, str]
    ) -> None:
        # .model tags stored embeddings - the generation flag must not move it
        flag_state["llm_use_api"] = True
        routing, _, _ = self._make()
        assert routing.model == "ollama-model"

        embedding_provider["embedding_provider"] = "api"
        assert routing.model == "api-embed"

    def test_embeddings_available_tracks_embedding_backend(
        self, flag_state: dict[str, bool], embedding_provider: dict[str, str]
    ) -> None:
        """Generation can be up while the embedding backend is down."""
        flag_state["llm_use_api"] = True
        ollama = MockBackend("ollama", available=False)
        api = MockBackend("api")
        routing = RoutingLLMClient(ollama, api)  # type: ignore[arg-type]
        assert routing.is_available() is True
        assert routing.embeddings_available() is False

    def test_clear_cache_clears_both_backends(
        self, flag_state: dict[str, bool], embedding_provider: dict[str, str]
    ) -> None:
        routing, ollama, api = self._make()
        routing.clear_cache()
        assert "clear_cache" in ollama.calls
        assert "clear_cache" in api.calls


# ============================================================================
# Provider construction from settings
# ============================================================================


class TestBuildProviders:
    def test_no_keys_no_providers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = MagicMock()
        settings.groq_api_key = None
        settings.gemini_api_key = ""
        monkeypatch.setattr(llm_module, "get_settings", lambda: settings)
        assert llm_module._build_providers() == []

    def test_groq_before_gemini(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settings = MagicMock()
        settings.groq_api_key = "gk"
        settings.groq_base_url = "https://groq.example"
        settings.groq_model = "groq-model"
        settings.gemini_api_key = "mk"
        settings.gemini_base_url = "https://gemini.example"
        settings.gemini_model = "gemini-model"
        monkeypatch.setattr(llm_module, "get_settings", lambda: settings)
        providers = llm_module._build_providers()
        assert [p.name for p in providers] == ["groq", "gemini"]
