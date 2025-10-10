# Multi-stage build for Python backend
FROM python:3.13-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Development stage
FROM base as development

# Install ALL dependencies (dev tools included)
COPY requirements-dev.txt requirements-base.txt ./
RUN pip install -r requirements-dev.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run with hot reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Install ONLY production dependencies
COPY requirements-prod.txt requirements-base.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt && \
    pip list  # Show installed packages for debugging

# Copy only necessary application code (no tests, scripts, etc.)
COPY --chown=appuser:appuser main.py config.py __init__.py ./

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/')"

# Run with production settings (uvloop, httptools from uvicorn[standard])
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools"]
