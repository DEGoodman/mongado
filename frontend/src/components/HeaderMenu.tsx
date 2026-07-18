/**
 * HeaderMenu - single consolidated header dropdown.
 *
 * Sections:
 * - Account: Sign In (logged out) OR name + Admin Settings + Sign Out (logged in)
 * - Appearance: Light/Dark theme segmented control
 * - AI Suggestions: Off / On-demand / Automatic (feature-flag gated)
 *
 * Replaces the former ThemeToggle + Settings + UserMenu header cluster.
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { User, GearSix } from "@phosphor-icons/react";
import { useTheme, type Theme } from "@/hooks/useTheme";
import { useDelight } from "@/hooks/useDelight";
import { sparkleBurst } from "@/lib/delight";
import { useUserPreferences } from "@/hooks/useUserPreferences";
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import type { AiMode } from "@/lib/settings";
import { logger } from "@/lib/logger";
import { isAuthenticated, clearAdminToken } from "@/lib/api/client";
import styles from "./HeaderMenu.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function HeaderMenu() {
  const { llmFeaturesEnabled, loaded: flagsLoaded } = useFeatureFlags();
  const { preferences, updatePreferences } = useUserPreferences();
  const { theme, setTheme } = useTheme();
  const { delight, setDelight } = useDelight();
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
    const oldMode = preferences.aiMode;
    updatePreferences({ aiMode: newMode });

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

  const themeSegment = (value: Theme, label: string) => (
    <button
      onClick={() => setTheme(value)}
      className={`${styles.segmentButton} ${theme === value ? styles.active : styles.inactive}`}
    >
      {label}
    </button>
  );

  const aiSegment = (value: AiMode, label: string) => (
    <button
      onClick={() => handleModeChange(value)}
      className={`${styles.segmentButton} ${preferences.aiMode === value ? styles.active : styles.inactive}`}
    >
      {label}
    </button>
  );

  return (
    <div className={styles.container} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={styles.menuButton}
        aria-label="Menu"
        aria-expanded={isOpen}
      >
        {isUserAuthenticated ? (
          <User size={18} aria-hidden="true" />
        ) : (
          <GearSix size={18} aria-hidden="true" />
        )}
      </button>

      {isOpen && (
        <div className={styles.dropdown}>
          <div className={styles.dropdownContent}>
            {/* Account */}
            <div className={styles.section}>
              {isUserAuthenticated ? (
                <>
                  <div className={styles.userName}>Admin User</div>
                  <Link href="/admin" className={styles.menuLink} onClick={() => setIsOpen(false)}>
                    Admin Settings
                  </Link>
                  <button onClick={handleLogout} className={styles.signOutButton}>
                    Sign Out
                  </button>
                </>
              ) : (
                <Link href="/login" className={styles.menuLink} onClick={() => setIsOpen(false)}>
                  Sign In
                </Link>
              )}
            </div>

            {/* Appearance */}
            <div className={styles.section}>
              <h3 className={styles.sectionLabel}>Theme</h3>
              <div className={styles.segmentedControl}>
                {themeSegment("light", "Light")}
                {themeSegment("dark", "Dark")}
              </div>
            </div>

            {/* Delight Mode (#240) */}
            <div className={styles.section}>
              <h3 className={styles.sectionLabel}>Delight</h3>
              <div className={styles.segmentedControl}>
                <button
                  onClick={() => setDelight(false)}
                  className={`${styles.segmentButton} ${delight === false ? styles.active : styles.inactive}`}
                >
                  Off
                </button>
                <button
                  onClick={(e) => {
                    setDelight(true);
                    // Celebrate the flip itself; sparkleBurst checks reduced-motion
                    sparkleBurst(e.clientX, e.clientY, 12);
                  }}
                  className={`${styles.segmentButton} ${delight === true ? styles.active : styles.inactive}`}
                >
                  On ✦
                </button>
              </div>
            </div>

            {/* AI Suggestions */}
            <div className={styles.section}>
              <h3 className={styles.sectionLabel}>AI Suggestions</h3>
              {!flagsLoaded ? null : llmFeaturesEnabled ? (
                <>
                  {isWarmingUp && <div className={styles.warmupIndicator}>Warming up...</div>}
                  <div className={styles.segmentedControl}>
                    {aiSegment("off", "Off")}
                    {aiSegment("on-demand", "On-demand")}
                    {aiSegment("real-time", "Automatic")}
                  </div>
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
          </div>
        </div>
      )}
    </div>
  );
}
