"""Resource-related Pydantic models for knowledge base entries."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ArticleMetadata(BaseModel):
    """Lightweight metadata model for article list views (excludes content)."""

    id: int | None = None
    title: str
    summary: str | None = None  # Brief 1-2 sentence description
    url: str | None = None
    tags: list[str] = []
    draft: bool | None = None  # True for draft articles (hidden in production)
    published_date: str | None = None  # ISO 8601 date string
    updated_date: str | None = None  # ISO 8601 date string
    created_at: datetime | None = None


class Resource(BaseModel):
    """Resource model for knowledge base entries."""

    id: int | None = None
    title: str
    summary: str | None = None  # Brief 1-2 sentence description
    content: str  # Markdown content (fallback) or plain text
    html_content: str | None = None  # Pre-rendered HTML (preferred for performance)
    content_type: str = "markdown"  # "markdown" (default) or "plain"
    url: str | None = None
    tags: list[str] = []
    draft: bool | None = None  # True for draft articles (hidden in production)
    published_date: str | None = None  # ISO 8601 date string
    updated_date: str | None = None  # ISO 8601 date string
    created_at: datetime | None = None


class ResourceResponse(BaseModel):
    """Response model for resource operations."""

    resource: Resource


class ArticleMetadataListResponse(BaseModel):
    """Response model for listing article metadata (without content)."""

    resources: list[ArticleMetadata]


class ResourceListResponse(BaseModel):
    """Response model for listing resources."""

    resources: list[dict[str, Any]]


class StatusResponse(BaseModel):
    """Response model for status endpoint."""

    message: str
    version: str
    onepassword_enabled: bool  # Changed from "1password_enabled" for valid Python identifier


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str  # "healthy"
    version: str


class ReadyResponse(BaseModel):
    """Response model for readiness check endpoint."""

    ready: bool
    embedding_sync_complete: bool
    message: str


class ImageUploadResponse(BaseModel):
    """Response model for image upload."""

    url: str
    filename: str
