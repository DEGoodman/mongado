"""Unit tests for adapters.article_loader module.

These tests verify article loading logic including:
- Draft article filtering based on environment
- Proper loading of date fields (published_date, updated_date)
- Cache invalidation
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from adapters import article_loader


class TestArticleLoaderDraftFiltering:
    """Tests for draft article filtering in different environments."""

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

    def test_loads_published_articles_in_production(self):
        """Should load non-draft articles in production mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            articles_dir = Path(tmpdir)

            # Create published and draft articles
            self.create_test_article(articles_dir, "published.md", draft=False)
            self.create_test_article(articles_dir, "draft.md", draft=True)

            # Mock production mode (debug=False)
            with patch("adapters.article_loader.settings.debug", False):
                # Clear cache before test
                article_loader._articles_cache = None
                article_loader._articles_hash = None

                articles = article_loader.load_static_articles_from_local(articles_dir)

                # Should only load published article
                assert len(articles) == 1
                assert articles[0]["draft"] is False

    def test_loads_all_articles_in_dev_mode(self):
        """Should load both draft and published articles in dev mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            articles_dir = Path(tmpdir)

            # Create published and draft articles
            self.create_test_article(articles_dir, "published.md", draft=False)
            self.create_test_article(articles_dir, "draft.md", draft=True)

            # Mock dev mode (debug=True)
            with patch("adapters.article_loader.settings.debug", True):
                # Clear cache before test
                article_loader._articles_cache = None
                article_loader._articles_hash = None

                articles = article_loader.load_static_articles_from_local(articles_dir)

                # Should load both articles
                assert len(articles) == 2
                draft_count = sum(1 for a in articles if a.get("draft", False))
                assert draft_count == 1

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
