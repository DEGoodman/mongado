"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import {
  listAllLibraryEntries,
  LibraryEntry,
  LibraryEntryType,
  LIBRARY_ENTRY_TYPES,
} from "@/lib/api/library";
import { logger } from "@/lib/logger";
import Breadcrumb from "@/components/Breadcrumb";
import PageHeader from "@/components/PageHeader";
import { LoadingState, ErrorState } from "@/components/PageState";
import styles from "./page.module.scss";

type TypeFilter = "all" | LibraryEntryType;

export default function LibraryPage() {
  const [entries, setEntries] = useState<LibraryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");

  useEffect(() => {
    async function fetchEntries() {
      try {
        setLoading(true);
        const all = await listAllLibraryEntries();
        setEntries(all);
        logger.info("Library entries loaded", { count: all.length });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load library";
        setError(message);
        logger.error("Failed to load library entries", err);
      } finally {
        setLoading(false);
      }
    }
    fetchEntries();
  }, []);

  // Which types actually have entries (so we don't show empty filter chips)
  const availableTypes = useMemo(() => {
    const present = new Set(entries.map((e) => e.type));
    return LIBRARY_ENTRY_TYPES.filter((t) => present.has(t));
  }, [entries]);

  const filteredEntries = useMemo(() => {
    return entries.filter((entry) => {
      if (typeFilter !== "all" && entry.type !== typeFilter) return false;

      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matches =
          entry.title.toLowerCase().includes(q) ||
          entry.author.toLowerCase().includes(q) ||
          entry.summary.toLowerCase().includes(q) ||
          entry.tags.some((tag) => tag.toLowerCase().includes(q));
        if (!matches) return false;
      }
      return true;
    });
  }, [entries, searchQuery, typeFilter]);

  const clearFilters = () => {
    setSearchQuery("");
    setTypeFilter("all");
  };
  const hasActiveFilters = searchQuery !== "" || typeFilter !== "all";

  if (loading) {
    return (
      <div className={styles.container}>
        <LoadingState variant="cards" label="Loading library" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <ErrorState message={error} backHref="/" backLabel="Back to home" />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <PageHeader
        title="Library"
        subtitle="Books, articles, and resources worth reaching back to"
        breadcrumb={<Breadcrumb section="library" toHub />}
        actions={
          <Link href="/library/new" className={styles.newButton}>
            + New Entry
          </Link>
        }
      />

      <main className={styles.main}>
        {/* Filter bar */}
        <div className={styles.filterBar}>
          <input
            type="text"
            placeholder="Search the library..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
            aria-label="Search the library"
          />
          {availableTypes.length > 0 && (
            <div className={styles.typeFilters} role="group" aria-label="Filter by type">
              <button
                type="button"
                onClick={() => setTypeFilter("all")}
                className={`${styles.typeChip} ${typeFilter === "all" ? styles.typeChipActive : ""}`}
                aria-pressed={typeFilter === "all"}
              >
                All ({entries.length})
              </button>
              {availableTypes.map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTypeFilter(t)}
                  className={`${styles.typeChip} ${typeFilter === t ? styles.typeChipActive : ""}`}
                  aria-pressed={typeFilter === t}
                >
                  {t} ({entries.filter((e) => e.type === t).length})
                </button>
              ))}
            </div>
          )}
        </div>

        <div className={styles.resultsBar}>
          <span className={styles.resultsCount}>
            {filteredEntries.length} {filteredEntries.length === 1 ? "entry" : "entries"}
            {hasActiveFilters && " matching filters"}
          </span>
          {hasActiveFilters && (
            <button type="button" onClick={clearFilters} className={styles.clearButton}>
              Clear filters
            </button>
          )}
        </div>

        {/* Empty states */}
        {entries.length === 0 && (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>📚</div>
            <h3 className={styles.emptyTitle}>The library is empty</h3>
            <p className={styles.emptyMessage}>
              Curated books, articles, and resources you value will appear here.
            </p>
            <Link href="/library/new" className={styles.createButton}>
              Add the first entry
            </Link>
          </div>
        )}

        {entries.length > 0 && filteredEntries.length === 0 && (
          <div className={styles.noResults}>
            <p>No entries match your filters.</p>
            <button type="button" onClick={clearFilters} className={styles.clearButton}>
              Clear filters
            </button>
          </div>
        )}

        {/* Entry grid */}
        {filteredEntries.length > 0 && (
          <ul className={styles.grid}>
            {filteredEntries.map((entry) => (
              <li key={entry.id}>
                <Link href={`/library/${entry.id}`} className={styles.card}>
                  <div className={styles.cardTop}>
                    <span className={styles.typeBadge}>{entry.type}</span>
                  </div>
                  <h2 className={styles.cardTitle}>{entry.title}</h2>
                  {entry.author && <p className={styles.cardAuthor}>{entry.author}</p>}
                  {entry.summary && (
                    <p className={styles.cardSummary}>{entry.summary.slice(0, 180)}</p>
                  )}
                  {entry.tags.length > 0 && (
                    <div className={styles.cardTags}>
                      {entry.tags.map((tag) => (
                        <span key={tag} className={styles.cardTag}>
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
