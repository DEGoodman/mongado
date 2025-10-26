"""Pure business logic for AI features (Functional Core).

This module contains pure functions with no I/O or side effects.
All functions are deterministic and fully unit-testable.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Cosine similarity score (0.0 to 1.0)
    """
    if len(vec1) != len(vec2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def rank_documents_by_similarity(
    query_embedding: list[float],
    documents_with_embeddings: list[dict[str, Any]],
    top_k: int = 5
) -> list[dict[str, Any]]:
    """Rank documents by cosine similarity to query embedding.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        query_embedding: Query embedding vector
        documents_with_embeddings: Documents with 'embedding' field
        top_k: Maximum number of results to return

    Returns:
        Top K documents sorted by similarity (highest first) with 'score' field added
    """
    scored_docs: list[tuple[float, dict[str, Any]]] = []

    for doc in documents_with_embeddings:
        doc_embedding = doc.get("embedding")
        if not doc_embedding:
            continue

        # Calculate similarity
        similarity = cosine_similarity(query_embedding, doc_embedding)

        # Add score to document (non-destructive)
        doc_with_score = {**doc, "score": similarity}
        scored_docs.append((similarity, doc_with_score))

    # Sort by similarity (highest first) and take top_k
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored_docs[:top_k]]


def build_context_from_documents(
    documents: list[dict[str, Any]],
    max_docs: int = 5
) -> str:
    """Build context string from documents for AI prompts.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        documents: List of documents with 'title' and 'content' fields
        max_docs: Maximum number of documents to include

    Returns:
        Formatted context string
    """
    if not documents:
        return "No relevant documents found."

    context_parts = []
    for i, doc in enumerate(documents[:max_docs], 1):
        title = doc.get("title", f"Document {i}")
        content = doc.get("content", "")
        context_parts.append(f"### {title}\n{content}\n")

    return "\n".join(context_parts)


def build_qa_prompt(
    question: str,
    context_documents: list[dict[str, Any]],
    allow_general_knowledge: bool = True
) -> str:
    """Build Q&A prompt with context and instructions.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        question: User's question
        context_documents: Relevant documents for context
        allow_general_knowledge: Allow answering from general knowledge if KB insufficient

    Returns:
        Complete prompt string for LLM
    """
    context = build_context_from_documents(context_documents, max_docs=5)

    if allow_general_knowledge:
        prompt = f"""You are a helpful AI assistant with access to a knowledge base.

Knowledge Base Articles:
{context}

Question: {question}

Instructions:
1. First check if the knowledge base articles contain relevant information
2. If the KB has the answer, cite it and use that information
3. If the KB doesn't have enough info, you may answer from your general knowledge
4. Be clear about whether you're using KB articles or general knowledge
5. If you can't answer confidently, say so

Answer:"""
    else:
        # KB-only mode (stricter)
        prompt = f"""Based on the following knowledge base articles, please answer the question.
If the answer is not in the provided articles, say "I don't have enough information in the knowledge base to answer that question."

Knowledge Base:
{context}

Question: {question}

Answer:"""

    return prompt


def build_summary_prompt(content: str) -> str:
    """Build prompt for article summarization.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        content: Article content to summarize

    Returns:
        Complete prompt string for LLM
    """
    return f"""Please provide a concise 2-3 sentence summary of this article:

{content}

Summary:"""


def build_tag_suggestion_prompt(
    title: str,
    content: str,
    current_tags: list[str],
    existing_tags: set[str]
) -> str:
    """Build prompt for AI tag suggestions.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        title: Note title
        content: Note content (will be truncated to 1000 chars)
        current_tags: Tags already on this note
        existing_tags: All tags in the knowledge base

    Returns:
        Complete prompt string for LLM
    """
    existing_tags_str = ", ".join(sorted(existing_tags)) if existing_tags else "None yet"
    current_tags_str = ", ".join(current_tags) if current_tags else "None"

    return f"""Analyze this note and suggest 2-4 relevant tags.

Note Title: {title}
Note Content:
{content[:1000]}

Current Tags: {current_tags_str}
Existing tags in knowledge base: {existing_tags_str[:200]}

Focus on:
- Topic/domain (e.g., "management", "sre", "pkm", "devops")
- Type (e.g., "framework", "concept", "practice", "mental-model")
- Avoid duplicating current tags
- Prefer tags already in use when appropriate

Return ONLY a JSON array of suggestions, each with: tag, confidence (0-1), reason
Example: [{{"tag": "management", "confidence": 0.9, "reason": "Discusses leadership and team dynamics"}}]

JSON:"""


def filter_link_candidates(
    all_notes: list[dict[str, Any]],
    current_note_id: str,
    existing_links: list[str]
) -> list[dict[str, Any]]:
    """Filter notes to get valid link candidates.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        all_notes: All notes in the system
        current_note_id: ID of the current note
        existing_links: IDs of notes already linked from current note

    Returns:
        List of candidate notes (excluding current note and existing links)
    """
    excluded_ids = set(existing_links)
    excluded_ids.add(current_note_id)

    return [
        note for note in all_notes
        if note["id"] not in excluded_ids and note.get("content")
    ]


def build_link_suggestion_prompt(
    current_title: str,
    current_content: str,
    candidate_notes: list[dict[str, Any]],
    max_candidates: int = 50
) -> str:
    """Build prompt for AI link suggestions.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        current_title: Title of the current note
        current_content: Content of the current note (truncated to 500 chars)
        candidate_notes: List of candidate notes to suggest
        max_candidates: Maximum number of candidates to include in prompt

    Returns:
        Complete prompt string for LLM
    """
    # Format candidate notes for the prompt (limit to avoid token limits)
    candidates_text = "\n\n".join([
        f"ID: {n['id']}\nTitle: {n.get('title', 'Untitled')}\nContent: {n.get('content', '')[:200]}..."
        for n in candidate_notes[:max_candidates]
    ])

    return f"""You are analyzing a note to suggest related notes that should be linked.

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


def parse_json_response(
    raw_response: str,
    expected_type: str = "array"
) -> list[dict[str, Any]] | dict[str, Any] | None:
    """Defensively parse JSON response from LLM.

    Pure function: No I/O, no side effects, deterministic.
    Handles common LLM output issues (markdown wrappers, line-by-line JSON).

    Args:
        raw_response: Raw text response from LLM
        expected_type: Expected JSON type ("array" or "object")

    Returns:
        Parsed JSON data or None if parsing fails
    """
    if not raw_response:
        return None

    response = raw_response.strip()

    # Strip markdown code block wrappers
    if response.startswith("```json"):
        response = response[7:]
    if response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]

    response = response.strip()

    # Try standard JSON parsing first
    try:
        data = json.loads(response)

        # Normalize to expected type
        if expected_type == "array":
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
            else:
                logger.warning("Unexpected JSON type: %s (expected array)", type(data))
                return None
        else:  # expected_type == "object"
            if isinstance(data, dict):
                return data
            else:
                logger.warning("Unexpected JSON type: %s (expected object)", type(data))
                return None

    except json.JSONDecodeError:
        # Fallback: Try line-by-line parsing (some models output newline-delimited JSON)
        if expected_type == "array":
            parsed_objects = []
            for line in response.split('\n'):
                line = line.strip()
                if line and line.startswith('{'):
                    try:
                        obj = json.loads(line)
                        parsed_objects.append(obj)
                    except json.JSONDecodeError:
                        continue

            if parsed_objects:
                return parsed_objects

        logger.error("Failed to parse JSON response")
        logger.debug("Raw response (first 500 chars): %s", raw_response[:500])
        return None
