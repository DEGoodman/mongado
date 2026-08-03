"""AI-powered features API routes (Q&A, summaries, suggestions).

Uses FastAPI dependency injection for testability. Dependencies can be
overridden in tests using app.dependency_overrides.
"""

import json
import logging
from collections.abc import Generator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from auth import AdminUser
from core import ai as ai_core
from dependencies import get_llm, get_neo4j, get_notes, get_static_articles, get_user_resources
from models import (
    EditorAssistRequest,
    EditorAssistResponse,
    GPUStatusResponse,
    LinkSuggestion,
    LinkSuggestionsResponse,
    QuestionRequest,
    QuestionResponse,
    SynthesisRequest,
    SynthesisResponse,
    TagSuggestion,
    TagSuggestionsResponse,
    WarmupResponse,
)
from rate_limiter import RATE_LIMITS, limiter

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


def _format_sources(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize retrieved documents into the id/type/title/content/score shape
    the frontend already renders (mirrors routers/search.py's
    _normalize_search_result, kept separate since that helper returns a
    SearchResult model rather than a plain dict).
    """
    sources = []
    for doc in docs:
        is_note = "note_id" in doc
        sources.append(
            {
                "id": doc.get("note_id") if is_note else doc.get("id"),
                "type": "note" if is_note else "article",
                "title": doc.get("title", "Untitled"),
                "content": doc.get("content", ""),
                "score": doc.get("score", 0.0),
            }
        )
    return sources


def _retrieve_documents_for_synthesis(
    query: str,
    ollama: Any,
    neo4j: Any,
    all_resources: list[dict[str, Any]],
    top_k: int = 12,
) -> list[dict[str, Any]]:
    """Retrieve up to top_k documents for deep synthesis (#166).

    Mirrors the chunk -> whole-doc -> on-demand fallback ladder used by
    /api/search's semantic mode (routers/search.py:184-286), widened to
    top_k~12 parent docs (vs. /api/ask's top_k=5 whole-doc-only retrieval).

    This is intentionally its own helper rather than a shared one with
    search.py: the two callers need different output shapes (search.py
    builds SearchResult models with snippets; synthesis needs raw document
    dicts to feed into the synthesis prompt) and the pull sizes/priorities
    differ enough that trying to unify them would just add parameters to
    thread through. The three fallback tiers below are commented to keep
    the duplication with search.py explicit and auditable.
    """
    if not ollama.embeddings_available():
        return []

    if neo4j.is_available():
        # Tier 1: chunk-level scoring (#192) - a document ranks on its
        # best-matching section instead of one diluted whole-document vector.
        chunk_data = neo4j.get_all_chunk_embeddings()
        if chunk_data:
            query_embedding = ollama.generate_embedding(query, use_cache=False)
            if not query_embedding:
                logger.warning("Synthesis: failed to generate query embedding")
                return []

            ranked = ai_core.rank_parents_by_chunk_similarity(query_embedding, chunk_data, top_k)
            docs = []
            for item in ranked:
                full_doc = next(
                    (
                        doc
                        for doc in all_resources
                        if (item["type"] == "Article" and str(doc.get("id")) == item["id"])
                        or (item["type"] == "Note" and doc.get("note_id") == item["id"])
                    ),
                    None,
                )
                if full_doc:
                    docs.append({**full_doc, "score": item["score"]})
            if docs:
                logger.info("Synthesis: chunk-based retrieval found %d documents", len(docs))
                return docs
            logger.info("Synthesis: chunk embeddings present but matched no documents")

        # Tier 2: whole-document precomputed embeddings.
        embeddings_data = neo4j.get_all_embeddings()
        if embeddings_data:
            documents_with_embeddings = []
            for emb_data in embeddings_data:
                doc_id = emb_data["id"]
                doc_type = emb_data["type"]
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
                    documents_with_embeddings.append(
                        {**full_doc, "embedding": emb_data["embedding"]}
                    )
            if documents_with_embeddings:
                docs = ollama.semantic_search_with_precomputed_embeddings(
                    query, documents_with_embeddings, top_k
                )
                if docs:
                    logger.info("Synthesis: whole-doc retrieval found %d documents", len(docs))
                    result: list[dict[str, Any]] = docs
                    return result

    # Tier 3: generate embeddings on-demand (slow, but works without Neo4j).
    logger.info("Synthesis: falling back to on-demand embedding generation")
    fallback: list[dict[str, Any]] = ollama.semantic_search(query, all_resources, top_k)
    return fallback


def _build_link_command_prompt(
    text: str,
    title: str,
    note_id: str | None,
    notes_service: Any,
) -> tuple[str, list[dict[str, Any]]]:
    """Build the link-suggestion prompt for the `/link` editor command (#146).

    Reuses filter_link_candidates + build_link_suggestion_prompt - the same
    pure functions POST /api/notes/{note_id}/suggest-links uses - rather than
    duplicating retrieval logic. When note_id is omitted (a note being
    created and not yet saved), the current note is not excluded from
    candidates by ID and there are no existing links to exclude.

    Returns:
        (prompt, candidate_notes) - candidate_notes is empty if there is
        nothing to suggest against.
    """
    all_notes = notes_service.list_notes()

    existing_links: list[str] = []
    excluded_id = note_id or ""
    if note_id:
        note = notes_service.get_note(note_id)
        if note:
            existing_links = note.get("links", [])

    candidate_notes = ai_core.filter_link_candidates(
        all_notes=all_notes, current_note_id=excluded_id, existing_links=existing_links
    )

    prompt = ai_core.build_link_suggestion_prompt(
        current_title=title or "Untitled",
        current_content=text,
        candidate_notes=candidate_notes,
        max_candidates=50,
    )
    return prompt, candidate_notes


def _parse_link_command_response(
    response_text: str, candidate_notes: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Parse the LLM's link-suggestion JSON into plain suggestion dicts.

    Mirrors the parsing in suggest_links; kept separate rather than shared
    since suggest_links builds LinkSuggestion models directly while the
    editor-assist endpoints need plain dicts for both the JSON response body
    and the SSE `link` event payload.
    """
    suggestions_data = ai_core.parse_json_response(response_text, expected_type="array")
    if suggestions_data is None or not isinstance(suggestions_data, list):
        return []

    note_map = {n["id"]: n for n in candidate_notes}
    suggestions = []
    for item in suggestions_data:
        if not isinstance(item, dict):
            continue
        suggested_id = item.get("note_id")
        if suggested_id and suggested_id in note_map:
            suggestions.append(
                {
                    "note_id": suggested_id,
                    "title": note_map[suggested_id].get("title", "Untitled"),
                    "confidence": item.get("confidence", 0.5),
                    "reason": item.get("reason", ""),
                }
            )

    return suggestions[:5]


# Editor writing-partner commands (#146 Phase 2): narrower retrieval than
# synthesis's top_k=12 - this is focused critique of one passage (the text
# under review in the editor), not a corpus-wide summary, so a handful of the
# most relevant notes is plenty and keeps the prompt small/fast to generate.
# Fetch one extra so excluding the current note (see below) still leaves up
# to WRITING_PARTNER_TOP_K results rather than quietly shrinking the pull.
WRITING_PARTNER_TOP_K = 6


def _retrieve_for_writing_partner(
    text: str,
    note_title: str | None,
    note_id: str | None,
    ollama: Any,
    neo4j: Any,
    all_resources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Retrieve context documents for a writing-partner command (#146 Phase 2).

    Reuses _retrieve_documents_for_synthesis (the same chunk -> whole-doc ->
    on-demand retrieval ladder /api/synthesize uses) rather than writing a
    third copy. The query is the note title plus the text under review, so
    retrieval is anchored to what's actually being critiqued.

    Excludes the current note from its own results when note_id is known -
    a note "contradicting itself" is just noise, not a finding.
    """
    query = f"{note_title}\n\n{text}" if note_title else text
    docs = _retrieve_documents_for_synthesis(
        query, ollama, neo4j, all_resources, top_k=WRITING_PARTNER_TOP_K + (1 if note_id else 0)
    )
    if note_id:
        docs = [d for d in docs if d.get("note_id") != note_id]
    return docs[:WRITING_PARTNER_TOP_K]


# Type aliases for cleaner signatures
OllamaDep = Annotated[Any, Depends(get_llm)]
NotesDep = Annotated[Any, Depends(get_notes)]
Neo4jDep = Annotated[Any, Depends(get_neo4j)]
ArticlesDep = Annotated[list[dict[str, Any]], Depends(get_static_articles)]
UserResourcesDep = Annotated[list[dict[str, Any]], Depends(get_user_resources)]


@router.post("/ollama/warmup", response_model=WarmupResponse)
@limiter.limit(RATE_LIMITS["ai_warmup"])
def warmup_ollama(
    request: Request, ollama: OllamaDep, context: str = "chat"
) -> WarmupResponse:
    """Warm up an Ollama model by starting the llama runner.

    This endpoint takes ~15-20 seconds to complete, but makes subsequent
    AI requests much faster.

    **Context-aware warmup:** Warm up the model that will be used next:
    - `chat` (default): For Q&A and summaries (llama3.2:1b)
    - `structured`: For AI suggestions with JSON output (qwen2.5:1.5b)
    - `embedding`: For semantic search (nomic-embed-text)

    **Usage:**
    - User opens Q&A panel → warmup with context=chat
    - User enters note edit mode → warmup with context=structured
    - User opens semantic search → warmup with context=embedding
    """
    if not ollama.is_available():
        return WarmupResponse(
            success=False,
            message="Ollama is not available or not configured.",
            context=context,
        )

    # Validate context
    valid_contexts = {"chat", "structured", "embedding"}
    if context not in valid_contexts:
        return WarmupResponse(
            success=False,
            message=f"Invalid context '{context}'. Must be one of: {', '.join(valid_contexts)}",
            context=context,
        )

    success, model = ollama.warmup(context=context)
    if success:
        return WarmupResponse(
            success=True,
            message=f"Ollama {context} model ({model}) warmed up successfully.",
            model=model,
            context=context,
        )
    else:
        return WarmupResponse(
            success=False,
            message=f"Failed to warm up Ollama {context} model. Check logs for details.",
            model=model,
            context=context,
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
        provider = getattr(ollama, "active_provider", "ollama")
        message = (
            f"AI generation served by hosted API ({provider}). AI features will be fast."
            if provider != "ollama"
            else "GPU acceleration is available. AI features will be fast."
        )
        return GPUStatusResponse(has_gpu=True, message=message)
    else:
        return GPUStatusResponse(
            has_gpu=False,
            message="Running on CPU only. AI generation features will be slower (60-120s response times).",
        )


@router.post("/ask", response_model=QuestionResponse)
@limiter.limit(RATE_LIMITS["ai_ask"])
def ask_question(
    request: Request,
    question_request: QuestionRequest,
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
    # (needs Ollama for the query embedding even when generation uses the API)
    if neo4j.is_available() and ollama.embeddings_available():
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
                question_request.question, documents_with_embeddings, top_k=5
            )
            logger.info("Q&A: Fast semantic search found %d relevant docs", len(relevant_docs))
        else:
            logger.warning(
                "Q&A: No precomputed embeddings found, falling back to on-demand generation"
            )

    # Fallback: Generate embeddings on-demand (slow but works without Neo4j)
    if not relevant_docs:
        logger.info("Q&A: Using on-demand embedding generation (slower)")
        relevant_docs = ollama.semantic_search(question_request.question, all_resources, top_k=5)

    # Generate answer with hybrid mode (KB + general knowledge)
    answer = ollama.ask_question(question_request.question, relevant_docs, allow_general_knowledge=True)

    if not answer:
        raise HTTPException(status_code=500, detail="Failed to generate answer. Please try again.")

    return QuestionResponse(answer=answer, sources=relevant_docs)


@router.post("/notes/{note_id}/suggest-tags", response_model=TagSuggestionsResponse)
@limiter.limit(RATE_LIMITS["ai_suggest"])
def suggest_tags(
    request: Request,
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
        logger.warning("LLM not available for tag suggestions")
        return TagSuggestionsResponse(suggestions=[], count=0, degraded=True)

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
        # Use the structured-output role (Ollama: qwen2.5:1.5b; API: hosted model)
        response = ollama.generate(prompt, role="structured", num_ctx=4096)
        if not response:
            logger.error("Empty response from LLM for tag suggestions")
            return TagSuggestionsResponse(suggestions=[], count=0, degraded=True)

        # Parse JSON response using pure function
        suggestions_data = ai_core.parse_json_response(response, expected_type="array")
        # None means the parse failed; [] means the model ran and found nothing
        if suggestions_data is None or not isinstance(suggestions_data, list):
            logger.warning("Unparseable tag suggestion response for note %s", note_id)
            return TagSuggestionsResponse(suggestions=[], count=0, degraded=True)

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
        return TagSuggestionsResponse(suggestions=[], count=0, degraded=True)


@router.post("/notes/{note_id}/suggest-links", response_model=LinkSuggestionsResponse)
@limiter.limit(RATE_LIMITS["ai_suggest"])
def suggest_links(
    request: Request,
    note_id: str,
    ollama: OllamaDep,
    notes_service: NotesDep,
    refresh: bool = False,
) -> LinkSuggestionsResponse:
    """Suggest related notes that should be linked via wikilinks.

    Returns cached suggestions if available, or generates new ones.

    Args:
        note_id: Note ID
        refresh: If True, regenerate suggestions even if cached (default: False)

    Returns:
        Suggestions with confidence scores and cached indicator
    """
    # Get the current note
    note = notes_service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

    # Try to get cached suggestions first (unless refresh requested)
    if not refresh:
        ai_content = notes_service.get_ai_content(note_id)
        if ai_content and ai_content.get("ai_link_suggestions"):
            cached_suggestions = ai_content["ai_link_suggestions"]
            suggestions = [
                LinkSuggestion(
                    note_id=s.get("note_id", ""),
                    title=s.get("title", "Untitled"),
                    confidence=s.get("confidence", 0.5),
                    reason=s.get("reason", ""),
                )
                for s in cached_suggestions
                if isinstance(s, dict)
            ]
            return LinkSuggestionsResponse(
                suggestions=suggestions,
                count=len(suggestions),
                cached=True,
                cached_at=ai_content.get("ai_link_suggestions_at"),
            )

    # No cache or refresh requested - generate new suggestions
    if not ollama.is_available():
        logger.warning("LLM not available for link suggestions")
        return LinkSuggestionsResponse(suggestions=[], count=0, degraded=True)

    # Force regeneration
    if refresh:
        ai_content = notes_service.regenerate_ai_content(note_id)
        if ai_content and ai_content.get("ai_link_suggestions"):
            cached_suggestions = ai_content["ai_link_suggestions"]
            suggestions = [
                LinkSuggestion(
                    note_id=s.get("note_id", ""),
                    title=s.get("title", "Untitled"),
                    confidence=s.get("confidence", 0.5),
                    reason=s.get("reason", ""),
                )
                for s in cached_suggestions
                if isinstance(s, dict)
            ]
            return LinkSuggestionsResponse(
                suggestions=suggestions,
                count=len(suggestions),
                cached=True,
                cached_at=ai_content.get("ai_link_suggestions_at"),
            )

    # Fallback: generate on-demand (shouldn't normally reach here for new notes)
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
        # Use the structured-output role; larger context for multiple notes
        response = ollama.generate(prompt, role="structured", num_ctx=8192)
        if not response:
            logger.error("Empty response from LLM for link suggestions")
            return LinkSuggestionsResponse(suggestions=[], count=0, degraded=True)

        # Parse JSON response using pure function
        suggestions_data = ai_core.parse_json_response(response, expected_type="array")
        # None means the parse failed; [] means the model ran and found nothing
        if suggestions_data is None or not isinstance(suggestions_data, list):
            logger.warning("Unparseable link suggestion response for note %s", note_id)
            return LinkSuggestionsResponse(suggestions=[], count=0, degraded=True)

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
        return LinkSuggestionsResponse(suggestions=suggestions, count=len(suggestions), cached=False)

    except Exception as e:
        logger.error("Error generating link suggestions: %s", e)
        return LinkSuggestionsResponse(suggestions=[], count=0, degraded=True)


@router.get("/notes/{note_id}/suggest-stream")
@limiter.limit(RATE_LIMITS["ai_stream"])
def suggest_stream(
    request: Request,
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
            # Generate tags with token streaming for real-time progress
            tag_text = ""
            token_count = 0
            for text in _ollama.generate_stream(tag_prompt, role="structured", num_ctx=4096):
                tag_text += text
                token_count += 1
                # Send heartbeat every 10 tokens to show activity
                if token_count % 10 == 0:
                    yield format_sse(
                        {"type": "generating", "phase": "tags", "tokens": token_count}
                    )

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

            logger.info("Streamed tag suggestions for note %s (%d tokens)", note_id, token_count)

        except Exception as e:
            logger.error("Error generating tag suggestions during stream: %s", e)
            # Tell the client this phase degraded, then continue to links (#260).
            # Silently dropping the phase is indistinguishable from "no tags fit".
            yield format_sse({"type": "degraded", "phase": "tags"})

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
                # Generate links with token streaming for real-time progress
                link_text = ""
                token_count = 0
                for text in _ollama.generate_stream(
                    link_prompt, role="structured", num_ctx=8192
                ):
                    link_text += text
                    token_count += 1
                    # Send heartbeat every 10 tokens to show activity
                    if token_count % 10 == 0:
                        yield format_sse(
                            {"type": "generating", "phase": "links", "tokens": token_count}
                        )

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

                logger.info(
                    "Streamed link suggestions for note %s (%d tokens)", note_id, token_count
                )

            except Exception as e:
                logger.error("Error generating link suggestions during stream: %s", e)
                yield format_sse({"type": "degraded", "phase": "links"})

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


# Synthesis (#166): "deep synthesis" mode of /api/ask - wider retrieval
# (chunk-ranked, top_k~12 parent docs) + a structured markdown prompt
# instead of a short answer.
SYNTHESIS_TOP_K = 12


@router.post("/synthesize", response_model=SynthesisResponse)
@limiter.limit(RATE_LIMITS["ai_synthesis"])
def synthesize(
    request: Request,
    synthesis_request: SynthesisRequest,
    ollama: OllamaDep,
    notes_service: NotesDep,
    neo4j: Neo4jDep,
    static_articles: ArticlesDep,
    user_resources: UserResourcesDep,
) -> SynthesisResponse:
    """Synthesize a structured markdown summary across the knowledge base (#166).

    Non-streaming counterpart to /api/synthesize/stream. Uses the same
    chunk-first retrieval ladder, widened to ~12 parent documents, and the
    synthesis-specific prompt (Key Concepts / Your Positions / Gaps & Open
    Questions) instead of the short-answer Q&A prompt.
    """
    if not ollama.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI synthesis feature is not available. LLM is not running or not configured.",
        )

    all_resources = _get_all_resources(static_articles, user_resources, notes_service)
    relevant_docs = _retrieve_documents_for_synthesis(
        synthesis_request.query, ollama, neo4j, all_resources, top_k=SYNTHESIS_TOP_K
    )

    prompt = ai_core.build_synthesis_prompt(synthesis_request.query, relevant_docs)
    synthesis_text = ollama.generate(prompt, role="chat")

    if not synthesis_text:
        logger.warning("Synthesis: empty response from LLM")
        return SynthesisResponse(
            synthesis="", sources=_format_sources(relevant_docs), degraded=True
        )

    return SynthesisResponse(
        synthesis=synthesis_text, sources=_format_sources(relevant_docs), degraded=False
    )


@router.post("/synthesize/stream")
@limiter.limit(RATE_LIMITS["ai_synthesis"])
def synthesize_stream(
    request: Request,
    synthesis_request: SynthesisRequest,
    ollama: OllamaDep,
    notes_service: NotesDep,
    neo4j: Neo4jDep,
    static_articles: ArticlesDep,
    user_resources: UserResourcesDep,
) -> StreamingResponse:
    """Stream a deep-synthesis response via Server-Sent Events (#166).

    POST (not GET) because the query plus a wide document pull won't fit a
    querystring - so the browser can't use EventSource for this endpoint;
    the frontend uses a fetch()-based SSE reader instead (frontend/src/lib/sse.ts).

    Event types:
    - sources: the retrieved documents, sent first so citations can render
      before any prose arrives
    - token: incremental text chunks of the synthesis
    - complete: synthesis finished
    - error: something failed; the stream ends without raising
    """
    # Capture dependencies for use in generator (it runs after the request
    # handler returns, so dependencies must be captured now, not resolved lazily).
    _ollama = ollama
    _notes_service = notes_service
    _neo4j = neo4j
    _static_articles = static_articles
    _user_resources = user_resources
    _query = synthesis_request.query

    def format_sse(data: dict[str, Any]) -> str:
        return f"data: {json.dumps(data)}\n\n"

    def event_generator() -> Generator[str]:
        if not _ollama.is_available():
            yield format_sse({"type": "error", "message": "AI service unavailable"})
            return

        try:
            all_resources = _get_all_resources(_static_articles, _user_resources, _notes_service)
            relevant_docs = _retrieve_documents_for_synthesis(
                _query, _ollama, _neo4j, all_resources, top_k=SYNTHESIS_TOP_K
            )
        except Exception as e:
            logger.error("Synthesis stream: retrieval failed: %s", e)
            yield format_sse({"type": "error", "message": "Failed to retrieve documents"})
            return

        # Sources first, so citations render before prose arrives.
        yield format_sse({"type": "sources", "sources": _format_sources(relevant_docs)})

        prompt = ai_core.build_synthesis_prompt(_query, relevant_docs)

        try:
            token_count = 0
            for text in _ollama.generate_stream(prompt, role="chat"):
                token_count += 1
                yield format_sse({"type": "token", "text": text})

            if token_count == 0:
                logger.warning("Synthesis stream: empty response from LLM")
                yield format_sse({"type": "error", "message": "Failed to generate synthesis"})
                return

            logger.info("Synthesis stream complete (%d tokens)", token_count)
            yield format_sse({"type": "complete"})

        except Exception as e:
            logger.error("Synthesis stream: generation failed: %s", e)
            yield format_sse({"type": "error", "message": "Failed to generate synthesis"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# Editor slash commands (#146 Phase 1). Admin-gated (AdminUser, not the
# open-to-all pattern used by /api/ask and /api/notes/{id}/suggest-stream):
# only admins can edit notes, so an unauthenticated caller has no legitimate
# use for these, and leaving them open would make the site a free LLM proxy
# for arbitrary attacker-supplied text. The frontend uses lib/sse.ts's
# fetch()-based SSE reader (not EventSource), which can send the
# Authorization header these endpoints require.
@router.post("/editor/assist", response_model=EditorAssistResponse)
@limiter.limit(RATE_LIMITS["ai_editor"])
def editor_assist(
    request: Request,
    assist_request: EditorAssistRequest,
    ollama: OllamaDep,
    notes_service: NotesDep,
    neo4j: Neo4jDep,
    static_articles: ArticlesDep,
    user_resources: UserResourcesDep,
    _admin: AdminUser,
) -> EditorAssistResponse:
    """Non-streaming counterpart to /api/editor/assist/stream, for fallback.

    Text-transform commands return `result`; `/link` returns `suggestions`;
    writing-partner commands (challenge/gaps/contradictions, Phase 2) return
    both `result` (markdown commentary) and `sources` (the notes it drew on).
    """
    command = assist_request.command

    if command not in ai_core.EDITOR_COMMANDS:
        raise HTTPException(status_code=400, detail=f"Unknown editor command: {command!r}")

    if not ollama.is_available():
        raise HTTPException(
            status_code=503,
            detail="AI editor assist feature is not available. LLM is not running or not configured.",
        )

    if command == "link":
        prompt, candidate_notes = _build_link_command_prompt(
            assist_request.text,
            assist_request.note_title or "",
            assist_request.note_id,
            notes_service,
        )
        if not candidate_notes:
            return EditorAssistResponse(command=command, suggestions=[])

        response_text = ollama.generate(prompt, role="structured", num_ctx=8192)
        if not response_text:
            logger.error("Empty response from LLM for editor /link command")
            return EditorAssistResponse(command=command, suggestions=[], degraded=True)

        suggestions = _parse_link_command_response(response_text, candidate_notes)
        return EditorAssistResponse(command=command, suggestions=suggestions)

    if command in ai_core.EDITOR_PARTNER_COMMANDS:
        all_resources = _get_all_resources(static_articles, user_resources, notes_service)
        relevant_docs = _retrieve_for_writing_partner(
            assist_request.text,
            assist_request.note_title,
            assist_request.note_id,
            ollama,
            neo4j,
            all_resources,
        )

        if not relevant_docs:
            # Never call the LLM with an empty context - a clean, honest
            # "nothing to check against" beats a hallucinated critique.
            return EditorAssistResponse(
                command=command,
                result=(
                    "There's nothing in the knowledge base yet to check this "
                    "against."
                ),
                sources=[],
                degraded=True,
            )

        prompt = ai_core.build_writing_partner_prompt(
            command, assist_request.text, assist_request.note_title, relevant_docs
        )
        result = ollama.generate(prompt, role="chat")
        if not result:
            logger.error("Empty response from LLM for writing-partner command %s", command)
            return EditorAssistResponse(
                command=command, result="", sources=_format_sources(relevant_docs), degraded=True
            )

        return EditorAssistResponse(
            command=command,
            result=result,
            sources=_format_sources(relevant_docs),
            degraded=False,
        )

    try:
        prompt = ai_core.build_editor_command_prompt(
            command, assist_request.text, assist_request.note_title, assist_request.note_content
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    result = ollama.generate(prompt, role="chat")
    if not result:
        logger.error("Empty response from LLM for editor command %s", command)
        return EditorAssistResponse(command=command, result="", degraded=True)

    return EditorAssistResponse(command=command, result=result)


@router.post("/editor/assist/stream")
@limiter.limit(RATE_LIMITS["ai_editor"])
def editor_assist_stream(
    request: Request,
    assist_request: EditorAssistRequest,
    ollama: OllamaDep,
    notes_service: NotesDep,
    neo4j: Neo4jDep,
    static_articles: ArticlesDep,
    user_resources: UserResourcesDep,
    _admin: AdminUser,
) -> StreamingResponse:
    """Stream an editor slash-command result via Server-Sent Events (#146).

    POST (not GET) so the frontend can send the note text/context in the
    body and an Authorization header - not possible with EventSource, so the
    frontend uses the fetch()-based reader in frontend/src/lib/sse.ts.

    Event types:
    - sources: retrieved notes (writing-partner commands only), sent before
      any token so citations can render before prose arrives
    - token: incremental text chunk (text-transform and writing-partner
      commands)
    - link: one link suggestion ({note_id, title, reason, confidence}) (`/link` only)
    - complete: command finished
    - error: something failed; the stream ends without raising

    Never raises out of the generator - failures are reported as an `error`
    event so the frontend can leave the document untouched.
    """
    _ollama = ollama
    _notes_service = notes_service
    _neo4j = neo4j
    _static_articles = static_articles
    _user_resources = user_resources
    _command = assist_request.command
    _text = assist_request.text
    _title = assist_request.note_title
    _content = assist_request.note_content
    _note_id = assist_request.note_id

    def format_sse(data: dict[str, Any]) -> str:
        return f"data: {json.dumps(data)}\n\n"

    def event_generator() -> Generator[str]:
        if _command not in ai_core.EDITOR_COMMANDS:
            yield format_sse({"type": "error", "message": f"Unknown editor command: {_command!r}"})
            return

        if not _ollama.is_available():
            yield format_sse({"type": "error", "message": "AI service unavailable"})
            return

        if _command == "link":
            try:
                prompt, candidate_notes = _build_link_command_prompt(
                    _text, _title or "", _note_id, _notes_service
                )
            except Exception as e:
                logger.error("Editor /link stream: failed to prepare candidates: %s", e)
                yield format_sse({"type": "error", "message": "Failed to prepare link suggestions"})
                return

            if not candidate_notes:
                yield format_sse({"type": "complete"})
                return

            try:
                link_text = ""
                for chunk in _ollama.generate_stream(prompt, role="structured", num_ctx=8192):
                    link_text += chunk

                if not link_text:
                    logger.error("Editor /link stream: empty response from LLM")
                    yield format_sse(
                        {"type": "error", "message": "Failed to generate link suggestions"}
                    )
                    return

                suggestions = _parse_link_command_response(link_text, candidate_notes)
                for suggestion in suggestions:
                    yield format_sse({"type": "link", **suggestion})

                yield format_sse({"type": "complete"})

            except Exception as e:
                logger.error("Editor /link stream: generation failed: %s", e)
                yield format_sse({"type": "error", "message": "Failed to generate link suggestions"})

            return

        if _command in ai_core.EDITOR_PARTNER_COMMANDS:
            try:
                all_resources = _get_all_resources(
                    _static_articles, _user_resources, _notes_service
                )
                relevant_docs = _retrieve_for_writing_partner(
                    _text, _title, _note_id, _ollama, _neo4j, all_resources
                )
            except Exception as e:
                logger.error(
                    "Editor writing-partner stream: retrieval failed (%s): %s", _command, e
                )
                yield format_sse({"type": "error", "message": "Failed to retrieve context"})
                return

            # Sources first, so citations render before prose arrives.
            yield format_sse({"type": "sources", "sources": _format_sources(relevant_docs)})

            if not relevant_docs:
                # Never call the LLM with an empty context - a clean, honest
                # "nothing to check against" beats a hallucinated critique.
                yield format_sse(
                    {
                        "type": "token",
                        "text": (
                            "There's nothing in the knowledge base yet to check "
                            "this against."
                        ),
                    }
                )
                yield format_sse({"type": "complete", "degraded": True})
                return

            try:
                prompt = ai_core.build_writing_partner_prompt(
                    _command, _text, _title, relevant_docs
                )
            except ValueError as e:
                yield format_sse({"type": "error", "message": str(e)})
                return

            try:
                token_count = 0
                for chunk in _ollama.generate_stream(prompt, role="chat"):
                    token_count += 1
                    yield format_sse({"type": "token", "text": chunk})

                if token_count == 0:
                    logger.warning(
                        "Writing-partner stream: empty response from LLM (%s)", _command
                    )
                    yield format_sse({"type": "error", "message": "Failed to generate response"})
                    return

                logger.info(
                    "Writing-partner stream complete: %s (%d tokens)", _command, token_count
                )
                yield format_sse({"type": "complete"})

            except Exception as e:
                logger.error(
                    "Writing-partner stream: generation failed (%s): %s", _command, e
                )
                yield format_sse({"type": "error", "message": "Failed to generate response"})

            return

        try:
            prompt = ai_core.build_editor_command_prompt(_command, _text, _title, _content)
        except ValueError as e:
            yield format_sse({"type": "error", "message": str(e)})
            return

        try:
            token_count = 0
            for text in _ollama.generate_stream(prompt, role="chat"):
                token_count += 1
                yield format_sse({"type": "token", "text": text})

            if token_count == 0:
                logger.warning("Editor command stream: empty response from LLM (%s)", _command)
                yield format_sse({"type": "error", "message": "Failed to generate response"})
                return

            logger.info(
                "Editor command stream complete: %s (%d tokens)", _command, token_count
            )
            yield format_sse({"type": "complete"})

        except Exception as e:
            logger.error("Editor command stream: generation failed (%s): %s", _command, e)
            yield format_sse({"type": "error", "message": "Failed to generate response"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
