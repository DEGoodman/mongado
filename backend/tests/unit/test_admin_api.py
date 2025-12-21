"""Unit tests for admin API endpoints (backup management).

Note: These tests focus on authentication, validation, and error handling.
Deep integration testing of backup/restore functionality is done separately
since the neo4j_adapter is instantiated at module level in main.py.
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# Set testing mode before importing app modules
os.environ["TESTING"] = "1"

from config import get_settings
from main import app

# Test admin token constant
TEST_ADMIN_TOKEN = "test-admin-token-for-ci"


@pytest.fixture
def client() -> TestClient:
    """Get test client for API testing."""
    return TestClient(app)


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Get admin authentication headers for testing."""
    settings = get_settings()
    token = settings.admin_token or TEST_ADMIN_TOKEN
    return {"Authorization": f"Bearer {token}"}


class TestListBackups:
    """Tests for GET /api/admin/backups endpoint."""

    def test_list_backups_requires_auth(self, client: TestClient) -> None:
        """Test that listing backups requires authentication."""
        response = client.get("/api/admin/backups")
        assert response.status_code == 401
        assert "Authorization required" in response.json()["detail"]

    def test_list_backups_with_invalid_token(self, client: TestClient) -> None:
        """Test that invalid token is rejected."""
        response = client.get(
            "/api/admin/backups",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 403
        assert "Invalid token" in response.json()["detail"]

    @patch("routers.admin.Path.exists")
    def test_list_backups_no_backup_dir(
        self,
        mock_exists: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test listing backups when backup directory doesn't exist."""
        mock_exists.return_value = False

        response = client.get("/api/admin/backups", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["backups"] == []
        assert data["count"] == 0

    def test_list_backups_success(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test successfully listing backups."""
        with TemporaryDirectory() as temp_dir:
            # Create mock backup directories
            backup1_path = Path(temp_dir) / "neo4j_backup_20241201_120000"
            backup1_path.mkdir()
            (backup1_path / "backup.json").write_text('{"notes": []}')

            backup2_path = Path(temp_dir) / "neo4j_backup_20241130_100000"
            backup2_path.mkdir()
            (backup2_path / "backup.json").write_text('{"notes": []}')

            with (
                patch.object(Path, "exists", return_value=True),
                patch.object(Path, "glob") as mock_glob,
            ):
                mock_glob.return_value = [backup1_path, backup2_path]

                response = client.get("/api/admin/backups", headers=admin_headers)
                assert response.status_code == 200
                data = response.json()
                assert data["count"] == 2
                assert len(data["backups"]) == 2

                # Check that backups are sorted by timestamp (newest first)
                assert data["backups"][0]["filename"] == "neo4j_backup_20241201_120000"
                assert data["backups"][1]["filename"] == "neo4j_backup_20241130_100000"


class TestCreateBackup:
    """Tests for POST /api/admin/backup endpoint."""

    def test_create_backup_requires_auth(self, client: TestClient) -> None:
        """Test that creating backup requires authentication."""
        response = client.post("/api/admin/backup")
        assert response.status_code == 401

    def test_create_backup_with_invalid_token(self, client: TestClient) -> None:
        """Test that invalid token is rejected."""
        response = client.post(
            "/api/admin/backup",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 403

    def test_create_backup_returns_expected_response_structure(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test that backup endpoint returns expected response structure.

        This is an integration test - it uses the real Neo4j adapter.
        The response should have the expected fields even with test data.
        """
        # First check if Neo4j is available (health endpoint doesn't require auth)
        health_response = client.get("/api/admin/health/database")
        if not health_response.json().get("neo4j_available", False):
            pytest.skip("Neo4j not available - skipping backup integration test")

        response = client.post("/api/admin/backup", headers=admin_headers)
        # Should succeed (uses real adapter with test data)
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert data["status"] == "success"
        assert "backup_file" in data
        assert data["backup_file"].startswith("neo4j_backup_")
        assert "timestamp" in data
        assert "downtime_seconds" in data
        assert data["downtime_seconds"] == 0  # Python-based backup has no downtime
        assert "note_count" in data


class TestRestoreBackup:
    """Tests for POST /api/admin/restore endpoint."""

    def test_restore_backup_requires_auth(self, client: TestClient) -> None:
        """Test that restoring backup requires authentication."""
        response = client.post("/api/admin/restore", json={})
        assert response.status_code == 401

    def test_restore_backup_with_invalid_token(self, client: TestClient) -> None:
        """Test that invalid token is rejected."""
        response = client.post(
            "/api/admin/restore",
            json={},
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 403

    def test_restore_backup_no_backups_found(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test restore fails when no backups exist."""
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "glob", return_value=[]),
        ):
            response = client.post("/api/admin/restore", json={}, headers=admin_headers)
            assert response.status_code == 404
            assert "No backups found" in response.json()["detail"]

    def test_restore_backup_json_not_found(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test restore fails when backup.json doesn't exist."""
        with TemporaryDirectory() as temp_dir:
            # Create backup directory without backup.json
            backup_path = Path(temp_dir) / "neo4j_backup_20241201_120000"
            backup_path.mkdir()

            with patch.object(Path, "glob") as mock_glob:
                mock_glob.return_value = [backup_path]

                response = client.post("/api/admin/restore", json={}, headers=admin_headers)
                assert response.status_code == 404
                assert "Backup not found" in response.json()["detail"]

    def test_restore_backup_invalid_json(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test restore fails with invalid JSON backup file."""
        with TemporaryDirectory() as temp_dir:
            # Create mock backup with invalid JSON
            backup_path = Path(temp_dir) / "neo4j_backup_20241201_120000"
            backup_path.mkdir()
            (backup_path / "backup.json").write_text("invalid json {{{")

            with patch.object(Path, "glob") as mock_glob:
                mock_glob.return_value = [backup_path]

                response = client.post("/api/admin/restore", json={}, headers=admin_headers)
                assert response.status_code == 400
                assert "Invalid backup file format" in response.json()["detail"]

    def test_restore_backup_path_traversal_attempt(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test that path traversal attempts are rejected."""
        # Test various path traversal attempts
        traversal_attempts = [
            "../../../etc/passwd",
            "../../config.yml",
            "../backup",
            "backup/../../../etc/passwd",
            "backup/../../sensitive",
        ]

        for attempt in traversal_attempts:
            response = client.post(
                "/api/admin/restore",
                json={"backup_file": attempt},
                headers=admin_headers,
            )
            # Should be rejected by Pydantic validator with 422 (validation error)
            assert response.status_code == 422, f"Failed to reject: {attempt}"
            assert "value_error" in response.text or "validation" in response.text.lower()

    def test_restore_backup_invalid_filename_format(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test that invalid filename formats are rejected."""
        # Test various invalid formats that don't match the pattern
        # Note: We only validate pattern, not actual date values
        invalid_formats = [
            "invalid_backup",
            "neo4j_backup_",
            "neo4j_backup_2024",
            "backup.tar.gz",
            "../../backup",
            "/absolute/path/backup",
            "neo4j_backup_abc_def",  # Non-numeric
            "neo4j_backup_2024120_120000",  # Wrong date length
            "neo4j_backup_20241201_12000",  # Wrong time length
        ]

        for invalid_format in invalid_formats:
            response = client.post(
                "/api/admin/restore",
                json={"backup_file": invalid_format},
                headers=admin_headers,
            )
            # Should be rejected by Pydantic validator
            assert response.status_code == 422, f"Failed to reject: {invalid_format}"

    def test_restore_backup_old_format_rejected(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test that old-format backups (neo4j.dump) are rejected with helpful message."""
        with TemporaryDirectory() as temp_dir:
            # Create old-format backup with neo4j.dump (no backup.json)
            backup_path = Path(temp_dir) / "neo4j_backup_20241201_120000"
            backup_path.mkdir()
            (backup_path / "neo4j.dump").write_text("binary dump data")

            with patch.object(Path, "glob") as mock_glob:
                mock_glob.return_value = [backup_path]

                response = client.post("/api/admin/restore", json={}, headers=admin_headers)
                assert response.status_code == 400
                assert "old format" in response.json()["detail"]


class TestDatabaseHealth:
    """Tests for GET /api/admin/health/database endpoint."""

    def test_database_health_no_auth_required(self, client: TestClient) -> None:
        """Test that database health check doesn't require authentication."""
        response = client.get("/api/admin/health/database")
        assert response.status_code == 200
        assert "status" in response.json()

    @patch("routers.admin.Path.exists")
    def test_database_health_no_backups(
        self,
        mock_exists: Mock,
        client: TestClient,
    ) -> None:
        """Test database health when no backups exist."""
        mock_exists.return_value = False

        response = client.get("/api/admin/health/database")
        assert response.status_code == 200
        data = response.json()
        assert data["backups_available"] == 0
        assert "status" in data
        assert "notes_count" in data
        assert "needs_restore" in data
        assert "neo4j_available" in data

    @patch("routers.admin.Path.glob")
    @patch("routers.admin.Path.exists")
    def test_database_health_with_backups(
        self,
        mock_exists: Mock,
        mock_glob: Mock,
        client: TestClient,
    ) -> None:
        """Test database health with available backups."""
        mock_exists.return_value = True

        # Mock backup directories
        backup1 = MagicMock()
        backup1.name = "neo4j_backup_20241201_120000"
        backup1.is_dir.return_value = True

        backup2 = MagicMock()
        backup2.name = "neo4j_backup_20241130_100000"
        backup2.is_dir.return_value = True

        mock_glob.return_value = [backup1, backup2]

        response = client.get("/api/admin/health/database")
        assert response.status_code == 200
        data = response.json()
        assert data["backups_available"] == 2
        assert data["last_backup"] is not None
        assert "2024-12-01" in data["last_backup"]

    @patch("routers.admin.Path.glob")
    @patch("routers.admin.Path.exists")
    def test_database_health_degraded_state(
        self,
        mock_exists: Mock,
        mock_glob: Mock,
        client: TestClient,
    ) -> None:
        """Test database health in degraded state (0 notes but backups available)."""
        mock_exists.return_value = True

        # Mock backup directories
        backup = MagicMock()
        backup.name = "neo4j_backup_20241201_120000"
        backup.is_dir.return_value = True
        mock_glob.return_value = [backup]

        response = client.get("/api/admin/health/database")
        assert response.status_code == 200
        data = response.json()

        # If Neo4j is available but has 0 notes and backups exist, needs_restore should be True
        if data["neo4j_available"] and data["notes_count"] == 0:
            assert data["needs_restore"] is True
            assert data["status"] in ["degraded", "unhealthy"]
