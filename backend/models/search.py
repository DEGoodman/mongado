"""Search-related Pydantic models."""

from pydantic import BaseModel, field_validator


class SearchRequest(BaseModel):
    """Request model for search."""

    query: str
    top_k: int = 5
    semantic: bool = False  # Use AI semantic search (slower, opt-in)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is not empty."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v


class SearchResult(BaseModel):
    """A single search result with normalized fields."""

    id: int | str
    type: str  # "article" or "note"
    title: str
    content: str
    snippet: str  # Contextual snippet with match highlighted
    score: float  # 1.0 for text search, cosine similarity for semantic


class SearchResponse(BaseModel):
    """Response model for search (both text and semantic)."""

    results: list[SearchResult]
    count: int
