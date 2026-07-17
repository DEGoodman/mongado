"""Tests for failed-admin-auth lockout (#225)."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ["TESTING"] = "1"

from auth import MAX_FAILED_ATTEMPTS, FailedAuthTracker, auth_tracker
from config import get_settings
from main import app

TEST_ADMIN_TOKEN = "test-admin-token-for-ci"


@pytest.fixture
def client() -> TestClient:
    """Test client (auth_tracker reset handled by the autouse conftest fixture)."""
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    settings = get_settings()
    token = settings.admin_token or TEST_ADMIN_TOKEN
    return {"Authorization": f"Bearer {token}"}


BAD_HEADERS = {"Authorization": "Bearer definitely-wrong-token"}


class TestFailedAuthTracker:
    """Unit tests for the tracker itself."""

    def test_not_locked_initially(self) -> None:
        tracker = FailedAuthTracker(max_attempts=3, lockout_seconds=60)
        assert tracker.is_locked("1.2.3.4") is False

    def test_locks_after_max_attempts(self) -> None:
        tracker = FailedAuthTracker(max_attempts=3, lockout_seconds=60)
        for _ in range(3):
            tracker.record_failure("1.2.3.4")
        assert tracker.is_locked("1.2.3.4") is True

    def test_below_threshold_not_locked(self) -> None:
        tracker = FailedAuthTracker(max_attempts=3, lockout_seconds=60)
        tracker.record_failure("1.2.3.4")
        tracker.record_failure("1.2.3.4")
        assert tracker.is_locked("1.2.3.4") is False

    def test_ips_are_independent(self) -> None:
        tracker = FailedAuthTracker(max_attempts=2, lockout_seconds=60)
        tracker.record_failure("1.1.1.1")
        tracker.record_failure("1.1.1.1")
        assert tracker.is_locked("1.1.1.1") is True
        assert tracker.is_locked("2.2.2.2") is False

    def test_success_clears_failures(self) -> None:
        tracker = FailedAuthTracker(max_attempts=3, lockout_seconds=60)
        tracker.record_failure("1.2.3.4")
        tracker.record_failure("1.2.3.4")
        tracker.record_success("1.2.3.4")
        # Two more failures should not lock (counter restarted)
        tracker.record_failure("1.2.3.4")
        tracker.record_failure("1.2.3.4")
        assert tracker.is_locked("1.2.3.4") is False

    def test_lockout_expires(self) -> None:
        tracker = FailedAuthTracker(max_attempts=2, lockout_seconds=0.0)
        tracker.record_failure("1.2.3.4")
        tracker.record_failure("1.2.3.4")
        # lockout_seconds=0 means the window has always already expired
        assert tracker.is_locked("1.2.3.4") is False

    def test_stale_window_resets_count(self) -> None:
        tracker = FailedAuthTracker(max_attempts=2, lockout_seconds=0.0)
        tracker.record_failure("1.2.3.4")
        # Window expired -> next failure starts a fresh count at 1
        assert tracker.record_failure("1.2.3.4") == 1


class TestAuthLockoutEndpoint:
    """Integration tests through an admin endpoint."""

    def test_invalid_attempts_then_locked(self, client: TestClient) -> None:
        """After MAX_FAILED_ATTEMPTS invalid tokens, the IP gets 429."""
        for _ in range(MAX_FAILED_ATTEMPTS):
            response = client.get("/api/admin/backups", headers=BAD_HEADERS)
            assert response.status_code == 403

        response = client.get("/api/admin/backups", headers=BAD_HEADERS)
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    def test_lockout_applies_even_with_correct_token(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """A locked-out IP is rejected even if it finally sends the right token."""
        for _ in range(MAX_FAILED_ATTEMPTS):
            client.get("/api/admin/backups", headers=BAD_HEADERS)

        response = client.get("/api/admin/backups", headers=admin_headers)
        assert response.status_code == 429

    def test_missing_header_does_not_count(self, client: TestClient) -> None:
        """401s (no token guessed) never contribute to the lockout."""
        for _ in range(MAX_FAILED_ATTEMPTS + 2):
            response = client.get("/api/admin/backups")
            assert response.status_code == 401

        # Still not locked: an invalid token gets 403, not 429
        response = client.get("/api/admin/backups", headers=BAD_HEADERS)
        assert response.status_code == 403

    def test_success_resets_counter(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        """A successful auth clears the failure history for that IP."""
        for _ in range(MAX_FAILED_ATTEMPTS - 1):
            client.get("/api/admin/backups", headers=BAD_HEADERS)

        response = client.get("/api/admin/backups", headers=admin_headers)
        assert response.status_code == 200

        # Counter restarted: more failures allowed before lockout
        for _ in range(MAX_FAILED_ATTEMPTS - 1):
            response = client.get("/api/admin/backups", headers=BAD_HEADERS)
            assert response.status_code == 403

    def test_tracker_reset_between_tests(self, client: TestClient) -> None:
        """Sanity check that the autouse conftest fixture isolates tests."""
        assert auth_tracker.is_locked("testclient") is False
        response = client.get("/api/admin/backups", headers=BAD_HEADERS)
        assert response.status_code == 403
