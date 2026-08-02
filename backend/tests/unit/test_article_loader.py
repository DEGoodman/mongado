"""Unit tests for adapters.article_loader module.

These tests verify article loading logic including:
- Draft articles are always loaded (filtering happens downstream, see
  dependencies.get_static_articles vs get_all_static_articles, #184)
- Proper loading of date fields (published_date, updated_date)
- Cache invalidation
"""

import tempfile
from pathlib import Path

from adapters import article_loader


class TestArticleLoaderDraftFiltering:
    """Tests for draft article loading.

    The loader itself no longer filters drafts by environment (#184) - it
    always loads every article, tagged with its `draft` field. Visibility is
    decided by callers (dependencies.py, routers/articles.py).
    """

    def create_test_article(self, article_dir: Path, filename: str, draft: bool = False) -> None:
        """Helper to create a test article with frontmatter."""
        content = f"""---
id: 1
title: "Test Article"
tags: ["test"]
draft: {str(draft).lower()}
published_date: "2025-10-14T10:00:00"
created_at: "2025-10-14T10:00:00"
---

# Test Article

This is test content.
"""
        article_path = article_dir / filename
        article_path.write_text(content)

    def test_loads_both_published_and_draft_articles(self):
        """Should load both draft and published articles, regardless of mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            articles_dir = Path(tmpdir)

            # Create published and draft articles
            self.create_test_article(articles_dir, "published.md", draft=False)
            self.create_test_article(articles_dir, "draft.md", draft=True)

            # Clear cache before test
            article_loader._articles_cache = None
            article_loader._articles_hash = None

            articles = article_loader.load_static_articles_from_local(articles_dir)

            # Should load both articles, with draft field preserved
            assert len(articles) == 2
            draft_flags = {a["draft"] for a in articles}
            assert draft_flags == {True, False}

    def test_loads_date_fields(self):
        """Should properly load published_date and updated_date fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            articles_dir = Path(tmpdir)

            # Create article with dates
            content = """---
id: 2
title: "Article with Dates"
tags: ["test"]
draft: false
published_date: "2025-10-14T10:00:00"
updated_date: "2025-10-20T15:30:00"
created_at: "2025-10-14T10:00:00"
---

# Article with dates
"""
            (articles_dir / "dated.md").write_text(content)

            # Clear cache before test
            article_loader._articles_cache = None
            article_loader._articles_hash = None

            articles = article_loader.load_static_articles_from_local(articles_dir)

            assert len(articles) == 1
            article = articles[0]
            assert article["published_date"] == "2025-10-14T10:00:00"
            assert article["updated_date"] == "2025-10-20T15:30:00"
            assert article["created_at"] == "2025-10-14T10:00:00"

    def test_defaults_draft_to_false_when_missing(self):
        """Should treat articles without draft field as published."""
        with tempfile.TemporaryDirectory() as tmpdir:
            articles_dir = Path(tmpdir)

            # Create article without draft field
            content = """---
id: 3
title: "Legacy Article"
tags: ["test"]
created_at: "2025-10-14T10:00:00"
---

# Legacy Article
"""
            (articles_dir / "legacy.md").write_text(content)

            # Clear cache before test
            article_loader._articles_cache = None
            article_loader._articles_hash = None

            articles = article_loader.load_static_articles_from_local(articles_dir)

            assert len(articles) == 1
            # Should default to False (published)
            assert articles[0].get("draft", False) is False

    def test_cache_invalidation_on_file_change(self):
        """Cache should invalidate when article files change."""
        with tempfile.TemporaryDirectory() as tmpdir:
            articles_dir = Path(tmpdir)

            # Create initial article
            self.create_test_article(articles_dir, "article.md", draft=False)

            # Clear cache before test
            article_loader._articles_cache = None
            article_loader._articles_hash = None

            # First load
            articles1 = article_loader.load_static_articles_from_local(articles_dir)
            assert len(articles1) == 1

            # Add another article
            self.create_test_article(articles_dir, "article2.md", draft=False)

            # Second load should detect change
            articles2 = article_loader.load_static_articles_from_local(articles_dir)
            assert len(articles2) == 2


class TestArticleLoaderCaching:
    """Tests for article caching behavior."""

    def test_uses_cache_when_files_unchanged(self):
        """Should return cached articles when files haven't changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            articles_dir = Path(tmpdir)

            # Create test article
            content = """---
id: 4
title: "Cached Article"
tags: ["test"]
draft: false
published_date: "2025-10-14T10:00:00"
created_at: "2025-10-14T10:00:00"
---

# Cached Article
"""
            (articles_dir / "cached.md").write_text(content)

            # Clear cache before test
            article_loader._articles_cache = None
            article_loader._articles_hash = None

            # First load
            articles1 = article_loader.load_static_articles_from_local(articles_dir)

            # Second load should use cache (same reference)
            articles2 = article_loader.load_static_articles_from_local(articles_dir)

            # Should return the same cached object
            assert articles1 is articles2
