/**
 * User settings management using localStorage.
 *
 * For now, settings are stored client-side only since this is a personal
 * project with admin-only features. Future: sync to backend when we add
 * user accounts.
 */

export interface UserSettings {
  aiSuggestionsEnabled: boolean;
}

const SETTINGS_KEY = "mongado-settings";

const DEFAULT_SETTINGS: UserSettings = {
  aiSuggestionsEnabled: false, // Default to OFF (user opts in)
};

/**
 * Load settings from localStorage.
 * Falls back to defaults if not found or invalid.
 */
export function loadSettings(): UserSettings {
  if (typeof window === "undefined") {
    return DEFAULT_SETTINGS;
  }

  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (!stored) {
      return DEFAULT_SETTINGS;
    }

    const parsed = JSON.parse(stored);
    return {
      ...DEFAULT_SETTINGS,
      ...parsed,
    };
  } catch (error) {
    console.error("Failed to load settings from localStorage:", error);
    return DEFAULT_SETTINGS;
  }
}

/**
 * Save settings to localStorage.
 */
export function saveSettings(settings: UserSettings): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch (error) {
    console.error("Failed to save settings to localStorage:", error);
  }
}

/**
 * Update a single setting.
 */
export function updateSetting<K extends keyof UserSettings>(key: K, value: UserSettings[K]): void {
  const current = loadSettings();
  const updated = { ...current, [key]: value };
  saveSettings(updated);
}
