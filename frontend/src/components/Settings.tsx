/**
 * Settings component - Global app settings (available to all users)
 *
 * Contains:
 * - AI Suggestions mode (Off, On-demand, Automatic)
 * - Display preferences
 * - Other app-wide settings
 *
 * Separate from UserMenu (which handles account-specific actions)
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { useUserPreferences } from "@/hooks/useUserPreferences";
import type { AiMode } from "@/lib/settings";
import { logger } from "@/lib/logger";
import { config } from "@/lib/config";
import styles from "./Settings.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Settings() {
  const { preferences, updatePreferences } = useUserPreferences();
  const [isOpen, setIsOpen] = useState(false);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const warmupOllama = async () => {
    setIsWarmingUp(true);
    try {
      const response = await fetch(`${API_URL}/api/ollama/warmup`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Warmup failed");
      }

      logger.info("Ollama warmed up successfully");
    } catch (err) {
      logger.error("Failed to warm up Ollama", err);
      // Don't block the setting change - warmup will happen on first use
    } finally {
      setIsWarmingUp(false);
    }
  };

  const handleModeChange = async (newMode: AiMode) => {
    const oldMode = preferences.aiMode;
    updatePreferences({ aiMode: newMode });

    // Warmup if switching from "off" to an AI-enabled mode
    if (oldMode === "off" && (newMode === "on-demand" || newMode === "real-time")) {
      await warmupOllama();
    }
  };

  return (
    <div className={styles.container} ref={dropdownRef}>
      {/* Settings button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={styles.settingsButton}
        aria-label="Settings"
        aria-expanded={isOpen}
        title="Settings"
      >
        <span className={styles.icon}>⚙️</span>
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <div className={styles.dropdown}>
          <div className={styles.dropdownContent}>
            {/* AI Assistance Section */}
            <div className={styles.section}>
              {config.llmFeaturesEnabled ? (
                <>
                  {isWarmingUp && <div className={styles.warmupIndicator}>Warming up...</div>}

                  {/* Segmented Control */}
                  <div className={styles.segmentedControl}>
                    <button
                      onClick={() => handleModeChange("off")}
                      className={`${styles.segmentButton} ${preferences.aiMode === "off" ? styles.active : styles.inactive}`}
                      title="No AI suggestions"
                    >
                      Off
                    </button>
                    <button
                      onClick={() => handleModeChange("on-demand")}
                      className={`${styles.segmentButton} ${preferences.aiMode === "on-demand" ? styles.active : styles.inactive}`}
                      title="Click to get AI suggestions"
                    >
                      On-demand
                    </button>
                    <button
                      onClick={() => handleModeChange("real-time")}
                      className={`${styles.segmentButton} ${preferences.aiMode === "real-time" ? styles.active : styles.inactive}`}
                      title="Automatic AI suggestions"
                    >
                      Automatic
                    </button>
                  </div>

                  {/* Mode descriptions */}
                  <div className={styles.modeDescription}>
                    {preferences.aiMode === "off" && (
                      <p>
                        No AI suggestions. Fast, minimal overhead. Pure Zettelkasten experience.
                      </p>
                    )}
                    {preferences.aiMode === "on-demand" && (
                      <p>
                        Click &quot;Get Suggestions&quot; when you want AI help. Balanced approach
                        with no overhead while writing.
                      </p>
                    )}
                    {preferences.aiMode === "real-time" && (
                      <p>
                        Automatically generate suggestions in the background as you type. Panel
                        stays collapsed until you open it.
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <div className={styles.modeDescription}>
                  <p>AI features are not available in this environment.</p>
                </div>
              )}
            </div>

            {/* Future sections can be added here:
            - Display preferences (font size, compact/comfortable view)
            - Search preferences (default mode)
            - About/Help
            */}
          </div>
        </div>
      )}
    </div>
  );
}
