"""Unit tests for content inspiration features."""

import os

import pytest
from fastapi.testclient import TestClient

# Set testing mode before importing app modules
os.environ["TESTING"] = "1"

from config import get_settings
from core import inspire as inspire_core
from main import app
from notes_service import get_notes_service

# Test admin token constant
TEST_ADMIN_TOKEN = "test-admin-token-for-ci"


@pytest.fixture
def client() -> TestClient:
    """Get test client for API testing."""
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Get admin authentication headers for testing."""
    settings = get_settings()
    token = settings.admin_token or TEST_ADMIN_TOKEN
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clean_notes() -> None:
    """Clean up notes before and after each test."""
    notes_service = get_notes_service()

    # Clear Neo4j notes before test
    if notes_service.neo4j.is_available():
        notes_service.neo4j.driver.execute_query("MATCH (n:Note) DETACH DELETE n")

    yield

    # Clear Neo4j notes after test
    if notes_service.neo4j.is_available():
        notes_service.neo4j.driver.execute_query("MATCH (n:Note) DETACH DELETE n")


class TestCoreInspire:
    """Unit tests for pure functions in core/inspire.py."""

    def test_find_underdeveloped_topics_empty(self) -> None:
        """Test with empty notes list."""
        result = inspire_core.find_underdeveloped_topics([])
        assert result == []

    def test_find_underdeveloped_topics_short_content(self) -> None:
        """Test finding notes with short content."""
        notes = [
            {"id": "short-note", "title": "Short", "content_length": 100, "link_count": 5, "backlink_count": 3},
            {"id": "long-note", "title": "Long", "content_length": 1000, "link_count": 5, "backlink_count": 3},
        ]
        result = inspire_core.find_underdeveloped_topics(notes, min_content_length=500)

        assert len(result) == 1
        assert result[0]["note_id"] == "short-note"
        assert result[0]["is_short"] is True

    def test_find_underdeveloped_topics_few_links(self) -> None:
        """Test finding notes with few links."""
        notes = [
            {"id": "isolated-note", "title": "Isolated", "content_length": 1000, "link_count": 0, "backlink_count": 0},
            {"id": "connected-note", "title": "Connected", "content_length": 1000, "link_count": 5, "backlink_count": 3},
        ]
        result = inspire_core.find_underdeveloped_topics(notes, max_links=1)

        assert len(result) == 1
        assert result[0]["note_id"] == "isolated-note"
        assert result[0]["has_few_links"] is True

    def test_find_underdeveloped_topics_sorted_by_length(self) -> None:
        """Test that results are sorted by content length (shortest first)."""
        notes = [
            {"id": "medium", "title": "Medium", "content_length": 200, "link_count": 0, "backlink_count": 0},
            {"id": "shortest", "title": "Shortest", "content_length": 50, "link_count": 0, "backlink_count": 0},
            {"id": "long", "title": "Long", "content_length": 400, "link_count": 0, "backlink_count": 0},
        ]
        result = inspire_core.find_underdeveloped_topics(notes, min_content_length=500, limit=10)

        assert len(result) == 3
        assert result[0]["note_id"] == "shortest"
        assert result[1]["note_id"] == "medium"
        assert result[2]["note_id"] == "long"

    def test_find_underdeveloped_topics_respects_limit(self) -> None:
        """Test that limit parameter is respected."""
        notes = [
            {"id": f"note-{i}", "title": f"Note {i}", "content_length": 100, "link_count": 0, "backlink_count": 0}
            for i in range(10)
        ]
        result = inspire_core.find_underdeveloped_topics(notes, limit=3)

        assert len(result) == 3

    def test_find_unlinked_similar_notes_empty(self) -> None:
        """Test with empty embeddings list."""
        result = inspire_core.find_unlinked_similar_notes([], {})
        assert result == []

    def test_find_unlinked_similar_notes_similar_pair(self) -> None:
        """Test finding similar unlinked notes."""
        # Create embeddings that are similar (same normalized vector)
        embedding = [1.0, 0.0, 0.0]
        note_embeddings = [
            ("note-a", "Note A", embedding),
            ("note-b", "Note B", embedding),  # Same embedding = 100% similar
        ]
        existing_links: dict[str, set[str]] = {}

        result = inspire_core.find_unlinked_similar_notes(
            note_embeddings=note_embeddings,
            existing_links=existing_links,
            similarity_threshold=0.7,
        )

        assert len(result) == 1
        assert result[0]["note_a_id"] == "note-a"
        assert result[0]["note_b_id"] == "note-b"
        assert result[0]["similarity"] == 1.0

    def test_find_unlinked_similar_notes_excludes_linked(self) -> None:
        """Test that already linked notes are excluded."""
        embedding = [1.0, 0.0, 0.0]
        note_embeddings = [
            ("note-a", "Note A", embedding),
            ("note-b", "Note B", embedding),
        ]
        existing_links = {"note-a": {"note-b"}}  # Already linked

        result = inspire_core.find_unlinked_similar_notes(
            note_embeddings=note_embeddings,
            existing_links=existing_links,
            similarity_threshold=0.7,
        )

        assert len(result) == 0

    def test_find_unlinked_similar_notes_below_threshold(self) -> None:
        """Test that dissimilar notes are excluded."""
        note_embeddings = [
            ("note-a", "Note A", [1.0, 0.0, 0.0]),
            ("note-b", "Note B", [0.0, 1.0, 0.0]),  # Orthogonal = 0% similar
        ]
        existing_links: dict[str, set[str]] = {}

        result = inspire_core.find_unlinked_similar_notes(
            note_embeddings=note_embeddings,
            existing_links=existing_links,
            similarity_threshold=0.7,
        )

        assert len(result) == 0

    def test_build_inspiration_prompt_gaps_only(self) -> None:
        """Test prompt building with only gap notes."""
        gap_notes = [
            {"title": "Test Note", "content_length": 100, "is_short": True, "has_few_links": False, "link_count": 0, "backlink_count": 0},
        ]
        prompt = inspire_core.build_inspiration_prompt(gap_notes, [])

        assert "Knowledge Gaps" in prompt
        assert "Test Note" in prompt
        assert "100 chars" in prompt

    def test_build_inspiration_prompt_connections_only(self) -> None:
        """Test prompt building with only connection opportunities."""
        connections = [
            {"note_a_title": "Note A", "note_b_title": "Note B", "similarity": 0.85},
        ]
        prompt = inspire_core.build_inspiration_prompt([], connections)

        assert "Connection Opportunities" in prompt
        assert "Note A" in prompt
        assert "Note B" in prompt
        assert "85%" in prompt

    def test_build_inspiration_prompt_empty(self) -> None:
        """Test prompt building with no data."""
        prompt = inspire_core.build_inspiration_prompt([], [])

        assert "No significant gaps or opportunities found" in prompt

    def test_parse_inspiration_response_valid_json(self) -> None:
        """Test parsing valid JSON response."""
        response = """[
            {
                "type": "gap",
                "title": "Expand: Test Note",
                "description": "This note needs expansion.",
                "related_notes": ["test-note"],
                "action_text": "Edit Note"
            }
        ]"""
        result = inspire_core.parse_inspiration_response(response)

        assert len(result) == 1
        assert result[0]["type"] == "gap"
        assert result[0]["title"] == "Expand: Test Note"

    def test_parse_inspiration_response_with_markdown(self) -> None:
        """Test parsing JSON wrapped in markdown code blocks."""
        response = """```json
        [{"type": "gap", "title": "Test", "description": "Test", "related_notes": ["a"], "action_text": "Edit"}]
        ```"""
        result = inspire_core.parse_inspiration_response(response)

        assert len(result) == 1
        assert result[0]["type"] == "gap"

    def test_parse_inspiration_response_invalid_type(self) -> None:
        """Test that invalid types are filtered out."""
        response = """[
            {"type": "invalid", "title": "Test", "description": "Test", "related_notes": ["a"], "action_text": "Edit"}
        ]"""
        result = inspire_core.parse_inspiration_response(response)

        assert len(result) == 0

    def test_parse_inspiration_response_missing_fields(self) -> None:
        """Test that suggestions with missing fields are filtered out."""
        response = """[{"type": "gap", "title": "Test"}]"""  # Missing required fields
        result = inspire_core.parse_inspiration_response(response)

        assert len(result) == 0

    def test_parse_inspiration_response_empty(self) -> None:
        """Test parsing empty response."""
        result = inspire_core.parse_inspiration_response("")
        assert result == []

    def test_build_fallback_suggestions_gaps(self) -> None:
        """Test fallback suggestion generation for gaps."""
        gap_notes = [
            {"note_id": "test-note", "title": "Test Note", "content_length": 100, "is_short": True, "has_few_links": True, "link_count": 0, "backlink_count": 0},
        ]
        result = inspire_core.build_fallback_suggestions(gap_notes, [], limit=5)

        assert len(result) == 1
        assert result[0]["type"] == "gap"
        assert result[0]["title"] == "Expand: Test Note"
        assert "test-note" in result[0]["related_notes"]

    def test_build_fallback_suggestions_connections(self) -> None:
        """Test fallback suggestion generation for connections."""
        connections = [
            {"note_a_id": "note-a", "note_a_title": "Note A", "note_b_id": "note-b", "note_b_title": "Note B", "similarity": 0.85},
        ]
        result = inspire_core.build_fallback_suggestions([], connections, limit=5)

        assert len(result) == 1
        assert result[0]["type"] == "connection"
        assert "note-a" in result[0]["related_notes"]
        assert "note-b" in result[0]["related_notes"]


class TestInspireAPI:
    """Integration tests for inspire API endpoints."""

    def test_get_suggestions_empty(self, client: TestClient) -> None:
        """Test getting suggestions with no notes."""
        response = client.get("/api/inspire/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "generated_at" in data
        assert "has_llm" in data

    def test_get_suggestions_with_notes(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test getting suggestions with some notes."""
        # Create a short note (underdeveloped)
        client.post(
            "/api/notes",
            json={"content": "Short note", "title": "Short"},
            headers=admin_headers,
        )

        response = client.get("/api/inspire/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["suggestions"], list)
        # May or may not have suggestions depending on thresholds

    def test_get_knowledge_gaps_empty(self, client: TestClient) -> None:
        """Test getting gaps with no notes."""
        response = client.get("/api/inspire/gaps")

        assert response.status_code == 200
        data = response.json()
        assert data["gaps"] == []
        assert data["count"] == 0

    def test_get_knowledge_gaps_with_short_note(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """Test getting gaps with a short note."""
        # Create a short note
        client.post(
            "/api/notes",
            json={"content": "Short", "title": "Short Note"},
            headers=admin_headers,
        )

        response = client.get("/api/inspire/gaps?min_content_length=100")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        # First gap should be our short note
        assert any(gap["title"] == "Short Note" for gap in data["gaps"])

    def test_get_knowledge_gaps_custom_thresholds(self, client: TestClient) -> None:
        """Test getting gaps with custom thresholds."""
        response = client.get("/api/inspire/gaps?min_content_length=1000&max_links=5&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["min_content_length"] == 1000
        assert data["max_links"] == 5

    def test_get_connection_opportunities_empty(self, client: TestClient) -> None:
        """Test getting connections with no notes."""
        response = client.get("/api/inspire/connections")

        assert response.status_code == 200
        data = response.json()
        assert data["connections"] == []
        assert data["count"] == 0

    def test_get_connection_opportunities_custom_threshold(
        self, client: TestClient
    ) -> None:
        """Test getting connections with custom similarity threshold."""
        response = client.get("/api/inspire/connections?similarity_threshold=0.9&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["similarity_threshold"] == 0.9

    def test_suggestions_limit_parameter(self, client: TestClient) -> None:
        """Test that limit parameter is respected."""
        response = client.get("/api/inspire/suggestions?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["suggestions"]) <= 2

    def test_gaps_limit_parameter(self, client: TestClient) -> None:
        """Test that limit parameter is respected for gaps."""
        response = client.get("/api/inspire/gaps?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data["gaps"]) <= 3

    def test_connections_limit_parameter(self, client: TestClient) -> None:
        """Test that limit parameter is respected for connections."""
        response = client.get("/api/inspire/connections?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data["connections"]) <= 3
