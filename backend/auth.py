"""Authentication middleware for Zettelkasten notes system.

Two credentials share the `Authorization: Bearer` transport (#229):

- **Passkey session tokens** - signed, 12-hour, minted by /api/auth/login/verify.
  The primary path for humans, and the only one the frontend issues.
- **The static admin token** - retained for machine callers (the deploy
  workflow's pre/post-deploy backups) and to gate first-time passkey
  enrollment. Long-lived and unrevokable, hence the #225 lockout below.

Session tokens are checked first and are exempt from the lockout: they are
unguessable by construction, so failed attempts carry no signal about them.
"""

import hmac
import logging
import threading
import time
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import get_settings
from core.sessions import derive_session_secret, looks_like_session_token, verify_session_token

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


def _check_session_token(token: str) -> dict[str, Any] | None:
    """Try to authenticate a bearer token as a passkey session.

    Args:
        token: The bearer token from the Authorization header

    Returns:
        Auth context if the token is a valid session, else None. None also
        covers session-*shaped* tokens that failed verification - the caller
        distinguishes those with looks_like_session_token.
    """
    secret = derive_session_secret(settings.admin_token, settings.session_secret)
    if not secret:
        return None

    claims = verify_session_token(token, secret, time.time())
    if claims is None:
        return None

    return {
        "authenticated": True,
        "kind": "passkey",
        "credential_id": claims.credential_id,
        "expires_at": claims.expires_at,
    }


def _authenticate(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> dict[str, Any]:
    """Authenticate an admin request, returning the principal or raising.

    Shared by verify_admin (passkey sessions only) and verify_enrollment
    (sessions or the static token). Returns a dict with 'kind' ('passkey' or
    'token'); each caller decides whether that kind is allowed for its endpoint.

    The #225 lockout lives here because this is where the static token is
    checked: repeated invalid tokens from one IP trigger 429 for LOCKOUT_SECONDS,
    even for a request that would otherwise carry the correct token. A passkey
    session is HMAC-signed and unguessable, so an expired or malformed session is
    reported as 401 and does not count toward that budget - counting it would let
    a stale browser tab lock the admin out of signing back in.

    Args:
        request: Incoming request (for the client IP)
        credentials: HTTPAuthorizationCredentials from HTTPBearer (None if missing)

    Returns:
        Principal dict with 'kind' ('passkey' or 'token')

    Raises:
        HTTPException: 401 if no auth header or an expired session, 403 if
            invalid token, 429 if the client IP is locked out
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

    # Passkey session first - the primary path for humans
    if _check_session_token(token):
        auth_tracker.record_success(ip)
        logger.debug("Admin authenticated via passkey session")
        return {"kind": "passkey"}

    if looks_like_session_token(token):
        logger.info("Rejected expired or invalid passkey session from %s", ip)
        raise HTTPException(
            status_code=401,
            detail="Session expired. Sign in again with your passkey.",
        )

    # Fall back to the static token (CI/automation, passkey enrollment)
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
    logger.debug("Admin authenticated via static token")
    return {"kind": "token"}


def verify_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> bool:
    """Full admin access: a passkey session is required (#267).

    The static token no longer grants general admin access - it is scoped to
    passkey enrollment (see verify_enrollment). A correct static token still
    authenticates, but is rejected here with 403 directing the caller to sign in
    with a passkey. This is the dependency behind AdminUser, used by every admin
    operation except enrollment.

    Args:
        request: Incoming request (for the client IP)
        credentials: HTTPAuthorizationCredentials from HTTPBearer (None if missing)

    Returns:
        True if authenticated with a passkey session

    Raises:
        HTTPException: 401 if no auth header or an expired session, 403 if the
            credential is an invalid or enrollment-only static token, 429 if the
            client IP is locked out
    """
    principal = _authenticate(request, credentials)
    if principal["kind"] != "passkey":
        raise HTTPException(
            status_code=403,
            detail="This operation requires a passkey session. Sign in with your passkey.",
        )
    return True


def verify_enrollment(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> bool:
    """Passkey-enrollment access: a passkey session OR the static token (#267).

    Enrollment is the one operation the static token still authorizes, so the
    first passkey can be created before any session exists - and as a break-glass
    path if every passkey is lost. Once a passkey session is available, it works
    here too.

    Returns:
        True if authenticated with either credential

    Raises:
        HTTPException: same as _authenticate (401 / 403 / 429)
    """
    _authenticate(request, credentials)
    return True


def verify_admin_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """Report auth state without rejecting unauthenticated callers.

    Backs GET /api/auth/session, which answers "am I signed in?" - a question
    whose negative answer is a 200, not a 401. Does not touch the lockout
    tracker in either direction: this endpoint is a status read, so it must
    neither consume attempts nor clear a running lockout.

    Args:
        credentials: HTTPAuthorizationCredentials from HTTPBearer (None if missing)

    Returns:
        Dict with 'authenticated', 'kind' ('passkey'/'token'/'none'), and for
        passkey sessions 'credential_id' and 'expires_at'
    """
    unauthenticated: dict[str, Any] = {"authenticated": False, "kind": "none", "expires_at": None}

    if not credentials:
        return unauthenticated

    token = credentials.credentials

    session = _check_session_token(token)
    if session:
        return session

    if settings.admin_token and hmac.compare_digest(token, settings.admin_token):
        return {"authenticated": True, "kind": "token", "expires_at": None}

    return unauthenticated


# Type aliases for dependency injection.
# AdminUser gates full admin access (passkey session only). EnrollmentUser gates
# passkey enrollment, which the static token may still authorize (#267).
AdminUser = Annotated[bool, Depends(verify_admin)]
EnrollmentUser = Annotated[bool, Depends(verify_enrollment)]
