"""AI-powered features API routes (Q&A, summaries, suggestions).

Uses FastAPI dependency injection for testability. Dependencies can be
overridden in tests using app.dependency_overrides.
"""

import json
import logging
from collections.abc import Generator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from core import ai as ai_core
from dependencies import get_neo4j, get_notes, get_ollama, get_static_articles, get_user_resources
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


def _get_all_resources(
    static_articles: list[dict[str, Any]], user_resources: list[dict[str, Any]], notes_service: Any
) -> list[dict[str, Any]]:
    """Get all searchable resources (articles + notes).

    Notes are normalized to have 'note_id' field to distinguish from articles.
    """
    all_notes = notes_service.list_notes()

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

    result: list[dict[str, Any]] = static_articles + user_resources + normalized_notes
    return result


# Type aliases for cleaner signatures
OllamaDep = Annotated[Any, Depends(get_ollama)]
NotesDep = Annotated[Any, Depends(get_notes)]
Neo4jDep = Annotated[Any, Depends(get_neo4j)]
ArticlesDep = Annotated[list[dict[str, Any]], Depends(get_static_articles)]
UserResourcesDep = Annotated[list[dict[str, Any]], Depends(get_user_resources)]


@router.post("/ollama/warmup", response_model=WarmupResponse)
def warmup_ollama(ollama: OllamaDep) -> WarmupResponse:
    """Warm up the Ollama model by starting the llama runner.

    This endpoint takes ~15-20 seconds to complete, but makes subsequent
    AI requests much faster. Call this when the user opens the Q&A panel
    or knowledge base page.

    **Optimization:** Pre-load the model before users need it.
    """
    if not ollama.is_available():
        return WarmupResponse(success=False, message="Ollama is not available or not configured.")

    success = ollama.warmup()
    if success:
        return WarmupResponse(
            success=True,
            message="Ollama model warmed up successfully. Subsequent requests will be faster.",
        )
    else:
        return WarmupResponse(
            success=False, message="Failed to warm up Ollama model. Check logs for details."
        )


@router.get("/ollama/gpu-status", response_model=GPUStatusResponse)
def get_gpu_status(ollama: OllamaDep) -> GPUStatusResponse:
    """Check if GPU acceleration is available for AI features.

    Returns GPU availability status. When GPU is not available,
    AI generation features (Q&A, summaries, suggestions) will be
    significantly slower (60-120 seconds vs 2-5 seconds).

    Semantic search remains fast even without GPU as it uses
    pre-computed embeddings.
    """
    if not ollama.is_available():
        return GPUStatusResponse(
            has_gpu=False, message="Ollama is not available. AI features are disabled."
        )

    has_gpu = ollama.has_gpu()
    if has_gpu:
        return GPUStatusResponse(
            has_gpu=True, message="GPU acceleration is available. AI features will be fast."
        )
    else:
        return GPUStatusResponse(
            has_gpu=False,
            message="Running on CPU only. AI generation features will be slower (60-120s response times).",
        )


@router.post("/ask", response_model=QuestionResponse)
def ask_question(
    request: QuestionRequest,
    ollama: OllamaDep,
    notes_service: NotesDep,
    neo4j: Neo4jDep,
    static_articles: ArticlesDep,
    user_resources: UserResourcesDep,
) -> QuestionResponse:
    """Answer a question using Ollama with hybrid KB + general knowledge.

    First performs semantic search to find relevant articles/notes,
    then uses those as context. Can answer from general knowledge if KB
    doesn't have the answer.
    """
    if not ollama.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI Q&A feature is not available. Ollama is not running or not configured.",
        )

    # Find relevant articles and notes
    all_resources = _get_all_resources(static_articles, user_resources, notes_service)
    relevant_docs = []

    # Try to use fast semantic search with precomputed embeddings from Neo4j
    if neo4j.is_available():
        logger.info("Q&A: Using fast semantic search with precomputed embeddings from Neo4j")

        # Fetch precomputed embeddings for articles and notes
        embeddings_data = neo4j.get_all_embeddings()
        logger.info("Q&A: Fetched %d precomputed embeddings from Neo4j", len(embeddings_data))

        if embeddings_data:
            # Build documents with embeddings
            documents_with_embeddings = []

            for emb_data in embeddings_data:
                doc_id = emb_data["id"]
                doc_type = emb_data["type"]

                # Find the full document from all_resources
                full_doc = next(
                    (
                        doc
                        for doc in all_resources
                        if (doc_type == "Article" and str(doc.get("id")) == doc_id)
                        or (doc_type == "Note" and doc.get("note_id") == doc_id)
                    ),
                    None,
                )

                if full_doc:
                    # Combine full document with its embedding
                    doc_with_embedding = {**full_doc, "embedding": emb_data["embedding"]}
                    documents_with_embeddings.append(doc_with_embedding)

            logger.info("Q&A: Matched %d documents with embeddings", len(documents_with_embeddings))

            # Perform fast semantic search
            relevant_docs = ollama.semantic_search_with_precomputed_embeddings(
                request.question, documents_with_embeddings, top_k=5
            )
            logger.info("Q&A: Fast semantic search found %d relevant docs", len(relevant_docs))
        else:
            logger.warning(
                "Q&A: No precomputed embeddings found, falling back to on-demand generation"
            )

    # Fallback: Generate embeddings on-demand (slow but works without Neo4j)
    if not relevant_docs:
        logger.info("Q&A: Using on-demand embedding generation (slower)")
        relevant_docs = ollama.semantic_search(request.question, all_resources, top_k=5)

    # Generate answer with hybrid mode (KB + general knowledge)
    answer = ollama.ask_question(request.question, relevant_docs, allow_general_knowledge=True)

    if not answer:
        raise HTTPException(status_code=500, detail="Failed to generate answer. Please try again.")

    return QuestionResponse(answer=answer, sources=relevant_docs)


@router.post("/notes/{note_id}/suggest-tags", response_model=TagSuggestionsResponse)
def suggest_tags(
    note_id: str,
    ollama: OllamaDep,
    notes_service: NotesDep,
) -> TagSuggestionsResponse:
    """Suggest relevant tags for a note using AI analysis.

    Analyzes note content and suggests 2-4 relevant tags based on:
    - Topic/domain (e.g., "management", "sre", "pkm")
    - Type (e.g., "framework", "concept", "practice")
    - Existing tags in the knowledge base

    Returns empty suggestions if Ollama is unavailable.
    """
    # Get the note
    note = notes_service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

    # If Ollama unavailable, return empty suggestions
    if not ollama.is_available():
        logger.warning("Ollama not available for tag suggestions")
        return TagSuggestionsResponse(suggestions=[], count=0)

    # Get all existing tags from all notes for context
    all_notes = notes_service.list_notes()
    existing_tags = set()
    for n in all_notes:
        existing_tags.update(n.get("tags", []))

    # Build prompt using pure function
    title = note.get("title", "")
    content = note.get("content", "")
    current_tags = note.get("tags", [])

    prompt = ai_core.build_tag_suggestion_prompt(
        title=title, content=content, current_tags=current_tags, existing_tags=existing_tags
    )

    try:
        # Use structured output model (qwen2.5:1.5b) for reliable JSON
        response_data = ollama.client.generate(
            model=ollama.structured_model, prompt=prompt, options={"num_ctx": 4096}
        )

        response = response_data.get("response", "")
        if not response:
            logger.error("Empty response from Ollama for tag suggestions")
            return TagSuggestionsResponse(suggestions=[], count=0)

        # Parse JSON response using pure function
        suggestions_data = ai_core.parse_json_response(response, expected_type="array")
        if not suggestions_data or not isinstance(suggestions_data, list):
            return TagSuggestionsResponse(suggestions=[], count=0)

        # Convert to TagSuggestion models
        suggestions = [
            TagSuggestion(
                tag=s["tag"], confidence=s.get("confidence", 0.5), reason=s.get("reason", "")
            )
            for s in suggestions_data
            if isinstance(s, dict)
        ]

        # Limit to top 4 suggestions
        suggestions = suggestions[:4]

        logger.info("Generated %d tag suggestions for note %s", len(suggestions), note_id)
        return TagSuggestionsResponse(suggestions=suggestions, count=len(suggestions))

    except Exception as e:
        logger.error("Error generating tag suggestions: %s", e)
        return TagSuggestionsResponse(suggestions=[], count=0)


@router.post("/notes/{note_id}/suggest-links", response_model=LinkSuggestionsResponse)
def suggest_links(
    note_id: str,
    ollama: OllamaDep,
    notes_service: NotesDep,
) -> LinkSuggestionsResponse:
    """Suggest related notes that should be linked via wikilinks.

    Analyzes note content and suggests other notes that are conceptually related.
    Returns suggestions with confidence scores and reasoning.

    Returns empty suggestions if Ollama is unavailable or note not found.
    """
    # Get the current note
    note = notes_service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

    # If Ollama unavailable, return empty suggestions
    if not ollama.is_available():
        logger.warning("Ollama not available for link suggestions")
        return LinkSuggestionsResponse(suggestions=[], count=0)

    # Get all other notes and filter candidates using pure function
    all_notes = notes_service.list_notes()
    existing_links = note.get("links", [])

    candidate_notes = ai_core.filter_link_candidates(
        all_notes=all_notes, current_note_id=note_id, existing_links=existing_links
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
        max_candidates=50,
    )

    try:
        # Use structured output model (qwen2.5:1.5b) for reliable JSON
        response_data = ollama.client.generate(
            model=ollama.structured_model,
            prompt=prompt,
            options={"num_ctx": 8192},  # Larger context for multiple notes
        )

        response = response_data.get("response", "")
        if not response:
            logger.error("Empty response from Ollama for link suggestions")
            return LinkSuggestionsResponse(suggestions=[], count=0)

        # Parse JSON response using pure function
        suggestions_data = ai_core.parse_json_response(response, expected_type="array")
        if not suggestions_data or not isinstance(suggestions_data, list):
            return LinkSuggestionsResponse(suggestions=[], count=0)

        # Convert to LinkSuggestion models and add titles
        suggestions = []
        note_map = {n["id"]: n for n in candidate_notes}

        for s in suggestions_data:
            if not isinstance(s, dict):
                continue
            note_id_suggestion = s.get("note_id")
            if note_id_suggestion and note_id_suggestion in note_map:
                suggestions.append(
                    LinkSuggestion(
                        note_id=note_id_suggestion,
                        title=note_map[note_id_suggestion].get("title", "Untitled"),
                        confidence=s.get("confidence", 0.5),
                        reason=s.get("reason", ""),
                    )
                )

        # Limit to top 5 suggestions
        suggestions = suggestions[:5]

        logger.info("Generated %d link suggestions for note %s", len(suggestions), note_id)
        return LinkSuggestionsResponse(suggestions=suggestions, count=len(suggestions))

    except Exception as e:
        logger.error("Error generating link suggestions: %s", e)
        return LinkSuggestionsResponse(suggestions=[], count=0)


@router.get("/notes/{note_id}/suggest-stream")
def suggest_stream(
    note_id: str,
    ollama: OllamaDep,
    notes_service: NotesDep,
) -> StreamingResponse:
    """Stream AI suggestions (tags then links) via Server-Sent Events.

    This endpoint streams suggestions progressively as they're generated,
    reducing perceived wait time for CPU-bound AI operations (10-15 seconds).

    Event types:
    - progress: Phase update (tags, links)
    - tag: Individual tag suggestion
    - link: Individual link suggestion
    - complete: All suggestions generated
    - error: Error occurred

    Returns:
        StreamingResponse with text/event-stream content type
    """
    # Capture dependencies for use in generator
    # (generator runs after request handler returns, so we need to capture now)
    _ollama = ollama
    _notes_service = notes_service

    def format_sse(data: dict[str, Any]) -> str:
        """Format data as SSE event."""
        return f"data: {json.dumps(data)}\n\n"

    def event_generator() -> Generator[str]:
        # Get the note
        note = _notes_service.get_note(note_id)
        if not note:
            yield format_sse({"type": "error", "message": f"Note '{note_id}' not found"})
            return

        # Check Ollama availability
        if not _ollama.is_available():
            yield format_sse({"type": "error", "message": "AI service unavailable"})
            return

        # === PHASE 1: Generate Tags ===
        yield format_sse({"type": "progress", "phase": "tags"})

        # Get existing tags for context
        all_notes = _notes_service.list_notes()
        existing_tags: set[str] = set()
        for n in all_notes:
            existing_tags.update(n.get("tags", []))

        # Build tag suggestion prompt
        title = note.get("title", "")
        content = note.get("content", "")
        current_tags = note.get("tags", [])

        tag_prompt = ai_core.build_tag_suggestion_prompt(
            title=title, content=content, current_tags=current_tags, existing_tags=existing_tags
        )

        try:
            # Generate tags using structured output model
            tag_response = _ollama.client.generate(
                model=_ollama.structured_model, prompt=tag_prompt, options={"num_ctx": 4096}
            )

            tag_text = tag_response.get("response", "")
            if tag_text:
                tags_data = ai_core.parse_json_response(tag_text, expected_type="array")
                if tags_data and isinstance(tags_data, list):
                    for tag_item in tags_data[:4]:
                        if isinstance(tag_item, dict):
                            tag_suggestion = {
                                "tag": tag_item.get("tag", ""),
                                "confidence": tag_item.get("confidence", 0.5),
                                "reason": tag_item.get("reason", ""),
                            }
                            yield format_sse({"type": "tag", "data": tag_suggestion})

            logger.info("Streamed tag suggestions for note %s", note_id)

        except Exception as e:
            logger.error("Error generating tag suggestions during stream: %s", e)
            # Continue to links even if tags fail

        # === PHASE 2: Generate Links ===
        yield format_sse({"type": "progress", "phase": "links"})

        # Filter link candidates
        existing_links = note.get("links", [])
        candidate_notes = ai_core.filter_link_candidates(
            all_notes=all_notes, current_note_id=note_id, existing_links=existing_links
        )

        if candidate_notes:
            # Build link suggestion prompt
            link_prompt = ai_core.build_link_suggestion_prompt(
                current_title=title,
                current_content=content,
                candidate_notes=candidate_notes,
                max_candidates=50,
            )

            try:
                # Generate links using structured output model
                link_response = _ollama.client.generate(
                    model=_ollama.structured_model, prompt=link_prompt, options={"num_ctx": 8192}
                )

                link_text = link_response.get("response", "")
                if link_text:
                    links_data = ai_core.parse_json_response(link_text, expected_type="array")
                    if links_data and isinstance(links_data, list):
                        note_map = {n["id"]: n for n in candidate_notes}
                        for link_item in links_data[:5]:
                            if isinstance(link_item, dict):
                                link_note_id = link_item.get("note_id")
                                if link_note_id and link_note_id in note_map:
                                    link_suggestion = {
                                        "note_id": link_note_id,
                                        "title": note_map[link_note_id].get("title", "Untitled"),
                                        "confidence": link_item.get("confidence", 0.5),
                                        "reason": link_item.get("reason", ""),
                                    }
                                    yield format_sse({"type": "link", "data": link_suggestion})

                logger.info("Streamed link suggestions for note %s", note_id)

            except Exception as e:
                logger.error("Error generating link suggestions during stream: %s", e)

        # === COMPLETE ===
        yield format_sse({"type": "complete"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
