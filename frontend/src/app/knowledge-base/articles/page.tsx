"use client";

import { Suspense } from "react";
import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { logger } from "@/lib/logger";
import MarkdownWithWikilinks from "@/components/MarkdownWithWikilinks";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import Breadcrumb from "@/components/Breadcrumb";
import { TagPillList } from "@/components/TagPill";
import styles from "./page.module.scss";

interface Resource {
  id: number;
  title: string;
  content: string;
  content_type?: string;
  url?: string;
  tags: string[];
  draft?: boolean;
  published_date?: string;
  updated_date?: string;
  created_at: string; // Legacy fallback
}

function ArticlesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tagFilter = searchParams.get("tag");

  const [resources, setResources] = useState<Resource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchResources = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/resources`);
      const data = await response.json();
      setResources(data.resources);
      logger.debug("Fetched articles", { count: data.resources.length });
    } catch (error) {
      logger.error("Error fetching articles", error);
    } finally {
      setIsLoading(false);
    }
  }, [API_URL]);

  useEffect(() => {
    fetchResources();
  }, [fetchResources]);

  const filteredResources = resources.filter((resource) => {
    // Filter by tag if tag query param is present
    if (tagFilter && !resource.tags.includes(tagFilter)) {
      return false;
    }

    // Filter by search query
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      resource.title.toLowerCase().includes(query) ||
      resource.content.toLowerCase().includes(query) ||
      resource.tags.some((tag) => tag.toLowerCase().includes(query))
    );
  });

  const handleTagClick = (tag: string) => {
    router.push(`/knowledge-base/articles?tag=${encodeURIComponent(tag)}`);
  };

  const clearTagFilter = () => {
    router.push("/knowledge-base/articles");
  };

  return (
    <div className={styles.container}>
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div className={styles.breadcrumb}>
            <Breadcrumb section="articles" />
          </div>
          <h1 className={styles.title}>Articles</h1>
        </div>
      </header>

      <main className={styles.main}>
        {/* Tag Filter Banner */}
        {tagFilter && (
          <div className={styles.tagFilterBanner}>
            <div className={styles.filterInfo}>
              <span className={styles.filterLabel}>Filtering by tag:</span>
              <span className={styles.tagPill}>#{tagFilter}</span>
            </div>
            <button onClick={clearTagFilter} className={styles.clearButton}>
              Clear filter
            </button>
          </div>
        )}

        {/* Search Bar */}
        <div className={styles.searchBar}>
          <input
            type="text"
            placeholder="Search articles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
        </div>

        {/* Articles List */}
        <div className={styles.articlesList}>
          {isLoading ? (
            <div className={styles.loadingState}>
              <p>Loading articles...</p>
            </div>
          ) : filteredResources.length === 0 ? (
            <div className={styles.emptyState}>
              <p className={styles.emptyMessage}>
                {searchQuery ? "No articles match your search" : "No articles yet"}
              </p>
              {searchQuery && (
                <button onClick={() => setSearchQuery("")} className={styles.clearSearchButton}>
                  Clear search
                </button>
              )}
            </div>
          ) : (
            filteredResources.map((resource) => {
              // Extract first paragraph or first 200 chars as preview
              const preview = resource.content
                .split("\n\n")[0]
                .replace(/[#*`[\]]/g, "")
                .substring(0, 200);
              const needsTruncation = resource.content.length > 200;

              return (
                <Link
                  key={resource.id}
                  href={`/knowledge-base/articles/${resource.id}`}
                  className={styles.articleCard}
                >
                  <div className={styles.articleHeader}>
                    <h3 className={styles.articleTitle}>{resource.title}</h3>
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
                            resource.published_date || resource.created_at
                          ).toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                          })}
                        </>
                      )}
                    </div>
                  </div>

                  {/* Preview */}
                  <p className={styles.articlePreview}>
                    {preview}
                    {needsTruncation && "..."}
                  </p>

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
      </main>
    </div>
  );
}

export default function ArticlesPage() {
  return (
    <Suspense
      fallback={
        <div className={styles.container}>
          <header className={styles.header}>
            <div className={styles.headerContent}>
              <h1 className={styles.title}>Articles</h1>
            </div>
          </header>
          <main className={styles.main}>
            <div className={styles.loadingState}>
              <p>Loading articles...</p>
            </div>
          </main>
        </div>
      }
    >
      <ArticlesContent />
    </Suspense>
  );
}
