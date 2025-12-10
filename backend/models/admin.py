"""Pydantic models for admin endpoints (backup management)."""

import re

from pydantic import BaseModel, Field, field_validator


class BackupInfo(BaseModel):
    """Information about a single backup."""

    filename: str = Field(..., description="Backup filename (e.g., neo4j_backup_20241201_120000)")
    size: str = Field(..., description="Human-readable size (e.g., '2.3M')")
    timestamp: str = Field(..., description="ISO 8601 timestamp of backup creation")
    path: str = Field(..., description="Full path to backup directory")


class BackupListResponse(BaseModel):
    """Response for listing available backups."""

    backups: list[BackupInfo] = Field(..., description="List of available backups")
    count: int = Field(..., description="Total number of backups")


class BackupCreateResponse(BaseModel):
    """Response for creating a new backup."""

    status: str = Field(..., description="Status message")
    backup_file: str = Field(..., description="Name of created backup")
    timestamp: str = Field(..., description="ISO 8601 timestamp of backup creation")
    downtime_seconds: int | None = Field(None, description="Actual downtime in seconds")
    note_count: int | None = Field(None, description="Number of notes backed up")


class RestoreRequest(BaseModel):
    """Request to restore from a backup."""

    backup_file: str | None = Field(
        None,
        description="Backup filename to restore (None = latest backup)",
        examples=["neo4j_backup_20241201_120000"],
    )

    @field_validator("backup_file")
    @classmethod
    def validate_backup_file(cls, v: str | None) -> str | None:
        """Validate backup filename to prevent path traversal attacks.

        Args:
            v: Backup filename to validate

        Returns:
            Validated filename

        Raises:
            ValueError: If filename contains invalid characters or path separators
        """
        if v is None:
            return v

        # Must match pattern: neo4j_backup_YYYYMMDD_HHMMSS
        # Only allow alphanumeric, underscore, and hyphen to prevent path traversal
        if not re.match(r"^neo4j_backup_\d{8}_\d{6}$", v):
            raise ValueError(
                "Invalid backup filename format. Expected: neo4j_backup_YYYYMMDD_HHMMSS"
            )

        # Explicitly check for path traversal attempts
        if "/" in v or "\\" in v or ".." in v:
            raise ValueError("Backup filename must not contain path separators")

        return v


class RestoreResponse(BaseModel):
    """Response for restoring from a backup."""

    status: str = Field(..., description="Status message")
    restored_from: str = Field(..., description="Name of backup that was restored")
    timestamp: str = Field(..., description="ISO 8601 timestamp of restore completion")
    downtime_seconds: int | None = Field(None, description="Actual downtime in seconds")
    notes_before: int | None = Field(None, description="Note count before restore")
    notes_after: int | None = Field(None, description="Note count after restore")


class DatabaseHealthResponse(BaseModel):
    """Response for database health check."""

    status: str = Field(..., description="Overall status: 'healthy', 'degraded', or 'unhealthy'")
    notes_count: int = Field(..., description="Number of notes in database")
    backups_available: int = Field(..., description="Number of available backups")
    needs_restore: bool = Field(..., description="Whether database appears to need restore")
    last_backup: str | None = Field(None, description="Timestamp of last backup (ISO 8601)")
    neo4j_available: bool = Field(..., description="Whether Neo4j connection is available")
