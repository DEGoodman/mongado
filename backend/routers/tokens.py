"""Scoped API token management endpoints (#300).

Lets a full admin mint, list, and revoke `mgd_`-prefixed bearer tokens with
assignable scopes - the safe way to script against the API without exposing the
unrevocable static admin token. Managing tokens itself always requires full
admin (a passkey session or an `admin:*` token), so a narrowly-scoped token
cannot escalate by minting a broader one.

The plaintext token is returned exactly once, at creation; only its SHA-256
hash is stored. Pure token logic (hashing, scope validation) lives in
core.api_tokens; this router is the imperative shell around Neo4j storage.
"""

import logging
import secrets
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from auth import AdminUser
from core.api_tokens import (
    KNOWN_SCOPES,
    SCOPE_DESCRIPTIONS,
    TOKEN_PREFIX,
    hash_token,
    validate_scopes,
)
from models import (
    ApiScopeInfo,
    ApiScopesResponse,
    ApiTokenCreateRequest,
    ApiTokenCreateResponse,
    ApiTokenDeleteResponse,
    ApiTokenInfo,
    ApiTokensListResponse,
)

logger = logging.getLogger(__name__)


def create_tokens_router(neo4j_adapter: Any) -> APIRouter:
    """Create the API-token router with dependencies injected.

    Args:
        neo4j_adapter: Neo4j adapter for token storage

    Returns:
        Configured APIRouter with token endpoints
    """
    router = APIRouter(prefix="/api/admin/tokens", tags=["tokens"])

    def _require_neo4j() -> None:
        """Tokens need persistent storage; fail loudly rather than half-work."""
        if not neo4j_adapter.is_available():
            raise HTTPException(
                status_code=503,
                detail="API tokens unavailable: database not reachable.",
            )

    def _to_info(record: dict[str, Any]) -> ApiTokenInfo:
        return ApiTokenInfo(
            token_id=record["token_id"],
            name=record["name"],
            scopes=list(record["scopes"]),
            created_at=record["created_at"],
            expires_at=record["expires_at"],
            last_used_at=record["last_used_at"],
        )

    @router.get("/scopes", response_model=ApiScopesResponse)
    async def list_scopes(_admin: AdminUser) -> ApiScopesResponse:
        """List the assignable scopes, for the admin create form."""
        return ApiScopesResponse(
            scopes=[
                ApiScopeInfo(name=name, description=SCOPE_DESCRIPTIONS.get(name, ""))
                for name in sorted(KNOWN_SCOPES)
            ]
        )

    @router.get("", response_model=ApiTokensListResponse)
    async def list_tokens(_admin: AdminUser) -> ApiTokensListResponse:
        """List stored API tokens (metadata only, never the secret)."""
        _require_neo4j()
        records = neo4j_adapter.list_api_tokens()
        return ApiTokensListResponse(
            tokens=[_to_info(r) for r in records],
            count=len(records),
        )

    @router.post("", response_model=ApiTokenCreateResponse)
    async def create_token(
        body: ApiTokenCreateRequest, _admin: AdminUser
    ) -> ApiTokenCreateResponse:
        """Mint a new scoped API token. Returns the plaintext exactly once."""
        _require_neo4j()

        try:
            scopes = validate_scopes(body.scopes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        # High-entropy random secret; only its hash is ever stored.
        plaintext = f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
        token_id = uuid.uuid4().hex
        now = time.time()
        expires_at = (
            now + body.expires_in_days * 86400 if body.expires_in_days is not None else None
        )

        stored = neo4j_adapter.create_api_token(
            token_id=token_id,
            token_hash=hash_token(plaintext),
            name=body.name,
            scopes=scopes,
            created_at=now,
            expires_at=expires_at,
        )
        if not stored:
            raise HTTPException(status_code=503, detail="Failed to store token.")

        # Log the id/scopes for the audit trail - never the plaintext.
        logger.info(
            "Minted API token %s ('%s') scopes=%s expires_at=%s",
            token_id,
            body.name,
            scopes,
            expires_at,
        )
        return ApiTokenCreateResponse(
            token=plaintext,
            info=ApiTokenInfo(
                token_id=token_id,
                name=body.name,
                scopes=scopes,
                created_at=now,
                expires_at=expires_at,
                last_used_at=None,
            ),
        )

    @router.delete("/{token_id}", response_model=ApiTokenDeleteResponse)
    async def delete_token(token_id: str, _admin: AdminUser) -> ApiTokenDeleteResponse:
        """Revoke an API token immediately."""
        _require_neo4j()
        if not neo4j_adapter.delete_api_token(token_id):
            raise HTTPException(status_code=404, detail="Token not found.")
        logger.info("Revoked API token %s", token_id)
        return ApiTokenDeleteResponse(success=True, message="Token revoked.")

    return router
