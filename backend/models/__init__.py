"""Pydantic models for API requests and responses."""

from models.admin import (
    BackupCreateResponse,
    BackupInfo,
    BackupListResponse,
    DatabaseHealthResponse,
    RestoreRequest,
    RestoreResponse,
)
from models.ai import (
    BatchConceptExtractionResponse,
    BatchConceptSuggestion,
    ConceptExtractionResponse,
    ConceptSuggestion,
    EmbeddingSyncResponse,
    GPUStatusResponse,
    QuestionRequest,
    QuestionResponse,
    SummaryResponse,
    WarmupResponse,
)
from models.note import (
    BacklinksResponse,
    LinkSuggestion,
    LinkSuggestionsResponse,
    NoteCreate,
    NoteResponse,
    NotesListResponse,
    NoteUpdate,
    TagSuggestion,
    TagSuggestionsResponse,
)
from models.resource import (
    ArticleMetadata,
    ArticleMetadataListResponse,
    HealthResponse,
    ImageUploadResponse,
    ReadyResponse,
    Resource,
    ResourceListResponse,
    ResourceResponse,
    StatusResponse,
)
from models.search import SearchRequest, SearchResponse, SearchResult

__all__ = [
    # Admin models
    "BackupCreateResponse",
    "BackupInfo",
    "BackupListResponse",
    "DatabaseHealthResponse",
    "RestoreRequest",
    "RestoreResponse",
    # AI models
    "BatchConceptExtractionResponse",
    "BatchConceptSuggestion",
    "ConceptExtractionResponse",
    "ConceptSuggestion",
    "EmbeddingSyncResponse",
    "GPUStatusResponse",
    "QuestionRequest",
    "QuestionResponse",
    "SummaryResponse",
    "WarmupResponse",
    # Note models
    "BacklinksResponse",
    "LinkSuggestion",
    "LinkSuggestionsResponse",
    "NoteCreate",
    "NoteResponse",
    "NotesListResponse",
    "NoteUpdate",
    "TagSuggestion",
    "TagSuggestionsResponse",
    # Resource models
    "ArticleMetadata",
    "ArticleMetadataListResponse",
    "HealthResponse",
    "ImageUploadResponse",
    "ReadyResponse",
    "Resource",
    "ResourceListResponse",
    "ResourceResponse",
    "StatusResponse",
    # Search models
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
]
