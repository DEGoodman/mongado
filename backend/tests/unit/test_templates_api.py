"""Unit tests for templates API endpoints."""

import os

import pytest
from fastapi.testclient import TestClient

# Set testing mode before importing app modules
os.environ["TESTING"] = "1"

from main import app


@pytest.fixture
def client() -> TestClient:
    """Get test client for API testing."""
    return TestClient(app)


class TestListTemplates:
    """Tests for GET /api/templates endpoint."""

    def test_list_templates_returns_all_templates(self, client: TestClient) -> None:
        """Test that listing templates returns all available templates."""
        response = client.get("/api/templates")
        assert response.status_code == 200

        data = response.json()
        assert "templates" in data
        assert "count" in data
        assert data["count"] >= 4  # We have at least 4 templates

        # Verify template structure
        for template in data["templates"]:
            assert "id" in template
            assert "title" in template
            assert "description" in template
            assert "icon" in template
            # Should not include content in list view
            assert "content" not in template

    def test_list_templates_includes_expected_templates(self, client: TestClient) -> None:
        """Test that expected templates are included."""
        response = client.get("/api/templates")
        assert response.status_code == 200

        data = response.json()
        template_ids = [t["id"] for t in data["templates"]]

        # Check for expected templates
        assert "person" in template_ids
        assert "book" in template_ids
        assert "concept" in template_ids
        assert "project" in template_ids


class TestGetTemplate:
    """Tests for GET /api/templates/{template_id} endpoint."""

    def test_get_person_template(self, client: TestClient) -> None:
        """Test getting the person template."""
        response = client.get("/api/templates/person")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "person"
        assert data["title"] == "Person Template"
        assert "content" in data
        assert "# [Person Name]" in data["content"]
        assert "icon" in data

    def test_get_book_template(self, client: TestClient) -> None:
        """Test getting the book template."""
        response = client.get("/api/templates/book")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "book"
        assert "Book Title" in data["content"]
        assert "Key Takeaways" in data["content"]

    def test_get_concept_template(self, client: TestClient) -> None:
        """Test getting the concept template."""
        response = client.get("/api/templates/concept")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "concept"
        assert "Definition" in data["content"]

    def test_get_project_template(self, client: TestClient) -> None:
        """Test getting the project template."""
        response = client.get("/api/templates/project")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == "project"
        assert "Goal" in data["content"]

    def test_get_nonexistent_template(self, client: TestClient) -> None:
        """Test that requesting a nonexistent template returns 404."""
        response = client.get("/api/templates/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_template_includes_wikilink_placeholder(self, client: TestClient) -> None:
        """Test that templates include wikilink placeholders for guidance."""
        response = client.get("/api/templates/person")
        assert response.status_code == 200

        data = response.json()
        # Templates should include wikilink syntax to guide users
        assert "[[" in data["content"]
        assert "]]" in data["content"]
