"""Unit tests for notes API endpoints."""

import os

import pytest
from fastapi.testclient import TestClient

# Set testing mode before importing app modules
os.environ["TESTING"] = "1"

from config import get_settings
from database import get_database
from main import app
from notes_service import get_notes_service


@pytest.fixture
def client() -> TestClient:
    """Get test client for API testing."""
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Get admin authentication headers for testing."""
    settings = get_settings()
    return {"Authorization": f"Bearer {settings.admin_token}"}


@pytest.fixture(autouse=True)
def clean_notes() -> None:
    """Clean up notes before and after each test."""
    # Clear database notes
    db = get_database()
    db.execute("DELETE FROM notes")
    db.execute("DELETE FROM note_links")
    db.commit()

    # Clear Neo4j notes
    notes_service = get_notes_service()
    if notes_service.neo4j and notes_service.neo4j.is_available():
        # Delete all notes from Neo4j
        notes_service.neo4j.driver.execute_query("MATCH (n:Note) DETACH DELETE n")

    yield

    # Cleanup after test
    db.execute("DELETE FROM notes")
    db.execute("DELETE FROM note_links")
    db.commit()

    # Clear Neo4j notes after test
    if notes_service.neo4j and notes_service.neo4j.is_available():
        notes_service.neo4j.driver.execute_query("MATCH (n:Note) DETACH DELETE n")


class TestCreateNote:
    """Tests for POST /api/notes endpoint."""

    def test_create_note_with_admin_token(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Test creating a note with admin authentication."""
        response = client.post(
            "/api/notes",
            json={"content": "Test note", "title": "Test Title", "tags": ["test"]},
            headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Test note"
        assert data["title"] == "Test Title"
        assert data["tags"] == ["test"]
        assert data["author"] == "Erik"
        assert "id" in data

    def test_create_note_without_auth(self, client: TestClient) -> None:
        """Test that creating note without authentication fails."""
        response = client.post(
            "/api/notes",
            json={"content": "Test note"}
        )

        assert response.status_code == 401
        assert "Authorization required" in response.json()["detail"]

    def test_create_note_with_invalid_token(self, client: TestClient) -> None:
        """Test that creating note with invalid token fails."""
        response = client.post(
            "/api/notes",
            json={"content": "Test note"},
            headers={"Authorization": "Bearer invalid-token"}
        )

        assert response.status_code == 403
        assert "Invalid token" in response.json()["detail"]

    def test_create_note_with_wikilinks(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Test that wikilinks are extracted from content."""
        response = client.post(
            "/api/notes",
            json={"content": "This note links to [[other-note]] and [[another-note]]"},
            headers=admin_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert set(data["links"]) == {"other-note", "another-note"}


class TestListNotes:
    """Tests for GET /api/notes endpoint."""

    def test_list_empty_notes(self, client: TestClient) -> None:
        """Test listing notes when none exist."""
        response = client.get("/api/notes")

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == []
        assert data["count"] == 0

    def test_list_multiple_notes(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Test listing multiple notes."""
        # Create notes
        client.post(
            "/api/notes",
            json={"content": "Note 1"},
            headers=admin_headers
        )
        client.post(
            "/api/notes",
            json={"content": "Note 2"},
            headers=admin_headers
        )

        # List notes
        response = client.get("/api/notes")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert all(note["author"] == "Erik" for note in data["notes"])

    def test_list_notes_ordered_by_created_at(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Test that notes are ordered by created_at descending (newest first)."""
        # Create notes in order
        response1 = client.post("/api/notes", json={"content": "First"}, headers=admin_headers)
        response2 = client.post("/api/notes", json={"content": "Second"}, headers=admin_headers)
        response3 = client.post("/api/notes", json={"content": "Third"}, headers=admin_headers)

        # List notes
        response = client.get("/api/notes")
        notes = response.json()["notes"]

        # Should be in reverse order (newest first)
        assert notes[0]["content"] == "Third"
        assert notes[1]["content"] == "Second"
        assert notes[2]["content"] == "First"


class TestGetNote:
    """Tests for GET /api/notes/{note_id} endpoint."""

    def test_get_note_by_id(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Test getting specific note."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "Test note", "title": "Title"},
            headers=admin_headers
        )
        note_id = create_response.json()["id"]

        # Get note
        response = client.get(f"/api/notes/{note_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == note_id
        assert data["content"] == "Test note"

    def test_get_nonexistent_note(self, client: TestClient) -> None:
        """Test getting note that doesn't exist."""
        response = client.get("/api/notes/nonexistent-id")
        assert response.status_code == 404


class TestUpdateNote:
    """Tests for PUT /api/notes/{note_id} endpoint."""

    def test_update_note_with_admin_token(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Test updating note with admin authentication."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "Original content"},
            headers=admin_headers
        )
        note_id = create_response.json()["id"]

        # Update note
        response = client.put(
            f"/api/notes/{note_id}",
            json={"content": "Updated content", "title": "New Title", "tags": ["updated"]},
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content"
        assert data["title"] == "New Title"
        assert data["tags"] == ["updated"]

    def test_update_note_without_auth(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Test that updating note without authentication fails."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "Original"},
            headers=admin_headers
        )
        note_id = create_response.json()["id"]

        # Try to update without auth
        response = client.put(
            f"/api/notes/{note_id}",
            json={"content": "Hacked"}
        )

        assert response.status_code == 401

    def test_update_with_new_wikilinks(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Test that updating content updates wikilinks."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "Links to [[old-note]]"},
            headers=admin_headers
        )
        note_id = create_response.json()["id"]

        # Update with new links
        response = client.put(
            f"/api/notes/{note_id}",
            json={"content": "Links to [[new-note]] and [[another-note]]"},
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert set(data["links"]) == {"new-note", "another-note"}


class TestDeleteNote:
    """Tests for DELETE /api/notes/{note_id} endpoint."""

    def test_delete_note_with_admin_token(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Test deleting note with admin authentication."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "To be deleted"},
            headers=admin_headers
        )
        note_id = create_response.json()["id"]

        # Delete note
        response = client.delete(f"/api/notes/{note_id}", headers=admin_headers)
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify note is gone
        get_response = client.get(f"/api/notes/{note_id}")
        assert get_response.status_code == 404

    def test_delete_note_without_auth(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        """Test that deleting note without authentication fails."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "Protected"},
            headers=admin_headers
        )
        note_id = create_response.json()["id"]

        # Try to delete without auth
        response = client.delete(f"/api/notes/{note_id}")
        assert response.status_code == 401


class TestBacklinks:
    """Tests for GET /api/notes/{note_id}/backlinks endpoint."""

    def test_get_backlinks(self, client: TestClient) -> None:
        """Test getting backlinks to a note."""
        # Create target note
        from notes_service import get_notes_service
        notes_service = get_notes_service()

        # Create notes with links
        target = notes_service.create_note(
            content="Target note",
            title="Target"
        )
        target_id = target["id"]

        source1 = notes_service.create_note(
            content=f"Links to [[{target_id}]]",
            title="Source 1"
        )

        source2 = notes_service.create_note(
            content=f"Also links to [[{target_id}]]",
            title="Source 2"
        )

        # Get backlinks
        response = client.get(f"/api/notes/{target_id}/backlinks")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

        backlink_ids = {note["id"] for note in data["backlinks"]}
        assert source1["id"] in backlink_ids
        assert source2["id"] in backlink_ids

    def test_get_backlinks_for_note_with_none(self, client: TestClient) -> None:
        """Test getting backlinks when note has none."""
        # Create note with no backlinks
        from notes_service import get_notes_service
        notes_service = get_notes_service()

        note = notes_service.create_note(content="Lonely note")

        response = client.get(f"/api/notes/{note['id']}/backlinks")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["backlinks"] == []


class TestOutboundLinks:
    """Tests for GET /api/notes/{note_id}/links endpoint."""

    def test_get_outbound_links(self, client: TestClient) -> None:
        """Test getting outbound links from a note."""
        from notes_service import get_notes_service
        notes_service = get_notes_service()

        # Create target notes
        target1 = notes_service.create_note(content="Target 1")
        target2 = notes_service.create_note(content="Target 2")

        # Create source note with links
        source = notes_service.create_note(
            content=f"Links to [[{target1['id']}]] and [[{target2['id']}]]"
        )

        # Get outbound links
        response = client.get(f"/api/notes/{source['id']}/links")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

        link_ids = {note["id"] for note in data["links"]}
        assert target1["id"] in link_ids
        assert target2["id"] in link_ids

    def test_get_outbound_links_for_note_with_none(self, client: TestClient) -> None:
        """Test getting outbound links when note has none."""
        from notes_service import get_notes_service
        notes_service = get_notes_service()

        note = notes_service.create_note(content="No links here")

        response = client.get(f"/api/notes/{note['id']}/links")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["links"] == []
