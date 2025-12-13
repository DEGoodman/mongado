"""Search and Q&A API routes.

Uses FastAPI dependency injection for testability. Dependencies can be
overridden in tests using app.dependency_overrides.
"""

import logging
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from rapidfuzz import fuzz

from core.search import extract_snippet
from dependencies import get_neo4j, get_notes, get_ollama, get_static_articles, get_user_resources
from models import SearchRequest, SearchResponse, SearchResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])

# Type aliases for cleaner signatures
OllamaDep = Annotated[Any, Depends(get_ollama)]
NotesDep = Annotated[Any, Depends(get_notes)]
Neo4jDep = Annotated[Any, Depends(get_neo4j)]
ArticlesDep = Annotated[list[dict[str, Any]], Depends(get_static_articles)]
UserResourcesDep = Annotated[list[dict[str, Any]], Depends(get_user_resources)]


def _fuzzy_match_text(query: str, text: str, threshold: int = 80) -> float:
    """
    Check if query fuzzy matches the text and return relevance score.

    - Queries < 3 chars: exact substring match only (for terms like "SRE")
    - Queries >= 3 chars: fuzzy match with 80% threshold (handles typos)

    Args:
        query: Search query (lowercase)
        text: Text to search in (lowercase)
        threshold: Minimum similarity score (0-100)

    Returns:
        Relevance score (0.0 = no match, 1.0 = fuzzy match, 2.0 = exact match)
    """
    # Short queries: require exact match (prevents false positives)
    if len(query) < 3:
        return 2.0 if query in text else 0.0

    # Exact match (highest score)
    if query in text:
        return 2.0

    # Fuzzy match: check if query is similar to any word in text
    # Only match against words of similar length to avoid false positives
    words = text.split()
    best_score = 0.0
    for word in words:
        # Only fuzzy match words that are within 2 chars of query length
        if abs(len(word) - len(query)) <= 2:
            similarity = fuzz.ratio(query, word)
            if similarity >= threshold:
                # Map 80-100 similarity to 0.8-1.0 score
                best_score = max(best_score, similarity / 100.0)

    return best_score


def _get_all_resources(
    static_articles: list[dict[str, Any]],
    user_resources: list[dict[str, Any]],
    notes_service: Any,
) -> list[dict[str, Any]]:
    """Get all searchable resources (articles + notes).

    Notes are normalized to have 'note_id' field to distinguish from articles.
    """
    all_notes = notes_service.list_notes()

    # Normalize note structure to match article structure for search
    normalized_notes = []
    for note in all_notes:
        normalized_note = {
            "note_id": note.get("id"),  # Keep string ID as note_id
            "title": note.get("title", "Untitled"),
            "content": note.get("content", ""),
            "tags": note.get("tags", []),
            "created_at": note.get("created_at"),
        }
        normalized_notes.append(normalized_note)

    return static_articles + user_resources + normalized_notes


def _normalize_search_result(doc: dict[str, Any], query: str, score: float = 1.0) -> SearchResult:
    """Normalize a resource document into a consistent SearchResult.

    Args:
        doc: The document dictionary with title, content, etc.
        query: The search query (used to generate contextual snippet)
        score: The relevance score
    """
    # Determine if this is an article or note
    is_note = "note_id" in doc
    resource_type = "note" if is_note else "article"
    resource_id: str | int = str(doc.get("note_id") if is_note else doc.get("id", ""))

    content = doc.get("content", "")
    snippet = extract_snippet(content, query)

    return SearchResult(
        id=resource_id,
        type=resource_type,
        title=doc.get("title", "Untitled"),
        content=content,
        snippet=snippet,
        score=score,
    )


@router.post("/search", response_model=SearchResponse)
def search_resources(
    request: SearchRequest,
    static_articles: ArticlesDep,
    user_resources: UserResourcesDep,
    notes_service: NotesDep,
    ollama: OllamaDep,
    neo4j: Neo4jDep,
) -> SearchResponse:
    """
    Search across all resources (articles + notes).

    **Default:** Fast text search with fuzzy matching (instant)
    - Queries < 3 chars: exact match only (e.g., "SRE")
    - Queries >= 3 chars: fuzzy match with 80% threshold (handles typos like "biling" → "billing")

    **Semantic mode:** AI-powered semantic search via Ollama (slower, opt-in)
    - Set semantic=true to use AI embeddings for semantic search
    - Finds conceptually related content even without keyword matches
    - Takes 15-30+ seconds depending on corpus size

    The default text search is instant and works even when Ollama is unavailable
    or slow, making it ideal for the main search UI.
    """
    start_time = time.time()

    logger.info(
        "Search request received: query=%s, semantic=%s, limit=%s",
        request.query,
        request.semantic,
        request.top_k,
    )
    # Get current state dynamically (not captured at router creation time)
    all_resources = _get_all_resources(static_articles, user_resources, notes_service)

    # Default: Fast text search with fuzzy matching
    if not request.semantic:
        logger.debug("Using fast text search with fuzzy matching")
        query_lower = request.query.lower()

        # Score each document based on title and content matches
        scored_docs = []
        for doc in all_resources:
            title_score = _fuzzy_match_text(query_lower, doc.get("title", "").lower())
            content_score = _fuzzy_match_text(query_lower, doc.get("content", "").lower())

            # Title matches are weighted higher (2x)
            total_score = (title_score * 2.0) + content_score

            if total_score > 0:
                # Debug: Check for None IDs before adding
                is_note = "note_id" in doc
                resource_id = doc.get("note_id") if is_note else doc.get("id")
                if resource_id is None:
                    logger.error(
                        "Found resource with None ID! Query=%s, Title=%s, Type=%s, Keys=%s",
                        query_lower,
                        doc.get("title", "Unknown"),
                        "note" if is_note else "article",
                        list(doc.keys()),
                    )
                    continue  # Skip resources with None IDs
                scored_docs.append((doc, total_score))

        # Sort by score (descending) and take top_k
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        results = [
            _normalize_search_result(doc, request.query, score=score)
            for doc, score in scored_docs[: request.top_k]
        ]

        duration = time.time() - start_time
        logger.info("Text search complete: %d results in %.2fs", len(results), duration)
        return SearchResponse(results=results, count=len(results))

    # Semantic mode: Use Ollama for AI-powered search (opt-in)
    logger.info("Using semantic search via Ollama (corpus size: %d)", len(all_resources))

    # Check if Ollama is available
    if not ollama.is_available():
        logger.warning("Ollama not available, falling back to text search with fuzzy matching")
        query_lower = request.query.lower()

        # Score each document based on title and content matches (same logic as text search)
        scored_docs = []
        for doc in all_resources:
            title_score = _fuzzy_match_text(query_lower, doc.get("title", "").lower())
            content_score = _fuzzy_match_text(query_lower, doc.get("content", "").lower())

            # Title matches are weighted higher (2x)
            total_score = (title_score * 2.0) + content_score

            if total_score > 0:
                # Skip resources with None IDs
                is_note = "note_id" in doc
                resource_id = doc.get("note_id") if is_note else doc.get("id")
                if resource_id is None:
                    logger.warning(
                        "Skipping resource with None ID in fallback search: Title=%s",
                        doc.get("title", "Unknown"),
                    )
                    continue
                scored_docs.append((doc, total_score))

        # Sort by score (descending) and take top_k
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        results = [
            _normalize_search_result(doc, request.query, score=score)
            for doc, score in scored_docs[: request.top_k]
        ]

        duration = time.time() - start_time
        logger.info("Fallback text search complete: %d results in %.2fs", len(results), duration)
        return SearchResponse(results=results, count=len(results))

    # Try to use fast semantic search with precomputed embeddings from Neo4j
    if neo4j.is_available():
        logger.info("Using fast semantic search with precomputed embeddings from Neo4j")

        # Fetch precomputed embeddings for articles and notes
        embeddings_data = neo4j.get_all_embeddings()
        logger.info("Fetched %d precomputed embeddings from Neo4j", len(embeddings_data))

        if embeddings_data:
            # Build documents with embeddings
            # Need to merge embedding data with full document content
            documents_with_embeddings = []

            for emb_data in embeddings_data:
                doc_id = emb_data["id"]
                doc_type = emb_data["type"]

                # Find the full document from all_resources
                full_doc = next(
                    (
                        doc
                        for doc in all_resources
                        if (doc_type == "Article" and str(doc.get("id")) == doc_id)
                        or (doc_type == "Note" and doc.get("note_id") == doc_id)
                    ),
                    None,
                )

                if full_doc:
                    # Combine full document with its embedding
                    doc_with_embedding = {**full_doc, "embedding": emb_data["embedding"]}
                    documents_with_embeddings.append(doc_with_embedding)

            logger.info("Matched %d documents with embeddings", len(documents_with_embeddings))

            # Perform fast semantic search
            semantic_results = ollama.semantic_search_with_precomputed_embeddings(
                request.query, documents_with_embeddings, request.top_k
            )

            results = [
                _normalize_search_result(doc, request.query, score=doc.get("score", 0.0))
                for doc in semantic_results
            ]
            duration = time.time() - start_time
            logger.info(
                "Fast semantic search complete: %d results in %.2fs", len(results), duration
            )
            return SearchResponse(results=results, count=len(results))
        else:
            logger.warning("No precomputed embeddings found, falling back to on-demand generation")

    # Fallback: Generate embeddings on-demand (slow but works without Neo4j)
    logger.info("Using on-demand embedding generation (slower)")
    semantic_results = ollama.semantic_search(request.query, all_resources, request.top_k)
    results = [
        _normalize_search_result(doc, request.query, score=doc.get("score", 0.0))
        for doc in semantic_results
    ]
    duration = time.time() - start_time
    logger.info("Semantic search complete: %d results in %.2fs", len(results), duration)
    return SearchResponse(results=results, count=len(results))
