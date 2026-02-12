"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useSettings } from "@/hooks/useSettings";
import type { AiMode } from "@/lib/settings";
import { logger } from "@/lib/logger";
import { config } from "@/lib/config";
import { isAuthenticated, clearAdminToken } from "@/lib/api/client";
import styles from "./SettingsDropdown.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsDropdown() {
  const { settings, updateSettings } = useSettings();
  const [isOpen, setIsOpen] = useState(false);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [isUserAuthenticated, setIsUserAuthenticated] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Check authentication status on mount and when dropdown opens
  useEffect(() => {
    setIsUserAuthenticated(isAuthenticated());
  }, [isOpen]);

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
    const oldMode = settings.aiMode;
    updateSettings({ aiMode: newMode });

    // Warmup if switching from "off" to an AI-enabled mode
    if (oldMode === "off" && (newMode === "on-demand" || newMode === "real-time")) {
      await warmupOllama();
    }
  };

  const handleLogout = () => {
    clearAdminToken();
    logger.info("User logged out");
    setIsOpen(false);
    router.push("/login");
  };

  return (
    <div className={styles.container}>
      {/* Sign In link when not authenticated */}
      {!isUserAuthenticated && (
        <Link href="/login" className={styles.signInLink}>
          Sign In
        </Link>
      )}

      {/* Settings dropdown */}
      <div className={styles.dropdownWrapper} ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={styles.settingsButton}
          aria-label="Settings"
        >
          <span className={styles.icon}>⚙️</span>
          <span className={styles.label}>Settings</span>
          <svg
            className={`${styles.chevron} ${isOpen ? styles.open : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {isOpen && (
          <div className={styles.dropdown}>
            <div className={styles.dropdownContent}>
              {config.llmFeaturesEnabled ? (
                <>
                  <div className={styles.header}>
                    <h3 className={styles.title}>AI Suggestions</h3>
                    {isWarmingUp && <span className={styles.warmupIndicator}>Warming up...</span>}
                  </div>

                  {/* Segmented Control */}
                  <div className={styles.segmentedControl}>
                    <button
                      onClick={() => handleModeChange("off")}
                      className={`${styles.segmentButton} ${settings.aiMode === "off" ? styles.active : styles.inactive}`}
                    >
                      Off
                    </button>
                    <button
                      onClick={() => handleModeChange("on-demand")}
                      className={`${styles.segmentButton} ${settings.aiMode === "on-demand" ? styles.active : styles.inactive}`}
                    >
                      On-demand
                    </button>
                    <button
                      onClick={() => handleModeChange("real-time")}
                      className={`${styles.segmentButton} ${settings.aiMode === "real-time" ? styles.active : styles.inactive}`}
                    >
                      Automatic
                    </button>
                  </div>

                  {/* Mode descriptions */}
                  <div className={styles.modeDescription}>
                    {settings.aiMode === "off" && (
                      <p>No AI suggestions. Fast, minimal overhead. Pure Zettelkasten experience.</p>
                    )}
                    {settings.aiMode === "on-demand" && (
                      <p>
                        Click &quot;Get Suggestions&quot; when you want AI help. Balanced approach with
                        no overhead while writing.
                      </p>
                    )}
                    {settings.aiMode === "real-time" && (
                      <p>
                        Automatically generate suggestions in the background as you type. Panel stays
                        collapsed until you open it.
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <div className={styles.modeDescription}>
                  <p>AI features are not available in this environment.</p>
                </div>
              )}

              {/* Logout section */}
              {isUserAuthenticated && (
                <div className={styles.logoutSection}>
                  <button onClick={handleLogout} className={styles.logoutButton}>
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
