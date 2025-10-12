# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

Mongado is the personal website of D. Erik Goodman (Mongado = anagram of Goodman). Built with Python FastAPI backend and Next.js frontend.

The site features:
- **Homepage**: Portfolio and professional presence
- **Knowledge Base**: Personal knowledge management (moving from Notion/offline notes)
- **Extensible architecture**: Designed for adding future projects

Currently in early development. Knowledge Base implements basic CRUD operations with in-memory storage (database integration planned).

## Key Patterns

### Functional Core, Imperative Shell

- **Functional Core**: Pure business logic, no side effects (unit tests)
- **Imperative Shell**: I/O operations (integration tests)
- Keep business logic pure and separate from data access

### Configuration & Secrets

All configuration in `backend/config.py`:
- Pydantic Settings for env vars and `.env` files
- **1Password Integration**: `SecretManager` auto-detects SDK/CLI, gracefully falls back
- Access: `secret_manager.get_secret("op://vault/item/field")`

### Logging

**Backend** (`backend/logging_config.py`):
- Always use `logger = logging.getLogger(__name__)` - never `print()`
- Use `%s` formatting: `logger.info("User %s logged in", user_id)`

**Frontend** (`frontend/src/lib/logger.ts`):
- Use `import { logger } from "@/lib/logger"`
- Contextual: `const apiLogger = logger.withContext("API")`

### Data Storage

**Static Content** (`backend/static/`):
- Articles: Markdown files with YAML frontmatter (`backend/static/articles/`)
- Images: WebP format recommended (`backend/static/assets/images/`)
- Cached at startup, auto-reload on file changes in dev mode
- See `docs/KNOWLEDGE_BASE.md` for content authoring guide

**User Data** (in-memory, temporary):
- Will migrate to database (PostgreSQL/MongoDB)
- Keep pure logic separate from data access
- Use dependency injection
- Follow functional core / imperative shell pattern

## Common Commands

### Backend (Python 3.13)

```bash
cd backend

# Development
make run              # Start dev server
make install          # Install dev dependencies

# Testing
make test             # Run all tests
make test-unit        # Unit tests only
make test-cov         # Tests with coverage

# Code Quality
make lint             # Ruff linter
make format           # Auto-format
make typecheck        # Mypy type checking
make check            # lint + typecheck + security
make ci               # Full CI pipeline

# Profiling & Performance
make profile          # py-spy profiler
make profile-viz      # VizTracer (interactive)
make benchmark        # API benchmarks
make memory           # Memory profiling

# Single test
./venv/bin/pytest tests/unit/test_main.py::test_function_name -v

# Image Optimization
./venv/bin/python image_optimizer.py input.jpg output.webp 85 1200
./venv/bin/python image_optimizer.py --batch static/assets/images/
```

### Frontend (Next.js 14 + TypeScript)

```bash
cd frontend

# Development
npm run dev           # Start dev server
npm install           # Install dependencies

# Testing
npm test              # Unit tests (Vitest)
npm run test:ui       # Tests with UI
npm run test:e2e      # E2E tests (Playwright)
npm run test:all      # Full suite

# Code Quality
npm run lint          # ESLint
npm run lint:fix      # ESLint with auto-fix
npm run type-check    # TypeScript

# Build
npm run build         # Production build
npm run build:analyze # Bundle size analysis

# Single test
npm test src/__tests__/Component.test.tsx
```

### Docker

```bash
# Development
docker compose up
docker compose up --build  # Rebuild after deps

# Production
docker compose -f docker-compose.prod.yml up -d
docker compose logs -f backend
```

## Type System

### Backend (Python 3.13)

**All functions must have type hints:**
```python
def process_resource(resource: Resource) -> dict[str, Any]:
    """Process a resource and return result."""
    return {"id": resource.id, "status": "processed"}
```

**Use modern Python 3.13 syntax:**
- `int | None` (not `Optional[int]`)
- `list[str]`, `dict[str, Any]` (not `List[str]`, `Dict[str, Any]`)

**Mypy strict mode** - all code must pass `make typecheck`.

### Frontend (TypeScript)

Strict TypeScript enabled. Avoid `any` unless absolutely necessary.

## Dependencies

### Backend (Three-Tier)

- `requirements-base.txt`: Core production (~8 packages)
- `requirements-dev.txt`: Base + dev tools (~30 packages)
- `requirements-prod.txt`: Production only
- `requirements.txt`: Symlink to requirements-dev.txt

**Adding:**
- Production: Add to `requirements-base.txt`
- Dev tools: Add to `requirements-dev.txt` only
- Run `make install` after changes

### Frontend

- `dependencies`: Production runtime (React, Next.js)
- `devDependencies`: Everything else (bundled by Next.js)

## API Structure

In `backend/main.py`:
- FastAPI with Pydantic v2 models
- All endpoints use response models
- CORS configured for `http://localhost:3000`
- Docs at `/docs` and `/redoc`

**Endpoints:**
- `GET /` - API status
- `GET /api/resources` - List all resources (static + user)
- `POST /api/resources` - Create user resource
- `GET /api/resources/{id}` - Get resource by ID
- `DELETE /api/resources/{id}` - Delete user resource (static articles read-only)
- `POST /api/search` - Semantic search with Ollama AI
- `POST /api/ask` - Q&A with context from articles
- `GET /api/articles/{id}/summary` - AI-generated summary
- `POST /api/upload-image` - Upload image (temporary storage)
- `GET /static/assets/*` - Static assets (images, icons, downloads)
- `GET /static/articles/*` - Raw markdown files

**Adding endpoints:**
1. Define Pydantic models
2. Add response_model to decorator
3. Use proper HTTP status codes
4. Add tests in `tests/unit/test_main.py`

## Testing

### Backend

Located in `backend/tests/`:
- `unit/` - Pure functions, no I/O
- `integration/` - API endpoints with TestClient

**Fixtures** in `conftest.py`:
- `client` - FastAPI TestClient
- `sample_resource` - Example data
- `clear_resources` - Auto-clears DB

### Frontend

- `src/__tests__/` - Component tests (Vitest)
- `tests/e2e/` - E2E tests (Playwright)

See existing tests for patterns.

## Documentation

- `docs/SETUP.md` - Installation and 1Password setup
- `docs/TESTING.md` - Testing tools and commands
- `docs/PROFILING.md` - Performance profiling tools
- `docs/DEPENDENCIES.md` - Dependency structure
- `docs/KNOWLEDGE_BASE.md` - Content authoring guide (articles & images)

Root `README.md` is a quick start guide.

## Before Committing

**Backend:**
```bash
make ci  # lint + typecheck + security + tests
```

**Frontend:**
```bash
npm run test:all  # typecheck + lint + tests
```

## Common Pitfalls

1. **Don't use `print()`** - Use `logging` module
2. **Don't use `console.log()`** - Use logger utility
3. **Type hints required** - Won't pass CI without them
4. **1Password optional** - Code must work without it
5. **In-memory storage temporary** - Design for future DB migration

## Future Work

- AI-powered search and context retrieval
- Database persistence (PostgreSQL/MongoDB)
- Full-text search
- User authentication
- Advanced tag filtering
