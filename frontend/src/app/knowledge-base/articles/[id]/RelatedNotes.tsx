"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { logger } from "@/lib/logger";
import styles from "./page.module.scss";

interface RelatedNote {
  id: string;
  title: string;
  content?: string;
  score?: number;
}

/**
 * Related-notes sidebar island. Fetched client-side after mount so the
 * server-rendered article body never waits on the similarity lookup.
 */
export default function RelatedNotes({ articleId }: { articleId: number }) {
  const [relatedNotes, setRelatedNotes] = useState<RelatedNote[]>([]);
  const [loading, setLoading] = useState(true);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    async function fetchRelatedNotes() {
      try {
        const response = await fetch(`${API_URL}/api/articles/${articleId}/related-notes?limit=5`);

        if (response.ok) {
          const data = await response.json();
          setRelatedNotes(data.notes || []);
          logger.info("Related notes loaded", { count: data.count });
        }
      } catch (err) {
        logger.warn("Failed to load related notes", err);
        // Silently fail - related notes are optional
      } finally {
        setLoading(false);
      }
    }

    fetchRelatedNotes();
  }, [articleId, API_URL]);

  if (!loading && relatedNotes.length === 0) return null;

  return (
    <div className={styles.relatedNotes}>
      <h3 className={styles.relatedNotesTitle}>Related Notes</h3>
      {loading ? (
        <div className={styles.loadingNotes}>Finding related notes...</div>
      ) : (
        <ul className={styles.relatedNotesList}>
          {relatedNotes.map((note) => (
            <li key={note.id} className={styles.relatedNoteItem}>
              <Link href={`/knowledge-base/notes/${note.id}`} className={styles.relatedNoteLink}>
                <span className={styles.noteTitle}>{note.title || note.id}</span>
                {note.score && (
                  <span className={styles.noteScore}>{Math.round(note.score * 100)}% match</span>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
