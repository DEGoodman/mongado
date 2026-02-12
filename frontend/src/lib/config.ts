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
   * Master switch for LLM/AI features
   * Default: false (off to save resources in production)
   * Set to "true" to enable AI features (Q&A, semantic search, suggestions)
   */
  llmFeaturesEnabled: process.env.NEXT_PUBLIC_LLM_FEATURES_ENABLED === "true",

  /**
   * Allow unauthenticated users to use AI features
   * Default: true (allows visitors to try AI suggestions)
   * Set to "false" to restrict AI features to authenticated users only
   *
   * Use case: Emergency kill switch if AI features are causing performance issues
   */
  allowUnauthenticatedAI: process.env.NEXT_PUBLIC_ALLOW_UNAUTHENTICATED_AI !== "false",
} as const;
