/**
 * Breadcrumb component - Simple back navigation
 * Shows "← Back" link to return to the parent page
 *
 * Usage:
 * - On detail pages (articles/[id], notes/[id]): links to list page
 * - On list pages (articles, notes): links to /knowledge-base hub
 */

import Link from "next/link";
import styles from "./Breadcrumb.module.scss";

interface BreadcrumbProps {
  section: "articles" | "notes";
  /** Set to true on list pages to link back to /knowledge-base hub */
  toHub?: boolean;
  className?: string;
}

export default function Breadcrumb({ section, toHub = false, className = "" }: BreadcrumbProps) {
  // If toHub is true, link back to the KB hub page
  if (toHub) {
    return (
      <nav aria-label="Breadcrumb" className={`${styles.breadcrumb} ${className}`}>
        <Link href="/knowledge-base" className={styles.link}>
          ← Back
        </Link>
      </nav>
    );
  }

  // Otherwise, link back to the section list page
  const sectionConfig = {
    articles: {
      label: "Back",
      href: "/knowledge-base/articles",
    },
    notes: {
      label: "Back",
      href: "/knowledge-base/notes",
    },
  };

  const config = sectionConfig[section];

  return (
    <nav aria-label="Breadcrumb" className={`${styles.breadcrumb} ${className}`}>
      <Link href={config.href} className={styles.link}>
        ← {config.label}
      </Link>
    </nav>
  );
}
