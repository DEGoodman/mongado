"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";
import Link from "next/link";

interface MarkdownWithWikilinksProps {
  content: string | null | undefined;
}

export default function MarkdownWithWikilinks({ content }: MarkdownWithWikilinksProps) {
  // Handle null/undefined content
  if (!content) {
    return (
      <div className="prose prose-sm max-w-none sm:prose lg:prose-lg">
        <p className="italic text-gray-500">No content</p>
      </div>
    );
  }

  // Split content by wikilinks and render each part
  const parts = content.split(/(\[\[[a-z0-9-]+\]\])/g);

  return (
    <div className="prose prose-sm max-w-none overflow-x-auto">
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
        }
      `}</style>
      {parts.map((part, i) => {
        const match = part.match(/\[\[([a-z0-9-]+)\]\]/);
        if (match) {
          // Render wikilink as a special styled link
          return (
            <Link
              key={i}
              href={`/knowledge-base/notes/${match[1]}`}
              className="inline-block rounded bg-blue-50 px-1 font-mono text-sm text-blue-600 no-underline hover:underline"
            >
              {part}
            </Link>
          );
        }
        // Render regular markdown
        return (
          <ReactMarkdown key={i} remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSlug]}>
            {part}
          </ReactMarkdown>
        );
      })}
    </div>
  );
}
