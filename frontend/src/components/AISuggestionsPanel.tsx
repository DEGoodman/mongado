"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { logger } from "@/lib/logger";
import type { AiMode } from "@/lib/settings";
import Toast from "@/components/Toast";
import {
  streamAISuggestions,
  isStreamingSupported,
  type TagSuggestion,
  type LinkSuggestion,
  type StreamPhase,
} from "@/lib/aiSuggestionsStream";
import styles from "./AISuggestionsPanel.module.scss";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEBOUNCE_MS = 5000; // 5 second debounce for automatic mode

interface CachedSuggestions {
  tags: TagSuggestion[];
  links: LinkSuggestion[];
  contentHash: string;
}

interface AISuggestionsPanelProps {
  noteId: string;
  mode: AiMode;
  content?: string;
  isOpen: boolean;
  onClose?: () => void;
  onAddTag: (tag: string) => void;
  onInsertLink: (noteId: string) => void;
}

// Simple hash function for content
function hashContent(content: string): string {
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash.toString(36);
}

export default function AISuggestionsPanel({
  noteId,
  mode,
  content,
  isOpen,
  onClose,
  onAddTag,
  onInsertLink,
}: AISuggestionsPanelProps) {
  const [tagSuggestions, setTagSuggestions] = useState<TagSuggestion[]>([]);
  const [linkSuggestions, setLinkSuggestions] = useState<LinkSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState<string>("");
  const [streamPhase, setStreamPhase] = useState<StreamPhase>("idle");
  const [tokenCount, setTokenCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [cachedData, setCachedData] = useState<CachedSuggestions | null>(null);
  const [isOutdated, setIsOutdated] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);
  const streamCleanupRef = useRef<(() => void) | null>(null);

  // Check if current content matches cached content
  useEffect(() => {
    if (cachedData && content) {
      const currentHash = hashContent(content);
      setIsOutdated(currentHash !== cachedData.contentHash);
    }
  }, [content, cachedData]);

  // Streaming fetch using SSE
  const fetchSuggestionsStreaming = useCallback(() => {
    // Clean up any existing stream
    if (streamCleanupRef.current) {
      streamCleanupRef.current();
      streamCleanupRef.current = null;
    }

    setLoading(true);
    setError(null);
    setTagSuggestions([]);
    setLinkSuggestions([]);
    setStreamPhase("idle");
    setTokenCount(0);
    setLoadingStatus("Connecting to AI service...");

    const cleanup = streamAISuggestions(noteId, {
      onProgress: (phase) => {
        setStreamPhase(phase);
        setTokenCount(0); // Reset token count when phase changes
        if (phase === "tags") {
          setLoadingStatus("Generating tag suggestions...");
        } else if (phase === "links") {
          setLoadingStatus("Finding related notes...");
        }
      },
      onGenerating: (_phase, tokens) => {
        setTokenCount(tokens);
      },
      onTag: (tag) => {
        setTagSuggestions((prev) => [...prev, tag]);
      },
      onLink: (link) => {
        setLinkSuggestions((prev) => [...prev, link]);
      },
      onComplete: () => {
        setLoading(false);
        setLoadingStatus("");
        setStreamPhase("complete");

        // Cache the results after complete
        if (content) {
          const contentHash = hashContent(content);
          // Use the current state values at completion time
          setTagSuggestions((currentTags) => {
            setLinkSuggestions((currentLinks) => {
              setCachedData({
                tags: currentTags,
                links: currentLinks,
                contentHash,
              });
              return currentLinks;
            });
            return currentTags;
          });
          setIsOutdated(false);
        }

        logger.info("AI suggestions streaming complete");

        // Show toast notification for automatic mode
        if (mode === "real-time") {
          setShowToast(true);
        }
      },
      onError: (message) => {
        setError(message);
        setLoading(false);
        setLoadingStatus("");
        setStreamPhase("error");
        logger.error("AI suggestions streaming failed", { message });
      },
    });

    streamCleanupRef.current = cleanup;
  }, [noteId, content, mode]);

  // Non-streaming fallback fetch
  const fetchSuggestionsFallback = useCallback(async () => {
    setLoading(true);
    setError(null);
    setLoadingStatus("Generating AI suggestions... typically takes 10-15 seconds");

    try {
      // Fetch tags first
      setLoadingStatus("Finding relevant tags...");
      const tagsResponse = await fetch(`${API_URL}/api/notes/${noteId}/suggest-tags`, {
        method: "POST",
      });

      if (!tagsResponse.ok) {
        throw new Error("Failed to fetch tag suggestions");
      }

      const tagsData = await tagsResponse.json();
      setTagSuggestions(tagsData.suggestions || []);
      setLoadingStatus("Analyzing related notes...");

      // Then fetch links
      const linksResponse = await fetch(`${API_URL}/api/notes/${noteId}/suggest-links`, {
        method: "POST",
      });

      if (!linksResponse.ok) {
        throw new Error("Failed to fetch link suggestions");
      }

      const linksData = await linksResponse.json();
      setLinkSuggestions(linksData.suggestions || []);

      // Cache the results
      if (content) {
        const contentHash = hashContent(content);
        setCachedData({
          tags: tagsData.suggestions || [],
          links: linksData.suggestions || [],
          contentHash,
        });
        setIsOutdated(false);
      }

      logger.info("AI suggestions fetched", {
        tags: tagsData.count,
        links: linksData.count,
      });

      // Show toast notification for automatic mode
      if (mode === "real-time") {
        setShowToast(true);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load suggestions";
      setError(message);
      logger.error("Failed to fetch AI suggestions", err);
    } finally {
      setLoading(false);
      setLoadingStatus("");
    }
  }, [noteId, content, mode]);

  // Main fetch function - uses streaming if available
  const fetchSuggestions = useCallback(() => {
    if (isStreamingSupported()) {
      fetchSuggestionsStreaming();
    } else {
      fetchSuggestionsFallback();
    }
  }, [fetchSuggestionsStreaming, fetchSuggestionsFallback]);

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      if (streamCleanupRef.current) {
        streamCleanupRef.current();
      }
    };
  }, []);

  // On-demand mode: fetch when panel is opened (if no cached data or outdated)
  useEffect(() => {
    if (mode === "on-demand" && isOpen && content) {
      // Only fetch if we don't have suggestions or if content changed
      if (!cachedData || isOutdated) {
        fetchSuggestions();
      }
    }
  }, [mode, isOpen, content, cachedData, isOutdated, fetchSuggestions]);

  // Automatic mode: auto-fetch suggestions when content changes (debounced)
  useEffect(() => {
    if (mode !== "real-time" || !content || !isOpen) {
      return;
    }

    // Clear existing timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // Set new timer to fetch suggestions after debounce period
    debounceTimer.current = setTimeout(() => {
      // Only fetch if content is non-empty
      if (content.trim().length > 10) {
        fetchSuggestions();
      }
    }, DEBOUNCE_MS);

    // Cleanup timer on unmount or when dependencies change
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [mode, content, fetchSuggestions, isOpen]);

  if (!isOpen) {
    return null;
  }

  const totalSuggestions = tagSuggestions.length + linkSuggestions.length;
  const hasAnySuggestions = totalSuggestions > 0;

  return (
    <>
      {/* Backdrop for tablet/mobile */}
      <div className={styles.backdrop} onClick={onClose} />

      {/* Panel container - responsive positioning */}
      <div className={styles.panel}>
        <div className={styles.panelContent}>
          {/* Header with close button for mobile/tablet */}
          <div className={styles.header}>
            <div className={styles.headerLeft}>
              <h3 className={styles.title}>✨ AI Suggestions</h3>
              {mode === "real-time" && (
                <div className={styles.modeIndicator}>
                  {loading && <div className={styles.autoIndicatorDot}></div>}
                  <span className={styles.autoIndicatorLabel}>Automatic mode</span>
                </div>
              )}
            </div>
            <div className={styles.headerActions}>
              {isOutdated && !loading && (
                <button
                  onClick={fetchSuggestions}
                  className={styles.refreshButton}
                  title="Content has changed - refresh suggestions"
                >
                  <span className={styles.refreshIcon}>🔄</span>
                  <span className={styles.refreshLabel}>Refresh</span>
                </button>
              )}
              {/* Close button for mobile/tablet */}
              {onClose && (
                <button
                  onClick={onClose}
                  className={styles.closeButton}
                  aria-label="Close suggestions"
                >
                  <svg
                    className={styles.closeIcon}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Streaming Progress Indicator */}
          {loading && (
            <div className={styles.streamingProgress}>
              <div className={styles.loadingContent}>
                <div className={styles.spinner}></div>
                <div className={styles.progressText}>
                  <span className={styles.progressStatus}>
                    {loadingStatus}
                    {tokenCount > 0 && ` (${tokenCount} tokens)`}
                  </span>
                  <span className={styles.progressCounts}>
                    {tagSuggestions.length > 0 && `${tagSuggestions.length} tags`}
                    {tagSuggestions.length > 0 && streamPhase === "links" && ", "}
                    {streamPhase === "links" && `${linkSuggestions.length} links`}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Error State */}
          {error && !loading && <div className={styles.errorBanner}>{error}</div>}

          {/* Empty State - only show when not loading and no suggestions */}
          {!loading &&
            !hasAnySuggestions &&
            !error &&
            streamPhase !== "tags" &&
            streamPhase !== "links" && (
              <p className={styles.emptyState}>
                {mode === "on-demand"
                  ? "No suggestions yet. Click the button above to generate AI recommendations."
                  : "Suggestions will appear automatically as you type."}
              </p>
            )}

          {/* Outdated Warning */}
          {isOutdated && !loading && hasAnySuggestions && (
            <div className={styles.outdatedBanner}>
              ⚠️ Suggestions may be outdated - content has changed since generation.
            </div>
          )}

          {/* Tag Suggestions - show progressively during streaming */}
          {tagSuggestions.length > 0 && (
            <div className={styles.suggestionsSection}>
              <h4 className={styles.sectionTitle}>🏷️ Suggested Tags</h4>
              <div className={styles.suggestionsList}>
                {tagSuggestions.map((suggestion, index) => (
                  <div key={index} className={`${styles.suggestionCard} ${styles.fadeIn}`}>
                    <div className={styles.suggestionHeader}>
                      <span className={styles.suggestionTitle}>{suggestion.tag}</span>
                      <button
                        onClick={() => {
                          onAddTag(suggestion.tag);
                          // Remove from current suggestions (optimistic UI)
                          setTagSuggestions((prev) => prev.filter((_, i) => i !== index));
                        }}
                        className={styles.suggestionAction}
                      >
                        Add
                      </button>
                    </div>
                    <p className={styles.suggestionReason}>{suggestion.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Link Suggestions - show progressively during streaming */}
          {linkSuggestions.length > 0 && (
            <div className={styles.suggestionsSection}>
              <h4 className={styles.sectionTitle}>🔗 Suggested Links</h4>
              <div className={styles.suggestionsList}>
                {linkSuggestions.map((suggestion, index) => (
                  <div key={index} className={`${styles.suggestionCard} ${styles.fadeIn}`}>
                    <div className={styles.suggestionHeader}>
                      <div className={styles.suggestionMeta}>
                        <div className={styles.suggestionSubtitle}>{suggestion.title}</div>
                        <code className={styles.suggestionNoteId}>{suggestion.note_id}</code>
                      </div>
                      <button
                        onClick={() => {
                          onInsertLink(suggestion.note_id);
                          // Remove from current suggestions (optimistic UI)
                          setLinkSuggestions((prev) => prev.filter((_, i) => i !== index));
                        }}
                        className={styles.suggestionAction}
                      >
                        Insert
                      </button>
                    </div>
                    <p className={styles.suggestionReason}>{suggestion.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Toast for automatic mode */}
          <Toast
            message="AI suggestions ready"
            isVisible={showToast}
            onClose={() => setShowToast(false)}
            duration={4000}
          />
        </div>
      </div>
    </>
  );
}
