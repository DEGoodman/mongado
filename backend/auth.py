"""Authentication middleware for Zettelkasten notes system.

Three credentials share the `Authorization: Bearer` transport:

- **Passkey session tokens** (#229) - signed, 12-hour, minted by
  /api/auth/login/verify. The primary path for humans, full admin, and the
  only one the frontend issues.
- **Scoped API tokens** (#300) - `mgd_`-prefixed random secrets, stored as
  hashes in Neo4j, each carrying a set of scopes for programmatic use. Created
  and revoked from the admin panel; the safe way to script against prod.
- **The static admin token** - scoped to first-time passkey enrollment (#267),
  plus (in local dev only, #291) a full-admin session when ALLOW_TOKEN_AUTH is
  set. Long-lived and unrevokable, hence the #225 lockout below.

Endpoints declare a required scope via `require_scope(...)`. A passkey session
satisfies every scope (full admin); an API token satisfies a scope it was
granted (with `admin:*` a wildcard); the static token satisfies scopes only on
the dev bootstrap path. Session tokens are checked first and are exempt from the
lockout: they are unguessable by construction, so failed attempts carry no
signal about them.
"""

import hmac
import logging
import threading
import time
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from adapters.neo4j import get_neo4j_adapter
from config import get_settings
from core.api_tokens import (
    ADMIN_WILDCARD,
    hash_token,
    is_expired,
    looks_like_api_token,
    scopes_satisfy,
)
from core.sessions import derive_session_secret, looks_like_session_token, verify_session_token

logger = logging.getLogger(__name__)
settings = get_settings()

# A resolved caller: always has 'kind' ('passkey' | 'api_token' | 'token'),
# and for API tokens also 'scopes' (set[str]) and 'token_id'.
Principal = dict[str, Any]

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


def _check_api_token(token: str) -> tuple[str, Principal | None]:
    """Try to authenticate a bearer token as a scoped API token (#300).

    Args:
        token: The bearer token from the Authorization header

    Returns:
        (status, principal) where status is:
        - "valid": principal is the resolved caller (scopes recorded, use stamped)
        - "expired": the token was ours but has expired (do not count as a
          brute-force attempt - it is a genuine, if stale, secret)
        - "miss": no such token (a wrong secret - the caller counts it toward
          the #225 lockout, exactly like a wrong static token)
    """
    adapter = get_neo4j_adapter()
    record = adapter.get_api_token_by_hash(hash_token(token))
    if record is None:
        return "miss", None

    if is_expired(record["expires_at"], time.time()):
        return "expired", None

    adapter.record_api_token_use(record["token_id"], time.time())
    return "valid", {
        "authenticated": True,
        "kind": "api_token",
        "token_id": record["token_id"],
        "scopes": set(record["scopes"]),
        "name": record["name"],
        "expires_at": record["expires_at"],
    }


def _authenticate(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> dict[str, Any]:
    """Resolve the caller's credential to a principal, or raise.

    Establishes *who* is calling (passkey session, API token, or static token);
    callers decide whether that principal is *allowed* via _authorize /
    require_scope. Returns a dict with 'kind' ('passkey', 'api_token', or
    'token') and, for API tokens, 'scopes'.

    The #225 lockout lives here because this is where guessable secrets (the
    static token and API tokens) are checked: repeated wrong secrets from one IP
    trigger 429 for LOCKOUT_SECONDS. A passkey session or a genuine-but-expired
    API token is reported as 401 and does not count toward that budget - counting
    it would let a stale credential lock the admin out of getting back in.

    Args:
        request: Incoming request (for the client IP)
        credentials: HTTPAuthorizationCredentials from HTTPBearer (None if missing)

    Returns:
        Principal dict with 'kind' (and 'scopes' for API tokens)

    Raises:
        HTTPException: 401 if no auth header or an expired credential, 403 if an
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

    # Scoped API token (#300): a mgd_-shaped secret looked up by hash in Neo4j
    if looks_like_api_token(token):
        status, principal = _check_api_token(token)
        if status == "valid" and principal is not None:
            auth_tracker.record_success(ip)
            logger.debug("Authenticated via API token %s", principal["token_id"])
            return principal
        if status == "expired":
            logger.info("Rejected expired API token from %s", ip)
            raise HTTPException(
                status_code=401,
                detail="API token expired. Create a new one from the admin panel.",
            )
        # "miss": a wrong secret - count it, exactly like a wrong static token
        failures = auth_tracker.record_failure(ip)
        logger.warning("Invalid API token attempt from %s (failure %d)", ip, failures)
        if failures >= MAX_FAILED_ATTEMPTS:
            logger.warning(
                "IP %s locked out for %ds after %d failed attempts",
                ip,
                LOCKOUT_SECONDS,
                failures,
            )
        raise HTTPException(status_code=403, detail="Invalid API token.")

    # Fall back to the static token (passkey enrollment, dev bootstrap)
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


def _authorize(principal: Principal, required_scopes: tuple[str, ...]) -> None:
    """Enforce that a resolved principal may exercise the required scopes.

    Authorization policy, kept separate from _authenticate (which only
    establishes identity):
    - passkey session -> full admin, satisfies everything.
    - API token -> must have been granted every required scope (admin:* is a
      wildcard, see core.api_tokens.scopes_satisfy).
    - static token -> only the local-dev bootstrap (#291) treats it as full
      admin, gated on is_development AND allow_token_auth so it can never
      activate in production. Otherwise it is enrollment-only and rejected here.

    Args:
        principal: The resolved caller from _authenticate
        required_scopes: Scopes the endpoint demands (all must be satisfied)

    Raises:
        HTTPException: 403 if the principal lacks a required scope
    """
    kind = principal["kind"]

    if kind == "passkey":
        return

    if kind == "api_token":
        granted: set[str] = principal["scopes"]
        for required in required_scopes:
            if not scopes_satisfy(granted, required):
                logger.info(
                    "API token %s lacks scope %s (has %s)",
                    principal.get("token_id"),
                    required,
                    sorted(granted),
                )
                raise HTTPException(
                    status_code=403,
                    detail=f"This token lacks the required scope: {required}.",
                )
        return

    # kind == "token": the static admin token
    if settings.is_development and settings.allow_token_auth:
        logger.warning("Static admin token accepted as full admin (dev ALLOW_TOKEN_AUTH, #291)")
        return

    raise HTTPException(
        status_code=403,
        detail="This operation requires a passkey session or a scoped API token.",
    )


def require_scope(
    *required_scopes: str,
) -> Callable[[Request, HTTPAuthorizationCredentials | None], Principal]:
    """Build a dependency that authenticates and enforces the given scopes.

    Use on any admin-gated endpoint in place of AdminUser to allow scoped API
    tokens (#300) alongside passkey sessions. The returned dependency yields the
    resolved principal, so a handler can inspect the caller if it needs to.

    Example:
        @router.post("/notes")
        async def create(_admin: Annotated[Principal, Depends(require_scope("notes:write"))]):
            ...

    Args:
        *required_scopes: One or more scopes the caller must satisfy

    Returns:
        A FastAPI dependency callable
    """

    def dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> Principal:
        principal = _authenticate(request, credentials)
        _authorize(principal, required_scopes)
        return principal

    return dependency


def verify_admin(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> bool:
    """Full admin access: a passkey session, an `admin:*` API token, or (in
    local dev) the static token.

    The static token is otherwise scoped to passkey enrollment (#267). This is
    the dependency behind AdminUser, used by the most sensitive operations
    (backups, auth and token management) that map to no narrower scope.

    Args:
        request: Incoming request (for the client IP)
        credentials: HTTPAuthorizationCredentials from HTTPBearer (None if missing)

    Returns:
        True if authorized for full admin

    Raises:
        HTTPException: 401 if no auth header or an expired credential, 403 if the
            credential is insufficient, 429 if the client IP is locked out
    """
    principal = _authenticate(request, credentials)
    _authorize(principal, (ADMIN_WILDCARD,))
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
        Dict with 'authenticated', 'kind' ('passkey'/'api_token'/'token'/'none'),
        and for passkey sessions 'credential_id' and 'expires_at'
    """
    unauthenticated: dict[str, Any] = {"authenticated": False, "kind": "none", "expires_at": None}

    if not credentials:
        return unauthenticated

    token = credentials.credentials

    session = _check_session_token(token)
    if session:
        return session

    if looks_like_api_token(token):
        status, principal = _check_api_token(token)
        if status == "valid" and principal is not None:
            return principal
        return unauthenticated

    if settings.admin_token and hmac.compare_digest(token, settings.admin_token):
        return {"authenticated": True, "kind": "token", "expires_at": None}

    return unauthenticated


# Type aliases for dependency injection.
# AdminUser gates full admin (passkey, an admin:* API token, or the dev static
# token). For narrower access, use require_scope("...") directly. EnrollmentUser
# gates passkey enrollment, which the static token may still authorize (#267).
AdminUser = Annotated[bool, Depends(verify_admin)]
EnrollmentUser = Annotated[bool, Depends(verify_enrollment)]
