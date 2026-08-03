"use client";

import { useEffect, useState } from "react";

import { apiGet, isAuthenticated } from "@/lib/api/client";
import { logger } from "@/lib/logger";
import { LoadingState } from "@/components/PageState";
import ArticleView, { type Article } from "./ArticleView";
import { ArticleNotFoundContent } from "./not-found";

/**
 * Rendered when the anonymous, server-side article fetch 404s (#184).
 *
 * A draft article always 404s from the public server fetch (page.tsx), since
 * that fetch has no way to carry the admin's localStorage token during SSR.
 * This component retries client-side with auth headers: if the caller is a
 * signed-in admin and the article turns out to exist (i.e. it's a draft),
 * render it with the Draft badge. Otherwise fall back to the same
 * "article not found" UI anonymous visitors always see - so nothing about
 * this path leaks whether an ID belongs to a draft.
 */
export default function DraftArticleFallback({ articleId }: { articleId: string }) {
  const [status, setStatus] = useState<"checking" | "not-found" | "found">("checking");
  const [article, setArticle] = useState<Article | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      setStatus("not-found");
      return;
    }

    let cancelled = false;

    async function fetchDraft() {
      try {
        const data = await apiGet<{ resource: Article }>(`/api/articles/${articleId}`);
        if (cancelled) return;
        setArticle(data.resource);
        setStatus("found");
      } catch (err) {
        logger.error("Failed to load draft article", err);
        if (!cancelled) setStatus("not-found");
      }
    }

    fetchDraft();

    return () => {
      cancelled = true;
    };
  }, [articleId]);

  if (status === "checking") {
    return <LoadingState inline label="Loading article" />;
  }

  if (status === "found" && article) {
    return <ArticleView article={article} />;
  }

  return <ArticleNotFoundContent />;
}
