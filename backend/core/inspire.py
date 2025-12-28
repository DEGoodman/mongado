"""Pure business logic for content inspiration features (Functional Core).

This module contains pure functions with no I/O or side effects.
All functions are deterministic and fully unit-testable.
"""

import json
import logging
from typing import Any

from core.ai import cosine_similarity

logger = logging.getLogger(__name__)


def find_underdeveloped_topics(
    notes: list[dict[str, Any]],
    min_content_length: int = 500,
    max_links: int = 1,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Find notes that are short and have few connections.

    Pure function: No I/O, no side effects, deterministic.
    Identifies notes that could benefit from expansion or more links.

    Args:
        notes: List of notes with content_length, link_count, backlink_count
        min_content_length: Notes shorter than this are considered underdeveloped
        max_links: Notes with this many or fewer total links are candidates
        limit: Maximum results to return

    Returns:
        List of underdeveloped notes sorted by potential (shortest first)
    """
    underdeveloped = []

    for note in notes:
        content_length = note.get("content_length", len(note.get("content", "")))
        link_count = note.get("link_count", 0)
        backlink_count = note.get("backlink_count", 0)
        total_links = link_count + backlink_count

        # Check if note qualifies as underdeveloped
        is_short = content_length < min_content_length
        has_few_links = total_links <= max_links

        if is_short or has_few_links:
            underdeveloped.append(
                {
                    "note_id": note["id"],
                    "title": note.get("title", note["id"]),
                    "content_length": content_length,
                    "link_count": link_count,
                    "backlink_count": backlink_count,
                    "is_short": is_short,
                    "has_few_links": has_few_links,
                }
            )

    # Sort by content length (shortest first) to prioritize most underdeveloped
    underdeveloped.sort(key=lambda x: x["content_length"])
    return underdeveloped[:limit]


def find_unlinked_similar_notes(
    note_embeddings: list[tuple[str, str, list[float]]],
    existing_links: dict[str, set[str]],
    similarity_threshold: float = 0.7,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Find semantically similar notes that aren't linked to each other.

    Pure function: No I/O, no side effects, deterministic.
    Identifies connection opportunities based on semantic similarity.

    Args:
        note_embeddings: List of (note_id, title, embedding) tuples
        existing_links: Dict mapping note_id -> set of linked note_ids (bidirectional)
        similarity_threshold: Minimum cosine similarity to consider (0.0 to 1.0)
        limit: Maximum results to return

    Returns:
        List of connection opportunities with similarity scores
    """
    opportunities: list[dict[str, Any]] = []
    n = len(note_embeddings)

    # Compare all pairs (only check each pair once)
    for i in range(n):
        note_a_id, note_a_title, embedding_a = note_embeddings[i]

        for j in range(i + 1, n):
            note_b_id, note_b_title, embedding_b = note_embeddings[j]

            # Skip if already linked (check both directions)
            a_links = existing_links.get(note_a_id, set())
            b_links = existing_links.get(note_b_id, set())
            if note_b_id in a_links or note_a_id in b_links:
                continue

            # Calculate similarity
            similarity = cosine_similarity(embedding_a, embedding_b)

            if similarity >= similarity_threshold:
                opportunities.append(
                    {
                        "note_a_id": note_a_id,
                        "note_a_title": note_a_title,
                        "note_b_id": note_b_id,
                        "note_b_title": note_b_title,
                        "similarity": round(similarity, 3),
                    }
                )

    # Sort by similarity (highest first)
    opportunities.sort(key=lambda x: float(x["similarity"]), reverse=True)
    return opportunities[:limit]


def build_inspiration_prompt(
    gap_notes: list[dict[str, Any]],
    connection_opportunities: list[dict[str, Any]],
) -> str:
    """Build prompt for Ollama to generate human-friendly suggestions.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        gap_notes: Underdeveloped notes from find_underdeveloped_topics()
        connection_opportunities: Connections from find_unlinked_similar_notes()

    Returns:
        Complete prompt string for LLM
    """
    gap_section = ""
    if gap_notes:
        gap_items = []
        for note in gap_notes[:5]:
            reasons = []
            if note.get("is_short"):
                reasons.append(f"only {note['content_length']} chars")
            if note.get("has_few_links"):
                total = note.get("link_count", 0) + note.get("backlink_count", 0)
                reasons.append(f"only {total} connections")
            reason_str = ", ".join(reasons)
            gap_items.append(f"- \"{note['title']}\" ({reason_str})")
        gap_section = "Knowledge Gaps (underdeveloped notes):\n" + "\n".join(gap_items)

    conn_section = ""
    if connection_opportunities:
        conn_items = []
        for conn in connection_opportunities[:5]:
            conn_items.append(
                f"- \"{conn['note_a_title']}\" and \"{conn['note_b_title']}\" "
                f"(similarity: {conn['similarity']:.0%})"
            )
        conn_section = "Connection Opportunities (similar but unlinked):\n" + "\n".join(
            conn_items
        )

    sections = [s for s in [gap_section, conn_section] if s]
    analysis = "\n\n".join(sections) if sections else "No significant gaps or opportunities found."

    return f"""You are helping a knowledge base owner improve their notes.
Based on this analysis, provide 3-5 actionable suggestions.

{analysis}

For each suggestion, provide:
- type: "gap" (expand content) or "connection" (add link)
- title: A short, actionable title (e.g., "Expand: Technical Debt" or "Connect: Leadership & Motivation")
- description: 1-2 sentences explaining why and how to improve
- related_notes: Array of note IDs involved
- action_text: Short button label (e.g., "Edit Note" or "Add Link")

Return ONLY a JSON array of suggestions.
Example: [{{"type": "gap", "title": "Expand: Note Title", "description": "...", "related_notes": ["note-id"], "action_text": "Edit Note"}}]

JSON:"""


def parse_inspiration_response(raw_response: str) -> list[dict[str, Any]]:
    """Parse LLM response into structured suggestions.

    Pure function: No I/O, no side effects, deterministic.
    Handles common LLM output issues (markdown wrappers, etc.).

    Args:
        raw_response: Raw text response from LLM

    Returns:
        List of parsed suggestion dicts, or empty list if parsing fails
    """
    if not raw_response:
        return []

    response = raw_response.strip()

    # Strip markdown code block wrappers
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]

    response = response.strip()

    try:
        data = json.loads(response)

        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            logger.warning("Unexpected JSON type: %s (expected array)", type(data))
            return []

        # Validate each suggestion has required fields
        valid_suggestions = []
        required_fields = {"type", "title", "description", "related_notes", "action_text"}

        for item in data:
            if not isinstance(item, dict):
                continue
            if not required_fields.issubset(item.keys()):
                missing = required_fields - set(item.keys())
                logger.debug("Suggestion missing fields: %s", missing)
                continue
            if item["type"] not in ("gap", "connection"):
                logger.debug("Invalid suggestion type: %s", item["type"])
                continue
            valid_suggestions.append(item)

        return valid_suggestions

    except json.JSONDecodeError:
        logger.error("Failed to parse inspiration response as JSON")
        logger.debug("Raw response (first 500 chars): %s", raw_response[:500])
        return []


def build_fallback_suggestions(
    gap_notes: list[dict[str, Any]],
    connection_opportunities: list[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Build suggestions without LLM (fallback when Ollama unavailable).

    Pure function: No I/O, no side effects, deterministic.

    Args:
        gap_notes: Underdeveloped notes from find_underdeveloped_topics()
        connection_opportunities: Connections from find_unlinked_similar_notes()
        limit: Maximum suggestions to return

    Returns:
        List of suggestion dicts
    """
    suggestions = []

    # Add gap suggestions
    for note in gap_notes:
        reasons = []
        if note.get("is_short"):
            reasons.append(f"only {note['content_length']} characters")
        if note.get("has_few_links"):
            total = note.get("link_count", 0) + note.get("backlink_count", 0)
            reasons.append(f"only {total} connections")
        reason_str = " and ".join(reasons)

        suggestions.append(
            {
                "type": "gap",
                "title": f"Expand: {note['title']}",
                "description": f"This note has {reason_str}. Consider expanding the content or adding links to related notes.",
                "related_notes": [note["note_id"]],
                "action_text": "Edit Note",
            }
        )

    # Add connection suggestions
    for conn in connection_opportunities:
        suggestions.append(
            {
                "type": "connection",
                "title": f"Connect: {conn['note_a_title'][:20]}... & {conn['note_b_title'][:20]}...",
                "description": f"These notes are {conn['similarity']:.0%} similar but not linked. Consider adding a wikilink.",
                "related_notes": [conn["note_a_id"], conn["note_b_id"]],
                "action_text": "Add Link",
            }
        )

    return suggestions[:limit]
