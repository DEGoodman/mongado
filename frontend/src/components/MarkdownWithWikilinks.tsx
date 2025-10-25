"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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
    <div className="prose prose-sm max-w-none overflow-x-auto sm:prose lg:prose-lg">
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
          <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>
            {part}
          </ReactMarkdown>
        );
      })}
    </div>
  );
}
