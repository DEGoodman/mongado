"""On-demand logical backup of the Neo4j database (#267).

Writes the same zero-downtime JSON export that ``POST /api/admin/backup``
produces, but as a CLI so the deploy workflow can create pre/post-deploy
snapshots over SSH instead of an authenticated HTTP call. This removes the
deploy's dependency on ``ADMIN_TOKEN`` -- CI authenticates to the droplet with
its SSH key, and the backup no longer needs an admin credential at all.

Run inside the backend container:
    docker compose exec -T backend python -m scripts.backup_export

Exit status:
    0  backup written (path printed on the last line)
    1  Neo4j unavailable or the export/write failed
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from adapters.neo4j import get_neo4j_adapter

logger = logging.getLogger(__name__)


def _backup_dir() -> Path:
    """Resolve the backup directory.

    Honours ``BACKUP_DIR`` (set in docker-compose.prod.yml to
    ``/var/mongado-backups``) so the CLI, the nightly cron, and the API endpoint
    all write to the same place; falls back to the endpoint's convention when it
    is unset.
    """
    env_dir = os.getenv("BACKUP_DIR")
    if env_dir:
        return Path(env_dir)
    if "prod" in os.getenv("COMPOSE_FILE", "docker-compose.yml"):
        return Path("/var/mongado-backups")
    return Path("/app").parent / "backups"


def create_backup() -> Path:
    """Export the database to a timestamped JSON file and return its path.

    Raises:
        RuntimeError: If Neo4j is unavailable.
    """
    adapter = get_neo4j_adapter()
    if not adapter.is_available():
        raise RuntimeError("Neo4j not available - cannot create backup")

    export_data = adapter.export_database()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = _backup_dir() / f"neo4j_backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)
    backup_file = backup_path / "backup.json"
    with open(backup_file, "w") as f:
        json.dump(export_data, f, indent=2)

    metadata = export_data.get("metadata", {})
    logger.info(
        "Backup created: %s (%d notes, %d relationships, %d bytes)",
        backup_path.name,
        metadata.get("note_count", 0),
        metadata.get("relationship_count", 0),
        backup_file.stat().st_size,
    )
    return backup_file


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        backup_file = create_backup()
    except Exception as e:  # noqa: BLE001 - CLI boundary: report and exit non-zero
        logger.error("Backup failed: %s", e)
        return 1
    # Last line is the path so the caller can capture it
    print(backup_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
