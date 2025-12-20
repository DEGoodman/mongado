"""Authentication middleware for Zettelkasten notes system."""

import hmac
import logging
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# HTTPBearer security scheme - enables "Authorize" button in Swagger UI
# auto_error=False so we can return custom 401 message for missing auth
security = HTTPBearer(auto_error=False)


def verify_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> bool:
    """Verify admin token from Authorization header.

    Uses FastAPI's HTTPBearer security scheme for proper Swagger UI integration.
    The token is stored in the environment (.env or 1Password).

    Args:
        credentials: HTTPAuthorizationCredentials from HTTPBearer (None if missing)

    Returns:
        True if authenticated

    Raises:
        HTTPException: 401 if no auth header, 403 if invalid token
    """
    if not credentials:
        logger.warning("Missing Authorization header")
        raise HTTPException(
            status_code=401,
            detail="Authorization required. Include 'Authorization: Bearer <token>' header.",
        )

    token = credentials.credentials

    # Get expected token from settings
    expected_token = settings.admin_token

    if not expected_token:
        logger.error("ADMIN_TOKEN not configured in environment")
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: admin token not set.",
        )

    if not hmac.compare_digest(token, expected_token):
        logger.warning("Invalid token attempt")
        raise HTTPException(status_code=403, detail="Invalid token.")

    logger.debug("Admin authenticated successfully")
    return True


# Type alias for dependency injection
AdminUser = Annotated[bool, Depends(verify_admin)]
