"""Load note templates from filesystem."""

import logging
from pathlib import Path
from typing import Any

import frontmatter

logger = logging.getLogger(__name__)

# Cache for loaded templates
_templates_cache: dict[str, dict[str, Any]] | None = None


def load_templates() -> dict[str, dict[str, Any]]:
    """Load all note templates from static/templates directory.

    Templates are cached in memory and returned on subsequent calls.
    Restart the server to reload templates.

    Returns:
        Dictionary mapping template ID to template data
    """
    global _templates_cache

    if _templates_cache is not None:
        return _templates_cache

    templates_dir = Path(__file__).parent.parent / "static" / "templates"

    if not templates_dir.exists():
        logger.warning("Templates directory not found: %s", templates_dir)
        _templates_cache = {}
        return _templates_cache

    templates: dict[str, dict[str, Any]] = {}
    md_files = sorted(templates_dir.glob("*.md"))
    logger.info("Loading %d templates from %s", len(md_files), templates_dir)

    for md_file in md_files:
        try:
            post = frontmatter.load(md_file)

            template_id = post.get("id", md_file.stem)
            templates[template_id] = {
                "id": template_id,
                "title": post.get("title", template_id.replace("-", " ").title()),
                "description": post.get("description", ""),
                "icon": post.get("icon", "📝"),
                "content": post.content,
            }
            logger.debug("Loaded template: %s", template_id)

        except Exception as e:
            logger.error("Failed to load template %s: %s", md_file.name, e)
            continue

    logger.info("Successfully loaded %d templates", len(templates))
    _templates_cache = templates
    return templates


def get_template(template_id: str) -> dict[str, Any] | None:
    """Get a specific template by ID.

    Args:
        template_id: The template identifier (e.g., "person", "book")

    Returns:
        Template data dict or None if not found
    """
    templates = load_templates()
    return templates.get(template_id)


def list_templates() -> list[dict[str, Any]]:
    """List all available templates with metadata (without full content).

    Returns:
        List of template metadata dictionaries
    """
    templates = load_templates()
    return [
        {
            "id": t["id"],
            "title": t["title"],
            "description": t["description"],
            "icon": t["icon"],
        }
        for t in templates.values()
    ]
