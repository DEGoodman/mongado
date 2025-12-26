/**
 * NoteOfDay Component
 * Homepage widget displaying a random stale note (or random note if none stale)
 * Encourages knowledge base maintenance and serendipitous rediscovery
 */

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import styles from "./NoteOfDay.module.scss";

interface Note {
  id: string;
  title?: string;
  content: string;
  updated_at: number;
  days_stale?: number;
}

interface NoteOfDayData {
  note: Note;
  is_stale: boolean;
  message: string;
}

export default function NoteOfDay() {
  const [data, setData] = useState<NoteOfDayData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchNoteOfDay() {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/notes/note-of-day`);
        if (!response.ok) {
          if (response.status === 404) {
            // No notes yet - this is fine
            setData(null);
            return;
          }
          throw new Error("Failed to fetch note of the day");
        }
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    }

    fetchNoteOfDay();
  }, []);

  if (loading) {
    return (
      <div className={styles.noteOfDay}>
        <div className={styles.skeleton}></div>
      </div>
    );
  }

  if (error || !data) {
    return null; // Don't show widget if no notes or error
  }

  const { note, is_stale, message } = data;
  const previewContent = note.content.slice(0, 150) + (note.content.length > 150 ? "..." : "");

  return (
    <div className={`${styles.noteOfDay} ${is_stale ? styles.stale : ""}`}>
      <div className={styles.header}>
        <span className={styles.icon} aria-hidden="true">
          {is_stale ? "🕰️" : "💡"}
        </span>
        <h3 className={styles.title}>{is_stale ? "Note to Revisit" : "Note of the Day"}</h3>
        {is_stale && <span className={styles.staleBadge}>Needs Review</span>}
      </div>

      <Link href={`/knowledge-base/notes/${note.id}`} className={styles.noteCard}>
        <div className={styles.noteTitle}>{note.title || note.id}</div>
        <p className={styles.notePreview}>{previewContent}</p>
        <div className={styles.noteMeta}>
          <code className={styles.noteId}>{note.id}</code>
          {is_stale && note.days_stale && (
            <span className={styles.daysStale}>{note.days_stale} days since last update</span>
          )}
        </div>
      </Link>

      <p className={styles.message}>{message}</p>
    </div>
  );
}
