"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import AIAssistant from "@/components/AIAssistant";
import { EmptyState } from "@/components/PageState";
import { useRouter, useSearchParams } from "next/navigation";
import Breadcrumb from "@/components/Breadcrumb";
import PageHeader from "@/components/PageHeader";
import { TagPillList } from "@/components/TagPill";
import { apiGet, isAuthenticated } from "@/lib/api/client";
import { logger } from "@/lib/logger";
import styles from "./page.module.scss";

export interface ArticleMetadata {
  id: number;
  title: string;
  summary?: string; // Optional 1-2 sentence description
  url?: string;
  tags: string[];
  draft?: boolean;
  published_date?: string;
  updated_date?: string;
  created_at?: string; // Legacy fallback
}

type SortOption = "newest" | "oldest" | "recently-updated" | "alphabetical";

export default function ArticlesClient({ resources }: { resources: ArticleMetadata[] }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tagsParam = searchParams.get("tags");
  const selectedTags = tagsParam ? tagsParam.split(",") : [];

  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("newest");
  const [showAllTags, setShowAllTags] = useState(false);

  // Draft articles (#184): the server fetch that produced `resources` is
  // anonymous/cached, so it never includes drafts. When signed in, re-fetch
  // with auth headers and merge in any draft-only entries. Starts empty to
  // avoid a hydration mismatch (server never renders drafts) - populated
  // client-side only, same pattern as NoteEditorForm's aiAvailable state.
  const [draftResources, setDraftResources] = useState<ArticleMetadata[]>([]);

  useEffect(() => {
    if (!isAuthenticated()) return;

    let cancelled = false;

    async function fetchDrafts() {
      try {
        const data = await apiGet<{ resources: ArticleMetadata[] }>("/api/articles");
        if (cancelled) return;
        setDraftResources(data.resources.filter((r) => r.draft));
      } catch (err) {
        logger.error("Failed to load draft articles", err);
      }
    }

    fetchDrafts();

    return () => {
      cancelled = true;
    };
  }, []);

  const knownIds = new Set(resources.map((r) => r.id));
  const allResources = [...resources, ...draftResources.filter((r) => !knownIds.has(r.id))];

  // Calculate tag counts
  const tagCounts = allResources.reduce(
    (acc, resource) => {
      resource.tags.forEach((tag) => {
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

  // Separate tags into top (2+ articles) and other (1 article)
  const topTags = sortedTags.filter(([_, count]) => count >= 2);
  const otherTags = sortedTags.filter(([_, count]) => count === 1);
  const visibleTags = showAllTags ? sortedTags : topTags;

  const filteredResources = allResources
    .filter((resource) => {
      // Filter by tags (OR logic - article must have at least one selected tag)
      if (selectedTags.length > 0) {
        const hasMatchingTag = selectedTags.some((tag) => resource.tags.includes(tag));
        if (!hasMatchingTag) return false;
      }

      // Filter by search query
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        resource.title.toLowerCase().includes(query) ||
        (resource.summary && resource.summary.toLowerCase().includes(query)) ||
        resource.tags.some((tag) => tag.toLowerCase().includes(query))
      );
    })
    .sort((a, b) => {
      // Sort drafts to the top first
      if (a.draft && !b.draft) return -1;
      if (!a.draft && b.draft) return 1;

      // Then sort by selected option
      switch (sortBy) {
        case "newest": {
          const dateA = new Date(a.published_date || a.created_at || 0).getTime();
          const dateB = new Date(b.published_date || b.created_at || 0).getTime();
          return dateB - dateA;
        }
        case "oldest": {
          const dateA = new Date(a.published_date || a.created_at || 0).getTime();
          const dateB = new Date(b.published_date || b.created_at || 0).getTime();
          return dateA - dateB;
        }
        case "recently-updated": {
          const dateA = new Date(a.updated_date || a.published_date || a.created_at || 0).getTime();
          const dateB = new Date(b.updated_date || b.published_date || b.created_at || 0).getTime();
          return dateB - dateA;
        }
        case "alphabetical":
          return a.title.localeCompare(b.title);
        default:
          return 0;
      }
    });

  const handleTagClick = (tag: string) => {
    let newTags: string[];

    if (selectedTags.includes(tag)) {
      // Tag is already selected, remove it
      newTags = selectedTags.filter((t) => t !== tag);
    } else {
      // Tag is not selected, add it
      newTags = [...selectedTags, tag];
    }

    // Update URL with new tags
    if (newTags.length > 0) {
      router.push(`/knowledge-base/articles?tags=${newTags.map(encodeURIComponent).join(",")}`);
    } else {
      router.push("/knowledge-base/articles");
    }
  };

  const clearAllFilters = () => {
    setSearchQuery("");
    router.push("/knowledge-base/articles");
  };

  const hasActiveFilters = Boolean(selectedTags.length > 0 || searchQuery);

  return (
    <div className={styles.container}>
      {/* AI panel + button island (only shown when LLM features enabled) */}
      <AIAssistant />

      <PageHeader title="Articles" breadcrumb={<Breadcrumb section="articles" toHub />} />

      <main className={styles.main}>
        <div className={styles.contentGrid}>
          {/* Sidebar - Filters */}
          <aside className={styles.sidebar}>
            {/* Search */}
            <div className={styles.searchBar}>
              <input
                type="text"
                placeholder="Search articles..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={styles.searchInput}
                aria-label="Search articles by title, summary, or tags"
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
                <option value="recently-updated">Recently Updated</option>
                <option value="alphabetical">Alphabetical</option>
              </select>
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
                    // Determine tag size class based on count
                    let sizeClass = styles.tagLow;
                    if (count >= 3) sizeClass = styles.tagHigh;
                    else if (count === 2) sizeClass = styles.tagMedium;

                    return (
                      <button
                        key={tag}
                        onClick={() => handleTagClick(tag)}
                        className={`${styles.tagBadge} ${sizeClass} ${isActive ? styles.tagBadgeActive : ""}`}
                        type="button"
                        aria-label={`Filter by tag: ${tag}, ${count} articles`}
                        aria-pressed={isActive}
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
                    aria-label={`Show ${otherTags.length} more tags`}
                    aria-expanded="false"
                  >
                    + Show {otherTags.length} more
                  </button>
                )}
                {showAllTags && otherTags.length > 0 && (
                  <button
                    onClick={() => setShowAllTags(false)}
                    className={styles.showMoreButton}
                    type="button"
                    aria-label="Show fewer tags"
                    aria-expanded="true"
                  >
                    − Show fewer
                  </button>
                )}
              </div>
            )}

            {/* Clear Filters */}
            {hasActiveFilters && (
              <button
                onClick={clearAllFilters}
                className={styles.clearAllButtonSidebar}
                aria-label="Clear all active filters"
              >
                Clear all filters
              </button>
            )}
          </aside>

          {/* Main Content - Articles */}
          <div className={styles.articlesContent}>
            {/* Article Count and Active Filters */}
            <div className={styles.resultsBar}>
              <div className={styles.articleCountSection}>
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
                <div className={styles.articleCount}>
                  Showing {filteredResources.length}
                  {filteredResources.length !== allResources.length &&
                    ` of ${allResources.length}`}{" "}
                  {filteredResources.length === 1 ? "article" : "articles"}
                </div>
              </div>
            </div>

            {/* Articles List */}
            <div className={styles.articlesList}>
              {filteredResources.length === 0 ? (
                <EmptyState
                  inline
                  message={searchQuery ? "No articles match your search" : "No articles yet"}
                  actionLabel={searchQuery ? "Clear search" : undefined}
                  onAction={() => setSearchQuery("")}
                />
              ) : (
                filteredResources.map((resource) => {
                  return (
                    <Link
                      key={resource.id}
                      href={`/knowledge-base/articles/${resource.id}`}
                      className={`${styles.articleCard} ${resource.draft ? styles.draftCard : ""}`}
                    >
                      <div className={styles.articleHeader}>
                        <div className={styles.titleRow}>
                          <h3 className={styles.articleTitle}>{resource.title}</h3>
                          {resource.draft && <span className={styles.draftBadge}>Draft</span>}
                        </div>
                        <div className={styles.articleMeta}>
                          {resource.updated_date &&
                          resource.updated_date !== resource.published_date ? (
                            <>
                              Updated{" "}
                              {new Date(resource.updated_date).toLocaleDateString("en-US", {
                                year: "numeric",
                                month: "long",
                                day: "numeric",
                              })}
                            </>
                          ) : (
                            <>
                              Published{" "}
                              {new Date(
                                resource.published_date || resource.created_at || ""
                              ).toLocaleDateString("en-US", {
                                year: "numeric",
                                month: "long",
                                day: "numeric",
                              })}
                            </>
                          )}
                        </div>
                      </div>

                      {/* Summary */}
                      {resource.summary && (
                        <p className={styles.articlePreview}>{resource.summary}</p>
                      )}

                      {/* Tags */}
                      {resource.tags.length > 0 && (
                        <div className={styles.articleTags}>
                          <TagPillList tags={resource.tags} showHash onClick={handleTagClick} />
                        </div>
                      )}

                      {/* Read more indicator */}
                      <div className={styles.readMore}>Read more →</div>
                    </Link>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
