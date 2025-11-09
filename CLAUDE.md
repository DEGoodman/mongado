# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Critical Project Conventions

### 1. Use Docker Compose for Everything

**ALWAYS use `docker compose` commands. NEVER interact with services or virtual environments directly.**

This project runs entirely in Docker. All interactions with services must go through Docker Compose:

**❌ WRONG - Do NOT do this**:
```bash
./venv/bin/pytest tests/              # Direct venv access
python -m pytest tests/               # Direct Python
npm test                              # Direct npm
curl http://localhost:8000/           # Assumes local services
backend/venv/bin/python script.py     # Direct script execution
```

**✅ CORRECT - Always do this**:
```bash
docker compose exec backend pytest tests/              # Run tests in container
docker compose exec backend python script.py          # Run scripts in container
docker compose exec frontend npm test                 # Run frontend tests in container
docker compose logs backend                           # View logs
docker compose restart backend                        # Restart services
docker compose up -d --build                          # Rebuild containers
```

**Why this matters**:
- Ensures consistent environment (dependencies, Python version, etc.)
- Matches production deployment
- Avoids "works on my machine" issues
- Proper service networking and isolation

**When you need to run ANY command**, ask yourself: "Should this run in a container?" The answer is almost always YES.

### 2. Work Tracking

**All project work is tracked via [GitHub Issues](https://github.com/DEGoodman/mongado/issues).**

**CRITICAL: Always check for existing issues BEFORE starting work.**

**Workflow:**
1. **Before starting work:** Search for existing issue: `gh issue list --search "keyword"`
2. **If no issue exists:** Create one: `gh issue create --label "feature,status: todo"`
3. **While working:** Update issue status labels: `idea` → `todo` → `in-progress` → `done`
4. **In commits:** Reference issue: `feat: add feature (fixes #123)`
5. **After completing:** Issue auto-closes via commit reference, or manually close with `gh issue close N`

**Never create TODO files**. GitHub Issues are the single source of truth for all project work.

See `CONTRIBUTING.md` for complete workflow.

### 3. Deployment

**Deployment is fully automated via GitHub Actions.**

When you push to the `main` branch:
1. **CI runs automatically**: Linting, type checking, tests, security scans
2. **Production deployment**: Automatically deploys to DigitalOcean droplet
3. **Health checks**: Verifies backend and frontend are healthy

**DO NOT manually deploy to production.** Simply:
```bash
git push
```

GitHub Actions will handle the rest. You can monitor deployment status in the GitHub Actions tab.

**Note**: Some one-time setup scripts (like `setup_backups.sh`) may need to be run manually on the droplet after deployment, but the application code is deployed automatically.

### When to Create Issues

Create GitHub issues proactively for:
- New features or enhancements
- Bug fixes
- Article ideas
- Infrastructure improvements
- Documentation updates
- Technical debt

**Examples**:
```bash
# Feature request
gh issue create --title "Feature: Add note templates" --label "feature,status: todo"

# Article idea
gh issue create --title "Article: SRE Incident Response" --label "article-idea,sre,status: idea"

# Bug report
gh issue create --title "Bug: Search returns duplicates" --label "bug,status: todo"
```

## Writing Style for Articles

When creating or editing articles in `backend/static/articles/`, follow these guidelines based on the author's established tone and style:

**Principles:**
- **Concise and direct**: No fluff, get to the point quickly
- **Practical and actionable**: Focus on frameworks and concrete steps
- **Clear definitions**: Define terms upfront
- **Quantified examples**: Use specific numbers and measurements where possible
- **Structured sections**: Use consistent headings (Intro, Definitions, Framework, Examples, etc.)
- **Minimal prose**: Avoid flowery language, superlatives, or excessive storytelling
- **Bulleted lists**: Prefer lists over paragraphs for clarity
- **Caveats and pitfalls**: Call out what doesn't work and why

**Reference articles:**
- `005-software-delivery-perf-framework.md` - exemplary tone and structure
- `008-rocks-and-barnacles.md` - balance of metaphor (pirate ship) with practical execution

**Structure pattern:**
1. **Intro**: Problem statement and what this framework provides
2. **Definitions**: Clear, upfront definitions of key terms
3. **Framework/Process**: Step-by-step mechanics
4. **Examples**: Real-world outputs with numbers
5. **Pitfalls**: Common mistakes and fixes
6. **Measuring Success**: How to know it's working
7. **Conclusion**: Brief summary, no new info
8. **References**: Citations if applicable

**Avoid:**
- Excessive enthusiasm or motivational language
- Long paragraphs (keep to 2-3 sentences max)
- Burying the lede (start with the value prop)
- Vague advice without concrete steps
- Over-explaining obvious points

## Project Overview

Mongado is the personal website of D. Erik Goodman (Mongado = anagram of Goodman). Built with Python FastAPI backend and Next.js frontend.

The site features:
- **Homepage**: Portfolio and professional presence
- **Knowledge Base**: Personal knowledge management (moving from Notion/offline notes)
- **Extensible architecture**: Designed for adding future projects

The Knowledge Base combines static markdown articles with a Zettelkasten-style note system featuring bidirectional linking, graph visualization, and AI-powered search.

## Key Patterns

### Functional Core, Imperative Shell

The backend follows a strict **Functional Core / Imperative Shell** architecture pattern:

**Functional Core** (`backend/core/`):
- Pure business logic with no I/O or side effects
- Deterministic functions: same input → same output
- Fully unit-testable without mocks or fixtures
- Examples: graph algorithms, wikilink parsing, similarity calculations, prompt building

**Imperative Shell** (`backend/routers/`, `backend/adapters/`):
- Thin orchestration layer for I/O operations
- Calls pure functions from core/ for business logic
- Handles database access, API requests, file I/O
- Tested with integration tests

**Directory Structure:**
```
backend/
├── core/               # Pure business logic (Functional Core)
│   ├── ai.py          # AI/ML algorithms (cosine similarity, ranking, prompts)
│   └── notes.py       # Notes/graph logic (wikilinks, BFS, graph building)
├── routers/           # API endpoints (Imperative Shell)
│   ├── ai.py          # AI feature endpoints (search, Q&A, suggestions)
│   ├── articles.py    # Article management endpoints
│   ├── notes.py       # Notes CRUD and graph endpoints
│   └── search.py      # Search endpoints
├── adapters/          # Data access layer (Imperative Shell)
│   ├── neo4j.py       # Neo4j database operations
│   └── article_loader.py   # Static file loading
└── notes_service.py   # Service layer (orchestrates adapters + core)
```

**Adding New Routers (Factory Pattern):**

All routers use a factory function for dependency injection. Follow this pattern:

```python
# backend/routers/example.py
from fastapi import APIRouter, Depends
from typing import Any

router = APIRouter(prefix="/api/example", tags=["example"])

def create_example_router(service: Any) -> APIRouter:
    """Create example router with dependencies injected.

    Args:
        service: Service instance for data access

    Returns:
        Configured APIRouter with endpoints
    """

    @router.get("/data", response_model=dict[str, Any])
    async def get_data() -> dict[str, Any]:
        """Get data endpoint."""
        # 1. Fetch data (I/O via service)
        raw_data = service.get_raw_data()

        # 2. Process with pure function from core
        from core import example
        processed = example.process_data(raw_data)

        return processed

    return router
```

Then register in `main.py`:

```python
from routers.example import create_example_router

# Create router with injected dependencies
example_router = create_example_router(service=some_service)
app.include_router(example_router)
```

**Why This Pattern:**
- **Testability**: Pure functions are trivial to test (no mocks needed)
- **Maintainability**: Business logic isolated from infrastructure
- **Dependency Injection**: Services injected at router creation time
- **Reusability**: Pure functions can be composed and reused
- **Type Safety**: All functions have full type hints

**Real Examples:**
- `core/notes.py:build_local_subgraph()` - BFS algorithm for graph traversal
- `core/ai.py:cosine_similarity()` - Vector similarity calculation
- `routers/notes.py:create_notes_router()` - Factory with dependency injection
- `routers/ai.py:create_ai_router()` - Factory with Ollama + notes service

**Testing:**
- `tests/unit/test_core_*.py` - Unit tests for pure functions (no I/O)
- `tests/unit/test_*_api.py` - Integration tests for endpoints (with TestClient)

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
- See `docs/knowledge-base/ARTICLES.md` for content authoring guide

**Notes** (Zettelkasten system):
- Persistent notes: Neo4j graph database (admin only)
- Adjective-noun IDs (e.g., `curious-elephant`, `wise-mountain`)
- Bidirectional wikilinks: `[[note-id]]` syntax
- See `docs/knowledge-base/NOTES.md` for complete guide

**Architecture**:
- Keep pure logic separate from data access
- Use dependency injection
- Follow functional core / imperative shell pattern

## Common Commands

**REMEMBER**: Use `make` commands for all operations - they automatically use docker-compose under the hood!

### Quick Reference

```bash
make help              # Show all available commands
make up                # Start all services (detached, no more forgetting -d!)
make down              # Stop all services
make logs              # View all logs (follow mode)
make status            # Show service status
```

### Docker Operations

```bash
# Start/Stop
make up                       # Start all services (detached)
make down                     # Stop all services
make restart                  # Restart all services
make restart-backend          # Restart backend only
make restart-frontend         # Restart frontend only

# Build
make rebuild                  # Rebuild and start all services
make rebuild-backend          # Rebuild backend only
make rebuild-frontend         # Rebuild frontend only

# Logs
make logs                     # Follow all logs
make logs-backend             # Follow backend logs
make logs-frontend            # Follow frontend logs
make logs-neo4j              # Follow Neo4j logs

# Shell Access
make shell-backend           # Bash shell in backend container
make shell-frontend          # Shell in frontend container

# Database
make db-shell                # Neo4j browser info
```

### Backend (Python 3.13)

```bash
# Testing
make test-backend                  # All tests
make test-backend-unit             # Unit tests only
make test-backend-integration      # Integration tests only
make test-backend-cov              # Tests with coverage
make test-backend-watch            # Tests in watch mode

# Code Quality
make lint-backend                  # Lint with ruff
make format-backend                # Format with ruff
make typecheck-backend             # Type check with mypy
make security                      # Security checks with bandit

# For specific test files (use docker compose directly):
docker compose exec backend pytest tests/unit/test_main.py::test_function_name -v

# Other commands (use docker compose directly):
docker compose exec backend python image_optimizer.py input.jpg output.webp 85 1200
docker compose exec backend python -m backend.script_name
```

### Frontend (Next.js 14 + TypeScript)

```bash
# Testing
make test-frontend             # Unit tests
make test-frontend-ui          # Tests with UI
make test-e2e                  # E2E tests

# Code Quality
make lint-frontend             # ESLint
make lint-frontend-fix         # ESLint with auto-fix
make typecheck-frontend        # TypeScript type check

# Build
make build-frontend            # Production build
make build-frontend-analyze    # Bundle analysis

# Dependencies (use docker compose directly):
docker compose exec frontend npm install package-name
```

### Combined Operations

```bash
make test                      # All tests (backend + frontend)
make test-all                  # Full test suite with coverage
make lint                      # All linters
make typecheck                 # All type checkers
make ci                        # Full CI pipeline
make ci-full                   # CI + E2E tests
```

### Production

```bash
make prod-up                   # Start production services
make prod-down                 # Stop production services
make prod-logs                 # View production logs
make prod-logs-backend         # Backend production logs
make prod-logs-frontend        # Frontend production logs
```

### Utilities

```bash
make clean                     # Clean generated files and stop containers
make clean-volumes             # Clean everything including volumes (WARNING: deletes data)
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

*Resources (Articles + Notes):*
- `GET /` - API status
- `GET /api/resources` - List all resources (articles + notes)
- `POST /api/resources` - Create resource
- `GET /api/resources/{id}` - Get resource by ID
- `DELETE /api/resources/{id}` - Delete resource

*Notes (Zettelkasten):*
- `GET /api/notes` - List all notes
- `POST /api/notes` - Create note (auth required for persistent)
- `GET /api/notes/{note_id}` - Get single note
- `PUT /api/notes/{note_id}` - Update note
- `DELETE /api/notes/{note_id}` - Delete note
- `GET /api/notes/{note_id}/links` - Get outbound links
- `GET /api/notes/{note_id}/backlinks` - Get inbound links
- `GET /api/notes/graph` - Get full graph
- `GET /api/notes/{note_id}/graph` - Get local subgraph
- `GET /api/notes/generate-id` - Generate adjective-noun ID

*AI Features:*
- `POST /api/search` - Semantic search (articles + notes)
- `POST /api/ask` - Q&A with context
- `POST /api/notes/{note_id}/suggest-links` - AI-suggested related notes
- `GET /api/notes/{note_id}/summary` - AI-generated note summary
- `GET /api/articles/{id}/summary` - AI-generated article summary

*Static Assets:*
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

**General:**
- `README.md` - Quick start guide
- `docs/README.md` - Documentation index
- `docs/SETUP.md` - Installation and 1Password setup
- `docs/PROJECT_STATUS.md` - Project health and verification
- `docs/ROADMAP.md` - Future features and TODOs

**Development:**
- `docs/TESTING.md` - Testing tools and commands
- `docs/PROFILING.md` - Performance profiling tools
- `docs/DEPENDENCIES.md` - Dependency structure

**Knowledge Base:**
- `docs/knowledge-base/README.md` - KB architecture overview
- `docs/knowledge-base/ARTICLES.md` - Article authoring guide
- `docs/knowledge-base/NOTES.md` - Zettelkasten note system guide

## Before Committing

**Quick check (both backend + frontend):**
```bash
make ci  # Runs lint, typecheck, security, and tests for both backend and frontend
```

**Or individually:**
```bash
make ci              # Backend + frontend CI
make test-all        # Full test suite with coverage
make ci-full         # CI + E2E tests (comprehensive)
```

## Common Pitfalls

1. **Don't use `print()`** - Use `logging` module
2. **Don't use `console.log()`** - Use logger utility
3. **Type hints required** - Won't pass CI without them
4. **1Password optional** - Code must work without it
5. **Test coverage** - All new features need tests
6. **Documentation** - Update relevant docs when changing features

## Future Work

See `docs/ROADMAP.md` for complete list. High-priority items:

- **Authentication system** - Dev/prod passkeys for admin access
- **Database migration** - Evaluate PostgreSQL vs continued Neo4j usage
- **Homepage** - Build out portfolio/professional presence
- **Knowledge Base enhancements** - Note templates, version history, advanced search
- **AI improvements** - Auto-tagging, clustering, concept extraction
- each time you need to restart or stop or start a service in this project, use "docker compose" rather than manually running them