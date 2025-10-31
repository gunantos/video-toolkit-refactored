"""
Universal downloader using yt-dlp
"""

import subprocess
from pathlib import Path
from typing import Optional

from core.utils.logging import get_logger

logger = get_logger(__name__)


class UniversalDownloader:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str) -> Optional[Path]:
        template = str(self.output_dir / "%(title)s.%(ext)s")
        cmd = [
            "yt-dlp",
            "-f",
            "best",
            "--no-playlist",
            "-o",
            template,
            url,
        ]
        try:
            subprocess.run(cmd, check=True)
            # pick latest file
            files = sorted(self.output_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            return files[0] if files else None
        except subprocess.CalledProcessError as e:
            logger.error(f"yt-dlp failed: {e}")
            return None
