"""FastAPI endpoints for Zettelkasten notes."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import SessionID, get_session_id, verify_admin
from notes_service import get_notes_service

logger = logging.getLogger(__name__)

# Create router for notes endpoints
router = APIRouter(prefix="/api/notes", tags=["notes"])

# Get service
notes_service = get_notes_service()


# Pydantic models
class NoteCreate(BaseModel):
    """Request model for creating a note."""

    title: str | None = None
    content: str
    tags: list[str] = []


class NoteUpdate(BaseModel):
    """Request model for updating a note."""

    title: str | None = None
    content: str
    tags: list[str] | None = None


class NoteResponse(BaseModel):
    """Response model for a single note."""

    id: str
    title: str | None
    content: str
    author: str
    is_ephemeral: bool
    tags: list[str]
    created_at: str | float
    updated_at: str | float
    links: list[str]


class NotesListResponse(BaseModel):
    """Response model for list of notes."""

    notes: list[dict[str, Any]]
    count: int


class BacklinksResponse(BaseModel):
    """Response model for backlinks."""

    backlinks: list[dict[str, Any]]
    count: int


# Endpoints
@router.post("", response_model=dict[str, Any], status_code=201)
async def create_note(
    note: NoteCreate,
    session_id: SessionID = Depends(get_session_id),
    is_admin: bool = Depends(lambda: False),  # Default: not admin
) -> dict[str, Any]:
    """Create a new note.

    - Admin (with valid passkey): Creates persistent note
    - Visitor (with session ID): Creates ephemeral note
    """
    # Try admin auth (don't raise error if missing)
    try:
        is_admin = verify_admin()
    except HTTPException:
        is_admin = False

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
) -> NotesListResponse:
    """List all accessible notes.

    Returns persistent notes + ephemeral notes for current session.
    """
    # Try admin auth
    try:
        is_admin = verify_admin()
    except HTTPException:
        is_admin = False

    notes = notes_service.list_notes(is_admin=is_admin, session_id=session_id)

    return NotesListResponse(notes=notes, count=len(notes))


@router.get("/{note_id}", response_model=dict[str, Any])
async def get_note(
    note_id: str,
    session_id: SessionID = Depends(get_session_id),
) -> dict[str, Any]:
    """Get a specific note by ID."""
    # Try admin auth
    try:
        is_admin = verify_admin()
    except HTTPException:
        is_admin = False

    note = notes_service.get_note(note_id, is_admin=is_admin, session_id=session_id)

    if not note:
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

    return note


@router.put("/{note_id}", response_model=dict[str, Any])
async def update_note(
    note_id: str,
    note_update: NoteUpdate,
    session_id: SessionID = Depends(get_session_id),
) -> dict[str, Any]:
    """Update a note.

    - Admin can update persistent notes
    - Visitors can update their own ephemeral notes
    """
    # Try admin auth
    try:
        is_admin = verify_admin()
    except HTTPException:
        is_admin = False

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
) -> dict[str, str]:
    """Delete a note.

    - Admin can delete persistent notes
    - Visitors can delete their own ephemeral notes
    """
    # Try admin auth
    try:
        is_admin = verify_admin()
    except HTTPException:
        is_admin = False

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
