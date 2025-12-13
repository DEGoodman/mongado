"""Server-side markdown rendering with syntax highlighting.

Converts markdown to HTML with:
- Syntax highlighting via Pygments
- Wikilink support for [[note-id]] format
- GFM (GitHub Flavored Markdown) support
- Heading anchors for table of contents
"""

import re
from typing import Any

from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.front_matter import front_matter_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound


def _highlight_code(code: str, lang: str, **_kwargs: Any) -> str:
    """Highlight code using Pygments.

    Args:
        code: Source code to highlight
        lang: Language identifier (e.g., 'python', 'javascript')
        **_kwargs: Additional arguments (ignored)

    Returns:
        HTML string with syntax highlighting
    """
    try:
        lexer = get_lexer_by_name(lang, stripall=True) if lang else guess_lexer(code)
    except ClassNotFound:
        # Fallback to plain text if language not found
        return f"<pre><code>{code}</code></pre>"

    formatter = HtmlFormatter(
        style="monokai",  # Dark theme similar to oneDark
        cssclass="highlight",
        noclasses=False,  # Use CSS classes for better control
    )

    return str(highlight(code, lexer, formatter))


def _convert_wikilinks(html: str) -> str:
    """Convert [[note-id]] wikilinks to HTML links.

    Args:
        html: HTML content with potential wikilinks

    Returns:
        HTML with wikilinks converted to anchor tags
    """
    pattern = r"\[\[([a-z0-9-]+)\]\]"

    def replace_wikilink(match: re.Match[str]) -> str:
        note_id = match.group(1)
        return f'<a href="/knowledge-base/notes/{note_id}" class="wikilink">{match.group(0)}</a>'

    return re.sub(pattern, replace_wikilink, html)


def render_markdown_to_html(markdown_content: str) -> str:
    """Render markdown to HTML with syntax highlighting and wikilinks.

    Args:
        markdown_content: Raw markdown string

    Returns:
        Rendered HTML string
    """
    # Configure markdown-it with plugins
    md = (
        MarkdownIt("gfm-like", {"html": True, "linkify": True, "typographer": True})
        .use(front_matter_plugin)
        .use(footnote_plugin)
        .enable("table")
    )

    # Override fence renderer to use Pygments
    # Note: markdown-it-py has a different signature than markdown-it (JS)
    def custom_fence(tokens: Any, idx: int, options: Any, env: Any, **_kwargs: Any) -> str:
        """Custom fence renderer that uses Pygments for syntax highlighting."""
        token = tokens[idx]
        code = token.content
        lang = token.info.strip() if token.info else ""

        if lang:
            return _highlight_code(code, lang)
        else:
            # Plain code block without language
            return f"<pre><code>{code}</code></pre>"

    # Replace the default fence renderer
    md.renderer.rules["fence"] = custom_fence  # type: ignore[attr-defined]

    # Render markdown to HTML
    html = md.render(markdown_content)

    # Convert wikilinks
    html = _convert_wikilinks(html)

    return html


def get_pygments_css() -> str:
    """Get Pygments CSS for syntax highlighting.

    Returns:
        CSS string for syntax highlighting styles
    """
    formatter = HtmlFormatter(style="monokai", cssclass="highlight")
    return str(formatter.get_style_defs(".highlight"))
