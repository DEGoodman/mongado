"""Unit tests for the on-demand backup CLI (scripts/backup_export.py, #267).

The CLI replaces the deploy workflow's authenticated `POST /api/admin/backup`
call, so these cover the directory resolution, the export-to-file path, and the
exit codes the workflow relies on.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ["TESTING"] = "1"

from scripts import backup_export


class TestBackupDir:
    def test_honours_backup_dir_env(self, monkeypatch) -> None:
        monkeypatch.setenv("BACKUP_DIR", "/custom/backups")
        assert backup_export._backup_dir() == Path("/custom/backups")

    def test_prod_compose_defaults_to_var_mongado_backups(self, monkeypatch) -> None:
        monkeypatch.delenv("BACKUP_DIR", raising=False)
        monkeypatch.setenv("COMPOSE_FILE", "docker-compose.prod.yml")
        assert backup_export._backup_dir() == Path("/var/mongado-backups")

    def test_dev_default(self, monkeypatch) -> None:
        monkeypatch.delenv("BACKUP_DIR", raising=False)
        monkeypatch.delenv("COMPOSE_FILE", raising=False)
        assert backup_export._backup_dir() == Path("/app").parent / "backups"


class TestCreateBackup:
    def _fake_adapter(self) -> MagicMock:
        adapter = MagicMock()
        adapter.is_available.return_value = True
        adapter.export_database.return_value = {
            "notes": [{"id": "curious-elephant"}],
            "relationships": [],
            "metadata": {"note_count": 1, "relationship_count": 0},
        }
        return adapter

    def test_writes_json_and_returns_path(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
        with patch.object(backup_export, "get_neo4j_adapter", return_value=self._fake_adapter()):
            backup_file = backup_export.create_backup()

        assert backup_file.exists()
        assert backup_file.name == "backup.json"
        assert backup_file.parent.name.startswith("neo4j_backup_")
        written = json.loads(backup_file.read_text())
        assert written["metadata"]["note_count"] == 1

    def test_raises_when_neo4j_unavailable(self, monkeypatch) -> None:
        adapter = MagicMock()
        adapter.is_available.return_value = False
        with patch.object(backup_export, "get_neo4j_adapter", return_value=adapter):
            try:
                backup_export.create_backup()
            except RuntimeError as e:
                assert "not available" in str(e)
            else:
                raise AssertionError("expected RuntimeError when Neo4j is unavailable")


class TestMain:
    def test_returns_zero_on_success(self, tmp_path, monkeypatch, capsys) -> None:
        monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
        adapter = MagicMock()
        adapter.is_available.return_value = True
        adapter.export_database.return_value = {"notes": [], "relationships": [], "metadata": {}}
        with patch.object(backup_export, "get_neo4j_adapter", return_value=adapter):
            assert backup_export.main() == 0
        # Last line of stdout is the backup path, which the workflow can capture
        assert capsys.readouterr().out.strip().endswith("backup.json")

    def test_returns_one_on_failure(self, monkeypatch) -> None:
        adapter = MagicMock()
        adapter.is_available.return_value = False
        with patch.object(backup_export, "get_neo4j_adapter", return_value=adapter):
            assert backup_export.main() == 1
