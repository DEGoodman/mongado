"""Pydantic models for passkey (WebAuthn) admin authentication (#229)."""

from typing import Any

from pydantic import BaseModel, Field


class RegistrationOptionsRequest(BaseModel):
    """Request to begin passkey enrollment."""

    name: str = Field(
        "Passkey",
        max_length=64,
        description="Human label for the device being enrolled (e.g. 'MacBook')",
    )


class RegistrationOptionsResponse(BaseModel):
    """WebAuthn creation options, passed straight to navigator.credentials.create()."""

    options: dict[str, Any] = Field(..., description="PublicKeyCredentialCreationOptions as JSON")


class RegistrationVerifyRequest(BaseModel):
    """Completed registration ceremony from the browser."""

    credential: dict[str, Any] = Field(..., description="Credential returned by the authenticator")
    name: str = Field("Passkey", max_length=64, description="Human label for the device")


class AuthenticationOptionsResponse(BaseModel):
    """WebAuthn request options, passed to navigator.credentials.get()."""

    options: dict[str, Any] = Field(..., description="PublicKeyCredentialRequestOptions as JSON")


class AuthenticationVerifyRequest(BaseModel):
    """Completed authentication ceremony from the browser."""

    credential: dict[str, Any] = Field(..., description="Assertion returned by the authenticator")


class SessionResponse(BaseModel):
    """An issued admin session."""

    token: str = Field(..., description="Bearer token for subsequent admin requests")
    expires_at: int = Field(..., description="Unix timestamp when the session expires")
    credential_name: str = Field(..., description="Name of the passkey that authenticated")


class SessionStatusResponse(BaseModel):
    """Whether the caller's current credentials are valid."""

    authenticated: bool = Field(..., description="Whether the request carried valid admin auth")
    kind: str = Field(..., description="'passkey', 'token', or 'none'")
    expires_at: int | None = Field(None, description="Session expiry, for passkey sessions only")


class CredentialInfo(BaseModel):
    """A registered passkey, as shown in the admin UI."""

    credential_id: str = Field(..., description="base64url credential ID")
    name: str = Field(..., description="Human label for the device")
    created_at: float = Field(..., description="Unix timestamp of enrollment")
    last_used_at: float | None = Field(None, description="Unix timestamp of last successful login")


class CredentialsListResponse(BaseModel):
    """All registered passkeys."""

    credentials: list[CredentialInfo] = Field(..., description="Registered passkeys, newest first")
    count: int = Field(..., description="Number of registered passkeys")


class CredentialDeleteResponse(BaseModel):
    """Result of revoking a passkey."""

    success: bool = Field(..., description="Whether the credential was deleted")
    message: str = Field(..., description="Human-readable outcome")
