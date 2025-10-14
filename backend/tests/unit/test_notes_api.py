"""Unit tests for notes API endpoints."""

import os

import pytest
from fastapi.testclient import TestClient

# Set testing mode before importing app modules
os.environ["TESTING"] = "1"

from database import get_database
from ephemeral_notes import get_ephemeral_store
from main import app
from notes_service import get_notes_service


@pytest.fixture
def client() -> TestClient:
    """Get test client for API testing."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_notes() -> None:
    """Clean up notes before and after each test."""
    # Clear database notes
    db = get_database()
    db.execute("DELETE FROM notes")
    db.execute("DELETE FROM note_links")
    db.commit()

    # Clear ephemeral notes
    ephemeral = get_ephemeral_store()
    ephemeral.clear_all()

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
    ephemeral.clear_all()

    # Clear Neo4j notes after test
    if notes_service.neo4j and notes_service.neo4j.is_available():
        notes_service.neo4j.driver.execute_query("MATCH (n:Note) DETACH DELETE n")


class TestCreateNote:
    """Tests for POST /api/notes endpoint."""

    def test_create_ephemeral_note_with_session_id(self, client: TestClient) -> None:
        """Test creating an ephemeral note with session ID."""
        response = client.post(
            "/api/notes",
            json={"content": "Test ephemeral note", "title": "Test Title", "tags": ["test"]},
            headers={"X-Session-ID": "test-session-123"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "Test ephemeral note"
        assert data["title"] == "Test Title"
        assert data["tags"] == ["test"]
        assert data["is_ephemeral"] is True
        assert data["author"] == "anonymous"
        assert "id" in data

    def test_create_ephemeral_note_without_session_id(self, client: TestClient) -> None:
        """Test that creating note without session ID fails for non-admin."""
        response = client.post(
            "/api/notes",
            json={"content": "Test note"}
        )

        assert response.status_code == 400
        assert "Session ID required" in response.json()["detail"]

    def test_create_persistent_note_with_passkey(self, client: TestClient) -> None:
        """Test creating persistent note with admin passkey."""
        # TODO: Implement once we have passkey configured for testing
        pass

    def test_create_note_with_wikilinks(self, client: TestClient) -> None:
        """Test that wikilinks are extracted from content."""
        response = client.post(
            "/api/notes",
            json={"content": "This note links to [[other-note]] and [[another-note]]"},
            headers={"X-Session-ID": "test-session-123"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["links"] == ["other-note", "another-note"]


class TestListNotes:
    """Tests for GET /api/notes endpoint."""

    def test_list_empty_notes(self, client: TestClient) -> None:
        """Test listing notes when none exist."""
        response = client.get("/api/notes", headers={"X-Session-ID": "test-session-123"})

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == []
        assert data["count"] == 0

    def test_list_ephemeral_notes_for_session(self, client: TestClient) -> None:
        """Test that only session's ephemeral notes are visible."""
        # Create notes for session 1
        client.post(
            "/api/notes",
            json={"content": "Session 1 note 1"},
            headers={"X-Session-ID": "session-1"}
        )
        client.post(
            "/api/notes",
            json={"content": "Session 1 note 2"},
            headers={"X-Session-ID": "session-1"}
        )

        # Create note for session 2
        client.post(
            "/api/notes",
            json={"content": "Session 2 note"},
            headers={"X-Session-ID": "session-2"}
        )

        # List notes for session 1
        response = client.get("/api/notes", headers={"X-Session-ID": "session-1"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert all(note["author"] == "anonymous" for note in data["notes"])

    def test_list_includes_persistent_notes(self, client: TestClient) -> None:
        """Test that persistent notes are visible to all users."""
        # Create persistent note directly in database
        from notes_service import get_notes_service
        notes_service = get_notes_service()
        notes_service.create_note(
            content="Persistent note",
            title="Admin Note",
            is_admin=True,
            session_id=None
        )

        # List as visitor
        response = client.get("/api/notes", headers={"X-Session-ID": "visitor-session"})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["notes"][0]["author"] == "Erik"


class TestGetNote:
    """Tests for GET /api/notes/{note_id} endpoint."""

    def test_get_ephemeral_note_by_id(self, client: TestClient) -> None:
        """Test getting specific ephemeral note."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "Test note", "title": "Title"},
            headers={"X-Session-ID": "test-session"}
        )
        note_id = create_response.json()["id"]

        # Get note
        response = client.get(f"/api/notes/{note_id}", headers={"X-Session-ID": "test-session"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == note_id
        assert data["content"] == "Test note"

    def test_get_nonexistent_note(self, client: TestClient) -> None:
        """Test getting note that doesn't exist."""
        response = client.get("/api/notes/nonexistent-id", headers={"X-Session-ID": "test-session"})
        assert response.status_code == 404

    def test_get_other_session_ephemeral_note(self, client: TestClient) -> None:
        """Test that you cannot access other session's ephemeral notes."""
        # Create note in session 1
        create_response = client.post(
            "/api/notes",
            json={"content": "Private note"},
            headers={"X-Session-ID": "session-1"}
        )
        note_id = create_response.json()["id"]

        # Try to access from session 2
        response = client.get(f"/api/notes/{note_id}", headers={"X-Session-ID": "session-2"})
        assert response.status_code == 404


class TestUpdateNote:
    """Tests for PUT /api/notes/{note_id} endpoint."""

    def test_update_own_ephemeral_note(self, client: TestClient) -> None:
        """Test updating own ephemeral note."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "Original content"},
            headers={"X-Session-ID": "test-session"}
        )
        note_id = create_response.json()["id"]

        # Update note
        response = client.put(
            f"/api/notes/{note_id}",
            json={"content": "Updated content", "title": "New Title", "tags": ["updated"]},
            headers={"X-Session-ID": "test-session"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content"
        assert data["title"] == "New Title"
        assert data["tags"] == ["updated"]

    def test_update_other_session_ephemeral_note(self, client: TestClient) -> None:
        """Test that you cannot update other session's notes."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "Original"},
            headers={"X-Session-ID": "session-1"}
        )
        note_id = create_response.json()["id"]

        # Try to update from different session
        response = client.put(
            f"/api/notes/{note_id}",
            json={"content": "Hacked"},
            headers={"X-Session-ID": "session-2"}
        )

        assert response.status_code == 404

    def test_update_with_new_wikilinks(self, client: TestClient) -> None:
        """Test that updating content updates wikilinks."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "Links to [[old-note]]"},
            headers={"X-Session-ID": "test-session"}
        )
        note_id = create_response.json()["id"]

        # Update with new links
        response = client.put(
            f"/api/notes/{note_id}",
            json={"content": "Links to [[new-note]] and [[another-note]]"},
            headers={"X-Session-ID": "test-session"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["links"] == ["new-note", "another-note"]


class TestDeleteNote:
    """Tests for DELETE /api/notes/{note_id} endpoint."""

    def test_delete_own_ephemeral_note(self, client: TestClient) -> None:
        """Test deleting own ephemeral note."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "To be deleted"},
            headers={"X-Session-ID": "test-session"}
        )
        note_id = create_response.json()["id"]

        # Delete note
        response = client.delete(f"/api/notes/{note_id}", headers={"X-Session-ID": "test-session"})
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify note is gone
        get_response = client.get(f"/api/notes/{note_id}", headers={"X-Session-ID": "test-session"})
        assert get_response.status_code == 404

    def test_delete_other_session_ephemeral_note(self, client: TestClient) -> None:
        """Test that you cannot delete other session's notes."""
        # Create note
        create_response = client.post(
            "/api/notes",
            json={"content": "Protected"},
            headers={"X-Session-ID": "session-1"}
        )
        note_id = create_response.json()["id"]

        # Try to delete from different session
        response = client.delete(f"/api/notes/{note_id}", headers={"X-Session-ID": "session-2"})
        assert response.status_code == 404


class TestBacklinks:
    """Tests for GET /api/notes/{note_id}/backlinks endpoint."""

    def test_get_backlinks(self, client: TestClient) -> None:
        """Test getting backlinks to a note."""
        # Create target note
        from notes_service import get_notes_service
        notes_service = get_notes_service()

        # Create persistent notes with links
        target = notes_service.create_note(
            content="Target note",
            title="Target",
            is_admin=True,
            session_id=None
        )
        target_id = target["id"]

        source1 = notes_service.create_note(
            content=f"Links to [[{target_id}]]",
            title="Source 1",
            is_admin=True,
            session_id=None
        )

        source2 = notes_service.create_note(
            content=f"Also links to [[{target_id}]]",
            title="Source 2",
            is_admin=True,
            session_id=None
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

        note = notes_service.create_note(
            content="Lonely note",
            is_admin=True,
            session_id=None
        )

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
        target1 = notes_service.create_note(
            content="Target 1",
            is_admin=True,
            session_id=None
        )
        target2 = notes_service.create_note(
            content="Target 2",
            is_admin=True,
            session_id=None
        )

        # Create source note with links
        source = notes_service.create_note(
            content=f"Links to [[{target1['id']}]] and [[{target2['id']}]]",
            is_admin=True,
            session_id=None
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

        note = notes_service.create_note(
            content="No links here",
            is_admin=True,
            session_id=None
        )

        response = client.get(f"/api/notes/{note['id']}/links")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["links"] == []
