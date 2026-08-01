"""Rate limiting configuration for API endpoints.

Uses slowapi for rate limiting with Redis backend (if available) or in-memory fallback.
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create rate limiter using remote IP as key. Disabled under TESTING so a test
# file's many calls to one endpoint do not trip the limit (every request in a
# TestClient shares the key "testclient"); routers/notes.py already did this
# for its own limiter.
limiter = Limiter(key_func=get_remote_address, enabled=os.getenv("TESTING") != "1")

# Rate limit presets for different endpoint types
RATE_LIMITS = {
    # AI endpoints (expensive operations)
    "ai_ask": "20/minute",  # Q&A with LLM
    "ai_suggest": "30/minute",  # Link/tag suggestions
    "ai_warmup": "5/minute",  # Model warmup
    "ai_stream": "20/minute",  # Streaming suggestions
    # Search endpoints
    "search": "60/minute",  # Semantic search
    # Upload endpoints
    "upload": "10/minute",  # File uploads
    # Note mutations
    "note_create": "10/minute",  # Note creation
    "note_update": "30/minute",  # Note updates
    # Admin endpoints (more restrictive)
    "admin": "30/minute",
}
