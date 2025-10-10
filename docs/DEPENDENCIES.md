# Dependency Management

## Backend (Python)

### Structure

We use a three-tier dependency structure:

```
requirements-base.txt      # Core production dependencies
requirements-dev.txt       # Development tools (includes base)
requirements-prod.txt      # Production only (includes base)
requirements.txt           # Symlink to requirements-dev.txt
```

### Production Dependencies (`requirements-base.txt`)

**Core Framework:**
- `fastapi`: Web framework
- `uvicorn[standard]`: ASGI server with performance extras
- `pydantic`: Data validation
- `pydantic-settings`: Settings management

**Performance:**
- `uvloop`: Fast event loop implementation
- `httptools`: Fast HTTP parsing

**Security:**
- `onepassword`: Secrets management

**Total: ~8 packages**

### Development Dependencies (`requirements-dev.txt`)

Includes base + these development tools:

**Testing:**
- `pytest`: Test framework
- `pytest-asyncio`: Async test support
- `pytest-cov`: Coverage reporting
- `pytest-mock`: Mocking support
- `pytest-xdist`: Parallel test execution
- `pytest-benchmark`: Performance benchmarking
- `httpx`: FastAPI test client

**Type Checking:**
- `mypy`: Static type checker
- `types-*`: Type stubs

**Linting & Formatting:**
- `ruff`: Fast linter and formatter (replaces black, isort, flake8)

**Security:**
- `bandit`: Security vulnerability scanner

**Code Quality:**
- `radon`: Complexity analyzer

**Profiling:**
- `py-spy`: Low-overhead profiler
- `memray`: Memory profiler
- `viztracer`: Visual tracing profiler
- `line-profiler`: Line-by-line profiler
- `memory-profiler`: Memory usage profiler

**Debugging:**
- `ipython`: Better REPL
- `ipdb`: IPython debugger
- `icecream`: Better print debugging
- `rich`: Beautiful terminal output

**Dev Tools:**
- `watchfiles`: Fast file watching

**Total: ~30 packages**

### Installation

```bash
# Development (default)
make install
# or
pip install -r requirements-dev.txt

# Production only
make install-prod
# or
pip install -r requirements-prod.txt
```

### Docker Builds

- **Development**: Uses `requirements-dev.txt` (all tools available)
- **Production**: Uses `requirements-prod.txt` (minimal footprint)

## Frontend (Next.js/React)

### Structure

```json
{
  "dependencies": {},      // Production runtime deps
  "devDependencies": {}   // Development and build tools
}
```

### Production Dependencies

**Core Framework:**
- `react`: UI library
- `react-dom`: React DOM renderer
- `next`: React framework

**Total: 3 packages**

All other dependencies are dev-only since Next.js bundles everything.

### Development Dependencies

**TypeScript:**
- `typescript`: Type system
- `@types/*`: Type definitions

**Testing:**
- `vitest`: Fast test runner
- `@vitest/ui`: Test UI
- `@vitest/coverage-v8`: Coverage
- `@testing-library/react`: Component testing
- `@testing-library/jest-dom`: DOM assertions
- `@testing-library/user-event`: User interaction simulation
- `@playwright/test`: E2E testing

**Linting & Formatting:**
- `eslint`: JavaScript linter
- `eslint-config-next`: Next.js ESLint config
- `eslint-config-prettier`: Prettier integration
- `prettier`: Code formatter
- `prettier-plugin-tailwindcss`: Tailwind class sorting

**Styling:**
- `tailwindcss`: Utility-first CSS
- `autoprefixer`: CSS vendor prefixing
- `postcss`: CSS processing

**Development Tools:**
- `@next/bundle-analyzer`: Bundle size analysis
- `why-did-you-render`: Re-render debugging

**Total: ~25 packages**

### Installation

```bash
# Install all dependencies
npm install

# Install production only
npm install --production
```

### Bundle Optimization

Production builds automatically exclude all devDependencies.

## Updating Dependencies

### Backend

```bash
cd backend

# Update all to latest compatible versions
pip install --upgrade -r requirements-dev.txt

# Check for security issues
pip-audit

# Update specific package
pip install --upgrade fastapi
```

### Frontend

```bash
cd frontend

# Update all to latest compatible versions
npm update

# Check for security issues
npm audit

# Update specific package
npm install next@latest

# Find outdated packages
npm outdated
```

## Dependency Policies

### Production

1. **Keep minimal**: Only include what's needed at runtime
2. **Pin versions**: Exact versions for reproducibility
3. **Security first**: Regular updates for security patches
4. **Test updates**: Always test before deploying

### Development

1. **Include all tools**: Don't make developers install separately
2. **Keep current**: Update regularly
3. **Document purpose**: Comment why each dependency exists
4. **Remove unused**: Regular cleanup

## Size Comparison

### Backend Docker Images

```
Development: ~800MB (with all tools)
Production:  ~200MB (minimal deps)
```

### Frontend Bundles

```
Development build: N/A (not bundled)
Production build:  ~200KB (gzipped)
```

## Security

### Automated Scanning

```bash
# Backend
cd backend
bandit -r . -c pyproject.toml

# Frontend
cd frontend
npm audit
```

### CI/CD

Both backend and frontend have automated security scanning in GitHub Actions:
- Runs on every PR
- Blocks merge if critical vulnerabilities found
- Auto-updates dependencies (optional)

## Common Issues

### Backend

**Issue**: `ImportError` in production
**Solution**: Add missing package to `requirements-base.txt`

**Issue**: Slow Docker builds
**Solution**: Use Docker layer caching, pin versions

### Frontend

**Issue**: Bundle too large
**Solution**: Run `npm run build:analyze` and remove unnecessary deps

**Issue**: Type errors after update
**Solution**: Update `@types/*` packages to match

## Best Practices

### Backend

1. Always use virtual environment
2. Pin exact versions in requirements files
3. Use `requirements-dev.txt` for development
4. Use `requirements-prod.txt` for Docker production
5. Regular security audits with `bandit`

### Frontend

1. Use exact versions (`1.2.3` not `^1.2.3`) for stability
2. Review bundle size after adding dependencies
3. Prefer lighter alternatives when possible
4. Keep React/Next.js in sync
5. Regular security audits with `npm audit`

## Migration Guide

### Adding New Production Dependency (Backend)

1. Add to `requirements-base.txt`
2. Run `make install` to update dev environment
3. Update Dockerfile if needed
4. Test in Docker
5. Update documentation

### Adding New Dev Tool (Backend)

1. Add to `requirements-dev.txt` only
2. Run `make install`
3. Update Makefile if it needs a command
4. Document in [PROFILING.md](PROFILING.md) or [TESTING.md](TESTING.md)

### Adding New Dependency (Frontend)

1. Decide: runtime (dependencies) or build-time (devDependencies)
2. Install with `npm install package` or `npm install -D package`
3. Test build: `npm run build`
4. Update documentation if it's a tool

## Logging

Both backend and frontend follow structured logging best practices:

- **Backend**: Python `logging` module configured in `logging_config.py`
- **Frontend**: Custom logger utility in `src/lib/logger.ts`
- Logs write to console (Docker/Kubernetes friendly)
- See [LOGGING.md](LOGGING.md) for complete guidelines

## Resources

- [pip requirements files](https://pip.pypa.io/en/stable/reference/requirements-file-format/)
- [npm package.json](https://docs.npmjs.com/cli/v10/configuring-npm/package-json)
- [Python security advisories](https://pypi.org/project/safety/)
- [npm security advisories](https://docs.npmjs.com/auditing-package-dependencies-for-security-vulnerabilities)
- [LOGGING.md](LOGGING.md) - Logging best practices guide
