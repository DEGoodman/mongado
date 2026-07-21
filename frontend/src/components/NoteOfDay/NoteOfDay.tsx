/**
 * NoteOfDay Component
 * Widget surfacing a random note for serendipitous rediscovery.
 *
 * This used to prefer notes untouched for 60+ days and badge them "Needs
 * Review". Removed in #262: every note was past the threshold, so the badge
 * fired on all of them. Age is not a defect in a Zettelkasten - real problems
 * are surfaced by Inspire and the quick lists.
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
}

interface NoteOfDayData {
  note: Note;
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

  const { note } = data;
  const previewContent = note.content.slice(0, 150) + (note.content.length > 150 ? "..." : "");

  return (
    <div className={styles.noteOfDay}>
      <div className={styles.header}>
        <h3 className={styles.title}>Note of the day</h3>
      </div>

      <Link href={`/knowledge-base/notes/${note.id}`} className={styles.noteCard}>
        <div className={styles.noteTitle}>{note.title || note.id}</div>
        <p className={styles.notePreview}>{previewContent}</p>
        <div className={styles.noteMeta}>
          <code className={styles.noteId}>{note.id}</code>
        </div>
      </Link>
    </div>
  );
}
