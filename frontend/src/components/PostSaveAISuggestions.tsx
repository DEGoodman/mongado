"use client";

import { useState, useEffect } from "react";
import { logger } from "@/lib/logger";

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">✨ AI found related notes</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
          <div className="py-8 text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
            <p className="mt-2 text-sm text-gray-600">Finding related notes...</p>
          </div>
        )}

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        {!loading && !error && linkSuggestions.length === 0 && (
          <div className="py-8 text-center">
            <p className="text-gray-600">No related notes found.</p>
            <p className="mt-2 text-sm text-gray-500">This note might be exploring a new topic!</p>
          </div>
        )}

        {!loading && linkSuggestions.length > 0 && (
          <div className="space-y-3">
            {linkSuggestions.map((suggestion, index) => (
              <div
                key={index}
                className="rounded-lg border border-gray-200 p-3 transition-colors hover:border-blue-300 hover:bg-blue-50"
              >
                <div className="mb-2 flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <code className="rounded bg-gray-100 px-2 py-0.5 font-mono text-sm text-gray-700">
                        {suggestion.note_id}
                      </code>
                      <span className="text-xs text-gray-500">
                        {Math.round(suggestion.confidence * 100)}% match
                      </span>
                    </div>
                    {suggestion.title && (
                      <p className="mt-1 font-medium text-gray-900">{suggestion.title}</p>
                    )}
                  </div>
                  <button
                    onClick={() => handleInsertLink(suggestion.note_id)}
                    className="ml-2 whitespace-nowrap rounded bg-blue-600 px-3 py-1.5 text-sm text-white transition-colors hover:bg-blue-700"
                  >
                    + Add Link
                  </button>
                </div>
                <p className="text-sm text-gray-600">{suggestion.reason}</p>
              </div>
            ))}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition hover:bg-gray-50"
          >
            {linkSuggestions.length > 0 ? "Done" : "Close"}
          </button>
        </div>
      </div>
    </div>
  );
}
