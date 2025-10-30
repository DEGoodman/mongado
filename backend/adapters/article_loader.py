"""Load static articles from filesystem or S3."""

import hashlib
import logging
from pathlib import Path
from typing import Any

import frontmatter

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Cache for loaded articles - cleared on restart
_articles_cache: list[dict[str, Any]] | None = None
_articles_hash: str | None = None


def _compute_directory_hash(articles_dir: Path) -> str:
    """Compute hash of all markdown files in directory for cache invalidation.

    Includes file count, names, and modification times to detect:
    - New files added
    - Existing files modified
    - Files removed

    Args:
        articles_dir: Path to directory containing markdown files

    Returns:
        SHA256 hash of all file metadata
    """
    if not articles_dir.exists():
        return ""

    md_files = sorted(articles_dir.glob("*.md"))

    # Start with file count to ensure new/deleted files trigger invalidation
    hash_content = f"count:{len(md_files)}:"

    for md_file in md_files:
        # Include filename, modification time, and file size
        stat = md_file.stat()
        hash_content += f"{md_file.name}:{stat.st_mtime}:{stat.st_size}:"

    hash_result = hashlib.sha256(hash_content.encode()).hexdigest()

    # Log hash computation for debugging (only first 8 chars to avoid log spam)
    logger.debug(
        "Computed directory hash: %s (files: %d, input length: %d)",
        hash_result[:8],
        len(md_files),
        len(hash_content),
    )

    return hash_result


def load_static_articles_from_local(articles_dir: Path) -> list[dict[str, Any]]:
    """Load articles from local filesystem with intelligent caching.

    Articles are cached in memory and only reloaded if files change.
    This provides fast response times while allowing hot-reload in development.

    Draft articles (draft: true in frontmatter) are only included in development mode.
    In production, they are filtered out.

    Args:
        articles_dir: Path to directory containing markdown files

    Returns:
        List of article dictionaries with metadata and content
    """
    global _articles_cache, _articles_hash

    if not articles_dir.exists():
        logger.warning("Static articles directory not found: %s", articles_dir)
        return []

    # Check if cache is valid
    current_hash = _compute_directory_hash(articles_dir)

    if _articles_cache is not None:
        if _articles_hash == current_hash:
            logger.debug(
                "✓ Cache HIT: Using cached articles (hash: %s, count: %d)",
                current_hash[:8],
                len(_articles_cache),
            )
            return _articles_cache
        else:
            logger.info(
                "✗ Cache MISS: Hash changed from %s to %s - reloading articles",
                _articles_hash[:8] if _articles_hash else "None",
                current_hash[:8],
            )
    else:
        logger.info("✗ Cache MISS: No cached articles - initial load")

    # Cache miss or invalidation - reload articles
    logger.info("Loading articles from %s", articles_dir)
    articles: list[dict[str, Any]] = []

    # Load all .md files
    md_files = sorted(articles_dir.glob("*.md"))
    logger.info("Found %d markdown files in %s", len(md_files), articles_dir)

    # Determine if we should include drafts (dev mode only)
    is_dev_mode = settings.debug
    logger.info("Environment mode: %s (drafts %s)",
                "development" if is_dev_mode else "production",
                "visible" if is_dev_mode else "hidden")

    for md_file in md_files:
        try:
            # Parse markdown with frontmatter
            post = frontmatter.load(md_file)

            # Check if article is a draft
            is_draft = post.get("draft", False)

            # Skip drafts in production
            if is_draft and not is_dev_mode:
                logger.info("Skipping draft article in production: %s", post.get("title", md_file.stem))
                continue

            # Extract metadata from frontmatter
            article = {
                "id": post.get("id"),
                "title": post.get("title", md_file.stem),
                "content": post.content,  # Markdown content
                "content_type": "markdown",
                "url": post.get("url"),
                "tags": post.get("tags", []),
                "draft": is_draft,
                "published_date": post.get("published_date"),
                "updated_date": post.get("updated_date"),
                "created_at": post.get("created_at"),  # Legacy field
            }

            articles.append(article)
            logger.debug("Loaded article: %s%s",
                        article["title"],
                        " [DRAFT]" if is_draft else "")

        except Exception as e:
            logger.error("Failed to load %s: %s", md_file, e)
            continue

    logger.info("Successfully loaded %d articles (%d drafts filtered)",
                len(articles),
                len([a for a in articles if a.get("draft", False)]))

    # Update cache
    _articles_cache = articles
    _articles_hash = current_hash

    return articles


def load_static_articles_from_s3(bucket: str, prefix: str = "articles/") -> list[dict[str, Any]]:
    """Load articles from S3 bucket.

    Draft articles (draft: true in frontmatter) are only included in development mode.
    In production, they are filtered out.

    Args:
        bucket: S3 bucket name
        prefix: S3 prefix/folder for articles

    Returns:
        List of article dictionaries with metadata and content
    """
    articles: list[dict[str, Any]] = []

    try:
        import boto3

        s3_client = boto3.client("s3")

        # List all .md files in the bucket/prefix
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)

        if "Contents" not in response:
            logger.warning("No articles found in s3://%s/%s", bucket, prefix)
            return articles

        md_files = [obj for obj in response["Contents"] if obj["Key"].endswith(".md")]
        logger.info("Found %d markdown files in s3://%s/%s", len(md_files), bucket, prefix)

        # Determine if we should include drafts (dev mode only)
        is_dev_mode = settings.debug
        logger.info("Environment mode: %s (drafts %s)",
                    "development" if is_dev_mode else "production",
                    "visible" if is_dev_mode else "hidden")

        for obj in md_files:
            try:
                # Download file content
                response = s3_client.get_object(Bucket=bucket, Key=obj["Key"])
                content = response["Body"].read().decode("utf-8")

                # Parse frontmatter
                post = frontmatter.loads(content)

                # Check if article is a draft
                is_draft = post.get("draft", False)

                # Skip drafts in production
                if is_draft and not is_dev_mode:
                    logger.info("Skipping draft article in production: %s", post.get("title", Path(obj["Key"]).stem))
                    continue

                article = {
                    "id": post.get("id"),
                    "title": post.get("title", Path(obj["Key"]).stem),
                    "content": post.content,
                    "content_type": "markdown",
                    "url": post.get("url"),
                    "tags": post.get("tags", []),
                    "draft": is_draft,
                    "published_date": post.get("published_date"),
                    "updated_date": post.get("updated_date"),
                    "created_at": post.get("created_at"),  # Legacy field
                }

                articles.append(article)
                logger.debug("Loaded article from S3: %s%s",
                            article["title"],
                            " [DRAFT]" if is_draft else "")

            except Exception as e:
                logger.error("Failed to load %s: %s", obj["Key"], e)
                continue

    except ImportError:
        logger.error("boto3 not installed - cannot load from S3")
        return articles
    except Exception as e:
        logger.error("Failed to load articles from S3: %s", e)
        return articles

    logger.info("Successfully loaded %d articles from S3 (%d drafts filtered)",
                len(articles),
                len([a for a in articles if a.get("draft", False)]))
    return articles


def load_static_articles() -> list[dict[str, Any]]:
    """Load static articles based on configuration.

    Reads STATIC_ARTICLES_SOURCE from settings:
    - 'local' (default): Load from backend/static/articles/
    - 's3': Load from S3 bucket specified in STATIC_ARTICLES_S3_BUCKET

    Returns:
        List of article dictionaries
    """
    source = getattr(settings, "static_articles_source", "local").lower()
    logger.info("Loading static articles from: %s", source)

    if source == "s3":
        bucket = getattr(settings, "static_articles_s3_bucket", None)
        if not bucket:
            logger.error("S3 source selected but STATIC_ARTICLES_S3_BUCKET not configured")
            return []
        prefix = getattr(settings, "static_articles_s3_prefix", "articles/")
        return load_static_articles_from_s3(bucket, prefix)
    else:
        # Default to local filesystem
        articles_dir = Path(__file__).parent.parent / "static" / "articles"
        return load_static_articles_from_local(articles_dir)
