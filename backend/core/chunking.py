"""Pure document chunking logic for embeddings (Functional Core).

Whole-document embeddings dilute topical signal in longer documents (#192):
a query matching one section gets averaged away by the rest of the article.
Chunking embeds sections separately so a strong local match ranks the
document highly.

All functions are pure: no I/O, deterministic.
"""

import re

# Target size keeps chunks comfortably inside embedding-model context windows
# while staying large enough to carry meaning. Characters, not tokens: close
# enough for chunk sizing and avoids a tokenizer dependency.
CHUNK_TARGET_CHARS = 1500
# Paragraphs longer than this are hard-split (rare: giant code blocks/tables)
CHUNK_MAX_CHARS = 2500

_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)


def _split_sections(content: str) -> list[str]:
    """Split markdown into sections at heading boundaries.

    Each section starts at a heading line (or the document start) and runs to
    the next heading. Headings stay with their section so chunks keep their
    local context.
    """
    starts = [m.start() for m in _HEADING_RE.finditer(content)]
    if not starts:
        return [content]

    boundaries = ([0] if starts[0] != 0 else []) + starts + [len(content)]
    sections = [content[a:b] for a, b in zip(boundaries, boundaries[1:], strict=False)]
    return [s for s in sections if s.strip()]


def _split_oversized(text: str, max_chars: int) -> list[str]:
    """Hard-split text that exceeds max_chars, preferring paragraph breaks."""
    if len(text) <= max_chars:
        return [text]

    pieces: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            pieces.append(current)
        # A single paragraph over the limit gets sliced at the limit
        while len(paragraph) > max_chars:
            pieces.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars:]
        current = paragraph
    if current.strip():
        pieces.append(current)
    return pieces


def chunk_document(
    title: str,
    content: str,
    target_chars: int = CHUNK_TARGET_CHARS,
    max_chars: int = CHUNK_MAX_CHARS,
) -> list[str]:
    """Split a document into embedding-sized chunks, title prefixed to each.

    Sections (split at markdown headings) are packed greedily into chunks of
    roughly target_chars. The title is prepended to every chunk so title terms
    contribute to every chunk's embedding (previously titles were not embedded
    at all - part of the #192 miss).

    Short documents produce a single chunk, which keeps behavior for typical
    notes identical to whole-document embedding (plus the title).

    Args:
        title: Document title, prepended to each chunk
        content: Markdown content
        target_chars: Soft chunk size; sections are packed up to this
        max_chars: Hard limit; oversized sections are split

    Returns:
        List of chunk texts (at least one, unless title and content are empty)
    """
    title = title.strip()
    content = content.strip()

    if not content:
        return [title] if title else []

    sections: list[str] = []
    for section in _split_sections(content):
        sections.extend(_split_oversized(section.strip(), max_chars))

    # Greedily pack sections into chunks up to target_chars
    chunks: list[str] = []
    current = ""
    for section in sections:
        candidate = f"{current}\n\n{section}" if current else section
        if current and len(candidate) > target_chars:
            chunks.append(current)
            current = section
        else:
            current = candidate
    if current:
        chunks.append(current)

    if title:
        return [f"{title}\n\n{chunk}" for chunk in chunks]
    return chunks
