"use client";

import { Suspense } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { listNotes, getRandomNote, Note, formatNoteDate } from "@/lib/api/notes";
import { logger } from "@/lib/logger";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import Breadcrumb from "@/components/Breadcrumb";
import { TagPillList } from "@/components/TagPill";
import QuickLists from "@/components/QuickLists/QuickLists";
import styles from "./page.module.scss";

type SortOption = "newest" | "oldest" | "alphabetical";
type NoteTypeFilter = "all" | "insights" | "references";

function NotesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tagsParam = searchParams.get("tags");
  const typeParam = searchParams.get("type");
  const selectedTags = tagsParam ? tagsParam.split(",") : [];

  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [randomNoteLoading, setRandomNoteLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("newest");
  const [showAllTags, setShowAllTags] = useState(false);
  const [typeFilter, setTypeFilter] = useState<NoteTypeFilter>(
    typeParam === "insights" || typeParam === "references" ? typeParam : "all"
  );

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

  // Calculate tag counts
  const tagCounts = notes.reduce(
    (acc, note) => {
      note.tags.forEach((tag) => {
        acc[tag] = (acc[tag] || 0) + 1;
      });
      return acc;
    },
    {} as Record<string, number>
  );

  // Sort tags by count (descending), then alphabetically
  const sortedTags = Object.entries(tagCounts).sort((a, b) => {
    if (b[1] !== a[1]) return b[1] - a[1];
    return a[0].localeCompare(b[0]);
  });

  // Separate tags into top (2+ notes) and other (1 note)
  const topTags = sortedTags.filter(([_, count]) => count >= 2);
  const otherTags = sortedTags.filter(([_, count]) => count === 1);
  const visibleTags = showAllTags ? sortedTags : topTags;

  // Calculate type counts for filter buttons
  const insightsCount = notes.filter((n) => !n.is_reference).length;
  const referencesCount = notes.filter((n) => n.is_reference).length;

  // Filter and sort notes
  const filteredNotes = notes
    .filter((note) => {
      // Filter by type
      if (typeFilter === "insights" && note.is_reference) return false;
      if (typeFilter === "references" && !note.is_reference) return false;

      // Filter by tags (OR logic)
      if (selectedTags.length > 0) {
        const hasMatchingTag = selectedTags.some((tag) => note.tags.includes(tag));
        if (!hasMatchingTag) return false;
      }

      // Filter by search query
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        note.id.toLowerCase().includes(query) ||
        (note.title && note.title.toLowerCase().includes(query)) ||
        note.content.toLowerCase().includes(query) ||
        note.tags.some((tag) => tag.toLowerCase().includes(query))
      );
    })
    .sort((a, b) => {
      switch (sortBy) {
        case "newest":
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case "oldest":
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        case "alphabetical":
          return (a.title || a.id).localeCompare(b.title || b.id);
        default:
          return 0;
      }
    });

  // Build URL with current filters
  const buildFilterUrl = (options: { tags?: string[]; type?: NoteTypeFilter }) => {
    const params = new URLSearchParams();
    const tags = options.tags ?? selectedTags;
    const type = options.type ?? typeFilter;

    if (tags.length > 0) {
      params.set("tags", tags.map(encodeURIComponent).join(","));
    }
    if (type !== "all") {
      params.set("type", type);
    }

    const queryString = params.toString();
    return queryString ? `/knowledge-base/notes?${queryString}` : "/knowledge-base/notes";
  };

  const handleTagClick = (tag: string) => {
    let newTags: string[];

    if (selectedTags.includes(tag)) {
      // Tag is already selected, remove it
      newTags = selectedTags.filter((t) => t !== tag);
    } else {
      // Tag is not selected, add it
      newTags = [...selectedTags, tag];
    }

    router.push(buildFilterUrl({ tags: newTags }));
  };

  const handleTypeFilter = (newType: NoteTypeFilter) => {
    setTypeFilter(newType);
    router.push(buildFilterUrl({ type: newType }));
  };

  const clearAllFilters = () => {
    setSearchQuery("");
    setTypeFilter("all");
    router.push("/knowledge-base/notes");
  };

  const hasActiveFilters = Boolean(selectedTags.length > 0 || searchQuery || typeFilter !== "all");

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

      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.headerTop}>
            <Breadcrumb section="notes" toHub />
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
      </div>

      <div className={styles.main}>
        <div className={styles.contentGrid}>
          {/* Sidebar - Filters */}
          <aside className={styles.sidebar}>
            {/* Search */}
            <div className={styles.searchBar}>
              <input
                type="text"
                placeholder="Search notes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={styles.searchInput}
              />
            </div>

            {/* Sort */}
            <div className={styles.sortSection}>
              <label htmlFor="sort-select" className={styles.sortLabel}>
                Sort by:
              </label>
              <select
                id="sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className={styles.sortSelect}
              >
                <option value="newest">Newest</option>
                <option value="oldest">Oldest</option>
                <option value="alphabetical">Alphabetical</option>
              </select>
            </div>

            {/* Type Filter Section */}
            <div className={styles.typeFilterSection}>
              <span className={styles.typeFilterLabel}>Type:</span>
              <div className={styles.typeButtons}>
                <button
                  type="button"
                  onClick={() => handleTypeFilter("all")}
                  className={`${styles.typeButton} ${typeFilter === "all" ? styles.typeButtonActive : ""}`}
                >
                  All ({notes.length})
                </button>
                <button
                  type="button"
                  onClick={() => handleTypeFilter("insights")}
                  className={`${styles.typeButton} ${typeFilter === "insights" ? styles.typeButtonActive : ""}`}
                >
                  Insights ({insightsCount})
                </button>
                <button
                  type="button"
                  onClick={() => handleTypeFilter("references")}
                  className={`${styles.typeButton} ${typeFilter === "references" ? styles.typeButtonActive : ""}`}
                >
                  References ({referencesCount})
                </button>
              </div>
            </div>

            {/* Tag Filter Section */}
            {sortedTags.length > 0 && (
              <div className={styles.tagFilterSection}>
                <div className={styles.tagFilterHeader}>
                  <span className={styles.tagFilterLabel}>Filter by tag:</span>
                </div>
                <div className={styles.tagBadges}>
                  {visibleTags.map(([tag, count]) => {
                    const isActive = selectedTags.includes(tag);
                    let sizeClass = styles.tagLow;
                    if (count >= 3) sizeClass = styles.tagHigh;
                    else if (count === 2) sizeClass = styles.tagMedium;

                    return (
                      <button
                        key={tag}
                        onClick={() => handleTagClick(tag)}
                        className={`${styles.tagBadge} ${sizeClass} ${isActive ? styles.tagBadgeActive : ""}`}
                        type="button"
                      >
                        #{tag} ({count})
                      </button>
                    );
                  })}
                </div>
                {otherTags.length > 0 && !showAllTags && (
                  <button
                    onClick={() => setShowAllTags(true)}
                    className={styles.showMoreButton}
                    type="button"
                  >
                    + Show {otherTags.length} more
                  </button>
                )}
                {showAllTags && otherTags.length > 0 && (
                  <button
                    onClick={() => setShowAllTags(false)}
                    className={styles.showMoreButton}
                    type="button"
                  >
                    − Show fewer
                  </button>
                )}
              </div>
            )}

            {/* Clear Filters */}
            {hasActiveFilters && (
              <button onClick={clearAllFilters} className={styles.clearAllButtonSidebar}>
                Clear all filters
              </button>
            )}

            {/* Quick Lists */}
            {!hasActiveFilters && <QuickLists />}
          </aside>

          {/* Main Content - Notes */}
          <div className={styles.notesContent}>
            {/* Note Count and Active Filters */}
            <div className={styles.resultsBar}>
              <div className={styles.noteCountSection}>
                {selectedTags.length > 0 && (
                  <div className={styles.activeFilters}>
                    Filtering by:{" "}
                    {selectedTags.map((tag, index) => (
                      <span key={tag}>
                        #{tag}
                        {index < selectedTags.length - 1 && ", "}
                      </span>
                    ))}
                  </div>
                )}
                <div className={styles.noteCount}>
                  Showing {filteredNotes.length}
                  {filteredNotes.length !== notes.length && ` of ${notes.length}`}{" "}
                  {filteredNotes.length === 1 ? "note" : "notes"}
                </div>
              </div>
            </div>

            {/* Notes list */}
            {filteredNotes.length === 0 ? (
              <div className={styles.emptyState}>
                <svg
                  className={styles.emptyIcon}
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
                        {/* Note ID and type badge */}
                        <div className={styles.noteIdRow}>
                          <code className={styles.noteId}>{note.id}</code>
                          {note.is_reference && (
                            <span className={styles.referenceBadge}>Reference</span>
                          )}
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
