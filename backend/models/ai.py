"""AI-related Pydantic models for Q&A, summaries, and concept extraction."""

from typing import Any

from pydantic import BaseModel


class QuestionRequest(BaseModel):
    """Request model for Q&A."""

    question: str


class QuestionResponse(BaseModel):
    """Response model for Q&A."""

    answer: str
    sources: list[dict[str, Any]]


class SummaryResponse(BaseModel):
    """Response model for article/note summary."""

    summary: str
    cached: bool = False  # True if returned from pre-computed cache
    cached_at: float | None = None  # Unix timestamp when cached


class WarmupResponse(BaseModel):
    """Response model for Ollama warmup."""

    success: bool
    message: str
    model: str | None = None  # Which model was warmed up
    context: str | None = None  # The context used (chat, structured, embedding)


class GPUStatusResponse(BaseModel):
    """Response model for GPU availability status."""

    has_gpu: bool
    message: str


class EmbeddingSyncResponse(BaseModel):
    """Response model for embedding sync trigger."""

    success: bool
    message: str
    stats: dict[str, int] | None = None


class ConceptSuggestion(BaseModel):
    """A single concept suggestion extracted from an article."""

    concept: str
    excerpt: str
    confidence: float
    reason: str


class ConceptExtractionResponse(BaseModel):
    """Response model for concept extraction from articles."""

    concepts: list[ConceptSuggestion]
    count: int


class BatchConceptSuggestion(BaseModel):
    """A concept suggestion with source article information."""

    concept: str
    excerpt: str
    confidence: float
    reason: str
    article_ids: list[int]  # Which articles mention this concept
    article_titles: list[str]


class BatchConceptExtractionResponse(BaseModel):
    """Response model for batch concept extraction from all articles."""

    concepts: list[BatchConceptSuggestion]
    count: int
    articles_processed: int
