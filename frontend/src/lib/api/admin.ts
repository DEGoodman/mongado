/**
 * Admin API - feature flag management (requires admin token)
 */

import { apiGet, apiPut } from "./client";

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
