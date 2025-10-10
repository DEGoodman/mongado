#!/usr/bin/env python3
"""Benchmark API endpoints for performance testing."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from logging_config import setup_logging
from main import app

setup_logging(level="INFO")
logger = logging.getLogger(__name__)


def benchmark_endpoints() -> None:
    """Benchmark common endpoints."""
    import time

    client = TestClient(app)

    # Warmup
    for _ in range(10):
        client.get("/")

    # Benchmark root endpoint
    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        client.get("/")
    elapsed = time.perf_counter() - start
    logger.info("Root endpoint: %d requests in %.3fs", iterations, elapsed)
    logger.info("  Average: %.2fms per request", (elapsed / iterations) * 1000)
    logger.info("  RPS: %.0f", iterations / elapsed)

    # Benchmark resource creation
    iterations = 100
    start = time.perf_counter()
    for i in range(iterations):
        client.post(
            "/api/resources",
            json={"title": f"Test {i}", "content": "Benchmark", "tags": []},
        )
    elapsed = time.perf_counter() - start
    logger.info("")
    logger.info("Create resource: %d requests in %.3fs", iterations, elapsed)
    logger.info("  Average: %.2fms per request", (elapsed / iterations) * 1000)
    logger.info("  RPS: %.0f", iterations / elapsed)


if __name__ == "__main__":
    logger.info("Running API benchmarks...")
    logger.info("")
    benchmark_endpoints()
