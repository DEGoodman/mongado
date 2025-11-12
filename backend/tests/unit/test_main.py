"""Unit tests for main API module."""

from io import BytesIO

from fastapi.testclient import TestClient


def test_read_root(client: TestClient) -> None:
    """Test root endpoint returns status information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "onepassword_enabled" in data
    assert data["version"] == "0.1.0"


def test_get_articles(client: TestClient) -> None:
    """Test getting all articles."""
    response = client.get("/api/articles")
    assert response.status_code == 200
    data = response.json()
    # Should include at least some static articles
    assert len(data["resources"]) > 0
    # Verify response structure is correct
    assert "resources" in data


def test_get_article_by_id(client: TestClient) -> None:
    """Test getting a specific article by ID."""
    # First get all articles to find a valid ID
    response = client.get("/api/articles")
    articles = response.json()["resources"]
    assert len(articles) > 0, "No articles found"

    # Get the first article's ID
    article_id = articles[0]["id"]

    # Get that specific article
    response = client.get(f"/api/articles/{article_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["resource"]["id"] == article_id


def test_get_nonexistent_article(client: TestClient) -> None:
    """Test getting an article that doesn't exist."""
    response = client.get("/api/articles/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"


def test_upload_image(client: TestClient) -> None:
    """Test image upload endpoint."""
    # Create a fake image file
    image_data = b"fake image data"
    files = {"file": ("test.jpg", BytesIO(image_data), "image/jpeg")}

    response = client.post("/api/upload-image", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "filename" in data
    assert data["url"].startswith("/uploads/")
    assert data["filename"].endswith(".jpg")


def test_upload_invalid_file_type(client: TestClient) -> None:
    """Test uploading non-image file is rejected."""
    file_data = b"not an image"
    files = {"file": ("test.txt", BytesIO(file_data), "text/plain")}

    response = client.post("/api/upload-image", files=files)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_article_has_markdown_content(client: TestClient) -> None:
    """Test that articles have markdown content."""
    response = client.get("/api/articles")
    articles = response.json()["resources"]
    assert len(articles) > 0, "No articles found"

    # Check that the first article has content
    article = articles[0]
    assert "content" in article
    assert len(article["content"]) > 0
