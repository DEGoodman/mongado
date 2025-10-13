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

# Install 1Password CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg && \
    curl -sS https://downloads.1password.com/linux/keys/1password.asc | \
    gpg --dearmor --output /usr/share/keyrings/1password-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/$(dpkg --print-architecture) stable main" | \
    tee /etc/apt/sources.list.d/1password.list && \
    apt-get update && \
    apt-get install -y 1password-cli && \
    rm -rf /var/lib/apt/lists/*

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

# Install curl for healthchecks and 1Password CLI
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg && \
    curl -sS https://downloads.1password.com/linux/keys/1password.asc | \
    gpg --dearmor --output /usr/share/keyrings/1password-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/$(dpkg --print-architecture) stable main" | \
    tee /etc/apt/sources.list.d/1password.list && \
    apt-get update && \
    apt-get install -y 1password-cli && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Install ONLY production dependencies
COPY requirements-prod.txt requirements-base.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt && \
    pip list  # Show installed packages for debugging

# Copy application code (exclude tests and dev files)
COPY --chown=appuser:appuser *.py ./
COPY --chown=appuser:appuser *.sql ./
COPY --chown=appuser:appuser static ./static

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check using curl (installed above)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run with production settings (uvloop, httptools from uvicorn[standard])
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools"]
