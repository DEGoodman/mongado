# Dependency Management

Dependency structure and management for backend and frontend.

## Backend (Python)

### Three-Tier Structure

```
requirements-base.txt      # Core production (~8 packages)
requirements-dev.txt       # Base + dev tools (~30 packages)
requirements-prod.txt      # Production only (base + monitoring)
requirements.txt           # Symlink to requirements-dev.txt
```

### Core Dependencies

**Production (`requirements-base.txt`):**
- `fastapi`: Web framework
- `uvicorn[standard]`: ASGI server with performance extras
- `pydantic`: Data validation
- `pydantic-settings`: Settings management
- `uvloop`: Fast event loop
- `httptools`: Fast HTTP parsing
- `onepassword`: Secrets management

**Development (`requirements-dev.txt`):**
- Testing: pytest, pytest-asyncio, pytest-cov, httpx
- Type checking: mypy, types-*
- Linting: ruff (replaces black, isort, flake8)
- Security: bandit
- Profiling: py-spy, memray, viztracer, line-profiler
- Debugging: ipython, ipdb, icecream, rich
- Quality: radon

### Commands

```bash
cd backend

# Development
make install          # Install dev dependencies

# Production
make install-prod     # Install production only
```

### Docker Builds

- **Development**: Uses `requirements-dev.txt` (all tools)
- **Production**: Uses `requirements-prod.txt` (minimal, ~600MB smaller)

## Frontend (Next.js/React)

### Structure

```json
{
  "dependencies": {},      // Production runtime (React, Next.js)
  "devDependencies": {}   // Everything else (bundled)
}
```

**Production:** React, react-dom, next (3 packages)

**Development:**
- TypeScript + type definitions
- Testing: Vitest, Testing Library, Playwright
- Linting: ESLint, Prettier
- Styling: Tailwind CSS, PostCSS, Autoprefixer
- Tools: Bundle analyzer, why-did-you-render

### Commands

```bash
cd frontend

npm install           # Install all
npm install --production  # Production only
npm update            # Update all
npm outdated          # Check for updates
```

## Adding Dependencies

### Backend

**Production dependency:**
1. Add to `requirements-base.txt`
2. Run `make install`
3. Test in Docker

**Dev tool:**
1. Add to `requirements-dev.txt` only
2. Run `make install`
3. Update Makefile if needed

### Frontend

**Production:**
```bash
npm install package
```

**Development:**
```bash
npm install -D package
```

## Security

```bash
# Backend
cd backend
bandit -r . -c pyproject.toml

# Frontend
cd frontend
npm audit
```

CI/CD runs automated security scanning on every PR.

## Size Comparison

**Backend Docker Images:**
- Development: ~800MB (with all tools)
- Production: ~200MB (minimal)

**Frontend Bundles:**
- Production: ~200KB (gzipped)

## Resources

- [pip requirements files](https://pip.pypa.io/en/stable/reference/requirements-file-format/)
- [npm package.json](https://docs.npmjs.com/cli/v10/configuring-npm/package-json)
- [Python security advisories](https://pypi.org/project/safety/)
- [npm security advisories](https://docs.npmjs.com/auditing-package-dependencies-for-security-vulnerabilities)
