"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { setAdminToken } from "@/lib/api/client";
import { isPasskeySupported, loginWithPasskey } from "@/lib/api/passkey";
import { hasDraft } from "@/lib/draft";
import { logger } from "@/lib/logger";
import TopNavigation from "@/components/TopNavigation";
import styles from "./page.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const loginLogger = logger.withContext("Login");

export default function LoginPage() {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [passkeyAvailable, setPasskeyAvailable] = useState(false);
  const [showTokenForm, setShowTokenForm] = useState(false);
  const router = useRouter();

  // Checked after mount: navigator is not available during SSR
  useEffect(() => {
    setPasskeyAvailable(isPasskeySupported());
  }, []);

  const goToDestination = () => {
    if (hasDraft()) {
      router.push("/knowledge-base/notes/new");
    } else {
      router.push("/knowledge-base/notes");
    }
  };

  const handlePasskeyLogin = async () => {
    setError("");
    setIsLoading(true);

    try {
      await loginWithPasskey();
      goToDestination();
    } catch (err) {
      // A cancelled OS prompt throws NotAllowedError - not worth an error box
      if (err instanceof DOMException && err.name === "NotAllowedError") {
        setError("Passkey prompt was dismissed.");
      } else {
        loginLogger.error("Passkey login failed:", err);
        setError(err instanceof Error ? err.message : "Passkey login failed.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleTokenLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      // Validate against the session endpoint, which exists to answer exactly
      // this question - no throwaway note round-trip needed.
      const response = await fetch(`${API_URL}/api/auth/session`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const status = await response.json();

      if (status.authenticated) {
        setAdminToken(token);
        goToDestination();
      } else {
        setError("Invalid token");
      }
    } catch (err) {
      loginLogger.error("Token login failed:", err);
      setError("Failed to connect to server");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <TopNavigation />
      <div className={styles.container}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.headerContent}>
            <button onClick={() => router.back()} className={styles.backButton}>
              ← Back
            </button>
            <h1 className={styles.title}>Admin Login</h1>
            <p className={styles.subtitle}>Sign in to create and edit persistent notes</p>
          </div>
        </header>

        {/* Form */}
        <main className={styles.main}>
          <div className={styles.formCard}>
            {passkeyAvailable && (
              <div className={styles.passkeySection}>
                <button
                  type="button"
                  onClick={handlePasskeyLogin}
                  disabled={isLoading}
                  className={styles.submitButton}
                >
                  {isLoading ? "Waiting for passkey..." : "Sign in with passkey"}
                </button>
                <p className={styles.hint}>Uses Touch ID, Windows Hello, or your security key.</p>
              </div>
            )}

            {error && (
              <div className={styles.errorBox}>
                <svg className={styles.errorIcon} viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
                <p className={styles.errorMessage}>{error}</p>
              </div>
            )}

            {passkeyAvailable && !showTokenForm && (
              <button
                type="button"
                className={styles.linkButton}
                onClick={() => setShowTokenForm(true)}
              >
                Use an admin token instead
              </button>
            )}

            {(!passkeyAvailable || showTokenForm) && (
              <form className={styles.form} onSubmit={handleTokenLogin}>
                <div className={styles.inputGroup}>
                  <label htmlFor="token" className={styles.label}>
                    Admin Token
                  </label>
                  <input
                    id="token"
                    name="token"
                    type="password"
                    autoComplete="current-password"
                    required
                    className={styles.input}
                    placeholder="Admin token"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    disabled={isLoading}
                  />
                </div>

                <button type="submit" disabled={isLoading} className={styles.submitButton}>
                  {isLoading ? "Verifying..." : "Sign in with token"}
                </button>
              </form>
            )}
          </div>
        </main>
      </div>
    </>
  );
}
