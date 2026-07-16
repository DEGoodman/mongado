"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import TopNavigation from "@/components/TopNavigation";
import { isAuthenticated } from "@/lib/api/client";
import {
  getFeatureFlags,
  updateFeatureFlag,
  getDatabaseHealth,
  createBackup,
  type FeatureFlag,
  type DatabaseHealth,
} from "@/lib/api/admin";
import { applyFeatureFlag } from "@/hooks/useFeatureFlags";
import { logger } from "@/lib/logger";
import styles from "./page.module.scss";

const adminLogger = logger.withContext("AdminSettings");

function formatTimestamp(iso: string | null): string {
  if (!iso) return "never";
  const date = new Date(iso);
  if (isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

export default function AdminPage() {
  const router = useRouter();
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);

  const [health, setHealth] = useState<DatabaseHealth | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [backingUp, setBackingUp] = useState(false);
  const [backupMessage, setBackupMessage] = useState<string | null>(null);

  const loadHealth = useCallback(() => {
    getDatabaseHealth()
      .then(setHealth)
      .catch((err) => {
        adminLogger.error("Failed to load database health:", err);
        setHealthError("Failed to load database health.");
      });
  }, []);

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

    loadHealth();
  }, [router, loadHealth]);

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

  const handleBackup = async () => {
    setBackingUp(true);
    setBackupMessage(null);
    setHealthError(null);

    try {
      const result = await createBackup();
      setBackupMessage(`Backup created: ${result.backup_file} (${result.note_count} notes)`);
      loadHealth();
    } catch (err) {
      adminLogger.error("Backup failed:", err);
      setHealthError("Backup failed. Check the backend logs.");
    } finally {
      setBackingUp(false);
    }
  };

  const cronStale = health?.backup_cron_healthy === false;

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

          <div className={styles.card}>
            <h2 className={styles.cardTitle}>Database &amp; Backups</h2>

            {healthError && <p className={styles.error}>{healthError}</p>}
            {backupMessage && <p className={styles.success}>{backupMessage}</p>}
            {cronStale && (
              <p className={styles.warning}>
                The nightly backup cron has not run in over 48 hours. Check{" "}
                <code>mongado-backup-cron</code> on the droplet.
              </p>
            )}

            {!health && !healthError && <p className={styles.status}>Loading health...</p>}

            {health && (
              <dl className={styles.healthGrid}>
                <dt>Status</dt>
                <dd>
                  <span className={`${styles.badge} ${styles[health.status] ?? ""}`}>
                    {health.status}
                  </span>
                </dd>
                <dt>Notes</dt>
                <dd>{health.notes_count}</dd>
                <dt>Backups available</dt>
                <dd>{health.backups_available}</dd>
                <dt>Last backup</dt>
                <dd>{formatTimestamp(health.last_backup)}</dd>
                <dt>Cron last ran</dt>
                <dd>
                  {health.backup_cron_last_run
                    ? formatTimestamp(health.backup_cron_last_run)
                    : "no heartbeat recorded"}
                </dd>
              </dl>
            )}

            <button
              type="button"
              className={styles.backupButton}
              disabled={backingUp}
              onClick={handleBackup}
            >
              {backingUp ? "Backing up..." : "Back up now"}
            </button>
          </div>
        </main>
      </div>
    </>
  );
}
