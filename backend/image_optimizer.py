"""Image optimization utilities for Knowledge Base static assets.

Provides tools to convert images to WebP format for optimal compression
and performance. WebP offers 25-35% smaller file sizes than JPEG/PNG with
equivalent quality.
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def is_pillow_available() -> bool:
    """Check if Pillow (PIL) is installed.

    Returns:
        True if Pillow is available, False otherwise
    """
    try:
        import PIL  # noqa: F401

        return True
    except ImportError:
        return False


def optimize_image_to_webp(
    input_path: Path | str,
    output_path: Path | str | None = None,
    quality: int = 85,
    max_width: int = 1200,
) -> Path | None:
    """Convert image to WebP format with optimization.

    Args:
        input_path: Path to input image
        output_path: Path for output WebP file (default: same name with .webp)
        quality: WebP quality (0-100, default 85 for good balance)
        max_width: Maximum width in pixels (default 1200, maintains aspect ratio)

    Returns:
        Path to optimized WebP file, or None if optimization failed
    """
    input_path = Path(input_path)

    if not input_path.exists():
        logger.error("Input image not found: %s", input_path)
        return None

    # Default output path
    output_path = input_path.with_suffix(".webp") if output_path is None else Path(output_path)

    # Try Pillow first (preferred)
    if is_pillow_available():
        return _optimize_with_pillow(input_path, output_path, quality, max_width)

    # Fallback to cwebp command-line tool
    return _optimize_with_cwebp(input_path, output_path, quality, max_width)


def _optimize_with_pillow(
    input_path: Path, output_path: Path, quality: int, max_width: int
) -> Path | None:
    """Optimize image using Pillow library.

    Args:
        input_path: Path to input image
        output_path: Path for output WebP file
        quality: WebP quality (0-100)
        max_width: Maximum width in pixels

    Returns:
        Path to optimized WebP file, or None if failed
    """
    try:
        from PIL import Image

        logger.info("Optimizing %s -> %s (Pillow)", input_path.name, output_path.name)

        # Open and process image
        with Image.open(input_path) as img:
            # Convert RGBA to RGB if necessary (WebP handles transparency)
            if img.mode in ("RGBA", "LA", "P"):
                # Keep transparency for WebP
                pass
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Resize if needed
            if img.width > max_width:
                aspect_ratio = img.height / img.width
                new_height = int(max_width * aspect_ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                logger.info("Resized to %dx%d", max_width, new_height)

            # Save as WebP
            img.save(
                output_path,
                format="WEBP",
                quality=quality,
                method=6,  # Better compression (0-6, 6 is slowest but best)
            )

        output_size = output_path.stat().st_size
        input_size = input_path.stat().st_size
        reduction = ((input_size - output_size) / input_size) * 100

        logger.info(
            "Optimized: %s -> %s (%.1f%% reduction)",
            _format_bytes(input_size),
            _format_bytes(output_size),
            reduction,
        )

        return output_path

    except Exception as e:
        logger.error("Failed to optimize with Pillow: %s", e)
        return None


def _optimize_with_cwebp(
    input_path: Path, output_path: Path, quality: int, max_width: int
) -> Path | None:
    """Optimize image using cwebp command-line tool.

    Requires cwebp to be installed (brew install webp on macOS).

    Args:
        input_path: Path to input image
        output_path: Path for output WebP file
        quality: WebP quality (0-100)
        max_width: Maximum width in pixels

    Returns:
        Path to optimized WebP file, or None if failed
    """
    try:
        # Check if cwebp is available
        result = subprocess.run(
            ["which", "cwebp"], capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            logger.warning(
                "cwebp not found. Install with: brew install webp (macOS) or apt install webp (Linux)"
            )
            return None

        logger.info("Optimizing %s -> %s (cwebp)", input_path.name, output_path.name)

        # Build cwebp command
        cmd = [
            "cwebp",
            "-q",
            str(quality),
            "-resize",
            str(max_width),
            "0",  # Auto height
            "-m",
            "6",  # Best compression
            str(input_path),
            "-o",
            str(output_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            logger.error("cwebp failed: %s", result.stderr)
            return None

        output_size = output_path.stat().st_size
        input_size = input_path.stat().st_size
        reduction = ((input_size - output_size) / input_size) * 100

        logger.info(
            "Optimized: %s -> %s (%.1f%% reduction)",
            _format_bytes(input_size),
            _format_bytes(output_size),
            reduction,
        )

        return output_path

    except Exception as e:
        logger.error("Failed to optimize with cwebp: %s", e)
        return None


def _format_bytes(size: int) -> str:
    """Format byte size for human readability.

    Args:
        size: Size in bytes

    Returns:
        Formatted string (e.g., "1.2 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def batch_optimize_directory(
    directory: Path | str, quality: int = 85, max_width: int = 1200
) -> list[Path]:
    """Optimize all images in a directory to WebP format.

    Args:
        directory: Directory containing images
        quality: WebP quality (0-100)
        max_width: Maximum width in pixels

    Returns:
        List of paths to optimized WebP files
    """
    directory = Path(directory)

    if not directory.exists() or not directory.is_dir():
        logger.error("Directory not found: %s", directory)
        return []

    # Common image formats
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"}

    optimized_files = []

    for img_file in directory.rglob("*"):
        if img_file.suffix.lower() in image_extensions and not img_file.name.startswith("."):
            output_path = img_file.with_suffix(".webp")

            # Skip if WebP already exists and is newer
            if output_path.exists() and output_path.stat().st_mtime > img_file.stat().st_mtime:
                logger.debug("Skipping %s (WebP already exists)", img_file.name)
                continue

            result = optimize_image_to_webp(img_file, output_path, quality, max_width)
            if result:
                optimized_files.append(result)

    logger.info("Batch optimization complete: %d files processed", len(optimized_files))
    return optimized_files


# CLI usage example
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python image_optimizer.py <input_file> [output_file] [quality] [max_width]")
        print("  or: python image_optimizer.py --batch <directory>")
        sys.exit(1)

    # Setup logging for CLI
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            print("Error: --batch requires directory path")
            sys.exit(1)

        directory = Path(sys.argv[2])
        quality = int(sys.argv[3]) if len(sys.argv) > 3 else 85
        max_width = int(sys.argv[4]) if len(sys.argv) > 4 else 1200

        batch_optimize_directory(directory, quality, max_width)

    else:
        input_file = Path(sys.argv[1])
        output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
        quality = int(sys.argv[3]) if len(sys.argv) > 3 else 85
        max_width = int(sys.argv[4]) if len(sys.argv) > 4 else 1200

        result = optimize_image_to_webp(input_file, output_file, quality, max_width)
        if result:
            print(f"Success: {result}")
        else:
            print("Optimization failed")
            sys.exit(1)
