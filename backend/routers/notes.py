"""Notes/Zettelkasten API routes (CRUD, graph operations)."""

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth import SessionID, get_session_id
from config import get_settings
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


# Helper function to try admin auth without raising
def try_verify_admin(authorization: str | None = Header(None)) -> bool:
    """Try to verify admin token without raising exceptions."""
    if not authorization:
        return False

    if not authorization.startswith("Bearer "):
        return False

    token = authorization.replace("Bearer ", "").strip()
    expected_token = get_settings().admin_token

    if not expected_token or token != expected_token:
        return False

    logger.info("Admin authenticated successfully")
    return True


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

**Authentication:**
- **Admin** (with Bearer token): Creates persistent note stored in Neo4j
- **Visitor** (with X-Session-ID header): Creates ephemeral note (session-specific)

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
        session_id: SessionID = Depends(get_session_id),
        is_admin: bool = Depends(try_verify_admin),
    ) -> dict[str, Any]:
        """Create a new note."""
        if not is_admin and not session_id:
            raise HTTPException(
                status_code=400,
                detail="Session ID required for anonymous users. Include X-Session-ID header.",
            )

        created_note = notes_service.create_note(
            content=note.content,
            title=note.title,
            tags=note.tags,
            is_admin=is_admin,
            session_id=session_id,
        )

        return created_note

    @router.get("", response_model=NotesListResponse)
    async def list_notes(
        session_id: SessionID = Depends(get_session_id),
        is_admin: bool = Depends(try_verify_admin),
    ) -> NotesListResponse:
        """List all accessible notes.

        Returns persistent notes + ephemeral notes for current session.
        """
        notes = notes_service.list_notes(is_admin=is_admin, session_id=session_id)

        return NotesListResponse(notes=notes, count=len(notes))

    @router.get("/{note_id}", response_model=dict[str, Any])
    async def get_note(
        note_id: str,
        session_id: SessionID = Depends(get_session_id),
        is_admin: bool = Depends(try_verify_admin),
    ) -> dict[str, Any]:
        """Get a specific note by ID."""
        note = notes_service.get_note(note_id, is_admin=is_admin, session_id=session_id)

        if not note:
            raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

        return note

    @router.put("/{note_id}", response_model=dict[str, Any])
    async def update_note(
        note_id: str,
        note_update: NoteUpdate,
        session_id: SessionID = Depends(get_session_id),
        is_admin: bool = Depends(try_verify_admin),
    ) -> dict[str, Any]:
        """Update a note.

        - Admin can update persistent notes
        - Visitors can update their own ephemeral notes
        """
        updated = notes_service.update_note(
            note_id=note_id,
            content=note_update.content,
            title=note_update.title,
            tags=note_update.tags,
            is_admin=is_admin,
            session_id=session_id,
        )

        if not updated:
            raise HTTPException(
                status_code=404,
                detail=f"Note '{note_id}' not found or unauthorized",
            )

        return updated

    @router.delete("/{note_id}")
    async def delete_note(
        note_id: str,
        session_id: SessionID = Depends(get_session_id),
        is_admin: bool = Depends(try_verify_admin),
    ) -> dict[str, str]:
        """Delete a note.

        - Admin can delete persistent notes
        - Visitors can delete their own ephemeral notes
        """
        deleted = notes_service.delete_note(
            note_id=note_id, is_admin=is_admin, session_id=session_id
        )

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Note '{note_id}' not found or unauthorized",
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
    async def get_graph_data(
        session_id: SessionID = Depends(get_session_id),
        is_admin: bool = Depends(try_verify_admin),
    ) -> dict[str, Any]:
        """Get full graph data (all nodes and edges) for visualization.

        Returns:
        - nodes: List of all accessible notes
        - edges: List of all links between notes
        """
        # Get all accessible notes (I/O)
        notes = notes_service.list_notes(is_admin=is_admin, session_id=session_id)

        # Build graph using pure function
        return notes_core.build_graph_data(notes)

    return router
