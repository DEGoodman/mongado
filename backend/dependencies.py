"""FastAPI dependency injection providers.

This module provides dependency functions that can be overridden in tests
using app.dependency_overrides. This enables clean mock injection without
module-level patching.

Usage in routers:
    from dependencies import get_ollama, get_notes_service

    @router.get("/endpoint")
    def endpoint(ollama: OllamaClient = Depends(get_ollama)):
        ...

Usage in tests:
    from dependencies import get_ollama

    app.dependency_overrides[get_ollama] = lambda: mock_ollama
    yield TestClient(app)
    app.dependency_overrides.clear()
"""

from typing import Any

from adapters.neo4j import Neo4jAdapter, get_neo4j_adapter
from notes_service import NotesService
from notes_service import get_notes_service as _get_notes_service
from ollama_client import OllamaClient, get_ollama_client

# Module-level instances (created once at import)
# These are the "real" instances used in production
_ollama_client: OllamaClient | None = None
_neo4j_adapter: Neo4jAdapter | None = None
_notes_service: NotesService | None = None


def get_ollama() -> OllamaClient:
    """Get the Ollama client instance.

    This dependency can be overridden in tests:
        app.dependency_overrides[get_ollama] = lambda: mock_client
    """
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = get_ollama_client()
    return _ollama_client


def get_neo4j() -> Neo4jAdapter:
    """Get the Neo4j adapter instance.

    This dependency can be overridden in tests:
        app.dependency_overrides[get_neo4j] = lambda: mock_adapter
    """
    global _neo4j_adapter
    if _neo4j_adapter is None:
        _neo4j_adapter = get_neo4j_adapter()
    return _neo4j_adapter


def get_notes() -> NotesService:
    """Get the notes service instance.

    This dependency can be overridden in tests:
        app.dependency_overrides[get_notes] = lambda: mock_service
    """
    global _notes_service
    if _notes_service is None:
        _notes_service = _get_notes_service()
    return _notes_service


# For static articles and user resources, we need callables that return
# the current state (since these are mutable lists loaded at startup)
_static_articles: list[dict[str, Any]] = []
_user_resources: list[dict[str, Any]] = []


def set_static_articles(articles: list[dict[str, Any]]) -> None:
    """Set the static articles list (called during app startup)."""
    global _static_articles
    _static_articles = articles


def set_user_resources(resources: list[dict[str, Any]]) -> None:
    """Set the user resources list (called during app startup)."""
    global _user_resources
    _user_resources = resources


def get_static_articles() -> list[dict[str, Any]]:
    """Get the current static articles list.

    This dependency can be overridden in tests:
        app.dependency_overrides[get_static_articles] = lambda: mock_articles
    """
    return _static_articles


def get_user_resources() -> list[dict[str, Any]]:
    """Get the current user resources list.

    This dependency can be overridden in tests:
        app.dependency_overrides[get_user_resources] = lambda: mock_resources
    """
    return _user_resources


def reset_dependencies() -> None:
    """Reset all cached dependencies (useful for tests).

    Call this in test fixtures to ensure clean state between tests.
    """
    global _ollama_client, _neo4j_adapter, _notes_service
    global _static_articles, _user_resources
    _ollama_client = None
    _neo4j_adapter = None
    _notes_service = None
    _static_articles = []
    _user_resources = []
