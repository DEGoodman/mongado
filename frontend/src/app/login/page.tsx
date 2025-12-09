"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setAdminToken } from "@/lib/api/client";
import { hasDraft } from "@/lib/draft";
import TopNavigation from "@/components/TopNavigation";
import styles from "./page.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      // Store the token first so the API client can use it
      setAdminToken(token);

      // Test the token by making an authenticated request to create a note
      // This endpoint requires auth, so it will validate our token
      const response = await fetch(`${API_URL}/api/notes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          content: "# Test Auth\n\nTemporary note to validate authentication",
          title: "Auth Test",
        }),
      });

      if (response.ok) {
        // Token is valid, delete the test note
        const testNote = await response.json();

        await fetch(`${API_URL}/api/notes/${testNote.id}`, {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        // Redirect to draft if one exists, otherwise to notes list
        if (hasDraft()) {
          router.push("/knowledge-base/notes/new");
        } else {
          router.push("/knowledge-base/notes");
        }
      } else {
        const data = await response.json().catch(() => ({ detail: "Invalid token" }));
        setError(data.detail || "Invalid token");
        // Clear the stored token on failure
        setAdminToken("");
      }
    } catch (err) {
      setError("Failed to connect to server");
      // Clear the stored token on failure
      setAdminToken("");
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
            <p className={styles.subtitle}>Enter your admin token to create persistent notes</p>
          </div>
        </header>

        {/* Form */}
        <main className={styles.main}>
          <div className={styles.formCard}>
            <form className={styles.form} onSubmit={handleLogin}>
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

              <button type="submit" disabled={isLoading} className={styles.submitButton}>
                {isLoading ? "Verifying..." : "Sign in"}
              </button>
            </form>
          </div>
        </main>
      </div>
    </>
  );
}
