import Link from "next/link";
import styles from "./page.module.scss";

export default function ArticleNotFound() {
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
