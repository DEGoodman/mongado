"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listNotes, Note, formatNoteDate } from "@/lib/api/notes";
import { logger } from "@/lib/logger";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);

  useEffect(() => {
    async function fetchNotes() {
      try {
        setLoading(true);
        const response = await listNotes();
        setNotes(response.notes);
        logger.info("Notes loaded", { count: response.count });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load notes";
        setError(message);
        logger.error("Failed to load notes", err);
      } finally {
        setLoading(false);
      }
    }

    fetchNotes();
  }, []);

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-8"></div>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h2 className="text-red-800 font-semibold mb-2">Error</h2>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Notes</h1>
          <p className="text-gray-600 mt-1">
            Your Zettelkasten knowledge base ({notes.length} notes)
          </p>
        </div>
        <Link
          href="/notes/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          + New Note
        </Link>
      </div>

      {/* Notes list */}
      {notes.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No notes yet</h3>
          <p className="mt-1 text-sm text-gray-500">
            Get started by creating your first note
          </p>
          <div className="mt-6">
            <Link
              href="/notes/new"
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Create Note
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {notes.map((note) => (
            <Link
              key={note.id}
              href={`/notes/${note.id}`}
              className="block bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-md transition"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  {/* Note ID and title */}
                  <div className="flex items-center gap-2 mb-1">
                    <code className="text-sm font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                      {note.id}
                    </code>
                    {note.is_ephemeral && (
                      <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                        ephemeral
                      </span>
                    )}
                  </div>

                  {note.title && (
                    <h3 className="text-lg font-semibold text-gray-900 mb-1">
                      {note.title}
                    </h3>
                  )}

                  {/* Content preview */}
                  <p className="text-gray-600 text-sm line-clamp-2 mb-2">
                    {note.content}
                  </p>

                  {/* Metadata */}
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>{formatNoteDate(note.created_at)}</span>
                    <span>by {note.author}</span>
                    {note.tags.length > 0 && (
                      <span className="flex gap-1">
                        {note.tags.slice(0, 3).map((tag) => (
                          <span
                            key={tag}
                            className="bg-gray-100 px-2 py-0.5 rounded"
                          >
                            {tag}
                          </span>
                        ))}
                      </span>
                    )}
                    {note.links.length > 0 && (
                      <span>
                        {note.links.length} link{note.links.length !== 1 ? "s" : ""}
                      </span>
                    )}
                  </div>
                </div>

                {/* Arrow icon */}
                <svg
                  className="w-5 h-5 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
