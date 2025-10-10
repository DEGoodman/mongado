# Logging Best Practices

## Overview

This project follows consistent logging practices across both backend and frontend to ensure proper observability and debugging capabilities.

## Backend (Python)

### Configuration

Logging is configured in `backend/logging_config.py` and provides:
- Console output with formatted timestamps
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Reduced noise from third-party libraries

### Usage

```python
import logging

# Get a logger for your module
logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Detailed debugging information")
logger.info("General informational messages")
logger.warning("Warning messages for recoverable issues")
logger.error("Error messages for failures")
logger.critical("Critical errors that may cause system failure")
```

### Log Levels

| Level    | When to Use | Example |
|----------|-------------|---------|
| DEBUG    | Detailed diagnostic info, only in development | Variable values, function entry/exit |
| INFO     | Confirmation that things are working | "Server started", "Configuration loaded" |
| WARNING  | Something unexpected but recoverable | "Config missing, using default", "Deprecated API used" |
| ERROR    | Serious problem, feature failed | "Failed to connect to database", "API request failed" |
| CRITICAL | Very serious error, app may crash | "Out of memory", "Critical dependency unavailable" |

### Best Practices

**DO:**
```python
# ✅ Use logger instead of print
logger.info("Processing request for user %s", user_id)

# ✅ Use string formatting with % style (lazy evaluation)
logger.debug("Processing %d items", len(items))

# ✅ Include context
logger.error("Failed to retrieve secret '%s': %s", reference, error)

# ✅ Log exceptions properly
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed: %s", e, exc_info=True)  # Includes stack trace
```

**DON'T:**
```python
# ❌ Don't use print for logging
print("Processing request")

# ❌ Don't use f-strings (evaluated even if not logged)
logger.debug(f"Processing {expensive_operation()}")  # Bad!

# ❌ Don't log sensitive data
logger.info("User password: %s", password)  # Never!

# ❌ Don't use generic messages
logger.error("Error occurred")  # Too vague
```

### Configuration

Set log level via environment variable or in code:

```python
from logging_config import setup_logging

# In development
setup_logging(level="DEBUG")

# In production
setup_logging(level="INFO")
```

### Example

```python
import logging
from config import get_secret_manager

logger = logging.getLogger(__name__)

def initialize_service():
    logger.info("Initializing service...")
    secret_manager = get_secret_manager()

    if not secret_manager.is_available():
        logger.warning("1Password not configured, using defaults")
    else:
        logger.info("1Password integration enabled")

    logger.info("Service initialized successfully")
```

## Frontend (TypeScript/React)

### Configuration

Logging utility is in `frontend/src/lib/logger.ts` and provides:
- Development vs production awareness
- Contextual logging
- Ready for integration with error tracking services (Sentry, LogRocket)

### Usage

```typescript
import { logger } from "@/lib/logger";

// Basic logging
logger.debug("Component rendered");
logger.info("User action completed");
logger.warn("Deprecated feature used");
logger.error("API request failed", error);

// Contextual logging
const apiLogger = logger.withContext("API");
apiLogger.info("Fetching resources...");
apiLogger.error("Request failed", error);
```

### Log Levels

| Level    | When to Use | Output |
|----------|-------------|--------|
| debug    | Development-only diagnostics | Only in NODE_ENV=development |
| info     | Informational messages | Always output |
| warn     | Warnings and deprecations | Always output |
| error    | Errors and exceptions | Always output + can send to error tracking |

### Best Practices

**DO:**
```typescript
// ✅ Use logger for errors
try {
  await fetchData();
} catch (error) {
  logger.error("Failed to fetch data", error);
}

// ✅ Include context
logger.info("Resource created successfully", { id: resource.id });

// ✅ Use debug for development info
logger.debug("Component mounted", { props });

// ✅ Use contextual loggers for modules
const authLogger = logger.withContext("Auth");
authLogger.info("User logged in", { userId });
```

**DON'T:**
```typescript
// ❌ Don't use console.log directly
console.log("User clicked button");  // Use logger.debug() instead

// ❌ Don't log sensitive data
logger.info("User password:", password);  // Never!

// ❌ Don't log too much in production
logger.info("Mouse moved", { x, y });  // Use debug for this

// ❌ Don't swallow errors silently
catch (error) {
  // Nothing here - always log!
}
```

### Example

```typescript
import { logger } from "@/lib/logger";

const apiLogger = logger.withContext("ResourceAPI");

async function fetchResources() {
  try {
    apiLogger.debug("Fetching resources from API");
    const response = await fetch(`${API_URL}/api/resources`);
    const data = await response.json();
    apiLogger.info("Resources fetched successfully", { count: data.resources.length });
    return data.resources;
  } catch (error) {
    apiLogger.error("Failed to fetch resources", error);
    throw error;
  }
}
```

## Production Considerations

### Backend

For production deployments:

1. **Set appropriate log level**:
   - Use `INFO` for production
   - Use `DEBUG` only when debugging specific issues

2. **Log aggregation**:
   - Logs go to stdout/stderr (Docker/Kubernetes friendly)
   - Use log aggregation tools (CloudWatch, DataDog, etc.)

3. **Structured logging** (future enhancement):
   ```python
   # Can add JSON logging for better parsing
   import json_logging
   json_logging.init_fastapi(enable_json=True)
   ```

### Frontend

For production deployments:

1. **Error tracking**:
   - Integrate with Sentry or similar service
   - Uncomment Sentry integration in `logger.ts`

2. **Minimize console output**:
   - `debug()` automatically disabled in production
   - Consider stripping all logs in production builds

3. **User privacy**:
   - Never log PII (Personally Identifiable Information)
   - Sanitize error messages before logging

## Testing with Logs

### Backend Tests

```python
import logging

def test_with_logging(caplog):
    """Test that captures log output."""
    with caplog.at_level(logging.INFO):
        my_function()
        assert "Expected log message" in caplog.text
```

### Frontend Tests

```typescript
// Mock logger in tests
jest.mock("@/lib/logger", () => ({
  logger: {
    error: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
  },
}));

it("logs errors when fetch fails", async () => {
  // Test that error logging happens
  expect(logger.error).toHaveBeenCalledWith(
    expect.stringContaining("Failed"),
    expect.any(Error)
  );
});
```

## Log Level Environment Variables

### Backend

```bash
# .env or environment
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Frontend

Automatically determined by `NODE_ENV`:
- `development`: All levels including debug
- `production`: Info, warn, error only

## Common Patterns

### API Request Logging

**Backend:**
```python
logger.info("Received %s request to %s", request.method, request.url.path)
```

**Frontend:**
```typescript
apiLogger.debug("Sending request", { method, url });
```

### Error Logging

**Backend:**
```python
try:
    operation()
except ValueError as e:
    logger.error("Invalid value provided: %s", e)
    raise
except Exception as e:
    logger.critical("Unexpected error: %s", e, exc_info=True)
    raise
```

**Frontend:**
```typescript
try {
  await operation();
} catch (error) {
  logger.error("Operation failed", error);
  // Show user-friendly error message
  throw error;
}
```

### Startup/Initialization Logging

**Backend:**
```python
logger.info("Starting %s v%s", app_name, version)
logger.info("Environment: %s", environment)
logger.info("Configuration loaded successfully")
```

**Frontend:**
```typescript
logger.info("App initialized", {
  version: process.env.NEXT_PUBLIC_VERSION,
  environment: process.env.NODE_ENV
});
```

## Resources

- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [Python Logging Cookbook](https://docs.python.org/3/howto/logging-cookbook.html)
- [12-Factor App: Logs](https://12factor.net/logs)
- [Sentry Documentation](https://docs.sentry.io/)
