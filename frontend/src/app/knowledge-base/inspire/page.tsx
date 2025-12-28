"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getSuggestions, Suggestion } from "@/lib/api/inspire";
import { logger } from "@/lib/logger";
import Breadcrumb from "@/components/Breadcrumb";
import styles from "./page.module.scss";

export default function InspirePage() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasLlm, setHasLlm] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchSuggestions = async () => {
    try {
      const response = await getSuggestions(6);
      setSuggestions(response.suggestions);
      setHasLlm(response.has_llm);
      logger.info("Suggestions loaded", { count: response.suggestions.length });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load suggestions";
      setError(message);
      logger.error("Failed to load suggestions", err);
    }
  };

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await fetchSuggestions();
      setLoading(false);
    };
    load();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchSuggestions();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSkeleton}>
            <div className={styles.skeletonHeader}></div>
            <div className={styles.skeletonGrid}>
              <div className={styles.skeletonCard}></div>
              <div className={styles.skeletonCard}></div>
              <div className={styles.skeletonCard}></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.errorContainer}>
          <div className={styles.errorCard}>
            <h2 className={styles.errorTitle}>Error</h2>
            <p className={styles.errorMessage}>{error}</p>
            <Link href="/knowledge-base" className={styles.backLink}>
              Back to Knowledge Base
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.headerTop}>
            <Breadcrumb section="inspire" />
          </div>
          <div className={styles.titleRow}>
            <div className={styles.titleSection}>
              <h1 className={styles.title}>Inspire Me</h1>
              <p className={styles.subtitle}>Suggestions to improve your knowledge base</p>
            </div>
            <div className={styles.actions}>
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className={styles.refreshButton}
              >
                {refreshing ? "Refreshing..." : "Refresh Suggestions"}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className={styles.main}>
        {/* AI Status */}
        <div className={styles.aiStatus}>
          {hasLlm ? (
            <span className={styles.aiEnabled}>AI-powered suggestions</span>
          ) : (
            <span className={styles.aiDisabled}>Basic suggestions (AI unavailable)</span>
          )}
        </div>

        {/* Empty State */}
        {suggestions.length === 0 && (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>🎉</div>
            <h3 className={styles.emptyTitle}>Your knowledge base looks great!</h3>
            <p className={styles.emptyMessage}>
              No suggestions right now. Keep adding notes and links to grow your knowledge graph.
            </p>
            <Link href="/knowledge-base/notes/new" className={styles.createButton}>
              Create New Note
            </Link>
          </div>
        )}

        {/* Suggestions Grid */}
        {suggestions.length > 0 && (
          <div className={styles.suggestionsGrid}>
            {suggestions.map((suggestion, index) => (
              <div key={index} className={`${styles.suggestionCard} ${styles[suggestion.type]}`}>
                <div className={styles.cardHeader}>
                  <span className={styles.typeBadge}>
                    {suggestion.type === "gap" ? "📝 Gap" : "🔗 Connection"}
                  </span>
                </div>

                <h3 className={styles.cardTitle}>{suggestion.title}</h3>
                <p className={styles.cardDescription}>{suggestion.description}</p>

                <div className={styles.relatedNotes}>
                  <span className={styles.relatedLabel}>Related:</span>
                  <div className={styles.noteLinks}>
                    {suggestion.related_notes.map((noteId) => (
                      <Link
                        key={noteId}
                        href={`/knowledge-base/notes/${noteId}`}
                        className={styles.noteLink}
                      >
                        {noteId}
                      </Link>
                    ))}
                  </div>
                </div>

                <div className={styles.cardActions}>
                  {suggestion.type === "gap" && suggestion.related_notes.length > 0 && (
                    <Link
                      href={`/knowledge-base/notes/${suggestion.related_notes[0]}/edit`}
                      className={styles.actionButton}
                    >
                      {suggestion.action_text}
                    </Link>
                  )}
                  {suggestion.type === "connection" && suggestion.related_notes.length > 0 && (
                    <Link
                      href={`/knowledge-base/notes/${suggestion.related_notes[0]}`}
                      className={styles.actionButton}
                    >
                      {suggestion.action_text}
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Help Text */}
        <div className={styles.helpSection}>
          <h4 className={styles.helpTitle}>How it works</h4>
          <div className={styles.helpGrid}>
            <div className={styles.helpItem}>
              <span className={styles.helpIcon}>📝</span>
              <div>
                <strong>Gap suggestions</strong>
                <p>Notes that are short or have few connections. Consider expanding them.</p>
              </div>
            </div>
            <div className={styles.helpItem}>
              <span className={styles.helpIcon}>🔗</span>
              <div>
                <strong>Connection suggestions</strong>
                <p>Similar notes that aren&apos;t linked. Consider adding wikilinks.</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
