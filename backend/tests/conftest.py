"""Pytest configuration and fixtures."""

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

# Set TESTING environment variable BEFORE any imports
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def clear_resources() -> Generator[None]:
    """Clear user resources before and after each test (static articles remain)."""
    main.user_resources_db.clear()
    yield
    main.user_resources_db.clear()


@pytest.fixture
def client() -> Generator[TestClient]:
    """Get test client for API testing with lifespan context."""
    with TestClient(main.app) as client:
        yield client


@pytest.fixture
def sample_resource() -> dict[str, str | list[str]]:
    """Get sample resource data for testing."""
    return {
        "title": "Test Resource",
        "content": "This is test content",
        "url": "https://example.com",
        "tags": ["test", "example"],
    }


# ============================================================================
# Ollama Mock Fixtures for AI Endpoint Testing
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
        self.client.generate.return_value = {
            "response": "This is a mock AI response for testing purposes."
        }
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

    def warmup(self) -> bool:
        """Mock model warmup."""
        return self._available

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
def client_with_mock_ollama(
    mock_ollama_available: MockOllamaClient,
) -> Generator[tuple[TestClient, MockOllamaClient]]:
    """Get test client with mocked Ollama client.

    This fixture patches the global ollama_client in main.py to use
    the mock, enabling AI endpoint tests without a running Ollama instance.
    """
    # Store original
    original_client = main.ollama_client

    # Replace with mock
    main.ollama_client = mock_ollama_available  # type: ignore[assignment]

    with TestClient(main.app) as client:
        yield client, mock_ollama_available

    # Restore original
    main.ollama_client = original_client


@pytest.fixture
def client_with_unavailable_ollama(
    mock_ollama_unavailable: MockOllamaClient,
) -> Generator[tuple[TestClient, MockOllamaClient]]:
    """Get test client with Ollama appearing unavailable.

    Use this to test graceful degradation when AI is not available.
    """
    original_client = main.ollama_client
    main.ollama_client = mock_ollama_unavailable  # type: ignore[assignment]

    with TestClient(main.app) as client:
        yield client, mock_ollama_unavailable

    main.ollama_client = original_client
