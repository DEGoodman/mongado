"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  getSuggestions,
  getKnowledgeGaps,
  getConnectionOpportunities,
  Suggestion,
  GapNote,
  ConnectionOpportunity,
} from "@/lib/api/inspire";
import { logger } from "@/lib/logger";
import Breadcrumb from "@/components/Breadcrumb";
import styles from "./page.module.scss";

type LoadingPhase = "initial" | "fast-data" | "ai-enhancing" | "complete";

export default function InspirePage() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loadingPhase, setLoadingPhase] = useState<LoadingPhase>("initial");
  const [error, setError] = useState<string | null>(null);
  const [hasLlm, setHasLlm] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // Convert raw data to suggestion format for quick display
  const buildQuickSuggestions = useCallback(
    (gaps: GapNote[], connections: ConnectionOpportunity[]): Suggestion[] => {
      const quickSuggestions: Suggestion[] = [];

      // Add gap suggestions
      gaps.slice(0, 3).forEach((gap) => {
        quickSuggestions.push({
          type: "gap",
          title: gap.title || gap.note_id,
          description: `This note is ${gap.is_short ? "short" : ""}${gap.is_short && gap.has_few_links ? " and " : ""}${gap.has_few_links ? "has few connections" : ""}. Consider expanding it.`,
          related_notes: [gap.note_id],
          action_text: "Expand Note",
        });
      });

      // Add connection suggestions
      connections.slice(0, 3).forEach((conn) => {
        quickSuggestions.push({
          type: "connection",
          title: `Link ${conn.note_a_title || conn.note_a_id} ↔ ${conn.note_b_title || conn.note_b_id}`,
          description: `These notes are ${Math.round(conn.similarity * 100)}% similar but not linked.`,
          related_notes: [conn.note_a_id, conn.note_b_id],
          action_text: "View Note",
        });
      });

      return quickSuggestions;
    },
    []
  );

  const fetchSuggestions = useCallback(async () => {
    setError(null);

    // Phase 1: Quickly fetch raw data (no LLM)
    setLoadingPhase("fast-data");
    try {
      const [gapsResponse, connectionsResponse] = await Promise.all([
        getKnowledgeGaps(500, 1, 5),
        getConnectionOpportunities(0.7, 5),
      ]);

      // Show quick suggestions immediately
      const quickSuggestions = buildQuickSuggestions(
        gapsResponse.gaps,
        connectionsResponse.connections
      );
      setSuggestions(quickSuggestions);
      logger.info("Quick suggestions ready", { count: quickSuggestions.length });

      // Phase 2: Fetch AI-enhanced suggestions
      if (quickSuggestions.length > 0) {
        setLoadingPhase("ai-enhancing");
        try {
          const aiResponse = await getSuggestions(6);
          if (aiResponse.suggestions.length > 0) {
            setSuggestions(aiResponse.suggestions);
            setHasLlm(aiResponse.has_llm);
            logger.info("AI suggestions ready", {
              count: aiResponse.suggestions.length,
              hasLlm: aiResponse.has_llm,
            });
          }
        } catch (aiErr) {
          // AI failed but we still have quick suggestions, just log it
          logger.warn("AI enhancement failed, keeping quick suggestions", aiErr);
        }
      }

      setLoadingPhase("complete");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load suggestions";
      setError(message);
      setLoadingPhase("complete");
      logger.error("Failed to load suggestions", err);
    }
  }, [buildQuickSuggestions]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchSuggestions();
    setRefreshing(false);
  };

  // Show skeleton only on initial load
  if (loadingPhase === "initial") {
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
          {loadingPhase === "ai-enhancing" ? (
            <span className={styles.aiLoading}>
              <span className={styles.spinner}></span>
              AI is enhancing suggestions...
            </span>
          ) : hasLlm ? (
            <span className={styles.aiEnabled}>AI-powered suggestions</span>
          ) : loadingPhase === "complete" ? (
            <span className={styles.aiDisabled}>Basic suggestions (AI unavailable)</span>
          ) : (
            <span className={styles.aiLoading}>Loading suggestions...</span>
          )}
        </div>

        {/* Empty State - only show when complete with no suggestions */}
        {loadingPhase === "complete" && suggestions.length === 0 && (
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
