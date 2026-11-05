/**
 * Turn a markdown snippet into plain text for card previews.
 *
 * Previews (notes list, toolbox, note of the day) render text, not HTML, so
 * raw markdown leaked through as `**S**pecific`, `[[note-id]]`, `## Heading`.
 * This strips the common syntax; it isn't a full parser and doesn't need to be.
 */
export function markdownToPlainPreview(markdown: string, maxLength?: number): string {
  let text = markdown
    // Fenced code blocks: keep nothing (code in a preview is noise)
    .replace(/```[\s\S]*?(```|$)/g, " ")
    // Images ![alt](url) -> alt
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    // Links [text](url) -> text
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    // Wikilinks [[id|label]] / [[id]] -> label / id
    .replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, "$2")
    .replace(/\[\[([^\]]+)\]\]/g, "$1")
    // Inline code `x` -> x
    .replace(/`([^`]*)`/g, "$1")
    // Line-start markers: headings, blockquotes, list bullets, numbered lists
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s{0,3}>\s?/gm, "")
    .replace(/^\s*[-*+]\s+(\[[ xX]\]\s+)?/gm, "")
    .replace(/^\s*\d+[.)]\s+/gm, "")
    // Horizontal rules and table separator rows
    .replace(/^\s*([-*_]\s*){3,}$/gm, " ")
    .replace(/^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-*:?\s*$/gm, " ")
    // Table pipes
    .replace(/\s*\|\s*/g, " ")
    // Emphasis markers: **x**, __x__, *x*, _x_, ~~x~~ (inside words too, e.g. **S**pecific)
    .replace(/(\*\*|__|~~)(.+?)\1/g, "$2")
    .replace(/(^|[^\w*])\*(?!\s)([^*]+?)\*(?!\w)/g, "$1$2")
    .replace(/(^|[^\w])_(?!\s)([^_]+?)_(?!\w)/g, "$1$2")
    // Collapse whitespace
    .replace(/\s+/g, " ")
    .trim();

  if (maxLength !== undefined && text.length > maxLength) {
    text = text.slice(0, maxLength).trimEnd() + "…";
  }
  return text;
}
