# Backend Architecture

This document describes the backend architecture pattern and implementation.

## Overview

The Mongado backend follows a **Functional Core / Imperative Shell** architecture pattern, which separates pure business logic from I/O operations. This provides excellent testability, maintainability, and clarity.

## Pattern: Functional Core / Imperative Shell

### Core Principles

**Functional Core** (`backend/core/`):
- Contains pure business logic with no side effects
- Deterministic: same input always produces same output
- No I/O operations (no database, file system, network calls)
- Fully unit-testable without mocks or fixtures
- Functions are composable and reusable

**Imperative Shell** (`backend/routers/`, `backend/adapters/`):
- Thin orchestration layer handling I/O operations
- Calls pure functions from core/ for business logic
- Manages database access, API requests, file operations
- Tested with integration tests

### Directory Structure

```
backend/
├── core/                      # Functional Core - Pure Logic
│   ├── __init__.py
│   ├── ai.py                 # AI/ML algorithms
│   │   ├── cosine_similarity()
│   │   ├── rank_documents_by_similarity()
│   │   ├── build_context_from_documents()
│   │   ├── build_qa_prompt()
│   │   ├── parse_json_response()
│   │   ├── build_tag_suggestion_prompt()
│   │   └── filter_link_candidates()
│   └── notes.py              # Notes/graph algorithms
│       ├── extract_wikilinks()
│       ├── validate_note_id()
│       ├── build_graph_data()
│       └── build_local_subgraph()
│
├── routers/                   # Imperative Shell - API Layer
│   ├── __init__.py
│   ├── ai.py                 # AI feature endpoints
│   ├── articles.py           # Article endpoints
│   ├── notes.py              # Notes CRUD/graph endpoints
│   └── search.py             # Search endpoints
│
├── adapters/                  # Imperative Shell - Data Layer
│   ├── __init__.py
│   ├── neo4j.py             # Neo4j database operations
│   ├── ephemeral_notes.py   # In-memory note storage
│   └── article_loader.py    # Static file loading
│
├── notes_service.py          # Service layer (orchestrates adapters + core)
├── ollama_client.py          # Ollama LLM client
└── main.py                   # FastAPI application
```

## Data Flow

### Example: Get Notes Graph

```
1. HTTP Request
   ↓
2. Router (routers/notes.py:get_graph_data)
   ├─→ Call notes_service.list_notes() [I/O]
   │   ├─→ Adapter: neo4j.py or ephemeral_notes.py
   │   └─→ Returns: list[dict] (raw note data)
   ↓
3. Pure Function (core/notes.py:build_graph_data)
   ├─→ Input: list of note dictionaries
   ├─→ Logic: Build nodes/edges data structure
   └─→ Output: {nodes, edges, count}
   ↓
4. HTTP Response (JSON)
```

### Example: AI Tag Suggestions

```
1. HTTP Request
   ↓
2. Router (routers/ai.py:suggest_tags)
   ├─→ Call notes_service.get_note() [I/O]
   ├─→ Call notes_service.list_notes() [I/O]
   │   └─→ Extract existing tags from all notes
   ↓
3. Pure Function (core/ai.py:build_tag_suggestion_prompt)
   ├─→ Input: title, content, current tags, existing tags
   ├─→ Logic: Format prompt string
   └─→ Output: prompt string
   ↓
4. LLM Call (ollama_client.generate) [I/O]
   ↓
5. Pure Function (core/ai.py:parse_json_response)
   ├─→ Input: raw LLM response
   ├─→ Logic: Parse JSON, handle markdown wrappers, validate
   └─→ Output: list[dict] or None
   ↓
6. HTTP Response (JSON)
```

## Factory Pattern with Dependency Injection

All routers use a factory function pattern for dependency injection.

### Pattern Template

```python
# backend/routers/example.py
from fastapi import APIRouter
from typing import Any

router = APIRouter(prefix="/api/example", tags=["example"])

def create_example_router(service: Any) -> APIRouter:
    """Create example router with dependencies injected.

    Args:
        service: Service instance for data operations

    Returns:
        Configured APIRouter with all endpoints
    """

    @router.get("/data")
    async def get_data() -> dict[str, Any]:
        """Endpoint that uses injected service."""
        # 1. I/O operations via service
        raw_data = service.fetch_data()

        # 2. Business logic via pure function
        from core import example
        processed = example.process_data(raw_data)

        # 3. Return result
        return processed

    return router
```

### Registration in main.py

```python
# backend/main.py
from routers.example import create_example_router

# Create router with injected dependencies
example_router = create_example_router(service=some_service)
app.include_router(example_router)
```

### Real Implementation Examples

**Notes Router:**
```python
# backend/routers/notes.py
def create_notes_router(notes_service: Any) -> APIRouter:
    """Create notes router with notes service injected."""

    @router.get("/graph/data")
    async def get_graph_data(...) -> dict[str, Any]:
        # I/O: Fetch all accessible notes
        notes = notes_service.list_notes(is_admin=is_admin, session_id=session_id)

        # Pure logic: Build graph structure
        from core import notes as notes_core
        return notes_core.build_graph_data(notes)

    return router
```

**AI Router:**
```python
# backend/routers/ai.py
def create_ai_router(
    ollama_client: OllamaClient,
    notes_service: Any
) -> APIRouter:
    """Create AI router with Ollama and notes service injected."""

    @router.post("/notes/{note_id}/suggest-tags")
    def suggest_tags(note_id: str) -> TagSuggestionsResponse:
        # I/O: Fetch note and existing tags
        note = notes_service.get_note(note_id, is_admin=True)
        all_notes = notes_service.list_notes(is_admin=True)
        existing_tags = set(tag for n in all_notes for tag in n.get("tags", []))

        # Pure logic: Build prompt
        from core import ai as ai_core
        prompt = ai_core.build_tag_suggestion_prompt(
            title=note.get("title", ""),
            content=note.get("content", ""),
            current_tags=note.get("tags", []),
            existing_tags=existing_tags
        )

        # I/O: Call LLM
        response_data = ollama_client.client.generate(
            model="qwen2.5:1.5b",
            prompt=prompt
        )

        # Pure logic: Parse response
        suggestions_data = ai_core.parse_json_response(
            response_data.get("response", ""),
            expected_type="array"
        )

        # Format and return
        return TagSuggestionsResponse(suggestions=suggestions_data, count=len(suggestions_data))

    return router
```

## Testing Strategy

### Unit Tests (Pure Functions)

Located in `backend/tests/unit/test_core_*.py`

Test pure functions with simple assertions, no mocks needed:

```python
# tests/unit/test_core_notes.py
from core import notes

def test_extract_wikilinks():
    """Test wikilink extraction from markdown."""
    content = "See [[foo-bar]] and [[baz-qux]]"
    links = notes.extract_wikilinks(content)
    assert links == ["foo-bar", "baz-qux"]

def test_build_graph_data():
    """Test graph data structure building."""
    notes_list = [
        {"id": "note-1", "title": "First", "links": ["note-2"], ...},
        {"id": "note-2", "title": "Second", "links": [], ...}
    ]
    graph = notes.build_graph_data(notes_list)

    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["edges"][0] == {"source": "note-1", "target": "note-2"}
```

### Integration Tests (Endpoints)

Located in `backend/tests/unit/test_*_api.py`

Test endpoints with FastAPI TestClient:

```python
# tests/unit/test_notes_api.py
def test_get_graph_data(client, clear_resources):
    """Test graph data endpoint."""
    # Create test data
    response = client.post("/api/notes", json={...})

    # Call graph endpoint
    response = client.get("/api/notes/graph/data")

    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
```

### Coverage Goals

- **Functional Core**: 90%+ coverage (pure functions are easy to test)
- **Imperative Shell**: 70%+ coverage (I/O operations harder to test)

Current coverage:
- `core/ai.py`: 89.13% (92 statements, 10 missing)
- `core/notes.py`: 100% (35 statements, 0 missing)

## Adding New Features

Follow this workflow when adding new features:

### 1. Identify Pure Logic

Ask: "What part of this feature is pure computation?"

Examples:
- Parsing/validation (wikilinks, note IDs)
- Data transformation (graph building, similarity ranking)
- Algorithm implementation (BFS, cosine similarity)
- Prompt construction (tag suggestions, link suggestions)

### 2. Implement in Core Module

Create pure function in appropriate `core/*.py` module:

```python
# backend/core/example.py
def process_data(raw_data: list[dict]) -> dict:
    """Pure function to process data.

    No I/O, no side effects, deterministic.
    """
    # Implementation
    return result
```

### 3. Write Unit Tests

Create unit tests in `tests/unit/test_core_example.py`:

```python
from core import example

def test_process_data_basic():
    """Test basic data processing."""
    input_data = [{"id": 1, "value": "test"}]
    result = example.process_data(input_data)
    assert result["count"] == 1
```

### 4. Implement Router

Create/update router in `routers/*.py`:

```python
# backend/routers/example.py
def create_example_router(service: Any) -> APIRouter:
    @router.post("/process")
    async def process_endpoint(data: InputModel):
        # I/O: Fetch from service
        raw = service.get_raw_data(data.id)

        # Pure logic: Process
        from core import example
        result = example.process_data(raw)

        return result

    return router
```

### 5. Register in main.py

```python
from routers.example import create_example_router

example_router = create_example_router(service=example_service)
app.include_router(example_router)
```

### 6. Write Integration Tests

Test the complete endpoint:

```python
def test_process_endpoint(client):
    response = client.post("/api/example/process", json={...})
    assert response.status_code == 200
```

## Benefits

### Testability
- Pure functions are trivial to test (no mocks, no fixtures)
- Unit tests run instantly (no I/O)
- Easy to achieve high coverage on business logic

### Maintainability
- Business logic isolated from infrastructure concerns
- Easy to understand data flow (input → pure function → output)
- Changes to I/O don't affect business logic

### Reusability
- Pure functions can be composed and reused
- No coupling to specific frameworks or databases
- Easy to refactor without breaking tests

### Type Safety
- All functions have complete type hints
- Mypy strict mode enforced
- Compiler catches errors before runtime

## Related Documentation

- **[TESTING.md](TESTING.md)** - Testing tools and commands
- **[DEPENDENCIES.md](DEPENDENCIES.md)** - Dependency structure
- **[API.md](API.md)** - API endpoint documentation

## References

- [Functional Core, Imperative Shell](https://www.destroyallsoftware.com/screencasts/catalog/functional-core-imperative-shell) - Gary Bernhardt
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/) - Alistair Cockburn
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) - Robert C. Martin
