"""Pytest configuration and fixtures."""

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

# Set TESTING environment variable BEFORE any imports
os.environ["TESTING"] = "1"
# Enable LLM features in tests so AI endpoints are registered
os.environ["LLM_FEATURES_ENABLED"] = "true"

import pytest
from fastapi.testclient import TestClient

import main

# ============================================================================
# Mock Classes (defined first so fixtures can use them)
# ============================================================================


class MockOllamaClient:
    """Mock OllamaClient for testing AI endpoints without a running Ollama instance.

    This mock provides predictable responses for all OllamaClient methods,
    allowing AI endpoint tests to run in CI without Ollama.
    """

    def __init__(self, available: bool = True, has_gpu: bool = False) -> None:
        """Initialize mock client.

        Args:
            available: Whether Ollama should appear available
            has_gpu: Whether GPU should appear available
        """
        self._available = available
        self._has_gpu = has_gpu
        self.enabled = available
        self.host = "http://mock:11434"
        self.embed_model = "nomic-embed-text"
        self.chat_model = "llama3.2:1b"  # Chat/Q&A model
        self.structured_model = "qwen2.5:1.5b"  # JSON output model
        self.model = "llama3.2:1b"  # Backwards compatibility
        self.num_ctx = 4096
        self.embedding_cache: dict[str, list[float]] = {}

        # Mock the internal ollama client
        self.client = MagicMock()

        def mock_generate(**kwargs: Any) -> Any:
            """Mock generate that supports streaming."""
            response_text = '[{"tag": "mock-tag", "confidence": 0.8, "reason": "mock reason"}]'
            if kwargs.get("stream"):
                # Return an iterator for streaming mode
                def stream_generator() -> Generator[dict[str, Any]]:
                    for char in response_text:
                        yield {"response": char, "done": False}
                    yield {"response": "", "done": True}

                return stream_generator()
            return {"response": response_text}

        self.client.generate = mock_generate
        self.client.embeddings.return_value = {
            "embedding": [0.1] * 768  # Standard embedding dimension
        }

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        return self._available

    def has_gpu(self) -> bool:
        """Check if GPU is available."""
        return self._has_gpu if self._available else False

    def generate_embedding(self, text: str, use_cache: bool = True) -> list[float] | None:
        """Generate mock embedding for text."""
        if not self._available:
            return None

        # Return consistent mock embedding (use hash for some variation)
        base_value = (hash(text) % 100) / 1000
        return [base_value + (i / 1000) for i in range(768)]

    def semantic_search(
        self, query: str, documents: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Mock semantic search - returns first top_k documents with mock scores."""
        if not self._available:
            return []

        results = []
        for i, doc in enumerate(documents[:top_k]):
            doc_with_score = {**doc, "score": 0.9 - (i * 0.1)}
            results.append(doc_with_score)
        return results

    def semantic_search_with_precomputed_embeddings(
        self, query: str, documents_with_embeddings: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Mock semantic search with precomputed embeddings."""
        if not self._available:
            return []

        results = []
        for i, doc in enumerate(documents_with_embeddings[:top_k]):
            doc_with_score = {**doc, "score": 0.95 - (i * 0.05)}
            results.append(doc_with_score)
        return results

    def ask_question(
        self,
        question: str,
        context_documents: list[dict[str, Any]],
        allow_general_knowledge: bool = True,
    ) -> str | None:
        """Mock Q&A response."""
        if not self._available:
            return None

        doc_titles = [d.get("title", "Untitled") for d in context_documents[:3]]
        return f"Based on the knowledge base ({', '.join(doc_titles)}), here is a mock answer to: {question}"

    def summarize_article(self, content: str) -> str | None:
        """Mock article summarization."""
        if not self._available:
            return None

        preview = content[:100] + "..." if len(content) > 100 else content
        return f"This is a mock summary of the article: {preview}"

    def warmup(self, context: str = "chat") -> tuple[bool, str]:
        """Mock model warmup."""
        if not self._available:
            return False, ""
        # Return the appropriate model name based on context
        if context == "structured":
            model = self.structured_model
        elif context == "embedding":
            model = self.embed_model
        else:
            model = self.chat_model
        return True, model

    def clear_cache(self) -> int:
        """Clear embedding cache."""
        count = len(self.embedding_cache)
        self.embedding_cache.clear()
        return count

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity (copied from real client)."""
        if len(vec1) != len(vec2):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        result: float = dot_product / (magnitude1 * magnitude2)
        return result


class MockNotesService:
    """Mock NotesService for testing without Neo4j."""

    def __init__(self) -> None:
        """Initialize with sample notes."""
        self._notes: dict[str, dict[str, Any]] = {
            "test-note-1": {
                "id": "test-note-1",
                "title": "Test Note 1",
                "content": "This is test content for note 1. [[test-note-2]]",
                "tags": ["test", "example"],
                "is_reference": False,
                "created_at": "2024-01-01T00:00:00Z",
                "links": ["test-note-2"],
            },
            "test-note-2": {
                "id": "test-note-2",
                "title": "Test Note 2",
                "content": "This is test content for note 2.",
                "tags": ["test"],
                "is_reference": False,
                "created_at": "2024-01-02T00:00:00Z",
                "links": [],
            },
        }

    def list_notes(
        self,
        is_reference: bool | None = None,
        include_full_content: bool = False,
        include_embedding: bool = False,
        minimal: bool = False,
    ) -> list[dict[str, Any]]:
        """List all notes."""
        notes = list(self._notes.values())
        if is_reference is not None:
            notes = [n for n in notes if n.get("is_reference") == is_reference]

        # Add mock embeddings if requested
        if include_embedding:
            for note in notes:
                # Generate a consistent mock embedding based on note ID
                base_value = (hash(note["id"]) % 100) / 1000
                note["embedding"] = [base_value + (i / 1000) for i in range(768)]

        return notes

    def get_note(self, note_id: str) -> dict[str, Any] | None:
        """Get a single note by ID."""
        return self._notes.get(note_id)

    def create_note(
        self,
        content: str,
        title: str | None = None,
        tags: list[str] | None = None,
        is_reference: bool = False,
    ) -> dict[str, Any]:
        """Create a note."""
        note_id = f"mock-note-{len(self._notes) + 1}"
        note = {
            "id": note_id,
            "title": title or "Untitled",
            "content": content,
            "tags": tags or [],
            "is_reference": is_reference,
            "created_at": "2024-01-01T00:00:00Z",
            "links": [],
        }
        self._notes[note_id] = note
        return note

    def update_note(
        self,
        note_id: str,
        content: str | None = None,
        title: str | None = None,
        tags: list[str] | None = None,
        is_reference: bool | None = None,
    ) -> dict[str, Any] | None:
        """Update a note."""
        if note_id not in self._notes:
            return None
        note = self._notes[note_id]
        if content is not None:
            note["content"] = content
        if title is not None:
            note["title"] = title
        if tags is not None:
            note["tags"] = tags
        if is_reference is not None:
            note["is_reference"] = is_reference
        return note

    def delete_note(self, note_id: str) -> bool:
        """Delete a note."""
        if note_id in self._notes:
            del self._notes[note_id]
            return True
        return False

    def get_backlinks(self, note_id: str) -> list[dict[str, Any]]:
        """Get notes that link to this note."""
        backlinks = []
        for note in self._notes.values():
            if note_id in note.get("links", []):
                backlinks.append(note)
        return backlinks

    def get_outbound_links(self, note_id: str) -> list[dict[str, Any]]:
        """Get notes this note links to."""
        note = self._notes.get(note_id)
        if not note:
            return []
        return [self._notes[lid] for lid in note.get("links", []) if lid in self._notes]

    def get_random_note(self) -> dict[str, Any] | None:
        """Get a random note."""
        notes = list(self._notes.values())
        return notes[0] if notes else None

    def get_orphan_notes(self) -> list[dict[str, Any]]:
        """Get orphan notes."""
        return []

    def get_dead_end_notes(self) -> list[dict[str, Any]]:
        """Get dead-end notes."""
        return []

    def get_hub_notes(self, min_links: int = 3) -> list[dict[str, Any]]:
        """Get hub notes."""
        return []

    def get_central_notes(self, min_backlinks: int = 3) -> list[dict[str, Any]]:
        """Get central notes."""
        return []

    def get_ai_content(self, note_id: str) -> dict[str, Any] | None:
        """Get pre-computed AI content (mock always returns test data)."""
        if note_id not in self._notes:
            return None
        return {
            "ai_summary": f"Mock summary for {note_id}",
            "ai_summary_at": 1704067200.0,  # 2024-01-01
            "ai_link_suggestions": [
                {"note_id": "test-note-1", "title": "Test Note 1", "confidence": 0.85, "reason": "Mock reason"}
            ],
            "ai_link_suggestions_at": 1704067200.0,
        }

    def regenerate_ai_content(self, note_id: str) -> dict[str, Any] | None:
        """Regenerate AI content (mock returns same as get_ai_content)."""
        return self.get_ai_content(note_id)


# ============================================================================
# Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_ollama_available() -> MockOllamaClient:
    """Get a mock OllamaClient that appears available (CPU-only)."""
    return MockOllamaClient(available=True, has_gpu=False)


@pytest.fixture
def mock_ollama_with_gpu() -> MockOllamaClient:
    """Get a mock OllamaClient that appears available with GPU."""
    return MockOllamaClient(available=True, has_gpu=True)


@pytest.fixture
def mock_ollama_unavailable() -> MockOllamaClient:
    """Get a mock OllamaClient that appears unavailable."""
    return MockOllamaClient(available=False)


@pytest.fixture
def mock_notes_service() -> MockNotesService:
    """Get a mock notes service with test data."""
    return MockNotesService()


# ============================================================================
# Test Client Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clear_resources() -> Generator[None]:
    """Clear user resources before and after each test (static articles remain)."""
    main.user_resources_db.clear()
    yield
    main.user_resources_db.clear()


@pytest.fixture
def client(
    mock_ollama_available: MockOllamaClient,
    mock_notes_service: MockNotesService,
) -> Generator[TestClient]:
    """Get test client with mocked dependencies.

    This is the default fixture for API testing - it uses mocks for
    Ollama and Notes services to ensure fast, deterministic tests
    that don't hit external services.

    For tests that need real services, use `client_real_services` fixture.
    """
    from dependencies import get_notes, get_ollama

    # Override dependencies with mocks
    main.app.dependency_overrides[get_ollama] = lambda: mock_ollama_available
    main.app.dependency_overrides[get_notes] = lambda: mock_notes_service

    with TestClient(main.app) as client:
        yield client

    # Clear overrides
    main.app.dependency_overrides.clear()


@pytest.fixture
def client_real_services() -> Generator[TestClient]:
    """Get test client with real services (no mocks).

    Use this for integration tests that need to hit real Ollama or Neo4j.
    These tests should be marked @slow.
    """
    with TestClient(main.app) as client:
        yield client


@pytest.fixture
def client_with_mock_ollama(
    mock_ollama_available: MockOllamaClient,
) -> Generator[tuple[TestClient, MockOllamaClient]]:
    """Get test client with mocked Ollama client.

    Uses FastAPI dependency_overrides for clean mock injection.
    This enables AI endpoint tests without a running Ollama instance.
    """
    from dependencies import get_ollama

    # Override the dependency
    main.app.dependency_overrides[get_ollama] = lambda: mock_ollama_available

    with TestClient(main.app) as client:
        yield client, mock_ollama_available

    # Clear the override
    main.app.dependency_overrides.clear()


@pytest.fixture
def client_with_unavailable_ollama(
    mock_ollama_unavailable: MockOllamaClient,
) -> Generator[tuple[TestClient, MockOllamaClient]]:
    """Get test client with Ollama appearing unavailable.

    Use this to test graceful degradation when AI is not available.
    """
    from dependencies import get_ollama

    # Override the dependency
    main.app.dependency_overrides[get_ollama] = lambda: mock_ollama_unavailable

    with TestClient(main.app) as client:
        yield client, mock_ollama_unavailable

    # Clear the override
    main.app.dependency_overrides.clear()


@pytest.fixture
def client_with_mocks(
    mock_ollama_available: MockOllamaClient,
    mock_notes_service: MockNotesService,
) -> Generator[TestClient]:
    """Get test client with all dependencies mocked.

    This is the recommended fixture for most tests - it provides
    fast, deterministic behavior without hitting real services.
    """
    from dependencies import get_notes, get_ollama

    # Override all dependencies
    main.app.dependency_overrides[get_ollama] = lambda: mock_ollama_available
    main.app.dependency_overrides[get_notes] = lambda: mock_notes_service

    with TestClient(main.app) as client:
        yield client

    # Clear all overrides
    main.app.dependency_overrides.clear()


@pytest.fixture
def sample_resource() -> dict[str, str | list[str]]:
    """Get sample resource data for testing."""
    return {
        "title": "Test Resource",
        "content": "This is test content",
        "url": "https://example.com",
        "tags": ["test", "example"],
    }
