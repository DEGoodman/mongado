"""AI-powered features API routes (Q&A, summaries, suggestions)."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from models import (
    QuestionRequest,
    QuestionResponse,
    WarmupResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ai"])


def _get_all_resources(static_articles: list, user_resources_db: list, notes_service: Any) -> list[dict[str, Any]]:
    """Get all searchable resources (articles + notes).

    Notes are normalized to have 'note_id' field to distinguish from articles.
    """
    all_notes = notes_service.list_notes(is_admin=True)

    # Normalize note structure to match article structure for search
    normalized_notes = []
    for note in all_notes:
        normalized_note = {
            "note_id": note.get("id"),  # Keep string ID as note_id
            "title": note.get("title", "Untitled"),
            "content": note.get("content", ""),
            "tags": note.get("tags", []),
            "created_at": note.get("created_at"),
        }
        normalized_notes.append(normalized_note)

    return static_articles + user_resources_db + normalized_notes


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

    @router.post("/ask", response_model=QuestionResponse)
    def ask_question(request: QuestionRequest) -> QuestionResponse:
        """Answer a question using Ollama with hybrid KB + general knowledge.

        First performs semantic search to find relevant articles/notes,
        then uses those as context. Can answer from general knowledge if KB
        doesn't have the answer.
        """
        if not ollama_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="AI Q&A feature is not available. Ollama is not running or not configured.",
            )

        # Find relevant articles and notes
        all_resources = _get_all_resources(static_articles, user_resources_db, notes_service)
        relevant_docs = []

        # Try to use fast semantic search with precomputed embeddings from Neo4j
        if neo4j_adapter.is_available():
            logger.info("Q&A: Using fast semantic search with precomputed embeddings from Neo4j")

            # Fetch precomputed embeddings for articles and notes
            embeddings_data = neo4j_adapter.get_all_embeddings()
            logger.info("Q&A: Fetched %d precomputed embeddings from Neo4j", len(embeddings_data))

            if embeddings_data:
                # Build documents with embeddings
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

                logger.info("Q&A: Matched %d documents with embeddings", len(documents_with_embeddings))

                # Perform fast semantic search
                relevant_docs = ollama_client.semantic_search_with_precomputed_embeddings(
                    request.question, documents_with_embeddings, top_k=5
                )
                logger.info("Q&A: Fast semantic search found %d relevant docs", len(relevant_docs))
            else:
                logger.warning("Q&A: No precomputed embeddings found, falling back to on-demand generation")

        # Fallback: Generate embeddings on-demand (slow but works without Neo4j)
        if not relevant_docs:
            logger.info("Q&A: Using on-demand embedding generation (slower)")
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

    return router
