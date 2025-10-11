"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface RichTextDisplayProps {
  markdown: string;
}

export default function RichTextDisplay({ markdown }: RichTextDisplayProps) {
  return (
    <div className="prose prose-sm sm:prose lg:prose-lg max-w-none">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
    </div>
  );
}
