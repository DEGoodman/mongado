"""Notes/Zettelkasten API routes (CRUD, graph operations).

Uses FastAPI dependency injection for testability. Dependencies can be
overridden in tests using app.dependency_overrides.
"""

import logging
import os
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth import AdminUser
from core import notes as notes_core
from dependencies import get_notes, get_ollama
from models import (
    BacklinksResponse,
    NoteCreate,
    NotesListResponse,
    NoteUpdate,
    SummaryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notes", tags=["notes"])

# Rate limiter - disabled in tests
limiter = Limiter(key_func=get_remote_address, enabled=os.getenv("TESTING") != "1")

# Type aliases for cleaner signatures
OllamaDep = Annotated[Any, Depends(get_ollama)]
NotesDep = Annotated[Any, Depends(get_notes)]


@router.post(
    "",
    response_model=dict[str, Any],
    status_code=201,
    summary="Create a new note",
    description="""
Create a new note in the knowledge base.

**Authentication:** Requires admin Bearer token

**Wikilinks:**
Use double brackets to link to other notes: `[[note-id]]`
Links are automatically parsed and stored as graph relationships.

**Note Types:**
- `is_reference: false` (default) - Zettelkasten insights/atomic notes
- `is_reference: true` - Quick references (checklists, frameworks, acronyms)

**Background Processing:**
Embedding and AI content (summary, link suggestions) are generated in the background
after the note is saved. This makes note creation instant while still enabling
semantic search and AI features within seconds.

**Rate Limit:** 10 notes per minute per IP address
""",
)
@limiter.limit("10/minute")  # 10 note creations per minute per IP
async def create_note(
    request: Request,
    note: NoteCreate,
    _admin: AdminUser,
    notes_service: NotesDep,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Create a new note (admin only)."""
    created_note: dict[str, Any] = notes_service.create_note(
        content=note.content,
        title=note.title,
        tags=note.tags,
        is_reference=note.is_reference,
    )

    # Schedule embedding and AI content generation in background (non-blocking)
    note_id = created_note.get("id", "")
    content = note.content
    title = note.title or ""

    background_tasks.add_task(notes_service.generate_embedding_for_note, note_id, content)
    background_tasks.add_task(notes_service.generate_ai_content_for_note, note_id, content, title)
    logger.debug("Scheduled background tasks for note: %s", note_id)

    return created_note


@router.get("", response_model=NotesListResponse)
async def list_notes(
    notes_service: NotesDep,
    is_reference: bool | None = None,
    include_full_content: bool = False,
    include_embedding: bool = False,
    minimal: bool = False,
    page: int = 1,
    limit: int = 20,
) -> NotesListResponse:
    """List all notes with configurable response payload and pagination.

    Query Parameters:
        is_reference: Filter by reference notes (True/False/None for all)
        include_full_content: Return full markdown (default: False, returns 200 char preview)
        include_embedding: Include embedding vectors (default: False, ~6KB/note)
        minimal: Only id+title for autocomplete/graph (default: False)
        page: Page number (1-indexed, default: 1)
        limit: Items per page (default: 20, max: 100)

    Default response (~500 bytes/note):
        - id, title, content_preview (200 chars), author, tags, created_at, is_reference, link_count

    Performance Impact:
        - Default (preview): ~50KB for 100 notes, ~10KB for 20 notes/page
        - Full content: ~500KB-1MB for 100 notes
        - With embeddings: +600KB for 100 notes
        - Minimal mode: ~5KB for 100 notes

    Examples:
        - List view: /api/notes (uses defaults, 20/page)
        - Page 2: /api/notes?page=2
        - All notes: /api/notes?limit=100
        - Detail view: /api/notes?include_full_content=true
        - Autocomplete: /api/notes?minimal=true
    """
    # Validate and cap pagination params
    page = max(1, page)  # Minimum page 1
    limit = min(max(1, limit), 100)  # Limit between 1-100

    # Get all notes (filtering applied in service)
    all_notes = notes_service.list_notes(
        is_reference=is_reference,
        include_full_content=include_full_content,
        include_embedding=include_embedding,
        minimal=minimal,
    )

    # Calculate pagination
    total = len(all_notes)
    total_pages = (total + limit - 1) // limit  # Ceiling division
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_notes = all_notes[start_idx:end_idx]

    return NotesListResponse(
        notes=paginated_notes,
        count=len(paginated_notes),
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/random", response_model=dict[str, Any])
async def get_random_note(notes_service: NotesDep) -> dict[str, Any]:
    """Get a random note for serendipitous discovery."""
    note: dict[str, Any] | None = notes_service.get_random_note()

    if not note:
        raise HTTPException(status_code=404, detail="No notes available")

    return note


@router.get("/orphans", response_model=dict[str, Any])
async def get_orphan_notes(notes_service: NotesDep) -> dict[str, Any]:
    """Get orphan notes (notes with no links and no backlinks).

    These are isolated notes that haven't been integrated into the knowledge base yet.
    """
    orphans = notes_service.get_orphan_notes()
    return {"notes": orphans, "count": len(orphans)}


@router.get("/dead-ends", response_model=dict[str, Any])
async def get_dead_end_notes(notes_service: NotesDep) -> dict[str, Any]:
    """Get dead-end notes (notes with no outbound links).

    These notes receive links but don't link to other notes - good candidates for expansion.
    """
    dead_ends = notes_service.get_dead_end_notes()
    return {"notes": dead_ends, "count": len(dead_ends)}


@router.get("/hubs", response_model=dict[str, Any])
async def get_hub_notes(notes_service: NotesDep, min_links: int = 3) -> dict[str, Any]:
    """Get hub notes (notes with many outbound links).

    These are index or map notes that serve as entry points into topic areas.

    Args:
        min_links: Minimum number of outbound links (default: 3)
    """
    hubs = notes_service.get_hub_notes(min_links=min_links)
    return {"notes": hubs, "count": len(hubs)}


@router.get("/central", response_model=dict[str, Any])
async def get_central_notes(notes_service: NotesDep, min_backlinks: int = 3) -> dict[str, Any]:
    """Get central concept notes (notes with many backlinks).

    These are highly referenced notes representing core concepts.

    Args:
        min_backlinks: Minimum number of backlinks (default: 3)
    """
    central = notes_service.get_central_notes(min_backlinks=min_backlinks)
    return {"notes": central, "count": len(central)}


@router.get("/quick-lists", response_model=dict[str, Any])
async def get_quick_lists(
    notes_service: NotesDep,
    min_hub_links: int = 3,
    min_central_backlinks: int = 3,
    stale_days: int = 60,
) -> dict[str, Any]:
    """Get categorized quick lists for knowledge base navigation.

    Returns four categories of notes:
    - orphans: Isolated notes needing integration (0 links, 0 backlinks)
    - hubs: Entry point notes with many outbound links (3+ links)
    - central_concepts: Highly referenced core concept notes (3+ backlinks)
    - stale: Notes not updated in 60+ days (needs review)

    Args:
        min_hub_links: Minimum outbound links for hub notes (default: 3)
        min_central_backlinks: Minimum backlinks for central notes (default: 3)
        stale_days: Days threshold for stale notes (default: 60)

    Returns:
        Dict with orphans, hubs, central_concepts, and stale arrays plus counts
    """
    orphans = notes_service.get_orphan_notes()
    hubs = notes_service.get_hub_notes(min_links=min_hub_links)
    central = notes_service.get_central_notes(min_backlinks=min_central_backlinks)
    stale = notes_service.get_stale_notes(days_threshold=stale_days, limit=10)

    return {
        "orphans": orphans,
        "hubs": hubs,
        "central_concepts": central,
        "stale": stale,
        "counts": {
            "orphans": len(orphans),
            "hubs": len(hubs),
            "central_concepts": len(central),
            "stale": len(stale),
        },
    }


@router.get("/stale", response_model=dict[str, Any])
async def get_stale_notes(
    notes_service: NotesDep,
    days: int = 60,
    limit: int = 50,
) -> dict[str, Any]:
    """Get stale notes (notes not updated in specified number of days).

    These are notes that may need review or updating - good candidates for resurface.

    Args:
        days: Number of days threshold (default: 60)
        limit: Maximum number of notes to return (default: 50)

    Returns:
        Dict with notes array, count, and days_threshold
    """
    stale = notes_service.get_stale_notes(days_threshold=days, limit=limit)
    return {
        "notes": stale,
        "count": len(stale),
        "days_threshold": days,
    }


@router.get("/note-of-day", response_model=dict[str, Any])
async def get_note_of_day(notes_service: NotesDep, days: int = 60) -> dict[str, Any]:
    """Get 'note of the day' for resurface widget.

    Returns a random stale note if any exist, otherwise returns any random note.
    Designed for homepage widgets to encourage knowledge base maintenance.

    Args:
        days: Staleness threshold in days (default: 60)

    Returns:
        Dict with note, is_stale indicator, and message
    """
    # Try to get a stale note first
    stale_note = notes_service.get_random_stale_note(days_threshold=days)

    if stale_note:
        return {
            "note": stale_note,
            "is_stale": True,
            "message": f"This note hasn't been updated in over {days} days",
        }

    # Fall back to any random note
    random_note = notes_service.get_random_note()

    if not random_note:
        raise HTTPException(status_code=404, detail="No notes available")

    return {
        "note": random_note,
        "is_stale": False,
        "message": "Random note for discovery",
    }


@router.get("/{note_id}", response_model=dict[str, Any])
async def get_note(note_id: str, notes_service: NotesDep) -> dict[str, Any]:
    """Get a specific note by ID."""
    note: dict[str, Any] | None = notes_service.get_note(note_id)

    if not note:
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

    return note


@router.put("/{note_id}", response_model=dict[str, Any])
async def update_note(
    note_id: str,
    note_update: NoteUpdate,
    _admin: AdminUser,
    notes_service: NotesDep,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Update a note (admin only).

    Embedding and AI content are regenerated in the background after save.
    """
    updated: dict[str, Any] | None = notes_service.update_note(
        note_id=note_id,
        content=note_update.content,
        title=note_update.title,
        tags=note_update.tags,
        is_reference=note_update.is_reference,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail=f"Note '{note_id}' not found",
        )

    # Schedule embedding and AI content regeneration in background (non-blocking)
    content = note_update.content
    title = note_update.title or ""

    background_tasks.add_task(notes_service.generate_embedding_for_note, note_id, content)
    background_tasks.add_task(notes_service.generate_ai_content_for_note, note_id, content, title)
    logger.debug("Scheduled background tasks for note update: %s", note_id)

    return updated


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    _admin: AdminUser,
    notes_service: NotesDep,
) -> dict[str, str]:
    """Delete a note (admin only)."""
    deleted = notes_service.delete_note(note_id=note_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Note '{note_id}' not found",
        )

    return {"message": f"Note '{note_id}' deleted successfully"}


@router.get("/{note_id}/backlinks", response_model=BacklinksResponse)
async def get_backlinks(note_id: str, notes_service: NotesDep) -> BacklinksResponse:
    """Get all notes that link to this note."""
    backlinks = notes_service.get_backlinks(note_id)

    return BacklinksResponse(backlinks=backlinks, count=len(backlinks))


@router.get("/{note_id}/links", response_model=dict[str, Any])
async def get_outbound_links(note_id: str, notes_service: NotesDep) -> dict[str, Any]:
    """Get all notes this note links to."""
    links = notes_service.get_outbound_links(note_id)

    return {"links": links, "count": len(links)}


@router.post("/{note_id}/review", response_model=dict[str, Any])
async def mark_note_reviewed(
    note_id: str,
    _admin: AdminUser,
    notes_service: NotesDep,
) -> dict[str, Any]:
    """Mark a note as reviewed (admin only).

    Updates the note's updated_at timestamp without requiring content changes.
    This resets the staleness clock for notes that have been reviewed but
    don't need actual updates.

    Args:
        note_id: Note ID

    Returns:
        Updated note dict
    """
    updated: dict[str, Any] | None = notes_service.mark_note_reviewed(note_id)

    if not updated:
        raise HTTPException(
            status_code=404,
            detail=f"Note '{note_id}' not found",
        )

    return updated


@router.get("/graph/data", response_model=dict[str, Any])
async def get_graph_data(notes_service: NotesDep) -> dict[str, Any]:
    """Get full graph data (all nodes and edges) for visualization.

    Returns:
    - nodes: List of all notes
    - edges: List of all links between notes
    """
    # Get all notes (I/O)
    notes = notes_service.list_notes()

    # Build graph using pure function
    return notes_core.build_graph_data(notes)


@router.get("/{note_id}/summary", response_model=SummaryResponse)
async def get_note_summary(
    note_id: str, notes_service: NotesDep, ollama: OllamaDep, refresh: bool = False
) -> SummaryResponse:
    """Get AI summary of a note (returns cached if available).

    Args:
        note_id: Note ID
        refresh: If True, regenerate summary even if cached (default: False)

    Returns:
        Summary with cached indicator
    """
    # Get the note first to verify it exists
    note = notes_service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Try to get cached summary first (unless refresh requested)
    if not refresh:
        ai_content = notes_service.get_ai_content(note_id)
        if ai_content and ai_content.get("ai_summary"):
            return SummaryResponse(
                summary=ai_content["ai_summary"],
                cached=True,
                cached_at=ai_content.get("ai_summary_at"),
            )

    # No cache or refresh requested - generate new summary
    if not ollama.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI summary feature is not available. Ollama is not running or not configured.",
        )

    # Force regeneration
    if refresh:
        ai_content = notes_service.regenerate_ai_content(note_id)
        if ai_content and ai_content.get("ai_summary"):
            return SummaryResponse(
                summary=ai_content["ai_summary"],
                cached=True,
                cached_at=ai_content.get("ai_summary_at"),
            )

    # Fallback: generate on-demand (shouldn't normally reach here)
    summary = ollama.summarize_article(note.get("content", ""))

    if not summary:
        raise HTTPException(status_code=500, detail="Failed to generate summary. Please try again.")

    return SummaryResponse(summary=summary, cached=False)
