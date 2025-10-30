"use client";

import { Suspense } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  listNotes,
  getRandomNote,
  getOrphanNotes,
  getHubNotes,
  getCentralNotes,
  Note,
  formatNoteDate,
} from "@/lib/api/notes";
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

  // Special note categories
  const [orphans, setOrphans] = useState<Note[]>([]);
  const [hubs, setHubs] = useState<Note[]>([]);
  const [central, setCentral] = useState<Note[]>([]);
  const [showOrphans, setShowOrphans] = useState(false);
  const [showHubs, setShowHubs] = useState(false);
  const [showCentral, setShowCentral] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const [notesResp, orphansResp, hubsResp, centralResp] = await Promise.all([
          listNotes(),
          getOrphanNotes(),
          getHubNotes(),
          getCentralNotes(),
        ]);
        setNotes(notesResp.notes);
        setOrphans(orphansResp.notes);
        setHubs(hubsResp.notes);
        setCentral(centralResp.notes);
        logger.info("All notes data loaded");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load notes";
        setError(message);
        logger.error("Failed to load notes", err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
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

      {/* Special Note Categories */}
      {(orphans.length > 0 || hubs.length > 0 || central.length > 0) && (
        <div className="mb-6 space-y-3">
          {/* Orphans - Notes needing integration */}
          {orphans.length > 0 && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50">
              <button
                onClick={() => setShowOrphans(!showOrphans)}
                className="flex w-full items-center justify-between p-4 text-left hover:bg-yellow-100"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">🏝️</span>
                  <span className="font-medium text-yellow-900">
                    Orphan Notes ({orphans.length})
                  </span>
                  <span className="text-sm text-yellow-700">
                    - Isolated notes needing integration
                  </span>
                </div>
                <svg
                  className={`h-5 w-5 text-yellow-600 transition-transform ${showOrphans ? "rotate-180" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showOrphans && (
                <div className="space-y-2 border-t border-yellow-200 p-4">
                  {orphans.map((note) => (
                    <Link
                      key={note.id}
                      href={`/knowledge-base/notes/${note.id}`}
                      className="block rounded border border-yellow-300 bg-white p-3 text-sm hover:border-yellow-400 hover:shadow"
                    >
                      <code className="text-xs text-yellow-700">{note.id}</code>
                      {note.title && <div className="font-medium text-gray-900">{note.title}</div>}
                      <div className="mt-1 line-clamp-1 text-gray-600">{note.content}</div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Hub Notes - Entry points */}
          {hubs.length > 0 && (
            <div className="rounded-lg border border-blue-200 bg-blue-50">
              <button
                onClick={() => setShowHubs(!showHubs)}
                className="flex w-full items-center justify-between p-4 text-left hover:bg-blue-100"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">🗺️</span>
                  <span className="font-medium text-blue-900">Hub Notes ({hubs.length})</span>
                  <span className="text-sm text-blue-700">- Entry points with many links</span>
                </div>
                <svg
                  className={`h-5 w-5 text-blue-600 transition-transform ${showHubs ? "rotate-180" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showHubs && (
                <div className="space-y-2 border-t border-blue-200 p-4">
                  {hubs.map((note: any) => (
                    <Link
                      key={note.id}
                      href={`/knowledge-base/notes/${note.id}`}
                      className="block rounded border border-blue-300 bg-white p-3 text-sm hover:border-blue-400 hover:shadow"
                    >
                      <div className="flex items-center justify-between">
                        <code className="text-xs text-blue-700">{note.id}</code>
                        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800">
                          {note.link_count} links
                        </span>
                      </div>
                      {note.title && <div className="font-medium text-gray-900">{note.title}</div>}
                      <div className="mt-1 line-clamp-1 text-gray-600">{note.content}</div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Central Notes - Core concepts */}
          {central.length > 0 && (
            <div className="rounded-lg border border-purple-200 bg-purple-50">
              <button
                onClick={() => setShowCentral(!showCentral)}
                className="flex w-full items-center justify-between p-4 text-left hover:bg-purple-100"
              >
                <div className="flex items-center gap-2">
                  <span className="text-lg">⭐</span>
                  <span className="font-medium text-purple-900">
                    Central Concepts ({central.length})
                  </span>
                  <span className="text-sm text-purple-700">
                    - Highly referenced core ideas
                  </span>
                </div>
                <svg
                  className={`h-5 w-5 text-purple-600 transition-transform ${showCentral ? "rotate-180" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showCentral && (
                <div className="space-y-2 border-t border-purple-200 p-4">
                  {central.map((note: any) => (
                    <Link
                      key={note.id}
                      href={`/knowledge-base/notes/${note.id}`}
                      className="block rounded border border-purple-300 bg-white p-3 text-sm hover:border-purple-400 hover:shadow"
                    >
                      <div className="flex items-center justify-between">
                        <code className="text-xs text-purple-700">{note.id}</code>
                        <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-800">
                          {note.backlink_count} backlinks
                        </span>
                      </div>
                      {note.title && <div className="font-medium text-gray-900">{note.title}</div>}
                      <div className="mt-1 line-clamp-1 text-gray-600">{note.content}</div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

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
