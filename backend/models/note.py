"""Note-related Pydantic models for Zettelkasten system."""

from typing import Any

from pydantic import BaseModel


class NoteCreate(BaseModel):
    """Request model for creating a note.

    Examples:
        {
            "title": "My First Note",
            "content": "This is a note with a [[wikilink]] to another note.",
            "tags": ["pkm", "learning"],
            "is_reference": false
        }
    """

    title: str | None = None
    content: str
    tags: list[str] = []
    is_reference: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Zettelkasten Method",
                    "content": "Personal knowledge management system based on interconnected atomic notes.\n\nKey principles:\n- One idea per note\n- Link liberally with [[wikilinks]]\n- Emerge structure organically",
                    "tags": ["pkm", "methodology"],
                    "is_reference": False,
                }
            ]
        }
    }


class NoteUpdate(BaseModel):
    """Request model for updating a note."""

    title: str | None = None
    content: str
    tags: list[str] | None = None
    is_reference: bool | None = None


class NoteResponse(BaseModel):
    """Response model for a single note."""

    id: str
    title: str | None
    content: str
    author: str
    tags: list[str]
    created_at: str | float
    updated_at: str | float
    links: list[str]
    is_reference: bool


class NoteListItem(BaseModel):
    """Lightweight note for list views - includes preview, not full content.

    Optimized for list displays where full content is not needed.
    Content is truncated to ~200 characters for preview.
    Excludes embeddings to reduce payload size (~6KB per note).
    """

    id: str
    title: str | None
    content_preview: str  # First 200 chars of content
    author: str
    tags: list[str]
    created_at: str | float
    is_reference: bool
    link_count: int  # Number of outbound links


class NoteMinimal(BaseModel):
    """Minimal note for autocomplete, graph nodes.

    Ultra-lightweight response for use cases that only need
    basic identification: autocomplete widgets, graph visualization.
    """

    id: str
    title: str | None


class NoteWithEmbedding(NoteResponse):
    """Full note + embedding (for AI search only).

    Extends NoteResponse with embedding data. Only used for
    semantic search where embeddings are needed for similarity
    calculations. Frontend should never request this.
    """

    embedding: list[float]
    embedding_model: str | None = None
    embedding_version: int | None = None


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
