"""Parse and process [[wikilinks]] in Zettelkasten notes."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class WikilinkParser:
    """Parse [[note-id]] wikilinks from markdown content."""

    # Regex pattern for [[note-id]] or [[article-slug]]
    WIKILINK_PATTERN = re.compile(r"\[\[([a-z0-9-]+)\]\]")

    def extract_links(self, content: str) -> list[str]:
        """Extract all [[note-id]] links from content.

        Args:
            content: Markdown content containing wikilinks

        Returns:
            List of unique note/article IDs
        """
        links = self.WIKILINK_PATTERN.findall(content)
        unique_links = list(dict.fromkeys(links))  # Preserve order, remove duplicates
        logger.debug("Extracted %d wikilinks from content", len(unique_links))
        return unique_links

    def validate_links(self, content: str, existing_ids: set[str]) -> tuple[list[str], list[str]]:
        """Validate wikilinks against existing note/article IDs.

        Args:
            content: Markdown content
            existing_ids: Set of valid note/article IDs

        Returns:
            Tuple of (valid_links, broken_links)
        """
        links = self.extract_links(content)
        valid = [link for link in links if link in existing_ids]
        broken = [link for link in links if link not in existing_ids]

        if broken:
            logger.warning("Found %d broken wikilinks: %s", len(broken), broken)

        return valid, broken

    def render_links_html(self, content: str, notes_map: dict[str, dict[str, Any]]) -> str:
        """Convert [[note-id]] to clickable HTML links.

        Args:
            content: Markdown content with wikilinks
            notes_map: Dict mapping note IDs to note objects with 'title' field

        Returns:
            Content with wikilinks replaced by HTML anchor tags
        """

        def replace_link(match: re.Match[str]) -> str:
            note_id = match.group(1)

            if note_id in notes_map:
                note = notes_map[note_id]
                title = note.get("title", note_id)
                # Determine if note or article based on ID format
                if "-" in note_id and not note_id.count("-") > 1:
                    # Likely a note (e.g., curious-elephant)
                    url = f"/knowledge-base/notes/{note_id}"
                    css_class = "wikilink-note"
                else:
                    # Likely an article (e.g., saas-billing-models)
                    url = f"/knowledge-base/articles/{note_id}"
                    css_class = "wikilink-article"

                return f'<a href="{url}" class="{css_class}" title="{title}">{note_id}</a>'
            else:
                # Broken link
                return f'<span class="wikilink-broken" title="Note not found">[[{note_id}]]</span>'

        return self.WIKILINK_PATTERN.sub(replace_link, content)

    def render_links_markdown(self, content: str, notes_map: dict[str, dict[str, Any]]) -> str:
        """Convert [[note-id]] to markdown links.

        Useful for exporting notes while preserving links.

        Args:
            content: Markdown content with wikilinks
            notes_map: Dict mapping note IDs to note objects

        Returns:
            Content with wikilinks replaced by markdown links
        """

        def replace_link(match: re.Match[str]) -> str:
            note_id = match.group(1)

            if note_id in notes_map:
                note = notes_map[note_id]
                title = note.get("title", note_id)
                url = f"/knowledge-base/notes/{note_id}"
                return f"[{title}]({url})"
            else:
                # Keep broken links as-is
                return f"[[{note_id}]]"

        return self.WIKILINK_PATTERN.sub(replace_link, content)

    def get_link_context(self, content: str, link_id: str, context_chars: int = 100) -> str | None:
        """Get surrounding context for a specific link.

        Useful for displaying backlink previews.

        Args:
            content: Markdown content
            link_id: Note ID to find context for
            context_chars: Number of characters before/after link

        Returns:
            Context string or None if link not found
        """
        pattern = re.compile(r"\[\[" + re.escape(link_id) + r"\]\]")
        match = pattern.search(content)

        if not match:
            return None

        start = max(0, match.start() - context_chars)
        end = min(len(content), match.end() + context_chars)

        context = content[start:end].strip()

        # Add ellipsis if truncated
        if start > 0:
            context = "..." + context
        if end < len(content):
            context = context + "..."

        return context


# Global instance
_parser: WikilinkParser | None = None


def get_wikilink_parser() -> WikilinkParser:
    """Get global WikilinkParser instance (singleton).

    Returns:
        WikilinkParser instance
    """
    global _parser
    if _parser is None:
        _parser = WikilinkParser()
    return _parser
