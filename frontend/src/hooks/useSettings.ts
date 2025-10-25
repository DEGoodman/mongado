"use client";

import { useEffect, useState } from "react";
import { loadSettings, saveSettings, type UserSettings } from "@/lib/settings";

/**
 * React hook for accessing and updating user settings.
 *
 * Settings are persisted to localStorage and synchronized across components.
 */
export function useSettings() {
  const [settings, setSettings] = useState<UserSettings>(loadSettings);

  // Update settings and persist to localStorage
  const updateSettings = (updates: Partial<UserSettings>) => {
    const newSettings = { ...settings, ...updates };
    setSettings(newSettings);
    saveSettings(newSettings);
  };

  // Load settings on mount (handles SSR)
  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  return {
    settings,
    updateSettings,
  };
}
