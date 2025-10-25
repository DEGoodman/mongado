"""FastAPI endpoints for Zettelkasten notes."""

import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth import SessionID, get_session_id
from config import get_settings
from notes_service import get_notes_service

logger = logging.getLogger(__name__)

# Create router for notes endpoints
router = APIRouter(prefix="/api/notes", tags=["notes"])

# Get service
notes_service = get_notes_service()

# Rate limiter - disabled in tests
limiter = Limiter(key_func=get_remote_address, enabled=os.getenv("TESTING") != "1")


# Pydantic models
class NoteCreate(BaseModel):
    """Request model for creating a note.

    Examples:
        {
            "title": "My First Note",
            "content": "This is a note with a [[wikilink]] to another note.",
            "tags": ["pkm", "learning"]
        }
    """

    title: str | None = None
    content: str
    tags: list[str] = []

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "Zettelkasten Method",
                    "content": "Personal knowledge management system based on interconnected atomic notes.\n\nKey principles:\n- One idea per note\n- Link liberally with [[wikilinks]]\n- Emerge structure organically",
                    "tags": ["pkm", "methodology"]
                }
            ]
        }
    }


class NoteUpdate(BaseModel):
    """Request model for updating a note."""

    title: str | None = None
    content: str
    tags: list[str] | None = None


class NoteResponse(BaseModel):
    """Response model for a single note."""

    id: str
    title: str | None
    content: str
    author: str
    is_ephemeral: bool
    tags: list[str]
    created_at: str | float
    updated_at: str | float
    links: list[str]


class NotesListResponse(BaseModel):
    """Response model for list of notes."""

    notes: list[dict[str, Any]]
    count: int


class BacklinksResponse(BaseModel):
    """Response model for backlinks."""

    backlinks: list[dict[str, Any]]
    count: int


class TagSuggestion(BaseModel):
    """A single tag suggestion."""

    tag: str
    confidence: float
    reason: str


class TagSuggestionsResponse(BaseModel):
    """Response model for tag suggestions."""

    suggestions: list[TagSuggestion]
    count: int


class LinkSuggestion(BaseModel):
    """A single link suggestion."""

    note_id: str
    title: str
    confidence: float
    reason: str


class LinkSuggestionsResponse(BaseModel):
    """Response model for link suggestions."""

    suggestions: list[LinkSuggestion]
    count: int


# Helper function to try admin auth without raising
def try_verify_admin(authorization: str | None = Header(None)) -> bool:
    """Try to verify admin token without raising exceptions."""
    if not authorization:
        return False

    if not authorization.startswith("Bearer "):
        return False

    token = authorization.replace("Bearer ", "").strip()
    expected_token = get_settings().admin_token

    if not expected_token or token != expected_token:
        return False

    logger.info("Admin authenticated successfully")
    return True


# Endpoints
@router.post(
    "",
    response_model=dict[str, Any],
    status_code=201,
    summary="Create a new note",
    description="""
Create a new note in the knowledge base.

**Authentication:**
- **Admin** (with Bearer token): Creates persistent note stored in Neo4j
- **Visitor** (with X-Session-ID header): Creates ephemeral note (session-specific)

**Wikilinks:**
Use double brackets to link to other notes: `[[note-id]]`
Links are automatically parsed and stored as graph relationships.

**Rate Limit:** 10 notes per minute per IP address
""",
)
@limiter.limit("10/minute")  # 10 note creations per minute per IP
async def create_note(
    request: Request,
    note: NoteCreate,
    session_id: SessionID = Depends(get_session_id),
    is_admin: bool = Depends(try_verify_admin),
) -> dict[str, Any]:
    """Create a new note."""
    if not is_admin and not session_id:
        raise HTTPException(
            status_code=400,
            detail="Session ID required for anonymous users. Include X-Session-ID header.",
        )

    created_note = notes_service.create_note(
        content=note.content,
        title=note.title,
        tags=note.tags,
        is_admin=is_admin,
        session_id=session_id,
    )

    return created_note


@router.get("", response_model=NotesListResponse)
async def list_notes(
    session_id: SessionID = Depends(get_session_id),
    is_admin: bool = Depends(try_verify_admin),
) -> NotesListResponse:
    """List all accessible notes.

    Returns persistent notes + ephemeral notes for current session.
    """
    notes = notes_service.list_notes(is_admin=is_admin, session_id=session_id)

    return NotesListResponse(notes=notes, count=len(notes))


@router.get("/{note_id}", response_model=dict[str, Any])
async def get_note(
    note_id: str,
    session_id: SessionID = Depends(get_session_id),
    is_admin: bool = Depends(try_verify_admin),
) -> dict[str, Any]:
    """Get a specific note by ID."""
    note = notes_service.get_note(note_id, is_admin=is_admin, session_id=session_id)

    if not note:
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

    return note


@router.put("/{note_id}", response_model=dict[str, Any])
async def update_note(
    note_id: str,
    note_update: NoteUpdate,
    session_id: SessionID = Depends(get_session_id),
    is_admin: bool = Depends(try_verify_admin),
) -> dict[str, Any]:
    """Update a note.

    - Admin can update persistent notes
    - Visitors can update their own ephemeral notes
    """
    updated = notes_service.update_note(
        note_id=note_id,
        content=note_update.content,
        title=note_update.title,
        tags=note_update.tags,
        is_admin=is_admin,
        session_id=session_id,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail=f"Note '{note_id}' not found or unauthorized",
        )

    return updated


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    session_id: SessionID = Depends(get_session_id),
    is_admin: bool = Depends(try_verify_admin),
) -> dict[str, str]:
    """Delete a note.

    - Admin can delete persistent notes
    - Visitors can delete their own ephemeral notes
    """
    deleted = notes_service.delete_note(
        note_id=note_id, is_admin=is_admin, session_id=session_id
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Note '{note_id}' not found or unauthorized",
        )

    return {"message": f"Note '{note_id}' deleted successfully"}


@router.get("/{note_id}/backlinks", response_model=BacklinksResponse)
async def get_backlinks(note_id: str) -> BacklinksResponse:
    """Get all notes that link to this note."""
    backlinks = notes_service.get_backlinks(note_id)

    return BacklinksResponse(backlinks=backlinks, count=len(backlinks))


@router.get("/{note_id}/links", response_model=dict[str, Any])
async def get_outbound_links(note_id: str) -> dict[str, Any]:
    """Get all notes this note links to."""
    links = notes_service.get_outbound_links(note_id)

    return {"links": links, "count": len(links)}


@router.get("/graph/data", response_model=dict[str, Any])
async def get_graph_data(
    session_id: SessionID = Depends(get_session_id),
    is_admin: bool = Depends(try_verify_admin),
) -> dict[str, Any]:
    """Get full graph data (all nodes and edges) for visualization.

    Returns:
    - nodes: List of all accessible notes
    - edges: List of all links between notes
    """
    # Get all accessible notes
    notes = notes_service.list_notes(is_admin=is_admin, session_id=session_id)

    # Build nodes list
    nodes = [
        {
            "id": note["id"],
            "title": note.get("title") or note["id"],
            "author": note["author"],
            "is_ephemeral": note["is_ephemeral"],
            "tags": note.get("tags", []),
        }
        for note in notes
    ]

    # Build edges list from all notes' links
    edges = []
    for note in notes:
        source_id = note["id"]
        for target_id in note.get("links", []):
            edges.append({
                "source": source_id,
                "target": target_id,
            })

    return {
        "nodes": nodes,
        "edges": edges,
        "count": {
            "nodes": len(nodes),
            "edges": len(edges),
        }
    }


@router.post("/{note_id}/suggest-tags", response_model=TagSuggestionsResponse)
async def suggest_tags(note_id: str) -> TagSuggestionsResponse:
    """Suggest relevant tags for a note using AI analysis.

    Analyzes note content and suggests 2-4 relevant tags based on:
    - Topic/domain (e.g., "management", "sre", "pkm")
    - Type (e.g., "framework", "concept", "practice")
    - Existing tags in the knowledge base

    Returns empty suggestions if Ollama is unavailable.
    """
    import json

    from ollama_client import get_ollama_client

    ollama = get_ollama_client()

    # Get the note
    note = notes_service.get_note(note_id, is_admin=True)
    if not note:
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

    # If Ollama unavailable, return empty suggestions
    if not ollama.is_available():
        logger.warning("Ollama not available for tag suggestions")
        return TagSuggestionsResponse(suggestions=[], count=0)

    # Get all existing tags from all notes for context
    all_notes = notes_service.list_notes(is_admin=True)
    existing_tags = set()
    for n in all_notes:
        existing_tags.update(n.get("tags", []))
    existing_tags_str = ", ".join(sorted(existing_tags)) if existing_tags else "None yet"

    # Build prompt for LLM
    title = note.get("title", "")
    content = note.get("content", "")
    current_tags = note.get("tags", [])

    prompt = f"""Analyze this note and suggest 2-4 relevant tags.

Note Title: {title}
Note Content:
{content[:1000]}

Current Tags: {', '.join(current_tags) if current_tags else 'None'}
Existing tags in knowledge base: {existing_tags_str[:200]}

Focus on:
- Topic/domain (e.g., "management", "sre", "pkm", "devops")
- Type (e.g., "framework", "concept", "practice", "mental-model")
- Avoid duplicating current tags
- Prefer tags already in use when appropriate

Return ONLY a JSON array of suggestions, each with: tag, confidence (0-1), reason
Example: [{{"tag": "management", "confidence": 0.9, "reason": "Discusses leadership and team dynamics"}}]

JSON:"""

    try:
        # Use qwen2.5:1.5b for instruction-following (excellent at JSON format)
        response_data = ollama.client.generate(
            model="qwen2.5:1.5b",
            prompt=prompt,
            options={"num_ctx": 4096}
        )

        response = response_data.get("response", "")
        if not response:
            logger.error("Empty response from Ollama for tag suggestions")
            return TagSuggestionsResponse(suggestions=[], count=0)

        # Parse JSON response
        # Extract JSON from response (might have extra text or markdown)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        # Try to parse as array first
        try:
            suggestions_data = json.loads(response)
            if isinstance(suggestions_data, dict):
                suggestions_data = [suggestions_data]
            elif not isinstance(suggestions_data, list):
                logger.error("Unexpected response format from LLM: %s", type(suggestions_data))
                return TagSuggestionsResponse(suggestions=[], count=0)
        except json.JSONDecodeError:
            # LLM might return multiple JSON objects on separate lines
            # Try to parse each line as a separate JSON object
            suggestions_data = []
            for line in response.split('\n'):
                line = line.strip()
                if line and line.startswith('{'):
                    try:
                        obj = json.loads(line)
                        suggestions_data.append(obj)
                    except json.JSONDecodeError:
                        continue

            if not suggestions_data:
                logger.error("Could not parse any JSON from response")
                logger.error("Full response was: %s", response[:500])
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

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON from Ollama response: %s", e)
        logger.error("Full response was: %s", response[:500])
        return TagSuggestionsResponse(suggestions=[], count=0)
    except Exception as e:
        logger.error("Error generating tag suggestions: %s", e)
        return TagSuggestionsResponse(suggestions=[], count=0)


@router.post("/{note_id}/suggest-links", response_model=LinkSuggestionsResponse)
async def suggest_links(note_id: str) -> LinkSuggestionsResponse:
    """Suggest related notes that should be linked via wikilinks.

    Analyzes note content and suggests other notes that are conceptually related.
    Returns suggestions with confidence scores and reasoning.

    Returns empty suggestions if Ollama is unavailable or note not found.
    """
    import json

    from ollama_client import get_ollama_client

    ollama = get_ollama_client()

    # Get the current note
    note = notes_service.get_note(note_id, is_admin=True)
    if not note:
        raise HTTPException(status_code=404, detail=f"Note '{note_id}' not found")

    # If Ollama unavailable, return empty suggestions
    if not ollama.is_available():
        logger.warning("Ollama not available for link suggestions")
        return LinkSuggestionsResponse(suggestions=[], count=0)

    # Get all other notes (exclude current note and its existing links)
    all_notes = notes_service.list_notes(is_admin=True)
    existing_links = set(note.get("links", []))
    existing_links.add(note_id)  # Don't suggest linking to self

    candidate_notes = [
        n for n in all_notes
        if n["id"] not in existing_links and n.get("content")  # Must have content
    ]

    if not candidate_notes:
        logger.info("No candidate notes for link suggestions")
        return LinkSuggestionsResponse(suggestions=[], count=0)

    # Build prompt for LLM
    current_title = note.get("title", note_id)
    current_content = note.get("content", "")

    # Format candidate notes for the prompt (limit to first 50 to avoid token limits)
    candidates_text = "\n\n".join([
        f"ID: {n['id']}\nTitle: {n.get('title', 'Untitled')}\nContent: {n.get('content', '')[:200]}..."
        for n in candidate_notes[:50]
    ])

    prompt = f"""You are analyzing a note to suggest related notes that should be linked.

Current Note:
Title: {current_title}
Content:
{current_content[:500]}

Candidate Notes to Link:
{candidates_text}

Suggest 3-5 notes that are most related to the current note. Focus on:
- Directly related concepts or prerequisites
- Practical applications or examples
- Contrasting viewpoints
- Building blocks or dependencies

For each suggestion, provide:
- note_id: The ID of the note to link to
- confidence: Float 0-1 indicating relevance
- reason: Brief explanation of why they should be linked

Return ONLY a JSON array of suggestions.
Example: [{{"note_id": "psychological-safety", "confidence": 0.85, "reason": "Both discuss team culture"}}]

JSON:"""

    try:
        # Use qwen2.5:1.5b for structured output
        response_data = ollama.client.generate(
            model="qwen2.5:1.5b",
            prompt=prompt,
            options={"num_ctx": 8192}  # Larger context for multiple notes
        )

        response = response_data.get("response", "")
        if not response:
            logger.error("Empty response from Ollama for link suggestions")
            return LinkSuggestionsResponse(suggestions=[], count=0)

        # Parse JSON response (same defensive parsing as suggest-tags)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        # Try to parse as array first
        try:
            suggestions_data = json.loads(response)
            if isinstance(suggestions_data, dict):
                suggestions_data = [suggestions_data]
            elif not isinstance(suggestions_data, list):
                logger.error("Unexpected response format from LLM: %s", type(suggestions_data))
                return LinkSuggestionsResponse(suggestions=[], count=0)
        except json.JSONDecodeError:
            # Try line-by-line parsing
            suggestions_data = []
            for line in response.split('\n'):
                line = line.strip()
                if line and line.startswith('{'):
                    try:
                        obj = json.loads(line)
                        suggestions_data.append(obj)
                    except json.JSONDecodeError:
                        continue

            if not suggestions_data:
                logger.error("Could not parse any JSON from response")
                logger.error("Full response was: %s", response[:500])
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

    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON from Ollama response: %s", e)
        logger.error("Full response was: %s", response[:500])
        return LinkSuggestionsResponse(suggestions=[], count=0)
    except Exception as e:
        logger.error("Error generating link suggestions: %s", e)
        return LinkSuggestionsResponse(suggestions=[], count=0)
