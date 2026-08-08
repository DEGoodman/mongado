"use client";

/**
 * Shared create/edit form for Library entries (#294).
 * Presentational: the parent owns submission (create vs update).
 */

import { useState } from "react";
import { LibraryEntryType, LIBRARY_ENTRY_TYPES } from "@/lib/api/library";
import styles from "./LibraryEntryForm.module.scss";

export interface LibraryFormValues {
  title: string;
  source_url: string;
  author: string;
  type: LibraryEntryType;
  summary: string;
  tags: string; // comma-separated in the form; parsed on submit
}

export const EMPTY_LIBRARY_VALUES: LibraryFormValues = {
  title: "",
  source_url: "",
  author: "",
  type: "book",
  summary: "",
  tags: "",
};

export function parseTags(tags: string): string[] {
  return tags
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);
}

interface LibraryEntryFormProps {
  initialValues?: LibraryFormValues;
  submitLabel: string;
  onSubmit: (values: LibraryFormValues) => Promise<void>;
  onCancelHref: string;
}

export default function LibraryEntryForm({
  initialValues = EMPTY_LIBRARY_VALUES,
  submitLabel,
  onSubmit,
  onCancelHref,
}: LibraryEntryFormProps) {
  const [values, setValues] = useState<LibraryFormValues>(initialValues);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof LibraryFormValues>(key: K, value: LibraryFormValues[K]) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!values.title.trim()) {
      setError("Title is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(values);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setSubmitting(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      {error && (
        <div className={styles.error} role="alert">
          {error}
        </div>
      )}

      <label className={styles.field}>
        <span className={styles.label}>Title *</span>
        <input
          type="text"
          value={values.title}
          onChange={(e) => set("title", e.target.value)}
          className={styles.input}
          required
        />
      </label>

      <div className={styles.row}>
        <label className={styles.field}>
          <span className={styles.label}>Type</span>
          <select
            value={values.type}
            onChange={(e) => set("type", e.target.value as LibraryEntryType)}
            className={styles.input}
          >
            {LIBRARY_ENTRY_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Author</span>
          <input
            type="text"
            value={values.author}
            onChange={(e) => set("author", e.target.value)}
            className={styles.input}
          />
        </label>
      </div>

      <label className={styles.field}>
        <span className={styles.label}>Source URL</span>
        <input
          type="url"
          value={values.source_url}
          onChange={(e) => set("source_url", e.target.value)}
          className={styles.input}
          placeholder="https://..."
        />
      </label>

      <label className={styles.field}>
        <span className={styles.label}>Tags</span>
        <input
          type="text"
          value={values.tags}
          onChange={(e) => set("tags", e.target.value)}
          className={styles.input}
          placeholder="comma, separated, tags"
        />
      </label>

      <label className={styles.field}>
        <span className={styles.label}>Summary</span>
        <textarea
          value={values.summary}
          onChange={(e) => set("summary", e.target.value)}
          className={styles.textarea}
          rows={8}
          placeholder="Your own summary. Markdown supported."
        />
        <span className={styles.hint}>Your own notes — Markdown supported.</span>
      </label>

      <div className={styles.actions}>
        <a href={onCancelHref} className={styles.cancel}>
          Cancel
        </a>
        <button type="submit" className={styles.submit} disabled={submitting}>
          {submitting ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
