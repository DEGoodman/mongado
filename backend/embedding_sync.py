"""Embedding synchronization service for Articles and Notes.

This service:
1. Syncs static articles to Neo4j on startup
2. Detects which articles/notes need embeddings
3. Generates and stores embeddings
4. Provides progress logging

Usage:
    from embedding_sync import sync_embeddings_on_startup

    # Call during app startup
    sync_embeddings_on_startup(articles, ollama_client, neo4j_adapter)
"""

import logging
import time
from typing import Any

from core.ai import mean_vector
from core.chunking import chunk_document
from utils import calculate_content_hash

logger = logging.getLogger(__name__)

# Embedding version - increment when model or logic changes
# v2: chunked embeddings with title prefix (#192)
EMBEDDING_VERSION = 2

# Retry-with-backoff settings for rate-limited embedding APIs (e.g. Gemini 429s).
# The whole sync shares one time budget; per-item retries back off exponentially.
SYNC_TIME_BUDGET_SECONDS = 600.0
RETRY_BASE_DELAY_SECONDS = 2.0
RETRY_MAX_DELAY_SECONDS = 60.0


def _generate_with_retry(
    ollama_client: Any,
    content: str,
    deadline: float,
) -> list[float] | None:
    """Generate an embedding, retrying with exponential backoff until deadline.

    Embedding APIs enforce per-minute rate limits (429s), so waiting and
    retrying usually succeeds. Retries stop once the next wait would pass
    the shared sync deadline; the item is then reported as failed.

    Args:
        ollama_client: Client with generate_embedding()
        content: Text to embed
        deadline: time.monotonic() timestamp after which no more retries

    Returns:
        Embedding vector, or None if all attempts failed
    """
    delay = RETRY_BASE_DELAY_SECONDS
    attempt = 1
    while True:
        embedding: list[float] | None = ollama_client.generate_embedding(content, use_cache=True)
        if embedding:
            return embedding
        if time.monotonic() + delay > deadline:
            return None
        logger.warning("  Embedding attempt %d failed, retrying in %.0fs", attempt, delay)
        time.sleep(delay)
        delay = min(delay * 2, RETRY_MAX_DELAY_SECONDS)
        attempt += 1


def sync_articles_to_neo4j(
    articles: list[dict[str, Any]],
    neo4j_adapter: Any,
) -> tuple[int, int, int]:
    """Sync static articles to Neo4j.

    Creates or updates Article nodes based on content_hash, then deletes
    stale nodes for articles that no longer exist in the static set (#215).

    Args:
        articles: List of article dicts from article_loader
        neo4j_adapter: Neo4jAdapter instance

    Returns:
        Tuple of (created_count, updated_count, deleted_count)
    """
    if not neo4j_adapter.is_available():
        logger.warning("Neo4j not available - skipping article sync")
        return (0, 0, 0)

    created = 0
    updated = 0

    logger.info("Syncing %d articles to Neo4j...", len(articles))

    for article in articles:
        article_id = str(article["id"])
        title = article.get("title", "Untitled")
        content = article.get("content", "")
        content_hash = calculate_content_hash(content)
        created_at = article.get("created_at", time.time())
        updated_at = article.get("updated_at", created_at)

        # Check if article exists and has same content
        existing = neo4j_adapter.get_article(article_id)

        if existing:
            if existing.get("content_hash") != content_hash:
                # Content changed - update article
                neo4j_adapter.upsert_article(
                    article_id, title, content, content_hash, created_at, updated_at
                )
                updated += 1
                logger.debug("Updated article: %s (content changed)", article_id)
            else:
                logger.debug("Article unchanged: %s", article_id)
        else:
            # New article - create it
            neo4j_adapter.upsert_article(
                article_id, title, content, content_hash, created_at, updated_at
            )
            created += 1
            logger.debug("Created article: %s", article_id)

    # Static articles are the source of truth: drop nodes for renamed or
    # removed articles. Skip when the loader returned nothing - an empty
    # list more likely means a load failure than an emptied corpus.
    deleted_ids: list[str] = []
    if articles:
        deleted_ids = neo4j_adapter.delete_articles_not_in(
            [str(article["id"]) for article in articles]
        )
        if deleted_ids:
            logger.info(
                "Deleted %d stale article node(s): %s", len(deleted_ids), ", ".join(deleted_ids)
            )

    logger.info(
        "Article sync complete: %d created, %d updated, %d deleted",
        created,
        updated,
        len(deleted_ids),
    )
    return (created, updated, len(deleted_ids))


def needs_embedding_regeneration(
    node: dict[str, Any],
    current_model: str,
    current_version: int,
    content: str,
) -> bool:
    """Check if a node needs its embedding regenerated.

    Args:
        node: Article or Note dict from Neo4j
        current_model: Current embedding model name
        current_version: Current embedding version
        content: Current content (for hash comparison)

    Returns:
        True if embedding needs regeneration
    """
    # No embedding exists
    if not node.get("embedding"):
        return True

    # Model changed
    if node.get("embedding_model") != current_model:
        logger.debug(
            "Model changed for %s: %s -> %s", node["id"], node.get("embedding_model"), current_model
        )
        return True

    # Version changed (logic update)
    if node.get("embedding_version", 0) < current_version:
        logger.debug(
            "Version outdated for %s: %d < %d",
            node["id"],
            node.get("embedding_version", 0),
            current_version,
        )
        return True

    # Content changed
    current_hash = calculate_content_hash(content)
    if node.get("content_hash") != current_hash:
        logger.debug("Content changed for %s", node["id"])
        return True

    return False


def _process_embeddings_for_nodes(
    nodes: list[dict[str, Any]],
    node_type: str,
    stat_key: str,
    current_model: str,
    current_version: int,
    neo4j_adapter: Any,
    ollama_client: Any,
    stats: dict[str, int],
    deadline: float,
) -> None:
    """Process embeddings for a list of nodes (Articles or Notes).

    This unified function eliminates code duplication between article and note processing.

    Args:
        nodes: List of node dicts from Neo4j
        node_type: "Article" or "Note" (for Neo4j label)
        stat_key: Stats key prefix ("articles" or "notes")
        current_model: Current embedding model name
        current_version: Current embedding version
        neo4j_adapter: Neo4jAdapter instance
        ollama_client: OllamaClient instance
        stats: Stats dict to update (modified in place)
        deadline: time.monotonic() timestamp bounding retry waits
    """
    logger.info("Checking %ss for missing embeddings...", node_type.lower())

    for idx, node in enumerate(nodes, 1):
        node_id = node["id"]
        content = node.get("content", "")
        title = node.get("title", node_id)[:50]

        if needs_embedding_regeneration(node, current_model, current_version, content):
            start_time = time.time()

            # Chunk the document (title prefixed to each chunk, #192)
            chunks = chunk_document(node.get("title") or "", content)
            logger.info(
                "  [%d/%d] Generating %d chunk embedding(s) for %s: %s",
                idx,
                len(nodes),
                len(chunks),
                node_type.lower(),
                title,
            )

            chunk_embeddings: list[list[float]] = []
            for chunk in chunks:
                embedding = _generate_with_retry(ollama_client, chunk, deadline)
                if embedding is None:
                    break
                chunk_embeddings.append(embedding)

            if chunks and len(chunk_embeddings) == len(chunks):
                # Chunks first, node embedding last: the node's metadata is
                # what needs_embedding_regeneration checks, so a partial write
                # is retried on the next sync.
                neo4j_adapter.replace_chunk_embeddings(
                    node_type, node_id, chunk_embeddings, current_model, current_version
                )
                # Whole-document embedding (used by related-notes/suggest-links)
                # is the mean of chunk embeddings - no extra API calls
                neo4j_adapter.store_embedding(
                    node_type,
                    node_id,
                    mean_vector(chunk_embeddings),
                    current_model,
                    current_version,
                    calculate_content_hash(content),
                )
                duration = time.time() - start_time
                logger.info(
                    "  [%d/%d] ✓ %d embedding(s) generated in %.1fs: %s",
                    idx,
                    len(nodes),
                    len(chunk_embeddings),
                    duration,
                    title,
                )
                stats["embeddings_generated"] += 1
                stats[f"{stat_key}_processed"] += 1
            else:
                logger.error(
                    "  [%d/%d] ✗ Failed to generate embedding for: %s", idx, len(nodes), title
                )
                stats["embeddings_failed"] += 1
        else:
            logger.debug(
                "  [%d/%d] %s has valid embedding: %s", idx, len(nodes), node_type, node_id
            )
            stats["embeddings_cached"] += 1
            stats[f"{stat_key}_processed"] += 1


def sync_embeddings(
    neo4j_adapter: Any,
    ollama_client: Any,
) -> dict[str, int]:
    """Generate and store missing embeddings for articles and notes.

    Args:
        neo4j_adapter: Neo4jAdapter instance
        ollama_client: OllamaClient instance

    Returns:
        Dict with counts: {
            "articles_processed": int,
            "notes_processed": int,
            "embeddings_generated": int,
            "embeddings_cached": int,
            "embeddings_failed": int,
        }
    """
    stats = {
        "articles_processed": 0,
        "notes_processed": 0,
        "embeddings_generated": 0,
        "embeddings_cached": 0,
        "embeddings_failed": 0,
    }

    if not neo4j_adapter.is_available():
        logger.warning("Neo4j not available - skipping embedding sync")
        return stats

    if not ollama_client.embeddings_available():
        logger.warning("Ollama not available - skipping embedding sync")
        return stats

    current_model = ollama_client.model
    current_version = EMBEDDING_VERSION
    deadline = time.monotonic() + SYNC_TIME_BUDGET_SECONDS

    # Process Articles (with embedding metadata so staleness checks can skip fresh ones)
    articles = neo4j_adapter.get_all_articles(include_embeddings=True)
    _process_embeddings_for_nodes(
        articles,
        "Article",
        "articles",
        current_model,
        current_version,
        neo4j_adapter,
        ollama_client,
        stats,
        deadline,
    )

    # Process Notes (with embedding metadata so staleness checks can skip fresh ones)
    notes = neo4j_adapter.get_all_notes(include_embeddings=True)
    _process_embeddings_for_nodes(
        notes,
        "Note",
        "notes",
        current_model,
        current_version,
        neo4j_adapter,
        ollama_client,
        stats,
        deadline,
    )

    logger.info(
        "Embedding sync complete: %d generated, %d cached, %d failed",
        stats["embeddings_generated"],
        stats["embeddings_cached"],
        stats["embeddings_failed"],
    )

    return stats


def sync_embeddings_on_startup(
    articles: list[dict[str, Any]],
    ollama_client: Any,
    neo4j_adapter: Any,
) -> None:
    """Full embedding sync on app startup.

    This is the main entry point called from main.py startup.

    Args:
        articles: List of static articles from article_loader
        ollama_client: OllamaClient instance
        neo4j_adapter: Neo4jAdapter instance
    """
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("Starting embedding sync on startup...")
    logger.info("=" * 60)

    # Step 1: Sync articles to Neo4j
    created, updated, deleted = sync_articles_to_neo4j(articles, neo4j_adapter)
    logger.info("Articles synced: %d created, %d updated, %d deleted", created, updated, deleted)

    # Step 2: Generate missing embeddings
    stats = sync_embeddings(neo4j_adapter, ollama_client)

    duration = time.time() - start_time
    logger.info("=" * 60)
    logger.info("Embedding sync complete in %.1fs", duration)
    logger.info("  Articles: %d processed", stats["articles_processed"])
    logger.info("  Notes: %d processed", stats["notes_processed"])
    logger.info("  Embeddings generated: %d", stats["embeddings_generated"])
    logger.info("  Embeddings cached: %d", stats["embeddings_cached"])
    logger.info("=" * 60)
