"use client";

import React, { useMemo, memo, useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";
import Link from "next/link";
import type { Components } from "react-markdown";
import dynamic from "next/dynamic";
import styles from "./MarkdownWithWikilinks.module.scss";

// Lazy load syntax highlighter to reduce initial bundle size (~200KB)
// Only loads when first code block is rendered
const SyntaxHighlighter = dynamic(
  () => import("react-syntax-highlighter").then((mod) => mod.Prism),
  {
    loading: () => (
      <div className="animate-pulse bg-gray-800 rounded p-4">Loading syntax highlighter...</div>
    ),
    ssr: false,
  }
);

// Lazy load theme separately
const useSyntaxTheme = () => {
  const [theme, setTheme] = useState<any>(null);

  useEffect(() => {
    import("react-syntax-highlighter/dist/esm/styles/prism").then((mod) => {
      setTheme(mod.oneDark);
    });
  }, []);

  return theme;
};

interface MarkdownWithWikilinksProps {
  content: string | null | undefined;
}

// Process children to convert [[note-id]] and [[article:id]] to Link components
const processWikilinks = (children: React.ReactNode): React.ReactNode => {
  if (typeof children === "string") {
    // Split on both note wikilinks and article wikilinks
    const parts = children.split(/(\[\[(?:article:)?\d*[a-z0-9-]*\]\])/g);
    return parts.map((part, i) => {
      // Check for article link first: [[article:123]]
      const articleMatch = part.match(/\[\[article:(\d+)\]\]/);
      if (articleMatch) {
        return (
          <Link
            key={i}
            href={`/knowledge-base/articles/${articleMatch[1]}`}
            className={`${styles.wikilink} ${styles.articleLink}`}
          >
            📄 Article {articleMatch[1]}
          </Link>
        );
      }

      // Check for note link: [[note-id]]
      const noteMatch = part.match(/\[\[([a-z0-9-]+)\]\]/);
      if (noteMatch) {
        return (
          <Link key={i} href={`/knowledge-base/notes/${noteMatch[1]}`} className={styles.wikilink}>
            {part}
          </Link>
        );
      }
      return part;
    });
  }

  if (Array.isArray(children)) {
    return children.map((child, i) => {
      if (typeof child === "string") {
        return <span key={i}>{processWikilinks(child)}</span>;
      }
      return child;
    });
  }

  return children;
};

function MarkdownWithWikilinks({ content }: MarkdownWithWikilinksProps) {
  const syntaxTheme = useSyntaxTheme();
  const [showSyntaxHighlighting, setShowSyntaxHighlighting] = useState(false);

  // Progressive rendering: show content first, then enable syntax highlighting
  useEffect(() => {
    // Delay syntax highlighting to prioritize initial render
    const timer = setTimeout(() => {
      setShowSyntaxHighlighting(true);
    }, 100);
    return () => clearTimeout(timer);
  }, []);

  // Memoize components to prevent recreation on every render
  // This is especially important for large articles with many code blocks
  // NOTE: Must be before early return to satisfy React Hooks rules
  const components: Components = useMemo(
    () => ({
      // Process text nodes to convert wikilinks to actual links
      p: ({ children, ...props }) => {
        const processedChildren = processWikilinks(children);
        return <p {...props}>{processedChildren}</p>;
      },
      li: ({ children, ...props }) => {
        const processedChildren = processWikilinks(children);
        return <li {...props}>{processedChildren}</li>;
      },
      // Syntax highlighting for code blocks
      code: ({ node, inline, className, children, ...props }: any) => {
        const match = /language-(\w+)/.exec(className || "");
        const language = match ? match[1] : "";

        // Show plain code first for faster initial render
        if (!inline && language && showSyntaxHighlighting && syntaxTheme) {
          return (
            <SyntaxHighlighter style={syntaxTheme} language={language} PreTag="div" {...props}>
              {String(children).replace(/\n$/, "")}
            </SyntaxHighlighter>
          );
        }

        // Fallback to plain code block
        return (
          <code className={className} {...props}>
            {children}
          </code>
        );
      },
    }),
    [showSyntaxHighlighting, syntaxTheme] // Re-create when highlighting becomes available
  );

  // Handle null/undefined content after hooks
  if (!content) {
    return (
      <div className={`${styles.container} prose prose-sm`}>
        <p className={styles.emptyState}>No content</p>
      </div>
    );
  }

  return (
    <div className={`${styles.container} prose prose-sm`}>
      <style jsx global>{`
        /* Fix table overflow in all browsers */
        .prose table {
          display: block;
          overflow-x: auto;
          white-space: nowrap;
        }

        /* Ensure tables don't break container */
        .prose th,
        .prose td {
          white-space: normal;
          word-break: break-word;
        }

        /* Consistent, compact typography for better information density */
        .prose {
          font-size: 0.9375rem; /* 15px */
          line-height: 1.6;
        }

        .prose h1 {
          font-size: 1.875rem; /* 30px */
          line-height: 1.2;
          margin-top: 0;
          margin-bottom: 1rem;
        }

        .prose h2 {
          font-size: 1.5rem; /* 24px */
          line-height: 1.3;
          margin-top: 2rem;
          margin-bottom: 0.75rem;
        }

        .prose h3 {
          font-size: 1.25rem; /* 20px */
          line-height: 1.4;
          margin-top: 1.5rem;
          margin-bottom: 0.5rem;
        }

        .prose h4 {
          font-size: 1.125rem; /* 18px */
          line-height: 1.4;
          margin-top: 1.25rem;
          margin-bottom: 0.5rem;
        }

        .prose p {
          margin-top: 0.75rem;
          margin-bottom: 0.75rem;
        }

        .prose ul,
        .prose ol {
          margin-top: 0.75rem;
          margin-bottom: 0.75rem;
        }

        .prose li {
          margin-top: 0.25rem;
          margin-bottom: 0.25rem;
        }

        .prose code {
          font-size: 0.875em;
        }

        .prose pre {
          margin-top: 1rem;
          margin-bottom: 1rem;
          padding: 1rem;
          background-color: #1f2937;
          border-radius: 0.5rem;
          overflow-x: auto;
        }

        .prose pre code {
          background-color: transparent;
          color: #e5e7eb;
          padding: 0;
          font-size: 0.875rem;
          line-height: 1.7;
        }

        /* Inline code (not in pre blocks) */
        .prose :not(pre) > code {
          background-color: #f3f4f6;
          color: #1f2937;
          padding: 0.125rem 0.375rem;
          border-radius: 0.25rem;
          font-size: 0.875em;
          font-weight: 500;
        }
      `}</style>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSlug]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

// Export memoized component to prevent re-renders when parent re-renders
// This is crucial for performance with large articles
export default memo(MarkdownWithWikilinks);
