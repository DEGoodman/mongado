"""Mongado API - Personal website backend with Knowledge Base and future features."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from article_loader import load_static_articles
from config import SecretManager, Settings, get_secret_manager, get_settings
# Temporarily disabled - image_optimizer causing import hang
# TODO: Fix Pillow/image import issue
# from image_optimizer import optimize_image_to_webp
from logging_config import setup_logging
from notes_api import router as notes_router
from ollama_client import get_ollama_client

# Configure logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

# Load settings
settings: Settings = get_settings()
secret_manager: SecretManager = get_secret_manager()
ollama_client = get_ollama_client()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

# Log startup information
logger.info("Starting %s v%s", settings.app_name, settings.app_version)
logger.info("1Password integration: %s", "enabled" if secret_manager.is_available() else "disabled")


# Cache control middleware for static assets
class CacheControlMiddleware(BaseHTTPMiddleware):
    """Add cache control headers for static assets and API responses."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process request and add appropriate cache headers."""
        response = await call_next(request)

        # Static assets (images, icons, etc.) - cache for 1 year
        if request.url.path.startswith("/static/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        # Static markdown articles - cache but revalidate
        elif request.url.path.startswith("/static/articles/"):
            response.headers["Cache-Control"] = "public, max-age=3600, must-revalidate"

        # User uploads - cache for 1 day
        elif request.url.path.startswith("/uploads/"):
            response.headers["Cache-Control"] = "public, max-age=86400"

        # API responses - no cache by default (can override per endpoint)
        elif request.url.path.startswith("/api/"):
            # Allow browser to cache list/read operations for 60 seconds
            if request.method == "GET":
                response.headers["Cache-Control"] = "public, max-age=60"
            else:
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

        return response


# Configure middleware (order matters!)
# 1. CORS - must be first
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. GZip compression for all responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 3. Cache control
app.add_middleware(CacheControlMiddleware)

# Include routers
app.include_router(notes_router)

# Create uploads directory for user-uploaded images (temporary storage)
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Static assets directory (checked into source control)
STATIC_DIR = Path(__file__).parent / "static"

# Mount static files
# Static assets (images, icons, etc.) - long cache time
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=False), name="static")

# User uploads - shorter cache time
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Static articles (loaded from files/S3, read-only)
static_articles: list[dict[str, Any]] = []

# User-created resources (in-memory for now, will be DB later)
user_resources_db: list[dict[str, Any]] = []

# Load static articles on startup
static_articles = load_static_articles()
logger.info("Loaded %d static articles", len(static_articles))


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


class ImageUploadResponse(BaseModel):
    """Response model for image upload."""

    url: str
    filename: str


class SearchRequest(BaseModel):
    """Request model for semantic search."""

    query: str
    top_k: int = 5


class SearchResponse(BaseModel):
    """Response model for semantic search."""

    results: list[dict[str, Any]]
    count: int


class QuestionRequest(BaseModel):
    """Request model for Q&A."""

    question: str


class QuestionResponse(BaseModel):
    """Response model for Q&A."""

    answer: str
    sources: list[dict[str, Any]]


class SummaryResponse(BaseModel):
    """Response model for article summary."""

    summary: str


@app.get("/", response_model=StatusResponse)
def read_root() -> StatusResponse:
    """Get API status and information."""
    return StatusResponse(
        message=settings.app_name,
        version=settings.app_version,
        onepassword_enabled=secret_manager.is_available(),
    )


@app.post("/api/upload-image", response_model=ImageUploadResponse)
async def upload_image(file: Annotated[UploadFile, File()]) -> ImageUploadResponse:
    """Upload an image file and return its URL.

    TODO: Re-enable image optimization once Pillow import issue is resolved.
    """
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed.")

    # Generate unique filename
    file_extension = Path(file.filename or "image.jpg").suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename

    # Save file
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        logger.info("Image uploaded successfully: %s", unique_filename)
    except Exception as e:
        logger.error("Error uploading image: %s", e)
        raise HTTPException(status_code=500, detail="Failed to upload image") from e

    # Return URL
    image_url = f"/uploads/{unique_filename}"
    return ImageUploadResponse(url=image_url, filename=unique_filename)


@app.get("/api/resources", response_model=ResourceListResponse)
def get_resources() -> ResourceListResponse:
    """Get all resources (static articles + user-created)."""
    all_resources = static_articles + user_resources_db
    return ResourceListResponse(resources=all_resources)


@app.post("/api/resources", response_model=ResourceResponse, status_code=201)
def create_resource(resource: Resource) -> ResourceResponse:
    """Create a new user resource."""
    # Generate ID based on total resources (static + user)
    total_resources = len(static_articles) + len(user_resources_db)
    resource.id = total_resources + 1
    resource.created_at = datetime.now()
    user_resources_db.append(resource.model_dump())
    return ResourceResponse(resource=resource)


@app.get("/api/resources/{resource_id}", response_model=ResourceResponse)
def get_resource(resource_id: int) -> ResourceResponse:
    """Get a specific resource by ID (static or user-created)."""
    all_resources = static_articles + user_resources_db
    for resource in all_resources:
        if resource["id"] == resource_id:
            return ResourceResponse(resource=Resource(**resource))
    raise HTTPException(status_code=404, detail="Resource not found")


@app.delete("/api/resources/{resource_id}")
def delete_resource(resource_id: int) -> dict[str, str]:
    """Delete a user resource by ID (static articles cannot be deleted)."""
    global user_resources_db

    # Check if it's a static article (read-only)
    for article in static_articles:
        if article["id"] == resource_id:
            raise HTTPException(
                status_code=403, detail="Cannot delete static article. Static articles are read-only."
            )

    # Try to delete from user resources
    initial_length = len(user_resources_db)
    user_resources_db = [r for r in user_resources_db if r["id"] != resource_id]

    if len(user_resources_db) == initial_length:
        raise HTTPException(status_code=404, detail="Resource not found")

    return {"message": "Resource deleted"}


@app.post("/api/search", response_model=SearchResponse)
def semantic_search(request: SearchRequest) -> SearchResponse:
    """
    Perform semantic search across all resources using Ollama.

    If Ollama is not available, falls back to basic text search.
    """
    if not ollama_client.is_available():
        logger.warning("Ollama not available, performing basic text search")

    all_resources = static_articles + user_resources_db
    results = ollama_client.semantic_search(request.query, all_resources, request.top_k)

    return SearchResponse(results=results, count=len(results))


@app.post("/api/ask", response_model=QuestionResponse)
def ask_question(request: QuestionRequest) -> QuestionResponse:
    """
    Answer a question based on the knowledge base using Ollama.

    First performs semantic search to find relevant articles,
    then uses those as context to answer the question.
    """
    if not ollama_client.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI Q&A feature is not available. Ollama is not running or not configured.",
        )

    # Find relevant articles
    all_resources = static_articles + user_resources_db
    relevant_docs = ollama_client.semantic_search(request.question, all_resources, top_k=5)

    # Generate answer
    answer = ollama_client.ask_question(request.question, relevant_docs)

    if not answer:
        raise HTTPException(
            status_code=500, detail="Failed to generate answer. Please try again."
        )

    return QuestionResponse(answer=answer, sources=relevant_docs)


@app.get("/api/articles/{resource_id}/summary", response_model=SummaryResponse)
def get_article_summary(resource_id: int) -> SummaryResponse:
    """Generate an AI summary of a specific article using Ollama."""
    if not ollama_client.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI summary feature is not available. Ollama is not running or not configured.",
        )

    # Find the article
    all_resources = static_articles + user_resources_db
    article = None
    for resource in all_resources:
        if resource["id"] == resource_id:
            article = resource
            break

    if not article:
        raise HTTPException(status_code=404, detail="Resource not found")

    # Generate summary
    summary = ollama_client.summarize_article(article["content"])

    if not summary:
        raise HTTPException(
            status_code=500, detail="Failed to generate summary. Please try again."
        )

    return SummaryResponse(summary=summary)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
