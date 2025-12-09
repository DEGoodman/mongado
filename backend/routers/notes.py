"""Notes/Zettelkasten API routes (CRUD, graph operations)."""

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth import AdminUser, verify_admin
from core import notes as notes_core
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


def create_notes_router(notes_service: Any, ollama_client: Any) -> APIRouter:
    """Create notes router with dependencies injected.

    Args:
        notes_service: Notes service for note operations
        ollama_client: Ollama client for AI features (summaries, etc.)

    Returns:
        Configured APIRouter with notes endpoints
    """

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

**Rate Limit:** 10 notes per minute per IP address
""",
    )
    @limiter.limit("10/minute")  # 10 note creations per minute per IP
    async def create_note(
        request: Request,
        note: NoteCreate,
        _admin: AdminUser = Depends(verify_admin),
    ) -> dict[str, Any]:
        """Create a new note (admin only)."""
        created_note: dict[str, Any] = notes_service.create_note(
            content=note.content,
            title=note.title,
            tags=note.tags,
            is_reference=note.is_reference,
        )

        return created_note

    @router.get("", response_model=NotesListResponse)
    async def list_notes(
        is_reference: bool | None = None,
        include_full_content: bool = False,
        include_embedding: bool = False,
        minimal: bool = False,
    ) -> NotesListResponse:
        """List all notes with configurable response payload.

        Query Parameters:
            is_reference: Filter by reference notes (True/False/None for all)
            include_full_content: Return full markdown (default: False, returns 200 char preview)
            include_embedding: Include embedding vectors (default: False, ~6KB/note)
            minimal: Only id+title for autocomplete/graph (default: False)

        Default response (~500 bytes/note):
            - id, title, content_preview (200 chars), author, tags, created_at, is_reference, link_count

        Performance Impact:
            - Default (preview): ~50KB for 100 notes
            - Full content: ~500KB-1MB for 100 notes
            - With embeddings: +600KB for 100 notes
            - Minimal mode: ~5KB for 100 notes

        Examples:
            - List view: /api/notes (uses defaults)
            - Detail view: /api/notes?include_full_content=true
            - Autocomplete: /api/notes?minimal=true
            - Search with embeddings: /api/notes?include_embedding=true
        """
        notes = notes_service.list_notes(
            is_reference=is_reference,
            include_full_content=include_full_content,
            include_embedding=include_embedding,
            minimal=minimal,
        )

        return NotesListResponse(notes=notes, count=len(notes))

    @router.get("/random", response_model=dict[str, Any])
    async def get_random_note() -> dict[str, Any]:
        """Get a random note for serendipitous discovery."""
        note: dict[str, Any] | None = notes_service.get_random_note()

        if not note:
            raise HTTPException(status_code=404, detail="No notes available")

        return note

    @router.get("/orphans", response_model=dict[str, Any])
    async def get_orphan_notes() -> dict[str, Any]:
        """Get orphan notes (notes with no links and no backlinks).

        These are isolated notes that haven't been integrated into the knowledge base yet.
        """
        orphans = notes_service.get_orphan_notes()
        return {"notes": orphans, "count": len(orphans)}

    @router.get("/dead-ends", response_model=dict[str, Any])
    async def get_dead_end_notes() -> dict[str, Any]:
        """Get dead-end notes (notes with no outbound links).

        These notes receive links but don't link to other notes - good candidates for expansion.
        """
        dead_ends = notes_service.get_dead_end_notes()
        return {"notes": dead_ends, "count": len(dead_ends)}

    @router.get("/hubs", response_model=dict[str, Any])
    async def get_hub_notes(min_links: int = 3) -> dict[str, Any]:
        """Get hub notes (notes with many outbound links).

        These are index or map notes that serve as entry points into topic areas.

        Args:
            min_links: Minimum number of outbound links (default: 3)
        """
        hubs = notes_service.get_hub_notes(min_links=min_links)
        return {"notes": hubs, "count": len(hubs)}

    @router.get("/central", response_model=dict[str, Any])
    async def get_central_notes(min_backlinks: int = 3) -> dict[str, Any]:
        """Get central concept notes (notes with many backlinks).

        These are highly referenced notes representing core concepts.

        Args:
            min_backlinks: Minimum number of backlinks (default: 3)
        """
        central = notes_service.get_central_notes(min_backlinks=min_backlinks)
        return {"notes": central, "count": len(central)}

    @router.get("/quick-lists", response_model=dict[str, Any])
    async def get_quick_lists(
        min_hub_links: int = 3, min_central_backlinks: int = 3
    ) -> dict[str, Any]:
        """Get categorized quick lists for knowledge base navigation.

        Returns three categories of notes:
        - orphans: Isolated notes needing integration (0 links, 0 backlinks)
        - hubs: Entry point notes with many outbound links (3+ links)
        - central_concepts: Highly referenced core concept notes (3+ backlinks)

        Args:
            min_hub_links: Minimum outbound links for hub notes (default: 3)
            min_central_backlinks: Minimum backlinks for central notes (default: 3)

        Returns:
            Dict with orphans, hubs, and central_concepts arrays plus counts
        """
        orphans = notes_service.get_orphan_notes()
        hubs = notes_service.get_hub_notes(min_links=min_hub_links)
        central = notes_service.get_central_notes(min_backlinks=min_central_backlinks)

        return {
            "orphans": orphans,
            "hubs": hubs,
            "central_concepts": central,
            "counts": {
                "orphans": len(orphans),
                "hubs": len(hubs),
                "central_concepts": len(central),
            },
        }

    @router.get("/{note_id}", response_model=dict[str, Any])
    async def get_note(note_id: str) -> dict[str, Any]:
        """Get a specific note by ID."""
        note: dict[str, Any] | None = notes_service.get_note(note_id)

        if not note:
            raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

        return note

    @router.put("/{note_id}", response_model=dict[str, Any])
    async def update_note(
        note_id: str,
        note_update: NoteUpdate,
        _admin: AdminUser = Depends(verify_admin),
    ) -> dict[str, Any]:
        """Update a note (admin only)."""
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

        return updated

    @router.delete("/{note_id}")
    async def delete_note(
        note_id: str,
        _admin: AdminUser = Depends(verify_admin),
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
    async def get_backlinks(note_id: str) -> BacklinksResponse:
        """Get all notes that link to this note."""
        backlinks = notes_service.get_backlinks(note_id)

        return BacklinksResponse(backlinks=backlinks, count=len(backlinks))

    @router.get("/{note_id}/links", response_model=dict[str, Any])
    async def get_outbound_links(note_id: str) -> dict[str, Any]:
        """Get all notes this note links to."""
        links = notes_service.get_outbound_links(note_id)

        return {"links": links, "count": len(links)}

    @router.get("/graph/data", response_model=dict[str, Any])
    async def get_graph_data() -> dict[str, Any]:
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
    async def get_note_summary(note_id: str) -> SummaryResponse:
        """Generate an AI summary of a specific note using Ollama."""
        if not ollama_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="AI summary feature is not available. Ollama is not running or not configured.",
            )

        # Get the note
        note = notes_service.get_note(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")

        # Generate summary from note content
        summary = ollama_client.summarize_article(note.get("content", ""))

        if not summary:
            raise HTTPException(
                status_code=500, detail="Failed to generate summary. Please try again."
            )

        return SummaryResponse(summary=summary)

    return router
