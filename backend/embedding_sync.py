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

from utils import calculate_content_hash

logger = logging.getLogger(__name__)

# Embedding version - increment when model or logic changes
EMBEDDING_VERSION = 1


def sync_articles_to_neo4j(
    articles: list[dict[str, Any]],
    neo4j_adapter: Any,
) -> tuple[int, int]:
    """Sync static articles to Neo4j.

    Creates or updates Article nodes based on content_hash.

    Args:
        articles: List of article dicts from article_loader
        neo4j_adapter: Neo4jAdapter instance

    Returns:
        Tuple of (created_count, updated_count)
    """
    if not neo4j_adapter.is_available():
        logger.warning("Neo4j not available - skipping article sync")
        return (0, 0)

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

    logger.info("Article sync complete: %d created, %d updated", created, updated)
    return (created, updated)


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
        logger.debug("Model changed for %s: %s -> %s",
                    node["id"], node.get("embedding_model"), current_model)
        return True

    # Version changed (logic update)
    if node.get("embedding_version", 0) < current_version:
        logger.debug("Version outdated for %s: %d < %d",
                    node["id"], node.get("embedding_version", 0), current_version)
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
    """
    logger.info("Checking %ss for missing embeddings...", node_type.lower())

    for idx, node in enumerate(nodes, 1):
        node_id = node["id"]
        content = node.get("content", "")
        title = node.get("title", node_id)[:50]

        if needs_embedding_regeneration(node, current_model, current_version, content):
            start_time = time.time()
            logger.info("  [%d/%d] Generating embedding for %s: %s",
                       idx, len(nodes), node_type.lower(), title)

            embedding = ollama_client.generate_embedding(content, use_cache=True)

            if embedding:
                neo4j_adapter.store_embedding(
                    node_type, node_id, embedding, current_model, current_version
                )
                duration = time.time() - start_time
                logger.info("  [%d/%d] ✓ Embedding generated in %.1fs: %s",
                           idx, len(nodes), duration, title)
                stats["embeddings_generated"] += 1
                stats[f"{stat_key}_processed"] += 1
            else:
                logger.error("  [%d/%d] ✗ Failed to generate embedding for: %s",
                            idx, len(nodes), title)
        else:
            logger.debug("  [%d/%d] %s has valid embedding: %s",
                        idx, len(nodes), node_type, node_id)
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
        }
    """
    if not neo4j_adapter.is_available():
        logger.warning("Neo4j not available - skipping embedding sync")
        return {"articles_processed": 0, "notes_processed": 0,
                "embeddings_generated": 0, "embeddings_cached": 0}

    if not ollama_client.is_available():
        logger.warning("Ollama not available - skipping embedding sync")
        return {"articles_processed": 0, "notes_processed": 0,
                "embeddings_generated": 0, "embeddings_cached": 0}

    current_model = ollama_client.model
    current_version = EMBEDDING_VERSION

    stats = {
        "articles_processed": 0,
        "notes_processed": 0,
        "embeddings_generated": 0,
        "embeddings_cached": 0,
    }

    # Process Articles
    articles = neo4j_adapter.get_all_articles()
    _process_embeddings_for_nodes(
        articles, "Article", "articles",
        current_model, current_version,
        neo4j_adapter, ollama_client, stats
    )

    # Process Notes
    notes = neo4j_adapter.get_all_notes()
    _process_embeddings_for_nodes(
        notes, "Note", "notes",
        current_model, current_version,
        neo4j_adapter, ollama_client, stats
    )

    logger.info("Embedding sync complete: %d generated, %d cached",
                stats["embeddings_generated"], stats["embeddings_cached"])

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
    created, updated = sync_articles_to_neo4j(articles, neo4j_adapter)
    logger.info("Articles synced: %d created, %d updated", created, updated)

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
