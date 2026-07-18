"""Unit tests for core.search module (pure business logic).

These tests verify pure functions with no I/O dependencies.
All functions should be deterministic: same input → same output.
"""

from core import search


class TestExtractSnippet:
    """Tests for extract_snippet function."""

    def test_match_at_beginning(self):
        """Match at start should show from beginning."""
        content = "The quick brown fox jumps over the lazy dog"
        result = search.extract_snippet(content, "quick")
        assert "quick" in result
        assert result.startswith("The")

    def test_match_in_middle(self):
        """Match in middle should show context around it."""
        content = "A" * 100 + " the systems fail here " + "B" * 100
        result = search.extract_snippet(content, "systems", context_chars=30)
        assert "systems" in result
        assert result.startswith("...")
        assert result.endswith("...")

    def test_match_at_end(self):
        """Match at end should show trailing context."""
        content = "A" * 150 + " finally the conclusion"
        result = search.extract_snippet(content, "conclusion", context_chars=50)
        assert "conclusion" in result
        assert not result.endswith("...")

    def test_no_match_returns_beginning(self):
        """No match should return beginning of content."""
        content = "The quick brown fox jumps over the lazy dog"
        result = search.extract_snippet(content, "elephant")
        assert result.startswith("The quick")

    def test_empty_content(self):
        """Empty content should return empty string."""
        result = search.extract_snippet("", "query")
        assert result == ""

    def test_empty_query(self):
        """Empty query should return beginning of content."""
        content = "The quick brown fox"
        result = search.extract_snippet(content, "")
        assert result.startswith("The")

    def test_case_insensitive_match(self):
        """Match should be case insensitive."""
        content = "The Quick Brown FOX jumps"
        result = search.extract_snippet(content, "fox")
        assert "FOX" in result

    def test_respects_max_length(self):
        """Snippet should not exceed max_snippet_length."""
        content = "A" * 500
        result = search.extract_snippet(content, "A", max_snippet_length=100)
        assert len(result) <= 110  # Allow some buffer for ellipsis

    def test_short_content_no_ellipsis(self):
        """Short content should not have ellipsis."""
        content = "Short text"
        result = search.extract_snippet(content, "Short")
        assert "..." not in result

    def test_word_boundary_cleanup(self):
        """Snippet should not start/end mid-word when possible."""
        content = "The magnificent systems engineering approach works well"
        result = search.extract_snippet(content, "systems", context_chars=15)
        # Should not start with partial word like "ificent"
        assert "systems" in result


class TestExtractMultipleSnippets:
    """Tests for extract_multiple_snippets function."""

    def test_single_match(self):
        """Single match returns single snippet."""
        content = "The systems work well"
        result = search.extract_multiple_snippets(content, "systems")
        assert len(result) == 1
        assert "systems" in result[0]

    def test_multiple_matches(self):
        """Multiple matches return multiple snippets."""
        content = "First systems here. " + "X" * 200 + " Second systems there."
        result = search.extract_multiple_snippets(
            content, "systems", max_snippets=2, max_snippet_length=50
        )
        assert len(result) <= 2
        for snippet in result:
            assert "systems" in snippet

    def test_respects_max_snippets(self):
        """Should not return more than max_snippets."""
        content = "sys " * 100
        result = search.extract_multiple_snippets(content, "sys", max_snippets=2)
        assert len(result) <= 2

    def test_no_match_returns_beginning(self):
        """No match returns beginning of content."""
        content = "The quick brown fox"
        result = search.extract_multiple_snippets(content, "elephant")
        assert len(result) == 1
        assert result[0].startswith("The")

    def test_empty_content(self):
        """Empty content returns empty list."""
        result = search.extract_multiple_snippets("", "query")
        assert result == []


class TestFindBestMatchPosition:
    """Tests for find_best_match_position function."""

    def test_finds_first_match(self):
        """Should find position of first match."""
        content = "Hello world, hello again"
        pos = search.find_best_match_position(content, "hello")
        assert pos == 0  # First "Hello" (case insensitive)

    def test_no_match_returns_none(self):
        """No match should return None."""
        content = "The quick brown fox"
        pos = search.find_best_match_position(content, "elephant")
        assert pos is None

    def test_empty_content_returns_none(self):
        """Empty content returns None."""
        pos = search.find_best_match_position("", "query")
        assert pos is None

    def test_empty_query_returns_none(self):
        """Empty query returns None."""
        pos = search.find_best_match_position("content", "")
        assert pos is None

    def test_case_insensitive(self):
        """Match should be case insensitive."""
        content = "The SYSTEMS work"
        pos = search.find_best_match_position(content, "systems")
        assert pos == 4  # Position of "SYSTEMS"


class TestFuzzyMatchText:
    """Tests for fuzzy_match_text function."""

    def test_exact_phrase_match(self):
        """Exact phrase gets the highest score."""
        assert search.fuzzy_match_text("golden signals", "the four golden signals are") == 2.0

    def test_single_word_typo(self):
        """Single-word typo matches fuzzily (pre-existing behavior)."""
        score = search.fuzzy_match_text("sofware", "software delivery performance")
        assert 0.8 <= score <= 1.0

    def test_multi_word_query_with_typo(self):
        """Multi-word query with a typo in one word still matches (#232)."""
        score = search.fuzzy_match_text("golden sognals", "the four golden signals of monitoring")
        assert score > 0.8

    def test_multi_word_all_tokens_must_match(self):
        """Query token with no match anywhere fails the whole query."""
        assert search.fuzzy_match_text("golden zebras", "the four golden signals") == 0.0

    def test_multi_word_tokens_out_of_order(self):
        """All tokens exact but not as a phrase scores below exact phrase."""
        score = search.fuzzy_match_text("signals golden", "the four golden signals")
        assert score == 1.0

    def test_short_query_exact_only(self):
        """Queries under 3 chars require exact substring."""
        assert search.fuzzy_match_text("ai", "ai tooling") == 2.0
        assert search.fuzzy_match_text("ai", "ml tooling") == 0.0

    def test_short_token_in_multi_word_query(self):
        """Short tokens within a longer query require exact presence."""
        assert search.fuzzy_match_text("go routines", "go routines and channels") == 2.0
        assert search.fuzzy_match_text("qq routines", "goroutines and channels") == 0.0

    def test_no_match(self):
        """Completely unrelated query scores zero."""
        assert search.fuzzy_match_text("kubernetes", "gardening tips for spring") == 0.0


class TestExtractSnippetFuzzyFallback:
    """Tests for extract_snippet anchoring on token matches (#232)."""

    def test_multi_word_query_anchors_on_token(self):
        """Snippet centers on a matching token when the full phrase is absent."""
        content = "X" * 300 + " the golden signals of monitoring " + "Y" * 300
        result = search.extract_snippet(content, "golden sognals", context_chars=40)
        assert "golden" in result

    def test_typo_query_anchors_on_fuzzy_word(self):
        """Snippet centers on the fuzzy-matched word for typo queries."""
        content = "Z" * 300 + " observability signals matter most " + "W" * 300
        result = search.extract_snippet(content, "sognals", context_chars=40)
        assert "signals" in result

    def test_no_token_match_still_returns_beginning(self):
        """Nothing matching anywhere still falls back to content start."""
        content = "The quick brown fox jumps over the lazy dog"
        result = search.extract_snippet(content, "elephant parade")
        assert result.startswith("The quick")
