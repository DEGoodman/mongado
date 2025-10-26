"""Resource-related Pydantic models for knowledge base entries."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Resource(BaseModel):
    """Resource model for knowledge base entries."""

    id: int | None = None
    title: str
    content: str  # Markdown content (preferred) or plain text
    content_type: str = "markdown"  # "markdown" (default) or "plain"
    url: str | None = None
    tags: list[str] = []
    created_at: datetime | None = None


class ResourceResponse(BaseModel):
    """Response model for resource operations."""

    resource: Resource


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
