"""AI-powered features API routes (Q&A, summaries, suggestions)."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from core import ai as ai_core
from models import (
    GPUStatusResponse,
    LinkSuggestion,
    LinkSuggestionsResponse,
    QuestionRequest,
    QuestionResponse,
    TagSuggestion,
    TagSuggestionsResponse,
    WarmupResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ai"])


def _get_all_resources(get_static_articles: Any, get_user_resources_db: Any, notes_service: Any) -> list[dict[str, Any]]:
    """Get all searchable resources (articles + notes).

    Notes are normalized to have 'note_id' field to distinguish from articles.

    Args:
        get_static_articles: Callable that returns current static articles list
        get_user_resources_db: Callable that returns current user resources list
        notes_service: Notes service for note operations
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

    return get_static_articles() + get_user_resources_db() + normalized_notes


def create_ai_router(
    ollama_client: Any,
    get_static_articles: Any,  # Callable that returns current articles list
    get_user_resources_db: Any,  # Callable that returns current user resources
    notes_service: Any,
    neo4j_adapter: Any,
) -> APIRouter:
    """Create AI router with dependencies injected.

    Args:
        ollama_client: Ollama client for AI operations
        get_static_articles: Callable that returns current static articles list
        get_user_resources_db: Callable that returns current user resources list
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

    @router.get("/ollama/gpu-status", response_model=GPUStatusResponse)
    def get_gpu_status() -> GPUStatusResponse:
        """Check if GPU acceleration is available for AI features.

        Returns GPU availability status. When GPU is not available,
        AI generation features (Q&A, summaries, suggestions) will be
        significantly slower (60-120 seconds vs 2-5 seconds).

        Semantic search remains fast even without GPU as it uses
        pre-computed embeddings.
        """
        if not ollama_client.is_available():
            return GPUStatusResponse(
                has_gpu=False,
                message="Ollama is not available. AI features are disabled."
            )

        has_gpu = ollama_client.has_gpu()
        if has_gpu:
            return GPUStatusResponse(
                has_gpu=True,
                message="GPU acceleration is available. AI features will be fast."
            )
        else:
            return GPUStatusResponse(
                has_gpu=False,
                message="Running on CPU only. AI generation features will be slower (60-120s response times)."
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

        # Find relevant articles and notes - get current state dynamically
        all_resources = _get_all_resources(get_static_articles, get_user_resources_db, notes_service)
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

    @router.post("/notes/{note_id}/suggest-tags", response_model=TagSuggestionsResponse)
    def suggest_tags(note_id: str) -> TagSuggestionsResponse:
        """Suggest relevant tags for a note using AI analysis.

        Analyzes note content and suggests 2-4 relevant tags based on:
        - Topic/domain (e.g., "management", "sre", "pkm")
        - Type (e.g., "framework", "concept", "practice")
        - Existing tags in the knowledge base

        Returns empty suggestions if Ollama is unavailable.
        """
        # Get the note
        note = notes_service.get_note(note_id, is_admin=True)
        if not note:
            raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

        # If Ollama unavailable, return empty suggestions
        if not ollama_client.is_available():
            logger.warning("Ollama not available for tag suggestions")
            return TagSuggestionsResponse(suggestions=[], count=0)

        # Get all existing tags from all notes for context
        all_notes = notes_service.list_notes(is_admin=True)
        existing_tags = set()
        for n in all_notes:
            existing_tags.update(n.get("tags", []))

        # Build prompt using pure function
        title = note.get("title", "")
        content = note.get("content", "")
        current_tags = note.get("tags", [])

        prompt = ai_core.build_tag_suggestion_prompt(
            title=title,
            content=content,
            current_tags=current_tags,
            existing_tags=existing_tags
        )

        try:
            # Use qwen2.5:1.5b for instruction-following (excellent at JSON format)
            response_data = ollama_client.client.generate(
                model="qwen2.5:1.5b",
                prompt=prompt,
                options={"num_ctx": 4096}
            )

            response = response_data.get("response", "")
            if not response:
                logger.error("Empty response from Ollama for tag suggestions")
                return TagSuggestionsResponse(suggestions=[], count=0)

            # Parse JSON response using pure function
            suggestions_data = ai_core.parse_json_response(response, expected_type="array")
            if not suggestions_data:
                return TagSuggestionsResponse(suggestions=[], count=0)

            # Convert to TagSuggestion models
            suggestions = [
                TagSuggestion(
                    tag=s["tag"],
                    confidence=s.get("confidence", 0.5),
                    reason=s.get("reason", "")
                )
                for s in suggestions_data
            ]

            # Limit to top 4 suggestions
            suggestions = suggestions[:4]

            logger.info("Generated %d tag suggestions for note %s", len(suggestions), note_id)
            return TagSuggestionsResponse(suggestions=suggestions, count=len(suggestions))

        except Exception as e:
            logger.error("Error generating tag suggestions: %s", e)
            return TagSuggestionsResponse(suggestions=[], count=0)

    @router.post("/notes/{note_id}/suggest-links", response_model=LinkSuggestionsResponse)
    def suggest_links(note_id: str) -> LinkSuggestionsResponse:
        """Suggest related notes that should be linked via wikilinks.

        Analyzes note content and suggests other notes that are conceptually related.
        Returns suggestions with confidence scores and reasoning.

        Returns empty suggestions if Ollama is unavailable or note not found.
        """
        # Get the current note
        note = notes_service.get_note(note_id, is_admin=True)
        if not note:
            raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

        # If Ollama unavailable, return empty suggestions
        if not ollama_client.is_available():
            logger.warning("Ollama not available for link suggestions")
            return LinkSuggestionsResponse(suggestions=[], count=0)

        # Get all other notes and filter candidates using pure function
        all_notes = notes_service.list_notes(is_admin=True)
        existing_links = note.get("links", [])

        candidate_notes = ai_core.filter_link_candidates(
            all_notes=all_notes,
            current_note_id=note_id,
            existing_links=existing_links
        )

        if not candidate_notes:
            logger.info("No candidate notes for link suggestions")
            return LinkSuggestionsResponse(suggestions=[], count=0)

        # Build prompt using pure function
        current_title = note.get("title", note_id)
        current_content = note.get("content", "")

        prompt = ai_core.build_link_suggestion_prompt(
            current_title=current_title,
            current_content=current_content,
            candidate_notes=candidate_notes,
            max_candidates=50
        )

        try:
            # Use qwen2.5:1.5b for structured output
            response_data = ollama_client.client.generate(
                model="qwen2.5:1.5b",
                prompt=prompt,
                options={"num_ctx": 8192}  # Larger context for multiple notes
            )

            response = response_data.get("response", "")
            if not response:
                logger.error("Empty response from Ollama for link suggestions")
                return LinkSuggestionsResponse(suggestions=[], count=0)

            # Parse JSON response using pure function
            suggestions_data = ai_core.parse_json_response(response, expected_type="array")
            if not suggestions_data:
                return LinkSuggestionsResponse(suggestions=[], count=0)

            # Convert to LinkSuggestion models and add titles
            suggestions = []
            note_map = {n["id"]: n for n in candidate_notes}

            for s in suggestions_data:
                note_id_suggestion = s.get("note_id")
                if note_id_suggestion and note_id_suggestion in note_map:
                    suggestions.append(
                        LinkSuggestion(
                            note_id=note_id_suggestion,
                            title=note_map[note_id_suggestion].get("title", "Untitled"),
                            confidence=s.get("confidence", 0.5),
                            reason=s.get("reason", "")
                        )
                    )

            # Limit to top 5 suggestions
            suggestions = suggestions[:5]

            logger.info("Generated %d link suggestions for note %s", len(suggestions), note_id)
            return LinkSuggestionsResponse(suggestions=suggestions, count=len(suggestions))

        except Exception as e:
            logger.error("Error generating link suggestions: %s", e)
            return LinkSuggestionsResponse(suggestions=[], count=0)

    return router
