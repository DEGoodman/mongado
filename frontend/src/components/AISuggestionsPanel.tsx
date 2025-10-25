"use client";

import { useState } from "react";
import { logger } from "@/lib/logger";
import type { AiMode } from "@/lib/settings";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

interface AISuggestionsPanelProps {
  noteId: string;
  mode: AiMode;
  onAddTag: (tag: string) => void;
  onInsertLink: (noteId: string) => void;
}

export default function AISuggestionsPanel({
  noteId,
  mode,
  onAddTag,
  onInsertLink,
}: AISuggestionsPanelProps) {
  const [tagSuggestions, setTagSuggestions] = useState<TagSuggestion[]>([]);
  const [linkSuggestions, setLinkSuggestions] = useState<LinkSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestions = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch both suggestions in parallel
      const [tagsResponse, linksResponse] = await Promise.all([
        fetch(`${API_URL}/api/notes/${noteId}/suggest-tags`, { method: "POST" }),
        fetch(`${API_URL}/api/notes/${noteId}/suggest-links`, { method: "POST" }),
      ]);

      if (!tagsResponse.ok || !linksResponse.ok) {
        throw new Error("Failed to fetch AI suggestions");
      }

      const tagsData = await tagsResponse.json();
      const linksData = await linksResponse.json();

      setTagSuggestions(tagsData.suggestions || []);
      setLinkSuggestions(linksData.suggestions || []);

      logger.info("AI suggestions fetched", {
        tags: tagsData.count,
        links: linksData.count,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load suggestions";
      setError(message);
      logger.error("Failed to fetch AI suggestions", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">✨ AI Suggestions</h3>
        {mode === "on-demand" && (
          <button
            onClick={fetchSuggestions}
            disabled={loading}
            className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-blue-700 disabled:bg-gray-300"
          >
            {loading ? "Loading..." : "Get Suggestions"}
          </button>
        )}
        {mode === "real-time" && (
          <span className="rounded-lg bg-green-100 px-3 py-1.5 text-xs font-medium text-green-800">
            Real-time mode
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {!loading && tagSuggestions.length === 0 && linkSuggestions.length === 0 && !error && (
        <p className="text-sm text-gray-500">
          {mode === "on-demand"
            ? 'Click "Get Suggestions" to see AI-powered tag and link recommendations.'
            : "Suggestions will appear automatically as you type."}
        </p>
      )}

      {/* Tag Suggestions */}
      {tagSuggestions.length > 0 && (
        <div className="mb-4">
          <h4 className="mb-2 text-sm font-semibold text-gray-700">🏷️ Suggested Tags</h4>
          <div className="space-y-2">
            {tagSuggestions.map((suggestion, index) => (
              <div
                key={index}
                className="rounded-lg border border-gray-200 p-3 transition-colors hover:border-blue-300 hover:bg-blue-50"
              >
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-medium text-gray-900">{suggestion.tag}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      {Math.round(suggestion.confidence * 100)}%
                    </span>
                    <button
                      onClick={() => onAddTag(suggestion.tag)}
                      className="rounded bg-blue-600 px-2 py-1 text-xs text-white transition-colors hover:bg-blue-700"
                    >
                      Add
                    </button>
                  </div>
                </div>
                <p className="text-xs text-gray-600">{suggestion.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Link Suggestions */}
      {linkSuggestions.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-semibold text-gray-700">🔗 Suggested Links</h4>
          <div className="space-y-2">
            {linkSuggestions.map((suggestion, index) => (
              <div
                key={index}
                className="rounded-lg border border-gray-200 p-3 transition-colors hover:border-blue-300 hover:bg-blue-50"
              >
                <div className="mb-1 flex items-center justify-between">
                  <div>
                    <span className="font-medium text-gray-900">{suggestion.title}</span>
                    <code className="ml-2 text-xs text-gray-500">{suggestion.note_id}</code>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      {Math.round(suggestion.confidence * 100)}%
                    </span>
                    <button
                      onClick={() => onInsertLink(suggestion.note_id)}
                      className="rounded bg-blue-600 px-2 py-1 text-xs text-white transition-colors hover:bg-blue-700"
                    >
                      Insert
                    </button>
                  </div>
                </div>
                <p className="text-xs text-gray-600">{suggestion.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
