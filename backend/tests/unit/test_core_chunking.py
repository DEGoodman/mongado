"""Unit tests for core.chunking (pure document chunking, #192)."""

from core.chunking import CHUNK_MAX_CHARS, CHUNK_TARGET_CHARS, chunk_document


class TestChunkDocument:
    def test_short_document_single_chunk_with_title(self) -> None:
        chunks = chunk_document("My Title", "Short content.")
        assert chunks == ["My Title\n\nShort content."]

    def test_empty_content_returns_title_only(self) -> None:
        assert chunk_document("My Title", "") == ["My Title"]

    def test_empty_title_and_content(self) -> None:
        assert chunk_document("", "") == []

    def test_empty_title_keeps_content(self) -> None:
        chunks = chunk_document("", "Just content.")
        assert chunks == ["Just content."]

    def test_long_document_splits_at_headings(self) -> None:
        section_a = "## Alpha\n\n" + ("aaa " * 300)
        section_b = "## Beta\n\n" + ("bbb " * 300)
        content = f"{section_a}\n\n{section_b}"

        chunks = chunk_document("Title", content)

        assert len(chunks) == 2
        assert chunks[0].startswith("Title\n\n## Alpha")
        assert chunks[1].startswith("Title\n\n## Beta")

    def test_title_prefixed_to_every_chunk(self) -> None:
        content = "\n\n".join(f"## H{i}\n\n" + ("word " * 250) for i in range(4))
        chunks = chunk_document("The Title", content)

        assert len(chunks) > 1
        assert all(chunk.startswith("The Title\n\n") for chunk in chunks)

    def test_small_sections_packed_together(self) -> None:
        content = "\n\n".join(f"## H{i}\n\nshort section {i}" for i in range(5))
        chunks = chunk_document("Title", content)
        # All sections fit well within the target, so they stay in one chunk
        assert len(chunks) == 1
        assert "short section 4" in chunks[0]

    def test_oversized_paragraph_hard_split(self) -> None:
        content = "x" * (CHUNK_MAX_CHARS * 2 + 100)  # no headings, no paragraph breaks
        chunks = chunk_document("T", content)

        assert len(chunks) >= 2
        # Every chunk stays within max size (plus the title prefix)
        assert all(len(chunk) <= CHUNK_MAX_CHARS + len("T\n\n") for chunk in chunks)
        # No content lost
        assert sum(len(chunk) - len("T\n\n") for chunk in chunks) == len(content)

    def test_preamble_before_first_heading_kept(self) -> None:
        content = "Intro paragraph before headings.\n\n## First\n\nBody"
        chunks = chunk_document("Title", content)
        joined = "\n".join(chunks)
        assert "Intro paragraph before headings." in joined
        assert "## First" in joined

    def test_typical_note_matches_whole_document_embedding_shape(self) -> None:
        # A typical note stays a single chunk: behavior identical to
        # whole-document embedding, just with the title included
        content = "A note about barnacles.\n\nThey accumulate on ships."
        chunks = chunk_document("Rocks and Barnacles", content, target_chars=CHUNK_TARGET_CHARS)
        assert len(chunks) == 1
