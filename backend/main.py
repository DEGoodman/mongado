"""Knowledge Base API - Main application module."""

import logging
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import SecretManager, Settings, get_secret_manager, get_settings
from logging_config import setup_logging

# Configure logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

# Load settings
settings: Settings = get_settings()
secret_manager: SecretManager = get_secret_manager()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

# Log startup information
logger.info("Starting %s v%s", settings.app_name, settings.app_version)
logger.info("1Password integration: %s", "enabled" if secret_manager.is_available() else "disabled")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (will be replaced with database later)
# Using list[dict] for now, will be replaced with proper DB models
resources_db: list[dict[str, Any]] = []


class Resource(BaseModel):
    """Resource model for knowledge base entries."""

    id: int | None = None
    title: str
    content: str
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


@app.get("/", response_model=StatusResponse)
def read_root() -> StatusResponse:
    """Get API status and information."""
    return StatusResponse(
        message=settings.app_name,
        version=settings.app_version,
        onepassword_enabled=secret_manager.is_available(),
    )


@app.get("/api/resources", response_model=ResourceListResponse)
def get_resources() -> ResourceListResponse:
    """Get all resources."""
    return ResourceListResponse(resources=resources_db)


@app.post("/api/resources", response_model=ResourceResponse, status_code=201)
def create_resource(resource: Resource) -> ResourceResponse:
    """Create a new resource."""
    resource.id = len(resources_db) + 1
    resource.created_at = datetime.now()
    resources_db.append(resource.model_dump())
    return ResourceResponse(resource=resource)


@app.get("/api/resources/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int) -> ResourceResponse:
    """Get a specific resource by ID."""
    for resource in resources_db:
        if resource["id"] == resource_id:
            return ResourceResponse(resource=Resource(**resource))
    raise HTTPException(status_code=404, detail="Resource not found")


@app.delete("/api/resources/{resource_id}")
def delete_resource(resource_id: int) -> dict[str, str]:
    """Delete a resource by ID."""
    global resources_db
    initial_length = len(resources_db)
    resources_db = [r for r in resources_db if r["id"] != resource_id]

    if len(resources_db) == initial_length:
        raise HTTPException(status_code=404, detail="Resource not found")

    return {"message": "Resource deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
