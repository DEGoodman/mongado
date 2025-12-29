# Documentation Index

Documentation for the Mongado project - personal website and Knowledge Base.

## Quick Start

- **[Quick Start](../README.md)** - Get up and running in minutes
- **[SETUP.md](SETUP.md)** - Installation and 1Password configuration

## Project Documentation

### Planning & Status

- **[GitHub Issues](https://github.com/DEGoodman/mongado/issues)** - ⭐ Active work tracking and planning

### Deployment & Operations

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete production deployment guide (DigitalOcean)
- **[DISASTER_RECOVERY.md](DISASTER_RECOVERY.md)** - Recovery procedures and backups

### Development Guides

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Backend architecture (Functional Core / Imperative Shell)
- **[API.md](API.md)** - Interactive API documentation (Swagger/OpenAPI)
- **[SETUP.md](SETUP.md)** - 1Password service account setup
- **[TESTING.md](TESTING.md)** - Testing tools and commands
- **[PROFILING.md](PROFILING.md)** - Performance profiling tools
- **[DEPENDENCIES.md](DEPENDENCIES.md)** - Dependency structure and management

### Knowledge Base

The Knowledge Base is a separate subproject with its own documentation:

- **[knowledge-base/README.md](knowledge-base/README.md)** - Architecture overview
- **[knowledge-base/ARTICLES.md](knowledge-base/ARTICLES.md)** - Creating static articles
- **[knowledge-base/NOTES.md](knowledge-base/NOTES.md)** - Zettelkasten note system
- **[knowledge-base/BACKUP_RESTORE.md](knowledge-base/BACKUP_RESTORE.md)** - Backup and restore procedures

### UI/Design System

- **[UI_MIGRATION_GUIDE.md](UI_MIGRATION_GUIDE.md)** - SCSS module system (replaced Tailwind)
- **[DESIGN_TOKENS.md](DESIGN_TOKENS.md)** - Color, spacing, typography tokens
- **[COLOR_PALETTE.md](COLOR_PALETTE.md)** - Color scheme documentation
- **[COMPONENT_REFERENCE.md](COMPONENT_REFERENCE.md)** - Component styling patterns

## Quick Reference

### Common Commands (use `make` from project root)

```bash
make up                    # Start all services
make down                  # Stop all services
make logs                  # View all logs
make test                  # Run all tests (backend + frontend)
make ci                    # Full CI pipeline
make rebuild               # Rebuild and start all services
```

### Backend Commands (via Docker)

```bash
make test-backend          # Run backend tests
make test-backend-cov      # Tests with coverage
make lint-backend          # Lint with ruff
make typecheck-backend     # Type check with mypy
```

### Frontend Commands (via Docker)

```bash
make test-frontend         # Run frontend tests
make lint-frontend         # ESLint
make typecheck-frontend    # TypeScript check
make build-frontend        # Production build
```

See [TESTING.md](TESTING.md) for complete command reference.

## Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── ARCHITECTURE.md              # Backend architecture (Functional Core / Imperative Shell)
├── API.md                       # API documentation (Swagger/OpenAPI)
├── SETUP.md                     # Installation and 1Password configuration
├── TESTING.md                   # Testing guide and commands
├── PROFILING.md                 # Performance profiling tools
├── DEPENDENCIES.md              # Dependency management
├── DEPLOYMENT.md                # Production deployment guide
├── DISASTER_RECOVERY.md         # Backup and recovery procedures
├── UI_MIGRATION_GUIDE.md        # SCSS module system guide
├── DESIGN_TOKENS.md             # Design token documentation
├── COLOR_PALETTE.md             # Color scheme documentation
├── COMPONENT_REFERENCE.md       # Component styling patterns
├── DOCKER_DATA_SAFETY.md        # Docker volume safety info
└── knowledge-base/              # Knowledge Base documentation
    ├── README.md                # KB architecture overview
    ├── ARTICLES.md              # Article authoring guide
    ├── NOTES.md                 # Notes/Zettelkasten guide
    └── BACKUP_RESTORE.md        # KB backup/restore procedures
```

## External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [1Password Developer Documentation](https://developer.1password.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [Ollama Documentation](https://ollama.ai/)
