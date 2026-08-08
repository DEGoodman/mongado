"""Library-related Pydantic models (#294).

The Library is a curated catalog of external resources (books, articles, videos,
docs) Erik values and reaches back to. Entries carry a structured source link and
resource type, plus Erik's own summary. See LibraryEntryDict in domain_types.py.
"""

from typing import Any, Literal

from pydantic import BaseModel

# Allowed resource types (kept in sync with the frontend filter chips).
LibraryEntryType = Literal["book", "article", "video", "doc", "paper", "other"]


class LibraryEntryCreate(BaseModel):
    """Request model for creating a Library entry."""

    title: str
    source_url: str = ""
    author: str = ""
    type: LibraryEntryType = "other"
    summary: str = ""
    tags: list[str] = []

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Exercises in Programming Style",
                    "source_url": "https://www.oreilly.com/library/view/exercises-in-programming/9781482227376/",
                    "author": "Cristina Videira Lopes",
                    "type": "book",
                    "summary": "40 solutions to one computation task, grouped by style. Knowing *when* to apply a style is a skill in itself.",
                    "tags": ["programming", "problem-solving"],
                }
            ]
        }
    }


class LibraryEntryUpdate(BaseModel):
    """Request model for updating a Library entry. Only provided fields change."""

    title: str | None = None
    source_url: str | None = None
    author: str | None = None
    type: LibraryEntryType | None = None
    summary: str | None = None
    tags: list[str] | None = None


class LibraryListResponse(BaseModel):
    """Response model for a list of Library entries with pagination support."""

    entries: list[dict[str, Any]]
    count: int  # Number of entries in current page
    total: int  # Total number of entries (all pages)
    page: int  # Current page number (1-indexed)
    limit: int  # Items per page
    total_pages: int  # Total number of pages
