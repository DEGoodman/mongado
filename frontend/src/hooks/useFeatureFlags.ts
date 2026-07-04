"use client";

import { useEffect, useSyncExternalStore } from "react";
import { config } from "@/lib/config";
import { logger } from "@/lib/logger";

const flagsLogger = logger.withContext("FeatureFlags");

export interface FeatureFlags {
  llmFeaturesEnabled: boolean;
  loaded: boolean;
}

/**
 * Module-level store so all components share one fetch of the runtime
 * feature flags (from the backend status endpoint). Flags are controlled
 * at runtime via the /admin page, not build-time env vars.
 */
let flags: FeatureFlags = { llmFeaturesEnabled: false, loaded: false };
let fetchStarted = false;
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot(): FeatureFlags {
  return flags;
}

function setFlags(next: FeatureFlags): void {
  flags = next;
  listeners.forEach((listener) => listener());
}

async function fetchFlags(): Promise<void> {
  try {
    const response = await fetch(`${config.apiUrl}/`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Status endpoint returned ${response.status}`);
    }
    const status = await response.json();
    setFlags({
      llmFeaturesEnabled: status.llm_features_enabled === true,
      loaded: true,
    });
  } catch (error) {
    flagsLogger.error("Failed to fetch feature flags, defaulting to disabled:", error);
    setFlags({ llmFeaturesEnabled: false, loaded: true });
  }
}

/**
 * Apply a flag value directly to the store (from an authoritative source,
 * e.g. the response of an admin PUT). Backend flag names map to store fields.
 */
export function applyFeatureFlag(name: string, enabled: boolean): void {
  if (name === "llm_features") {
    setFlags({ ...flags, llmFeaturesEnabled: enabled, loaded: true });
  }
}

/**
 * React hook exposing runtime feature flags.
 *
 * Flags default to disabled until the first fetch resolves; check `loaded`
 * to distinguish "disabled" from "still loading" when needed.
 */
export function useFeatureFlags(): FeatureFlags {
  // Start the fetch after mount, not during render: if it resolved before
  // hydration finished, the client tree would no longer match the server
  // HTML (hydration error on e.g. the AIButton).
  useEffect(() => {
    if (!fetchStarted) {
      fetchStarted = true;
      void fetchFlags();
    }
  }, []);
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}
