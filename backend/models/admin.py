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


class UploadCleanupResponse(BaseModel):
    """Response for cleaning up stale unreferenced uploads."""

    success: bool = Field(..., description="Whether cleanup ran (False if refused)")
    message: str = Field(..., description="Human-readable outcome")
    removed_count: int = Field(0, description="Files deleted")
    freed_bytes: int = Field(0, description="Bytes reclaimed")
    kept_referenced: int = Field(0, description="Files kept because notes/articles reference them")
    kept_recent: int = Field(0, description="Files kept because they are newer than min_age_days")


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


class FeatureFlagInfo(BaseModel):
    """A single feature flag with its current state."""

    name: str = Field(..., description="Flag name (e.g., 'llm_features')")
    enabled: bool = Field(..., description="Whether the flag is currently enabled")
    description: str = Field(..., description="What the flag controls")


class FeatureFlagsResponse(BaseModel):
    """Response listing all feature flags."""

    flags: list[FeatureFlagInfo] = Field(..., description="All known feature flags")


class FeatureFlagUpdateRequest(BaseModel):
    """Request to update a feature flag."""

    enabled: bool = Field(..., description="New value for the flag")


class FeatureFlagUpdateResponse(BaseModel):
    """Response after updating a feature flag."""

    flag: FeatureFlagInfo = Field(..., description="The updated flag")
    persisted: bool = Field(
        ..., description="False if Neo4j was unavailable (value resets on restart)"
    )


class DatabaseHealthResponse(BaseModel):
    """Response for database health check."""

    status: str = Field(..., description="Overall status: 'healthy', 'degraded', or 'unhealthy'")
    notes_count: int = Field(..., description="Number of notes in database")
    backups_available: int = Field(..., description="Number of available backups")
    needs_restore: bool = Field(..., description="Whether database appears to need restore")
    last_backup: str | None = Field(None, description="Timestamp of last backup (ISO 8601)")
    neo4j_available: bool = Field(..., description="Whether Neo4j connection is available")
    backup_cron_last_run: str | None = Field(
        None, description="Timestamp of the last backup-cron run (ISO 8601, from heartbeat file)"
    )
    backup_cron_healthy: bool | None = Field(
        None,
        description="False if the backup cron has not run within 48h; None if no heartbeat exists",
    )
