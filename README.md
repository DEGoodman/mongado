# Mongado Knowledge Base

A modern web application for managing your personal knowledge base with integrated AI capabilities. Built with Python (FastAPI) backend and Next.js frontend.

## Features

- 📚 Create, view, and manage knowledge resources
- 🏷️ Tag resources for easy organization
- 🔗 Store links alongside your notes
- 🎨 Clean, responsive UI with Tailwind CSS
- 🔐 Secure credential management with 1Password
- 🐳 Docker containerization for dev and production

## Quick Start

### Prerequisites

- Docker Desktop or Docker Engine
- Docker Compose v2.0+
- (Optional) 1Password CLI for credential management

### Run with Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mongado
   ```

2. **Start the application**:
   ```bash
   docker-compose up
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

That's it! The application is now running with hot reload enabled.

### Manual Setup (without Docker)

If you prefer to run without Docker:

**Backend:**
```bash
cd backend
python3.13 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
python main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

See [docs/SETUP.md](docs/SETUP.md) for detailed setup instructions.

## Project Structure

```
mongado/
├── backend/              # Python FastAPI backend
│   ├── main.py          # API endpoints
│   ├── config.py        # Configuration & 1Password
│   ├── logging_config.py # Logging setup
│   ├── tests/           # Test suite
│   └── scripts/         # Profiling & benchmarking
├── frontend/            # Next.js React frontend
│   └── src/
│       ├── app/         # Pages and layouts
│       └── lib/         # Utilities (logger, etc.)
├── docs/                # Documentation
└── docker-compose.yml   # Development orchestration
```

## API Endpoints

- `GET /` - API information
- `GET /api/resources` - Get all resources
- `POST /api/resources` - Create a new resource
- `GET /api/resources/{id}` - Get a specific resource
- `DELETE /api/resources/{id}` - Delete a resource

Full API documentation available at http://localhost:8000/docs when running.

## Development

### Common Commands

```bash
# Start development environment
docker-compose up

# Rebuild after dependency changes
docker-compose up --build

# Run backend tests
cd backend && make test

# Run frontend tests
cd frontend && npm test

# View logs
docker-compose logs -f
```

### Documentation

- **[Setup Guide](docs/SETUP.md)** - Detailed installation and configuration
- **[Testing](docs/TESTING.md)** - Testing strategy and tools
- **[Logging](docs/LOGGING.md)** - Logging best practices
- **[Profiling](docs/PROFILING.md)** - Performance profiling and optimization
- **[Dependencies](docs/DEPENDENCIES.md)** - Dependency management strategy
- **[Development Setup](docs/DEVELOPMENT_SETUP.md)** - Complete development environment

### Technology Stack

**Backend:**
- Python 3.13
- FastAPI
- Pydantic v2
- pytest (testing)
- mypy (type checking)
- ruff (linting)

**Frontend:**
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Vitest (testing)
- Playwright (E2E testing)

**DevOps:**
- Docker & Docker Compose
- 1Password (secrets management)
- GitHub Actions (CI/CD)

## 1Password Integration (Optional)

This project supports 1Password for secure credential management. This is especially useful when developing in the open to avoid committing secrets to GitHub.

**Quick Setup:**
```bash
# Install 1Password CLI
brew install 1password-cli  # macOS

# Sign in
op account add

# Set token (for service accounts)
export OP_MONGADO_SERVICE_ACCOUNT_TOKEN="your-token"
```

See [docs/SETUP.md](docs/SETUP.md#1password-setup) for detailed instructions.

## Production Deployment

```bash
# Build and run production containers
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

Production builds use optimized dependencies and multi-stage Docker builds for minimal image sizes (~600MB smaller than dev).

## Contributing

This is a personal project, but suggestions and improvements are welcome! Please check the documentation in the `docs/` directory for development guidelines.

## Future Enhancements

- 🤖 AI-powered search and context retrieval
- 💾 Database persistence (PostgreSQL/MongoDB)
- 🔍 Full-text search
- 👤 User authentication
- 📱 Mobile-responsive improvements
- 🏷️ Advanced tag filtering

## License

MIT
