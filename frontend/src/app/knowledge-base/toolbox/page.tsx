"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { listNotes, Note } from "@/lib/api/notes";
import { logger } from "@/lib/logger";
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

  useEffect(() => {
    async function fetchReferences() {
      try {
        setLoading(true);
        // Fetch with previews only for performance
        const response = await listNotes({
          is_reference: true,
          include_full_content: false,
        });
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
            <div className={styles.actions}>
              <Link href="/knowledge-base/notes/new?ref=true" className={styles.newReferenceButton}>
                + New Reference
              </Link>
            </div>
          </div>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.contentGrid}>
          {/* Sidebar - Filters */}
          <aside className={styles.sidebar}>
            {/* Search */}
            <div className={styles.searchBar}>
              <input
                type="text"
                placeholder="Search references..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={styles.searchInput}
              />
            </div>

            {/* Category Filter Section */}
            {categories.length > 0 && (
              <div className={styles.categoryFilterSection}>
                <div className={styles.categoryFilterHeader}>
                  <span className={styles.categoryFilterLabel}>Filter by category:</span>
                </div>
                <div className={styles.categoryBadges} role="group" aria-label="Category filters">
                  <button
                    type="button"
                    onClick={() => setCategoryFilter("all")}
                    className={`${styles.categoryBadge} ${categoryFilter === "all" ? styles.categoryBadgeActive : ""}`}
                    aria-label="Show all categories"
                    aria-pressed={categoryFilter === "all"}
                  >
                    All ({references.length})
                  </button>
                  {categories.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setCategoryFilter(cat)}
                      className={`${styles.categoryBadge} ${categoryFilter === cat ? styles.categoryBadgeActive : ""}`}
                      aria-label={`Filter by category: ${cat}`}
                      aria-pressed={categoryFilter === cat}
                    >
                      {cat} ({references.filter((r) => r.tags.includes(cat)).length})
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Clear Filters */}
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className={styles.clearAllButtonSidebar}
                aria-label="Clear category filter"
              >
                Clear all filters
              </button>
            )}
          </aside>

          {/* Main Content - References */}
          <div className={styles.referencesContent}>
            {/* Results Count */}
            <div className={styles.resultsBar}>
              <div className={styles.referenceCountSection}>
                {categoryFilter !== "all" && (
                  <div className={styles.activeFilters}>Filtering by: {categoryFilter}</div>
                )}
                <div className={styles.referenceCount}>
                  {filteredReferences.length} reference{filteredReferences.length !== 1 ? "s" : ""}
                  {hasActiveFilters && " matching filters"}
                </div>
              </div>
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
                <button
                  type="button"
                  onClick={clearFilters}
                  className={styles.clearFiltersButton}
                  aria-label="Clear category filter"
                >
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
                    <Link
                      key={ref.id}
                      href={`/knowledge-base/notes/${ref.id}`}
                      className={styles.referenceCard}
                    >
                      <div className={styles.cardContent}>
                        <div className={styles.cardInfo}>
                          {/* Note ID and title */}
                          <div className={styles.cardIdRow}>
                            <code className={styles.cardId}>{ref.id}</code>
                            <span className={styles.referenceBadge}>Reference</span>
                          </div>

                          {ref.title && <h3 className={styles.cardTitle}>{ref.title}</h3>}

                          {/* Content preview */}
                          <p className={styles.cardPreview}>{ref.content_preview || ref.content}</p>

                          {/* Tags (skip first tag as it's the category) */}
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

                        {/* Arrow icon */}
                        <svg
                          className={styles.cardArrow}
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
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
