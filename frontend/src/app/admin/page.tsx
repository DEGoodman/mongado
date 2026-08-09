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
import {
  deletePasskey,
  isPasskeySupported,
  listPasskeys,
  registerPasskey,
  type PasskeyCredential,
} from "@/lib/api/passkey";
import {
  createApiToken,
  deleteApiToken,
  getApiScopes,
  listApiTokens,
  type ApiScope,
  type ApiTokenInfo,
} from "@/lib/api/tokens";
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

function formatUnixTimestamp(seconds: number | null): string {
  if (!seconds) return "never";
  return new Date(seconds * 1000).toLocaleString();
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

  const [passkeys, setPasskeys] = useState<PasskeyCredential[]>([]);
  const [passkeyError, setPasskeyError] = useState<string | null>(null);
  const [passkeyMessage, setPasskeyMessage] = useState<string | null>(null);
  const [passkeyName, setPasskeyName] = useState("");
  const [enrolling, setEnrolling] = useState(false);
  const [passkeySupported, setPasskeySupported] = useState(false);

  const [scopes, setScopes] = useState<ApiScope[]>([]);
  const [tokens, setTokens] = useState<ApiTokenInfo[]>([]);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [tokenMessage, setTokenMessage] = useState<string | null>(null);
  const [tokenName, setTokenName] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [tokenExpiry, setTokenExpiry] = useState("30"); // days; "" = never
  const [creatingToken, setCreatingToken] = useState(false);
  const [newToken, setNewToken] = useState<string | null>(null);

  const loadTokens = useCallback(() => {
    listApiTokens()
      .then(setTokens)
      .catch((err) => {
        adminLogger.error("Failed to load API tokens:", err);
        setTokenError("Failed to load API tokens.");
      });
    getApiScopes()
      .then(setScopes)
      .catch((err) => adminLogger.error("Failed to load scopes:", err));
  }, []);

  const loadPasskeys = useCallback(() => {
    listPasskeys()
      .then(setPasskeys)
      .catch((err) => {
        adminLogger.error("Failed to load passkeys:", err);
        setPasskeyError("Failed to load passkeys.");
      });
  }, []);

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
    setPasskeySupported(isPasskeySupported());
    loadPasskeys();
    loadTokens();
  }, [router, loadHealth, loadPasskeys, loadTokens]);

  const toggleScope = (name: string) => {
    setSelectedScopes((current) =>
      current.includes(name) ? current.filter((s) => s !== name) : [...current, name]
    );
  };

  const handleCreateToken = async () => {
    const name = tokenName.trim();
    if (!name || selectedScopes.length === 0) {
      setTokenError("A name and at least one scope are required.");
      return;
    }

    setCreatingToken(true);
    setTokenError(null);
    setTokenMessage(null);
    setNewToken(null);

    const expiresInDays = tokenExpiry === "" ? null : parseInt(tokenExpiry, 10);
    try {
      const result = await createApiToken(name, selectedScopes, expiresInDays);
      setNewToken(result.token);
      setTokens((current) => [result.info, ...current]);
      setTokenName("");
      setSelectedScopes([]);
      setTokenMessage(`Created "${name}".`);
    } catch (err) {
      adminLogger.error("Token creation failed:", err);
      setTokenError(err instanceof Error ? err.message : "Failed to create token.");
    } finally {
      setCreatingToken(false);
    }
  };

  const handleRevokeToken = async (token: ApiTokenInfo) => {
    if (!window.confirm(`Revoke "${token.name}"? Any script using it will stop working.`)) {
      return;
    }

    setTokenError(null);
    setTokenMessage(null);
    try {
      await deleteApiToken(token.token_id);
      setTokens((current) => current.filter((t) => t.token_id !== token.token_id));
      setTokenMessage(`Revoked "${token.name}".`);
    } catch (err) {
      adminLogger.error("Token revocation failed:", err);
      setTokenError("Failed to revoke token.");
    }
  };

  const handleCopyToken = async () => {
    if (!newToken) return;
    try {
      await navigator.clipboard.writeText(newToken);
      setTokenMessage("Copied to clipboard.");
    } catch {
      setTokenMessage("Copy failed - select and copy the token manually.");
    }
  };

  const handleEnrollPasskey = async () => {
    setEnrolling(true);
    setPasskeyError(null);
    setPasskeyMessage(null);

    const name = passkeyName.trim() || "Passkey";
    try {
      setPasskeys(await registerPasskey(name));
      setPasskeyName("");
      setPasskeyMessage(`Enrolled "${name}".`);
    } catch (err) {
      if (err instanceof DOMException && err.name === "NotAllowedError") {
        setPasskeyError("Enrollment was cancelled.");
      } else if (err instanceof DOMException && err.name === "InvalidStateError") {
        // The browser refuses to double-enroll an excluded authenticator
        setPasskeyError("This device already has a passkey registered.");
      } else {
        adminLogger.error("Passkey enrollment failed:", err);
        setPasskeyError(err instanceof Error ? err.message : "Enrollment failed.");
      }
    } finally {
      setEnrolling(false);
    }
  };

  const handleRevokePasskey = async (credential: PasskeyCredential) => {
    if (!window.confirm(`Revoke "${credential.name}"? That device will no longer sign in.`)) {
      return;
    }

    setPasskeyError(null);
    setPasskeyMessage(null);
    try {
      await deletePasskey(credential.credential_id);
      setPasskeys((current) => current.filter((c) => c.credential_id !== credential.credential_id));
      setPasskeyMessage(`Revoked "${credential.name}".`);
    } catch (err) {
      adminLogger.error("Passkey revocation failed:", err);
      setPasskeyError("Failed to revoke passkey.");
    }
  };

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
      const detail = err instanceof Error ? err.message : "Check the backend logs.";
      setHealthError(`Backup failed: ${detail}`);
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
            <h2 className={styles.cardTitle}>Passkeys</h2>
            <p className={styles.cardDescription}>
              Sign in with Touch ID, Windows Hello, or a security key instead of the admin token.
              Each device is enrolled and revoked independently.
            </p>

            {passkeyError && <p className={styles.error}>{passkeyError}</p>}
            {passkeyMessage && <p className={styles.success}>{passkeyMessage}</p>}

            {passkeys.length === 0 ? (
              <p className={styles.status}>No passkeys enrolled yet.</p>
            ) : (
              <ul className={styles.passkeyList}>
                {passkeys.map((credential) => (
                  <li key={credential.credential_id} className={styles.passkeyRow}>
                    <div className={styles.passkeyInfo}>
                      <span className={styles.passkeyName}>{credential.name}</span>
                      <span className={styles.passkeyMeta}>
                        Added {formatUnixTimestamp(credential.created_at)} · Last used{" "}
                        {formatUnixTimestamp(credential.last_used_at)}
                      </span>
                    </div>
                    <button
                      type="button"
                      className={styles.revokeButton}
                      onClick={() => handleRevokePasskey(credential)}
                    >
                      Revoke
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {passkeySupported ? (
              <div className={styles.passkeyEnroll}>
                <label htmlFor="passkey-name" className={styles.srOnly}>
                  Device name
                </label>
                <input
                  id="passkey-name"
                  type="text"
                  className={styles.passkeyInput}
                  placeholder="Device name (e.g. MacBook)"
                  maxLength={64}
                  value={passkeyName}
                  onChange={(e) => setPasskeyName(e.target.value)}
                  disabled={enrolling}
                />
                <button
                  type="button"
                  className={styles.backupButton}
                  disabled={enrolling}
                  onClick={handleEnrollPasskey}
                >
                  {enrolling ? "Waiting for device..." : "Add passkey"}
                </button>
              </div>
            ) : (
              <p className={styles.status}>This browser does not support passkeys.</p>
            )}
          </div>

          <div className={styles.card}>
            <h2 className={styles.cardTitle}>API Tokens</h2>
            <p className={styles.cardDescription}>
              Scoped, revocable bearer tokens for programmatic API use - the safe way to script
              against the site without exposing the admin token. Each token can do only what its
              scopes allow.
            </p>

            {tokenError && <p className={styles.error}>{tokenError}</p>}
            {tokenMessage && <p className={styles.success}>{tokenMessage}</p>}

            {newToken && (
              <div className={styles.tokenReveal}>
                <p className={styles.tokenRevealWarning}>
                  Copy this token now - it will not be shown again.
                </p>
                <div className={styles.tokenRevealCode}>
                  <code className={styles.tokenValue}>{newToken}</code>
                  <button type="button" className={styles.copyButton} onClick={handleCopyToken}>
                    Copy
                  </button>
                </div>
              </div>
            )}

            {tokens.length === 0 ? (
              <p className={styles.status}>No API tokens yet.</p>
            ) : (
              <ul className={styles.passkeyList}>
                {tokens.map((token) => (
                  <li key={token.token_id} className={styles.passkeyRow}>
                    <div className={styles.passkeyInfo}>
                      <span className={styles.passkeyName}>{token.name}</span>
                      <span className={styles.tokenScopes}>
                        {token.scopes.map((scope) => (
                          <span key={scope} className={styles.scopeTag}>
                            {scope}
                          </span>
                        ))}
                      </span>
                      <span className={styles.passkeyMeta}>
                        Created {formatUnixTimestamp(token.created_at)} · Expires{" "}
                        {token.expires_at ? formatUnixTimestamp(token.expires_at) : "never"} · Last
                        used {formatUnixTimestamp(token.last_used_at)}
                      </span>
                    </div>
                    <button
                      type="button"
                      className={styles.revokeButton}
                      onClick={() => handleRevokeToken(token)}
                    >
                      Revoke
                    </button>
                  </li>
                ))}
              </ul>
            )}

            <div className={styles.tokenForm}>
              <div className={styles.tokenField}>
                <label htmlFor="token-name" className={styles.tokenLabel}>
                  Name
                </label>
                <input
                  id="token-name"
                  type="text"
                  className={styles.passkeyInput}
                  placeholder="e.g. deploy job, importer"
                  maxLength={64}
                  value={tokenName}
                  onChange={(e) => setTokenName(e.target.value)}
                  disabled={creatingToken}
                />
              </div>

              <div className={styles.tokenField}>
                <span className={styles.tokenLabel}>Scopes</span>
                <div className={styles.scopeList}>
                  {scopes.map((scope) => (
                    <label key={scope.name} className={styles.scopeItem}>
                      <input
                        type="checkbox"
                        checked={selectedScopes.includes(scope.name)}
                        onChange={() => toggleScope(scope.name)}
                        disabled={creatingToken}
                      />
                      <span>
                        <span className={styles.scopeName}>{scope.name}</span>
                        <br />
                        <span className={styles.scopeDescription}>{scope.description}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className={styles.tokenField}>
                <label htmlFor="token-expiry" className={styles.tokenLabel}>
                  Expires
                </label>
                <select
                  id="token-expiry"
                  className={styles.tokenSelect}
                  value={tokenExpiry}
                  onChange={(e) => setTokenExpiry(e.target.value)}
                  disabled={creatingToken}
                >
                  <option value="7">7 days</option>
                  <option value="30">30 days</option>
                  <option value="90">90 days</option>
                  <option value="">Never</option>
                </select>
              </div>

              <button
                type="button"
                className={styles.backupButton}
                disabled={creatingToken}
                onClick={handleCreateToken}
              >
                {creatingToken ? "Creating..." : "Create token"}
              </button>
            </div>
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
