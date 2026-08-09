"""Pure logic for scoped API bearer tokens (Functional Core, #300).

Programmatic callers (scripts, a GitHub deploy job) need to hit the API
without the static admin token - which is unrevocable - or a browser passkey
ceremony. This module is the pure half: token shape, hashing, scope matching,
and expiry, all deterministic and unit-testable without I/O. The imperative
half (random generation, Neo4j storage, request auth) lives in the shell.

Token model:
    - The plaintext is `mgd_<random>`; only its SHA-256 hash is ever stored,
      so a database read cannot recover a usable token.
    - Each token carries a set of scopes (see KNOWN_SCOPES). A request is
      allowed when the token's scopes satisfy the endpoint's required scope,
      with `admin:*` acting as a wildcard that satisfies everything.
    - A passkey session (verified elsewhere) is full admin and bypasses this
      check entirely; scopes only ever constrain API tokens.
"""

from hashlib import sha256

TOKEN_PREFIX = "mgd_"  # nosec B105 - a public token prefix, not a secret
"""Marks a bearer token as an API token, distinguishing it at a glance from a
passkey session token (which is `<payload>.<sig>`) and letting auth route a
mismatched `mgd_` token to the brute-force lockout instead of the session path."""

ADMIN_WILDCARD = "admin:*"
"""A scope that satisfies every required scope: full admin, but revocable."""

KNOWN_SCOPES: frozenset[str] = frozenset(
    {
        "notes:write",
        "library:write",
        "feature_flags:write",
        "ai:use",
        ADMIN_WILDCARD,
    }
)
"""The controlled vocabulary of assignable scopes. Reads (notes/library GETs)
are currently public, so no read scopes exist yet; add them the day a read
endpoint gets gated."""

SCOPE_DESCRIPTIONS: dict[str, str] = {
    "notes:write": "Create, update, and delete notes; upload images",
    "library:write": "Create, update, and delete library entries",
    "feature_flags:write": "Read and toggle feature flags (LLM break-glass)",
    "ai:use": "Use AI editor and suggestion endpoints",
    ADMIN_WILDCARD: "Full admin: everything above plus backups, auth, and token management",
}
"""Human-readable descriptions for the admin create-token form. Keys mirror
KNOWN_SCOPES exactly."""


def hash_token(token: str) -> str:
    """Hash a plaintext token for storage and lookup.

    SHA-256 (not a slow password hash) is deliberate: these are
    high-entropy random secrets, not user-chosen passwords, so there is
    nothing to brute-force and lookup happens on every authed request.

    Args:
        token: The plaintext bearer token

    Returns:
        Lowercase hex SHA-256 digest
    """
    return sha256(token.encode("utf-8")).hexdigest()


def token_display_prefix(token: str, chars: int = 8) -> str:
    """A safe, non-secret fragment of a token for display in the admin list.

    Shows the `mgd_` marker plus a few characters so a human can tell two
    tokens apart, without revealing enough to be usable.

    Args:
        token: The plaintext bearer token
        chars: How many characters after the prefix to reveal

    Returns:
        e.g. "mgd_a1b2c3d4…"
    """
    head = token[: len(TOKEN_PREFIX) + chars]
    return f"{head}…" if len(token) > len(head) else head


def looks_like_api_token(token: str) -> bool:
    """Whether a bearer token is shaped like an API token.

    Decidable without any secret, so auth can tell an API-token attempt from
    a passkey session or static-token attempt and route lockout accordingly.
    """
    return token.startswith(TOKEN_PREFIX)


def scopes_satisfy(granted: set[str], required: str) -> bool:
    """Whether a set of granted scopes satisfies a required scope.

    `admin:*` is a wildcard that satisfies any requirement.

    Args:
        granted: Scopes attached to the presented token
        required: The scope the endpoint demands

    Returns:
        True if the token may proceed
    """
    return ADMIN_WILDCARD in granted or required in granted


def is_expired(expires_at: float | None, now: float) -> bool:
    """Whether a token has expired.

    Args:
        expires_at: Unix timestamp of expiry, or None for a token that
            never expires
        now: Current unix timestamp

    Returns:
        True if the token is past its expiry
    """
    if expires_at is None:
        return False
    return now >= expires_at


def validate_scopes(requested: list[str]) -> list[str]:
    """Normalize and validate a requested scope list.

    Deduplicates while preserving order and rejects anything outside the
    controlled vocabulary, so an unknown scope cannot be silently stored and
    then never match (a token that can do nothing).

    Args:
        requested: Scopes asked for at token creation

    Returns:
        The cleaned scope list

    Raises:
        ValueError: If the list is empty or contains an unknown scope
    """
    seen: dict[str, None] = {}
    for scope in requested:
        normalized = scope.strip()
        if normalized not in KNOWN_SCOPES:
            raise ValueError(f"Unknown scope: {scope!r}. Known scopes: {sorted(KNOWN_SCOPES)}")
        seen[normalized] = None
    if not seen:
        raise ValueError("At least one scope is required.")
    return list(seen)
