"""Note-related Pydantic models for Zettelkasten system."""

from typing import Any

from pydantic import BaseModel


class NoteCreate(BaseModel):
    """Request model for creating a note.

    Examples:
        {
            "title": "My First Note",
            "content": "This is a note with a [[wikilink]] to another note.",
            "tags": ["pkm", "learning"]
        }
    """

    title: str | None = None
    content: str
    tags: list[str] = []

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Zettelkasten Method",
                    "content": "Personal knowledge management system based on interconnected atomic notes.\n\nKey principles:\n- One idea per note\n- Link liberally with [[wikilinks]]\n- Emerge structure organically",
                    "tags": ["pkm", "methodology"],
                }
            ]
        }
    }


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


class TagSuggestion(BaseModel):
    """A single tag suggestion."""

    tag: str
    confidence: float
    reason: str


class TagSuggestionsResponse(BaseModel):
    """Response model for tag suggestions."""

    suggestions: list[TagSuggestion]
    count: int


class LinkSuggestion(BaseModel):
    """A single link suggestion."""

    note_id: str
    title: str
    confidence: float
    reason: str


class LinkSuggestionsResponse(BaseModel):
    """Response model for link suggestions."""

    suggestions: list[LinkSuggestion]
    count: int
