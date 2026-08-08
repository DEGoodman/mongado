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
  section: "articles" | "notes" | "toolbox" | "inspire" | "library";
  /** Set to true on list pages to link back to the parent hub */
  toHub?: boolean;
  className?: string;
}

export default function Breadcrumb({ section, toHub = false, className = "" }: BreadcrumbProps) {
  // If toHub is true, link back to the parent hub. The Library is a top-level
  // app, so its hub is the home page; everything else lives under the KB.
  if (toHub) {
    const hubHref = section === "library" ? "/" : "/knowledge-base";
    return (
      <nav aria-label="Breadcrumb" className={`${styles.breadcrumb} ${className}`}>
        <Link href={hubHref} className={styles.link}>
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
    toolbox: {
      label: "Back",
      href: "/knowledge-base",
    },
    inspire: {
      label: "Back",
      href: "/knowledge-base",
    },
    library: {
      label: "Back",
      href: "/library",
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
