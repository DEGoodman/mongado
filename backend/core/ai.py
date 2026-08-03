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

    similarity: float = dot_product / (magnitude1 * magnitude2)
    return similarity


def rank_documents_by_similarity(
    query_embedding: list[float], documents_with_embeddings: list[dict[str, Any]], top_k: int = 5
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


def mean_vector(vectors: list[list[float]]) -> list[float]:
    """Element-wise mean of equal-length vectors.

    Pure function: No I/O, no side effects, deterministic.

    Used to derive a whole-document embedding from its chunk embeddings
    without extra embedding-API calls. Magnitude is irrelevant for cosine
    similarity, so the mean is not re-normalized.

    Args:
        vectors: Non-empty list of equal-length vectors

    Returns:
        Mean vector ([] for empty input)
    """
    if not vectors:
        return []
    dim = len(vectors[0])
    if any(len(v) != dim for v in vectors):
        logger.warning("mean_vector: mismatched vector lengths, returning []")
        return []
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]


def rank_parents_by_chunk_similarity(
    query_embedding: list[float],
    chunks: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Rank parent documents by their best-matching chunk (#192).

    Pure function: No I/O, no side effects, deterministic.

    Max-aggregation is the point: a document with one strongly matching
    section ranks on that section alone, instead of having the signal
    diluted across the whole document.

    Args:
        query_embedding: Query embedding vector
        chunks: Chunk dicts with 'parent_id', 'parent_type', 'embedding'
        top_k: Maximum number of parents to return

    Returns:
        Top K parents as {'id', 'type', 'score'} sorted by score descending
    """
    best: dict[tuple[str, str], float] = {}
    for chunk in chunks:
        embedding = chunk.get("embedding")
        if not embedding:
            continue
        key = (chunk["parent_type"], chunk["parent_id"])
        similarity = cosine_similarity(query_embedding, embedding)
        if similarity > best.get(key, -1.0):
            best[key] = similarity

    ranked = sorted(best.items(), key=lambda item: item[1], reverse=True)
    return [
        {"id": parent_id, "type": parent_type, "score": score}
        for (parent_type, parent_id), score in ranked[:top_k]
    ]


def build_context_from_documents(documents: list[dict[str, Any]], max_docs: int = 5) -> str:
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
    question: str, context_documents: list[dict[str, Any]], allow_general_knowledge: bool = True
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


# Character budget for synthesis context (#166).
#
# Synthesis pulls ~12 full documents rather than the 5 short excerpts used by
# build_qa_prompt, so an unbounded context can blow past the model's context
# window. Token math: local/hosted models we route to (llama3.2, qwen2.5,
# Groq/Gemini defaults) are typically run with num_ctx in the 4096-8192 range.
# Using the common ~4 chars/token estimate, 8192 tokens is ~32800 chars total.
# Reserve room for the prompt template/instructions (~1000 chars) and the
# model's own response (~2000-3000 tokens / ~10000 chars), leaving roughly
# 20000 chars of headroom for document context. Round down for safety margin.
SYNTHESIS_CONTEXT_CHAR_BUDGET = 18000


def build_synthesis_prompt(
    query: str,
    context_documents: list[dict[str, Any]],
    max_docs: int = 12,
    max_context_chars: int = SYNTHESIS_CONTEXT_CHAR_BUDGET,
) -> str:
    """Build a deep-synthesis prompt across many documents (#166).

    Unlike build_qa_prompt (short answer from a handful of excerpts), this
    asks the model to synthesize a structured markdown summary across up to
    `max_docs` full documents. Because whole documents (not short excerpts)
    are included, each document is truncated to a share of
    `max_context_chars` so the combined context stays within the model's
    context window.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        query: The topic/question to synthesize knowledge about
        context_documents: Relevant documents with 'title' and 'content'
        max_docs: Maximum number of documents to include
        max_context_chars: Character budget for the combined document context

    Returns:
        Complete prompt string for LLM, instructing markdown output with a
        fixed section structure (Key Concepts / Your Positions / Gaps &
        Open Questions) and inline citation by source title.
    """
    docs = context_documents[:max_docs]

    if docs:
        # Split the budget evenly across the documents actually included, so
        # a shorter document list gets more room per document instead of
        # always truncating to a worst-case (max_docs-sized) slice.
        per_doc_budget = max(max_context_chars // len(docs), 200)
        parts = []
        for i, doc in enumerate(docs, 1):
            title = doc.get("title", f"Document {i}")
            content = doc.get("content", "")
            if len(content) > per_doc_budget:
                content = content[:per_doc_budget].rstrip() + "\n... [truncated]"
            parts.append(f"### {title}\n{content}\n")
        context = "\n".join(parts)
    else:
        context = "No relevant documents were found in the knowledge base."

    return f"""You are synthesizing knowledge from a personal knowledge base to answer a broad query.

Knowledge Base Documents:
{context}

Query: {query}

Instructions:
1. Write a cohesive synthesis in markdown using EXACTLY these three section headers, in this order:
   ## Key Concepts
   ## Your Positions
   ## Gaps & Open Questions
2. "Key Concepts": summarize the main ideas and themes found across the documents.
3. "Your Positions": summarize the specific arguments, opinions, or conclusions expressed in the documents (this is the author's own knowledge base, so frame it as their thinking).
4. "Gaps & Open Questions": call out topics related to the query that the documents do NOT cover, or where the documents are thin, contradictory, or inconclusive.
5. Cite sources inline using the document's title in parentheses, e.g. "(Incident Response Basics)", right after the claim it supports.
6. Do not invent information. If the knowledge base does not cover an aspect of the query, say so plainly in "Gaps & Open Questions" instead of filling the gap with general knowledge.
7. If no documents were found at all, say so plainly and keep all three section headers with a brief note that the knowledge base has no coverage yet.

Synthesis:"""


# Editor slash commands (#146 Phase 1).
#
# Character budget for the note-context portion of an editor-command prompt.
# Mirrors SYNTHESIS_CONTEXT_CHAR_BUDGET's reasoning but scaled down: unlike
# synthesis (many full documents), this is a single note's content used only
# as background so the transformed text matches the note's voice - a much
# smaller budget is plenty and keeps the prompt fast to generate.
EDITOR_CONTEXT_CHAR_BUDGET = 4000

# Text-transform commands handled by build_editor_command_prompt. "link" is a
# valid editor command too (see routers/ai.py) but is not a text transform -
# it runs the link-suggestion retrieval/prompt path instead, so it is
# deliberately excluded here and rejected by this function.
EDITOR_TRANSFORM_COMMANDS = ("expand", "simplify", "summarize", "continue", "rephrase")

# All commands the editor-assist endpoints accept, including "link".
EDITOR_COMMANDS = (*EDITOR_TRANSFORM_COMMANDS, "link")

_EDITOR_COMMAND_INSTRUCTIONS: dict[str, str] = {
    "expand": (
        "Expand the following text with more detail, examples, or explanation, "
        "matching the voice and tone of the surrounding note. Return ONLY the "
        "expanded replacement text - no preamble, no markdown fences, no "
        "commentary.\n\nText to expand:\n{selected_text}"
    ),
    "simplify": (
        "Simplify the following text: use plainer language and shorter "
        "sentences while preserving its meaning. Return ONLY the simplified "
        "replacement text - no preamble, no markdown fences, no "
        "commentary.\n\nText to simplify:\n{selected_text}"
    ),
    "summarize": (
        "Summarize the following text concisely, preserving its key points. "
        "Return ONLY the summary text - no preamble, no markdown fences, no "
        "commentary.\n\nText to summarize:\n{selected_text}"
    ),
    "continue": (
        "Continue writing directly from where the following text leaves off, "
        "matching its voice, tone, and train of thought. Return ONLY the new "
        "continuation text (do not repeat any of the input) - no preamble, no "
        "markdown fences, no commentary.\n\nText so far:\n{selected_text}"
    ),
    "rephrase": (
        "Rephrase the following text with alternative wording while "
        "preserving its meaning and tone. Return ONLY the rephrased "
        "replacement text - no preamble, no markdown fences, no "
        "commentary.\n\nText to rephrase:\n{selected_text}"
    ),
}


def build_editor_command_prompt(
    command: str,
    selected_text: str,
    note_title: str | None = None,
    note_content: str | None = None,
    max_context_chars: int = EDITOR_CONTEXT_CHAR_BUDGET,
) -> str:
    """Build a prompt for an editor slash-command text transform (#146).

    Pure function: No I/O, no side effects, deterministic.

    Covers the five text-transform commands (expand, simplify, summarize,
    continue, rephrase). "link" is a distinct retrieval-backed command
    handled separately in routers/ai.py and is rejected here.

    Args:
        command: One of EDITOR_TRANSFORM_COMMANDS
        selected_text: The text the command operates on (selection, current
            paragraph, or preceding text, depending on command - decided by
            the caller/frontend)
        note_title: Title of the note being edited, for voice/context
        note_content: Full content of the note being edited, for voice/context
            (truncated to max_context_chars)
        max_context_chars: Character budget for the note_content portion

    Returns:
        Complete prompt string for LLM, instructing it to return only the
        replacement/continuation prose with no preamble or commentary.

    Raises:
        ValueError: If command is not a recognized text-transform command
    """
    if command not in EDITOR_TRANSFORM_COMMANDS:
        raise ValueError(
            f"Unknown editor command: {command!r}. Must be one of {EDITOR_TRANSFORM_COMMANDS}"
        )

    instruction = _EDITOR_COMMAND_INSTRUCTIONS[command].format(selected_text=selected_text)

    context_parts = []
    if note_title:
        context_parts.append(f"Note title: {note_title}")
    if note_content:
        content = note_content
        if len(content) > max_context_chars:
            content = content[:max_context_chars].rstrip() + "\n... [truncated]"
        context_parts.append(f"Full note content (for context/voice only):\n{content}")

    if context_parts:
        context_block = "\n\n".join(context_parts)
        return (
            f"You are helping write a personal knowledge-base note. Use the "
            f"note context below only to match its voice and topic - do not "
            f"summarize or reference the context itself in your output.\n\n"
            f"{context_block}\n\n{instruction}"
        )

    return instruction


def build_summary_prompt(content: str, content_type: str = "article") -> str:
    """Build prompt for content summarization.

    Pure function: No I/O, no side effects, deterministic.

    Args:
        content: Content to summarize
        content_type: Type of content ("article" or "note")

    Returns:
        Complete prompt string for LLM
    """
    if content_type == "note":
        return f"""Please provide a concise 1-2 sentence summary of this note:

{content[:2000]}

Summary:"""
    else:
        return f"""Please provide a concise 2-3 sentence summary of this article:

{content}

Summary:"""


def build_tag_suggestion_prompt(
    title: str, content: str, current_tags: list[str], existing_tags: set[str]
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
    all_notes: list[dict[str, Any]], current_note_id: str, existing_links: list[str]
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

    return [note for note in all_notes if note["id"] not in excluded_ids and note.get("content")]


def build_link_suggestion_prompt(
    current_title: str,
    current_content: str,
    candidate_notes: list[dict[str, Any]],
    max_candidates: int = 50,
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
    candidates_text = "\n\n".join(
        [
            f"ID: {n['id']}\nTitle: {n.get('title', 'Untitled')}\nContent: {n.get('content', '')[:200]}..."
            for n in candidate_notes[:max_candidates]
        ]
    )

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


def extract_json_payload(text: str, opener: str = "[") -> str | None:
    """Extract the first balanced JSON array or object from surrounding text.

    Pure function: No I/O, no side effects, deterministic.

    Small models routinely wrap their output in prose ("Sure! Here is the
    JSON: [...] Hope that helps!"). Bracket matching recovers the payload
    where a plain json.loads fails. Quote- and escape-aware, so brackets
    inside string values do not throw off the depth count.

    Args:
        text: Raw text that may contain a JSON payload
        opener: "[" for arrays, "{" for objects

    Returns:
        The JSON substring, or None if no balanced payload is found
    """
    closer = "]" if opener == "[" else "}"

    start = text.find(opener)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]

        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None


def parse_json_response(
    raw_response: str, expected_type: str = "array"
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
        # Fallback 1: the payload is embedded in prose ("Here is the JSON: [...]")
        opener = "[" if expected_type == "array" else "{"
        extracted = extract_json_payload(response, opener=opener)
        if extracted is not None:
            try:
                data = json.loads(extracted)
                if expected_type == "array":
                    if isinstance(data, dict):
                        return [data]
                    if isinstance(data, list):
                        return data
                elif isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass

        # Fallback 2: newline-delimited JSON objects (some models emit these)
        if expected_type == "array":
            parsed_objects = []
            for line in response.split("\n"):
                line = line.strip()
                if line and line.startswith("{"):
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
