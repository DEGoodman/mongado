# Mongado Backend

FastAPI-based backend for the Mongado knowledge base application.

## Tech Stack

- **Python 3.13** - Latest Python with performance improvements
- **FastAPI 0.118+** - Modern, high-performance web framework
- **Pydantic 2.12+** - Data validation using Python type hints
- **Uvicorn 0.37+** - Lightning-fast ASGI server with uvloop

## Quick Start

### Development

```bash
# Install dependencies
make install

# Run development server (with hot reload)
make run

# Run tests
make test

# Run all quality checks
make check
```

The API will be available at http://localhost:8000 with auto-generated docs at `/docs`.

### Docker

```bash
# From project root
docker compose up

# Or build and run backend only
docker build -t mongado-backend -f backend/Dockerfile backend/
docker run -p 8000:8000 mongado-backend
```

## Project Structure

```
backend/
├── main.py              # FastAPI application & API endpoints
├── config.py            # Configuration & 1Password integration
├── logging_config.py    # Centralized logging setup
├── tests/               # Test suite
│   ├── unit/           # Unit tests (pure functions)
│   └── integration/    # Integration tests (API endpoints)
├── uploads/            # Uploaded images (gitignored)
└── requirements*.txt   # Dependency management
```

## Architecture

### Functional Core, Imperative Shell

The codebase follows this pattern for maximum testability:

- **Functional Core**: Pure business logic with no side effects → Fast unit tests
- **Imperative Shell**: I/O operations (API, DB, external services) → Integration tests

Keep business logic pure and separate from I/O operations.

### Configuration Management

All configuration happens through `config.py` using Pydantic Settings:

```python
from config import get_settings, get_secret_manager

settings = get_settings()          # Access settings
secret = secret_manager.get_secret("op://vault/item/field")  # 1Password secrets
```

**1Password Integration**:
- Auto-detects and uses either 1Password SDK or CLI
- Gracefully falls back if unavailable
- Set `OP_MONGADO_SERVICE_ACCOUNT_TOKEN` for service account access

### Logging

**Always use the logging module**, never `print()`:

```python
import logging
logger = logging.getLogger(__name__)

# Use lazy formatting
logger.info("User %s logged in", user_id)
logger.error("Failed to process %s: %s", resource_id, error)
```

Log levels:
- **DEBUG**: Development debugging (not in production)
- **INFO**: Normal operations
- **WARNING**: Recoverable issues
- **ERROR**: Failures requiring attention
- **CRITICAL**: System crashes

See `docs/LOGGING.md` for detailed guidelines.

## Development Commands

All commands use the Makefile for convenience:

### Running & Development
```bash
make run              # Start dev server with hot reload
make install          # Install dev dependencies
make install-prod     # Install production dependencies only
```

### Testing
```bash
make test             # Run all tests
make test-unit        # Unit tests only
make test-integration # Integration tests only
make test-cov         # Tests with coverage report
```

### Code Quality
```bash
make lint             # Ruff linter
make format           # Auto-format with ruff
make typecheck        # Mypy type checking
make security         # Bandit security scan
make quality          # Radon complexity analysis
make check            # Run lint + typecheck + security
make ci               # Full CI pipeline (check + test-cov)
```

### Profiling & Performance
```bash
make profile          # Profile with py-spy (low overhead)
make profile-viz      # Profile with VizTracer (interactive GUI)
make benchmark        # Run API benchmarks
make memory           # Memory profiling with memray
make debug            # Run with IPython debugger
```

### Cleanup
```bash
make clean            # Remove cache and generated files
```

## Dependency Management

Three-tier dependency structure:

- **requirements-base.txt**: Core production dependencies (~8 packages)
- **requirements-dev.txt**: Development tools + base (~30 packages)
- **requirements-prod.txt**: Production-only (base + optional monitoring)
- **requirements.txt**: Symlink → requirements-dev.txt

**Adding dependencies:**
1. Production runtime → Add to `requirements-base.txt`
2. Dev/test tools → Add to `requirements-dev.txt` only
3. Run `make install` to update environment

## API Endpoints

Current endpoints (see `/docs` for full API documentation):

### Core
- `GET /` - API status & version info
- `GET /api/resources` - List all resources
- `POST /api/resources` - Create new resource
- `GET /api/resources/{id}` - Get specific resource
- `DELETE /api/resources/{id}` - Delete resource

### Media
- `POST /api/upload-image` - Upload image file
  - Returns URL for embedding in rich text content
  - Validates file type (JPEG, PNG, GIF, WebP)
  - Stores in `uploads/` directory

## Type System

**All functions must have type hints** using modern Python 3.13 syntax:

```python
def process_resource(resource: Resource) -> dict[str, Any]:
    """Process a resource and return result."""
    return {"id": resource.id, "status": "processed"}
```

**Modern syntax:**
- ✅ `int | None` (not `Optional[int]`)
- ✅ `list[str]` (not `List[str]`)
- ✅ `dict[str, Any]` (not `Dict[str, Any]`)

Mypy runs in strict mode - all code must type check with `make typecheck`.

## Testing

### Writing Tests

```python
def test_create_resource(client: TestClient, sample_resource: dict) -> None:
    """Test creating a new resource."""
    response = client.post("/api/resources", json=sample_resource)
    assert response.status_code == 201
    assert response.json()["resource"]["title"] == sample_resource["title"]
```

### Test Fixtures

Available in `tests/conftest.py`:
- `client` - FastAPI TestClient (auto-injected)
- `sample_resource` - Example resource data
- `clear_resources` - Clears in-memory DB before/after tests

### Running Specific Tests

```bash
./venv/bin/pytest tests/unit/test_main.py::test_function_name -v
```

## Common Tasks

### Add a New Endpoint

1. Define Pydantic models for request/response
2. Add endpoint with `response_model` decorator
3. Use proper HTTP status codes
4. Add tests in `tests/unit/test_main.py`

Example:
```python
@app.get("/api/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: int) -> ItemResponse:
    """Get an item by ID."""
    item = find_item(item_id)  # Pure function in functional core
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse(item=item)
```

### Update Dependencies

```bash
# Check for outdated packages
./venv/bin/pip list --outdated

# Update requirements files
vim requirements-base.txt  # or requirements-dev.txt

# Install updates
make install

# Run tests to verify
make ci
```

## Before Committing

Always run the full CI pipeline:

```bash
make ci
```

This runs:
1. Linting (ruff)
2. Type checking (mypy)
3. Security scanning (bandit)
4. All tests with coverage

All checks must pass before committing.

## Common Pitfalls

1. ❌ Don't use `print()` → ✅ Use `logging` module
2. ❌ Don't skip type hints → ✅ Add type hints to all functions
3. ❌ Don't commit without tests → ✅ Add tests for new features
4. ❌ Don't hardcode config → ✅ Use `settings` from `config.py`
5. ❌ Don't mix business logic with I/O → ✅ Follow functional core pattern

## Future Enhancements

- PostgreSQL/MongoDB database integration
- User authentication & authorization
- AI-powered search & context retrieval
- Full-text search with vector embeddings
- Async task queue for background jobs

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python 3.13 Release Notes](https://docs.python.org/3.13/whatsnew/3.13.html)
- Project docs: `docs/` directory
  - `docs/LOGGING.md` - Logging best practices
  - `docs/TESTING.md` - Comprehensive testing guide
  - `docs/PROFILING.md` - Performance profiling guide
  - `docs/DEPENDENCIES.md` - Dependency management details
