/**
 * UserMenu component - Account-specific actions (logged in users only)
 *
 * Contains:
 * - User name/email display
 * - Sign Out
 *
 * For logged out users, shows "Sign In" link instead of dropdown
 */

"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { logger } from "@/lib/logger";
import { isAuthenticated, clearAdminToken } from "@/lib/api/client";
import styles from "./UserMenu.module.scss";

export default function UserMenu() {
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

  return (
    <div className={styles.container} ref={dropdownRef}>
      {/* User button/link */}
      {!isUserAuthenticated ? (
        <Link href="/login" className={styles.signInLink}>
          Sign In
        </Link>
      ) : (
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={styles.userButton}
          aria-label="User menu"
          aria-expanded={isOpen}
        >
          <span className={styles.userIcon}>👤</span>
          <svg
            className={`${styles.chevron} ${isOpen ? styles.open : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      )}

      {/* Dropdown menu */}
      {isOpen && isUserAuthenticated && (
        <div className={styles.dropdown}>
          <div className={styles.dropdownContent}>
            {/* User Info */}
            <div className={styles.section}>
              <div className={styles.userInfo}>
                <div className={styles.userName}>Admin User</div>
                {/* Email could be added here if available */}
              </div>
            </div>

            {/* Divider */}
            <div className={styles.divider} />

            {/* Account Actions */}
            <div className={styles.section}>
              <button onClick={handleLogout} className={styles.logoutButton}>
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
