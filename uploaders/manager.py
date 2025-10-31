"""
Add TikTok support in UploadManager (skeleton)
"""

from pathlib import Path
from typing import Dict

from core.utils.logging import get_logger
from .platforms.telegram import TelegramUploader
from .platforms.tiktok import TikTokUploader

logger = get_logger(__name__)


class UploadManager:
    def __init__(self):
        self.uploaders = {
            "telegram": TelegramUploader(),
            "tiktok": TikTokUploader(profile_name="default"),
        }

    def upload(self, platform: str, file_path: Path, metadata: Dict = None) -> bool:
        if platform not in self.uploaders:
            logger.error(f"Unsupported platform: {platform}")
            return False
        metadata = metadata or {}
        if platform == "telegram":
            cap = metadata.get("caption", "")
            return self.uploaders[platform].upload_video(file_path, caption=cap)
        if platform == "tiktok":
            cap = metadata.get("caption", "")
            tags = metadata.get("tags", [])
            return self.uploaders[platform].upload(file_path, caption=cap, tags=tags)
        return False
