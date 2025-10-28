"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { logger } from "@/lib/logger";
import type { AiMode } from "@/lib/settings";
import Toast from "@/components/Toast";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEBOUNCE_MS = 5000; // 5 second debounce for automatic mode

interface TagSuggestion {
  tag: string;
  confidence: number;
  reason: string;
}

interface LinkSuggestion {
  note_id: string;
  title: string;
  confidence: number;
  reason: string;
}

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
  onAddTag,
  onInsertLink,
}: AISuggestionsPanelProps) {
  const [tagSuggestions, setTagSuggestions] = useState<TagSuggestion[]>([]);
  const [linkSuggestions, setLinkSuggestions] = useState<LinkSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [cachedData, setCachedData] = useState<CachedSuggestions | null>(null);
  const [isOutdated, setIsOutdated] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const debounceTimer = useRef<NodeJS.Timeout | null>(null);

  // Check if current content matches cached content
  useEffect(() => {
    if (cachedData && content) {
      const currentHash = hashContent(content);
      setIsOutdated(currentHash !== cachedData.contentHash);
    }
  }, [content, cachedData]);

  const fetchSuggestions = useCallback(async () => {
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
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">✨ AI Suggestions</h3>
          {mode === "real-time" && (
            <div className="mt-1 flex items-center gap-2">
              {loading && <div className="h-2 w-2 animate-pulse rounded-full bg-green-500"></div>}
              <span className="text-xs text-green-700">Automatic mode</span>
            </div>
          )}
        </div>
        {isOutdated && !loading && (
          <button
            onClick={fetchSuggestions}
            className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50"
            title="Content has changed - refresh suggestions"
          >
            <span>🔄</span>
            <span>Refresh</span>
          </button>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="space-y-4">
          <div className="rounded-lg bg-blue-50 p-4">
            <div className="flex items-center gap-3">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
              <p className="text-sm text-blue-900">{loadingStatus}</p>
            </div>
          </div>

          {/* Skeleton UI */}
          <div className="space-y-4">
            <div>
              <div className="mb-3 h-4 w-32 animate-pulse rounded bg-gray-200"></div>
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <div
                    key={i}
                    className="animate-pulse rounded-lg border border-gray-200 bg-gray-50 p-4"
                  >
                    <div className="mb-2 h-4 w-3/4 rounded bg-gray-200"></div>
                    <div className="h-3 w-full rounded bg-gray-200"></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && !hasAnySuggestions && !error && (
        <p className="text-sm leading-relaxed text-gray-500">
          {mode === "on-demand"
            ? "No suggestions yet. Click the button above to generate AI recommendations."
            : "Suggestions will appear automatically as you type."}
        </p>
      )}

      {/* Outdated Warning */}
      {isOutdated && !loading && hasAnySuggestions && (
        <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
          ⚠️ Suggestions may be outdated - content has changed since generation.
        </div>
      )}

      {/* Tag Suggestions */}
      {!loading && tagSuggestions.length > 0 && (
        <div className="mb-6">
          <h4 className="mb-3 text-sm font-semibold text-gray-700">🏷️ Suggested Tags</h4>
          <div className="space-y-3">
            {tagSuggestions.map((suggestion, index) => (
              <div
                key={index}
                className="rounded-lg border border-gray-200 bg-gray-50 p-4 transition-colors hover:border-blue-300 hover:bg-blue-50"
              >
                <div className="mb-2 flex items-start justify-between gap-3">
                  <span className="font-medium text-gray-900">{suggestion.tag}</span>
                  <button
                    onClick={() => {
                      onAddTag(suggestion.tag);
                      // Remove from current suggestions (optimistic UI)
                      setTagSuggestions((prev) => prev.filter((_, i) => i !== index));
                    }}
                    className="flex-shrink-0 rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700"
                  >
                    Add
                  </button>
                </div>
                <p className="text-xs leading-relaxed text-gray-600">{suggestion.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Link Suggestions */}
      {!loading && linkSuggestions.length > 0 && (
        <div>
          <h4 className="mb-3 text-sm font-semibold text-gray-700">🔗 Suggested Links</h4>
          <div className="space-y-3">
            {linkSuggestions.map((suggestion, index) => (
              <div
                key={index}
                className="rounded-lg border border-gray-200 bg-gray-50 p-4 transition-colors hover:border-blue-300 hover:bg-blue-50"
              >
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 font-medium text-gray-900">{suggestion.title}</div>
                    <code className="text-xs text-gray-500">{suggestion.note_id}</code>
                  </div>
                  <button
                    onClick={() => {
                      onInsertLink(suggestion.note_id);
                      // Remove from current suggestions (optimistic UI)
                      setLinkSuggestions((prev) => prev.filter((_, i) => i !== index));
                    }}
                    className="flex-shrink-0 rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700"
                  >
                    Insert
                  </button>
                </div>
                <p className="text-xs leading-relaxed text-gray-600">{suggestion.reason}</p>
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
  );
}
