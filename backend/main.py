"""Mongado API - Personal website backend with Knowledge Base and future features."""

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from adapters.article_loader import load_static_articles
from adapters.neo4j import get_neo4j_adapter
from auth import verify_admin
from config import SecretManager, Settings, get_secret_manager, get_settings
from dependencies import get_neo4j, get_ollama, set_static_articles, set_user_resources
from embedding_sync import sync_embeddings_on_startup
from image_optimizer import optimize_image_to_webp
from logging_config import setup_logging
from models import (
    EmbeddingSyncResponse,
    HealthResponse,
    ImageUploadResponse,
    ReadyResponse,
    StatusResponse,
)
from notes_service import get_notes_service
from ollama_client import get_ollama_client
from routers.admin import create_admin_router
from routers.ai import router as ai_router
from routers.articles import router as articles_router
from routers.notes import router as notes_router
from routers.search import router as search_router
from routers.templates import router as templates_router

# Configure logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

# Load settings and initialize services
settings: Settings = get_settings()
secret_manager: SecretManager = get_secret_manager()
ollama_client = get_ollama_client()
neo4j_adapter = get_neo4j_adapter()
notes_service = get_notes_service()

# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Static articles (loaded from files/S3, read-only)
static_articles: list[dict[str, Any]] = []

# User-created resources (in-memory for now, will be DB later)
user_resources_db: list[dict[str, Any]] = []

# Readiness state (becomes True after embedding sync completes)
_embedding_sync_ready: bool = False
_embedding_sync_task: asyncio.Task[None] | None = None


async def _sync_embeddings_background() -> None:
    """Run embedding sync in background during startup."""
    global _embedding_sync_ready

    try:
        # Run the sync in a thread pool (it's blocking I/O)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, sync_embeddings_on_startup, static_articles, ollama_client, neo4j_adapter
        )
        _embedding_sync_ready = True
        logger.info("Background embedding sync completed - app is fully ready")
    except Exception as e:
        logger.error("Background embedding sync failed: %s", e)
        # Don't set ready flag, but app is still healthy


def _auto_seed_notes_if_empty() -> None:
    """Auto-seed test notes if database is empty (dev mode only)."""
    if not settings.debug:
        return

    if not neo4j_adapter.is_available():
        logger.warning("Neo4j not available - skipping auto-seed check")
        return

    note_count = neo4j_adapter.get_note_count()
    if note_count > 0:
        logger.info("Found %d existing notes - skipping auto-seed", note_count)
        return

    logger.info("No notes found in dev mode - auto-seeding test data...")
    try:
        from scripts.seed_test_notes import seed_notes

        seed_notes()
        new_count = neo4j_adapter.get_note_count()
        logger.info("✅ Auto-seeded %d test notes", new_count)
    except Exception as e:
        logger.error("Failed to auto-seed notes: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    global static_articles, _embedding_sync_task, _embedding_sync_ready

    # Startup
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info(
        "1Password integration: %s", "enabled" if secret_manager.is_available() else "disabled"
    )
    logger.info("CORS allowed origins: %s", settings.cors_origins_list)

    # Load static articles (fast) and set in dependency system
    static_articles = load_static_articles()
    set_static_articles(static_articles)
    set_user_resources(user_resources_db)
    logger.info("Loaded %d static articles", len(static_articles))

    # Auto-seed test notes if database is empty (dev mode only)
    _auto_seed_notes_if_empty()

    # Conditionally start embedding sync in background (non-blocking)
    if settings.sync_embeddings_on_startup:
        logger.info("Starting background embedding sync (SYNC_EMBEDDINGS_ON_STARTUP=true)...")
        _embedding_sync_task = asyncio.create_task(_sync_embeddings_background())
    else:
        logger.info("Skipping embedding sync on startup (SYNC_EMBEDDINGS_ON_STARTUP=false)")
        logger.info("Embeddings will be synced via: POST /api/admin/sync-embeddings")
        # Mark as ready immediately since we're not syncing
        _embedding_sync_ready = True

    # App is healthy immediately (embedding sync runs in background if enabled)

    yield

    # Shutdown (nothing to do currently)


app = FastAPI(
    lifespan=lifespan,
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
- Admin-only features: Create/update/delete notes
""",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Hide schemas by default
        "persistAuthorization": True,  # Remember auth token
    },
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]


# Cache control middleware for static assets
class CacheControlMiddleware(BaseHTTPMiddleware):
    """Add cache control headers for static assets and API responses."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process request and add appropriate cache headers."""
        response: Response = await call_next(request)

        # Static assets (images, icons, etc.) - cache for 1 year
        if request.url.path.startswith("/static/assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        # Static markdown articles - cache but revalidate
        elif request.url.path.startswith("/static/articles/"):
            response.headers["Cache-Control"] = "public, max-age=3600, must-revalidate"

        # User uploads - cache for 1 day
        elif request.url.path.startswith("/uploads/"):
            response.headers["Cache-Control"] = "public, max-age=86400"

        # API responses - respect explicit cache headers, add defaults otherwise
        elif request.url.path.startswith("/api/") and "Cache-Control" not in response.headers:
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

# Create and include domain routers
# AI, Notes, Search, and Articles routers use FastAPI Depends() - no factory needed
app.include_router(ai_router)
app.include_router(notes_router)
app.include_router(search_router)
app.include_router(articles_router)
app.include_router(templates_router)

admin_router = create_admin_router(neo4j_adapter=neo4j_adapter)
app.include_router(admin_router)

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


@app.get("/", response_model=StatusResponse)
def read_root() -> StatusResponse:
    """Get API status and information."""
    return StatusResponse(
        message=settings.app_name,
        version=settings.app_version,
        onepassword_enabled=secret_manager.is_available(),
    )


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    Liveness probe - checks if the application is alive and can serve requests.

    This endpoint returns 200 immediately after the app starts, even if
    background tasks (like embedding sync) are still running.

    Use this for:
    - Kubernetes liveness probes
    - Load balancer health checks
    - Deployment verification
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
    )


@app.get("/ready", response_model=ReadyResponse)
def readiness_check() -> ReadyResponse:
    """
    Readiness probe - checks if the application is fully ready to handle traffic.

    This endpoint returns ready=True only after all background initialization
    tasks (like embedding sync) have completed.

    Use this for:
    - Kubernetes readiness probes
    - Waiting for full initialization before sending traffic
    - Monitoring background task completion

    Note: The app is still healthy and functional even if ready=False.
    Embedding sync runs in the background and search will work with cached embeddings.
    """
    return ReadyResponse(
        ready=_embedding_sync_ready,
        embedding_sync_complete=_embedding_sync_ready,
        message="App is fully ready"
        if _embedding_sync_ready
        else "App is healthy, embedding sync in progress",
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


# Article CRUD and AI features moved to routers/articles.py
# Note CRUD and features moved to routers/notes.py
# Search and Q&A routes moved to routers/search.py and routers/ai.py


@app.post("/api/admin/sync-embeddings", response_model=EmbeddingSyncResponse)
def trigger_embedding_sync(
    _admin: Annotated[bool, Depends(verify_admin)],
    neo4j: Annotated[Any, Depends(get_neo4j)],
    ollama: Annotated[Any, Depends(get_ollama)],
) -> EmbeddingSyncResponse:
    """
    Manually trigger embedding sync for all articles and notes (admin only).

    This endpoint allows admins to sync embeddings on-demand without restarting
    the application. Useful for:
    - Deploying new articles without setting SYNC_EMBEDDINGS_ON_STARTUP
    - Regenerating embeddings after model changes
    - Manual recovery if sync failed during startup

    Requires authentication via Bearer token in Authorization header.
    """
    if not neo4j.is_available():
        return EmbeddingSyncResponse(
            success=False, message="Neo4j not available - cannot sync embeddings", stats=None
        )

    if not ollama.is_available():
        return EmbeddingSyncResponse(
            success=False, message="Ollama not available - cannot generate embeddings", stats=None
        )

    logger.info("Admin triggered manual embedding sync")

    try:
        # Import here to avoid circular dependency
        from embedding_sync import sync_articles_to_neo4j, sync_embeddings

        # Sync articles to Neo4j first
        created, updated = sync_articles_to_neo4j(static_articles, neo4j)
        logger.info("Articles synced: %d created, %d updated", created, updated)

        # Generate embeddings for anything that needs it
        stats = sync_embeddings(neo4j, ollama)

        message = (
            f"Sync complete: {stats['articles_processed']} articles, "
            f"{stats['notes_processed']} notes processed. "
            f"{stats['embeddings_generated']} embeddings generated, "
            f"{stats['embeddings_cached']} cached."
        )

        logger.info("Manual embedding sync complete: %s", message)

        return EmbeddingSyncResponse(success=True, message=message, stats=stats)

    except Exception as e:
        logger.error("Manual embedding sync failed: %s", e)
        return EmbeddingSyncResponse(success=False, message=f"Sync failed: {str(e)}", stats=None)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
