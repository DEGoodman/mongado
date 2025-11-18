/**
 * User preferences hook for global settings (persisted to localStorage)
 *
 * This hook manages user-level preferences that persist across sessions,
 * such as AI mode settings that should apply globally rather than per-note.
 */

"use client";

import { useState, useEffect } from "react";
import type { AiMode } from "@/lib/settings";
import { logger } from "@/lib/logger";

const STORAGE_KEY = "mongado_user_preferences";

export interface UserPreferences {
  aiMode: AiMode;
}

const DEFAULT_PREFERENCES: UserPreferences = {
  aiMode: "on-demand",
};

/**
 * Load user preferences from localStorage
 */
function loadPreferences(): UserPreferences {
  if (typeof window === "undefined") {
    return DEFAULT_PREFERENCES;
  }

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...DEFAULT_PREFERENCES, ...parsed };
    }
  } catch (err) {
    logger.error("Failed to load user preferences", err);
  }

  return DEFAULT_PREFERENCES;
}

/**
 * Save user preferences to localStorage
 */
function savePreferences(preferences: UserPreferences): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  } catch (err) {
    logger.error("Failed to save user preferences", err);
  }
}

/**
 * Hook for managing user preferences
 */
export function useUserPreferences() {
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_PREFERENCES);
  const [isLoaded, setIsLoaded] = useState(false);

  // Load preferences on mount
  useEffect(() => {
    const loaded = loadPreferences();
    setPreferences(loaded);
    setIsLoaded(true);
    logger.debug("User preferences loaded", loaded);
  }, []);

  // Save preferences whenever they change
  useEffect(() => {
    if (isLoaded) {
      savePreferences(preferences);
      logger.debug("User preferences saved", preferences);
    }
  }, [preferences, isLoaded]);

  /**
   * Update preferences (partial update supported)
   */
  const updatePreferences = (updates: Partial<UserPreferences>) => {
    setPreferences((prev) => ({ ...prev, ...updates }));
  };

  return {
    preferences,
    updatePreferences,
    isLoaded,
  };
}
