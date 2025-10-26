# Documentation Index

Documentation for the Mongado project - personal website and Knowledge Base.

## Quick Start

- **[Quick Start](../README.md)** - Get up and running in minutes
- **[SETUP.md](SETUP.md)** - Installation and 1Password configuration

## Project Documentation

### Current Status & Planning

- **[CURRENT_STATUS.md](CURRENT_STATUS.md)** - ⭐ Single source of truth for project status (Oct 2025)
- **[ROADMAP.md](ROADMAP.md)** - Future features, improvements, and TODOs

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

### Archived Documentation

- **[archive/](archive/)** - Historical documentation (outdated but kept for reference)

### Knowledge Base

The Knowledge Base is a separate subproject with its own documentation:

- **[knowledge-base/README.md](knowledge-base/README.md)** - Architecture overview
- **[knowledge-base/ARTICLES.md](knowledge-base/ARTICLES.md)** - Creating static articles
- **[knowledge-base/NOTES.md](knowledge-base/NOTES.md)** - Zettelkasten note system

## Quick Reference

### Backend Commands

```bash
cd backend
make run        # Start dev server
make test       # Run tests
make ci         # Full CI pipeline
make profile    # Profile performance
```

See [TESTING.md](TESTING.md) for complete command reference.

### Frontend Commands

```bash
cd frontend
npm run dev     # Start dev server
npm test        # Run tests
npm run test:all  # Full test suite
npm run build:analyze  # Bundle analysis
```

See [TESTING.md](TESTING.md) for complete command reference.

## Documentation Structure

```
docs/
├── README.md                    # This file - documentation index
├── CURRENT_STATUS.md            # ⭐ Current project status (single source of truth)
├── ROADMAP.md                   # Future plans and TODOs
├── DEPLOYMENT.md                # Production deployment guide
├── DISASTER_RECOVERY.md         # Recovery procedures
├── ARCHITECTURE.md              # Backend architecture (Functional Core / Imperative Shell)
├── API.md                       # API documentation (Swagger/OpenAPI)
├── SETUP.md                     # 1Password setup
├── TESTING.md                   # Testing guide
├── PROFILING.md                 # Performance profiling
├── DEPENDENCIES.md              # Dependency management
├── archive/                     # Historical/outdated documentation
│   ├── PROJECT_STATUS.md        # Old status doc (Oct 2024)
│   ├── DEVELOPMENT_SETUP.md     # Old setup doc (Oct 2024)
│   └── DNS_SETUP.md             # DNS setup (completed)
└── knowledge-base/              # Knowledge Base documentation
    ├── README.md                # KB architecture overview
    ├── ARTICLES.md              # Article authoring guide
    └── NOTES.md                 # Notes/Zettelkasten guide
```

## External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [1Password Developer Documentation](https://developer.1password.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [Ollama Documentation](https://ollama.ai/)
