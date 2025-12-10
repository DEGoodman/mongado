"""Admin API routes for backup management and database operations."""

import contextlib
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from auth import AdminUser, verify_admin
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

    def _get_script_path(script_name: str) -> Path:
        """Get path to backup/restore script.

        Args:
            script_name: Name of the script file

        Returns:
            Path to script
        """
        return Path(__file__).parent.parent / "scripts" / script_name

    @router.get("/backups", response_model=BackupListResponse)
    async def list_backups(_admin: AdminUser = Depends(verify_admin)) -> BackupListResponse:
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
                # Get size of backup directory
                size_result = subprocess.run(
                    ["du", "-sh", str(backup_path)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=True,
                )
                size = size_result.stdout.split()[0] if size_result.stdout else "unknown"

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
    async def create_backup(_admin: AdminUser = Depends(verify_admin)) -> BackupCreateResponse:
        """Trigger a new Neo4j backup.

        WARNING: This causes ~30-60 seconds of downtime as the Neo4j container
        is stopped during backup.

        Requires admin authentication.

        Returns:
            Backup creation status and metadata

        Raises:
            HTTPException: 500 if backup fails
        """
        script_path = _get_script_path("backup_neo4j.sh")

        if not script_path.exists():
            logger.error("Backup script not found: %s", script_path)
            raise HTTPException(
                status_code=500,
                detail=f"Backup script not found: {script_path}",
            )

        logger.info("Admin triggered backup via API")

        try:
            # Execute backup script with non-interactive mode
            env = os.environ.copy()
            env["NON_INTERACTIVE"] = "true"
            env["FORCE_BACKUP"] = "true"  # Force backup even if no changes detected

            result = subprocess.run(
                [str(script_path)],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                env=env,
                check=True,
            )

            # Parse backup information from script output
            output = result.stdout
            logger.info("Backup output: %s", output)

            # Extract backup filename from output (look for "Backup: neo4j_backup_...")
            backup_file = "unknown"
            for line in output.split("\n"):
                if "Backup:" in line and "neo4j_backup_" in line:
                    # Extract directory name
                    parts = line.split("/")
                    for part in parts:
                        if part.startswith("neo4j_backup_"):
                            backup_file = part.rstrip("/")
                            break
                    break

            # Extract downtime from output
            downtime = None
            for line in output.split("\n"):
                if "Downtime:" in line:
                    with contextlib.suppress(ValueError, IndexError):
                        downtime = int(line.split("Downtime:")[1].split("seconds")[0].strip())
                    break

            # Extract note count from output
            note_count = None
            for line in output.split("\n"):
                if "Notes backed up:" in line:
                    with contextlib.suppress(ValueError, IndexError):
                        note_count = int(line.split("Notes backed up:")[1].strip())
                    break

            return BackupCreateResponse(
                status="success",
                backup_file=backup_file,
                timestamp=datetime.now().isoformat(),
                downtime_seconds=downtime,
                note_count=note_count,
            )

        except subprocess.TimeoutExpired as e:
            logger.error("Backup script timed out after 5 minutes")
            raise HTTPException(
                status_code=500,
                detail="Backup timed out after 5 minutes",
            ) from e
        except subprocess.CalledProcessError as e:
            logger.error("Backup script failed: %s", e.stderr)
            raise HTTPException(
                status_code=500,
                detail=f"Backup failed: {e.stderr}",
            ) from e
        except Exception as e:
            logger.error("Unexpected error during backup: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Backup failed: {str(e)}",
            ) from e

    @router.post("/restore", response_model=RestoreResponse)
    async def restore_backup(
        restore_req: RestoreRequest,
        _admin: AdminUser = Depends(verify_admin),
    ) -> RestoreResponse:
        """Restore Neo4j database from a backup.

        WARNING: This causes ~1-2 minutes of downtime and REPLACES the current database.

        If backup_file is not specified, restores from the latest backup.

        Requires admin authentication.

        Args:
            restore_req: Request specifying which backup to restore (None = latest)

        Returns:
            Restore status and metadata

        Raises:
            HTTPException: 404 if backup not found, 500 if restore fails
        """
        script_path = _get_script_path("restore_neo4j.sh")

        if not script_path.exists():
            logger.error("Restore script not found: %s", script_path)
            raise HTTPException(
                status_code=500,
                detail=f"Restore script not found: {script_path}",
            )

        # If backup_file specified, verify it exists and is within backup directory
        if restore_req.backup_file:
            backup_dir = _get_backup_dir()
            backup_path = backup_dir / restore_req.backup_file

            # Defense in depth: Resolve path and verify it's within backup_dir
            # This prevents path traversal even if validator is bypassed
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

            if not backup_path.exists():
                logger.error("Backup not found: %s", backup_path)
                raise HTTPException(
                    status_code=404,
                    detail=f"Backup not found: {restore_req.backup_file}",
                )

        logger.info(
            "Admin triggered restore via API: %s",
            restore_req.backup_file or "latest",
        )

        try:
            # Execute restore script with forced mode
            env = os.environ.copy()
            env["FORCE"] = "true"  # Skip confirmation prompts

            # Build command with optional backup file argument
            cmd = [str(script_path)]
            if restore_req.backup_file:
                cmd.append(restore_req.backup_file)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                env=env,
                check=True,
            )

            # Parse restore information from script output
            output = result.stdout
            logger.info("Restore output: %s", output)

            # Extract backup filename from output
            restored_from = restore_req.backup_file or "latest"
            for line in output.split("\n"):
                if "Using" in line and "backup:" in line:
                    parts = line.split("backup:")
                    if len(parts) > 1:
                        restored_from = parts[1].strip()
                    break

            # Extract downtime from output
            downtime = None
            for line in output.split("\n"):
                if "Downtime:" in line:
                    with contextlib.suppress(ValueError, IndexError):
                        downtime = int(line.split("Downtime:")[1].split("seconds")[0].strip())
                    break

            # Extract note counts from output
            notes_before = None
            notes_after = None
            for line in output.split("\n"):
                if "Notes before restore:" in line or "Notes before:" in line:
                    try:
                        # Extract number after colon
                        parts = line.split(":")
                        if len(parts) > 1:
                            notes_before = int(parts[-1].strip())
                    except (ValueError, IndexError):
                        pass
                elif "Notes after:" in line:
                    try:
                        # Extract number after colon
                        parts = line.split(":")
                        if len(parts) > 1:
                            notes_after = int(parts[-1].strip())
                    except (ValueError, IndexError):
                        pass

            return RestoreResponse(
                status="success",
                restored_from=restored_from,
                timestamp=datetime.now().isoformat(),
                downtime_seconds=downtime,
                notes_before=notes_before,
                notes_after=notes_after,
            )

        except subprocess.TimeoutExpired as e:
            logger.error("Restore script timed out after 10 minutes")
            raise HTTPException(
                status_code=500,
                detail="Restore timed out after 10 minutes",
            ) from e
        except subprocess.CalledProcessError as e:
            logger.error("Restore script failed: %s", e.stderr)
            raise HTTPException(
                status_code=500,
                detail=f"Restore failed: {e.stderr}",
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
