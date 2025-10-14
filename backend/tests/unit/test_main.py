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


def test_get_resources_includes_static(client: TestClient) -> None:
    """Test getting resources includes static articles."""
    response = client.get("/api/resources")
    assert response.status_code == 200
    data = response.json()
    # Should include at least some static articles
    assert len(data["resources"]) > 0
    # Test is flexible - demo articles may or may not exist
    # Just verify response structure is correct
    assert "resources" in data


def test_create_resource(client: TestClient, sample_resource: dict[str, str | list[str]]) -> None:
    """Test creating a new resource."""
    # Get current resource count
    initial_response = client.get("/api/resources")
    initial_count = len(initial_response.json()["resources"])

    response = client.post("/api/resources", json=sample_resource)
    assert response.status_code == 201
    data = response.json()
    assert "resource" in data
    resource = data["resource"]
    assert resource["title"] == sample_resource["title"]
    assert resource["content"] == sample_resource["content"]
    # ID should be total count + 1 (after all existing resources)
    assert resource["id"] == initial_count + 1
    assert "created_at" in resource


def test_get_resource_by_id(
    client: TestClient, sample_resource: dict[str, str | list[str]]
) -> None:
    """Test getting a resource by ID."""
    # Create resource first
    create_response = client.post("/api/resources", json=sample_resource)
    resource_id = create_response.json()["resource"]["id"]

    # Get the resource
    response = client.get(f"/api/resources/{resource_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["resource"]["id"] == resource_id
    assert data["resource"]["title"] == sample_resource["title"]


def test_get_nonexistent_resource(client: TestClient) -> None:
    """Test getting a resource that doesn't exist."""
    response = client.get("/api/resources/990")
    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"


def test_delete_resource(client: TestClient, sample_resource: dict[str, str | list[str]]) -> None:
    """Test deleting a resource."""
    # Create resource first
    create_response = client.post("/api/resources", json=sample_resource)
    resource_id = create_response.json()["resource"]["id"]

    # Delete the resource
    response = client.delete(f"/api/resources/{resource_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Resource deleted"

    # Verify it's gone
    get_response = client.get(f"/api/resources/{resource_id}")
    assert get_response.status_code == 404


def test_delete_nonexistent_resource(client: TestClient) -> None:
    """Test deleting a resource that doesn't exist."""
    response = client.delete("/api/resources/990")
    assert response.status_code == 404


def test_create_multiple_resources(client: TestClient) -> None:
    """Test creating multiple resources assigns unique IDs."""
    resource1 = {"title": "First", "content": "Content 1", "tags": []}
    resource2 = {"title": "Second", "content": "Content 2", "tags": []}

    response1 = client.post("/api/resources", json=resource1)
    response2 = client.post("/api/resources", json=resource2)

    assert response1.status_code == 201
    assert response2.status_code == 201

    id1 = response1.json()["resource"]["id"]
    id2 = response2.json()["resource"]["id"]

    assert id1 != id2
    assert id2 == id1 + 1


def test_get_all_resources(client: TestClient) -> None:
    """Test getting all resources returns all created resources plus static articles."""
    # Get initial count of static articles
    initial_response = client.get("/api/resources")
    initial_count = len(initial_response.json()["resources"])

    # Create multiple resources
    num_created = 3
    for i in range(num_created):
        client.post(
            "/api/resources",
            json={"title": f"Resource {i}", "content": f"Content {i}", "tags": []},
        )

    # Get all resources
    response = client.get("/api/resources")
    assert response.status_code == 200
    data = response.json()
    # Should have initial static articles + newly created ones
    assert len(data["resources"]) == initial_count + num_created


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


def test_create_resource_with_markdown(client: TestClient) -> None:
    """Test creating a resource with markdown content."""
    resource = {
        "title": "Rich Content",
        "content": "## Heading\n\nSome **bold** text",
        "content_type": "markdown",
        "tags": ["test"],
    }

    response = client.post("/api/resources", json=resource)
    assert response.status_code == 201
    data = response.json()
    assert data["resource"]["content"] == "## Heading\n\nSome **bold** text"
    assert data["resource"]["content_type"] == "markdown"
