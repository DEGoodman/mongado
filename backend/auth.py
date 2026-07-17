"""Authentication middleware for Zettelkasten notes system."""

import hmac
import logging
import threading
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# HTTPBearer security scheme - enables "Authorize" button in Swagger UI
# auto_error=False so we can return custom 401 message for missing auth
security = HTTPBearer(auto_error=False)

# Lockout policy for failed token attempts (#225). The admin token is a single
# static secret, so unlimited guessing must not be possible. Only *invalid*
# tokens count - missing headers and server misconfiguration do not.
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 15 * 60


class FailedAuthTracker:
    """Per-IP failed-authentication tracker with lockout.

    In-memory and per-process: each uvicorn worker tracks independently,
    which multiplies the effective attempt budget by the worker count.
    That is acceptable - the goal is stopping network-speed brute force,
    not producing an exact global counter.
    """

    def __init__(
        self,
        max_attempts: int = MAX_FAILED_ATTEMPTS,
        lockout_seconds: float = LOCKOUT_SECONDS,
    ) -> None:
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        # ip -> (failure_count, last_failure_timestamp)
        self._failures: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def is_locked(self, ip: str) -> bool:
        """Whether this IP is currently locked out."""
        now = time.monotonic()
        with self._lock:
            entry = self._failures.get(ip)
            if entry is None:
                return False
            count, last_failure = entry
            if now - last_failure >= self.lockout_seconds:
                # Window expired - forget the history entirely
                del self._failures[ip]
                return False
            return count >= self.max_attempts

    def record_failure(self, ip: str) -> int:
        """Record a failed attempt for this IP. Returns the current count."""
        now = time.monotonic()
        with self._lock:
            count, last_failure = self._failures.get(ip, (0, now))
            if now - last_failure >= self.lockout_seconds:
                count = 0
            count += 1
            self._failures[ip] = (count, now)
            # Opportunistic prune so the dict cannot grow unboundedly
            if len(self._failures) > 1000:
                self._failures = {
                    k: v for k, v in self._failures.items() if now - v[1] < self.lockout_seconds
                }
            return count

    def record_success(self, ip: str) -> None:
        """Clear failure history for this IP after successful auth."""
        with self._lock:
            self._failures.pop(ip, None)

    def reset(self) -> None:
        """Clear all state (used by tests)."""
        with self._lock:
            self._failures.clear()


auth_tracker = FailedAuthTracker()


def _client_ip(request: Request) -> str:
    """Best-effort client IP (real visitor IP behind nginx, see #226)."""
    return request.client.host if request.client else "unknown"


def verify_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> bool:
    """Verify admin token from Authorization header.

    Uses FastAPI's HTTPBearer security scheme for proper Swagger UI integration.
    The token is stored in the environment (.env or 1Password).

    Repeated invalid tokens from one IP trigger a lockout (#225): after
    MAX_FAILED_ATTEMPTS failures, that IP gets 429 for LOCKOUT_SECONDS -
    even for requests that would otherwise carry the correct token.

    Args:
        request: Incoming request (for the client IP)
        credentials: HTTPAuthorizationCredentials from HTTPBearer (None if missing)

    Returns:
        True if authenticated

    Raises:
        HTTPException: 401 if no auth header, 403 if invalid token,
            429 if the client IP is locked out
    """
    ip = _client_ip(request)

    if auth_tracker.is_locked(ip):
        logger.warning("Rejected auth attempt from locked-out IP %s", ip)
        raise HTTPException(
            status_code=429,
            detail="Too many failed authentication attempts. Try again later.",
            headers={"Retry-After": str(LOCKOUT_SECONDS)},
        )

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
        failures = auth_tracker.record_failure(ip)
        logger.warning("Invalid token attempt from %s (failure %d)", ip, failures)
        if failures >= MAX_FAILED_ATTEMPTS:
            logger.warning(
                "IP %s locked out for %ds after %d failed attempts",
                ip,
                LOCKOUT_SECONDS,
                failures,
            )
        raise HTTPException(status_code=403, detail="Invalid token.")

    auth_tracker.record_success(ip)
    logger.debug("Admin authenticated successfully")
    return True


# Type alias for dependency injection
AdminUser = Annotated[bool, Depends(verify_admin)]
