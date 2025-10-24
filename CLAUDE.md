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

**Never create TODO files**. Instead:
1. Create issues: `gh issue create --label "feature,status: todo"`
2. Track progress with status labels: `idea` → `todo` → `in-progress` → `done`
3. Reference issues in commits: `feat: add feature (fixes #123)`
4. Close issues when work is complete

See `CONTRIBUTING.md` for complete workflow.

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

## Project Overview

Mongado is the personal website of D. Erik Goodman (Mongado = anagram of Goodman). Built with Python FastAPI backend and Next.js frontend.

The site features:
- **Homepage**: Portfolio and professional presence
- **Knowledge Base**: Personal knowledge management (moving from Notion/offline notes)
- **Extensible architecture**: Designed for adding future projects

The Knowledge Base combines static markdown articles with a Zettelkasten-style note system featuring bidirectional linking, graph visualization, and AI-powered search.

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
- See `docs/knowledge-base/ARTICLES.md` for content authoring guide

**Notes** (Zettelkasten system):
- Persistent notes: Neo4j graph database (admin only)
- Ephemeral notes: In-memory with session tracking (visitors)
- Adjective-noun IDs (e.g., `curious-elephant`, `wise-mountain`)
- Bidirectional wikilinks: `[[note-id]]` syntax
- See `docs/knowledge-base/NOTES.md` for complete guide

**Architecture**:
- Keep pure logic separate from data access
- Use dependency injection
- Follow functional core / imperative shell pattern

## Common Commands

**REMEMBER**: Always use `docker compose exec` to run commands in containers!

### Docker (Primary Interface)

```bash
# Start/Stop Services
docker compose up -d              # Start all services (detached)
docker compose down               # Stop all services
docker compose restart backend    # Restart specific service
docker compose up -d --build      # Rebuild and start

# View Logs
docker compose logs -f backend    # Follow backend logs
docker compose logs frontend      # View frontend logs
docker compose logs               # All services

# Execute Commands in Containers
docker compose exec backend bash                    # Shell into backend
docker compose exec frontend sh                     # Shell into frontend
docker compose exec backend python manage.py        # Run Python script
docker compose exec frontend npm run build          # Run npm command

# Production
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f backend
```

### Backend (Python 3.13) - via Docker

**Run ALL backend commands through docker compose**:

```bash
# Testing
docker compose exec backend pytest tests/                           # All tests
docker compose exec backend pytest tests/unit/                      # Unit tests
docker compose exec backend pytest tests/ --cov                     # With coverage
docker compose exec backend pytest tests/unit/test_main.py::test_function_name -v  # Single test

# Code Quality
docker compose exec backend ruff check .                            # Lint
docker compose exec backend ruff format .                           # Format
docker compose exec backend mypy main.py                            # Type check

# Other Commands
docker compose exec backend python image_optimizer.py input.jpg output.webp 85 1200
docker compose exec backend python -m backend.script_name           # Run script
```

**Make commands** (if you're already in the backend directory and need quick reference):
```bash
# These internally use docker compose exec
make test             # docker compose exec backend pytest tests/
make lint             # docker compose exec backend ruff check .
make format           # docker compose exec backend ruff format .
```

### Frontend (Next.js 14 + TypeScript) - via Docker

**Run ALL frontend commands through docker compose**:

```bash
# Testing
docker compose exec frontend npm test                    # Unit tests
docker compose exec frontend npm run test:ui             # Tests with UI
docker compose exec frontend npm run test:e2e            # E2E tests
docker compose exec frontend npm run test:all            # Full suite

# Code Quality
docker compose exec frontend npm run lint                # ESLint
docker compose exec frontend npm run lint:fix            # ESLint with auto-fix
docker compose exec frontend npm run type-check          # TypeScript

# Build
docker compose exec frontend npm run build               # Production build
docker compose exec frontend npm run build:analyze       # Bundle analysis

# Dependencies
docker compose exec frontend npm install package-name    # Install new package
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