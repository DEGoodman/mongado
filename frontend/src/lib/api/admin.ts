/**
 * Admin API - feature flag management (requires admin token)
 */

import { apiGet, apiPost, apiPut } from "./client";

export interface FeatureFlag {
  name: string;
  enabled: boolean;
  description: string;
}

interface FeatureFlagsResponse {
  flags: FeatureFlag[];
}

export interface FeatureFlagUpdateResponse {
  flag: FeatureFlag;
  persisted: boolean;
}

export async function getFeatureFlags(): Promise<FeatureFlag[]> {
  const response = await apiGet<FeatureFlagsResponse>("/api/admin/feature-flags");
  return response.flags;
}

export async function updateFeatureFlag(
  name: string,
  enabled: boolean
): Promise<FeatureFlagUpdateResponse> {
  return apiPut<FeatureFlagUpdateResponse>(`/api/admin/feature-flags/${name}`, { enabled });
}

export interface DatabaseHealth {
  status: "healthy" | "degraded" | "unhealthy";
  notes_count: number;
  backups_available: number;
  needs_restore: boolean;
  last_backup: string | null;
  neo4j_available: boolean;
  backup_cron_last_run: string | null;
  backup_cron_healthy: boolean | null;
}

export interface BackupCreateResponse {
  status: string;
  backup_file: string;
  timestamp: string;
  downtime_seconds: number;
  note_count: number;
}

export async function getDatabaseHealth(): Promise<DatabaseHealth> {
  return apiGet<DatabaseHealth>("/api/admin/health/database");
}

export async function createBackup(): Promise<BackupCreateResponse> {
  return apiPost<BackupCreateResponse>("/api/admin/backup", {});
}
