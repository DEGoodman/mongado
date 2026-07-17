"""Tests for POST /api/admin/cleanup-uploads (#224)."""

import os
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

os.environ["TESTING"] = "1"

import main
from config import get_settings
from dependencies import get_neo4j, get_notes
from main import _find_referenced_uploads, app

TEST_ADMIN_TOKEN = "test-admin-token-for-ci"


@pytest.fixture
def admin_headers() -> dict[str, str]:
    settings = get_settings()
    token = settings.admin_token or TEST_ADMIN_TOKEN
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def upload_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the app's upload dir at a temp directory."""
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(main, "UPLOAD_DIR", uploads)
    return uploads


def _make_file(directory: Path, name: str, age_days: float) -> Path:
    path = directory / name
    path.write_bytes(b"x" * 100)
    stamp = time.time() - age_days * 86400
    os.utime(path, (stamp, stamp))
    return path


@pytest.fixture
def cleanup_client(upload_dir: Path) -> Generator[TestClient]:
    """Client with Neo4j available and one note referencing old-referenced.webp."""
    neo4j = MagicMock()
    neo4j.is_available.return_value = True

    notes = MagicMock()
    notes.list_notes.return_value = [
        {"id": "n1", "content": "See ![img](/uploads/old-referenced.webp) for details"},
    ]

    app.dependency_overrides[get_neo4j] = lambda: neo4j
    app.dependency_overrides[get_notes] = lambda: notes
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


class TestFindReferencedUploads:
    """Pure helper tests."""

    def test_extracts_filenames(self) -> None:
        texts = [
            "![a](/uploads/abc-123.webp) and http://x/uploads/def.jpg",
            "no references here",
        ]
        assert _find_referenced_uploads(texts) == {"abc-123.webp", "def.jpg"}

    def test_empty(self) -> None:
        assert _find_referenced_uploads([]) == set()


class TestCleanupUploads:
    def test_requires_auth(self, cleanup_client: TestClient) -> None:
        response = cleanup_client.post("/api/admin/cleanup-uploads")
        assert response.status_code == 401

    def test_deletes_only_old_unreferenced(
        self,
        cleanup_client: TestClient,
        upload_dir: Path,
        admin_headers: dict[str, str],
    ) -> None:
        old_unreferenced = _make_file(upload_dir, "old-unreferenced.webp", age_days=30)
        old_referenced = _make_file(upload_dir, "old-referenced.webp", age_days=30)
        recent = _make_file(upload_dir, "recent.webp", age_days=1)

        response = cleanup_client.post("/api/admin/cleanup-uploads", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["removed_count"] == 1
        assert data["kept_referenced"] == 1
        assert data["kept_recent"] == 1
        assert data["freed_bytes"] == 100

        assert not old_unreferenced.exists()
        assert old_referenced.exists()
        assert recent.exists()

    def test_refuses_without_neo4j(
        self,
        upload_dir: Path,
        admin_headers: dict[str, str],
    ) -> None:
        """No deletions when note references can't be checked."""
        stale = _make_file(upload_dir, "stale.webp", age_days=30)

        neo4j = MagicMock()
        neo4j.is_available.return_value = False
        app.dependency_overrides[get_neo4j] = lambda: neo4j
        try:
            with TestClient(app) as client:
                response = client.post("/api/admin/cleanup-uploads", headers=admin_headers)
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["removed_count"] == 0
        assert stale.exists()
