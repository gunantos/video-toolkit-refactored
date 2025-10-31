"""
Telegram uploader using Bot API
"""

import os
from pathlib import Path
import requests
from typing import Optional

from core.utils.logging import get_logger

logger = get_logger(__name__)


class TelegramUploader:
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        if not self.token or not self.chat_id:
            logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set; Telegram upload will fail")

    def upload_video(self, video_path: Path, caption: str = "") -> bool:
        url = f"https://api.telegram.org/bot{self.token}/sendVideo"
        with open(video_path, "rb") as f:
            files = {"video": f}
            data = {"chat_id": self.chat_id, "caption": caption}
            r = requests.post(url, data=data, files=files, timeout=600)
            try:
                r.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"Telegram upload failed: {e} - {r.text}")
                return False
