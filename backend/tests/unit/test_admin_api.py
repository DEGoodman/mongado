"""Unit tests for admin API endpoints (backup management)."""

import os
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

    @patch("routers.admin.subprocess.run")
    @patch("routers.admin.Path.glob")
    @patch("routers.admin.Path.exists")
    def test_list_backups_success(
        self,
        mock_exists: Mock,
        mock_glob: Mock,
        mock_subprocess: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test successfully listing backups."""
        mock_exists.return_value = True

        # Mock backup directories
        backup1 = MagicMock()
        backup1.name = "neo4j_backup_20241201_120000"
        backup1.is_dir.return_value = True

        backup2 = MagicMock()
        backup2.name = "neo4j_backup_20241130_100000"
        backup2.is_dir.return_value = True

        mock_glob.return_value = [backup1, backup2]

        # Mock du -sh output
        mock_result = MagicMock()
        mock_result.stdout = "2.3M\t/path/to/backup"
        mock_subprocess.return_value = mock_result

        response = client.get("/api/admin/backups", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["backups"]) == 2

        # Check that backups are sorted by timestamp (newest first)
        assert data["backups"][0]["filename"] == "neo4j_backup_20241201_120000"
        assert data["backups"][1]["filename"] == "neo4j_backup_20241130_100000"
        assert data["backups"][0]["size"] == "2.3M"


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

    @patch("routers.admin.Path.exists")
    def test_create_backup_script_not_found(
        self,
        mock_exists: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test backup fails when script doesn't exist."""
        mock_exists.return_value = False

        response = client.post("/api/admin/backup", headers=admin_headers)
        assert response.status_code == 500
        assert "Backup script not found" in response.json()["detail"]

    @patch("routers.admin.subprocess.run")
    @patch("routers.admin.Path.exists")
    def test_create_backup_success(
        self,
        mock_exists: Mock,
        mock_subprocess: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test successful backup creation."""
        mock_exists.return_value = True

        # Mock successful backup output
        mock_result = MagicMock()
        mock_result.stdout = """
[INFO] Backup: /backups/neo4j_backup_20241201_120000/
[INFO] Size: 2.3M
[INFO] Downtime: 45 seconds
[INFO] Notes backed up: 42
[INFO] === Backup Complete ===
"""
        mock_subprocess.return_value = mock_result

        response = client.post("/api/admin/backup", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["backup_file"] == "neo4j_backup_20241201_120000"
        assert data["downtime_seconds"] == 45
        assert data["note_count"] == 42

        # Verify subprocess was called with correct env vars
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args[1]
        assert call_kwargs["env"]["NON_INTERACTIVE"] == "true"
        assert call_kwargs["env"]["FORCE_BACKUP"] == "true"

    @patch("routers.admin.subprocess.run")
    @patch("routers.admin.Path.exists")
    def test_create_backup_timeout(
        self,
        mock_exists: Mock,
        mock_subprocess: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test backup timeout handling."""
        mock_exists.return_value = True
        mock_subprocess.side_effect = TimeoutError("Backup timed out")

        response = client.post("/api/admin/backup", headers=admin_headers)
        assert response.status_code == 500
        assert "Backup failed" in response.json()["detail"]

    @patch("routers.admin.subprocess.run")
    @patch("routers.admin.Path.exists")
    def test_create_backup_script_failure(
        self,
        mock_exists: Mock,
        mock_subprocess: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test handling of backup script failure."""
        mock_exists.return_value = True
        mock_subprocess.side_effect = Exception("Script failed")

        response = client.post("/api/admin/backup", headers=admin_headers)
        assert response.status_code == 500
        assert "Backup failed" in response.json()["detail"]


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

    @patch("routers.admin.Path.exists")
    def test_restore_backup_script_not_found(
        self,
        mock_exists: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test restore fails when script doesn't exist."""
        mock_exists.side_effect = [False]  # Script doesn't exist

        response = client.post("/api/admin/restore", json={}, headers=admin_headers)
        assert response.status_code == 500
        assert "Restore script not found" in response.json()["detail"]

    @patch("routers.admin.Path.exists")
    def test_restore_backup_not_found(
        self,
        mock_exists: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test restore fails when specified backup doesn't exist."""
        # Script exists, but backup doesn't
        mock_exists.side_effect = [True, False]

        response = client.post(
            "/api/admin/restore",
            json={"backup_file": "neo4j_backup_20241201_120000"},
            headers=admin_headers,
        )
        assert response.status_code == 404
        assert "Backup not found" in response.json()["detail"]

    @patch("routers.admin.subprocess.run")
    @patch("routers.admin.Path.exists")
    def test_restore_backup_latest_success(
        self,
        mock_exists: Mock,
        mock_subprocess: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test successful restore from latest backup."""
        mock_exists.return_value = True

        # Mock successful restore output
        mock_result = MagicMock()
        mock_result.stdout = """
[INFO] Using latest backup: neo4j_backup_20241201_120000
[INFO] Notes before restore: 10
[INFO] Downtime: 90 seconds
[INFO] Notes after: 42
[INFO] === Restore Complete ===
"""
        mock_subprocess.return_value = mock_result

        response = client.post("/api/admin/restore", json={}, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "neo4j_backup_20241201_120000" in data["restored_from"]
        assert data["downtime_seconds"] == 90
        assert data["notes_before"] == 10
        assert data["notes_after"] == 42

        # Verify subprocess was called with FORCE=true
        call_kwargs = mock_subprocess.call_args[1]
        assert call_kwargs["env"]["FORCE"] == "true"

    @patch("routers.admin.subprocess.run")
    @patch("routers.admin.Path.exists")
    def test_restore_backup_specific_success(
        self,
        mock_exists: Mock,
        mock_subprocess: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test successful restore from specific backup."""
        mock_exists.return_value = True

        # Mock successful restore output
        mock_result = MagicMock()
        mock_result.stdout = """
[INFO] Using specified backup: neo4j_backup_20241130_100000
[INFO] Notes before restore: 10
[INFO] Downtime: 85 seconds
[INFO] Notes after: 35
[INFO] === Restore Complete ===
"""
        mock_subprocess.return_value = mock_result

        response = client.post(
            "/api/admin/restore",
            json={"backup_file": "neo4j_backup_20241130_100000"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "neo4j_backup_20241130_100000" in data["restored_from"]

        # Verify subprocess was called with backup file argument
        call_args = mock_subprocess.call_args[0][0]
        assert "neo4j_backup_20241130_100000" in call_args

    @patch("routers.admin.subprocess.run")
    @patch("routers.admin.Path.exists")
    def test_restore_backup_timeout(
        self,
        mock_exists: Mock,
        mock_subprocess: Mock,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test restore timeout handling."""
        mock_exists.return_value = True
        mock_subprocess.side_effect = TimeoutError("Restore timed out")

        response = client.post("/api/admin/restore", json={}, headers=admin_headers)
        assert response.status_code == 500
        assert "Restore failed" in response.json()["detail"]

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

    def test_restore_backup_valid_filename_format(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
    ) -> None:
        """Test that valid filename format passes validation but fails on missing file."""
        with patch("routers.admin.Path.exists") as mock_exists:
            # Script exists, backup doesn't
            mock_exists.side_effect = [True, False]

            response = client.post(
                "/api/admin/restore",
                json={"backup_file": "neo4j_backup_20241201_120000"},
                headers=admin_headers,
            )
            # Should pass validation (422) but fail on not found (404)
            assert response.status_code == 404
            assert "Backup not found" in response.json()["detail"]


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
