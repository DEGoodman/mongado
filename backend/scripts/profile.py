#!/usr/bin/env python3
"""Profiling utilities for development."""

import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from logging_config import setup_logging

setup_logging(level="INFO")
logger = logging.getLogger(__name__)


def profile_with_pyspy() -> None:
    """Profile with py-spy (sampling profiler, low overhead)."""
    logger.info("Starting py-spy profiler...")
    logger.info("Run: py-spy top --pid <PID>")
    logger.info("Or: py-spy record -o profile.svg -- python main.py")


def profile_with_viztracer() -> None:
    """Profile with VizTracer (tracing profiler with GUI)."""
    logger.info("Starting VizTracer profiler...")
    import viztracer  # type: ignore[import-untyped]

    tracer = viztracer.VizTracer()
    tracer.start()

    # Import and run app
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)

    # Make some test requests
    logger.info("Making test requests...")
    client.get("/")
    client.get("/api/resources")
    client.post("/api/resources", json={"title": "Test", "content": "Test", "tags": []})

    tracer.stop()
    tracer.save("profiling_result.json")
    logger.info("Profiling complete! Run: vizviewer profiling_result.json")


def profile_with_line_profiler() -> None:
    """Profile specific functions with line_profiler."""
    logger.info("Line profiler - Use @profile decorator on functions")
    logger.info("Run: kernprof -l -v script.py")


def memory_profile() -> None:
    """Profile memory usage."""
    logger.info("Memory profiling with memray...")
    logger.info("Run: memray run main.py")
    logger.info("Then: memray flamegraph output.bin")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Profile the application")
    parser.add_argument(
        "profiler",
        choices=["pyspy", "viztracer", "line", "memory"],
        help="Profiler to use",
    )
    args = parser.parse_args()

    if args.profiler == "pyspy":
        profile_with_pyspy()
    elif args.profiler == "viztracer":
        profile_with_viztracer()
    elif args.profiler == "line":
        profile_with_line_profiler()
    elif args.profiler == "memory":
        memory_profile()
