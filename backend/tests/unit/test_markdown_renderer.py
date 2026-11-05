"""Unit tests for core.markdown_renderer (pure functions, no I/O)."""

from core.markdown_renderer import _slugify_heading, render_markdown_to_html


class TestSlugifyHeading:
    """Slug algorithm must match frontend ArticleTableOfContents.tsx."""

    def test_basic_heading(self) -> None:
        assert _slugify_heading("Golden Signals") == "golden-signals"

    def test_strips_punctuation(self) -> None:
        assert _slugify_heading("Latency & Errors!") == "latency-errors"

    def test_collapses_whitespace(self) -> None:
        assert _slugify_heading("A   B") == "a-b"


class TestRenderMarkdownToHtml:
    def test_heading_anchors(self) -> None:
        html = render_markdown_to_html("## Golden Signals\n\ntext")
        assert '<h2 id="golden-signals">Golden Signals</h2>' in html

    def test_duplicate_headings_get_suffixed_ids(self) -> None:
        html = render_markdown_to_html("## Same\n\na\n\n## Same\n\nb")
        assert 'id="same"' in html
        assert 'id="same-1"' in html

    def test_code_block_uses_pygments(self) -> None:
        html = render_markdown_to_html("```python\nx = 1\n```")
        assert '<div class="highlight">' in html

    def test_note_wikilink(self) -> None:
        html = render_markdown_to_html("See [[curious-elephant]]")
        assert '<a href="/knowledge-base/notes/curious-elephant" class="wikilink">' in html

    def test_article_wikilink(self) -> None:
        html = render_markdown_to_html("See [[article:3]]")
        assert '<a href="/knowledge-base/articles/3" class="wikilink wikilink-article">' in html

    def test_wikilink_in_inline_code_stays_literal(self) -> None:
        """#308: example syntax in `code` must not become a live link."""
        html = render_markdown_to_html("Write `[[note-id]]` to link, e.g. [[wise-mountain]]")
        assert "<code>[[note-id]]</code>" in html
        assert 'href="/knowledge-base/notes/note-id"' not in html
        assert 'href="/knowledge-base/notes/wise-mountain"' in html

    def test_wikilink_in_fenced_block_stays_literal(self) -> None:
        for fence in ("```markdown\nSee [[swift-river]]\n```", "```\nSee [[swift-river]]\n```"):
            html = render_markdown_to_html(fence)
            assert "wikilink" not in html, fence
            assert "swift-river" in html

    def test_article_wikilink_in_code_stays_literal(self) -> None:
        html = render_markdown_to_html("Use `[[article:3]]`")
        assert "wikilink" not in html

    def test_plain_code_block_is_escaped(self) -> None:
        html = render_markdown_to_html("```\n<b>x</b>\n```")
        assert "&lt;b&gt;x&lt;/b&gt;" in html

    def test_table_renders(self) -> None:
        html = render_markdown_to_html("| a | b |\n|---|---|\n| 1 | 2 |")
        assert "<table>" in html
