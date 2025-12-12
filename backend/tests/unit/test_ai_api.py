"""Tests for AI API endpoints.

These tests verify AI endpoint behavior both when Ollama is available and when
it gracefully degrades (unavailable). Tests are designed to pass in CI where
Ollama is not running.

Tests marked with @pytest.mark.slow hit real Ollama and can take 30-120+ seconds
on CPU-only systems. Run with `pytest -m "not slow"` to skip them.
"""

import pytest
from fastapi.testclient import TestClient

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
            "/api/ask",
            json={"question": "What is software delivery performance?"}
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
        response = client.post(
            "/api/ask",
            json={"question": ""}
        )

        # Empty question is technically valid (str type), endpoint decides behavior
        # Either 200 (with response), 503 (Ollama unavailable), or 400/422 (validation)
        assert response.status_code in [200, 400, 422, 503]

    def test_ask_question_missing_question_rejected(self, client: TestClient) -> None:
        """Ask question requires question field."""
        response = client.post(
            "/api/ask",
            json={}
        )

        assert response.status_code == 422


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
        """Mock warmup returns availability status."""
        from tests.conftest import MockOllamaClient

        available_client = MockOllamaClient(available=True)
        unavailable_client = MockOllamaClient(available=False)

        assert available_client.warmup() is True
        assert unavailable_client.warmup() is False

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
