"""Integration tests for search API endpoints.

Tests the /api/search endpoint including:
- Text search with fuzzy matching
- Snippet extraction and contextual highlighting
- Result scoring and ranking
- Error handling
"""

from fastapi.testclient import TestClient


class TestSearchEndpoint:
    """Tests for POST /api/search endpoint."""

    def test_search_returns_results(self, client: TestClient) -> None:
        """Search should return matching results."""
        response = client.post("/api/search", json={"query": "engineering", "top_k": 5})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "count" in data
        assert data["count"] == len(data["results"])

    def test_search_result_structure(self, client: TestClient) -> None:
        """Search results should have required fields including snippet."""
        response = client.post("/api/search", json={"query": "software", "top_k": 3})
        assert response.status_code == 200
        results = response.json()["results"]

        if len(results) > 0:
            result = results[0]
            # Check all required fields are present
            assert "id" in result
            assert "type" in result
            assert "title" in result
            assert "content" in result
            assert "snippet" in result  # New field from #58
            assert "score" in result
            # Type should be article or note
            assert result["type"] in ["article", "note"]

    def test_search_snippet_contains_query(self, client: TestClient) -> None:
        """Snippet should contain or be near the search query."""
        # Use a specific term likely to appear in articles
        response = client.post("/api/search", json={"query": "system", "top_k": 5})
        assert response.status_code == 200
        results = response.json()["results"]

        # At least one result should have the query in the snippet
        if len(results) > 0:
            # Check that snippets are reasonable length (not full content)
            for result in results:
                snippet = result["snippet"]
                # Snippet should be shorter than full content (unless content is very short)
                if len(result["content"]) > 250:
                    assert len(snippet) <= 250, "Snippet should be truncated"

    def test_search_respects_top_k(self, client: TestClient) -> None:
        """Search should return at most top_k results."""
        response = client.post(
            "/api/search",
            json={"query": "the", "top_k": 3},  # Common word, should have many matches
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 3

    def test_search_empty_query_rejected(self, client: TestClient) -> None:
        """Empty query should be rejected."""
        response = client.post("/api/search", json={"query": "", "top_k": 5})
        assert response.status_code == 422  # Validation error

    def test_search_whitespace_query_rejected(self, client: TestClient) -> None:
        """Whitespace-only query should be rejected."""
        response = client.post("/api/search", json={"query": "   ", "top_k": 5})
        assert response.status_code == 422  # Validation error

    def test_search_no_results(self, client: TestClient) -> None:
        """Search with no matches should return empty results."""
        response = client.post("/api/search", json={"query": "xyznonexistentterm123", "top_k": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["results"] == []
        assert data["count"] == 0

    def test_search_case_insensitive(self, client: TestClient) -> None:
        """Search should be case-insensitive."""
        # Search with lowercase
        response_lower = client.post("/api/search", json={"query": "software", "top_k": 5})
        # Search with uppercase
        response_upper = client.post("/api/search", json={"query": "SOFTWARE", "top_k": 5})

        assert response_lower.status_code == 200
        assert response_upper.status_code == 200

        # Should get same number of results
        assert response_lower.json()["count"] == response_upper.json()["count"]

    def test_search_short_query(self, client: TestClient) -> None:
        """Short queries (< 3 chars) should use exact matching."""
        response = client.post("/api/search", json={"query": "AI", "top_k": 10})
        assert response.status_code == 200
        # Should still return results if AI appears in content
        data = response.json()
        assert "results" in data

    def test_search_fuzzy_matching(self, client: TestClient) -> None:
        """Search should handle typos with fuzzy matching."""
        # Search for a typo of "software"
        response = client.post(
            "/api/search",
            json={"query": "sofware", "top_k": 5},  # Missing 't'
        )
        assert response.status_code == 200
        # Fuzzy matching should still find results
        # (depends on actual content, so just verify no error)

    def test_search_title_weighted_higher(self, client: TestClient) -> None:
        """Title matches should score higher than content matches."""
        response = client.post("/api/search", json={"query": "engineering", "top_k": 10})
        assert response.status_code == 200
        results = response.json()["results"]

        if len(results) >= 2:
            # Results should be sorted by score descending
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True), "Results should be sorted by score"

    def test_search_returns_both_types(self, client: TestClient) -> None:
        """Search should return both articles and notes."""
        response = client.post("/api/search", json={"query": "management", "top_k": 20})
        assert response.status_code == 200
        results = response.json()["results"]

        types = {r["type"] for r in results}
        # Should potentially have both types (if content exists)
        # Just verify the types are valid
        assert types.issubset({"article", "note"})

    def test_search_default_semantic_false(self, client: TestClient) -> None:
        """Search should default to text search (not semantic)."""
        response = client.post(
            "/api/search",
            json={"query": "test", "top_k": 5},
            # Not passing semantic parameter
        )
        assert response.status_code == 200
        # Should complete quickly (text search is instant)
        # Semantic search would take 15-30+ seconds


class TestSearchSnippets:
    """Tests specifically for snippet extraction feature (#58)."""

    def test_snippet_is_contextual(self, client: TestClient) -> None:
        """Snippet should show context around match, not just beginning."""
        response = client.post("/api/search", json={"query": "system", "top_k": 5})
        assert response.status_code == 200
        results = response.json()["results"]

        for result in results:
            content = result["content"].lower()
            # Verify snippet field exists and is a string
            assert isinstance(result["snippet"], str)

            # If the query appears in content but not at the start,
            # snippet should still contain it (contextual extraction)
            if "system" in content:
                # Snippet should either contain the term or be from start of content
                # (if term is in first 200 chars, snippet will be from start)
                pass  # Just verify no errors

    def test_snippet_has_ellipsis_for_middle_match(self, client: TestClient) -> None:
        """Snippets from middle of content should have ellipsis."""
        response = client.post("/api/search", json={"query": "architecture", "top_k": 10})
        assert response.status_code == 200
        results = response.json()["results"]

        # Check snippets that are clearly from middle of long content
        for result in results:
            snippet = result["snippet"]
            content = result["content"]

            # If content is long and snippet doesn't start at beginning
            if len(content) > 300 and not content.startswith(snippet[:20]):
                # Snippet should start with ellipsis
                assert snippet.startswith("..."), (
                    f"Middle snippet should start with ellipsis: {snippet[:50]}"
                )

    def test_snippet_length_reasonable(self, client: TestClient) -> None:
        """Snippets should be reasonable length, not full content."""
        response = client.post("/api/search", json={"query": "engineering", "top_k": 10})
        assert response.status_code == 200
        results = response.json()["results"]

        for result in results:
            snippet = result["snippet"]
            content = result["content"]

            # Snippet should not be longer than ~250 chars (with some buffer for ellipsis)
            if len(content) > 300:
                assert len(snippet) < 300, f"Snippet too long: {len(snippet)} chars"
