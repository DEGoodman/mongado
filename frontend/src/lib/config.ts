/**
 * Frontend configuration
 * Centralizes all environment variables and feature flags
 */

export const config = {
  /**
   * Backend API URL
   */
  apiUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",

  /**
   * Allow unauthenticated users to use AI features
   * Default: true (allows visitors to try AI suggestions)
   * Set to "false" to restrict AI features to authenticated users only
   *
   * Use case: Emergency kill switch if AI features are causing performance issues
   */
  allowUnauthenticatedAI: process.env.NEXT_PUBLIC_ALLOW_UNAUTHENTICATED_AI !== "false",
} as const;
