"""Tests for session-token logic (pure functions, #229)."""

import base64
import json

from core.sessions import (
    DEFAULT_TTL_SECONDS,
    create_session_token,
    derive_session_secret,
    looks_like_session_token,
    verify_session_token,
)

SECRET = "test-signing-secret"
NOW = 1_700_000_000.0


class TestDeriveSessionSecret:
    """Resolving the signing secret."""

    def test_explicit_secret_wins(self) -> None:
        assert derive_session_secret("admin-token", "explicit") == "explicit"

    def test_derived_from_admin_token(self) -> None:
        derived = derive_session_secret("admin-token")
        assert derived
        assert derived != "admin-token"

    def test_derivation_is_stable(self) -> None:
        """Every worker must derive the same secret, or sessions break at random."""
        assert derive_session_secret("admin-token") == derive_session_secret("admin-token")

    def test_different_tokens_derive_different_secrets(self) -> None:
        assert derive_session_secret("token-a") != derive_session_secret("token-b")

    def test_no_inputs_yields_no_secret(self) -> None:
        assert derive_session_secret("", "") == ""


class TestRoundTrip:
    """Minting and verifying."""

    def test_valid_token_verifies(self) -> None:
        token = create_session_token(SECRET, "cred-1", NOW)
        claims = verify_session_token(token, SECRET, NOW + 60)
        assert claims is not None
        assert claims.credential_id == "cred-1"
        assert claims.expires_at == int(NOW) + DEFAULT_TTL_SECONDS

    def test_custom_ttl_honored(self) -> None:
        token = create_session_token(SECRET, "cred-1", NOW, ttl_seconds=30)
        assert verify_session_token(token, SECRET, NOW + 10) is not None
        assert verify_session_token(token, SECRET, NOW + 31) is None

    def test_expired_token_rejected(self) -> None:
        token = create_session_token(SECRET, "cred-1", NOW)
        assert verify_session_token(token, SECRET, NOW + DEFAULT_TTL_SECONDS + 1) is None

    def test_expiry_boundary_is_exclusive(self) -> None:
        """A token is dead *at* its expiry, not one second after."""
        token = create_session_token(SECRET, "cred-1", NOW, ttl_seconds=10)
        assert verify_session_token(token, SECRET, NOW + 10) is None

    def test_wrong_secret_rejected(self) -> None:
        token = create_session_token(SECRET, "cred-1", NOW)
        assert verify_session_token(token, "other-secret", NOW) is None

    def test_empty_secret_cannot_sign(self) -> None:
        try:
            create_session_token("", "cred-1", NOW)
        except ValueError:
            return
        raise AssertionError("signing with an empty secret must raise")

    def test_empty_secret_verifies_nothing(self) -> None:
        token = create_session_token(SECRET, "cred-1", NOW)
        assert verify_session_token(token, "", NOW) is None


class TestTampering:
    """A token whose payload was edited must not verify."""

    def test_modified_payload_rejected(self) -> None:
        token = create_session_token(SECRET, "cred-1", NOW)
        encoded_payload, signature = token.split(".")
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload + "=="))
        payload["exp"] += 10_000
        forged = (
            base64.urlsafe_b64encode(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            )
            .decode()
            .rstrip("=")
        )
        assert verify_session_token(f"{forged}.{signature}", SECRET, NOW) is None

    def test_swapped_signature_rejected(self) -> None:
        a = create_session_token(SECRET, "cred-a", NOW)
        b = create_session_token(SECRET, "cred-b", NOW)
        forged = f"{a.split('.')[0]}.{b.split('.')[1]}"
        assert verify_session_token(forged, SECRET, NOW) is None

    def test_malformed_tokens_rejected(self) -> None:
        for bad in ["", "nodot", "a.b.c", "!!!.###", ".", "a."]:
            assert verify_session_token(bad, SECRET, NOW) is None

    def test_non_session_payload_rejected(self) -> None:
        """A correctly-signed blob that is not a session must not authenticate."""
        payload = json.dumps({"kind": "other", "cred": "x", "iat": 1, "exp": 9_999_999_999})
        encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        # Sign it properly, so only the `kind` check can reject it
        import hmac
        from hashlib import sha256

        sig = (
            base64.urlsafe_b64encode(
                hmac.new(SECRET.encode(), base64.urlsafe_b64decode(encoded + "=="), sha256).digest()
            )
            .decode()
            .rstrip("=")
        )
        assert verify_session_token(f"{encoded}.{sig}", SECRET, NOW) is None


class TestLooksLikeSessionToken:
    """Shape detection, which decides 401-expired vs 403-wrong-token."""

    def test_real_token_looks_like_one(self) -> None:
        assert looks_like_session_token(create_session_token(SECRET, "cred-1", NOW)) is True

    def test_expired_token_still_looks_like_one(self) -> None:
        """The whole point: an expired session must be recognizable as a session."""
        token = create_session_token(SECRET, "cred-1", NOW - 100_000)
        assert verify_session_token(token, SECRET, NOW) is None
        assert looks_like_session_token(token) is True

    def test_static_token_does_not(self) -> None:
        assert looks_like_session_token("some-static-admin-token") is False

    def test_garbage_does_not(self) -> None:
        for bad in ["", "a.b.c", "!!!.@@@", "nodot"]:
            assert looks_like_session_token(bad) is False
