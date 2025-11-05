"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearAdminToken } from "@/lib/api/client";
import styles from "./AuthStatusBanner.module.scss";

interface AuthStatusBannerProps {
  /**
   * Display mode: "warning" for unauthenticated, "success" for authenticated
   */
  mode?: "auto" | "warning" | "success";
}

export default function AuthStatusBanner({ mode = "auto" }: AuthStatusBannerProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const router = useRouter();

  const checkAuth = () => {
    try {
      const adminToken = localStorage.getItem("admin_token");
      setIsAuthenticated(!!adminToken);
    } catch (err) {
      setIsAuthenticated(false);
    } finally {
      setIsChecking(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const handleLogout = () => {
    clearAdminToken();
    setIsAuthenticated(false);
    router.push("/knowledge-base/notes");
  };

  if (isChecking) {
    return null; // Don't show anything while checking
  }

  const displayMode = mode === "auto" ? (isAuthenticated ? "success" : "warning") : mode;

  if (displayMode === "success" && isAuthenticated) {
    return (
      <div className={styles.bannerSuccess}>
        <div className={styles.content}>
          <svg className={styles.icon} fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <div className={styles.textContent}>
            <p className={styles.title}>Authenticated</p>
            <p className={styles.description}>
              Your notes will be saved persistently to the database
            </p>
          </div>
          <button onClick={handleLogout} className={styles.logoutButton}>
            Logout
          </button>
        </div>
      </div>
    );
  }

  if (displayMode === "warning" && !isAuthenticated) {
    return (
      <div className={styles.bannerWarning}>
        <div className={styles.content}>
          <svg className={styles.icon} fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <div className={styles.textContent}>
            <p className={styles.title}>You are not authenticated</p>
            <p className={styles.description}>
              <strong>Authentication is required</strong> to create, edit, or delete notes. You can
              view existing notes, but cannot make changes.
            </p>
            <div className={styles.divider}>
              <p className={styles.loginPrompt}>
                <strong>To manage notes:</strong>{" "}
                <Link href="/login" className={styles.loginLink}>
                  Login with admin token
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}

/**
 * Compact authentication indicator for the top of pages
 */
export function AuthStatusIndicator() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const adminToken = localStorage.getItem("admin_token");
        setIsAuthenticated(!!adminToken);
      } catch (err) {
        setIsAuthenticated(false);
      } finally {
        setIsChecking(false);
      }
    };

    checkAuth();
  }, []);

  if (isChecking) {
    return null;
  }

  return (
    <div
      className={`${styles.indicator} ${isAuthenticated ? styles.authenticated : styles.unauthenticated}`}
    >
      {isAuthenticated ? (
        <span>✓ Authenticated - Notes will be saved permanently</span>
      ) : (
        <span>⚠ Not authenticated - Login required to create or edit notes</span>
      )}
    </div>
  );
}
