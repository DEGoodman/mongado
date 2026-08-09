"""Integration tests for scoped API tokens (#300).

Covers the token-management router (create/list/revoke), and the end-to-end
authorization path: a minted token authenticating a request and being allowed
or rejected by require_scope. Auth's token lookup reads the global Neo4j
adapter, so we point that at the same in-memory fake the router writes to.
"""

import os
import time
from typing import Annotated, Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

os.environ["TESTING"] = "1"

import auth
from auth import auth_tracker, require_scope
from config import get_settings
from core.sessions import create_session_token, derive_session_secret
from routers.tokens import create_tokens_router

TEST_ADMIN_TOKEN = "test-admin-token-for-ci"


def _admin_token() -> str:
    return get_settings().admin_token or TEST_ADMIN_TOKEN


@pytest.fixture
def session_headers() -> dict[str, str]:
    """Full-admin headers via a valid passkey session token."""
    settings = get_settings()
    secret = derive_session_secret(_admin_token(), settings.session_secret)
    token = create_session_token(secret, "test-credential", time.time())
    return {"Authorization": f"Bearer {token}"}


class FakeNeo4jAdapter:
    """In-memory stand-in for the Neo4j adapter's API-token surface."""

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.tokens: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return self._available

    def create_api_token(
        self,
        token_id: str,
        token_hash: str,
        name: str,
        scopes: list[str],
        created_at: float,
        expires_at: float | None,
    ) -> bool:
        self.tokens.append(
            {
                "token_id": token_id,
                "token_hash": token_hash,
                "name": name,
                "scopes": list(scopes),
                "created_at": created_at,
                "expires_at": expires_at,
                "last_used_at": None,
            }
        )
        return True

    def _public(self, record: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in record.items() if k != "token_hash"}

    def list_api_tokens(self) -> list[dict[str, Any]]:
        return [self._public(t) for t in sorted(self.tokens, key=lambda t: -t["created_at"])]

    def get_api_token_by_hash(self, token_hash: str) -> dict[str, Any] | None:
        record = next((t for t in self.tokens if t["token_hash"] == token_hash), None)
        return self._public(record) if record else None

    def record_api_token_use(self, token_id: str, now: float) -> bool:
        for t in self.tokens:
            if t["token_id"] == token_id:
                t["last_used_at"] = now
                return True
        return False

    def delete_api_token(self, token_id: str) -> bool:
        before = len(self.tokens)
        self.tokens = [t for t in self.tokens if t["token_id"] != token_id]
        return len(self.tokens) < before


@pytest.fixture(autouse=True)
def reset_lockout() -> None:
    auth_tracker.reset()


@pytest.fixture
def adapter(monkeypatch: pytest.MonkeyPatch) -> FakeNeo4jAdapter:
    fake = FakeNeo4jAdapter()
    # Auth resolves API tokens against the *global* adapter; point it at the fake
    # so the token the router stores is the one auth can look up.
    monkeypatch.setattr(auth, "get_neo4j_adapter", lambda: fake)
    return fake


@pytest.fixture
def client(adapter: FakeNeo4jAdapter) -> TestClient:
    """Tokens router plus two scope-guarded probe endpoints."""
    app = FastAPI()
    app.include_router(create_tokens_router(neo4j_adapter=adapter))

    @app.post("/probe/notes")
    async def _notes(_p: Annotated[dict, Depends(require_scope("notes:write"))]) -> dict[str, bool]:
        return {"ok": True}

    @app.post("/probe/library")
    async def _library(
        _p: Annotated[dict, Depends(require_scope("library:write"))],
    ) -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestTokenManagement:
    def test_create_requires_full_admin(self, client: TestClient) -> None:
        response = client.post(
            "/api/admin/tokens",
            json={"name": "x", "scopes": ["notes:write"]},
        )
        assert response.status_code == 401

    def test_create_returns_plaintext_once(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/admin/tokens",
            json={"name": "importer", "scopes": ["library:write"], "expires_in_days": 30},
            headers=session_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["token"].startswith("mgd_")
        assert body["info"]["name"] == "importer"
        assert body["info"]["scopes"] == ["library:write"]
        assert body["info"]["expires_at"] is not None

    def test_create_rejects_unknown_scope(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/admin/tokens",
            json={"name": "x", "scopes": ["notes:destroy"]},
            headers=session_headers,
        )
        assert response.status_code == 400

    def test_list_never_exposes_secret(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        client.post(
            "/api/admin/tokens",
            json={"name": "a", "scopes": ["ai:use"]},
            headers=session_headers,
        )
        response = client.get("/api/admin/tokens", headers=session_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert "token_hash" not in body["tokens"][0]
        assert "token" not in body["tokens"][0]

    def test_revoke(self, client: TestClient, session_headers: dict[str, str]) -> None:
        created = client.post(
            "/api/admin/tokens",
            json={"name": "temp", "scopes": ["ai:use"]},
            headers=session_headers,
        ).json()
        token_id = created["info"]["token_id"]

        response = client.delete(f"/api/admin/tokens/{token_id}", headers=session_headers)
        assert response.status_code == 200
        assert client.get("/api/admin/tokens", headers=session_headers).json()["count"] == 0

    def test_revoke_unknown_is_404(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        response = client.delete("/api/admin/tokens/nope", headers=session_headers)
        assert response.status_code == 404

    def test_scopes_endpoint_lists_vocabulary(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/admin/tokens/scopes", headers=session_headers)
        assert response.status_code == 200
        names = {s["name"] for s in response.json()["scopes"]}
        assert "notes:write" in names
        assert "admin:*" in names


class TestScopeEnforcement:
    def _mint(
        self, client: TestClient, session_headers: dict[str, str], scopes: list[str]
    ) -> str:
        body = client.post(
            "/api/admin/tokens",
            json={"name": "t", "scopes": scopes},
            headers=session_headers,
        ).json()
        return body["token"]

    def test_scoped_token_allowed_on_its_scope(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        token = self._mint(client, session_headers, ["notes:write"])
        assert client.post("/probe/notes", headers=_bearer(token)).status_code == 200

    def test_scoped_token_rejected_off_scope(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        token = self._mint(client, session_headers, ["notes:write"])
        assert client.post("/probe/library", headers=_bearer(token)).status_code == 403

    def test_admin_wildcard_satisfies_everything(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        token = self._mint(client, session_headers, ["admin:*"])
        assert client.post("/probe/notes", headers=_bearer(token)).status_code == 200
        assert client.post("/probe/library", headers=_bearer(token)).status_code == 200

    def test_passkey_session_satisfies_scope(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        assert client.post("/probe/notes", headers=session_headers).status_code == 200

    def test_expired_token_rejected(
        self, client: TestClient, session_headers: dict[str, str], adapter: FakeNeo4jAdapter
    ) -> None:
        token = self._mint(client, session_headers, ["notes:write"])
        # Force expiry in the store
        adapter.tokens[0]["expires_at"] = time.time() - 1
        response = client.post("/probe/notes", headers=_bearer(token))
        assert response.status_code == 401

    def test_unknown_mgd_token_is_403_and_counts(
        self, client: TestClient, adapter: FakeNeo4jAdapter
    ) -> None:
        response = client.post("/probe/notes", headers=_bearer("mgd_not-a-real-token"))
        assert response.status_code == 403

    def test_revoked_token_stops_working(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        created = client.post(
            "/api/admin/tokens",
            json={"name": "t", "scopes": ["notes:write"]},
            headers=session_headers,
        ).json()
        token = created["token"]
        assert client.post("/probe/notes", headers=_bearer(token)).status_code == 200

        client.delete(f"/api/admin/tokens/{created['info']['token_id']}", headers=session_headers)
        assert client.post("/probe/notes", headers=_bearer(token)).status_code == 403


class TestFullAdminGate:
    """verify_admin (AdminUser) via the token-management endpoints."""

    def test_admin_wildcard_token_can_manage_tokens(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        """An admin:* token is full admin - it may even mint/list other tokens."""
        admin_token = client.post(
            "/api/admin/tokens",
            json={"name": "root", "scopes": ["admin:*"]},
            headers=session_headers,
        ).json()["token"]

        response = client.get("/api/admin/tokens", headers=_bearer(admin_token))
        assert response.status_code == 200

    def test_narrow_token_cannot_manage_tokens(
        self, client: TestClient, session_headers: dict[str, str]
    ) -> None:
        """A notes:write token cannot escalate by listing/minting tokens."""
        narrow = client.post(
            "/api/admin/tokens",
            json={"name": "narrow", "scopes": ["notes:write"]},
            headers=session_headers,
        ).json()["token"]

        assert client.get("/api/admin/tokens", headers=_bearer(narrow)).status_code == 403


class TestDevTokenAuth:
    """#291: the static token acts as full admin only in local dev."""

    def test_static_token_full_admin_when_dev_enabled(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "admin_token", TEST_ADMIN_TOKEN)
        monkeypatch.setattr(settings, "environment", "development")
        monkeypatch.setattr(settings, "allow_token_auth", True)

        response = client.get("/api/admin/tokens", headers=_bearer(TEST_ADMIN_TOKEN))
        assert response.status_code == 200

    def test_static_token_rejected_when_not_dev(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "admin_token", TEST_ADMIN_TOKEN)
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "allow_token_auth", True)

        response = client.get("/api/admin/tokens", headers=_bearer(TEST_ADMIN_TOKEN))
        assert response.status_code == 403

    def test_static_token_rejected_when_flag_off(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        settings = get_settings()
        monkeypatch.setattr(settings, "admin_token", TEST_ADMIN_TOKEN)
        monkeypatch.setattr(settings, "environment", "development")
        monkeypatch.setattr(settings, "allow_token_auth", False)

        response = client.get("/api/admin/tokens", headers=_bearer(TEST_ADMIN_TOKEN))
        assert response.status_code == 403
