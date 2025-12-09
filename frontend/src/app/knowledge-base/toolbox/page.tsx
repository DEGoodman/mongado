"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { listNotes, Note } from "@/lib/api/notes";
import { logger } from "@/lib/logger";
import MarkdownWithWikilinks from "@/components/MarkdownWithWikilinks";
import Breadcrumb from "@/components/Breadcrumb";
import styles from "./page.module.scss";

type CategoryFilter = "all" | string;

interface GroupedReferences {
  [category: string]: Note[];
}

export default function ToolboxPage() {
  const [references, setReferences] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");
  const [expandedNoteId, setExpandedNoteId] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReferences() {
      try {
        setLoading(true);
        const response = await listNotes({ is_reference: true });
        setReferences(response.notes);
        logger.info("Toolbox references loaded", { count: response.count });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load references";
        setError(message);
        logger.error("Failed to load toolbox references", err);
      } finally {
        setLoading(false);
      }
    }

    fetchReferences();
  }, []);

  // Extract unique categories from tags (use first tag as category)
  const categories = useMemo(() => {
    const cats = new Set<string>();
    references.forEach((ref) => {
      if (ref.tags.length > 0) {
        cats.add(ref.tags[0]);
      }
    });
    return Array.from(cats).sort();
  }, [references]);

  // Filter references by search and category
  const filteredReferences = useMemo(() => {
    return references.filter((ref) => {
      // Category filter
      if (categoryFilter !== "all") {
        if (!ref.tags.includes(categoryFilter)) return false;
      }

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const matchesTitle = ref.title?.toLowerCase().includes(query);
        const matchesContent = ref.content.toLowerCase().includes(query);
        const matchesTags = ref.tags.some((tag) => tag.toLowerCase().includes(query));
        const matchesId = ref.id.toLowerCase().includes(query);
        if (!matchesTitle && !matchesContent && !matchesTags && !matchesId) return false;
      }

      return true;
    });
  }, [references, categoryFilter, searchQuery]);

  // Group filtered references by category
  const groupedReferences = useMemo(() => {
    const grouped: GroupedReferences = {};

    filteredReferences.forEach((ref) => {
      const category = ref.tags.length > 0 ? ref.tags[0] : "Uncategorized";
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(ref);
    });

    // Sort categories alphabetically, but put "Uncategorized" last
    const sortedKeys = Object.keys(grouped).sort((a, b) => {
      if (a === "Uncategorized") return 1;
      if (b === "Uncategorized") return -1;
      return a.localeCompare(b);
    });

    const sortedGrouped: GroupedReferences = {};
    sortedKeys.forEach((key) => {
      sortedGrouped[key] = grouped[key];
    });

    return sortedGrouped;
  }, [filteredReferences]);

  const handleToggleExpand = (noteId: string) => {
    setExpandedNoteId(expandedNoteId === noteId ? null : noteId);
  };

  const clearFilters = () => {
    setSearchQuery("");
    setCategoryFilter("all");
  };

  const hasActiveFilters = searchQuery || categoryFilter !== "all";

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSkeleton}>
            <div className={styles.skeletonHeader}></div>
            <div className={styles.skeletonGrid}>
              <div className={styles.skeletonCard}></div>
              <div className={styles.skeletonCard}></div>
              <div className={styles.skeletonCard}></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.errorContainer}>
          <div className={styles.errorCard}>
            <h2 className={styles.errorTitle}>Error</h2>
            <p className={styles.errorMessage}>{error}</p>
            <Link href="/knowledge-base" className={styles.backLink}>
              Back to Knowledge Base
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.headerTop}>
            <Breadcrumb section="toolbox" />
          </div>
          <div className={styles.titleRow}>
            <div className={styles.titleSection}>
              <h1 className={styles.title}>Toolbox</h1>
              <p className={styles.subtitle}>
                Frameworks, checklists, and mental models at your fingertips
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className={styles.main}>
        {/* Search and Filter Bar */}
        <div className={styles.filterBar}>
          <div className={styles.searchBox}>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search references..."
              className={styles.searchInput}
            />
          </div>

          <div className={styles.categoryFilters}>
            <button
              type="button"
              onClick={() => setCategoryFilter("all")}
              className={`${styles.categoryButton} ${categoryFilter === "all" ? styles.active : ""}`}
            >
              All ({references.length})
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setCategoryFilter(cat)}
                className={`${styles.categoryButton} ${categoryFilter === cat ? styles.active : ""}`}
              >
                {cat} ({references.filter((r) => r.tags.includes(cat)).length})
              </button>
            ))}
          </div>

          {hasActiveFilters && (
            <button type="button" onClick={clearFilters} className={styles.clearButton}>
              Clear filters
            </button>
          )}
        </div>

        {/* Results Count */}
        <div className={styles.resultsBar}>
          <span className={styles.resultsCount}>
            {filteredReferences.length} reference{filteredReferences.length !== 1 ? "s" : ""}
            {hasActiveFilters && " matching filters"}
          </span>
        </div>

        {/* Empty State */}
        {references.length === 0 && (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>📦</div>
            <h3 className={styles.emptyTitle}>No references yet</h3>
            <p className={styles.emptyMessage}>
              Quick references like frameworks, checklists, and acronyms will appear here.
            </p>
            <p className={styles.emptyHint}>
              Create a note and check &quot;Quick Reference&quot; to add it to your toolbox.
            </p>
            <Link href="/knowledge-base/notes/new" className={styles.createButton}>
              Create Reference
            </Link>
          </div>
        )}

        {/* No Results for Filter */}
        {references.length > 0 && filteredReferences.length === 0 && (
          <div className={styles.noResults}>
            <p>No references match your filters.</p>
            <button type="button" onClick={clearFilters} className={styles.clearFiltersButton}>
              Clear filters
            </button>
          </div>
        )}

        {/* Reference Cards - Grouped by Category */}
        {Object.entries(groupedReferences).map(([category, refs]) => (
          <div key={category} className={styles.categorySection}>
            <h2 className={styles.categoryTitle}>
              {category} <span className={styles.categoryCount}>({refs.length})</span>
            </h2>
            <div className={styles.referenceGrid}>
              {refs.map((ref) => (
                <div
                  key={ref.id}
                  className={`${styles.referenceCard} ${expandedNoteId === ref.id ? styles.expanded : ""}`}
                >
                  <div
                    className={styles.cardHeader}
                    onClick={() => handleToggleExpand(ref.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        handleToggleExpand(ref.id);
                      }
                    }}
                  >
                    <div className={styles.cardTitleRow}>
                      <h3 className={styles.cardTitle}>{ref.title || ref.id}</h3>
                      <span className={styles.expandIcon}>
                        {expandedNoteId === ref.id ? "▼" : "▶"}
                      </span>
                    </div>
                    {ref.title && <code className={styles.cardId}>{ref.id}</code>}
                    {ref.tags.length > 1 && (
                      <div className={styles.cardTags}>
                        {ref.tags.slice(1).map((tag) => (
                          <span key={tag} className={styles.tag}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Expanded Content */}
                  {expandedNoteId === ref.id && (
                    <div className={styles.cardContent}>
                      <div className={styles.contentBody}>
                        <MarkdownWithWikilinks content={ref.content} />
                      </div>
                      <div className={styles.cardActions}>
                        <Link
                          href={`/knowledge-base/notes/${ref.id}`}
                          className={styles.openNoteButton}
                        >
                          Open in Notes →
                        </Link>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </main>
    </div>
  );
}
