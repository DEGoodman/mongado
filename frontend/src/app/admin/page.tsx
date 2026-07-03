"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopNavigation from "@/components/TopNavigation";
import { isAuthenticated } from "@/lib/api/client";
import { getFeatureFlags, updateFeatureFlag, type FeatureFlag } from "@/lib/api/admin";
import { applyFeatureFlag } from "@/hooks/useFeatureFlags";
import { logger } from "@/lib/logger";
import styles from "./page.module.scss";

const adminLogger = logger.withContext("AdminSettings");

export default function AdminPage() {
  const router = useRouter();
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    getFeatureFlags()
      .then(setFlags)
      .catch((err) => {
        adminLogger.error("Failed to load feature flags:", err);
        setError("Failed to load feature flags. Is your admin session still valid?");
      })
      .finally(() => setLoading(false));
  }, [router]);

  const handleToggle = async (flag: FeatureFlag) => {
    const newValue = !flag.enabled;
    setSaving(flag.name);
    setError(null);
    setWarning(null);

    try {
      const result = await updateFeatureFlag(flag.name, newValue);
      setFlags((current) =>
        current.map((f) => (f.name === flag.name ? { ...f, enabled: result.flag.enabled } : f))
      );
      if (!result.persisted) {
        setWarning(
          "Saved in memory only - the database is unavailable, so this value may revert shortly."
        );
      }
      // Update the rest of the app immediately from the authoritative response
      applyFeatureFlag(result.flag.name, result.flag.enabled);
    } catch (err) {
      adminLogger.error("Failed to update feature flag:", err);
      setError(`Failed to update "${flag.name}". Try again.`);
    } finally {
      setSaving(null);
    }
  };

  return (
    <>
      <TopNavigation />
      <div className={styles.container}>
        <header className={styles.header}>
          <div className={styles.headerContent}>
            <h1 className={styles.title}>Admin Settings</h1>
            <p className={styles.subtitle}>
              Runtime feature flags - changes take effect immediately
            </p>
          </div>
        </header>

        <main className={styles.main}>
          <div className={styles.card}>
            {loading && <p className={styles.status}>Loading feature flags...</p>}

            {error && <p className={styles.error}>{error}</p>}
            {warning && <p className={styles.warning}>{warning}</p>}

            {!loading && !error && flags.length === 0 && (
              <p className={styles.status}>No feature flags defined.</p>
            )}

            {flags.map((flag) => (
              <div key={flag.name} className={styles.flagRow}>
                <div className={styles.flagInfo}>
                  <span className={styles.flagName}>{flag.name}</span>
                  <span className={styles.flagDescription}>{flag.description}</span>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={flag.enabled}
                  aria-label={`Toggle ${flag.name}`}
                  className={`${styles.toggle} ${flag.enabled ? styles.toggleOn : ""}`}
                  disabled={saving === flag.name}
                  onClick={() => handleToggle(flag)}
                >
                  <span className={styles.toggleKnob} />
                </button>
              </div>
            ))}
          </div>
        </main>
      </div>
    </>
  );
}
