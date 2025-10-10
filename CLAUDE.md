# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mongado is a knowledge base web application built with Python FastAPI backend and Next.js frontend. The project is in early development with plans for AI-powered search and context retrieval. Currently implements basic CRUD operations for knowledge resources with in-memory storage (database integration planned).

## Key Architecture Patterns

### Functional Core, Imperative Shell

The codebase follows this pattern for testability:
- **Functional Core**: Pure business logic functions with no side effects (fast unit tests)
- **Imperative Shell**: I/O operations (API endpoints, DB calls, external services) tested with integration tests
- This separation is intentional - keep business logic pure and testable

### Configuration & Secrets Management

All configuration happens through `backend/config.py`:
- Uses Pydantic Settings for environment variables and `.env` files
- **1Password Integration**: The `SecretManager` class auto-detects and uses either:
  - 1Password SDK (for service accounts via `OP_MONGADO_SERVICE_ACCOUNT_TOKEN` env var)
  - 1Password CLI (`op` command for personal accounts)
  - Gracefully falls back if neither available
- Access secrets: `secret_manager.get_secret("op://vault/item/field")`
- Settings access: `settings = get_settings()`

### Logging Architecture

**Backend** (`backend/logging_config.py`):
- Centralized logging configuration, console output (Docker-friendly)
- Always use `logger = logging.getLogger(__name__)` - never `print()`
- Use `%s` formatting (lazy evaluation): `logger.info("User %s logged in", user_id)`
- Log levels: DEBUG (dev only), INFO (normal), WARNING (recoverable), ERROR (failures), CRITICAL (crashes)

**Frontend** (`frontend/src/lib/logger.ts`):
- Custom logger with dev/prod awareness
- Use `import { logger } from "@/lib/logger"`
- Contextual logging: `const apiLogger = logger.withContext("API")`
- Debug logs auto-filtered in production

### Data Storage

Currently uses in-memory storage (`resources_db: list[dict[str, Any]]` in `main.py`). This is temporary - database layer is planned. When adding DB:
- Keep pure business logic separate from data access
- Use dependency injection for testability
- Follow functional core / imperative shell pattern

## Common Commands

### Backend (Python 3.13)

All backend commands use the Makefile from `backend/` directory:

```bash
cd backend

# Development
make run              # Start development server
make install          # Install dev dependencies
make install-prod     # Install production dependencies only

# Testing
make test             # Run all tests
make test-unit        # Unit tests only
make test-integration # Integration tests only
make test-cov         # Tests with coverage report

# Code Quality
make lint             # Ruff linter
make format           # Auto-format with ruff
make typecheck        # Mypy type checking
make security         # Bandit security scan
make quality          # Radon complexity analysis
make check            # Run lint + typecheck + security
make ci               # Full CI pipeline (check + test-cov)

# Profiling & Performance
make profile          # Profile with py-spy (low overhead)
make profile-viz      # Profile with VizTracer (interactive)
make benchmark        # Run API benchmarks
make memory           # Memory profiling with memray
make debug            # Run with IPython debugger

# Cleanup
make clean            # Remove cache and generated files
```

**Running a single test:**
```bash
cd backend
./venv/bin/pytest tests/unit/test_main.py::test_function_name -v
```

### Frontend (Next.js 14 + TypeScript)

```bash
cd frontend

# Development
npm run dev           # Start dev server (http://localhost:3000)
npm install           # Install dependencies

# Testing
npm test              # Run unit tests (Vitest)
npm run test:ui       # Tests with UI
npm run test:coverage # Tests with coverage
npm run test:e2e      # E2E tests (Playwright)
npm run test:e2e:ui   # E2E with Playwright UI
npm run test:all      # Full suite (typecheck + lint + tests)

# Code Quality
npm run lint          # ESLint
npm run lint:fix      # ESLint with auto-fix
npm run format        # Prettier formatting
npm run type-check    # TypeScript type checking

# Build & Analysis
npm run build         # Production build
npm run build:analyze # Bundle size analysis
npm run start         # Serve production build
```

**Running a single test:**
```bash
cd frontend
npm test src/__tests__/Component.test.tsx
```

### Docker

```bash
# Development (hot reload enabled)
docker-compose up
docker-compose up --build  # Rebuild after dependency changes

# Production
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## Type System Requirements

### Backend (Python 3.13)

**All functions must have type hints:**
```python
def process_resource(resource: Resource) -> dict[str, Any]:
    """Process a resource and return result."""
    return {"id": resource.id, "status": "processed"}
```

**Use modern Python 3.13 syntax:**
- Union types: `int | None` (not `Optional[int]`)
- Generics: `list[str]`, `dict[str, Any]` (not `List[str]`, `Dict[str, Any]`)
- No need to import `Optional`, `List`, `Dict` from typing

**Mypy is configured with strict mode** - all code must type check with `make typecheck`.

### Frontend (TypeScript)

Strict TypeScript mode enabled. Always use proper types, no `any` unless absolutely necessary.

## Dependency Management

### Backend (Three-Tier Structure)

- `requirements-base.txt`: Core production dependencies (~8 packages)
- `requirements-dev.txt`: Includes base + dev tools (~30 packages)
- `requirements-prod.txt`: Production only (references base + optional monitoring)
- `requirements.txt`: Symlink to requirements-dev.txt

**Adding dependencies:**
- Production runtime: Add to `requirements-base.txt`
- Dev/test tools: Add to `requirements-dev.txt` only
- Run `make install` after changes

### Frontend

- `dependencies`: Production runtime (React, Next.js only)
- `devDependencies`: Everything else (bundled by Next.js)

## API Structure

Currently in `backend/main.py`:
- FastAPI app with Pydantic v2 models
- All endpoints use response models for type safety
- CORS configured for local development (`http://localhost:3000`)
- Auto-generated OpenAPI docs at `/docs` and `/redoc`

Current endpoints:
- `GET /` - API status (includes 1Password status)
- `GET /api/resources` - List resources
- `POST /api/resources` - Create resource
- `GET /api/resources/{id}` - Get resource
- `DELETE /api/resources/{id}` - Delete resource

**Adding new endpoints:**
1. Define Pydantic models for request/response
2. Add response_model to decorator
3. Use proper HTTP status codes
4. Add corresponding tests in `tests/unit/test_main.py`

## Testing Strategy

### Backend Tests

Located in `backend/tests/`:
- `unit/` - Pure functions, no I/O
- `integration/` - API endpoints with TestClient
- `e2e/` - Full system tests (not yet implemented)

**Test fixtures** in `conftest.py`:
- `client` - FastAPI TestClient
- `sample_resource` - Example resource data
- `clear_resources` - Auto-clears in-memory DB before/after each test

### Frontend Tests

- `src/__tests__/` - Component unit tests (Vitest + Testing Library)
- `tests/e2e/` - E2E tests (Playwright)

Mock the logger in tests:
```typescript
jest.mock("@/lib/logger", () => ({
  logger: { error: jest.fn(), info: jest.fn(), warn: jest.fn(), debug: jest.fn() }
}));
```

## Documentation Structure

All detailed docs in `docs/`:
- `docs/SETUP.md` - Installation and 1Password setup
- `docs/TESTING.md` - Complete testing guide
- `docs/LOGGING.md` - Logging best practices (reference this when logging)
- `docs/PROFILING.md` - Performance profiling guide
- `docs/DEPENDENCIES.md` - Dependency management
- `docs/DEVELOPMENT_SETUP.md` - Development environment overview

The root `README.md` is a quick start guide - keep it concise.

## Before Committing

**Backend:**
```bash
make ci  # Runs lint, typecheck, security, and tests with coverage
```

**Frontend:**
```bash
npm run test:all  # Runs typecheck, lint, and tests with coverage
```

## Common Pitfalls

1. **Don't use `print()` in backend code** - Always use `logging` module
2. **Don't use `console.log()` in frontend** - Use the logger utility
3. **Type hints are required** - Code won't pass CI without them
4. **Test isolation** - The `clear_resources` fixture handles DB cleanup
5. **1Password is optional** - Code must work without it (use defaults)
6. **In-memory storage is temporary** - Design for future DB migration

## Future Work

From README.md, planned enhancements:
- AI-powered search and context retrieval (primary goal)
- Database persistence (PostgreSQL or MongoDB)
- Full-text search
- User authentication
- Advanced tag filtering
