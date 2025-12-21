"""Admin API routes for backup management and database operations."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from auth import AdminUser
from models import (
    BackupCreateResponse,
    BackupInfo,
    BackupListResponse,
    DatabaseHealthResponse,
    RestoreRequest,
    RestoreResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def create_admin_router(neo4j_adapter: Any) -> APIRouter:
    """Create admin router with dependencies injected.

    Args:
        neo4j_adapter: Neo4j adapter for database health checks

    Returns:
        Configured APIRouter with admin endpoints
    """

    def _get_backup_dir() -> Path:
        """Get backup directory based on environment.

        Returns:
            Path to backup directory
        """
        # Check if we're in testing mode (CI or local tests)
        if os.getenv("TESTING"):
            # Use a local directory relative to current working directory
            # This allows tests to run without Docker and without root permissions
            return Path.cwd() / "backups"

        # Check if we're in production (docker-compose.prod.yml)
        compose_file = os.getenv("COMPOSE_FILE", "docker-compose.yml")
        if "prod" in compose_file:
            return Path("/var/mongado-backups")
        else:
            # Development: In Docker, /app is mounted to backend/
            # Project root is parent of /app (backend)
            # So backups dir is at /app/../backups which is /backups when viewed from container
            # But since /app is mounted to backend/, we need to go up one more level
            # Actually, since we're in a container with /app mounted to ./backend,
            # the backups dir is at /app/../backups
            project_root = Path("/app").parent  # This gives us the project root from container
            return project_root / "backups"

    def _get_directory_size(path: Path) -> str:
        """Get human-readable size of a directory.

        Args:
            path: Directory path to measure

        Returns:
            Human-readable size string (e.g., "1.2M", "500K")
        """
        total_bytes = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        size: float = float(total_bytes)

        # Convert to human-readable format
        for unit in ["B", "K", "M", "G"]:
            if size < 1024:
                return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}{unit}"
            size /= 1024
        return f"{size:.1f}T"

    def _get_script_path(script_name: str) -> Path:
        """Get path to backup/restore script.

        Args:
            script_name: Name of the script file

        Returns:
            Path to script
        """
        return Path(__file__).parent.parent / "scripts" / script_name

    @router.get("/backups", response_model=BackupListResponse)
    async def list_backups(_admin: AdminUser) -> BackupListResponse:
        """List available backups with metadata.

        Requires admin authentication.

        Returns:
            List of backups sorted by timestamp (newest first)
        """
        backup_dir = _get_backup_dir()

        if not backup_dir.exists():
            logger.warning("Backup directory does not exist: %s", backup_dir)
            return BackupListResponse(backups=[], count=0)

        # Find all backup directories (neo4j_backup_YYYYMMDD_HHMMSS)
        backup_dirs = sorted(
            [d for d in backup_dir.glob("neo4j_backup_*") if d.is_dir()],
            key=lambda x: x.name,
            reverse=True,  # Newest first
        )

        backups: list[BackupInfo] = []
        for backup_path in backup_dirs:
            try:
                # Get size of backup directory using pure Python
                size = _get_directory_size(backup_path)

                # Parse timestamp from directory name (neo4j_backup_20241201_120000)
                timestamp_str = backup_path.name.replace("neo4j_backup_", "")
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").isoformat()

                backups.append(
                    BackupInfo(
                        filename=backup_path.name,
                        size=size,
                        timestamp=timestamp,
                        path=str(backup_path),
                    )
                )
            except Exception as e:
                logger.warning("Failed to get info for backup %s: %s", backup_path.name, e)
                continue

        return BackupListResponse(backups=backups, count=len(backups))

    @router.post("/backup", response_model=BackupCreateResponse)
    async def create_backup(_admin: AdminUser) -> BackupCreateResponse:
        """Create a new Neo4j backup using Python-based export.

        This is a logical backup that exports all notes and relationships
        as JSON. Unlike the shell-based backup, this does NOT require
        stopping Neo4j and causes zero downtime.

        Requires admin authentication.

        Returns:
            Backup creation status and metadata

        Raises:
            HTTPException: 500 if backup fails
        """
        logger.info("Admin triggered backup via API")

        try:
            # Export database using Python method (no Docker required)
            export_data = neo4j_adapter.export_database()

            # Create backup directory
            backup_dir = _get_backup_dir()
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Create timestamped backup file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"neo4j_backup_{timestamp}"
            backup_path = backup_dir / backup_name
            backup_path.mkdir(parents=True, exist_ok=True)

            # Save as JSON
            backup_file = backup_path / "backup.json"
            with open(backup_file, "w") as f:
                json.dump(export_data, f, indent=2)

            # Get backup size
            backup_size = backup_file.stat().st_size

            note_count = export_data.get("metadata", {}).get("note_count", 0)
            rel_count = export_data.get("metadata", {}).get("relationship_count", 0)

            logger.info(
                "Backup created: %s (%d notes, %d relationships, %d bytes)",
                backup_name,
                note_count,
                rel_count,
                backup_size,
            )

            return BackupCreateResponse(
                status="success",
                backup_file=backup_name,
                timestamp=datetime.now().isoformat(),
                downtime_seconds=0,  # No downtime with logical backup
                note_count=note_count,
            )

        except Exception as e:
            logger.error("Unexpected error during backup: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Backup failed: {str(e)}",
            ) from e

    @router.post("/restore", response_model=RestoreResponse)
    async def restore_backup(
        restore_req: RestoreRequest,
        _admin: AdminUser,
    ) -> RestoreResponse:
        """Restore Neo4j database from a backup using Python-based import.

        WARNING: This REPLACES the current database with the backup data.
        Unlike the shell-based restore, this does NOT require stopping Neo4j.

        If backup_file is not specified, restores from the latest backup.

        Requires admin authentication.

        Args:
            restore_req: Request specifying which backup to restore (None = latest)

        Returns:
            Restore status and metadata

        Raises:
            HTTPException: 404 if backup not found, 500 if restore fails
        """
        backup_dir = _get_backup_dir()

        # Determine which backup to restore
        if restore_req.backup_file:
            backup_path = backup_dir / restore_req.backup_file

            # Defense in depth: Resolve path and verify it's within backup_dir
            try:
                resolved_path = backup_path.resolve()
                resolved_backup_dir = backup_dir.resolve()
                if not str(resolved_path).startswith(str(resolved_backup_dir)):
                    logger.error(
                        "Path traversal attempt detected: %s not in %s",
                        resolved_path,
                        resolved_backup_dir,
                    )
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid backup file path",
                    )
            except (ValueError, OSError) as e:
                logger.error("Invalid backup path: %s", e)
                raise HTTPException(
                    status_code=400,
                    detail="Invalid backup file path",
                ) from e
        else:
            # Find latest backup
            backup_dirs = sorted(
                [d for d in backup_dir.glob("neo4j_backup_*") if d.is_dir()],
                key=lambda x: x.name,
                reverse=True,
            )
            if not backup_dirs:
                raise HTTPException(
                    status_code=404,
                    detail="No backups found",
                )
            backup_path = backup_dirs[0]

        # Check for backup.json (new format) or neo4j.dump (old format)
        json_backup = backup_path / "backup.json"
        if not json_backup.exists():
            # Check if this is an old-format backup (neo4j.dump)
            dump_backup = backup_path / "neo4j.dump"
            if dump_backup.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Backup {backup_path.name} uses old format (neo4j.dump). "
                    "Use the host-based restore script for old backups.",
                )
            raise HTTPException(
                status_code=404,
                detail=f"Backup not found: {backup_path.name}",
            )

        logger.info("Admin triggered restore via API: %s", backup_path.name)

        try:
            # Load backup data
            with open(json_backup) as f:
                backup_data = json.load(f)

            # Import database using Python method
            import_result = neo4j_adapter.import_database(backup_data, clear_existing=True)

            logger.info(
                "Restore completed: %s (before: %d, imported: %d notes, %d relationships)",
                backup_path.name,
                import_result["notes_before"],
                import_result["notes_imported"],
                import_result["relationships_imported"],
            )

            return RestoreResponse(
                status="success",
                restored_from=backup_path.name,
                timestamp=datetime.now().isoformat(),
                downtime_seconds=0,  # No downtime with logical restore
                notes_before=import_result["notes_before"],
                notes_after=import_result["notes_imported"],
            )

        except json.JSONDecodeError as e:
            logger.error("Invalid backup file format: %s", e)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid backup file format: {str(e)}",
            ) from e
        except Exception as e:
            logger.error("Unexpected error during restore: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Restore failed: {str(e)}",
            ) from e

    @router.get("/health/database", response_model=DatabaseHealthResponse)
    async def database_health() -> DatabaseHealthResponse:
        """Check database health and backup status.

        This endpoint does NOT require authentication as it's used for monitoring.

        Returns:
            Database health status including:
            - Note count
            - Number of available backups
            - Last backup timestamp
            - Whether restore is recommended
        """
        backup_dir = _get_backup_dir()

        # Check Neo4j availability
        neo4j_available = neo4j_adapter.is_available()

        # Get note count if Neo4j is available
        notes_count = 0
        if neo4j_available:
            try:
                notes_count = neo4j_adapter.get_note_count()
            except Exception as e:
                logger.warning("Failed to get note count: %s", e)

        # Count available backups
        backups_available = 0
        last_backup: str | None = None
        if backup_dir.exists():
            backup_dirs = sorted(
                [d for d in backup_dir.glob("neo4j_backup_*") if d.is_dir()],
                key=lambda x: x.name,
                reverse=True,
            )
            backups_available = len(backup_dirs)

            # Get last backup timestamp
            if backup_dirs:
                try:
                    timestamp_str = backup_dirs[0].name.replace("neo4j_backup_", "")
                    last_backup = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").isoformat()
                except Exception as e:
                    logger.warning("Failed to parse backup timestamp: %s", e)

        # Determine if restore is needed
        # Criteria: Neo4j unavailable OR note count is 0 but backups exist
        needs_restore = (not neo4j_available and backups_available > 0) or (
            neo4j_available and notes_count == 0 and backups_available > 0
        )

        # Determine overall status
        if not neo4j_available:
            status = "unhealthy"
        elif needs_restore:
            status = "degraded"
        else:
            status = "healthy"

        return DatabaseHealthResponse(
            status=status,
            notes_count=notes_count,
            backups_available=backups_available,
            needs_restore=needs_restore,
            last_backup=last_backup,
            neo4j_available=neo4j_available,
        )

    return router
