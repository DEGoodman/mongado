"""Unit tests for runtime feature flags (service + admin API + gating)."""

import os
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Set testing mode before importing app modules
os.environ["TESTING"] = "1"

import feature_flags as feature_flags_module
from config import get_settings
from feature_flags import FeatureFlagService
from main import app

TEST_ADMIN_TOKEN = "test-admin-token-for-ci"


class MockNeo4jFlags:
    """Mock Neo4j adapter exposing only the feature-flag methods."""

    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.stored: dict[str, bool] = {}

    def get_feature_flags(self) -> dict[str, bool]:
        return dict(self.stored) if self.available else {}

    def set_feature_flag(self, name: str, enabled: bool) -> bool:
        if not self.available:
            return False
        self.stored[name] = enabled
        return True


@pytest.fixture
def mock_neo4j() -> MockNeo4jFlags:
    """Mock Neo4j adapter for flag persistence."""
    return MockNeo4jFlags()


@pytest.fixture
def flag_service(
    mock_neo4j: MockNeo4jFlags, monkeypatch: pytest.MonkeyPatch
) -> Generator[FeatureFlagService]:
    """Install a fresh flag service backed by the mock adapter as the global."""
    service = FeatureFlagService(mock_neo4j)  # type: ignore[arg-type]
    monkeypatch.setattr(feature_flags_module, "_service", service)
    yield service


@pytest.fixture
def client(flag_service: FeatureFlagService) -> TestClient:
    """Test client with the mock-backed flag service installed."""
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Admin authentication headers."""
    settings = get_settings()
    token = settings.admin_token or TEST_ADMIN_TOKEN
    return {"Authorization": f"Bearer {token}"}


class TestFeatureFlagService:
    """Tests for the FeatureFlagService (pure-ish logic over a mock adapter)."""

    def test_defaults_used_when_nothing_persisted(self, flag_service: FeatureFlagService) -> None:
        # conftest sets LLM_FEATURES_ENABLED=true, so the seed default is True
        assert flag_service.is_enabled("llm_features") is True

    def test_persisted_value_overrides_default(
        self, flag_service: FeatureFlagService, mock_neo4j: MockNeo4jFlags
    ) -> None:
        mock_neo4j.stored["llm_features"] = False
        flag_service.reset_cache()
        assert flag_service.is_enabled("llm_features") is False

    def test_unknown_flag_is_disabled(self, flag_service: FeatureFlagService) -> None:
        assert flag_service.is_enabled("nonexistent_flag") is False

    def test_set_flag_persists_and_updates_cache(
        self, flag_service: FeatureFlagService, mock_neo4j: MockNeo4jFlags
    ) -> None:
        persisted = flag_service.set_flag("llm_features", False)
        assert persisted is True
        assert mock_neo4j.stored["llm_features"] is False
        assert flag_service.is_enabled("llm_features") is False

    def test_set_unknown_flag_raises(self, flag_service: FeatureFlagService) -> None:
        with pytest.raises(KeyError):
            flag_service.set_flag("nonexistent_flag", True)

    def test_set_flag_without_neo4j_is_memory_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        unavailable = MockNeo4jFlags(available=False)
        service = FeatureFlagService(unavailable)  # type: ignore[arg-type]
        persisted = service.set_flag("llm_features", False)
        assert persisted is False
        assert service.is_enabled("llm_features") is False

    def test_other_workers_pick_up_changes_after_ttl(
        self, mock_neo4j: MockNeo4jFlags, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simulate two uvicorn workers sharing Neo4j but not memory."""
        worker_a = FeatureFlagService(mock_neo4j)  # type: ignore[arg-type]
        worker_b = FeatureFlagService(mock_neo4j)  # type: ignore[arg-type]

        # Both workers warm their caches with the default (True)
        assert worker_a.is_enabled("llm_features") is True
        assert worker_b.is_enabled("llm_features") is True

        # Admin toggle lands on worker A only
        worker_a.set_flag("llm_features", False)
        assert worker_a.is_enabled("llm_features") is False
        # Worker B still serves its cache within the TTL
        assert worker_b.is_enabled("llm_features") is True

        # After the TTL expires, worker B reloads from Neo4j
        import feature_flags as ff

        real_monotonic = ff.time.monotonic
        monkeypatch.setattr(
            ff.time,
            "monotonic",
            lambda: real_monotonic() + FeatureFlagService.CACHE_TTL_SECONDS + 1,
        )
        assert worker_b.is_enabled("llm_features") is False

    def test_set_flag_survives_neo4j_write_error(
        self, flag_service: FeatureFlagService, mock_neo4j: MockNeo4jFlags
    ) -> None:
        def boom(name: str, enabled: bool) -> bool:
            raise RuntimeError("transient write failure")

        mock_neo4j.set_feature_flag = boom  # type: ignore[method-assign]
        persisted = flag_service.set_flag("llm_features", False)
        assert persisted is False
        assert flag_service.is_enabled("llm_features") is False

    def test_ignores_persisted_unknown_flags(
        self, flag_service: FeatureFlagService, mock_neo4j: MockNeo4jFlags
    ) -> None:
        mock_neo4j.stored["removed_old_flag"] = True
        flag_service.reset_cache()
        assert "removed_old_flag" not in flag_service.all_flags()


class TestFeatureFlagsAPI:
    """Tests for GET/PUT /api/admin/feature-flags."""

    def test_list_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/admin/feature-flags")
        assert response.status_code == 401

    def test_update_requires_auth(self, client: TestClient) -> None:
        response = client.put("/api/admin/feature-flags/llm_features", json={"enabled": True})
        assert response.status_code == 401

    def test_list_flags(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        response = client.get("/api/admin/feature-flags", headers=admin_headers)
        assert response.status_code == 200
        flags = {f["name"]: f for f in response.json()["flags"]}
        assert "llm_features" in flags
        assert flags["llm_features"]["enabled"] is True
        assert flags["llm_features"]["description"]

    def test_list_flags_not_cached(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        response = client.get("/api/admin/feature-flags", headers=admin_headers)
        assert "no-store" in response.headers["Cache-Control"]

    def test_update_flag(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        mock_neo4j: MockNeo4jFlags,
    ) -> None:
        response = client.put(
            "/api/admin/feature-flags/llm_features",
            json={"enabled": False},
            headers=admin_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["flag"]["enabled"] is False
        assert body["persisted"] is True
        assert mock_neo4j.stored["llm_features"] is False

        # Reflected in subsequent list and public status
        response = client.get("/api/admin/feature-flags", headers=admin_headers)
        flags = {f["name"]: f for f in response.json()["flags"]}
        assert flags["llm_features"]["enabled"] is False

    def test_update_unknown_flag_404(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        response = client.put(
            "/api/admin/feature-flags/nonexistent",
            json={"enabled": True},
            headers=admin_headers,
        )
        assert response.status_code == 404


class TestRuntimeGating:
    """Tests that toggling the flag gates features without a restart."""

    def _disable_llm(self, flag_service: FeatureFlagService) -> None:
        flag_service.set_flag("llm_features", False)

    def test_status_reflects_flag(
        self, client: TestClient, flag_service: FeatureFlagService
    ) -> None:
        assert client.get("/").json()["llm_features_enabled"] is True
        self._disable_llm(flag_service)
        assert client.get("/").json()["llm_features_enabled"] is False

    def test_ai_endpoints_return_503_when_disabled(
        self, client: TestClient, flag_service: FeatureFlagService
    ) -> None:
        self._disable_llm(flag_service)
        response = client.post("/api/ask", json={"question": "What is SRE?"})
        assert response.status_code == 503
        assert "disabled" in response.json()["detail"]

    def test_semantic_search_falls_back_to_text_when_disabled(
        self,
        flag_service: FeatureFlagService,
        mock_ollama_available: Any,
        mock_notes_service: Any,
    ) -> None:
        from dependencies import get_notes, get_ollama

        self._disable_llm(flag_service)
        app.dependency_overrides[get_ollama] = lambda: mock_ollama_available
        app.dependency_overrides[get_notes] = lambda: mock_notes_service
        try:
            with TestClient(app) as client:
                response = client.post("/api/search", json={"query": "test", "semantic": True})
                assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_admin_sync_embeddings_blocked_when_disabled(
        self,
        client: TestClient,
        flag_service: FeatureFlagService,
        admin_headers: dict[str, str],
    ) -> None:
        self._disable_llm(flag_service)
        response = client.post("/api/admin/sync-embeddings", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is False
        assert "disabled" in body["message"]
