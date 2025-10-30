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
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notes", tags=["notes"])

# Rate limiter - disabled in tests
limiter = Limiter(key_func=get_remote_address, enabled=os.getenv("TESTING") != "1")


def create_notes_router(notes_service: Any) -> APIRouter:
    """Create notes router with dependencies injected.

    Args:
        notes_service: Notes service for note operations

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
        created_note = notes_service.create_note(
            content=note.content,
            title=note.title,
            tags=note.tags,
        )

        return created_note

    @router.get("", response_model=NotesListResponse)
    async def list_notes() -> NotesListResponse:
        """List all notes (ordered by created_at descending)."""
        notes = notes_service.list_notes()

        return NotesListResponse(notes=notes, count=len(notes))

    @router.get("/random", response_model=dict[str, Any])
    async def get_random_note() -> dict[str, Any]:
        """Get a random note for serendipitous discovery."""
        note = notes_service.get_random_note()

        if not note:
            raise HTTPException(status_code=404, detail="No notes available")

        return note

    @router.get("/{note_id}", response_model=dict[str, Any])
    async def get_note(note_id: str) -> dict[str, Any]:
        """Get a specific note by ID."""
        note = notes_service.get_note(note_id)

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
        updated = notes_service.update_note(
            note_id=note_id,
            content=note_update.content,
            title=note_update.title,
            tags=note_update.tags,
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

    return router
