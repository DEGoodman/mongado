# Testing Guide

Testing infrastructure for the Mongado Knowledge Base project.

## Architecture: Functional Core, Imperative Shell

- **Functional Core**: Pure functions, no side effects (fast unit tests)
- **Imperative Shell**: I/O operations, API calls, database (integration tests)

This separation provides fast feedback loops and better maintainability.

## Backend Testing (Python/FastAPI)

### Test Structure

```
backend/tests/
├── unit/           # Pure function tests, no I/O
├── integration/    # API endpoint tests with TestClient
└── e2e/            # Full system tests (planned)
```

### Tools

- **[pytest](https://docs.pytest.org/)**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **httpx**: FastAPI test client
- **[ruff](https://docs.astral.sh/ruff/)**: Fast linter and formatter
- **[mypy](https://mypy.readthedocs.io/)**: Static type checker
- **[bandit](https://bandit.readthedocs.io/)**: Security vulnerability scanner
- **[radon](https://radon.readthedocs.io/)**: Code complexity analyzer

### Running Tests

```bash
cd backend

make test             # Run all tests
make test-unit        # Unit tests only
make test-integration # Integration tests only
make test-cov         # Tests with coverage

make check            # lint + typecheck + security
make ci               # Full CI pipeline

# Single test
./venv/bin/pytest tests/unit/test_main.py::test_function_name -v
```

### Type Hints Required

All Python code must include type hints and pass `make typecheck`.

## Frontend Testing (Next.js/React/TypeScript)

### Test Structure

```
frontend/
├── src/__tests__/       # Component unit tests
├── tests/
│   ├── integration/     # Integration tests
│   └── e2e/            # Playwright E2E tests
```

### Tools

- **[Vitest](https://vitest.dev/)**: Fast test runner (Jest-compatible)
- **[Testing Library](https://testing-library.com/)**: React component testing
- **[Playwright](https://playwright.dev/)**: E2E browser testing
- **TypeScript**: Static type checking
- **ESLint**: Linting
- **Prettier**: Code formatting

### Running Tests

```bash
cd frontend

npm test              # Unit tests
npm run test:ui       # Tests with UI
npm run test:coverage # Tests with coverage
npm run test:e2e      # E2E tests
npm run test:e2e:ui   # With Playwright UI

npm run test:all      # typecheck + lint + test

# Single test
npm test src/__tests__/Component.test.tsx
```

## Test Coverage Goals

- **Unit Tests**: >80% coverage
- **Integration Tests**: All API endpoints
- **E2E Tests**: Critical user flows

## CI/CD Pipeline

GitHub Actions runs on every push/PR:

1. Backend: Lint, typecheck, security scan, tests with coverage
2. Frontend: Lint, typecheck, format check, tests with coverage
3. Frontend E2E: Playwright across browsers

## Best Practices

1. Write tests for new features
2. Keep tests simple and focused
3. Use descriptive test names (Arrange-Act-Assert pattern)
4. Mock external dependencies in unit tests
5. Test behavior, not implementation
6. See existing tests for patterns

## Before Committing

**Backend:**
```bash
make ci  # Runs everything
```

**Frontend:**
```bash
npm run test:all  # Runs everything
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Vitest documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [Playwright documentation](https://playwright.dev/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
