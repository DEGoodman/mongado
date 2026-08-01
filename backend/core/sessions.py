"""Pure session-token logic for passkey auth (Functional Core).

This module contains pure functions with no I/O or side effects. All
functions are deterministic given their arguments -- the current time is
passed in rather than read -- and fully unit-testable.

Token format (#229):
    <base64url(payload_json)>.<base64url(hmac_sha256(secret, payload_bytes))>

A stateless signed token, not a stored session id. The backend runs several
uvicorn workers with no shared session store, so a token that any worker can
verify from the shared secret alone is the smallest thing that works. The
cost is that individual sessions cannot be revoked before they expire --
acceptable at a 12-hour TTL for a single-admin site. Revoking a *device* is
done by deleting its credential, which stops new logins.

Deliberately not JWT: no algorithm negotiation (the `alg: none` family of
bugs is unreachable), no new dependency, and the payload is three fields.
"""

import base64
import hmac
import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

DEFAULT_TTL_SECONDS = 12 * 60 * 60
"""Session lifetime. Short enough that a stolen token expires the same day,
long enough to write for an evening without re-tapping the passkey."""

SESSION_KIND = "passkey"
"""Marks tokens minted by a passkey assertion, distinguishing them from the
static admin token that shares the same Authorization: Bearer transport."""


@dataclass(frozen=True)
class SessionClaims:
    """Verified contents of a session token."""

    credential_id: str
    issued_at: int
    expires_at: int


def _b64url_encode(raw: bytes) -> str:
    """Encode bytes as unpadded base64url."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    """Decode unpadded base64url. Raises ValueError on malformed input."""
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except Exception as e:  # binascii.Error and friends
        raise ValueError("malformed base64url segment") from e


def _sign(payload: bytes, secret: str) -> str:
    """Compute the base64url signature for a payload."""
    digest = hmac.new(secret.encode("utf-8"), payload, sha256).digest()
    return _b64url_encode(digest)


def derive_session_secret(admin_token: str, configured_secret: str | None = None) -> str:
    """Resolve the HMAC secret used to sign session tokens.

    An explicit SESSION_SECRET always wins. Without one, derive a stable
    secret from the admin token: every worker computes the same value, and
    sessions survive restarts, with no new secret to provision. It is no
    weaker than the admin token itself, which already grants full access.

    Args:
        admin_token: The static admin token from settings
        configured_secret: Explicit SESSION_SECRET, or None/empty if unset

    Returns:
        The signing secret (empty if neither input is configured)
    """
    if configured_secret:
        return configured_secret
    if not admin_token:
        return ""
    return hmac.new(admin_token.encode("utf-8"), b"mongado-session-v1", sha256).hexdigest()


def create_session_token(
    secret: str,
    credential_id: str,
    now: float,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> str:
    """Mint a signed session token.

    Args:
        secret: HMAC signing secret (see derive_session_secret)
        credential_id: The passkey credential that authenticated this session
        now: Current unix timestamp
        ttl_seconds: Lifetime in seconds

    Returns:
        The encoded token

    Raises:
        ValueError: If secret is empty
    """
    if not secret:
        raise ValueError("cannot sign a session token without a secret")

    payload: dict[str, Any] = {
        "kind": SESSION_KIND,
        "cred": credential_id,
        "iat": int(now),
        "exp": int(now) + ttl_seconds,
    }
    # sort_keys so the same claims always produce the same bytes
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"{_b64url_encode(payload_bytes)}.{_sign(payload_bytes, secret)}"


def looks_like_session_token(token: str) -> bool:
    """Whether a bearer token is *shaped* like a session token.

    Decidable without the signing secret, and deliberately so: it lets the
    caller tell "your session expired" from "that is a wrong admin token",
    so an expired session cannot burn attempts against the brute-force
    lockout. Nothing is trusted on the strength of this - a shaped token
    still has to pass verify_session_token.
    """
    if not token or token.count(".") != 1:
        return False
    encoded_payload = token.split(".")[0]
    try:
        payload = json.loads(_b64url_decode(encoded_payload))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("kind") == SESSION_KIND


def verify_session_token(token: str, secret: str, now: float) -> SessionClaims | None:
    """Verify a session token's signature and expiry.

    Args:
        token: The token from the Authorization header
        secret: HMAC signing secret
        now: Current unix timestamp

    Returns:
        SessionClaims if the token is authentic and unexpired, else None.
        Returns None rather than raising so callers can fall through to the
        static-token comparison without branching on exception type.
    """
    if not token or not secret or token.count(".") != 1:
        return None

    encoded_payload, signature = token.split(".")

    try:
        payload_bytes = _b64url_decode(encoded_payload)
    except ValueError:
        return None

    if not hmac.compare_digest(_sign(payload_bytes, secret), signature):
        return None

    try:
        payload = json.loads(payload_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(payload, dict) or payload.get("kind") != SESSION_KIND:
        return None

    credential_id = payload.get("cred")
    issued_at = payload.get("iat")
    expires_at = payload.get("exp")
    if not isinstance(credential_id, str) or not isinstance(issued_at, int):
        return None
    if not isinstance(expires_at, int) or int(now) >= expires_at:
        return None

    return SessionClaims(
        credential_id=credential_id,
        issued_at=issued_at,
        expires_at=expires_at,
    )
