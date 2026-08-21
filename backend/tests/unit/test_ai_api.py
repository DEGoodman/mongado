"""Tests for AI API endpoints.

These tests verify AI endpoint behavior both when Ollama is available and when
it gracefully degrades (unavailable). Tests are designed to pass in CI where
Ollama is not running.

Tests marked with @pytest.mark.slow hit real Ollama and can take 30-120+ seconds
on CPU-only systems. Run with `pytest -m "not slow"` to skip them.
"""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from dependencies import get_llm, get_neo4j, get_notes, get_static_articles, get_user_resources
from main import app
from tests.conftest import MockOllamaClient

# Mark for slow tests that hit real Ollama
slow = pytest.mark.slow


class TestOllamaWarmup:
    """Tests for POST /api/ollama/warmup endpoint."""

    def test_warmup_endpoint_returns_valid_response(self, client: TestClient) -> None:
        """Warmup endpoint returns valid response structure."""
        response = client.post("/api/ollama/warmup")

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data
        assert isinstance(data["success"], bool)
        assert isinstance(data["message"], str)

    def test_warmup_response_indicates_availability(self, client: TestClient) -> None:
        """Warmup response message indicates Ollama status."""
        response = client.post("/api/ollama/warmup")
        data = response.json()

        # Either Ollama is available (warmed up) or not (not available)
        if data["success"]:
            assert "warmed up" in data["message"].lower() or "success" in data["message"].lower()
        else:
            assert "not available" in data["message"].lower() or "failed" in data["message"].lower()


class TestGPUStatus:
    """Tests for GET /api/ollama/gpu-status endpoint."""

    def test_gpu_status_returns_valid_response(self, client: TestClient) -> None:
        """GPU status endpoint returns valid response structure."""
        response = client.get("/api/ollama/gpu-status")

        assert response.status_code == 200
        data = response.json()
        assert "has_gpu" in data
        assert "message" in data
        assert isinstance(data["has_gpu"], bool)
        assert isinstance(data["message"], str)

    def test_gpu_status_message_matches_status(self, client: TestClient) -> None:
        """GPU status message is consistent with has_gpu flag."""
        response = client.get("/api/ollama/gpu-status")
        data = response.json()

        if data["has_gpu"]:
            # GPU available - message should indicate GPU
            assert "gpu" in data["message"].lower() or "available" in data["message"].lower()
        else:
            # No GPU or Ollama unavailable
            assert (
                "cpu" in data["message"].lower()
                or "not available" in data["message"].lower()
                or "disabled" in data["message"].lower()
            )


class TestAskQuestion:
    """Tests for POST /api/ask endpoint."""

    @slow
    def test_ask_question_valid_request(self, client: TestClient) -> None:
        """Ask question accepts valid request and returns appropriate response."""
        response = client.post(
            "/api/ask", json={"question": "What is software delivery performance?"}
        )

        # Either success (200) with answer, or 503 if Ollama unavailable
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "answer" in data
            assert "sources" in data
            assert isinstance(data["answer"], str)
            assert isinstance(data["sources"], list)
        else:
            # 503 means Ollama not available - expected in CI
            assert "not available" in response.json()["detail"].lower()

    def test_ask_question_empty_question_handled(self, client: TestClient) -> None:
        """Ask question handles empty question gracefully."""
        response = client.post("/api/ask", json={"question": ""})

        # Empty question is technically valid (str type), endpoint decides behavior
        # Either 200 (with response), 503 (Ollama unavailable), or 400/422 (validation)
        assert response.status_code in [200, 400, 422, 503]

    def test_ask_question_missing_question_rejected(self, client: TestClient) -> None:
        """Ask question requires question field."""
        response = client.post("/api/ask", json={})

        assert response.status_code == 422

    def test_ask_question_provider_chain_exhausted_returns_503(
        self, client: TestClient, mock_ollama_available: MockOllamaClient
    ) -> None:
        """When the LLM provider chain is exhausted (ask_question returns None),
        the endpoint returns a graceful 503, not a bare 500 (#279)."""
        # The client fixture injects this same instance as the ollama dependency,
        # so patching it here makes generation fail while the service stays "up".
        mock_ollama_available.ask_question = lambda *args, **kwargs: None  # type: ignore[assignment,method-assign]

        response = client.post("/api/ask", json={"question": "What is SRE?"})

        assert response.status_code == 503
        assert "temporarily unavailable" in response.json()["detail"].lower()


class TestSuggestTags:
    """Tests for POST /api/notes/{note_id}/suggest-tags endpoint."""

    @slow
    def test_suggest_tags_returns_valid_structure(self, client: TestClient) -> None:
        """Suggest tags returns valid response structure for existing note."""
        # Get a note ID first
        notes_response = client.get("/api/notes")
        if notes_response.status_code != 200:
            pytest.skip("Notes endpoint not available")

        notes = notes_response.json().get("notes", [])
        if not notes:
            pytest.skip("No notes available for testing")

        note_id = notes[0]["id"]
        response = client.post(f"/api/notes/{note_id}/suggest-tags")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "count" in data
        assert isinstance(data["suggestions"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["suggestions"])

    def test_suggest_tags_not_found(self, client: TestClient) -> None:
        """Suggest tags returns 404 for non-existent note."""
        response = client.post("/api/notes/nonexistent-note-id-12345/suggest-tags")
        assert response.status_code == 404


class TestDegradedSignalling:
    """The `degraded` flag must separate "AI failed" from "nothing to suggest" (#260).

    Both cases return an empty suggestions list, so without this flag the
    client cannot tell a broken LLM from a note that genuinely needs no tags.
    """

    NOTE = {
        "id": "test-note",
        "title": "A Note",
        "content": "Some content about reliability.",
        "tags": ["sre"],
        "links": [],
    }

    class _NotesService:
        def __init__(self, note: dict[str, Any]) -> None:
            self._note = note

        def get_note(self, note_id: str) -> dict[str, Any] | None:
            return self._note if note_id == self._note["id"] else None

        def list_notes(self) -> list[dict[str, Any]]:
            return [self._note]

    class _LLM:
        """Stands in for the routed client, with a scriptable generate()."""

        def __init__(self, available: bool = True, response: str | None = None) -> None:
            self._available = available
            self._response = response

        def is_available(self) -> bool:
            return self._available

        def generate(self, prompt: str, **kwargs: Any) -> str | None:
            return self._response

    @contextmanager
    def _client(self, llm: Any) -> Generator[TestClient]:
        app.dependency_overrides[get_llm] = lambda: llm
        app.dependency_overrides[get_notes] = lambda: self._NotesService(self.NOTE)
        try:
            with TestClient(app) as test_client:
                yield test_client
        finally:
            app.dependency_overrides.clear()

    def test_degraded_when_llm_unavailable(self) -> None:
        with self._client(self._LLM(available=False)) as client:
            data = client.post("/api/notes/test-note/suggest-tags").json()

        assert data["suggestions"] == []
        assert data["degraded"] is True

    def test_degraded_when_llm_returns_nothing(self) -> None:
        with self._client(self._LLM(response=None)) as client:
            data = client.post("/api/notes/test-note/suggest-tags").json()

        assert data["degraded"] is True

    def test_degraded_when_output_unparseable(self) -> None:
        with self._client(self._LLM(response="I'm afraid I can't do that.")) as client:
            data = client.post("/api/notes/test-note/suggest-tags").json()

        assert data["degraded"] is True

    def test_not_degraded_when_llm_returns_empty_array(self) -> None:
        """A working LLM that finds no tags is NOT degraded - the key distinction."""
        with self._client(self._LLM(response="[]")) as client:
            data = client.post("/api/notes/test-note/suggest-tags").json()

        assert data["suggestions"] == []
        assert data["degraded"] is False

    def test_not_degraded_on_success(self) -> None:
        response = '[{"tag": "reliability", "confidence": 0.9, "reason": "core topic"}]'
        with self._client(self._LLM(response=response)) as client:
            data = client.post("/api/notes/test-note/suggest-tags").json()

        assert data["count"] == 1
        assert data["degraded"] is False

    def test_prose_wrapped_output_is_not_degraded(self) -> None:
        """The #260 parser fix, verified through the endpoint."""
        response = 'Sure!\n[{"tag": "reliability", "confidence": 0.9, "reason": "core"}]\nDone.'
        with self._client(self._LLM(response=response)) as client:
            data = client.post("/api/notes/test-note/suggest-tags").json()

        assert data["count"] == 1
        assert data["suggestions"][0]["tag"] == "reliability"
        assert data["degraded"] is False


class TestSuggestLinks:
    """Tests for POST /api/notes/{note_id}/suggest-links endpoint."""

    @slow
    def test_suggest_links_returns_valid_structure(self, client: TestClient) -> None:
        """Suggest links returns valid response structure for existing note."""
        notes_response = client.get("/api/notes")
        if notes_response.status_code != 200:
            pytest.skip("Notes endpoint not available")

        notes = notes_response.json().get("notes", [])
        if not notes:
            pytest.skip("No notes available for testing")

        note_id = notes[0]["id"]
        response = client.post(f"/api/notes/{note_id}/suggest-links")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "count" in data
        assert isinstance(data["suggestions"], list)
        assert isinstance(data["count"], int)

    def test_suggest_links_not_found(self, client: TestClient) -> None:
        """Suggest links returns 404 for non-existent note."""
        response = client.post("/api/notes/nonexistent-note-id-12345/suggest-links")
        assert response.status_code == 404


class TestArticleSummary:
    """Tests for GET /api/articles/{article_id}/summary endpoint."""

    @slow
    def test_article_summary_valid_response(self, client: TestClient) -> None:
        """Article summary returns valid response for existing article."""
        # Get first article ID
        articles_response = client.get("/api/articles")
        if articles_response.status_code != 200:
            pytest.skip("Articles endpoint not available")

        articles = articles_response.json().get("resources", [])
        if not articles:
            pytest.skip("No articles available for testing")

        article_id = articles[0]["id"]
        response = client.get(f"/api/articles/{article_id}/summary")

        # Either success or 503 if Ollama unavailable
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert "summary" in data
            assert isinstance(data["summary"], str)
            assert len(data["summary"]) > 0

    def test_article_summary_not_found(self, client: TestClient) -> None:
        """Article summary returns 404 for non-existent article (or 503 if Ollama unavailable)."""
        response = client.get("/api/articles/99999/summary")
        # 404 if Ollama available and article not found
        # 503 if Ollama unavailable (checked first in endpoint)
        assert response.status_code in [404, 503]


class TestExtractConcepts:
    """Tests for POST /api/articles/{article_id}/extract-concepts endpoint."""

    @slow
    def test_extract_concepts_valid_response(self, client: TestClient) -> None:
        """Extract concepts returns valid response structure."""
        articles_response = client.get("/api/articles")
        if articles_response.status_code != 200:
            pytest.skip("Articles endpoint not available")

        articles = articles_response.json().get("resources", [])
        if not articles:
            pytest.skip("No articles available for testing")

        article_id = articles[0]["id"]
        response = client.post(f"/api/articles/{article_id}/extract-concepts")

        assert response.status_code == 200
        data = response.json()
        assert "concepts" in data
        assert "count" in data
        assert isinstance(data["concepts"], list)
        assert isinstance(data["count"], int)

    def test_extract_concepts_not_found(self, client: TestClient) -> None:
        """Extract concepts returns 404 for non-existent article (or empty if Ollama unavailable)."""
        response = client.post("/api/articles/99999/extract-concepts")
        # 404 if Ollama available and article not found
        # 200 with empty concepts if Ollama unavailable (graceful degradation)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["concepts"] == []
            assert data["count"] == 0


class _SynthesisLLM:
    """Scriptable stand-in for the routed LLM client, for synthesis tests."""

    def __init__(
        self,
        available: bool = True,
        generate_response: str | None = "## Key Concepts\nStuff.\n\n## Your Positions\nMore.\n\n## Gaps & Open Questions\nUnknown.",
        stream_tokens: list[str] | None = None,
    ) -> None:
        self._available = available
        self._generate_response = generate_response
        self._stream_tokens = (
            stream_tokens if stream_tokens is not None else ["## Key Concepts\n", "Stuff.\n"]
        )

    def is_available(self) -> bool:
        return self._available

    def embeddings_available(self) -> bool:
        return self._available

    def generate(self, prompt: str, **kwargs: Any) -> str | None:
        return self._generate_response

    def generate_stream(self, prompt: str, **kwargs: Any) -> Generator[str]:
        yield from self._stream_tokens

    def semantic_search(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        results = []
        for i, doc in enumerate(documents[:top_k]):
            results.append({**doc, "score": 0.9 - (i * 0.1)})
        return results


class _UnavailableNeo4j:
    """Stands in for the Neo4j adapter, always reporting unavailable.

    This forces retrieval down to tier 3 (on-demand embedding generation via
    ollama.semantic_search), which is enough to exercise the endpoints without
    needing a real Neo4j instance.
    """

    def is_available(self) -> bool:
        return False


class _SynthesisNotesService:
    def list_notes(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "curious-elephant",
                "title": "Incident Response Basics",
                "content": "Runbooks matter a lot.",
                "tags": ["sre"],
            }
        ]


@contextmanager
def _synthesis_client(
    llm: Any, notes_service: Any | None = None
) -> Generator[TestClient]:
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_notes] = lambda: notes_service or _SynthesisNotesService()
    app.dependency_overrides[get_neo4j] = lambda: _UnavailableNeo4j()
    app.dependency_overrides[get_static_articles] = lambda: [
        {"id": 1, "title": "SRE Practices", "content": "On-call and monitoring."}
    ]
    app.dependency_overrides[get_user_resources] = lambda: []
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


class TestSynthesize:
    """Tests for POST /api/synthesize."""

    def test_happy_path_returns_synthesis_and_sources(self) -> None:
        with _synthesis_client(_SynthesisLLM()) as client:
            response = client.post(
                "/api/synthesize", json={"query": "incident response"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "## Key Concepts" in data["synthesis"]
        assert data["degraded"] is False
        assert len(data["sources"]) > 0
        # Sources use the id/type/title/content/score shape the frontend renders.
        source = data["sources"][0]
        assert {"id", "type", "title", "content", "score"} <= source.keys()

    def test_ai_unavailable_returns_503(self) -> None:
        with _synthesis_client(_SynthesisLLM(available=False)) as client:
            response = client.post(
                "/api/synthesize", json={"query": "incident response"}
            )

        assert response.status_code == 503

    def test_empty_llm_response_is_degraded(self) -> None:
        with _synthesis_client(_SynthesisLLM(generate_response=None)) as client:
            response = client.post(
                "/api/synthesize", json={"query": "incident response"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True
        assert data["synthesis"] == ""

    def test_missing_query_rejected(self) -> None:
        with _synthesis_client(_SynthesisLLM()) as client:
            response = client.post("/api/synthesize", json={})

        assert response.status_code == 422


class TestSynthesizeStream:
    """Tests for POST /api/synthesize/stream."""

    def _events(self, response: Any) -> list[dict[str, Any]]:
        import json as _json

        events = []
        for line in response.text.split("\n\n"):
            line = line.strip()
            if line.startswith("data: "):
                events.append(_json.loads(line[len("data: ") :]))
        return events

    def test_stream_emits_sources_before_tokens_then_completes(self) -> None:
        with _synthesis_client(
            _SynthesisLLM(stream_tokens=["## Key Concepts\n", "Some ", "text."])
        ) as client:
            response = client.post(
                "/api/synthesize/stream", json={"query": "incident response"}
            )

        assert response.status_code == 200
        events = self._events(response)
        types = [e["type"] for e in events]

        assert types[0] == "sources"
        assert "token" in types
        assert types[-1] == "complete"
        # sources must precede every token event
        sources_index = types.index("sources")
        first_token_index = types.index("token")
        assert sources_index < first_token_index

    def test_stream_degrades_gracefully_when_ai_unavailable(self) -> None:
        with _synthesis_client(_SynthesisLLM(available=False)) as client:
            response = client.post(
                "/api/synthesize/stream", json={"query": "incident response"}
            )

        assert response.status_code == 200
        events = self._events(response)
        assert events[0]["type"] == "error"

    def test_stream_emits_error_on_empty_generation(self) -> None:
        with _synthesis_client(_SynthesisLLM(stream_tokens=[])) as client:
            response = client.post(
                "/api/synthesize/stream", json={"query": "incident response"}
            )

        assert response.status_code == 200
        events = self._events(response)
        types = [e["type"] for e in events]
        assert "sources" in types
        assert "error" in types
        assert "complete" not in types


class _EditorLLM:
    """Scriptable stand-in for the routed LLM client, for editor-assist tests."""

    def __init__(
        self,
        available: bool = True,
        generate_response: str | None = "Expanded version of the text.",
        stream_tokens: list[str] | None = None,
        embeddings_available: bool = True,
    ) -> None:
        self._available = available
        self._generate_response = generate_response
        self._stream_tokens = (
            stream_tokens if stream_tokens is not None else ["Expanded ", "text."]
        )
        self._embeddings_available = embeddings_available

    def is_available(self) -> bool:
        return self._available

    def embeddings_available(self) -> bool:
        return self._embeddings_available

    def generate(self, prompt: str, **kwargs: Any) -> str | None:
        return self._generate_response

    def generate_stream(self, prompt: str, **kwargs: Any) -> Generator[str]:
        yield from self._stream_tokens

    def semantic_search(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        results = []
        for i, doc in enumerate(documents[:top_k]):
            results.append({**doc, "score": 0.9 - (i * 0.1)})
        return results


class _EditorNotesService:
    """Stand-in notes service with the two candidate notes /link can suggest."""

    def list_notes(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "curious-elephant",
                "title": "Incident Response Basics",
                "content": "Runbooks matter a lot.",
                "tags": ["sre"],
                "links": [],
            },
            {
                "id": "wise-mountain",
                "title": "Blameless Postmortems",
                "content": "Focus on systems, not people.",
                "tags": ["sre"],
                "links": [],
            },
        ]

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        return next((n for n in self.list_notes() if n["id"] == note_id), None)


@contextmanager
def _editor_client(llm: Any, notes_service: Any | None = None) -> Generator[TestClient]:
    app.dependency_overrides[get_llm] = lambda: llm
    app.dependency_overrides[get_notes] = lambda: notes_service or _EditorNotesService()
    # Writing-partner commands (#146 Phase 2) also depend on neo4j/static
    # articles/user resources for retrieval. _UnavailableNeo4j forces the
    # retrieval ladder down to tier 3 (on-demand embeddings via
    # llm.semantic_search), same as _synthesis_client, so these tests don't
    # need a real Neo4j instance.
    app.dependency_overrides[get_neo4j] = lambda: _UnavailableNeo4j()
    app.dependency_overrides[get_static_articles] = lambda: []
    app.dependency_overrides[get_user_resources] = lambda: []
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


class TestEditorAssist:
    """Tests for POST /api/editor/assist (#146)."""

    def test_happy_path_transform_command(self, admin_headers: dict[str, str]) -> None:
        with _editor_client(_EditorLLM(generate_response="Expanded version.")) as client:
            response = client.post(
                "/api/editor/assist",
                json={"command": "expand", "text": "short text"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["command"] == "expand"
        assert data["result"] == "Expanded version."
        assert data["degraded"] is False

    def test_link_command_returns_suggestions(self, admin_headers: dict[str, str]) -> None:
        with _editor_client(
            _EditorLLM(
                generate_response=(
                    '[{"note_id": "wise-mountain", "confidence": 0.8, "reason": "related"}]'
                )
            )
        ) as client:
            response = client.post(
                "/api/editor/assist",
                json={
                    "command": "link",
                    "text": "some text about postmortems",
                    "note_id": "curious-elephant",
                },
                headers=admin_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["command"] == "link"
        assert data["suggestions"][0]["note_id"] == "wise-mountain"

    def test_unauthenticated_rejected(self) -> None:
        with _editor_client(_EditorLLM()) as client:
            response = client.post(
                "/api/editor/assist", json={"command": "expand", "text": "hi"}
            )

        assert response.status_code == 401

    def test_unknown_command_rejected(self, admin_headers: dict[str, str]) -> None:
        with _editor_client(_EditorLLM()) as client:
            response = client.post(
                "/api/editor/assist",
                json={"command": "frobnicate", "text": "hi"},
                headers=admin_headers,
            )

        assert response.status_code == 400

    def test_ai_unavailable_returns_503(self, admin_headers: dict[str, str]) -> None:
        with _editor_client(_EditorLLM(available=False)) as client:
            response = client.post(
                "/api/editor/assist",
                json={"command": "expand", "text": "hi"},
                headers=admin_headers,
            )

        assert response.status_code == 503

    def test_empty_llm_response_is_degraded(self, admin_headers: dict[str, str]) -> None:
        with _editor_client(_EditorLLM(generate_response=None)) as client:
            response = client.post(
                "/api/editor/assist",
                json={"command": "expand", "text": "hi"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True


class TestEditorAssistStream:
    """Tests for POST /api/editor/assist/stream (#146)."""

    def _events(self, response: Any) -> list[dict[str, Any]]:
        import json as _json

        events = []
        for line in response.text.split("\n\n"):
            line = line.strip()
            if line.startswith("data: "):
                events.append(_json.loads(line[len("data: ") :]))
        return events

    def test_stream_emits_tokens_then_complete(self, admin_headers: dict[str, str]) -> None:
        with _editor_client(_EditorLLM(stream_tokens=["Ex", "pand", "ed."])) as client:
            response = client.post(
                "/api/editor/assist/stream",
                json={"command": "expand", "text": "hi"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        events = self._events(response)
        types = [e["type"] for e in events]
        assert types == ["token", "token", "token", "complete"]

    def test_link_stream_emits_link_events_then_complete(
        self, admin_headers: dict[str, str]
    ) -> None:
        with _editor_client(
            _EditorLLM(
                stream_tokens=[
                    '[{"note_id": "wise-mountain", "confidence": 0.8, "reason": "related"}]'
                ]
            )
        ) as client:
            response = client.post(
                "/api/editor/assist/stream",
                json={"command": "link", "text": "text", "note_id": "curious-elephant"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        events = self._events(response)
        types = [e["type"] for e in events]
        assert "link" in types
        assert types[-1] == "complete"
        link_event = next(e for e in events if e["type"] == "link")
        assert link_event["note_id"] == "wise-mountain"

    def test_unauthenticated_rejected(self) -> None:
        with _editor_client(_EditorLLM()) as client:
            response = client.post(
                "/api/editor/assist/stream", json={"command": "expand", "text": "hi"}
            )

        assert response.status_code == 401

    def test_stream_degrades_gracefully_when_ai_unavailable(
        self, admin_headers: dict[str, str]
    ) -> None:
        with _editor_client(_EditorLLM(available=False)) as client:
            response = client.post(
                "/api/editor/assist/stream",
                json={"command": "expand", "text": "hi"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        events = self._events(response)
        assert events[0]["type"] == "error"

    def test_stream_emits_error_on_empty_generation(
        self, admin_headers: dict[str, str]
    ) -> None:
        with _editor_client(_EditorLLM(stream_tokens=[])) as client:
            response = client.post(
                "/api/editor/assist/stream",
                json={"command": "expand", "text": "hi"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        events = self._events(response)
        types = [e["type"] for e in events]
        assert "error" in types
        assert "complete" not in types


class _PartnerNotesService:
    """Stand-in notes service for writing-partner tests: two other notes plus
    the note currently being edited (curious-elephant), so tests can assert
    the current note is excluded from its own retrieval results."""

    def list_notes(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "curious-elephant",
                "title": "Current Note",
                "content": "This is the note being edited right now.",
                "tags": [],
                "links": [],
            },
            {
                "id": "wise-mountain",
                "title": "Blameless Postmortems",
                "content": "Focus on systems, not people.",
                "tags": ["sre"],
                "links": [],
            },
            {
                "id": "brave-otter",
                "title": "Incident Response Basics",
                "content": "Runbooks matter a lot.",
                "tags": ["sre"],
                "links": [],
            },
        ]

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        return next((n for n in self.list_notes() if n["id"] == note_id), None)


class TestEditorAssistWritingPartner:
    """Tests for the challenge/gaps/contradictions commands on POST /api/editor/assist (#146 Phase 2)."""

    @pytest.mark.parametrize("command", ["challenge", "gaps", "contradictions"])
    def test_happy_path_returns_result_and_sources(
        self, command: str, admin_headers: dict[str, str]
    ) -> None:
        with _editor_client(
            _EditorLLM(generate_response="This is my critique. (Blameless Postmortems)"),
            notes_service=_PartnerNotesService(),
        ) as client:
            response = client.post(
                "/api/editor/assist",
                json={
                    "command": command,
                    "text": "Postmortems should always assign blame.",
                    "note_title": "My Draft",
                    "note_id": "curious-elephant",
                },
                headers=admin_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["command"] == command
        assert data["result"] == "This is my critique. (Blameless Postmortems)"
        assert data["degraded"] is False
        assert len(data["sources"]) > 0
        source = data["sources"][0]
        assert {"id", "type", "title", "content", "score"} <= source.keys()

    def test_current_note_excluded_from_its_own_sources(
        self, admin_headers: dict[str, str]
    ) -> None:
        with _editor_client(
            _EditorLLM(generate_response="Critique."),
            notes_service=_PartnerNotesService(),
        ) as client:
            response = client.post(
                "/api/editor/assist",
                json={
                    "command": "contradictions",
                    "text": "Some claim.",
                    "note_title": "Current Note",
                    "note_id": "curious-elephant",
                },
                headers=admin_headers,
            )

        assert response.status_code == 200
        data = response.json()
        source_ids = {s["id"] for s in data["sources"]}
        assert "curious-elephant" not in source_ids

    def test_unauthenticated_rejected(self) -> None:
        with _editor_client(_EditorLLM(), notes_service=_PartnerNotesService()) as client:
            response = client.post(
                "/api/editor/assist", json={"command": "gaps", "text": "hi"}
            )

        assert response.status_code == 401

    def test_ai_unavailable_returns_503(self, admin_headers: dict[str, str]) -> None:
        with _editor_client(
            _EditorLLM(available=False), notes_service=_PartnerNotesService()
        ) as client:
            response = client.post(
                "/api/editor/assist",
                json={"command": "gaps", "text": "hi"},
                headers=admin_headers,
            )

        assert response.status_code == 503

    def test_empty_llm_response_is_degraded(self, admin_headers: dict[str, str]) -> None:
        with _editor_client(
            _EditorLLM(generate_response=None), notes_service=_PartnerNotesService()
        ) as client:
            response = client.post(
                "/api/editor/assist",
                json={"command": "gaps", "text": "hi"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True

    def test_zero_retrieval_returns_degraded_without_calling_llm(
        self, admin_headers: dict[str, str]
    ) -> None:
        """No embeddings available -> retrieval returns nothing -> the
        endpoint must not call the LLM with an empty context."""

        class _NoEmbeddingsLLM(_EditorLLM):
            def generate(self, prompt: str, **kwargs: Any) -> str | None:
                raise AssertionError("LLM must not be called when retrieval is empty")

        with _editor_client(
            _NoEmbeddingsLLM(embeddings_available=False),
            notes_service=_PartnerNotesService(),
        ) as client:
            response = client.post(
                "/api/editor/assist",
                json={"command": "gaps", "text": "hi", "note_id": "curious-elephant"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["degraded"] is True
        assert data["sources"] == []

    def test_phase1_transform_command_unchanged(self, admin_headers: dict[str, str]) -> None:
        """Regression: transform commands still return result/degraded only,
        with sources absent (None), unaffected by the new deps."""
        with _editor_client(
            _EditorLLM(generate_response="Expanded version."),
            notes_service=_PartnerNotesService(),
        ) as client:
            response = client.post(
                "/api/editor/assist",
                json={"command": "expand", "text": "short text"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "Expanded version."
        assert data.get("sources") is None

    def test_phase1_link_command_unchanged(self, admin_headers: dict[str, str]) -> None:
        """Regression: /link still returns suggestions, unaffected by the new deps."""
        with _editor_client(
            _EditorLLM(
                generate_response=(
                    '[{"note_id": "wise-mountain", "confidence": 0.8, "reason": "related"}]'
                )
            ),
            notes_service=_EditorNotesService(),
        ) as client:
            response = client.post(
                "/api/editor/assist",
                json={
                    "command": "link",
                    "text": "some text about postmortems",
                    "note_id": "curious-elephant",
                },
                headers=admin_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"][0]["note_id"] == "wise-mountain"


class TestEditorAssistStreamWritingPartner:
    """Tests for the challenge/gaps/contradictions commands on POST /api/editor/assist/stream (#146 Phase 2)."""

    def _events(self, response: Any) -> list[dict[str, Any]]:
        import json as _json

        events = []
        for line in response.text.split("\n\n"):
            line = line.strip()
            if line.startswith("data: "):
                events.append(_json.loads(line[len("data: ") :]))
        return events

    def test_stream_emits_sources_before_tokens_then_completes(
        self, admin_headers: dict[str, str]
    ) -> None:
        with _editor_client(
            _EditorLLM(stream_tokens=["This ", "is ", "my critique."]),
            notes_service=_PartnerNotesService(),
        ) as client:
            response = client.post(
                "/api/editor/assist/stream",
                json={
                    "command": "challenge",
                    "text": "Postmortems should assign blame.",
                    "note_title": "My Draft",
                    "note_id": "curious-elephant",
                },
                headers=admin_headers,
            )

        assert response.status_code == 200
        events = self._events(response)
        types = [e["type"] for e in events]

        assert types[0] == "sources"
        assert "token" in types
        assert types[-1] == "complete"
        assert types.index("sources") < types.index("token")

    def test_current_note_excluded_from_stream_sources(
        self, admin_headers: dict[str, str]
    ) -> None:
        with _editor_client(
            _EditorLLM(stream_tokens=["Critique."]),
            notes_service=_PartnerNotesService(),
        ) as client:
            response = client.post(
                "/api/editor/assist/stream",
                json={
                    "command": "contradictions",
                    "text": "Some claim.",
                    "note_title": "Current Note",
                    "note_id": "curious-elephant",
                },
                headers=admin_headers,
            )

        events = self._events(response)
        sources_event = next(e for e in events if e["type"] == "sources")
        source_ids = {s["id"] for s in sources_event["sources"]}
        assert "curious-elephant" not in source_ids

    def test_unauthenticated_rejected(self) -> None:
        with _editor_client(_EditorLLM(), notes_service=_PartnerNotesService()) as client:
            response = client.post(
                "/api/editor/assist/stream", json={"command": "gaps", "text": "hi"}
            )

        assert response.status_code == 401

    def test_stream_degrades_gracefully_when_ai_unavailable(
        self, admin_headers: dict[str, str]
    ) -> None:
        with _editor_client(
            _EditorLLM(available=False), notes_service=_PartnerNotesService()
        ) as client:
            response = client.post(
                "/api/editor/assist/stream",
                json={"command": "gaps", "text": "hi"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        events = self._events(response)
        assert events[0]["type"] == "error"

    def test_zero_retrieval_emits_sources_then_degraded_complete_without_calling_llm(
        self, admin_headers: dict[str, str]
    ) -> None:
        class _NoEmbeddingsLLM(_EditorLLM):
            def generate_stream(self, prompt: str, **kwargs: Any) -> Generator[str]:
                raise AssertionError("LLM must not be called when retrieval is empty")
                yield ""  # pragma: no cover - unreachable, satisfies generator typing

        with _editor_client(
            _NoEmbeddingsLLM(embeddings_available=False),
            notes_service=_PartnerNotesService(),
        ) as client:
            response = client.post(
                "/api/editor/assist/stream",
                json={"command": "gaps", "text": "hi", "note_id": "curious-elephant"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        events = self._events(response)
        types = [e["type"] for e in events]
        assert types[0] == "sources"
        assert events[0]["sources"] == []
        assert "token" in types  # the "nothing to check against" message
        complete_event = next(e for e in events if e["type"] == "complete")
        assert complete_event.get("degraded") is True

    def test_phase1_transform_stream_unchanged(self, admin_headers: dict[str, str]) -> None:
        """Regression: transform command streams still emit token/complete only,
        no sources event, unaffected by the new deps."""
        with _editor_client(
            _EditorLLM(stream_tokens=["Ex", "pand", "ed."]),
            notes_service=_PartnerNotesService(),
        ) as client:
            response = client.post(
                "/api/editor/assist/stream",
                json={"command": "expand", "text": "hi"},
                headers=admin_headers,
            )

        assert response.status_code == 200
        events = self._events(response)
        types = [e["type"] for e in events]
        assert types == ["token", "token", "token", "complete"]


class TestMockOllamaClientUnit:
    """Unit tests for the MockOllamaClient fixture to ensure it works correctly."""

    def test_mock_client_available(self) -> None:
        """Mock client reports availability correctly."""
        from tests.conftest import MockOllamaClient

        available_client = MockOllamaClient(available=True)
        unavailable_client = MockOllamaClient(available=False)

        assert available_client.is_available() is True
        assert unavailable_client.is_available() is False

    def test_mock_client_gpu_status(self) -> None:
        """Mock client reports GPU status correctly."""
        from tests.conftest import MockOllamaClient

        cpu_client = MockOllamaClient(available=True, has_gpu=False)
        gpu_client = MockOllamaClient(available=True, has_gpu=True)
        unavailable_client = MockOllamaClient(available=False, has_gpu=True)

        assert cpu_client.has_gpu() is False
        assert gpu_client.has_gpu() is True
        # Unavailable client should return False for GPU even if configured
        assert unavailable_client.has_gpu() is False

    def test_mock_embedding_generation(self) -> None:
        """Mock client generates consistent embeddings."""
        from tests.conftest import MockOllamaClient

        client = MockOllamaClient(available=True)

        embedding1 = client.generate_embedding("test text")
        embedding2 = client.generate_embedding("test text")

        assert embedding1 is not None
        assert len(embedding1) == 768  # Standard dimension
        assert embedding1 == embedding2  # Same text = same embedding

    def test_mock_embedding_unavailable(self) -> None:
        """Mock client returns None when unavailable."""
        from tests.conftest import MockOllamaClient

        client = MockOllamaClient(available=False)

        embedding = client.generate_embedding("test text")
        assert embedding is None

    def test_mock_semantic_search(self) -> None:
        """Mock semantic search returns documents with scores."""
        from tests.conftest import MockOllamaClient

        client = MockOllamaClient(available=True)
        docs = [
            {"id": 1, "title": "Doc 1", "content": "Content 1"},
            {"id": 2, "title": "Doc 2", "content": "Content 2"},
        ]

        results = client.semantic_search("query", docs, top_k=2)

        assert len(results) == 2
        assert all("score" in r for r in results)
        # First result should have higher score
        assert results[0]["score"] > results[1]["score"]

    def test_mock_ask_question(self) -> None:
        """Mock Q&A returns answer referencing context."""
        from tests.conftest import MockOllamaClient

        client = MockOllamaClient(available=True)
        context = [{"title": "Test Article"}]

        answer = client.ask_question("What is testing?", context)

        assert answer is not None
        assert "Test Article" in answer

    def test_mock_summarize(self) -> None:
        """Mock summarization returns summary."""
        from tests.conftest import MockOllamaClient

        client = MockOllamaClient(available=True)

        summary = client.summarize_article("This is a long article about testing.")

        assert summary is not None
        assert "mock summary" in summary.lower()

    def test_mock_warmup(self) -> None:
        """Mock warmup returns (success, model) tuple."""
        from tests.conftest import MockOllamaClient

        available_client = MockOllamaClient(available=True)
        unavailable_client = MockOllamaClient(available=False)

        # Available client returns success with model name
        success, model = available_client.warmup()
        assert success is True
        assert model == "llama3.2:1b"  # Default chat model

        # Unavailable client returns failure
        success, model = unavailable_client.warmup()
        assert success is False
        assert model == ""

    def test_mock_warmup_context(self) -> None:
        """Mock warmup respects context parameter."""
        from tests.conftest import MockOllamaClient

        client = MockOllamaClient(available=True)

        # Chat context (default)
        success, model = client.warmup("chat")
        assert success is True
        assert model == "llama3.2:1b"

        # Structured context
        success, model = client.warmup("structured")
        assert success is True
        assert model == "qwen2.5:1.5b"

        # Embedding context
        success, model = client.warmup("embedding")
        assert success is True
        assert model == "nomic-embed-text"

    def test_mock_cosine_similarity(self) -> None:
        """Mock cosine similarity calculation works correctly."""
        from tests.conftest import MockOllamaClient

        # Identical vectors should have similarity 1.0
        vec = [1.0, 0.0, 0.0]
        assert MockOllamaClient._cosine_similarity(vec, vec) == pytest.approx(1.0)

        # Orthogonal vectors should have similarity 0.0
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        assert MockOllamaClient._cosine_similarity(vec1, vec2) == pytest.approx(0.0)

        # Different length vectors should return 0.0
        assert MockOllamaClient._cosine_similarity([1.0], [1.0, 2.0]) == 0.0


class TestSuggestStream:
    """Tests for GET /api/notes/{note_id}/suggest-stream endpoint (SSE streaming).

    Note: Tests that require actual AI generation are marked @slow because
    the current architecture captures ollama_client in closures at import time,
    making mocking difficult. See issue #141 for the planned DI refactor.
    """

    def test_suggest_stream_not_found(self, client: TestClient) -> None:
        """Streaming endpoint returns error event for non-existent note."""
        response = client.get("/api/notes/nonexistent-note-id-12345/suggest-stream")

        assert response.status_code == 200  # SSE always returns 200, errors in stream
        content = response.text

        # Should have error event
        assert "data: " in content
        assert '"type": "error"' in content or '"type":"error"' in content
        assert "not found" in content.lower()

    @slow
    def test_suggest_stream_returns_sse_content_type(self, client: TestClient) -> None:
        """Streaming endpoint returns text/event-stream content type."""
        # Get a note ID first
        notes_response = client.get("/api/notes")
        if notes_response.status_code != 200:
            pytest.skip("Notes endpoint not available")

        notes = notes_response.json().get("notes", [])
        if not notes:
            pytest.skip("No notes available for testing")

        note_id = notes[0]["id"]
        response = client.get(f"/api/notes/{note_id}/suggest-stream")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    @slow
    def test_suggest_stream_returns_sse_events(self, client: TestClient) -> None:
        """Streaming endpoint returns properly formatted SSE events."""
        notes_response = client.get("/api/notes")
        if notes_response.status_code != 200:
            pytest.skip("Notes endpoint not available")

        notes = notes_response.json().get("notes", [])
        if not notes:
            pytest.skip("No notes available for testing")

        note_id = notes[0]["id"]
        response = client.get(f"/api/notes/{note_id}/suggest-stream")

        assert response.status_code == 200
        content = response.text

        # SSE events should start with "data: "
        assert "data: " in content

        # Parse events
        events = []
        for line in content.split("\n\n"):
            if line.startswith("data: "):
                import json

                try:
                    event_data = json.loads(line[6:])  # Skip "data: "
                    events.append(event_data)
                except json.JSONDecodeError:
                    pass

        # Should have at least progress and complete events
        assert len(events) >= 1

        # First event should be progress or error
        assert events[0]["type"] in ["progress", "error"]

        # If Ollama is available, should have complete event at end
        # If not available, should have error event
        last_event_type = events[-1]["type"]
        assert last_event_type in ["complete", "error"]

    @slow
    def test_suggest_stream_full_flow(self, client: TestClient) -> None:
        """Full streaming flow returns tags and links (slow test, hits real Ollama)."""
        notes_response = client.get("/api/notes")
        if notes_response.status_code != 200:
            pytest.skip("Notes endpoint not available")

        notes = notes_response.json().get("notes", [])
        if not notes:
            pytest.skip("No notes available for testing")

        note_id = notes[0]["id"]
        response = client.get(f"/api/notes/{note_id}/suggest-stream")

        assert response.status_code == 200
        content = response.text

        # Parse all events
        events = []
        for line in content.split("\n\n"):
            if line.startswith("data: "):
                import json

                try:
                    event_data = json.loads(line[6:])
                    events.append(event_data)
                except json.JSONDecodeError:
                    pass

        event_types = [e.get("type") for e in events]

        # If Ollama is available, should see progress phases
        if "error" not in event_types:
            assert "progress" in event_types
            assert "complete" in event_types

            # Check progress phases
            progress_events = [e for e in events if e.get("type") == "progress"]
            phases = [e.get("phase") for e in progress_events]
            assert "tags" in phases
            assert "links" in phases

    def test_suggest_stream_generating_events(self, client: TestClient) -> None:
        """Streaming generates 'generating' heartbeat events during token generation."""
        notes_response = client.get("/api/notes")
        if notes_response.status_code != 200:
            pytest.skip("Notes endpoint not available")

        notes = notes_response.json().get("notes", [])
        if not notes:
            pytest.skip("No notes available for testing")

        note_id = notes[0]["id"]
        response = client.get(f"/api/notes/{note_id}/suggest-stream")

        assert response.status_code == 200
        content = response.text

        # Parse all events
        events = []
        for line in content.split("\n\n"):
            if line.startswith("data: "):
                import json

                try:
                    event_data = json.loads(line[6:])
                    events.append(event_data)
                except json.JSONDecodeError:
                    pass

        event_types = [e.get("type") for e in events]

        # If not an error, should have generating events with token counts
        if "error" not in event_types:
            # The mock generates tokens character by character, so we get generating events
            generating_events = [e for e in events if e.get("type") == "generating"]
            # Should have at least some generating events (sent every 10 tokens)
            # Mock returns ~60 chars so we expect at least 5-6 generating events
            assert len(generating_events) >= 4
            # Each should have phase and token count
            for gen_event in generating_events:
                assert "phase" in gen_event
                assert "tokens" in gen_event
                assert gen_event["tokens"] > 0

    @slow
    def test_suggest_stream_no_buffering_headers(self, client: TestClient) -> None:
        """Streaming endpoint sets proper no-buffering headers."""
        notes_response = client.get("/api/notes")
        if notes_response.status_code != 200:
            pytest.skip("Notes endpoint not available")

        notes = notes_response.json().get("notes", [])
        if not notes:
            pytest.skip("No notes available for testing")

        note_id = notes[0]["id"]
        response = client.get(f"/api/notes/{note_id}/suggest-stream")

        assert response.status_code == 200
        # Check for no-cache header
        assert response.headers.get("cache-control") == "no-cache"
