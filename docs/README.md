# Documentation Index

Documentation for the Mongado project - personal website and Knowledge Base.

## Quick Start

- **[Quick Start](../README.md)** - Get up and running in minutes
- **[SETUP.md](SETUP.md)** - Installation and 1Password configuration

## Project Documentation

### General

- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Current project status and setup verification
- **[ROADMAP.md](ROADMAP.md)** - Future features, improvements, and TODOs
- **[DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)** - Detailed development environment setup

### Development Guides

- **[TESTING.md](TESTING.md)** - Testing tools and commands
- **[PROFILING.md](PROFILING.md)** - Performance profiling tools
- **[DEPENDENCIES.md](DEPENDENCIES.md)** - Dependency structure and management

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
├── SETUP.md                     # Environment setup and configuration
├── PROJECT_STATUS.md           # Project health and verification
├── ROADMAP.md                  # Future plans and TODOs
├── TESTING.md                  # Testing guide
├── PROFILING.md                # Performance profiling
├── DEPENDENCIES.md             # Dependency management
└── knowledge-base/             # Knowledge Base documentation
    ├── README.md               # KB architecture overview
    ├── ARTICLES.md             # Article authoring guide
    └── NOTES.md                # Notes/Zettelkasten guide
```

## External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [1Password Developer Documentation](https://developer.1password.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [Ollama Documentation](https://ollama.ai/)
