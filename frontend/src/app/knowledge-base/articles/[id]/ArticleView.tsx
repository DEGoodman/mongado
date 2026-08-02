"use client";

import Link from "next/link";
import { CalendarBlank, PencilSimple, NotePencil } from "@phosphor-icons/react/dist/ssr";

import AIAssistant from "@/components/AIAssistant";
import ArticleTableOfContents from "@/components/ArticleTableOfContents";
import Breadcrumb from "@/components/Breadcrumb";
import Badge from "@/components/Badge";
import { sanitizeHtml } from "@/lib/sanitize";
import ArticleTags from "./ArticleTags";
import RelatedNotes from "./RelatedNotes";
import styles from "./page.module.scss";

export interface Article {
  id: number;
  title: string;
  content: string;
  html_content?: string; // Pre-rendered HTML from backend
  content_type?: string;
  summary?: string;
  url?: string;
  tags: string[];
  draft?: boolean;
  published_date?: string;
  updated_date?: string;
  created_at: string; // Legacy fallback
}

/**
 * Renders a full article. Shared by the server-rendered happy path
 * (page.tsx) and the client-side draft fallback (DraftArticleFallback.tsx,
 * #184) so both stay visually identical.
 */
export default function ArticleView({ article }: { article: Article }) {
  const publishedDate = article.published_date || article.created_at;

  return (
    <div className={styles.container}>
      {/* AI panel + button island (only shown when LLM features enabled) */}
      <AIAssistant />

      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerContent}>
          {/* Breadcrumb */}
          <div className={styles.headerTop}>
            <Breadcrumb section="articles" />
          </div>

          {/* Content Type Badge and Draft Badge */}
          <div className={styles.badgeRow}>
            <Badge type="article" />
            {article.draft && <span className={styles.draftBadge}>Draft</span>}
          </div>

          {/* Title */}
          <h1 className={styles.title}>{article.title}</h1>

          {/* Metadata */}
          <div className={styles.metadata}>
            <div className={styles.metaItem}>
              <CalendarBlank size={14} aria-hidden="true" />
              <span>
                Published{" "}
                <time dateTime={publishedDate}>
                  {new Date(publishedDate).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </time>
              </span>
            </div>
            {article.updated_date && article.updated_date !== article.published_date && (
              <div className={styles.metaItem}>
                <PencilSimple size={14} aria-hidden="true" />
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
              <ArticleTags tags={article.tags} />
            </div>
          )}

          {/* Create Note from Article */}
          <div className={styles.actions}>
            <Link
              href={`/knowledge-base/notes/new?from_article=${article.id}&title=Notes on: ${encodeURIComponent(article.title)}&content=${encodeURIComponent(`See [[article:${article.id}]] for the full article.\n\n## Key Takeaways\n\n- `)}`}
              className={styles.createNoteButton}
            >
              <NotePencil size={16} aria-hidden="true" /> Create Note from Article
            </Link>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className={styles.main}>
        <div className={styles.contentGrid}>
          {/* Main Article Content */}
          <div className={styles.articleContent}>
            <article className={styles.articleCard}>
              {article.html_content ? (
                // Use pre-rendered HTML from backend (includes footnotes, syntax highlighting)
                // Sanitize to prevent XSS attacks
                <div
                  className={`${styles.renderedContent} prose prose-sm`}
                  dangerouslySetInnerHTML={{ __html: sanitizeHtml(article.html_content) }}
                />
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

            {/* Related Notes Section */}
            <RelatedNotes articleId={article.id} />
          </div>
        </div>
      </main>
    </div>
  );
}
