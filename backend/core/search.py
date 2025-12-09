"""Pure functions for search-related operations.

This module contains stateless, side-effect-free functions for search
functionality like snippet extraction and text matching.
"""


def extract_snippet(
    content: str,
    query: str,
    context_chars: int = 80,
    max_snippet_length: int = 200,
) -> str:
    """Extract a contextual snippet around the first match of query in content.

    Finds the first occurrence of the query (case-insensitive) and returns
    surrounding context. If no match is found, returns the beginning of content.

    Args:
        content: The full text content to search
        query: The search query to find
        context_chars: Characters to show before/after match
        max_snippet_length: Maximum total snippet length

    Returns:
        A snippet string with ellipsis indicators if truncated.
        Format: "...text before **match** text after..."

    Examples:
        >>> extract_snippet("The quick brown fox jumps over the lazy dog", "fox")
        'The quick brown fox jumps over the lazy dog'

        >>> extract_snippet("Long intro... the systems fail here", "systems", 20)
        '...the systems fail here...'
    """
    if not content or not query:
        return content[:max_snippet_length] if content else ""

    query_lower = query.lower().strip()
    content_lower = content.lower()

    # Find first match position
    match_pos = content_lower.find(query_lower)

    if match_pos == -1:
        # No match found - return beginning of content
        snippet = content[:max_snippet_length].strip()
        if len(content) > max_snippet_length:
            # Find last word boundary to avoid cutting mid-word
            last_space = snippet.rfind(" ")
            if last_space > max_snippet_length * 0.7:
                snippet = snippet[:last_space]
            snippet += "..."
        return snippet

    # Calculate window around match
    start = max(0, match_pos - context_chars)
    end = min(len(content), match_pos + len(query) + context_chars)

    # Adjust to not exceed max length
    if end - start > max_snippet_length:
        # Center around match as much as possible
        half_length = max_snippet_length // 2
        start = max(0, match_pos - half_length)
        end = min(len(content), start + max_snippet_length)

    # Extract snippet
    snippet = content[start:end]

    # Clean up word boundaries
    if start > 0:
        # Find first word boundary to avoid starting mid-word
        first_space = snippet.find(" ")
        if first_space != -1 and first_space < 20:
            snippet = snippet[first_space + 1 :]
        snippet = "..." + snippet

    if end < len(content):
        # Find last word boundary to avoid ending mid-word
        last_space = snippet.rfind(" ")
        if last_space != -1 and len(snippet) - last_space < 20:
            snippet = snippet[:last_space]
        snippet = snippet + "..."

    return snippet.strip()


def extract_multiple_snippets(
    content: str,
    query: str,
    max_snippets: int = 2,
    context_chars: int = 60,
    max_snippet_length: int = 150,
) -> list[str]:
    """Extract multiple contextual snippets for different match locations.

    Useful for showing multiple relevant portions of a long document.

    Args:
        content: The full text content to search
        query: The search query to find
        max_snippets: Maximum number of snippets to return
        context_chars: Characters to show before/after each match
        max_snippet_length: Maximum length per snippet

    Returns:
        List of snippet strings, up to max_snippets.
    """
    if not content or not query:
        return [content[:max_snippet_length]] if content else []

    query_lower = query.lower().strip()
    content_lower = content.lower()

    # Find all match positions
    matches: list[int] = []
    pos = 0
    while len(matches) < max_snippets * 2:  # Find more than we need to filter
        pos = content_lower.find(query_lower, pos)
        if pos == -1:
            break
        matches.append(pos)
        pos += len(query_lower)

    if not matches:
        return [extract_snippet(content, query, context_chars, max_snippet_length)]

    # Filter to non-overlapping matches (at least max_snippet_length apart)
    filtered_matches = [matches[0]]
    for match_pos in matches[1:]:
        if match_pos - filtered_matches[-1] >= max_snippet_length:
            filtered_matches.append(match_pos)
            if len(filtered_matches) >= max_snippets:
                break

    # Generate snippets for each match
    snippets = []
    for match_pos in filtered_matches[:max_snippets]:
        start = max(0, match_pos - context_chars)
        end = min(len(content), match_pos + len(query) + context_chars)

        snippet = content[start:end]

        # Clean up boundaries
        if start > 0:
            first_space = snippet.find(" ")
            if first_space != -1 and first_space < 15:
                snippet = snippet[first_space + 1 :]
            snippet = "..." + snippet

        if end < len(content):
            last_space = snippet.rfind(" ")
            if last_space != -1 and len(snippet) - last_space < 15:
                snippet = snippet[:last_space]
            snippet = snippet + "..."

        snippets.append(snippet.strip())

    return snippets


def find_best_match_position(content: str, query: str) -> int | None:
    """Find the position of the best match for query in content.

    Currently returns first match position, but could be extended
    to find "best" match based on word boundaries, proximity to
    start of sentences, etc.

    Args:
        content: The text to search
        query: The search term

    Returns:
        Character position of match, or None if not found.
    """
    if not content or not query:
        return None

    pos = content.lower().find(query.lower().strip())
    return pos if pos != -1 else None
