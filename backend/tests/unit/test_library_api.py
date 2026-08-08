"""Unit/integration tests for Library API endpoints (#294)."""

import os

import pytest
from fastapi.testclient import TestClient

# Set testing mode before importing app modules
os.environ["TESTING"] = "1"

from library_service import get_library_service
from main import app

# admin_headers (a passkey-session token) comes from conftest since #267.


@pytest.fixture
def client() -> TestClient:
    """Get test client for API testing."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_library() -> None:
    """Clean up library entries before and after each test."""
    service = get_library_service()

    if service.neo4j.is_available():
        service.neo4j.driver.execute_query("MATCH (e:LibraryEntry) DETACH DELETE e")

    yield

    if service.neo4j.is_available():
        service.neo4j.driver.execute_query("MATCH (e:LibraryEntry) DETACH DELETE e")


def _skip_if_no_neo4j() -> None:
    if not get_library_service().neo4j.is_available():
        pytest.skip("Neo4j not available")


class TestCreateLibraryEntry:
    """Tests for POST /api/library."""

    def test_create_with_admin(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        _skip_if_no_neo4j()
        response = client.post(
            "/api/library",
            json={
                "title": "Exercises in Programming Style",
                "source_url": "https://example.com/eps",
                "author": "Cristina Videira Lopes",
                "type": "book",
                "summary": "40 styles for one task.",
                "tags": ["programming"],
            },
            headers=admin_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Exercises in Programming Style"
        assert data["source_url"] == "https://example.com/eps"
        assert data["author"] == "Cristina Videira Lopes"
        assert data["type"] == "book"
        assert data["tags"] == ["programming"]
        assert "id" in data
        assert "html_summary" in data

    def test_create_without_auth_fails(self, client: TestClient) -> None:
        response = client.post("/api/library", json={"title": "No auth"})
        assert response.status_code == 401

    def test_create_rejects_invalid_type(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/library",
            json={"title": "Bad type", "type": "podcast"},
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_create_requires_title(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        response = client.post("/api/library", json={"author": "x"}, headers=admin_headers)
        assert response.status_code == 422


class TestGetLibraryEntry:
    """Tests for GET /api/library/{id}."""

    def test_get_existing(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        _skip_if_no_neo4j()
        created = client.post(
            "/api/library",
            json={"title": "Thing", "summary": "# Heading\n\nBody"},
            headers=admin_headers,
        ).json()
        response = client.get(f"/api/library/{created['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == created["id"]
        assert data["title"] == "Thing"
        assert "<h1" in data["html_summary"].lower() or "<h1>" in data["html_summary"]

    def test_get_missing_returns_404(self, client: TestClient) -> None:
        _skip_if_no_neo4j()
        response = client.get("/api/library/does-not-exist")
        assert response.status_code == 404


class TestListLibraryEntries:
    """Tests for GET /api/library."""

    def test_list_and_filter(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        _skip_if_no_neo4j()
        client.post(
            "/api/library",
            json={"title": "A book", "type": "book", "tags": ["x"]},
            headers=admin_headers,
        )
        client.post(
            "/api/library",
            json={"title": "A video", "type": "video", "tags": ["y"]},
            headers=admin_headers,
        )

        all_resp = client.get("/api/library").json()
        assert all_resp["total"] == 2
        assert {"page", "limit", "total_pages", "count"} <= all_resp.keys()

        books = client.get("/api/library?type=book").json()
        assert books["total"] == 1
        assert books["entries"][0]["title"] == "A book"

        tagged = client.get("/api/library?tag=y").json()
        assert tagged["total"] == 1
        assert tagged["entries"][0]["title"] == "A video"

    def test_list_public_no_auth(self, client: TestClient) -> None:
        _skip_if_no_neo4j()
        response = client.get("/api/library")
        assert response.status_code == 200

    def test_pagination(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        _skip_if_no_neo4j()
        for i in range(3):
            client.post("/api/library", json={"title": f"E{i}"}, headers=admin_headers)
        page1 = client.get("/api/library?limit=2&page=1").json()
        assert page1["count"] == 2
        assert page1["total"] == 3
        assert page1["total_pages"] == 2
        page2 = client.get("/api/library?limit=2&page=2").json()
        assert page2["count"] == 1


class TestUpdateLibraryEntry:
    """Tests for PUT /api/library/{id}."""

    def test_partial_update(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        _skip_if_no_neo4j()
        created = client.post(
            "/api/library",
            json={"title": "Old", "author": "Keep me", "type": "book"},
            headers=admin_headers,
        ).json()
        response = client.put(
            f"/api/library/{created['id']}",
            json={"title": "New"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New"
        assert data["author"] == "Keep me"  # unchanged
        assert data["type"] == "book"  # unchanged

    def test_update_without_auth_fails(self, client: TestClient) -> None:
        response = client.put("/api/library/whatever", json={"title": "x"})
        assert response.status_code == 401

    def test_update_missing_returns_404(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        _skip_if_no_neo4j()
        response = client.put(
            "/api/library/nope", json={"title": "x"}, headers=admin_headers
        )
        assert response.status_code == 404


class TestDeleteLibraryEntry:
    """Tests for DELETE /api/library/{id}."""

    def test_delete(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        _skip_if_no_neo4j()
        created = client.post(
            "/api/library", json={"title": "Delete me"}, headers=admin_headers
        ).json()
        response = client.delete(f"/api/library/{created['id']}", headers=admin_headers)
        assert response.status_code == 200
        assert client.get(f"/api/library/{created['id']}").status_code == 404

    def test_delete_without_auth_fails(self, client: TestClient) -> None:
        response = client.delete("/api/library/whatever")
        assert response.status_code == 401

    def test_delete_missing_returns_404(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        _skip_if_no_neo4j()
        response = client.delete("/api/library/nope", headers=admin_headers)
        assert response.status_code == 404
