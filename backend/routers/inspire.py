"""Content inspiration API routes (suggestions, gaps, connections).

Uses FastAPI dependency injection for testability. Dependencies can be
overridden in tests using app.dependency_overrides.
"""

import logging
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from core import inspire as inspire_core
from dependencies import get_notes, get_ollama

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inspire", tags=["inspire"])

# Type aliases for cleaner signatures
OllamaDep = Annotated[Any, Depends(get_ollama)]
NotesDep = Annotated[Any, Depends(get_notes)]


@router.get("/suggestions", response_model=dict[str, Any])
def get_suggestions(
    notes_service: NotesDep,
    ollama: OllamaDep,
    limit: int = 5,
) -> dict[str, Any]:
    """Get AI-powered content suggestions for knowledge base improvement.

    Analyzes the knowledge base to find:
    - Knowledge gaps (underdeveloped topics)
    - Connection opportunities (similar but unlinked notes)

    Uses Ollama to generate human-friendly suggestion descriptions.
    Falls back to structured suggestions if Ollama is unavailable.

    Args:
        limit: Maximum number of suggestions to return (default: 5)

    Returns:
        Dict with suggestions, generated_at timestamp, and has_llm indicator
    """
    # Get data for analysis
    notes_with_stats = notes_service.get_notes_with_stats()
    notes_with_embeddings = notes_service.get_notes_with_embeddings()
    all_links = notes_service.get_all_links()

    # Find underdeveloped topics
    gap_notes = inspire_core.find_underdeveloped_topics(
        notes=notes_with_stats,
        min_content_length=500,
        max_links=1,
        limit=limit,
    )
    logger.info("Found %d underdeveloped topics", len(gap_notes))

    # Find unlinked similar notes
    note_embeddings = [
        (note["id"], note["title"], note["embedding"]) for note in notes_with_embeddings
    ]
    connection_opportunities = inspire_core.find_unlinked_similar_notes(
        note_embeddings=note_embeddings,
        existing_links=all_links,
        similarity_threshold=0.7,
        limit=limit,
    )
    logger.info("Found %d connection opportunities", len(connection_opportunities))

    # Try to use LLM for human-friendly suggestions
    suggestions: list[dict[str, Any]] = []
    has_llm = False

    if ollama.is_available() and ollama.client and (gap_notes or connection_opportunities):
        try:
            # Build prompt for LLM
            prompt = inspire_core.build_inspiration_prompt(
                gap_notes=gap_notes,
                connection_opportunities=connection_opportunities,
            )

            # Generate suggestions
            response_data = ollama.client.generate(
                model=ollama.structured_model,
                prompt=prompt,
                options={"num_ctx": 4096, "num_predict": 1024},
            )

            response_text = response_data.get("response", "")
            if response_text:
                parsed = inspire_core.parse_inspiration_response(response_text)
                if parsed:
                    suggestions = parsed[:limit]
                    has_llm = True
                    logger.info("Generated %d AI-powered suggestions", len(suggestions))

        except Exception as e:
            logger.error("Error generating AI suggestions: %s", e)

    # Fallback to structured suggestions without LLM
    if not suggestions:
        suggestions = inspire_core.build_fallback_suggestions(
            gap_notes=gap_notes,
            connection_opportunities=connection_opportunities,
            limit=limit,
        )
        logger.info("Generated %d fallback suggestions (no LLM)", len(suggestions))

    return {
        "suggestions": suggestions,
        "generated_at": time.time(),
        "has_llm": has_llm,
    }


@router.get("/gaps", response_model=dict[str, Any])
def get_knowledge_gaps(
    notes_service: NotesDep,
    min_content_length: int = 500,
    max_links: int = 1,
    limit: int = 10,
) -> dict[str, Any]:
    """Get underdeveloped topics without LLM (fast endpoint).

    Finds notes that are short and/or have few connections.
    These are candidates for expansion.

    Args:
        min_content_length: Notes shorter than this are considered underdeveloped
        max_links: Notes with this many or fewer total links are candidates
        limit: Maximum results to return

    Returns:
        Dict with gaps list and count
    """
    notes_with_stats = notes_service.get_notes_with_stats()

    gaps = inspire_core.find_underdeveloped_topics(
        notes=notes_with_stats,
        min_content_length=min_content_length,
        max_links=max_links,
        limit=limit,
    )

    return {
        "gaps": gaps,
        "count": len(gaps),
        "min_content_length": min_content_length,
        "max_links": max_links,
    }


@router.get("/connections", response_model=dict[str, Any])
def get_connection_opportunities(
    notes_service: NotesDep,
    similarity_threshold: float = 0.7,
    limit: int = 10,
) -> dict[str, Any]:
    """Get unlinked similar notes without LLM (fast endpoint).

    Finds pairs of notes that are semantically similar but not linked.
    These are candidates for adding wikilinks.

    Args:
        similarity_threshold: Minimum cosine similarity to consider (0.0 to 1.0)
        limit: Maximum results to return

    Returns:
        Dict with connections list and count
    """
    notes_with_embeddings = notes_service.get_notes_with_embeddings()
    all_links = notes_service.get_all_links()

    # Format for the pure function
    note_embeddings = [
        (note["id"], note["title"], note["embedding"]) for note in notes_with_embeddings
    ]

    connections = inspire_core.find_unlinked_similar_notes(
        note_embeddings=note_embeddings,
        existing_links=all_links,
        similarity_threshold=similarity_threshold,
        limit=limit,
    )

    return {
        "connections": connections,
        "count": len(connections),
        "similarity_threshold": similarity_threshold,
    }
