"""Unit tests for embedding_sync: staleness detection, retry, and stats.

Regression tests for the bug where every sync regenerated all embeddings
(nodes fetched without embedding metadata + content_hash never persisted),
hammering the embedding API with burst requests (Gemini 429s).
"""

import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from embedding_sync import (
    EMBEDDING_VERSION,
    _generate_with_retry,
    _process_embeddings_for_nodes,
    needs_embedding_regeneration,
    sync_articles_to_neo4j,
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


class TestChunkedEmbeddings:
    """Chunked embedding generation (#192)."""

    def _stats(self) -> dict[str, int]:
        return {
            "articles_processed": 0,
            "notes_processed": 0,
            "embeddings_generated": 0,
            "embeddings_cached": 0,
            "embeddings_failed": 0,
        }

    def _long_node(self) -> dict[str, Any]:
        """A stale node whose content splits into two chunks."""
        content = "## Alpha\n\n" + ("a" * 1600) + "\n\n## Beta\n\n" + ("b" * 1600)
        return {"id": "1", "title": "Long Article", "content": content}

    def test_multi_chunk_node_stores_chunks_and_mean_embedding(self) -> None:
        neo4j = MagicMock()
        client = MagicMock()
        client.generate_embedding.side_effect = [[0.1, 0.3], [0.3, 0.5]]
        stats = self._stats()
        node = self._long_node()

        _process_embeddings_for_nodes(
            [node],
            "Article",
            "articles",
            MODEL,
            EMBEDDING_VERSION,
            neo4j,
            client,
            stats,
            deadline=time.monotonic() + 600,
        )

        # Two chunks embedded, both stored
        assert client.generate_embedding.call_count == 2
        neo4j.replace_chunk_embeddings.assert_called_once_with(
            "Article", "1", [[0.1, 0.3], [0.3, 0.5]], MODEL, EMBEDDING_VERSION
        )
        # Whole-document embedding is the mean of the chunk embeddings
        args = neo4j.store_embedding.call_args[0]
        assert args[0] == "Article"
        assert args[1] == "1"
        assert args[2] == pytest.approx([0.2, 0.4])
        assert args[3] == MODEL
        assert args[4] == EMBEDDING_VERSION
        assert args[5] == calculate_content_hash(node["content"])
        assert stats["embeddings_generated"] == 1

    def test_chunk_text_includes_title(self) -> None:
        neo4j = MagicMock()
        client = MagicMock()
        client.generate_embedding.return_value = [0.1]
        stats = self._stats()
        node = {"id": "n1", "title": "Rocks and Barnacles", "content": "Short content."}

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

        embedded_text = client.generate_embedding.call_args[0][0]
        assert embedded_text.startswith("Rocks and Barnacles\n\n")
        assert "Short content." in embedded_text

    def test_partial_chunk_failure_stores_nothing(self) -> None:
        """If any chunk fails, neither chunks nor the node embedding are written."""
        neo4j = MagicMock()
        client = MagicMock()
        client.generate_embedding.side_effect = [[0.1, 0.3], None]
        stats = self._stats()

        _process_embeddings_for_nodes(
            [self._long_node()],
            "Article",
            "articles",
            MODEL,
            EMBEDDING_VERSION,
            neo4j,
            client,
            stats,
            deadline=time.monotonic() - 1,  # no retries
        )

        neo4j.replace_chunk_embeddings.assert_not_called()
        neo4j.store_embedding.assert_not_called()
        assert stats["embeddings_failed"] == 1


class TestSyncArticlesToNeo4j:
    """Tests for sync_articles_to_neo4j, especially stale-node cleanup (#215)."""

    def _articles(self) -> list[dict[str, Any]]:
        return [
            {"id": 1, "title": "One", "content": "first article"},
            {"id": 2, "title": "Two", "content": "second article"},
        ]

    def test_deletes_stale_articles_after_upsert(self) -> None:
        neo4j = MagicMock()
        neo4j.is_available.return_value = True
        neo4j.get_article.return_value = None
        neo4j.delete_articles_not_in.return_value = ["7", "9"]

        created, updated, deleted = sync_articles_to_neo4j(self._articles(), neo4j)

        neo4j.delete_articles_not_in.assert_called_once_with(["1", "2"])
        assert (created, updated, deleted) == (2, 0, 2)

    def test_no_deletion_when_article_list_empty(self) -> None:
        """An empty static set means a load failure, not an emptied corpus."""
        neo4j = MagicMock()
        neo4j.is_available.return_value = True

        created, updated, deleted = sync_articles_to_neo4j([], neo4j)

        neo4j.delete_articles_not_in.assert_not_called()
        assert (created, updated, deleted) == (0, 0, 0)

    def test_unavailable_neo4j_skips_everything(self) -> None:
        neo4j = MagicMock()
        neo4j.is_available.return_value = False

        assert sync_articles_to_neo4j(self._articles(), neo4j) == (0, 0, 0)
        neo4j.delete_articles_not_in.assert_not_called()

    def test_unchanged_articles_not_reupserted(self) -> None:
        neo4j = MagicMock()
        neo4j.is_available.return_value = True
        neo4j.delete_articles_not_in.return_value = []
        articles = self._articles()
        neo4j.get_article.side_effect = lambda article_id: {
            "id": article_id,
            "content_hash": calculate_content_hash(
                next(a["content"] for a in articles if str(a["id"]) == article_id)
            ),
        }

        created, updated, deleted = sync_articles_to_neo4j(articles, neo4j)

        neo4j.upsert_article.assert_not_called()
        assert (created, updated, deleted) == (0, 0, 0)


class TestOrphanedChunkCleanup:
    """Tests for the orphaned-chunk sweep in sync_embeddings (#244)."""

    def test_orphans_deleted_and_counted(self) -> None:
        neo4j = MagicMock()
        neo4j.is_available.return_value = True
        neo4j.delete_orphaned_chunks.return_value = 100
        neo4j.get_all_articles.return_value = []
        neo4j.get_all_notes.return_value = []
        client = MagicMock()
        client.embeddings_available.return_value = True
        client.model = MODEL

        stats = sync_embeddings(neo4j, client)

        neo4j.delete_orphaned_chunks.assert_called_once()
        assert stats["orphaned_chunks_deleted"] == 100

    def test_sweep_runs_even_without_embedding_backend(self) -> None:
        """Cleanup is pure Neo4j work - no reason to skip it when Ollama is down."""
        neo4j = MagicMock()
        neo4j.is_available.return_value = True
        neo4j.delete_orphaned_chunks.return_value = 7
        client = MagicMock()
        client.embeddings_available.return_value = False

        stats = sync_embeddings(neo4j, client)

        neo4j.delete_orphaned_chunks.assert_called_once()
        assert stats["orphaned_chunks_deleted"] == 7
        assert stats["embeddings_generated"] == 0

    def test_sweep_skipped_when_neo4j_unavailable(self) -> None:
        neo4j = MagicMock()
        neo4j.is_available.return_value = False
        client = MagicMock()

        stats = sync_embeddings(neo4j, client)

        neo4j.delete_orphaned_chunks.assert_not_called()
        assert stats["orphaned_chunks_deleted"] == 0
