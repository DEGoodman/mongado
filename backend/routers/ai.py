"""AI-powered features API routes (Q&A, summaries, suggestions)."""

import logging
from typing import Any

from fastapi import APIRouter

from models import (
    QuestionRequest,
    QuestionResponse,
    SummaryResponse,
    TagSuggestion,
    TagSuggestionsResponse,
    LinkSuggestion,
    LinkSuggestionsResponse,
    WarmupResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ai"])


def create_ai_router(
    ollama_client: Any,
    static_articles: list,
    user_resources_db: list,
    notes_service: Any,
    neo4j_adapter: Any,
) -> APIRouter:
    """Create AI router with dependencies injected.

    Args:
        ollama_client: Ollama client for AI operations
        static_articles: List of static articles
        user_resources_db: User resources database
        notes_service: Notes service for note operations
        neo4j_adapter: Neo4j adapter for embeddings (optional)

    Returns:
        Configured APIRouter with AI endpoints
    """

    @router.post("/ollama/warmup", response_model=WarmupResponse)
    def warmup_ollama() -> WarmupResponse:
        """Warm up the Ollama model by starting the llama runner.

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

    return router
