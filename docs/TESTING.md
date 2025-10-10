## Testing Guide

This document describes the testing infrastructure and best practices for the Knowledge Base project.

## Architecture: Functional Core, Imperative Shell

We follow the "Functional Core, Imperative Shell" pattern:

- **Functional Core**: Pure functions with no side effects (easy to test)
- **Imperative Shell**: I/O operations, API calls, database interactions (integration tests)

### Benefits:
- Fast unit tests for business logic
- Fewer, focused integration tests for I/O
- Better separation of concerns
- Easier to maintain and refactor

## Backend Testing (Python/FastAPI)

### Test Structure

```
backend/tests/
├── unit/           # Pure function tests, no I/O
├── integration/    # API endpoint tests with test client
└── e2e/            # Full system tests with real services
```

### Running Tests

```bash
cd backend

# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-e2e

# Run with coverage
make test-cov

# Run quality checks
make check          # lint + typecheck + security
make lint           # ruff linting
make typecheck      # mypy type checking
make security       # bandit security scan
make format         # auto-format code

# Full CI pipeline
make ci             # Run everything
```

### Tools

- **pytest**: Test framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **httpx**: FastAPI test client
- **ruff**: Fast linter and formatter (replaces flake8, isort, black)
- **mypy**: Static type checker
- **bandit**: Security vulnerability scanner
- **radon**: Code complexity analyzer

### Writing Tests

**Unit Test Example:**
```python
def test_pure_function() -> None:
    """Test a pure function with no side effects."""
    result = calculate_something(input_data)
    assert result == expected_output
```

**Integration Test Example:**
```python
def test_api_endpoint(client: TestClient) -> None:
    """Test API endpoint with test client."""
    response = client.post("/api/resources", json=data)
    assert response.status_code == 201
```

### Type Hints

All Python code should include type hints:
```python
def process_resource(resource: Resource) -> dict[str, Any]:
    """Process a resource and return result."""
    return {"id": resource.id, "status": "processed"}
```

## Frontend Testing (Next.js/React/TypeScript)

### Test Structure

```
frontend/
├── src/__tests__/       # Component unit tests
├── tests/
│   ├── integration/     # Integration tests
│   └── e2e/            # Playwright E2E tests
```

### Running Tests

```bash
cd frontend

# Run unit tests
npm test

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e
npm run test:e2e:ui     # With Playwright UI

# Run all checks
npm run test:all        # typecheck + lint + test

# Linting and formatting
npm run lint
npm run lint:fix
npm run format
npm run type-check
```

### Tools

- **Vitest**: Fast test runner (Vite-powered, Jest-compatible)
- **Testing Library**: React component testing
- **Playwright**: E2E browser testing
- **TypeScript**: Static type checking
- **ESLint**: Linting
- **Prettier**: Code formatting

### Writing Tests

**Component Unit Test:**
```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Component from "./Component";

describe("Component", () => {
  it("renders correctly", () => {
    render(<Component />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });
});
```

**E2E Test:**
```typescript
import { test, expect } from "@playwright/test";

test("user can create resource", async ({ page }) => {
  await page.goto("/");
  await page.click("text=Add Resource");
  await page.fill('input[name="title"]', "Test");
  await page.click("text=Create");
  await expect(page.getByText("Test")).toBeVisible();
});
```

## Test Coverage Goals

- **Unit Tests**: >80% coverage
- **Integration Tests**: All API endpoints
- **E2E Tests**: Critical user flows

## CI/CD Pipeline

GitHub Actions runs on every push and PR:

1. **Backend Quality**: Lint, typecheck, security scan
2. **Backend Tests**: Unit + integration tests with coverage
3. **Frontend Quality**: Lint, typecheck, format check
4. **Frontend Tests**: Unit tests with coverage
5. **Frontend E2E**: Playwright tests across browsers

## Best Practices

### General
1. Write tests first for new features (TDD when appropriate)
2. Keep tests simple and focused
3. Use descriptive test names
4. Arrange-Act-Assert pattern
5. Mock external dependencies in unit tests
6. Use fixtures for common test data

### Backend
1. Use type hints everywhere
2. Keep functions pure when possible
3. Test business logic separately from I/O
4. Use FastAPI's dependency injection for testability
5. Run `make check` before committing

### Frontend
1. Test behavior, not implementation
2. Use Testing Library queries correctly
3. Avoid testing library internals
4. Mock API calls in unit tests
5. Test accessibility (use semantic HTML)
6. Run `npm run test:all` before committing

## Performance

### Fast Feedback Loop

```bash
# Backend: ~0.1s per unit test
make test-unit

# Frontend: ~0.01s per unit test (Vitest is FAST)
npm test

# Run specific test file
npm test src/__tests__/Component.test.tsx
```

### Optimization Tips

1. Keep unit tests pure (no I/O) for speed
2. Use `describe.concurrent` in Vitest for parallel tests
3. Mock expensive operations
4. Use test fixtures to avoid repeated setup
5. Run E2E tests less frequently (they're slow)

## Debugging

### Backend
```bash
# Run single test with output
pytest tests/unit/test_main.py::test_function -v -s

# Debug with pdb
pytest tests/unit/test_main.py::test_function --pdb
```

### Frontend
```bash
# Run tests in watch mode
npm test

# Run with UI for debugging
npm run test:ui

# Debug E2E in headed mode
npm run test:e2e -- --headed --debug
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Vitest documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [Playwright documentation](https://playwright.dev/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
