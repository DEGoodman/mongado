"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  ArrowsMerge,
  ArrowUpRight,
  Article,
  LinkSimple,
  Path,
  PlugsConnected,
  Scissors,
  Sparkle,
  TreeStructure,
} from "@phosphor-icons/react";
import Link from "next/link";
import { getSuggestions, Suggestion, SuggestionType } from "@/lib/api/inspire";
import { logger } from "@/lib/logger";
import Breadcrumb from "@/components/Breadcrumb";
import { LoadingState, ErrorState } from "@/components/PageState";
import styles from "./page.module.scss";

type LoadingPhase = "initial" | "fast-data" | "ai-enhancing" | "complete";

/** How each suggestion type is labelled and routed. */
const TYPE_CONFIG: Record<
  SuggestionType,
  { label: string; family: "fix" | "build"; href: (s: Suggestion) => string }
> = {
  orphan: {
    label: "Orphan",
    family: "fix",
    href: (s) => `/knowledge-base/notes/${s.related_notes[0]}/edit`,
  },
  duplicate: {
    label: "Duplicate",
    family: "fix",
    href: (s) => `/knowledge-base/notes/${s.related_notes[0]}`,
  },
  split: {
    label: "Too broad",
    family: "fix",
    href: (s) => `/knowledge-base/notes/${s.related_notes[0]}/edit`,
  },
  connection: {
    label: "Connection",
    family: "build",
    href: (s) => `/knowledge-base/notes/${s.related_notes[0]}/edit`,
  },
  hub: {
    label: "Hub",
    family: "build",
    // Prefill a hub note with wikilinks to every note in the cluster
    href: (s) =>
      `/knowledge-base/notes/new?content=${encodeURIComponent(
        s.related_notes.map((id) => `- [[${id}]]`).join("\n")
      )}`,
  },
  promote: {
    label: "Promote note",
    family: "build",
    href: (s) => `/knowledge-base/notes/${s.related_notes[0]}`,
  },
  article: {
    label: "Uncovered topic",
    family: "build",
    href: (s) => `/knowledge-base/notes/${s.related_notes[0]}`,
  },
};

const TYPE_ICONS: Record<SuggestionType, React.ReactNode> = {
  orphan: <PlugsConnected size={14} aria-hidden="true" />,
  duplicate: <ArrowsMerge size={14} aria-hidden="true" />,
  split: <Scissors size={14} aria-hidden="true" />,
  connection: <LinkSimple size={14} aria-hidden="true" />,
  hub: <TreeStructure size={14} aria-hidden="true" />,
  promote: <ArrowUpRight size={14} aria-hidden="true" />,
  article: <Article size={14} aria-hidden="true" />,
};

const SUGGESTION_LIMIT = 6;

export default function InspirePage() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loadingPhase, setLoadingPhase] = useState<LoadingPhase>("initial");
  const [error, setError] = useState<string | null>(null);
  const [hasLlm, setHasLlm] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  // Distinguishes "AI was asked and failed" from "AI was never asked"
  const [llmFailed, setLlmFailed] = useState(false);
  const hasLoaded = useRef(false);

  const fetchSuggestions = useCallback(async (refresh: boolean) => {
    setError(null);
    setLlmFailed(false);

    try {
      // Phase 1: templated wording, no LLM - paints immediately
      setLoadingPhase("fast-data");
      const fast = await getSuggestions(SUGGESTION_LIMIT, { refresh, skipLlm: true });
      setSuggestions(fast.suggestions);
      setHasLlm(false);
      logger.info("Templated suggestions ready", { count: fast.suggestions.length });

      // Phase 2: same findings, phrased by the LLM
      if (fast.suggestions.length > 0) {
        setLoadingPhase("ai-enhancing");
        try {
          const enhanced = await getSuggestions(SUGGESTION_LIMIT, { refresh });
          if (enhanced.suggestions.length > 0) {
            setSuggestions(enhanced.suggestions);
          }
          // Always reflect reality - a stale "AI-powered" badge over templated
          // output was the bug in #259
          setHasLlm(enhanced.has_llm);
          setLlmFailed(!enhanced.has_llm);
          logger.info("Suggestions finalized", {
            count: enhanced.suggestions.length,
            hasLlm: enhanced.has_llm,
            cached: enhanced.cached,
          });
        } catch (aiErr) {
          // Keep the templated suggestions, but say so
          setHasLlm(false);
          setLlmFailed(true);
          logger.warn("AI phrasing failed, keeping templated suggestions", aiErr);
        }
      }

      setLoadingPhase("complete");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load suggestions";
      setError(message);
      setLoadingPhase("complete");
      logger.error("Failed to load suggestions", err);
    }
  }, []);

  useEffect(() => {
    if (hasLoaded.current) return;
    hasLoaded.current = true;
    fetchSuggestions(false);
  }, [fetchSuggestions]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchSuggestions(true);
    setRefreshing(false);
  };

  // Show skeleton only on initial load
  if (loadingPhase === "initial") {
    return (
      <div className={styles.container}>
        <LoadingState variant="cards" label="Loading inspiration" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <ErrorState message={error} backHref="/knowledge-base" backLabel="Back to Knowledge Base" />
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
        <div className={styles.aiStatus} role="status">
          {loadingPhase === "ai-enhancing" ? (
            <span className={styles.aiLoading}>
              <span className={styles.spinner}></span>
              AI is phrasing suggestions...
            </span>
          ) : hasLlm ? (
            <span className={styles.aiEnabled}>
              <Sparkle size={14} aria-hidden="true" /> AI-powered suggestions
            </span>
          ) : llmFailed ? (
            <span className={styles.aiDisabled}>
              AI unavailable — showing the same findings in standard wording
            </span>
          ) : loadingPhase === "complete" ? (
            <span className={styles.aiDisabled}>Standard suggestions</span>
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
              No orphaned notes, duplicates, or uncovered topics right now. Keep adding notes and
              links to grow your knowledge graph.
            </p>
            <Link href="/knowledge-base/notes/new" className={styles.createButton}>
              Create New Note
            </Link>
          </div>
        )}

        {/* Suggestions Grid */}
        {suggestions.length > 0 && (
          <div className={styles.suggestionsGrid}>
            {suggestions.map((suggestion, index) => {
              const config = TYPE_CONFIG[suggestion.type];
              // Defend against an unrecognized type from the LLM
              if (!config) return null;

              return (
                <div
                  key={`${suggestion.type}-${suggestion.related_notes.join("-")}-${index}`}
                  className={`${styles.suggestionCard} ${styles[config.family]}`}
                >
                  <div className={styles.cardHeader}>
                    <span className={styles.typeBadge}>
                      {TYPE_ICONS[suggestion.type]}
                      {config.label}
                    </span>
                  </div>

                  <h3 className={styles.cardTitle}>{suggestion.title}</h3>
                  <p className={styles.cardDescription}>{suggestion.description}</p>

                  {suggestion.related_notes.length > 0 && (
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
                  )}

                  {suggestion.related_notes.length > 0 && (
                    <div className={styles.cardActions}>
                      <Link href={config.href(suggestion)} className={styles.actionButton}>
                        {suggestion.action_text}
                      </Link>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Help Text */}
        <div className={styles.helpSection}>
          <h4 className={styles.helpTitle}>How it works</h4>
          <div className={styles.helpGrid}>
            <div className={styles.helpItem}>
              <span className={styles.helpIcon} aria-hidden="true">
                <Path size={20} />
              </span>
              <div>
                <strong>Repairs</strong>
                <p>
                  Orphaned notes nothing links to, the same idea captured twice, or a note holding
                  more than one idea.
                </p>
              </div>
            </div>
            <div className={styles.helpItem}>
              <span className={styles.helpIcon} aria-hidden="true">
                <TreeStructure size={20} />
              </span>
              <div>
                <strong>Things to build</strong>
                <p>
                  Wikilinks between related notes, hub notes that index a cluster, and article ideas
                  from topics your notes already cover.
                </p>
              </div>
            </div>
          </div>
          <p className={styles.helpFootnote}>
            Short notes are never flagged — an atomic note is supposed to be brief.
          </p>
        </div>
      </main>
    </div>
  );
}
