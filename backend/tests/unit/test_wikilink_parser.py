"""Unit tests for wikilink_parser module.

Tests for [[note-id]] and [[article:id]] wikilink parsing.
"""

from wikilink_parser import WikilinkParser


class TestExtractLinks:
    """Tests for note link extraction [[note-id]]."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = WikilinkParser()

    def test_extracts_single_note_link(self):
        """Should extract single [[note-id]] wikilink."""
        content = "See [[curious-elephant]] for details"
        links = self.parser.extract_links(content)

        assert links == ["curious-elephant"]

    def test_extracts_multiple_note_links(self):
        """Should extract all note wikilinks in order."""
        content = "See [[foo-bar]] and [[baz-qux]] and [[another-note]]"
        links = self.parser.extract_links(content)

        assert links == ["foo-bar", "baz-qux", "another-note"]

    def test_deduplicates_links(self):
        """Duplicate links should appear only once."""
        content = "See [[foo-bar]] and then [[foo-bar]] again"
        links = self.parser.extract_links(content)

        assert links == ["foo-bar"]

    def test_excludes_article_links(self):
        """Should not extract [[article:id]] as note links."""
        content = "See [[article:123]] and [[note-id]]"
        links = self.parser.extract_links(content)

        assert links == ["note-id"]


class TestExtractArticleLinks:
    """Tests for article link extraction [[article:id]]."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = WikilinkParser()

    def test_extracts_single_article_link(self):
        """Should extract single [[article:id]] wikilink."""
        content = "See [[article:123]] for details"
        links = self.parser.extract_article_links(content)

        assert links == [123]

    def test_extracts_multiple_article_links(self):
        """Should extract all article wikilinks."""
        content = "See [[article:1]], [[article:42]], and [[article:999]]"
        links = self.parser.extract_article_links(content)

        assert links == [1, 42, 999]

    def test_deduplicates_article_links(self):
        """Duplicate article links should appear only once."""
        content = "See [[article:5]] and then [[article:5]] again"
        links = self.parser.extract_article_links(content)

        assert links == [5]

    def test_excludes_note_links(self):
        """Should not extract [[note-id]] as article links."""
        content = "See [[article:123]] and [[note-id]]"
        links = self.parser.extract_article_links(content)

        assert links == [123]

    def test_returns_integers(self):
        """Article IDs should be returned as integers."""
        content = "See [[article:42]]"
        links = self.parser.extract_article_links(content)

        assert links == [42]
        assert isinstance(links[0], int)


class TestExtractAllLinks:
    """Tests for combined link extraction."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = WikilinkParser()

    def test_extracts_both_types(self):
        """Should extract both note and article links."""
        content = "See [[curious-elephant]] and [[article:123]]"
        result = self.parser.extract_all_links(content)

        assert result["notes"] == ["curious-elephant"]
        assert result["articles"] == [123]

    def test_handles_mixed_content(self):
        """Should correctly categorize mixed content."""
        content = """
        Reference [[article:1]] for the full article.
        Also see [[note-one]] and [[note-two]] for related notes.
        And [[article:42]] has more context.
        """
        result = self.parser.extract_all_links(content)

        assert result["notes"] == ["note-one", "note-two"]
        assert result["articles"] == [1, 42]

    def test_handles_empty_content(self):
        """Empty content should return empty lists."""
        content = "No links here"
        result = self.parser.extract_all_links(content)

        assert result["notes"] == []
        assert result["articles"] == []


class TestRenderLinksHtml:
    """Tests for HTML rendering of wikilinks."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = WikilinkParser()

    def test_renders_valid_note_link(self):
        """Should render note link as anchor tag."""
        content = "See [[curious-elephant]]"
        notes_map = {"curious-elephant": {"title": "Curious Elephant"}}

        result = self.parser.render_links_html(content, notes_map)

        assert 'href="/knowledge-base/notes/curious-elephant"' in result
        assert 'class="wikilink wikilink-note"' in result
        assert "curious-elephant" in result

    def test_renders_broken_note_link(self):
        """Broken note link should render as span with error class."""
        content = "See [[nonexistent-note]]"
        notes_map = {}

        result = self.parser.render_links_html(content, notes_map)

        assert 'class="wikilink-broken"' in result
        assert "[[nonexistent-note]]" in result

    def test_renders_valid_article_link(self):
        """Should render article link with emoji and title."""
        content = "See [[article:123]]"
        articles_map = {123: {"title": "My Article"}}

        result = self.parser.render_links_html(content, {}, articles_map)

        assert 'href="/knowledge-base/articles/123"' in result
        assert 'class="wikilink wikilink-article"' in result
        assert "📄 My Article" in result

    def test_renders_broken_article_link(self):
        """Broken article link should render with error class."""
        content = "See [[article:999]]"
        articles_map = {}

        result = self.parser.render_links_html(content, {}, articles_map)

        assert 'class="wikilink-broken"' in result
        assert "[[article:999]]" in result

    def test_renders_mixed_links(self):
        """Should render both note and article links correctly."""
        content = "See [[curious-elephant]] and [[article:123]]"
        notes_map = {"curious-elephant": {"title": "Curious Elephant"}}
        articles_map = {123: {"title": "My Article"}}

        result = self.parser.render_links_html(content, notes_map, articles_map)

        assert 'href="/knowledge-base/notes/curious-elephant"' in result
        assert 'href="/knowledge-base/articles/123"' in result


class TestValidateLinks:
    """Tests for link validation."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = WikilinkParser()

    def test_identifies_valid_links(self):
        """Should identify links that exist in note IDs."""
        content = "See [[note-one]] and [[note-two]]"
        existing = {"note-one", "note-two"}

        valid, broken = self.parser.validate_links(content, existing)

        assert valid == ["note-one", "note-two"]
        assert broken == []

    def test_identifies_broken_links(self):
        """Should identify links that don't exist."""
        content = "See [[note-one]] and [[missing-note]]"
        existing = {"note-one"}

        valid, broken = self.parser.validate_links(content, existing)

        assert valid == ["note-one"]
        assert broken == ["missing-note"]


class TestGetLinkContext:
    """Tests for extracting context around links."""

    def setup_method(self):
        """Create parser instance for each test."""
        self.parser = WikilinkParser()

    def test_gets_context_around_link(self):
        """Should extract surrounding text around a link."""
        content = "This is before [[target-link]] and this is after"

        context = self.parser.get_link_context(content, "target-link", context_chars=20)

        assert "[[target-link]]" in context
        assert "before" in context
        assert "after" in context

    def test_returns_none_for_missing_link(self):
        """Should return None if link not found."""
        content = "No links here"

        context = self.parser.get_link_context(content, "missing-link")

        assert context is None
