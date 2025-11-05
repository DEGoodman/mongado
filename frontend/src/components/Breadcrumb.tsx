/**
 * Breadcrumb component for consistent navigation hierarchy
 * Handles both Articles and Notes sections with proper structure
 */

import Link from "next/link";
import styles from "./Breadcrumb.module.scss";

interface BreadcrumbProps {
  section: "articles" | "notes";
  subsection?: string; // e.g., "All notes" for notes list page
  className?: string;
}

export default function Breadcrumb({ section, subsection, className = "" }: BreadcrumbProps) {
  const sectionConfig = {
    articles: {
      label: "Articles",
      href: "/knowledge-base/articles",
    },
    notes: {
      label: "Notes",
      href: "/knowledge-base/notes",
    },
  };

  const config = sectionConfig[section];

  return (
    <nav aria-label="Breadcrumb" className={`${styles.breadcrumb} ${className}`}>
      <ol className={styles.list}>
        {/* Knowledge Base root */}
        <li>
          <Link href="/knowledge-base" className={styles.link}>
            ← Knowledge Base
          </Link>
        </li>

        {/* Section (Articles or Notes) */}
        <li className={styles.listItem}>
          <span className={styles.separator} aria-hidden="true">
            /
          </span>
          <Link href={config.href} className={styles.link}>
            {config.label}
          </Link>
        </li>

        {/* Subsection (optional, e.g., "All notes") */}
        {subsection && (
          <li className={styles.listItem}>
            <span className={styles.separator} aria-hidden="true">
              &gt;
            </span>
            <span className={styles.subsection}>{subsection}</span>
          </li>
        )}
      </ol>
    </nav>
  );
}
