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

> **⚠️ First Startup Note:** The backend generates and stores embeddings for all articles and notes on startup. This takes ~2-5 minutes the first time or after deleting containers/volumes. Subsequent startups are fast (~5-10 seconds) because embeddings are cached in Neo4j. You'll see progress logs like `[3/12] Generating embedding for article...` during this process.

## Technology Stack

**Backend:**
- Python 3.13, FastAPI, Pydantic v2
- pytest, mypy, ruff

**Frontend:**
- Next.js 14, React 18, TypeScript
- Tailwind CSS, Vitest, Playwright

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

## Roadmap

### Knowledge Base
- AI-powered search and context retrieval
- Database persistence (PostgreSQL/MongoDB)
- Full-text search
- Advanced tag filtering

### Future Projects
- Additional portfolio projects
- Blog/articles section
- Integration with other services

## License

MIT
