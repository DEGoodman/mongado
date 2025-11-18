/**
 * Breadcrumb component - Simple back navigation
 * Shows "← Back" link to return to the section list page
 */

import Link from "next/link";
import styles from "./Breadcrumb.module.scss";

interface BreadcrumbProps {
  section: "articles" | "notes";
  className?: string;
}

export default function Breadcrumb({ section, className = "" }: BreadcrumbProps) {
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
