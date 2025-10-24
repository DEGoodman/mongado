# Contributing to Mongado

Welcome! This guide covers how to contribute to Mongado, whether you're adding features, writing articles, fixing bugs, or improving documentation.

## Quick Start

1. **Check existing issues**: Browse [GitHub Issues](https://github.com/DEGoodman/mongado/issues) to see what's already planned
2. **Create an issue**: Discuss your idea before starting work
3. **Follow conventions**: See `CLAUDE.md` for code patterns and project structure
4. **Write tests**: All new features need tests
5. **Update docs**: Keep documentation in sync with changes

## Project Overview

Mongado is a personal website combining:
- **Knowledge Base**: Zettelkasten-style notes with AI-powered search
- **Articles**: Technical writing on engineering, management, and SaaS
- **Portfolio**: Professional presence (coming soon)

**Tech Stack**:
- Backend: Python 3.13 + FastAPI + Neo4j
- Frontend: Next.js 14 + TypeScript + React
- AI: Ollama (local LLM)
- Deployment: Docker + DigitalOcean + GitHub Actions

See `README.md` for setup instructions.

## Issue Tracking

All work is tracked via GitHub Issues. **Do not create TODO files** - use issues instead.

### Label System

**Status Labels** (Workflow):
- `status: idea` - Initial brainstorming, not ready to start
- `status: todo` - Ready to be worked on (backlog)
- `status: in-progress` - Currently being worked on
- `status: done` - Completed (close the issue)

**Category Labels** (Type of Work):
- `feature` - New feature or enhancement
- `bug` - Something isn't working
- `infrastructure` - Infrastructure, deployment, DevOps
- `documentation` - Documentation improvements
- `article-idea` - Future article topics to develop

**Topic Labels** (Content Area):
- `saas` - SaaS-related topics (billing, revenue, etc.)
- `management` - Engineering management and leadership
- `sre` - Site Reliability Engineering

### Creating Issues

**Article Idea**:
```bash
gh issue create \
  --title "Article: Your Article Title" \
  --label "article-idea,management,status: idea" \
  --body "## Overview
Cover the main topic...

## Tags
tag1, tag2, tag3"
```

**Feature Request**:
```bash
gh issue create \
  --title "Feature: Your Feature Name" \
  --label "feature,status: todo" \
  --body "## Goal
What we're trying to achieve...

## Tasks
- [ ] Task 1
- [ ] Task 2"
```

**Bug Report**:
```bash
gh issue create \
  --title "Bug: Description of the bug" \
  --label "bug,status: todo" \
  --body "## Steps to Reproduce
1. Step 1
2. Step 2

## Expected Behavior
What should happen

## Actual Behavior
What actually happens"
```

### Working on Issues

1. **Pick an issue**: Look for `status: todo` items
2. **Update status**: `gh issue edit 123 --remove-label "status: todo" --add-label "status: in-progress"`
3. **Create a branch**: `git checkout -b feature/issue-123-description`
4. **Do the work**: Follow code conventions in `CLAUDE.md`
5. **Reference issue**: In commits: `git commit -m "feat: add feature (fixes #123)"`
6. **Close when done**: `gh issue close 123`

### Finding Issues

```bash
# View ready-to-work items
gh issue list --label "status: todo"

# View all article ideas
gh issue list --label "article-idea"

# View by topic
gh issue list --label "management"
gh issue list --label "sre"
```

## Code Conventions

See `CLAUDE.md` for detailed conventions. Key points:

### Backend (Python 3.13)

- **Type hints required**: All functions must have type hints
- **Modern syntax**: Use `int | None`, not `Optional[int]`
- **Logging**: Use `logger = logging.getLogger(__name__)`, never `print()`
- **Functional core**: Keep business logic pure, separate from I/O
- **Tests**: All features need unit tests

```python
def process_resource(resource: Resource) -> dict[str, Any]:
    """Process a resource and return result."""
    return {"id": resource.id, "status": "processed"}
```

### Frontend (TypeScript)

- **Strict TypeScript**: Avoid `any` unless absolutely necessary
- **Logging**: Use `import { logger } from "@/lib/logger"`
- **Components**: Follow existing patterns in `src/components/`

### Testing

**Backend**:
```bash
cd backend
make test              # Run all tests
make test-unit         # Unit tests only
make test-cov          # Tests with coverage
```

**Frontend**:
```bash
cd frontend
npm test               # Unit tests
npm run test:e2e       # E2E tests
```

### Before Committing

**Backend**:
```bash
make ci  # lint + typecheck + security + tests
```

**Frontend**:
```bash
npm run test:all  # typecheck + lint + tests
```

## Git Workflow

### Commit Messages

Follow conventional commits:

```
feat: add new feature
fix: resolve bug in component
docs: update documentation
refactor: improve code structure
test: add missing tests
chore: update dependencies
```

Always reference issues: `feat: add auth system (fixes #8)`

### Pull Requests

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Push and create a PR
4. Link to the issue: `Closes #123`
5. Wait for CI checks to pass
6. Merge when approved

## Writing Articles

Articles are markdown files in `backend/static/articles/`.

### Article Structure

```markdown
---
id: 8
title: "Your Article Title"
url: "https://optional-reference.com"
tags: ["Tag1", "Tag2"]
created_at: "2025-10-24T10:00:00"
---

## Intro

Introduction paragraph setting context...

## Section 1

Content with clear structure...

## Key Takeaways

- Bullet point 1
- Bullet point 2
```

### Style Guide

- **Concise**: Get to the point quickly
- **Framework-focused**: Provide actionable structure
- **Examples**: Include practical examples
- **No fluff**: Skip unnecessary words
- **Scannable**: Use headers, bullets, tables

See existing articles (001-007) for reference.

### Creating Articles

1. Create issue: `gh issue create --label "article-idea,status: todo"`
2. Write article in `backend/static/articles/00X-slug.md`
3. Test locally: Article auto-loads on backend restart
4. Commit: `git commit -m "feat: add article on X (closes #Y)"`
5. Push: Deploys automatically via GitHub Actions

## Documentation

Keep these docs updated:

- `README.md` - Project overview and setup
- `CLAUDE.md` - Code conventions and patterns
- `CONTRIBUTING.md` - This file
- `docs/` - Detailed guides for specific features

**Do not create TODO files**. Use GitHub Issues instead.

## Deployment

Deployment is automatic via GitHub Actions:

- **Full deployment**: Push to `main` triggers rebuild
- **Article deployment**: Changes to `backend/static/articles/**` triggers fast deploy (~25s)
- **Production**: https://mongado.com and https://api.mongado.com

See `.github/workflows/` for CI/CD configuration.

## Mobile Workflow

You can manage issues from mobile:

### GitHub Mobile App
1. Download GitHub mobile app
2. Browse/create/update issues
3. Add comments and ideas
4. Update labels and status

### Web Browser
- https://github.com/DEGoodman/mongado/issues
- Fully functional on mobile

## Getting Help

- **Documentation**: Check `docs/` folder first
- **Ask questions**: Create an issue with `question` label
- **Code patterns**: See `CLAUDE.md`
- **Setup issues**: See `docs/SETUP.md`

## Project Structure

```
mongado/
├── backend/              # FastAPI backend
│   ├── static/
│   │   ├── articles/     # Markdown articles
│   │   └── assets/       # Images, icons
│   ├── tests/            # Backend tests
│   └── *.py              # Python modules
├── frontend/             # Next.js frontend
│   ├── src/
│   │   ├── app/          # Next.js 14 app router
│   │   ├── components/   # React components
│   │   └── lib/          # Utilities
│   └── tests/            # Frontend tests
├── docs/                 # Documentation
├── .github/workflows/    # CI/CD
├── CLAUDE.md             # Code conventions
├── CONTRIBUTING.md       # This file
└── README.md             # Getting started
```

## Common Commands

See `CLAUDE.md` for comprehensive command reference.

**Docker**:
```bash
docker compose up                    # Start dev environment
docker compose -f docker-compose.prod.yml up -d  # Production
```

**Issues**:
```bash
gh issue list --label "status: todo"  # View backlog
gh issue create                       # New issue
gh issue close 123                    # Close issue
```

**Testing**:
```bash
make test         # Backend tests
npm test          # Frontend tests
```

## Best Practices

1. **Create issues first** - Discuss before coding
2. **Small PRs** - Break large features into reviewable chunks
3. **Test coverage** - All new features need tests
4. **Update docs** - Keep documentation current
5. **Reference issues** - Use `fixes #123` in commits
6. **Status labels** - Keep issue status updated
7. **Close when done** - Close issues when work is complete

## Questions?

- Open an issue with `question` label
- Check existing documentation in `docs/`
- Review `CLAUDE.md` for project conventions

---

Last updated: 2025-10-24
