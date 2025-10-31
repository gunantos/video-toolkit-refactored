"""
Upload manager with platform routing
"""

from pathlib import Path
from typing import Dict

from core.utils.logging import get_logger
from .platforms.telegram import TelegramUploader

logger = get_logger(__name__)


class UploadManager:
    def __init__(self):
        self.uploaders = {
            "telegram": TelegramUploader(),
        }

    def upload(self, platform: str, file_path: Path, metadata: Dict = None) -> bool:
        if platform not in self.uploaders:
            logger.error(f"Unsupported platform: {platform}")
            return False
        if platform == "telegram":
            cap = (metadata or {}).get("caption", "")
            return self.uploaders[platform].upload_video(file_path, caption=cap)
        return False
