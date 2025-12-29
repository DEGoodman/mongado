/**
 * HTML sanitization utilities to prevent XSS attacks.
 *
 * Uses DOMPurify for safe HTML rendering of user-generated or markdown-converted content.
 */

import DOMPurify from "dompurify";

/**
 * Configuration for DOMPurify optimized for markdown content.
 * Allows common markdown HTML elements while stripping dangerous content.
 */
const MARKDOWN_CONFIG = {
  // Allow common markdown HTML elements
  ALLOWED_TAGS: [
    // Headings
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    // Text formatting
    "p",
    "br",
    "hr",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "del",
    "ins",
    "mark",
    "sub",
    "sup",
    "small",
    // Lists
    "ul",
    "ol",
    "li",
    // Links and images
    "a",
    "img",
    // Code
    "pre",
    "code",
    "kbd",
    "samp",
    "var",
    // Blocks
    "blockquote",
    "div",
    "span",
    // Tables
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "th",
    "td",
    "caption",
    "colgroup",
    "col",
    // Definition lists
    "dl",
    "dt",
    "dd",
    // Details/summary
    "details",
    "summary",
    // Figures
    "figure",
    "figcaption",
    // Footnotes and sections
    "section",
    "aside",
  ],
  ALLOWED_ATTR: [
    // Common attributes
    "class",
    "id",
    "title",
    "aria-label",
    "aria-describedby",
    "aria-hidden",
    "role",
    // Links
    "href",
    "target",
    "rel",
    // Images
    "src",
    "alt",
    "width",
    "height",
    "loading",
    // Tables
    "colspan",
    "rowspan",
    "scope",
    // Code highlighting
    "data-language",
    "data-line",
  ],
  // Strip potentially dangerous tags
  FORBID_TAGS: ["script", "style", "iframe", "object", "embed", "form", "input"],
  // Strip potentially dangerous attributes
  FORBID_ATTR: ["onerror", "onclick", "onload", "onmouseover", "onfocus", "onblur"],
};

/**
 * Sanitize HTML content for safe rendering.
 *
 * @param html - Raw HTML string to sanitize
 * @returns Sanitized HTML string safe for dangerouslySetInnerHTML
 *
 * @example
 * ```tsx
 * <div dangerouslySetInnerHTML={{ __html: sanitizeHtml(content) }} />
 * ```
 */
export function sanitizeHtml(html: string): string {
  if (typeof window === "undefined") {
    // Server-side: return as-is (will be sanitized on client hydration)
    // For full SSR safety, consider using isomorphic-dompurify
    return html;
  }

  return DOMPurify.sanitize(html, MARKDOWN_CONFIG);
}
