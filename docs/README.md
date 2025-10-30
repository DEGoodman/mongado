# Documentation Index

Documentation for the Mongado project - personal website and Knowledge Base.

## Quick Start

- **[Quick Start](../README.md)** - Get up and running in minutes
- **[SETUP.md](SETUP.md)** - Installation and 1Password configuration

## Project Documentation

### Planning & Status

- **[GitHub Issues](https://github.com/DEGoodman/mongado/issues)** - ⭐ Active work tracking and planning
- **[ROADMAP.md](ROADMAP.md)** - Historical roadmap (reference only, see GitHub Issues for active work)

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

### Archived Documentation

- **[archive/](archive/)** - Historical documentation and implementation notes (kept for reference)

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
├── ROADMAP.md                   # Historical roadmap (GitHub Issues is the active tracker)
├── ARCHITECTURE.md              # Backend architecture (Functional Core / Imperative Shell)
├── API.md                       # API documentation (Swagger/OpenAPI)
├── SETUP.md                     # Installation and 1Password configuration
├── TESTING.md                   # Testing guide and commands
├── PROFILING.md                 # Performance profiling tools
├── DEPENDENCIES.md              # Dependency management
├── DEPLOYMENT.md                # Production deployment guide
├── DISASTER_RECOVERY.md         # Backup and recovery procedures
├── knowledge-base/              # Knowledge Base documentation
│   ├── README.md                # KB architecture overview
│   ├── ARTICLES.md              # Article authoring guide
│   ├── NOTES.md                 # Notes/Zettelkasten guide
│   └── BACKUP_RESTORE.md        # KB backup/restore procedures
└── archive/                     # Historical documentation (reference only)
    ├── PROJECT_STATUS.md        # Old status doc (Oct 2024)
    ├── DEVELOPMENT_SETUP.md     # Old setup doc (Oct 2024)
    ├── DNS_SETUP.md             # DNS setup notes (completed)
    ├── EMBEDDING_STORAGE.md     # Embedding implementation design
    ├── LOCAL_API_SUBDOMAIN.md   # Local API subdomain setup
    └── LOCAL_DEV_OPTIMIZATION.md # Development optimizations
```

## External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [1Password Developer Documentation](https://developer.1password.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [Ollama Documentation](https://ollama.ai/)
