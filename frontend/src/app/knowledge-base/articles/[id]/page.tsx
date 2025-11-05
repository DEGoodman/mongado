"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import MarkdownWithWikilinks from "@/components/MarkdownWithWikilinks";
import ArticleTableOfContents from "@/components/ArticleTableOfContents";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import SettingsDropdown from "@/components/SettingsDropdown";
import Breadcrumb from "@/components/Breadcrumb";
import Badge from "@/components/Badge";
import { TagPillList } from "@/components/TagPill";
import { logger } from "@/lib/logger";
import styles from "./page.module.scss";

interface Article {
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

export default function ArticleDetailPage() {
  const params = useParams();
  const router = useRouter();
  const articleId = parseInt(params.id as string);

  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    async function fetchArticle() {
      try {
        setLoading(true);
        const response = await fetch(`${API_URL}/api/resources/${articleId}`);

        if (!response.ok) {
          throw new Error("Article not found");
        }

        const data = await response.json();
        setArticle(data.resource);
        logger.info("Article loaded", { id: articleId });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to load article";
        setError(message);
        logger.error("Failed to load article", err);
      } finally {
        setLoading(false);
      }
    }

    fetchArticle();
  }, [articleId, API_URL]);

  const handleTagClick = (tag: string) => {
    router.push(`/knowledge-base/articles?tag=${encodeURIComponent(tag)}`);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSkeleton}>
            <div className={styles.skeletonTitle}></div>
            <div className={styles.skeletonContent}></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className={styles.container}>
        <div className={styles.errorContainer}>
          <div className={styles.errorCard}>
            <h2 className={styles.errorTitle}>Error</h2>
            <p className={styles.errorMessage}>{error || "Article not found"}</p>
            <Link href="/knowledge-base/articles" className={styles.backLink}>
              ← Back to articles
            </Link>
          </div>
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
      <header className={styles.header}>
        <div className={styles.headerContent}>
          {/* Breadcrumb and Settings */}
          <div className={styles.headerTop}>
            <Breadcrumb section="articles" />
            <SettingsDropdown />
          </div>

          {/* Content Type Badge */}
          <div className={styles.badge}>
            <Badge type="article" />
          </div>

          {/* Title */}
          <h1 className={styles.title}>{article.title}</h1>

          {/* Metadata */}
          <div className={styles.metadata}>
            <div className={styles.metaItem}>
              <span aria-hidden="true">📅</span>
              <span>
                Published{" "}
                <time dateTime={article.published_date || article.created_at}>
                  {new Date(article.published_date || article.created_at).toLocaleDateString(
                    "en-US",
                    {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    }
                  )}
                </time>
              </span>
            </div>
            {article.updated_date && article.updated_date !== article.published_date && (
              <div className={styles.metaItem}>
                <span aria-hidden="true">✏️</span>
                <span>
                  Last updated{" "}
                  <time dateTime={article.updated_date}>
                    {new Date(article.updated_date).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </time>
                </span>
              </div>
            )}
          </div>

          {/* Tags */}
          {article.tags.length > 0 && (
            <div className={styles.tags}>
              <TagPillList tags={article.tags} showHash onClick={handleTagClick} />
            </div>
          )}
        </div>
      </header>

      {/* Content */}
      <main className={styles.main}>
        <div className={styles.contentGrid}>
          {/* Main Article Content */}
          <div className={styles.articleContent}>
            <article className={styles.articleCard}>
              {article.content_type === "markdown" || article.content_type === undefined ? (
                <MarkdownWithWikilinks content={article.content} />
              ) : (
                <div className="prose prose-sm max-w-none">
                  <p className="text-gray-700">{article.content}</p>
                </div>
              )}

              {article.url && (
                <div className={styles.externalLink}>
                  <h3 className={styles.linkTitle}>External Link</h3>
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={styles.linkUrl}
                  >
                    {article.url}
                  </a>
                </div>
              )}
            </article>

            {/* Back to articles */}
            <Link href="/knowledge-base/articles" className={styles.backLink}>
              ← Back to all articles
            </Link>
          </div>

          {/* Table of Contents Sidebar */}
          <div className={styles.tocSidebar}>
            {(article.content_type === "markdown" || article.content_type === undefined) && (
              <ArticleTableOfContents content={article.content} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
