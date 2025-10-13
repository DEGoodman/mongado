"""Authentication middleware for Zettelkasten notes system."""

import logging
from typing import Annotated

from fastapi import Header, HTTPException

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def verify_admin(authorization: Annotated[str | None, Header()] = None) -> bool:
    """Verify admin token from Authorization header.

    Expects: "Bearer your-secret-token"

    This is a simple bearer token auth for a single admin user.
    The token is stored in the environment (.env or 1Password).

    Args:
        authorization: Authorization header value

    Returns:
        True if authenticated

    Raises:
        HTTPException: 401 if no auth header, 403 if invalid token
    """
    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(
            status_code=401,
            detail="Authorization required. Include 'Authorization: Bearer <token>' header.",
        )

    if not authorization.startswith("Bearer "):
        logger.warning("Invalid Authorization format: %s", authorization[:20])
        raise HTTPException(
            status_code=401, detail="Invalid authorization format. Use 'Bearer <token>'."
        )

    token = authorization.replace("Bearer ", "").strip()

    # Get expected token from settings
    expected_token = settings.admin_token

    if not expected_token:
        logger.error("ADMIN_TOKEN not configured in environment")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: admin token not set.",
        )

    if token != expected_token:
        logger.warning("Invalid token attempt")
        raise HTTPException(status_code=403, detail="Invalid token.")

    logger.debug("Admin authenticated successfully")
    return True


def get_session_id(x_session_id: Annotated[str | None, Header()] = None) -> str | None:
    """Extract session ID from custom header.

    This is used to track ephemeral notes for anonymous visitors.
    The frontend should generate and persist a session ID in localStorage
    and send it with each request.

    Args:
        x_session_id: Custom X-Session-ID header

    Returns:
        Session ID string or None if not provided
    """
    if x_session_id:
        logger.debug("Session ID: %s", x_session_id[:8] + "...")
    return x_session_id


# Type aliases for dependency injection
AdminUser = Annotated[bool, verify_admin]
SessionID = Annotated[str | None, get_session_id]
