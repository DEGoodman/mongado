"use client";

import { useState, useEffect } from "react";
import { logger } from "@/lib/logger";
import styles from "./PostSaveAISuggestions.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface LinkSuggestion {
  note_id: string;
  title: string;
  confidence: number;
  reason: string;
}

interface PostSaveAISuggestionsProps {
  noteId: string;
  isOpen: boolean;
  onClose: () => void;
  onInsertLink: (noteId: string) => void;
}

export default function PostSaveAISuggestions({
  noteId,
  isOpen,
  onClose,
  onInsertLink,
}: PostSaveAISuggestionsProps) {
  const [linkSuggestions, setLinkSuggestions] = useState<LinkSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch suggestions when modal opens
  useEffect(() => {
    if (isOpen && noteId) {
      fetchSuggestions();
    }
  }, [isOpen, noteId]);

  const fetchSuggestions = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_URL}/api/notes/${noteId}/suggest-links`, {
        method: "POST",
      });

      if (!response.ok) {
        throw new Error("Failed to fetch link suggestions");
      }

      const data = await response.json();
      setLinkSuggestions(data.suggestions || []);

      logger.info("Post-save AI link suggestions fetched", {
        count: data.suggestions?.length || 0,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load suggestions";
      setError(message);
      logger.error("Failed to fetch post-save suggestions", err);
    } finally {
      setLoading(false);
    }
  };

  const handleInsertLink = (linkNoteId: string) => {
    onInsertLink(linkNoteId);
    // Keep modal open so user can add multiple links
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        <div className={styles.header}>
          <h3 className={styles.title}>✨ AI found related notes</h3>
          <button onClick={onClose} className={styles.closeButton} aria-label="Close">
            <svg className={styles.closeIcon} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {loading && (
          <div className={styles.loadingContainer}>
            <div className={styles.spinner}></div>
            <p className={styles.loadingText}>Finding related notes...</p>
          </div>
        )}

        {error && <div className={styles.errorBanner}>{error}</div>}

        {!loading && !error && linkSuggestions.length === 0 && (
          <div className={styles.emptyContainer}>
            <p className={styles.emptyTitle}>No related notes found.</p>
            <p className={styles.emptySubtitle}>This note might be exploring a new topic!</p>
          </div>
        )}

        {!loading && linkSuggestions.length > 0 && (
          <div className={styles.suggestionsList}>
            {linkSuggestions.map((suggestion, index) => (
              <div key={index} className={styles.suggestionCard}>
                <div className={styles.suggestionHeader}>
                  <div className={styles.suggestionMeta}>
                    <div className={styles.suggestionTopRow}>
                      <code className={styles.suggestionNoteId}>{suggestion.note_id}</code>
                      <span className={styles.suggestionConfidence}>
                        {Math.round(suggestion.confidence * 100)}% match
                      </span>
                    </div>
                    {suggestion.title && (
                      <p className={styles.suggestionTitle}>{suggestion.title}</p>
                    )}
                  </div>
                  <button
                    onClick={() => handleInsertLink(suggestion.note_id)}
                    className={styles.suggestionAction}
                  >
                    + Add Link
                  </button>
                </div>
                <p className={styles.suggestionReason}>{suggestion.reason}</p>
              </div>
            ))}
          </div>
        )}

        <div className={styles.footer}>
          <button onClick={onClose} className={styles.footerButton}>
            {linkSuggestions.length > 0 ? "Done" : "Close"}
          </button>
        </div>
      </div>
    </div>
  );
}
