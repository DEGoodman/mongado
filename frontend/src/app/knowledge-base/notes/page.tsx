"use client";

import { Suspense } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { listNotes, getRandomNote, Note, formatNoteDate } from "@/lib/api/notes";
import { logger } from "@/lib/logger";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import SettingsDropdown from "@/components/SettingsDropdown";
import Breadcrumb from "@/components/Breadcrumb";
import { TagPillList } from "@/components/TagPill";

function NotesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tagFilter = searchParams.get("tag");

  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [randomNoteLoading, setRandomNoteLoading] = useState(false);

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

  // Filter notes by tag
  const filteredNotes = tagFilter ? notes.filter((note) => note.tags.includes(tagFilter)) : notes;

  const handleTagClick = (tag: string) => {
    router.push(`/knowledge-base/notes?tag=${encodeURIComponent(tag)}`);
  };

  const clearTagFilter = () => {
    router.push("/knowledge-base/notes");
  };

  const handleRandomNote = async () => {
    try {
      setRandomNoteLoading(true);
      const randomNote = await getRandomNote();
      router.push(`/knowledge-base/notes/${randomNote.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to get random note";
      logger.error("Failed to get random note", err);
      alert(message);
    } finally {
      setRandomNoteLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse">
          <div className="mb-8 h-8 w-1/4 rounded bg-gray-200"></div>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 rounded bg-gray-200"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <h2 className="mb-2 font-semibold text-red-800">Error</h2>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-4xl px-4 py-8">
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <div className="mb-8">
        <div className="mb-6 flex items-center justify-between">
          <Breadcrumb section="notes" />
          <SettingsDropdown />
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Notes</h1>
            <p className="mt-1 text-gray-600">
              Your Zettelkasten knowledge base ({notes.length} notes)
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleRandomNote}
              disabled={randomNoteLoading || notes.length === 0}
              className="rounded-lg border border-blue-600 bg-white px-4 py-2 text-blue-600 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
              title="Open a random note for serendipitous discovery"
            >
              {randomNoteLoading ? "Loading..." : "Random Note"}
            </button>
            <Link
              href="/knowledge-base/notes/new"
              className="rounded-lg bg-blue-600 px-4 py-2 text-white transition hover:bg-blue-700"
            >
              + New Note
            </Link>
          </div>
        </div>
      </div>

      {/* Tag Filter Banner */}
      {tagFilter && (
        <div className="mb-6 flex items-center justify-between rounded-lg border border-purple-200 bg-purple-50 p-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-purple-900">Filtering by tag:</span>
            <span className="inline-flex items-center rounded-full bg-purple-100 px-3 py-1 text-sm font-medium text-purple-800">
              {tagFilter}
            </span>
          </div>
          <button
            onClick={clearTagFilter}
            className="text-sm text-purple-600 hover:text-purple-800 hover:underline"
          >
            Clear filter
          </button>
        </div>
      )}

      {/* Notes list */}
      {filteredNotes.length === 0 ? (
        <div className="rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 py-12 text-center">
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
          <p className="mt-1 text-sm text-gray-500">Get started by creating your first note</p>
          <div className="mt-6">
            <Link
              href="/knowledge-base/notes/new"
              className="inline-flex items-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
            >
              Create Note
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredNotes.map((note) => (
            <Link
              key={note.id}
              href={`/knowledge-base/notes/${note.id}`}
              className="block rounded-lg border border-gray-200 bg-white p-4 transition hover:border-blue-300 hover:shadow-md"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  {/* Note ID and title */}
                  <div className="mb-1 flex items-center gap-2">
                    <code className="rounded bg-blue-50 px-2 py-0.5 font-mono text-sm text-blue-600">
                      {note.id}
                    </code>
                  </div>

                  {note.title && (
                    <h3 className="mb-1 text-lg font-semibold text-gray-900">{note.title}</h3>
                  )}

                  {/* Content preview */}
                  <p className="mb-2 line-clamp-2 overflow-hidden break-words text-sm text-gray-600">
                    {note.content}
                  </p>

                  {/* Metadata */}
                  <div className="mb-2 flex items-center gap-4 text-xs text-gray-500">
                    <span>{formatNoteDate(note.created_at)}</span>
                    <span>by {note.author}</span>
                    {note.links.length > 0 && (
                      <span>
                        {note.links.length} link{note.links.length !== 1 ? "s" : ""}
                      </span>
                    )}
                  </div>

                  {/* Tags */}
                  {note.tags.length > 0 && (
                    <TagPillList tags={note.tags} maxVisible={3} onClick={handleTagClick} />
                  )}
                </div>

                {/* Arrow icon */}
                <svg
                  className="h-5 w-5 text-gray-400"
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

export default function NotesPage() {
  return (
    <Suspense
      fallback={
        <div className="container mx-auto px-4 py-8">
          <div className="animate-pulse">
            <div className="mb-8 h-8 w-1/4 rounded bg-gray-200"></div>
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 rounded bg-gray-200"></div>
              ))}
            </div>
          </div>
        </div>
      }
    >
      <NotesContent />
    </Suspense>
  );
}
