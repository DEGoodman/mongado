"""Admin API endpoints for system management.

Provides administrative endpoints for:
- Backup management (Neo4j database backups)
- Embedding synchronization
- System health checks
"""

import logging
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def create_admin_router() -> APIRouter:
    """Create admin router with system management endpoints.

    Note: These endpoints should be protected with authentication in production.
    """

    @router.post("/backup")
    async def trigger_backup() -> dict[str, Any]:
        """Trigger a Neo4j database backup.

        Runs the backup script which:
        - Only creates backup if data has changed (hash-based detection)
        - Compresses and stores in /var/mongado-backups
        - Maintains retention policy (14 backups or 30 days)

        Note: This endpoint must be called from the host, not from inside a container.
        Use: curl -X POST https://api.mongado.com/api/admin/backup

        Returns:
            dict with backup status and details
        """
        try:
            logger.info("Triggering Neo4j backup via API")

            # Run backup script in neo4j container using docker compose
            # This command works from the host or when docker socket is mounted
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "neo4j",
                    "bash",
                    "-c",
                    "/scripts/backup_neo4j.sh",
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd="/opt/mongado",  # Production path (will fail gracefully in dev)
            )

            if result.returncode == 0:
                logger.info("Backup completed successfully")
                return {
                    "status": "success",
                    "message": "Backup completed",
                    "output": result.stdout,
                }
            else:
                logger.error("Backup failed: %s", result.stderr)
                raise HTTPException(
                    status_code=500,
                    detail=f"Backup failed: {result.stderr}",
                )

        except subprocess.TimeoutExpired as e:
            logger.error("Backup timed out after 5 minutes")
            raise HTTPException(
                status_code=500,
                detail="Backup timed out",
            ) from e
        except FileNotFoundError as e:
            # Docker not available (running inside container)
            logger.warning("Docker not available - backup must be triggered from host")
            raise HTTPException(
                status_code=503,
                detail="Backup unavailable: must be called from host, not from inside container. "
                "Use: ssh root@host 'curl -X POST http://localhost:8000/api/admin/backup'",
            ) from e
        except Exception as e:
            logger.error("Backup error: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Backup error: {str(e)}",
            ) from e

    @router.get("/backup/status")
    async def backup_status() -> dict[str, Any]:
        """Get backup status and list recent backups.

        Returns:
            dict with backup directory info and recent backups
        """
        try:
            # List backups in directory
            result = subprocess.run(
                ["sh", "-c", "ls -lht /var/mongado-backups/neo4j_backup_*.tar.gz 2>/dev/null | head -10"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout.strip():
                backups = result.stdout.strip().split('\n')
                return {
                    "status": "ok",
                    "backup_count": len(backups),
                    "recent_backups": backups,
                }
            else:
                return {
                    "status": "no_backups",
                    "message": "No backups found",
                    "backup_count": 0,
                }

        except Exception as e:
            logger.error("Error checking backup status: %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Error checking backup status: {str(e)}",
            ) from e

    return router
