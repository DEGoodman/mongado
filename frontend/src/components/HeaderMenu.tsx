/**
 * HeaderMenu - single consolidated header dropdown.
 *
 * Sections:
 * - Account: Sign In (logged out) OR name + Admin Settings + Sign Out (logged in)
 * - Appearance: Light/Dark theme segmented control
 * - Slash Commands: On/Off (feature-flag gated)
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
import { useFeatureFlags } from "@/hooks/useFeatureFlags";
import { useSettings } from "@/hooks/useSettings";
import { logger } from "@/lib/logger";
import { isAuthenticated, clearAdminToken } from "@/lib/api/client";
import styles from "./HeaderMenu.module.scss";

export default function HeaderMenu() {
  const { llmFeaturesEnabled, loaded: flagsLoaded } = useFeatureFlags();
  const { settings, updateSettings } = useSettings();
  const { theme, setTheme } = useTheme();
  const { delight, setDelight } = useDelight();
  const [isOpen, setIsOpen] = useState(false);
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

            {/* Slash Commands (#146 Phase 1) */}
            {flagsLoaded && llmFeaturesEnabled && (
              <div className={styles.section}>
                <h3 className={styles.sectionLabel}>Slash Commands</h3>
                <div className={styles.segmentedControl}>
                  <button
                    onClick={() => updateSettings({ slashCommands: false })}
                    className={`${styles.segmentButton} ${!settings.slashCommands ? styles.active : styles.inactive}`}
                  >
                    Off
                  </button>
                  <button
                    onClick={() => updateSettings({ slashCommands: true })}
                    className={`${styles.segmentButton} ${settings.slashCommands ? styles.active : styles.inactive}`}
                  >
                    On
                  </button>
                </div>
                <div className={styles.modeDescription}>
                  <p>
                    Type <code>/</code> in the note editor for AI text commands (expand, simplify,
                    link, and more).
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
