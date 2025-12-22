"""Parse and process [[wikilinks]] in Zettelkasten notes."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class WikilinkParser:
    """Parse [[note-id]] and [[article:id]] wikilinks from markdown content."""

    # Regex pattern for [[note-id]] (standard note links)
    WIKILINK_PATTERN = re.compile(r"\[\[([a-z0-9-]+)\]\]")

    # Regex pattern for [[article:id]] (article references)
    ARTICLE_LINK_PATTERN = re.compile(r"\[\[article:(\d+)\]\]")

    # Combined pattern for all wikilinks (note or article)
    ALL_LINKS_PATTERN = re.compile(r"\[\[(?:article:)?([a-z0-9-]+|\d+)\]\]")

    def extract_links(self, content: str) -> list[str]:
        """Extract all [[note-id]] links from content (excludes article links).

        Args:
            content: Markdown content containing wikilinks

        Returns:
            List of unique note IDs
        """
        links = self.WIKILINK_PATTERN.findall(content)
        unique_links = list(dict.fromkeys(links))  # Preserve order, remove duplicates
        logger.debug("Extracted %d note wikilinks from content", len(unique_links))
        return unique_links

    def extract_article_links(self, content: str) -> list[int]:
        """Extract all [[article:id]] links from content.

        Args:
            content: Markdown content containing article wikilinks

        Returns:
            List of unique article IDs (integers)
        """
        links = self.ARTICLE_LINK_PATTERN.findall(content)
        unique_ids = list(dict.fromkeys(int(lid) for lid in links))
        logger.debug("Extracted %d article wikilinks from content", len(unique_ids))
        return unique_ids

    def extract_all_links(self, content: str) -> dict[str, list[str] | list[int]]:
        """Extract all wikilinks from content, categorized by type.

        Args:
            content: Markdown content containing wikilinks

        Returns:
            Dict with 'notes' (list of str IDs) and 'articles' (list of int IDs)
        """
        return {
            "notes": self.extract_links(content),
            "articles": self.extract_article_links(content),
        }

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

    def render_links_html(
        self,
        content: str,
        notes_map: dict[str, dict[str, Any]],
        articles_map: dict[int, dict[str, Any]] | None = None,
    ) -> str:
        """Convert [[note-id]] and [[article:id]] to clickable HTML links.

        Args:
            content: Markdown content with wikilinks
            notes_map: Dict mapping note IDs to note objects with 'title' field
            articles_map: Optional dict mapping article IDs to article objects

        Returns:
            Content with wikilinks replaced by HTML anchor tags
        """
        articles_map = articles_map or {}

        # First, handle article links [[article:id]]
        def replace_article_link(match: re.Match[str]) -> str:
            article_id = int(match.group(1))

            if article_id in articles_map:
                article = articles_map[article_id]
                title = article.get("title", f"Article {article_id}")
                url = f"/knowledge-base/articles/{article_id}"
                return f'<a href="{url}" class="wikilink wikilink-article" title="{title}">📄 {title}</a>'
            else:
                # Broken article link
                return f'<span class="wikilink-broken" title="Article not found">[[article:{article_id}]]</span>'

        content = self.ARTICLE_LINK_PATTERN.sub(replace_article_link, content)

        # Then, handle note links [[note-id]]
        def replace_note_link(match: re.Match[str]) -> str:
            note_id = match.group(1)

            if note_id in notes_map:
                note = notes_map[note_id]
                title = note.get("title", note_id)
                url = f"/knowledge-base/notes/{note_id}"
                return f'<a href="{url}" class="wikilink wikilink-note" title="{title}">{note_id}</a>'
            else:
                # Broken link
                return f'<span class="wikilink-broken" title="Note not found">[[{note_id}]]</span>'

        return self.WIKILINK_PATTERN.sub(replace_note_link, content)

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
