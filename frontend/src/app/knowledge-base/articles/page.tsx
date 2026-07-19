import { Suspense } from "react";
import type { Metadata } from "next";

import { getServerApiUrl } from "@/lib/server-api";
import ArticlesClient, { type ArticleMetadata } from "./ArticlesClient";
import { LoadingState } from "@/components/PageState";
import styles from "./page.module.scss";

export const metadata: Metadata = {
  title: "Articles",
};

// Server-render the list so article titles/summaries are in the initial HTML
// (#207). force-dynamic keeps `docker build` from prerendering this route
// (the backend isn't reachable at image-build time); the fetch below still
// caches the article list in the Next data cache between requests.
export const dynamic = "force-dynamic";

async function fetchArticles(): Promise<ArticleMetadata[]> {
  const response = await fetch(`${getServerApiUrl()}/api/articles`, {
    next: { revalidate: 300 },
  });
  if (!response.ok) {
    throw new Error(`Failed to load articles (${response.status})`);
  }

  const data = await response.json();
  return data.resources as ArticleMetadata[];
}

export default async function ArticlesPage() {
  const resources = await fetchArticles();

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
            <LoadingState inline variant="cards" label="Loading articles" />
          </main>
        </div>
      }
    >
      <ArticlesClient resources={resources} />
    </Suspense>
  );
}
