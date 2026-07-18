# Mongado

Personal website of D. Erik Goodman. Built with Python (FastAPI) backend and Next.js frontend.

> **Mongado** is an anagram of "Goodman"

## Features

- **Personal Homepage**: Portfolio and professional presence
- **Knowledge Base**: Personal knowledge management system (moving from Notion and offline notes)
- **Extensible**: Designed for easy addition of future projects

## Quick Start

### Docker (Recommended)

```bash
git clone <repository-url>
cd mongado
docker compose up
```

- Homepage: http://localhost:3000
- Knowledge Base: http://localhost:3000/knowledge-base
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Manual Setup

**Backend:**
```bash
cd backend
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
make run
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Git Hooks (Optional but Recommended):**
```bash
./setup-hooks.sh
```

This enables pre-push hooks that run fast quality checks (linting, type checking, formatting) before pushing code. Prevents CI failures and keeps the feedback loop tight.

**Seeding Test Notes (Optional):**
```bash
# Restore dev backup with 50+ test notes for development/testing
docker compose up -d
cat dev-backups/test-notes-backup.tar.gz | docker compose exec -T neo4j sh -c 'cat > /var/mongado-backups/test-notes.tar.gz'
docker compose exec -it neo4j /scripts/restore_neo4j.sh test-notes.tar.gz
docker compose restart neo4j
```

Articles load automatically from `backend/static/articles/`. Test notes provide a realistic Zettelkasten corpus (~50 notes) for testing AI features, search, and graph traversal.

## Project Structure

```
mongado/
├── backend/              # Python FastAPI backend
│   ├── main.py          # API endpoints
│   ├── config.py        # Configuration & secrets
│   ├── tests/           # Test suite
│   └── Makefile         # Dev commands
├── frontend/            # Next.js React frontend
│   └── src/
│       ├── app/         # Pages (homepage, knowledge-base, etc.)
│       ├── components/  # Reusable components
│       └── lib/         # Utilities
└── docs/                # Documentation
```

## Common Commands

**Backend:**
```bash
cd backend
make test       # Run tests
make ci         # Full CI pipeline (lint, typecheck, security, tests)
make profile    # Profile performance
```

**Frontend:**
```bash
cd frontend
npm test        # Run tests
npm run test:all  # Full test suite (typecheck, lint, tests)
npm run build:analyze  # Analyze bundle size
```

**Docker:**
```bash
docker compose up --build  # Rebuild after dependency changes
docker compose logs -f backend  # View logs
```

> **⚠️ Embeddings Note:** Semantic search needs embeddings stored in Neo4j. Sync is triggered manually via `POST /api/admin/sync-embeddings` (admin token required), or on startup if `SYNC_EMBEDDINGS_ON_STARTUP=true`. The first sync takes a few minutes (each document is embedded in section-level chunks); later syncs skip unchanged content via content hashing.

> **📦 Required Ollama Models:** The AI features require these models:
> - `nomic-embed-text` (embeddings, auto-downloaded)
> - `llama3.2:1b` (chat, auto-downloaded)
> - `qwen2.5:1.5b` (AI suggestions) - **Pull manually:** `docker compose exec ollama ollama pull qwen2.5:1.5b`

## Technology Stack

**Backend:**
- Python 3.13, FastAPI, Pydantic v2
- pytest, mypy, ruff

**Frontend:**
- Next.js 15 (App Router, server components), React 19, TypeScript
- SCSS Modules (design tokens + mixins), Vitest, Playwright

**DevOps:**
- Docker, 1Password (optional secrets management)

## Adding New Projects

The site uses centralized configuration for easy extensibility:

1. **Update site config** (`frontend/src/lib/site-config.ts`):
   - Add any new site-wide data or links

2. **Create new route** (e.g., `frontend/src/app/[project-name]/page.tsx`):
   ```tsx
   export default function ProjectPage() {
     return <div>Your project here</div>;
   }
   ```

3. **Add to homepage** (`frontend/src/app/page.tsx`):
   ```tsx
   <ProjectTile
     title="Project Name"
     description="Project description"
     href="/project-name"
     icon="🚀"
   />
   ```

4. **Add backend endpoints** (if needed) in `backend/main.py`

All existing infrastructure (components, styling, config) is reusable. The `ProjectTile` component and `siteConfig` follow DRY principles.

## Documentation

- [SETUP.md](docs/SETUP.md) - Installation and 1Password setup
- [TESTING.md](docs/TESTING.md) - Testing strategy and tools
- [PROFILING.md](docs/PROFILING.md) - Performance profiling
- [DEPENDENCIES.md](docs/DEPENDENCIES.md) - Dependency management

## Current Features

### Knowledge Base (Implemented)
- AI-powered semantic search (chunked embeddings; documents rank by their best-matching section. Ollama in dev, Gemini API in prod)
- Q&A with context from knowledge base
- Neo4j graph database for notes
- Zettelkasten-style bidirectional wikilinks
- Graph visualization with force-directed layout
- AI-generated summaries and link suggestions
- Note templates for structured content
- Stale note resurfacing ("Note of the Day")

### In Progress / Planned
See [GitHub Issues](https://github.com/DEGoodman/mongado/issues) for active work tracking.

Key open items:
- AI writing assistant in note editor (#146)
- Articles pagination and categorization (#113, #114)
- Homepage portfolio buildout

## License

MIT
