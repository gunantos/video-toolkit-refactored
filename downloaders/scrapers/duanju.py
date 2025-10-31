"""
Duanju scraper (skeleton) with Playwright
"""

from pathlib import Path
from typing import Optional

from core.utils.logging import get_logger

logger = get_logger(__name__)


class DuanjuScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def download_series(self, url_or_id: str, output_dir: Path) -> Optional[Path]:
        """Skeleton method: implement site-specific logic here.
        For now, returns None and logs a notice.
        """
        logger.warning("DuanjuScraper is not yet implemented. Returning None.")
        return None
