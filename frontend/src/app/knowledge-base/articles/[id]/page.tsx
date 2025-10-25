"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import MarkdownWithWikilinks from "@/components/MarkdownWithWikilinks";
import ArticleTableOfContents from "@/components/ArticleTableOfContents";
import AIPanel from "@/components/AIPanel";
import AIButton from "@/components/AIButton";
import SettingsDropdown from "@/components/SettingsDropdown";
import { logger } from "@/lib/logger";

interface Article {
  id: number;
  title: string;
  content: string;
  content_type?: string;
  url?: string;
  tags: string[];
  created_at: string;
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
        <div className="container mx-auto px-4 py-8">
          <div className="animate-pulse">
            <div className="mb-4 h-8 w-1/3 rounded bg-gray-200"></div>
            <div className="mb-4 h-64 rounded bg-gray-200"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
        <div className="container mx-auto px-4 py-8">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <h2 className="mb-2 font-semibold text-red-800">Error</h2>
            <p className="text-red-600">{error || "Article not found"}</p>
            <Link
              href="/knowledge-base/articles"
              className="mt-4 inline-block text-blue-600 hover:underline"
            >
              ← Back to articles
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* AI Panel */}
      <AIPanel isOpen={aiPanelOpen} onClose={() => setAiPanelOpen(false)} />

      {/* AI Button */}
      {!aiPanelOpen && <AIButton onClick={() => setAiPanelOpen(true)} />}

      {/* Header */}
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex gap-4">
              <Link href="/knowledge-base" className="text-sm text-blue-600 hover:text-blue-800">
                ← Knowledge Base
              </Link>
              <Link
                href="/knowledge-base/articles"
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                All articles
              </Link>
            </div>
            <SettingsDropdown />
          </div>

          <h1 className="mb-3 text-4xl font-bold text-gray-900">{article.title}</h1>

          <div className="flex items-center gap-4 text-sm text-gray-600">
            <time dateTime={article.created_at}>
              {new Date(article.created_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </time>
          </div>

          {/* Tags */}
          {article.tags.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {article.tags.map((tag, index) => (
                <span
                  key={index}
                  className="rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-700"
                >
                  #{tag}
                </span>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
          {/* Main Article Content */}
          <div className="lg:col-span-3">
            <article className="rounded-lg bg-white p-8 shadow-md">
              {article.content_type === "markdown" || article.content_type === undefined ? (
                <MarkdownWithWikilinks content={article.content} />
              ) : (
                <div className="prose prose-sm max-w-none">
                  <p className="text-gray-700">{article.content}</p>
                </div>
              )}

              {article.url && (
                <div className="mt-8 border-t pt-6">
                  <h3 className="mb-2 text-sm font-semibold text-gray-700">External Link</h3>
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    {article.url}
                  </a>
                </div>
              )}
            </article>

            {/* Back to articles */}
            <div className="mt-8">
              <Link
                href="/knowledge-base/articles"
                className="inline-flex items-center text-blue-600 hover:text-blue-800"
              >
                ← Back to all articles
              </Link>
            </div>
          </div>

          {/* Table of Contents Sidebar */}
          <div className="lg:col-span-1">
            {(article.content_type === "markdown" || article.content_type === undefined) && (
              <ArticleTableOfContents content={article.content} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
