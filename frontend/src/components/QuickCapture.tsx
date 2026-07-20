"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Lightning } from "@phosphor-icons/react";
import { createNote } from "@/lib/api/notes";
import { saveDraft } from "@/lib/draft";
import { logger } from "@/lib/logger";
import Toast from "@/components/Toast";
import styles from "./QuickCapture.module.scss";

interface QuickCaptureProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Quick Capture modal (#154 Phase 1): capture a thought without leaving the
 * current page. Opened from the nav button or the global "n" shortcut.
 *
 * Save = createNote (auth required; the trigger is only shown when
 * authenticated). On failure the text is stashed in the shared editor draft
 * (lib/draft), so nothing is lost - the note editor restores it.
 */
export default function QuickCapture({ isOpen, onClose }: QuickCaptureProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const contentRef = useRef<HTMLTextAreaElement>(null);

  // Focus the content field when opening
  useEffect(() => {
    if (isOpen) {
      setError(null);
      // Next tick so the element exists after the conditional render
      requestAnimationFrame(() => contentRef.current?.focus());
    }
  }, [isOpen]);

  const handleClose = useCallback(() => {
    setError(null);
    onClose();
  }, [onClose]);

  const handleSave = useCallback(async () => {
    if (!content.trim() || saving) return;

    const tagArray = tags
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t);

    try {
      setSaving(true);
      setError(null);

      const note = await createNote({
        content,
        title: title.trim() || undefined,
        tags: tagArray.length > 0 ? tagArray : undefined,
      });

      logger.info("Quick capture saved", { id: note.id });
      setTitle("");
      setContent("");
      setTags("");
      setToast(`Captured ${note.id}`);
      onClose();
    } catch (err) {
      // Stash in the shared editor draft so the thought is never lost
      saveDraft({ title, content, tags, isReference: false });
      const message = err instanceof Error ? err.message : "Failed to save";
      setError(message);
      logger.error("Quick capture failed; stashed as draft", err);
    } finally {
      setSaving(false);
    }
  }, [content, title, tags, saving, onClose]);

  // Esc closes, Cmd/Ctrl+Enter saves
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        handleClose();
      } else if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        void handleSave();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleClose, handleSave]);

  return (
    <>
      {isOpen && (
        <div className={styles.overlay} onClick={handleClose}>
          <div
            className={styles.modal}
            role="dialog"
            aria-modal="true"
            aria-label="Quick capture"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.header}>
              <h2 className={styles.title}>
                <Lightning size={16} aria-hidden="true" /> Quick capture
              </h2>
              <button onClick={handleClose} className={styles.closeButton} aria-label="Close">
                ✕
              </button>
            </div>

            {error && (
              <div className={styles.errorBox} role="alert">
                <p>{error}</p>
                <p className={styles.errorHint}>
                  Your text is preserved as a draft —{" "}
                  <Link href="/knowledge-base/notes/new" onClick={handleClose}>
                    open the editor
                  </Link>{" "}
                  to continue.
                </p>
              </div>
            )}

            <textarea
              ref={contentRef}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Capture the thought…"
              className={styles.contentInput}
              rows={5}
            />

            <div className={styles.metaRow}>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Title (optional)"
                className={styles.metaInput}
              />
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="Tags (optional)"
                className={styles.metaInput}
              />
            </div>

            <div className={styles.actions}>
              <span className={styles.hint}>
                <kbd>⌘↵</kbd> save · <kbd>esc</kbd> close
              </span>
              <button
                onClick={() => void handleSave()}
                disabled={saving || !content.trim()}
                className={styles.saveButton}
              >
                {saving ? "Saving…" : "Capture"}
              </button>
            </div>
          </div>
        </div>
      )}

      <Toast
        message={toast ?? ""}
        isVisible={toast !== null}
        onClose={() => setToast(null)}
        duration={4000}
      />
    </>
  );
}
