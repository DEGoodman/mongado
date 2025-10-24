"""Shared utility functions for the Mongado backend.

This module provides common utilities used across multiple modules,
following DRY principles and providing a single source of truth.
"""

import hashlib


def calculate_content_hash(content: str) -> str:
    """Calculate SHA256 hash of content.

    This is used for:
    - Detecting content changes in articles/notes (embedding_sync.py)
    - Cache keys for Ollama embeddings (ollama_client.py)

    Args:
        content: Text content to hash

    Returns:
        Hex digest of SHA256 hash

    Example:
        >>> calculate_content_hash("Hello, world!")
        '315f5bdb76d078c43b8ac0064e4a0164612b1fce77c869345bfc94c75894edd3'
    """
    return hashlib.sha256(content.encode()).hexdigest()
