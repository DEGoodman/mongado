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
from rapidfuzz import fuzz
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from article_loader import load_static_articles
from config import SecretManager, Settings, get_secret_manager, get_settings
from embedding_sync import sync_embeddings_on_startup
from image_optimizer import optimize_image_to_webp
from logging_config import setup_logging
from neo4j_adapter import get_neo4j_adapter
from notes_api import router as notes_router
from ollama_client import get_ollama_client

# Configure logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

# Load settings and initialize services
settings: Settings = get_settings()
secret_manager: SecretManager = get_secret_manager()
ollama_client = get_ollama_client()
neo4j_adapter = get_neo4j_adapter()

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="""
## Mongado API - Personal Knowledge Base

This API provides endpoints for managing a personal knowledge base with:
- **Static Articles**: Read-only markdown articles
- **Notes**: Zettelkasten-style notes with wikilinks and bidirectional linking
- **AI Features**: Semantic search and Q&A powered by Ollama

### Authentication

Some endpoints require admin authentication:
- Use the **Authorize** button (🔓) to add your Bearer token
- Format: `Bearer your-admin-token-here`
- Admin-only features: Create/update/delete persistent notes

### Session Management

For anonymous users (no Bearer token):
- Include `X-Session-ID` header to create ephemeral notes
- Ephemeral notes are session-specific and temporary
""",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Hide schemas by default
        "persistAuthorization": True,  # Remember auth token
    },
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Customize OpenAPI schema to add security definitions
def custom_openapi():
    """Customize OpenAPI schema with security definitions."""
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security scheme for Bearer token
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your admin token (without 'Bearer ' prefix)",
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Log startup information
logger.info("Starting %s v%s", settings.app_name, settings.app_version)
logger.info("1Password integration: %s", "enabled" if secret_manager.is_available() else "disabled")
logger.info("CORS allowed origins: %s", settings.cors_origins_list)


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
    allow_origins=settings.cors_origins_list,
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

# Sync articles to Neo4j and generate embeddings
sync_embeddings_on_startup(static_articles, ollama_client, neo4j_adapter)


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
    """Request model for search."""

    query: str
    top_k: int = 5
    semantic: bool = False  # Use AI semantic search (slower, opt-in)


class SearchResult(BaseModel):
    """A single search result with normalized fields."""

    id: int | str
    type: str  # "article" or "note"
    title: str
    content: str
    score: float  # 1.0 for text search, cosine similarity for semantic


class SearchResponse(BaseModel):
    """Response model for search (both text and semantic)."""

    results: list[SearchResult]
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


class WarmupResponse(BaseModel):
    """Response model for Ollama warmup."""

    success: bool
    message: str


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
    """Upload an image file, optimize to WebP, and return its URL."""
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed.")

    # Generate unique filename for temporary upload
    file_extension = Path(file.filename or "image.jpg").suffix
    temp_filename = f"{uuid.uuid4()}{file_extension}"
    temp_path = UPLOAD_DIR / temp_filename

    # Save file temporarily
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        logger.info("Image uploaded: %s", temp_filename)
    except Exception as e:
        logger.error("Error uploading image: %s", e)
        raise HTTPException(status_code=500, detail="Failed to upload image") from e

    # Optimize to WebP
    webp_filename = f"{uuid.uuid4()}.webp"
    webp_path = UPLOAD_DIR / webp_filename

    try:
        optimized_path = optimize_image_to_webp(
            temp_path,
            webp_path,
            quality=85,  # Good balance of quality and size
            max_width=1200,  # Reasonable max width for web
        )

        if not optimized_path:
            # Optimization failed, use original file
            logger.warning("Image optimization failed, using original: %s", temp_filename)
            image_url = f"/uploads/{temp_filename}"
            return ImageUploadResponse(url=image_url, filename=temp_filename)

        # Delete temporary original file after successful optimization
        temp_path.unlink()
        logger.info("Image optimized to WebP: %s -> %s", temp_filename, webp_filename)

        # Return WebP URL
        image_url = f"/uploads/{webp_filename}"
        return ImageUploadResponse(url=image_url, filename=webp_filename)

    except Exception as e:
        # If optimization fails, clean up temp file and use original
        logger.error("Error optimizing image: %s", e)
        logger.warning("Using original file: %s", temp_filename)
        image_url = f"/uploads/{temp_filename}"
        return ImageUploadResponse(url=image_url, filename=temp_filename)


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


def _fuzzy_match_text(query: str, text: str, threshold: int = 80) -> bool:
    """
    Check if query fuzzy matches the text.

    - Queries < 3 chars: exact substring match only (for terms like "SRE")
    - Queries >= 3 chars: fuzzy match with 80% threshold (handles typos)

    Args:
        query: Search query (lowercase)
        text: Text to search in (lowercase)
        threshold: Minimum similarity score (0-100)

    Returns:
        True if query matches text (exact or fuzzy)
    """
    # Short queries: require exact match (prevents false positives)
    if len(query) < 3:
        return query in text

    # Exact match (fastest path)
    if query in text:
        return True

    # Fuzzy match: check if query is similar to any word in text
    # Only match against words of similar length to avoid false positives
    words = text.split()
    for word in words:
        # Only fuzzy match words that are within 2 chars of query length
        if abs(len(word) - len(query)) <= 2 and fuzz.ratio(query, word) >= threshold:
            return True

    return False


def _normalize_search_result(doc: dict[str, Any], score: float = 1.0) -> SearchResult:
    """Normalize a resource document into a consistent SearchResult."""
    # Determine if this is an article or note
    is_note = "note_id" in doc
    resource_type = "note" if is_note else "article"
    resource_id = doc.get("note_id") if is_note else doc.get("id")

    return SearchResult(
        id=resource_id,
        type=resource_type,
        title=doc.get("title", "Untitled"),
        content=doc.get("content", ""),
        score=score
    )


@app.post("/api/search", response_model=SearchResponse)
def search_resources(request: SearchRequest) -> SearchResponse:
    """
    Search across all resources (articles + notes).

    **Default:** Fast text search with fuzzy matching (instant)
    - Queries < 3 chars: exact match only (e.g., "SRE")
    - Queries >= 3 chars: fuzzy match with 80% threshold (handles typos like "biling" → "billing")

    **Semantic mode:** AI-powered semantic search via Ollama (slower, opt-in)
    - Set semantic=true to use AI embeddings for semantic search
    - Finds conceptually related content even without keyword matches
    - Takes 15-30+ seconds depending on corpus size

    The default text search is instant and works even when Ollama is unavailable
    or slow, making it ideal for the main search UI.
    """
    import time
    start_time = time.time()

    logger.info("Search request received: query=%s, semantic=%s, limit=%s", request.query, request.semantic, request.top_k)
    all_resources = static_articles + user_resources_db

    # Default: Fast text search with fuzzy matching
    if not request.semantic:
        logger.debug("Using fast text search with fuzzy matching")
        query_lower = request.query.lower()
        matching_docs = [
            doc for doc in all_resources
            if _fuzzy_match_text(query_lower, doc.get("content", "").lower())
            or _fuzzy_match_text(query_lower, doc.get("title", "").lower())
        ]
        results = [_normalize_search_result(doc, score=1.0) for doc in matching_docs[:request.top_k]]
        duration = time.time() - start_time
        logger.info("Text search complete: %d results in %.2fs", len(results), duration)
        return SearchResponse(results=results, count=len(results))

    # Semantic mode: Use Ollama for AI-powered search (opt-in)
    logger.info("Using semantic search via Ollama (corpus size: %d)", len(all_resources))

    # Check if Ollama is available
    if not ollama_client.is_available():
        logger.warning("Ollama not available, falling back to text search with fuzzy matching")
        query_lower = request.query.lower()
        matching_docs = [
            doc for doc in all_resources
            if _fuzzy_match_text(query_lower, doc.get("content", "").lower())
            or _fuzzy_match_text(query_lower, doc.get("title", "").lower())
        ]
        results = [_normalize_search_result(doc, score=1.0) for doc in matching_docs[:request.top_k]]
        duration = time.time() - start_time
        logger.info("Fallback text search complete: %d results in %.2fs", len(results), duration)
        return SearchResponse(results=results, count=len(results))

    # Try to use fast semantic search with precomputed embeddings from Neo4j
    if neo4j_adapter.is_available():
        logger.info("Using fast semantic search with precomputed embeddings from Neo4j")

        # Fetch precomputed embeddings for articles and notes
        embeddings_data = neo4j_adapter.get_all_embeddings()
        logger.info("Fetched %d precomputed embeddings from Neo4j", len(embeddings_data))

        if embeddings_data:
            # Build documents with embeddings
            # Need to merge embedding data with full document content
            documents_with_embeddings = []

            for emb_data in embeddings_data:
                doc_id = emb_data["id"]
                doc_type = emb_data["type"]

                # Find the full document from all_resources
                full_doc = next(
                    (doc for doc in all_resources
                     if (doc_type == "Article" and str(doc.get("id")) == doc_id) or
                        (doc_type == "Note" and doc.get("note_id") == doc_id)),
                    None
                )

                if full_doc:
                    # Combine full document with its embedding
                    doc_with_embedding = {**full_doc, "embedding": emb_data["embedding"]}
                    documents_with_embeddings.append(doc_with_embedding)

            logger.info("Matched %d documents with embeddings", len(documents_with_embeddings))

            # Perform fast semantic search
            semantic_results = ollama_client.semantic_search_with_precomputed_embeddings(
                request.query, documents_with_embeddings, request.top_k
            )

            results = [
                _normalize_search_result(doc, score=doc.get("score", 0.0))
                for doc in semantic_results
            ]
            duration = time.time() - start_time
            logger.info("Fast semantic search complete: %d results in %.2fs", len(results), duration)
            return SearchResponse(results=results, count=len(results))
        else:
            logger.warning("No precomputed embeddings found, falling back to on-demand generation")

    # Fallback: Generate embeddings on-demand (slow but works without Neo4j)
    logger.info("Using on-demand embedding generation (slower)")
    semantic_results = ollama_client.semantic_search(request.query, all_resources, request.top_k)
    results = [
        _normalize_search_result(doc, score=doc.get("score", 0.0))
        for doc in semantic_results
    ]
    duration = time.time() - start_time
    logger.info("Semantic search complete: %d results in %.2fs", len(results), duration)
    return SearchResponse(results=results, count=len(results))


@app.post("/api/ask", response_model=QuestionResponse)
def ask_question(request: QuestionRequest) -> QuestionResponse:
    """
    Answer a question using Ollama with hybrid KB + general knowledge.

    First performs semantic search to find relevant articles/notes,
    then uses those as context. Can answer from general knowledge if KB
    doesn't have the answer.
    """
    if not ollama_client.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI Q&A feature is not available. Ollama is not running or not configured.",
        )

    # Find relevant articles
    all_resources = static_articles + user_resources_db
    relevant_docs = ollama_client.semantic_search(request.question, all_resources, top_k=5)

    # Generate answer with hybrid mode (KB + general knowledge)
    answer = ollama_client.ask_question(
        request.question, relevant_docs, allow_general_knowledge=True
    )

    if not answer:
        raise HTTPException(
            status_code=500, detail="Failed to generate answer. Please try again."
        )

    return QuestionResponse(answer=answer, sources=relevant_docs)


@app.post("/api/ollama/warmup", response_model=WarmupResponse)
def warmup_ollama() -> WarmupResponse:
    """
    Warm up the Ollama model by starting the llama runner.

    This endpoint takes ~15-20 seconds to complete, but makes subsequent
    AI requests much faster. Call this when the user opens the Q&A panel
    or knowledge base page.

    **Optimization:** Pre-load the model before users need it.
    """
    if not ollama_client.is_available():
        return WarmupResponse(
            success=False,
            message="Ollama is not available or not configured."
        )

    success = ollama_client.warmup()
    if success:
        return WarmupResponse(
            success=True,
            message="Ollama model warmed up successfully. Subsequent requests will be faster."
        )
    else:
        return WarmupResponse(
            success=False,
            message="Failed to warm up Ollama model. Check logs for details."
        )


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
