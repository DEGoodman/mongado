/**
 * Breadcrumb component for consistent navigation hierarchy
 * Handles both Articles and Notes sections with proper structure
 */

import Link from "next/link";

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
    <nav aria-label="Breadcrumb" className={`text-sm ${className}`}>
      <ol className="flex items-center gap-2">
        {/* Knowledge Base root */}
        <li>
          <Link
            href="/knowledge-base"
            className="text-blue-600 hover:text-blue-800 hover:underline"
          >
            ← Knowledge Base
          </Link>
        </li>

        {/* Section (Articles or Notes) */}
        <li className="flex items-center gap-2">
          <span className="text-gray-400" aria-hidden="true">
            /
          </span>
          <Link href={config.href} className="text-blue-600 hover:text-blue-800 hover:underline">
            {config.label}
          </Link>
        </li>

        {/* Subsection (optional, e.g., "All notes") */}
        {subsection && (
          <li className="flex items-center gap-2">
            <span className="text-gray-400" aria-hidden="true">
              &gt;
            </span>
            <span className="text-gray-600">{subsection}</span>
          </li>
        )}
      </ol>
    </nav>
  );
}
