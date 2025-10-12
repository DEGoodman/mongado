"""Authentication middleware for Zettelkasten notes system."""

import logging
from typing import Annotated

from fastapi import Header, HTTPException

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def verify_admin(authorization: Annotated[str | None, Header()] = None) -> bool:
    """Verify admin passkey from Authorization header.

    Expects: "Bearer your-secret-passkey"

    This is a simple passkey-based auth for a single admin user.
    The passkey is stored in the environment (.env or 1Password).

    Args:
        authorization: Authorization header value

    Returns:
        True if authenticated

    Raises:
        HTTPException: 401 if no auth header, 403 if invalid passkey
    """
    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(
            status_code=401,
            detail="Authorization required. Include 'Authorization: Bearer <passkey>' header.",
        )

    if not authorization.startswith("Bearer "):
        logger.warning("Invalid Authorization format: %s", authorization[:20])
        raise HTTPException(
            status_code=401, detail="Invalid authorization format. Use 'Bearer <passkey>'."
        )

    passkey = authorization.replace("Bearer ", "").strip()

    # Get expected passkey from settings
    expected_passkey = settings.admin_passkey

    if not expected_passkey:
        logger.error("ADMIN_PASSKEY not configured in environment")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: admin passkey not set.",
        )

    if passkey != expected_passkey:
        logger.warning("Invalid passkey attempt")
        raise HTTPException(status_code=403, detail="Invalid passkey.")

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
