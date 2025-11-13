"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";
import Link from "next/link";
import type { Components } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import styles from "./MarkdownWithWikilinks.module.scss";

interface MarkdownWithWikilinksProps {
  content: string | null | undefined;
}

export default function MarkdownWithWikilinks({ content }: MarkdownWithWikilinksProps) {
  // Handle null/undefined content
  if (!content) {
    return (
      <div className={`${styles.container} prose prose-sm`}>
        <p className={styles.emptyState}>No content</p>
      </div>
    );
  }

  // Custom component to handle text nodes and convert wikilinks
  const components: Components = {
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

      return !inline && language ? (
        <SyntaxHighlighter style={oneDark} language={language} PreTag="div" {...props}>
          {String(children).replace(/\n$/, "")}
        </SyntaxHighlighter>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
  };

  // Process children to convert [[note-id]] to Link components
  const processWikilinks = (children: React.ReactNode): React.ReactNode => {
    if (typeof children === "string") {
      const parts = children.split(/(\[\[[a-z0-9-]+\]\])/g);
      return parts.map((part, i) => {
        const match = part.match(/\[\[([a-z0-9-]+)\]\]/);
        if (match) {
          return (
            <Link key={i} href={`/knowledge-base/notes/${match[1]}`} className={styles.wikilink}>
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
