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
import styles from "./page.module.scss";

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
    async function fetchData() {
      try {
        setLoading(true);
        const notesResp = await listNotes();
        setNotes(notesResp.notes);
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
      <div className={styles.loadingContainer}>
        <div className={styles.loadingSkeleton}>
          <div className={styles.skeletonTitle}></div>
          <div className={styles.skeletonList}>
            {[1, 2, 3].map((i) => (
              <div key={i} className={styles.skeletonItem}></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <div className={styles.errorCard}>
          <h2 className={styles.errorTitle}>Error</h2>
          <p className={styles.errorMessage}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      <div className={styles.main}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerTop}>
            <Breadcrumb section="notes" />
            <SettingsDropdown />
          </div>
          <div className={styles.titleRow}>
            <div className={styles.titleSection}>
              <h1 className={styles.title}>Notes</h1>
              <p className={styles.subtitle}>
                Your Zettelkasten knowledge base ({notes.length} notes)
              </p>
            </div>
            <div className={styles.actions}>
              <button
                onClick={handleRandomNote}
                disabled={randomNoteLoading || notes.length === 0}
                className={styles.randomButton}
                title="Open a random note for serendipitous discovery"
              >
                {randomNoteLoading ? "Loading..." : "Random Note"}
              </button>
              <Link href="/knowledge-base/notes/new" className={styles.newNoteButton}>
                + New Note
              </Link>
            </div>
          </div>
        </div>

        {/* Tag Filter Banner */}
        {tagFilter && (
          <div className={styles.tagFilterBanner}>
            <div className={styles.filterInfo}>
              <span className={styles.filterLabel}>Filtering by tag:</span>
              <span className={styles.tagPill}>{tagFilter}</span>
            </div>
            <button onClick={clearTagFilter} className={styles.clearButton}>
              Clear filter
            </button>
          </div>
        )}

        {/* Notes list */}
        {filteredNotes.length === 0 ? (
          <div className={styles.emptyState}>
            <svg className={styles.emptyIcon} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 className={styles.emptyTitle}>No notes yet</h3>
            <p className={styles.emptyMessage}>Get started by creating your first note</p>
            <Link href="/knowledge-base/notes/new" className={styles.createButton}>
              Create Note
            </Link>
          </div>
        ) : (
          <div className={styles.notesList}>
            {filteredNotes.map((note) => (
              <Link
                key={note.id}
                href={`/knowledge-base/notes/${note.id}`}
                className={styles.noteCard}
              >
                <div className={styles.noteCardContent}>
                  <div className={styles.noteInfo}>
                    {/* Note ID and title */}
                    <div className={styles.noteIdRow}>
                      <code className={styles.noteId}>{note.id}</code>
                    </div>

                    {note.title && <h3 className={styles.noteTitle}>{note.title}</h3>}

                    {/* Content preview */}
                    <p className={styles.notePreview}>{note.content}</p>

                    {/* Metadata */}
                    <div className={styles.noteMeta}>
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
                      <div className={styles.noteTags}>
                        <TagPillList tags={note.tags} maxVisible={3} onClick={handleTagClick} />
                      </div>
                    )}
                  </div>

                  {/* Arrow icon */}
                  <svg
                    className={styles.noteArrow}
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
    </div>
  );
}

export default function NotesPage() {
  return (
    <Suspense
      fallback={
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSkeleton}>
            <div className={styles.skeletonTitle}></div>
            <div className={styles.skeletonList}>
              {[1, 2, 3].map((i) => (
                <div key={i} className={styles.skeletonItem}></div>
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
