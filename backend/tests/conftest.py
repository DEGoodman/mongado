"""Pytest configuration and fixtures."""

import os

# Set TESTING environment variable BEFORE any imports
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def clear_resources() -> None:
    """Clear user resources before and after each test (static articles remain)."""
    main.user_resources_db.clear()
    yield
    main.user_resources_db.clear()


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
