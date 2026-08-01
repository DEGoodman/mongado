"""Passkey (WebAuthn) admin authentication endpoints (#229).

Replaces the static admin token as the login mechanism for humans. The token
itself is not retired: CI/automation callers (deploy-time backups) still use
it, and it gates first-time passkey enrollment.

Ceremony flow:
    1. POST /api/auth/register/options    -> creation options + stored challenge
    2. POST /api/auth/register/verify     -> credential persisted to Neo4j
    3. POST /api/auth/login/options       -> request options + stored challenge
    4. POST /api/auth/login/verify        -> signed session token

Challenges live in Neo4j rather than memory because production runs four
uvicorn workers; the worker that issues a challenge is usually not the one
that verifies the response.
"""

import json
import logging
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url, parse_client_data_json
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from auth import AdminUser, verify_admin_optional
from config import Settings, get_settings
from core.sessions import (
    DEFAULT_TTL_SECONDS,
    create_session_token,
    derive_session_secret,
)
from models import (
    AuthenticationOptionsResponse,
    AuthenticationVerifyRequest,
    CredentialDeleteResponse,
    CredentialInfo,
    CredentialsListResponse,
    RegistrationOptionsRequest,
    RegistrationOptionsResponse,
    RegistrationVerifyRequest,
    SessionResponse,
    SessionStatusResponse,
)
from rate_limiter import RATE_LIMITS, limiter

logger = logging.getLogger(__name__)

CHALLENGE_TTL_SECONDS = 5 * 60
"""How long a ceremony may sit unfinished. Matches the 60s authenticator
timeout with generous slack for the OS prompt and a fumbled Touch ID."""

ADMIN_USER_NAME = "admin"
"""Single-admin site: every passkey belongs to the same notional user, so
the user handle is constant and the login ceremony can be usernameless."""


def create_auth_router(neo4j_adapter: Any) -> APIRouter:
    """Create the passkey auth router with dependencies injected.

    Args:
        neo4j_adapter: Neo4j adapter for credential and challenge storage

    Returns:
        Configured APIRouter with auth endpoints
    """
    # Created per call rather than at module level: a shared router object
    # would have every factory call register duplicate paths onto it, and the
    # first registration (with whichever adapter it captured) would win.
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    def _require_neo4j() -> None:
        """Passkeys need persistent storage; fail loudly rather than half-work."""
        if not neo4j_adapter.is_available():
            raise HTTPException(
                status_code=503,
                detail="Passkey authentication unavailable: database not reachable.",
            )

    def _stored_credentials() -> list[dict[str, Any]]:
        return list(neo4j_adapter.list_admin_credentials())

    def _session_secret(settings: Settings) -> str:
        secret = derive_session_secret(settings.admin_token, settings.session_secret)
        if not secret:
            raise HTTPException(
                status_code=500,
                detail="Server configuration error: no session signing secret available.",
            )
        return secret

    def _challenge_from_credential(credential: dict[str, Any]) -> str:
        """Extract the echoed challenge from a ceremony response.

        The authenticator returns the challenge we issued inside
        clientDataJSON. Reading it here lets us look the challenge up in the
        store; consuming it proves we issued it and that it is unused, and
        py_webauthn then re-verifies the match as part of its own checks.
        """
        try:
            client_data_b64 = credential["response"]["clientDataJSON"]
            client_data = parse_client_data_json(base64url_to_bytes(client_data_b64))
            return bytes_to_base64url(client_data.challenge)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as e:
            logger.warning("Malformed credential payload: %s", e)
            raise HTTPException(status_code=400, detail="Malformed credential payload.") from e

    @router.post("/register/options", response_model=RegistrationOptionsResponse)
    @limiter.limit(RATE_LIMITS["admin"])
    async def registration_options(
        request: Request,
        body: RegistrationOptionsRequest,
        _admin: AdminUser,
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> RegistrationOptionsResponse:
        """Begin passkey enrollment.

        Requires existing admin auth: the static token for the first passkey,
        a live passkey session for every one after. There is deliberately no
        unauthenticated enrollment path.
        """
        _require_neo4j()

        existing = _stored_credentials()
        options = generate_registration_options(
            rp_id=settings.webauthn_rp_id_resolved,
            rp_name=settings.webauthn_rp_name,
            user_name=ADMIN_USER_NAME,
            user_display_name=ADMIN_USER_NAME,
            user_id=ADMIN_USER_NAME.encode("utf-8"),
            # Stop the same authenticator from enrolling twice
            exclude_credentials=[
                PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["credential_id"]))
                for c in existing
            ],
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

        neo4j_adapter.store_webauthn_challenge(
            bytes_to_base64url(options.challenge), "registration", CHALLENGE_TTL_SECONDS
        )
        logger.info("Issued passkey registration challenge for '%s'", body.name)
        return RegistrationOptionsResponse(options=json.loads(options_to_json(options)))

    @router.post("/register/verify", response_model=CredentialsListResponse)
    @limiter.limit(RATE_LIMITS["admin"])
    async def registration_verify(
        request: Request,
        body: RegistrationVerifyRequest,
        _admin: AdminUser,
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> CredentialsListResponse:
        """Complete passkey enrollment and persist the credential."""
        _require_neo4j()

        challenge = _challenge_from_credential(body.credential)
        if not neo4j_adapter.consume_webauthn_challenge(challenge, "registration"):
            raise HTTPException(
                status_code=400, detail="Registration challenge expired or already used."
            )

        try:
            verified = verify_registration_response(
                credential=body.credential,
                expected_challenge=base64url_to_bytes(challenge),
                expected_rp_id=settings.webauthn_rp_id_resolved,
                expected_origin=settings.cors_origins_list,
            )
        except InvalidRegistrationResponse as e:
            logger.warning("Passkey registration rejected: %s", e)
            raise HTTPException(status_code=400, detail=f"Registration failed: {e}") from e

        neo4j_adapter.create_admin_credential(
            credential_id=bytes_to_base64url(verified.credential_id),
            public_key=verified.credential_public_key,
            sign_count=verified.sign_count,
            name=body.name,
        )
        logger.info("Registered passkey '%s'", body.name)
        return _credentials_response()

    @router.post("/login/options", response_model=AuthenticationOptionsResponse)
    @limiter.limit(RATE_LIMITS["admin"])
    async def authentication_options(
        request: Request,
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> AuthenticationOptionsResponse:
        """Begin passkey login. Unauthenticated by necessity."""
        _require_neo4j()

        credentials = _stored_credentials()
        if not credentials:
            raise HTTPException(
                status_code=409,
                detail="No passkeys registered. Enroll one from the admin page first.",
            )

        options = generate_authentication_options(
            rp_id=settings.webauthn_rp_id_resolved,
            allow_credentials=[
                PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["credential_id"]))
                for c in credentials
            ],
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        neo4j_adapter.store_webauthn_challenge(
            bytes_to_base64url(options.challenge), "authentication", CHALLENGE_TTL_SECONDS
        )
        return AuthenticationOptionsResponse(options=json.loads(options_to_json(options)))

    @router.post("/login/verify", response_model=SessionResponse)
    @limiter.limit(RATE_LIMITS["admin"])
    async def authentication_verify(
        request: Request,
        body: AuthenticationVerifyRequest,
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> SessionResponse:
        """Complete passkey login and issue a session token."""
        _require_neo4j()

        challenge = _challenge_from_credential(body.credential)
        if not neo4j_adapter.consume_webauthn_challenge(challenge, "authentication"):
            raise HTTPException(status_code=400, detail="Login challenge expired or already used.")

        credential_id = body.credential.get("id")
        if not isinstance(credential_id, str):
            raise HTTPException(status_code=400, detail="Malformed credential payload.")

        stored = neo4j_adapter.get_admin_credential(credential_id)
        if not stored:
            logger.warning("Login attempt with unknown credential %s", credential_id[:12])
            raise HTTPException(status_code=403, detail="Unknown passkey.")

        try:
            verified = verify_authentication_response(
                credential=body.credential,
                expected_challenge=base64url_to_bytes(challenge),
                expected_rp_id=settings.webauthn_rp_id_resolved,
                expected_origin=settings.cors_origins_list,
                credential_public_key=stored["public_key"],
                credential_current_sign_count=stored["sign_count"],
            )
        except InvalidAuthenticationResponse as e:
            logger.warning("Passkey login rejected: %s", e)
            raise HTTPException(status_code=403, detail=f"Login failed: {e}") from e

        neo4j_adapter.record_admin_credential_use(credential_id, verified.new_sign_count)

        now = time.time()
        token = create_session_token(
            secret=_session_secret(settings),
            credential_id=credential_id,
            now=now,
            ttl_seconds=DEFAULT_TTL_SECONDS,
        )
        logger.info("Passkey login succeeded for '%s'", stored["name"])
        return SessionResponse(
            token=token,
            expires_at=int(now) + DEFAULT_TTL_SECONDS,
            credential_name=stored["name"],
        )

    @router.get("/session", response_model=SessionStatusResponse)
    async def session_status(
        auth: Annotated[dict[str, Any], Depends(verify_admin_optional)],
    ) -> SessionStatusResponse:
        """Report whether the caller's credentials are currently valid.

        Replaces the frontend's old "create a note then delete it" probe.
        Never 401s - the answer to "am I logged in?" is a 200 either way.
        """
        return SessionStatusResponse(
            authenticated=auth["authenticated"],
            kind=auth["kind"],
            expires_at=auth.get("expires_at"),
        )

    def _credentials_response() -> CredentialsListResponse:
        credentials = [
            CredentialInfo(
                credential_id=c["credential_id"],
                name=c["name"] or "Passkey",
                created_at=c["created_at"] or 0.0,
                last_used_at=c["last_used_at"],
            )
            for c in _stored_credentials()
        ]
        return CredentialsListResponse(credentials=credentials, count=len(credentials))

    @router.get("/credentials", response_model=CredentialsListResponse)
    async def list_credentials(_admin: AdminUser) -> CredentialsListResponse:
        """List registered passkeys."""
        _require_neo4j()
        return _credentials_response()

    # Plain path param, not `:path` - credential IDs are base64url, which has
    # no "/", so nothing needs to span segments
    @router.delete("/credentials/{credential_id}", response_model=CredentialDeleteResponse)
    async def delete_credential(credential_id: str, _admin: AdminUser) -> CredentialDeleteResponse:
        """Revoke a passkey.

        Deleting the last one is allowed: the static admin token remains a
        working way back in, so this cannot lock the admin out.
        """
        _require_neo4j()

        deleted = neo4j_adapter.delete_admin_credential(credential_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Passkey not found.")

        logger.info("Revoked passkey %s", credential_id[:12])
        return CredentialDeleteResponse(success=True, message="Passkey revoked.")

    return router
