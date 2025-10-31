"""
Platform strategy and metadata generator
"""

from pathlib import Path
from typing import Dict, Any

from core.utils.logging import get_logger

logger = get_logger(__name__)


def apply_platform_strategy(context) -> None:
    """Adjust processing options based on selected platforms"""
    platforms = context.options.get("platforms") or context.config.platforms.enabled_platforms
    # Default strategies
    if "tiktok" in platforms:
        # prefer 180s splits for TikTok
        if context.options.get("split_duration") is None:
            context.config.processing.split_duration = 180
    if "youtube" in platforms or "dailymotion" in platforms or "facebook" in platforms:
        # long-form: no split by default unless explicitly set
        if context.options.get("split_duration") is None and "tiktok" not in platforms:
            context.config.processing.split_duration = None


def generate_basic_metadata(video_source: str, working_dir: Path) -> Dict[str, Any]:
    """Create simple metadata from file/folder name; placeholder for advanced AI generator"""
    stem = Path(video_source).stem if not video_source.startswith("http") else "Video"
    title = stem.replace("_", " ").replace("-", " ").title()
    tags = ["drama", "movie", "indonesia"]
    desc = f"{title}\n\nProcessed by Video Toolkit."
    meta = {"title": title, "description": desc, "tags": tags}
    logger.info(f"Generated metadata: {meta}")
    return meta
