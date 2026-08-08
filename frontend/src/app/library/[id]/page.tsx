"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Breadcrumb from "@/components/Breadcrumb";
import PageHeader from "@/components/PageHeader";
import { LoadingState, ErrorState } from "@/components/PageState";
import { getLibraryEntry, deleteLibraryEntry, LibraryEntry } from "@/lib/api/library";
import { isAuthenticated } from "@/lib/api/client";
import { sanitizeHtml } from "@/lib/sanitize";
import { logger } from "@/lib/logger";
import styles from "./page.module.scss";

export default function LibraryEntryPage() {
  const router = useRouter();
  const params = useParams();
  const entryId = params.id as string;

  const [entry, setEntry] = useState<LibraryEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authed, setAuthed] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setAuthed(isAuthenticated());
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const data = await getLibraryEntry(entryId);
        setEntry(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load entry");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [entryId]);

  const handleDelete = async () => {
    if (!confirm("Delete this library entry? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await deleteLibraryEntry(entryId);
      logger.info("Deleted library entry", { id: entryId });
      router.push("/library");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete entry");
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <LoadingState label="Loading entry" />
      </div>
    );
  }

  if (error || !entry) {
    return (
      <div className={styles.container}>
        <ErrorState
          message={error || "Entry not found"}
          backHref="/library"
          backLabel="Back to Library"
        />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <PageHeader
        title={entry.title}
        subtitle={entry.author || undefined}
        breadcrumb={<Breadcrumb section="library" />}
        actions={
          authed ? (
            <div className={styles.adminActions}>
              <Link href={`/library/${entry.id}/edit`} className={styles.editButton}>
                Edit
              </Link>
              <button
                type="button"
                onClick={handleDelete}
                className={styles.deleteButton}
                disabled={deleting}
              >
                {deleting ? "Deleting…" : "Delete"}
              </button>
            </div>
          ) : undefined
        }
      />

      <main className={styles.main}>
        <div className={styles.meta}>
          <span className={styles.typeBadge}>{entry.type}</span>
          {entry.source_url && (
            <a
              href={entry.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.sourceLink}
            >
              View source ↗
            </a>
          )}
        </div>

        {entry.tags.length > 0 && (
          <div className={styles.tags}>
            {entry.tags.map((tag) => (
              <span key={tag} className={styles.tag}>
                {tag}
              </span>
            ))}
          </div>
        )}

        <div className={styles.summaryCard}>
          {entry.html_summary ? (
            <div
              className={styles.renderedSummary}
              dangerouslySetInnerHTML={{ __html: sanitizeHtml(entry.html_summary) }}
            />
          ) : entry.summary ? (
            <div className={styles.plainSummary}>{entry.summary}</div>
          ) : (
            <p className={styles.noSummary}>No summary yet.</p>
          )}
        </div>
      </main>
    </div>
  );
}
