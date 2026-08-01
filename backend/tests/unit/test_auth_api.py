"""Tests for passkey authentication endpoints (#229).

The WebAuthn ceremonies themselves need a real authenticator, so they are
exercised in the browser with a virtual authenticator rather than here.
These tests cover everything around them: which endpoints require auth,
challenge issuance and single-use consumption, credential management, and
the interaction between session tokens and the #225 brute-force lockout.
"""

import os
import time
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ["TESTING"] = "1"

from auth import MAX_FAILED_ATTEMPTS
from config import get_settings
from core.sessions import create_session_token, derive_session_secret
from main import app as real_app
from routers.auth import create_auth_router

TEST_ADMIN_TOKEN = "test-admin-token-for-ci"


def _admin_token() -> str:
    return get_settings().admin_token or TEST_ADMIN_TOKEN


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_admin_token()}"}


@pytest.fixture
def session_headers() -> dict[str, str]:
    """Headers carrying a valid passkey session token."""
    settings = get_settings()
    secret = derive_session_secret(_admin_token(), settings.session_secret)
    token = create_session_token(secret, "test-credential", time.time())
    return {"Authorization": f"Bearer {token}"}


class FakeNeo4jAdapter:
    """In-memory stand-in for the Neo4j adapter.

    CI has no Neo4j, and these endpoints are pure orchestration over the
    adapter's interface, so a fake keeps the tests honest without a server.
    """

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.credentials: list[dict[str, Any]] = []
        self.challenges: list[tuple[str, str, float]] = []

    def is_available(self) -> bool:
        return self._available

    def list_admin_credentials(self) -> list[dict[str, Any]]:
        return list(self.credentials)

    def get_admin_credential(self, credential_id: str) -> dict[str, Any] | None:
        return next(
            (c for c in self.credentials if c["credential_id"] == credential_id),
            None,
        )

    def create_admin_credential(
        self, credential_id: str, public_key: bytes, sign_count: int, name: str
    ) -> bool:
        self.credentials.append(
            {
                "credential_id": credential_id,
                "public_key": public_key,
                "sign_count": sign_count,
                "name": name,
                "created_at": time.time(),
                "last_used_at": None,
            }
        )
        return True

    def record_admin_credential_use(self, credential_id: str, sign_count: int) -> bool:
        credential = self.get_admin_credential(credential_id)
        if not credential:
            return False
        credential["sign_count"] = sign_count
        credential["last_used_at"] = time.time()
        return True

    def delete_admin_credential(self, credential_id: str) -> bool:
        before = len(self.credentials)
        self.credentials = [c for c in self.credentials if c["credential_id"] != credential_id]
        return len(self.credentials) < before

    def store_webauthn_challenge(self, challenge: str, purpose: str, ttl_seconds: float) -> bool:
        self.challenges.append((challenge, purpose, time.time() + ttl_seconds))
        return True

    def consume_webauthn_challenge(self, challenge: str, purpose: str) -> bool:
        now = time.time()
        for entry in self.challenges:
            if entry[0] == challenge and entry[1] == purpose and entry[2] >= now:
                self.challenges.remove(entry)
                return True
        return False


def _client(adapter: FakeNeo4jAdapter) -> TestClient:
    """Mount the auth router alone, over the given adapter."""
    app = FastAPI()
    app.include_router(create_auth_router(neo4j_adapter=adapter))
    return TestClient(app)


@pytest.fixture
def adapter() -> FakeNeo4jAdapter:
    return FakeNeo4jAdapter()


@pytest.fixture
def client(adapter: FakeNeo4jAdapter) -> TestClient:
    return _client(adapter)


class TestRegistrationOptions:
    """POST /api/auth/register/options."""

    def test_requires_auth(self, client: TestClient) -> None:
        """Enrollment is never open - there is no unauthenticated path in."""
        response = client.post("/api/auth/register/options", json={"name": "Laptop"})
        assert response.status_code == 401

    def test_rejects_invalid_token(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/register/options",
            json={"name": "Laptop"},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 403

    def test_returns_creation_options(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/auth/register/options", json={"name": "Laptop"}, headers=admin_headers
        )
        assert response.status_code == 200
        options = response.json()["options"]
        assert options["challenge"]
        assert options["rp"]["name"] == "Mongado"
        assert options["user"]["name"] == "admin"

    def test_stores_challenge(
        self,
        client: TestClient,
        adapter: FakeNeo4jAdapter,
        admin_headers: dict[str, str],
    ) -> None:
        client.post("/api/auth/register/options", json={"name": "Laptop"}, headers=admin_headers)
        assert len(adapter.challenges) == 1
        assert adapter.challenges[0][1] == "registration"

    def test_session_token_can_enroll_another_passkey(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        """A signed-in admin adds a second device without the static token."""
        response = client.post(
            "/api/auth/register/options", json={"name": "Phone"}, headers=session_headers
        )
        assert response.status_code == 200

    def test_excludes_existing_credentials(
        self,
        client: TestClient,
        adapter: FakeNeo4jAdapter,
        admin_headers: dict[str, str],
    ) -> None:
        """An already-enrolled authenticator must not enroll twice."""
        adapter.create_admin_credential("dGVzdC1jcmVk", b"key", 0, "Existing")
        response = client.post(
            "/api/auth/register/options", json={"name": "Laptop"}, headers=admin_headers
        )
        assert len(response.json()["options"]["excludeCredentials"]) == 1


class TestRegistrationVerify:
    """POST /api/auth/register/verify."""

    def test_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/register/verify", json={"credential": {}, "name": "Laptop"}
        )
        assert response.status_code == 401

    def test_rejects_malformed_credential(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/auth/register/verify",
            json={"credential": {"nonsense": True}, "name": "Laptop"},
            headers=admin_headers,
        )
        assert response.status_code == 400
        assert "Malformed" in response.json()["detail"]


class TestAuthenticationOptions:
    """POST /api/auth/login/options."""

    def test_conflict_when_no_passkeys(self, client: TestClient) -> None:
        """Nothing to authenticate against yet - say so instead of 500ing."""
        response = client.post("/api/auth/login/options")
        assert response.status_code == 409

    def test_returns_request_options(self, client: TestClient, adapter: FakeNeo4jAdapter) -> None:
        adapter.create_admin_credential("dGVzdC1jcmVk", b"key", 0, "Laptop")
        response = client.post("/api/auth/login/options")
        assert response.status_code == 200
        options = response.json()["options"]
        assert options["challenge"]
        assert len(options["allowCredentials"]) == 1

    def test_needs_no_auth(self, client: TestClient, adapter: FakeNeo4jAdapter) -> None:
        """Login cannot require being logged in."""
        adapter.create_admin_credential("dGVzdC1jcmVk", b"key", 0, "Laptop")
        assert client.post("/api/auth/login/options").status_code == 200

    def test_stores_challenge(self, client: TestClient, adapter: FakeNeo4jAdapter) -> None:
        adapter.create_admin_credential("dGVzdC1jcmVk", b"key", 0, "Laptop")
        client.post("/api/auth/login/options")
        assert adapter.challenges[0][1] == "authentication"


class TestChallengeLifecycle:
    """Challenges are single-use and scoped to their ceremony."""

    def test_consume_removes_challenge(self, adapter: FakeNeo4jAdapter) -> None:
        adapter.store_webauthn_challenge("abc", "registration", 60)
        assert adapter.consume_webauthn_challenge("abc", "registration") is True
        assert adapter.consume_webauthn_challenge("abc", "registration") is False

    def test_purpose_is_scoped(self, adapter: FakeNeo4jAdapter) -> None:
        """A registration challenge must not authorize a login."""
        adapter.store_webauthn_challenge("abc", "registration", 60)
        assert adapter.consume_webauthn_challenge("abc", "authentication") is False

    def test_expired_challenge_rejected(self, adapter: FakeNeo4jAdapter) -> None:
        adapter.store_webauthn_challenge("abc", "registration", -1)
        assert adapter.consume_webauthn_challenge("abc", "registration") is False

    def test_login_rejects_unknown_challenge(
        self, client: TestClient, adapter: FakeNeo4jAdapter
    ) -> None:
        """A well-formed response whose challenge we never issued is refused."""
        adapter.create_admin_credential("dGVzdC1jcmVk", b"key", 0, "Laptop")
        # clientDataJSON for a challenge the server never stored
        import base64
        import json as json_lib

        client_data = base64.urlsafe_b64encode(
            json_lib.dumps(
                {"type": "webauthn.get", "challenge": "bm90LW91cnM", "origin": "http://x"}
            ).encode()
        ).decode()
        response = client.post(
            "/api/auth/login/verify",
            json={
                "credential": {"id": "dGVzdC1jcmVk", "response": {"clientDataJSON": client_data}}
            },
        )
        assert response.status_code == 400
        assert "expired or already used" in response.json()["detail"]


class TestCredentialManagement:
    """GET/DELETE /api/auth/credentials."""

    def test_list_requires_auth(self, client: TestClient) -> None:
        assert client.get("/api/auth/credentials").status_code == 401

    def test_list_returns_credentials(
        self,
        client: TestClient,
        adapter: FakeNeo4jAdapter,
        admin_headers: dict[str, str],
    ) -> None:
        adapter.create_admin_credential("dGVzdC1jcmVk", b"key", 0, "Laptop")
        response = client.get("/api/auth/credentials", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["credentials"][0]["name"] == "Laptop"

    def test_list_never_leaks_public_key(
        self,
        client: TestClient,
        adapter: FakeNeo4jAdapter,
        admin_headers: dict[str, str],
    ) -> None:
        adapter.create_admin_credential("dGVzdC1jcmVk", b"secret-key-bytes", 0, "Laptop")
        body = client.get("/api/auth/credentials", headers=admin_headers).text
        assert "public_key" not in body

    def test_delete_requires_auth(self, client: TestClient) -> None:
        assert client.delete("/api/auth/credentials/dGVzdC1jcmVk").status_code == 401

    def test_delete_removes_credential(
        self,
        client: TestClient,
        adapter: FakeNeo4jAdapter,
        admin_headers: dict[str, str],
    ) -> None:
        adapter.create_admin_credential("dGVzdC1jcmVk", b"key", 0, "Laptop")
        response = client.delete("/api/auth/credentials/dGVzdC1jcmVk", headers=admin_headers)
        assert response.status_code == 200
        assert adapter.credentials == []

    def test_delete_unknown_returns_404(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        response = client.delete("/api/auth/credentials/missing", headers=admin_headers)
        assert response.status_code == 404

    def test_delete_last_credential_allowed(
        self,
        client: TestClient,
        adapter: FakeNeo4jAdapter,
        admin_headers: dict[str, str],
    ) -> None:
        """The static token is still a way back in, so this cannot lock anyone out."""
        adapter.create_admin_credential("dGVzdC1jcmVk", b"key", 0, "Only")
        assert (
            client.delete("/api/auth/credentials/dGVzdC1jcmVk", headers=admin_headers).status_code
            == 200
        )


class TestNeo4jUnavailable:
    """Passkeys need storage; the failure must be explicit."""

    def test_register_options_returns_503(self, admin_headers: dict[str, str]) -> None:
        client = _client(FakeNeo4jAdapter(available=False))
        response = client.post(
            "/api/auth/register/options", json={"name": "Laptop"}, headers=admin_headers
        )
        assert response.status_code == 503

    def test_login_options_returns_503(self) -> None:
        client = _client(FakeNeo4jAdapter(available=False))
        assert client.post("/api/auth/login/options").status_code == 503


class TestSessionStatus:
    """GET /api/auth/session - the 'am I signed in?' probe."""

    def test_unauthenticated_is_200_not_401(self, client: TestClient) -> None:
        response = client.get("/api/auth/session")
        assert response.status_code == 200
        assert response.json() == {"authenticated": False, "kind": "none", "expires_at": None}

    def test_static_token_reported_as_token(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        body = client.get("/api/auth/session", headers=admin_headers).json()
        assert body["authenticated"] is True
        assert body["kind"] == "token"

    def test_session_token_reported_as_passkey(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        body = client.get("/api/auth/session", headers=session_headers).json()
        assert body["authenticated"] is True
        assert body["kind"] == "passkey"
        assert body["expires_at"] > time.time()

    def test_expired_session_reported_unauthenticated(self, client: TestClient) -> None:
        secret = derive_session_secret(_admin_token(), get_settings().session_secret)
        expired = create_session_token(secret, "cred", time.time() - 100_000)
        body = client.get(
            "/api/auth/session", headers={"Authorization": f"Bearer {expired}"}
        ).json()
        assert body["authenticated"] is False


class TestAuthResponsesAreNotCacheable:
    """Auth state must never be served from a cache.

    Regression for a bug found in browser testing: the API's blanket
    `max-age=60` on GETs meant that after enrolling a passkey, the admin page
    kept rendering the cached pre-enrollment (empty) credential list, and
    /api/auth/session kept reporting the pre-login answer, for a full minute.
    """

    def test_session_endpoint_is_no_store(self) -> None:
        client = TestClient(real_app)
        response = client.get("/api/auth/session")
        assert "no-store" in response.headers["Cache-Control"]

    def test_credentials_endpoint_is_no_store(self, admin_headers: dict[str, str]) -> None:
        client = TestClient(real_app)
        response = client.get("/api/auth/credentials", headers=admin_headers)
        assert "no-store" in response.headers["Cache-Control"]

    def test_auth_responses_are_private(self, admin_headers: dict[str, str]) -> None:
        """A shared cache must not hold one caller's credential list."""
        client = TestClient(real_app)
        response = client.get("/api/auth/credentials", headers=admin_headers)
        assert "private" in response.headers["Cache-Control"]

    def test_other_get_endpoints_still_cache(self) -> None:
        """The fix must not disable caching for the rest of the API."""
        client = TestClient(real_app)
        response = client.get("/api/notes?limit=1")
        assert "max-age=60" in response.headers["Cache-Control"]


class TestSessionTokenAcceptedByAdminEndpoints:
    """Session tokens must work everywhere the static token did."""

    def test_session_token_authorizes_admin_endpoint(self, session_headers: dict[str, str]) -> None:
        client = TestClient(real_app)
        response = client.get("/api/admin/backups", headers=session_headers)
        assert response.status_code == 200

    def test_expired_session_gets_401_not_403(self) -> None:
        """401 tells the frontend to re-authenticate; 403 means a bad token."""
        client = TestClient(real_app)
        secret = derive_session_secret(_admin_token(), get_settings().session_secret)
        expired = create_session_token(secret, "cred", time.time() - 100_000)
        response = client.get("/api/admin/backups", headers={"Authorization": f"Bearer {expired}"})
        assert response.status_code == 401
        assert "Session expired" in response.json()["detail"]

    def test_expired_sessions_do_not_trigger_lockout(self) -> None:
        """A stale browser tab must not lock the admin out of signing back in."""
        client = TestClient(real_app)
        secret = derive_session_secret(_admin_token(), get_settings().session_secret)
        expired = create_session_token(secret, "cred", time.time() - 100_000)
        headers = {"Authorization": f"Bearer {expired}"}

        for _ in range(MAX_FAILED_ATTEMPTS + 2):
            assert client.get("/api/admin/backups", headers=headers).status_code == 401

        # Not locked out: a valid token still works
        response = client.get(
            "/api/admin/backups", headers={"Authorization": f"Bearer {_admin_token()}"}
        )
        assert response.status_code == 200

    def test_forged_session_signature_rejected(self) -> None:
        """A session token signed with the wrong secret is not session-shaped auth."""
        client = TestClient(real_app)
        forged = create_session_token("attacker-secret", "cred", time.time())
        response = client.get("/api/admin/backups", headers={"Authorization": f"Bearer {forged}"})
        # Shaped like a session but unverifiable -> 401, never authorized
        assert response.status_code == 401
