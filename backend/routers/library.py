"""Library API routes (curated resource catalog, #294).

Uses FastAPI dependency injection for testability (override get_library in tests).
Mirrors the notes router: public reads, admin-gated writes, server-rendered HTML
for the summary so the frontend needs no markdown pipeline.
"""

import logging
import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth import require_scope
from core.markdown_renderer import render_markdown_to_html
from dependencies import get_library
from models import LibraryEntryCreate, LibraryEntryUpdate, LibraryListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/library", tags=["library"])

# Rate limiter - disabled in tests
limiter = Limiter(key_func=get_remote_address, enabled=os.getenv("TESTING") != "1")

LibraryDep = Annotated[Any, Depends(get_library)]

# Write access: a passkey session, an admin:* token, or a library:write token (#300)
LibraryWriter = Annotated[dict[str, Any], Depends(require_scope("library:write"))]


def _with_html_summary(entry: dict[str, Any]) -> dict[str, Any]:
    """Attach server-rendered HTML for the summary (mirrors notes, #233).

    On render failure the entry is returned without html_summary and the
    frontend falls back to plain-text display.
    """
    try:
        entry["html_summary"] = render_markdown_to_html(entry.get("summary", ""))
    except Exception:
        logger.warning("Failed to render HTML for library entry %s", entry.get("id"), exc_info=True)
    return entry


@router.get("", response_model=LibraryListResponse)
async def list_library_entries(
    library: LibraryDep,
    type: str | None = None,
    tag: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> LibraryListResponse:
    """List Library entries, newest first, with optional filters and pagination.

    Query Parameters:
        type: Filter by resource type (book/article/video/doc/paper/other)
        tag: Filter by tag (entries containing this tag)
        page: Page number (1-indexed, default: 1)
        limit: Items per page (default: 20, max: 100)
    """
    page = max(1, page)
    limit = min(max(1, limit), 100)

    all_entries = library.list_entries(type=type, tag=tag)

    total = len(all_entries)
    total_pages = (total + limit - 1) // limit
    start_idx = (page - 1) * limit
    paginated = all_entries[start_idx : start_idx + limit]

    return LibraryListResponse(
        entries=paginated,
        count=len(paginated),
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/{entry_id}", response_model=dict[str, Any])
async def get_library_entry(entry_id: str, library: LibraryDep) -> dict[str, Any]:
    """Get a single Library entry by ID."""
    entry: dict[str, Any] | None = library.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Library entry '{entry_id}' not found")
    return _with_html_summary(entry)


@router.post("", response_model=dict[str, Any], status_code=201)
@limiter.limit("10/minute")
async def create_library_entry(
    request: Request,
    entry: LibraryEntryCreate,
    _admin: LibraryWriter,
    library: LibraryDep,
) -> dict[str, Any]:
    """Create a new Library entry (admin only)."""
    created: dict[str, Any] = library.create_entry(
        title=entry.title,
        source_url=entry.source_url,
        author=entry.author,
        type=entry.type,
        summary=entry.summary,
        tags=entry.tags,
    )
    return _with_html_summary(created)


@router.put("/{entry_id}", response_model=dict[str, Any])
async def update_library_entry(
    entry_id: str,
    entry_update: LibraryEntryUpdate,
    _admin: LibraryWriter,
    library: LibraryDep,
) -> dict[str, Any]:
    """Update a Library entry (admin only). Only provided fields change."""
    updated: dict[str, Any] | None = library.update_entry(
        entry_id=entry_id,
        title=entry_update.title,
        source_url=entry_update.source_url,
        author=entry_update.author,
        type=entry_update.type,
        summary=entry_update.summary,
        tags=entry_update.tags,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Library entry '{entry_id}' not found")
    return _with_html_summary(updated)


@router.delete("/{entry_id}")
async def delete_library_entry(
    entry_id: str,
    _admin: LibraryWriter,
    library: LibraryDep,
) -> dict[str, str]:
    """Delete a Library entry (admin only)."""
    deleted = library.delete_entry(entry_id=entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Library entry '{entry_id}' not found")
    return {"message": f"Library entry '{entry_id}' deleted successfully"}
