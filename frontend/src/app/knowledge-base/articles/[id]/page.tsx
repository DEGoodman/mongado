import type { Metadata } from "next";

import { getServerApiUrl } from "@/lib/server-api";
import ArticleView, { type Article } from "./ArticleView";
import DraftArticleFallback from "./DraftArticleFallback";

// Articles are static markdown cached in backend memory - render on the
// server so content is in the initial HTML (#207). No generateStaticParams:
// the backend isn't reachable during `docker build`, so pages render on
// first request and are then cached (ISR) for the revalidate window.
//
// A draft article always 404s from this anonymous server fetch (#184) - the
// admin token lives in localStorage, unreachable during SSR. That's fine:
// ISR only caches this shell (or the anonymous not-found fallback), never
// draft content, and DraftArticleFallback re-checks auth client-side on
// every load regardless of the cached shell.
export const revalidate = 300;

async function fetchArticle(id: string): Promise<Article | null> {
  if (!/^\d+$/.test(id)) return null;

  const response = await fetch(`${getServerApiUrl()}/api/articles/${id}`, {
    next: { revalidate: 300 },
  });
  if (!response.ok) return null;

  const data = await response.json();
  return data.resource as Article;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const article = await fetchArticle(id);
  if (!article) return { title: "Article not found" };

  return {
    title: article.title,
    description: article.summary,
    openGraph: {
      title: article.title,
      description: article.summary,
      type: "article",
    },
  };
}

export default async function ArticleDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const article = await fetchArticle(id);

  // Published article (or bad id format handled inside fetchArticle) - render
  // normally. Otherwise this might be a draft: hand off to the client
  // fallback, which retries with the admin's auth headers, if any.
  if (!article) {
    return <DraftArticleFallback articleId={id} />;
  }

  return <ArticleView article={article} />;
}
