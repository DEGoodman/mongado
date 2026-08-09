/**
 * Scoped API token management (#300).
 *
 * Full admins mint, list, and revoke `mgd_`-prefixed bearer tokens for
 * programmatic API use. The plaintext is returned exactly once, at creation.
 */

import { apiDelete, apiGet, apiPost } from "./client";

export interface ApiScope {
  name: string;
  description: string;
}

export interface ApiTokenInfo {
  token_id: string;
  name: string;
  scopes: string[];
  created_at: number;
  expires_at: number | null;
  last_used_at: number | null;
}

export interface ApiTokenCreateResponse {
  /** The plaintext bearer token - shown only at creation. */
  token: string;
  info: ApiTokenInfo;
}

interface ApiScopesResponse {
  scopes: ApiScope[];
}

interface ApiTokensListResponse {
  tokens: ApiTokenInfo[];
  count: number;
}

export async function getApiScopes(): Promise<ApiScope[]> {
  const response = await apiGet<ApiScopesResponse>("/api/admin/tokens/scopes");
  return response.scopes;
}

export async function listApiTokens(): Promise<ApiTokenInfo[]> {
  const response = await apiGet<ApiTokensListResponse>("/api/admin/tokens");
  return response.tokens;
}

export async function createApiToken(
  name: string,
  scopes: string[],
  expiresInDays: number | null
): Promise<ApiTokenCreateResponse> {
  return apiPost<ApiTokenCreateResponse>("/api/admin/tokens", {
    name,
    scopes,
    expires_in_days: expiresInDays,
  });
}

export async function deleteApiToken(tokenId: string): Promise<void> {
  await apiDelete(`/api/admin/tokens/${encodeURIComponent(tokenId)}`);
}
