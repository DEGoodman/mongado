# Documentation Index

Welcome to the Mongado Knowledge Base documentation!

## Getting Started

- **[Quick Start](../README.md)** - Get up and running in minutes
- **[Setup Guide](SETUP.md)** - Detailed installation and 1Password configuration
- **[Development Setup](DEVELOPMENT_SETUP.md)** - Complete development environment overview

## Development Guides

- **[Testing](TESTING.md)** - Testing strategy, tools, and best practices
- **[Logging](LOGGING.md)** - Logging best practices for backend and frontend
- **[Profiling](PROFILING.md)** - Performance profiling and optimization
- **[Dependencies](DEPENDENCIES.md)** - Dependency management strategy

## Reference

- **[Project Status](PROJECT_STATUS.md)** - Current project status and verification

## Quick Links

### Backend (Python/FastAPI)

```bash
cd backend
make test          # Run tests
make lint          # Lint code
make format        # Format code
make typecheck     # Type check
make ci            # Full CI pipeline
```

See [TESTING.md](TESTING.md) for more backend commands.

### Frontend (Next.js/React)

```bash
cd frontend
npm test           # Run tests
npm run lint       # Lint code
npm run format     # Format code
npm run type-check # Type check
npm run test:all   # Full test suite
```

See [TESTING.md](TESTING.md) for more frontend commands.

## Documentation Organization

```
docs/
├── README.md              # This file
├── SETUP.md              # Setup and configuration
├── TESTING.md            # Testing guide
├── LOGGING.md            # Logging guide
├── PROFILING.md          # Performance guide
├── DEPENDENCIES.md       # Dependency management
├── DEVELOPMENT_SETUP.md  # Dev environment overview
└── PROJECT_STATUS.md     # Project status
```

## Contributing

When adding new documentation:

1. Place it in the `docs/` directory
2. Update this README with a link
3. Use relative links for cross-references
4. Keep the main README.md as a quick start guide

## External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [1Password Developer Documentation](https://developer.1password.com/)
- [Docker Documentation](https://docs.docker.com/)
