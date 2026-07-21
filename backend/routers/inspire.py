"""Content inspiration API routes (suggestions, gaps, connections).

Uses FastAPI dependency injection for testability. Dependencies can be
overridden in tests using app.dependency_overrides.

The analysis (graph + similarity + tag coverage) is pure and cheap enough to
recompute, but it is cached against a KB fingerprint so that pressing Refresh
rotates through an existing candidate pool instead of re-running an O(n^2)
similarity sweep and a fresh LLM call every time (#259).
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from core import inspire as inspire_core
from dependencies import get_llm, get_notes, get_static_articles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/inspire", tags=["inspire"])

# Type aliases for cleaner signatures
LlmDep = Annotated[Any, Depends(get_llm)]
NotesDep = Annotated[Any, Depends(get_notes)]
ArticlesDep = Annotated[list[dict[str, Any]], Depends(get_static_articles)]

# Interactive endpoint: fall through to the backup provider fast rather than
# making the user wait out the default 30s timeout on a hung primary.
LLM_TIMEOUT_SECONDS = 8.0

CACHE_TTL_SECONDS = 900.0


@dataclass
class _SuggestionCache:
    """Per-process cache of generated suggestions, keyed by KB fingerprint."""

    fingerprint: str = ""
    generated_at: float = 0.0
    refresh_count: int = 0
    entries: dict[int, tuple[list[dict[str, Any]], bool]] = field(default_factory=dict)

    def is_valid(self, fingerprint: str) -> bool:
        return (
            self.fingerprint == fingerprint
            and time.monotonic() - self.generated_at < CACHE_TTL_SECONDS
        )

    def reset(self, fingerprint: str) -> None:
        self.fingerprint = fingerprint
        self.generated_at = time.monotonic()
        self.refresh_count = 0
        self.entries = {}


_cache = _SuggestionCache()


def _analyze(
    notes_service: Any, articles: list[dict[str, Any]]
) -> tuple[dict[str, list[dict[str, Any]]], str]:
    """Run the full KB analysis and return candidates by type + a fingerprint.

    Everything here is I/O plus calls into the pure core; no business logic.
    """
    notes_with_stats = notes_service.get_notes_with_stats()
    notes_with_embeddings = notes_service.get_notes_with_embeddings()
    all_links = notes_service.get_all_links()

    note_embeddings = [
        (note["id"], note["title"], note["embedding"]) for note in notes_with_embeddings
    ]
    pairs = inspire_core.find_unlinked_similar_notes(
        note_embeddings=note_embeddings,
        existing_links=all_links,
        limit=30,
    )

    candidates: dict[str, list[dict[str, Any]]] = {
        "orphan": inspire_core.find_orphan_notes(notes_with_stats),
        "split": inspire_core.find_oversized_notes(notes_with_stats),
        "promote": inspire_core.find_promotion_candidates(notes_with_stats),
        "duplicate": [p for p in pairs if p["kind"] == "duplicate"],
        "connection": [p for p in pairs if p["kind"] == "connection"],
        "hub": inspire_core.find_hub_opportunities(pairs),
        "article": inspire_core.find_uncovered_tag_clusters(notes_with_stats, articles),
    }

    fingerprint = inspire_core.compute_kb_fingerprint(notes_with_stats, articles)

    logger.info(
        "KB analysis: %s",
        ", ".join(f"{k}={len(v)}" for k, v in candidates.items() if v) or "no opportunities",
    )
    return candidates, fingerprint


@router.get("/suggestions", response_model=dict[str, Any])
def get_suggestions(
    notes_service: NotesDep,
    llm: LlmDep,
    articles: ArticlesDep,
    limit: int = 5,
    refresh: bool = False,
    skip_llm: bool = False,
) -> dict[str, Any]:
    """Get AI-phrased content suggestions for knowledge base improvement.

    Analyzes the knowledge base for structural opportunities: orphaned notes,
    likely duplicates, unlinked but related notes, clusters wanting a hub,
    notes worth promoting to articles, oversized notes worth splitting, and
    topics with many notes but no article.

    Note length is deliberately not a signal on its own - short atomic notes
    are the goal, not a defect (#259).

    Uses the LLM only to phrase the findings. Falls back to templated wording
    if generation fails, and reports which happened via has_llm.

    Args:
        limit: Maximum number of suggestions to return (default: 5)
        refresh: Rotate to a different slice of the candidate pool
        skip_llm: Return templated wording immediately without calling the LLM.
            Lets the page paint real suggestions first and swap in the phrased
            ones when they arrive, without reimplementing the wording client-side.

    Returns:
        Dict with suggestions, generated_at, has_llm, and cached indicators
    """
    candidates, fingerprint = _analyze(notes_service, articles)

    if not _cache.is_valid(fingerprint):
        _cache.reset(fingerprint)
    elif refresh:
        _cache.refresh_count += 1

    offset = _cache.refresh_count
    cache_key = hash((limit, offset))

    if skip_llm:
        composed = inspire_core.compose_candidates(candidates, limit=limit, offset=offset)
        return {
            "suggestions": inspire_core.build_fallback_suggestions(composed, limit=limit),
            "generated_at": _cache.generated_at,
            "has_llm": False,
            "cached": False,
        }

    if not refresh and cache_key in _cache.entries:
        cached_suggestions, cached_has_llm = _cache.entries[cache_key]
        return {
            "suggestions": cached_suggestions,
            "generated_at": _cache.generated_at,
            "has_llm": cached_has_llm,
            "cached": True,
        }

    composed = inspire_core.compose_candidates(candidates, limit=limit, offset=offset)

    suggestions: list[dict[str, Any]] = []
    has_llm = False

    if composed and llm.is_available():
        try:
            prompt = inspire_core.build_inspiration_prompt(composed)
            response_text = llm.generate(
                prompt,
                role="structured",
                num_ctx=4096,
                max_tokens=1024,
                timeout=LLM_TIMEOUT_SECONDS,
            )
            if response_text:
                parsed = inspire_core.parse_inspiration_response(response_text)
                # Trust the LLM for wording only - IDs and types come from the analysis
                parsed = inspire_core.sanitize_suggestions(parsed, composed)
                if parsed:
                    suggestions = parsed[:limit]
                    has_llm = True
                    logger.info("Generated %d AI-phrased suggestions", len(suggestions))
                else:
                    logger.warning("LLM response was unparseable - using templated wording")
            else:
                logger.warning("LLM returned no content - using templated wording")
        except Exception as e:
            logger.error("Error generating AI suggestions: %s", e)

    if not suggestions:
        suggestions = inspire_core.build_fallback_suggestions(composed, limit=limit)
        logger.info("Generated %d templated suggestions (no LLM)", len(suggestions))

    _cache.entries[cache_key] = (suggestions, has_llm)

    return {
        "suggestions": suggestions,
        "generated_at": _cache.generated_at,
        "has_llm": has_llm,
        "cached": False,
    }


@router.get("/gaps", response_model=dict[str, Any])
def get_knowledge_gaps(
    notes_service: NotesDep,
    articles: ArticlesDep,
    limit: int = 10,
) -> dict[str, Any]:
    """Get structural gaps without an LLM (fast endpoint).

    Returns orphaned notes (unreachable in the graph), oversized notes (split
    candidates), well-referenced notes (article candidates), and tag clusters
    with no covering article.

    Args:
        limit: Maximum results per category

    Returns:
        Dict with orphans, oversized, promotable, uncovered_topics and counts
    """
    notes_with_stats = notes_service.get_notes_with_stats()

    orphans = inspire_core.find_orphan_notes(notes_with_stats, limit=limit)
    oversized = inspire_core.find_oversized_notes(notes_with_stats, limit=limit)
    promotable = inspire_core.find_promotion_candidates(notes_with_stats, limit=limit)
    uncovered = inspire_core.find_uncovered_tag_clusters(
        notes_with_stats, articles, limit=limit
    )

    return {
        "orphans": orphans,
        "oversized": oversized,
        "promotable": promotable,
        "uncovered_topics": uncovered,
        "count": len(orphans) + len(oversized) + len(promotable) + len(uncovered),
    }


@router.get("/connections", response_model=dict[str, Any])
def get_connection_opportunities(
    notes_service: NotesDep,
    similarity_threshold: float = inspire_core.CONNECTION_MIN_SIMILARITY,
    limit: int = 10,
) -> dict[str, Any]:
    """Get unlinked similar notes without an LLM (fast endpoint).

    Each pair is classified as a "duplicate" (same idea captured twice - merge)
    or a "connection" (related but distinct - link). Clusters of three or more
    mutually similar notes are also returned as hub-note opportunities.

    Args:
        similarity_threshold: Minimum cosine similarity to consider (0.0 to 1.0)
        limit: Maximum results to return

    Returns:
        Dict with connections, duplicates, hubs and counts
    """
    notes_with_embeddings = notes_service.get_notes_with_embeddings()
    all_links = notes_service.get_all_links()

    note_embeddings = [
        (note["id"], note["title"], note["embedding"]) for note in notes_with_embeddings
    ]

    pairs = inspire_core.find_unlinked_similar_notes(
        note_embeddings=note_embeddings,
        existing_links=all_links,
        similarity_threshold=similarity_threshold,
        limit=max(limit, 30),
    )

    duplicates = [p for p in pairs if p["kind"] == "duplicate"][:limit]
    connections = [p for p in pairs if p["kind"] == "connection"][:limit]
    hubs = inspire_core.find_hub_opportunities(pairs, limit=limit)

    return {
        "connections": connections,
        "duplicates": duplicates,
        "hubs": hubs,
        "count": len(connections) + len(duplicates) + len(hubs),
        "similarity_threshold": similarity_threshold,
    }
