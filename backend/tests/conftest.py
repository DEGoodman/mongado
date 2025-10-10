"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def clear_resources() -> None:
    """Clear resources before and after each test."""
    main.resources_db.clear()
    yield
    main.resources_db.clear()


@pytest.fixture
def client() -> TestClient:
    """Get test client for API testing."""
    return TestClient(main.app)


@pytest.fixture
def sample_resource() -> dict[str, str | list[str]]:
    """Get sample resource data for testing."""
    return {
        "title": "Test Resource",
        "content": "This is test content",
        "url": "https://example.com",
        "tags": ["test", "example"],
    }
