"""Unit tests for embedding_sync: staleness detection, retry, and stats.

Regression tests for the bug where every sync regenerated all embeddings
(nodes fetched without embedding metadata + content_hash never persisted),
hammering the embedding API with burst requests (Gemini 429s).
"""

import time
from typing import Any
from unittest.mock import MagicMock, patch

from embedding_sync import (
    EMBEDDING_VERSION,
    _generate_with_retry,
    _process_embeddings_for_nodes,
    needs_embedding_regeneration,
    sync_embeddings,
)
from utils import calculate_content_hash

MODEL = "gemini-embedding-001"


def _fresh_node(content: str = "hello world") -> dict[str, Any]:
    """A node whose embedding is up to date (should be skipped)."""
    return {
        "id": "curious-elephant",
        "title": "Test",
        "content": content,
        "embedding": [0.1, 0.2],
        "embedding_model": MODEL,
        "embedding_version": EMBEDDING_VERSION,
        "content_hash": calculate_content_hash(content),
    }


class TestNeedsEmbeddingRegeneration:
    def test_fresh_node_is_skipped(self) -> None:
        node = _fresh_node()
        assert not needs_embedding_regeneration(node, MODEL, EMBEDDING_VERSION, node["content"])

    def test_missing_embedding_regenerates(self) -> None:
        node = _fresh_node()
        del node["embedding"]
        assert needs_embedding_regeneration(node, MODEL, EMBEDDING_VERSION, node["content"])

    def test_model_change_regenerates(self) -> None:
        node = _fresh_node()
        assert needs_embedding_regeneration(node, "other-model", EMBEDDING_VERSION, node["content"])

    def test_content_change_regenerates(self) -> None:
        node = _fresh_node()
        assert needs_embedding_regeneration(node, MODEL, EMBEDDING_VERSION, "edited content")


class TestGenerateWithRetry:
    def test_returns_immediately_on_success(self) -> None:
        client = MagicMock()
        client.generate_embedding.return_value = [0.1]
        result = _generate_with_retry(client, "text", deadline=time.monotonic() + 600)
        assert result == [0.1]
        assert client.generate_embedding.call_count == 1

    def test_retries_after_failure(self) -> None:
        client = MagicMock()
        client.generate_embedding.side_effect = [None, None, [0.5]]
        with patch("embedding_sync.time.sleep") as mock_sleep:
            result = _generate_with_retry(client, "text", deadline=time.monotonic() + 600)
        assert result == [0.5]
        assert client.generate_embedding.call_count == 3
        # Exponential backoff: 2s then 4s
        assert [c.args[0] for c in mock_sleep.call_args_list] == [2.0, 4.0]

    def test_gives_up_at_deadline(self) -> None:
        client = MagicMock()
        client.generate_embedding.return_value = None
        # Deadline already passed: one attempt, no sleeps
        with patch("embedding_sync.time.sleep") as mock_sleep:
            result = _generate_with_retry(client, "text", deadline=time.monotonic() - 1)
        assert result is None
        assert client.generate_embedding.call_count == 1
        mock_sleep.assert_not_called()


class TestProcessEmbeddingsForNodes:
    def _stats(self) -> dict[str, int]:
        return {
            "articles_processed": 0,
            "notes_processed": 0,
            "embeddings_generated": 0,
            "embeddings_cached": 0,
            "embeddings_failed": 0,
        }

    def test_fresh_node_counts_as_cached_without_api_call(self) -> None:
        neo4j = MagicMock()
        client = MagicMock()
        stats = self._stats()

        _process_embeddings_for_nodes(
            [_fresh_node()],
            "Note",
            "notes",
            MODEL,
            EMBEDDING_VERSION,
            neo4j,
            client,
            stats,
            deadline=time.monotonic() + 600,
        )

        client.generate_embedding.assert_not_called()
        neo4j.store_embedding.assert_not_called()
        assert stats["embeddings_cached"] == 1
        assert stats["notes_processed"] == 1

    def test_stale_node_stores_embedding_with_content_hash(self) -> None:
        neo4j = MagicMock()
        client = MagicMock()
        client.generate_embedding.return_value = [0.1]
        stats = self._stats()
        node = _fresh_node()
        del node["content_hash"]  # simulates pre-fix nodes

        _process_embeddings_for_nodes(
            [node],
            "Note",
            "notes",
            MODEL,
            EMBEDDING_VERSION,
            neo4j,
            client,
            stats,
            deadline=time.monotonic() + 600,
        )

        neo4j.store_embedding.assert_called_once_with(
            "Note",
            node["id"],
            [0.1],
            MODEL,
            EMBEDDING_VERSION,
            calculate_content_hash(node["content"]),
        )
        assert stats["embeddings_generated"] == 1

    def test_failed_generation_counts_as_failed(self) -> None:
        neo4j = MagicMock()
        client = MagicMock()
        client.generate_embedding.return_value = None
        stats = self._stats()
        node = _fresh_node()
        del node["embedding"]

        _process_embeddings_for_nodes(
            [node],
            "Note",
            "notes",
            MODEL,
            EMBEDDING_VERSION,
            neo4j,
            client,
            stats,
            deadline=time.monotonic() - 1,  # no retries
        )

        neo4j.store_embedding.assert_not_called()
        assert stats["embeddings_failed"] == 1
        assert stats["notes_processed"] == 0


class TestSyncEmbeddings:
    def test_fetches_nodes_with_embedding_metadata(self) -> None:
        """Regression: fetching without embeddings made every sync regenerate everything."""
        neo4j = MagicMock()
        neo4j.is_available.return_value = True
        neo4j.get_all_articles.return_value = []
        neo4j.get_all_notes.return_value = [_fresh_node()]
        client = MagicMock()
        client.embeddings_available.return_value = True
        client.model = MODEL

        stats = sync_embeddings(neo4j, client)

        neo4j.get_all_articles.assert_called_once_with(include_embeddings=True)
        neo4j.get_all_notes.assert_called_once_with(include_embeddings=True)
        client.generate_embedding.assert_not_called()
        assert stats["embeddings_cached"] == 1
        assert stats["embeddings_failed"] == 0
