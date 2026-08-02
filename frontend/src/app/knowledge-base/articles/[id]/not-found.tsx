import Link from "next/link";
import styles from "./page.module.scss";

/**
 * The "article not found" experience. Exported so DraftArticleFallback.tsx
 * (#184) can render the identical UI for anonymous/unauthorized visitors
 * without duplicating markup - Next's automatic not-found.tsx wiring only
 * fires for the server-side notFound() case (published articles), not the
 * client-side draft check.
 */
export function ArticleNotFoundContent() {
  return (
    <div className={styles.container}>
      <div className={styles.errorContainer}>
        <div className={styles.errorCard}>
          <h2 className={styles.errorTitle}>Error</h2>
          <p className={styles.errorMessage}>Article not found</p>
          <Link href="/knowledge-base/articles" className={styles.backLink}>
            ← Back to articles
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ArticleNotFound() {
  return <ArticleNotFoundContent />;
}
