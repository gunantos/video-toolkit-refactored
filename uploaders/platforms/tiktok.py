"""
TikTok uploader (skeleton) using Selenium + user profile directory
"""

from pathlib import Path
from typing import Dict, Optional
import time
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.utils.logging import get_logger

logger = get_logger(__name__)


class TikTokUploader:
    def __init__(self, profile_name: str = "default", profiles_dir: Optional[Path] = None, headless: bool = False):
        self.profile_name = profile_name
        self.profiles_dir = Path(profiles_dir or "data/profiles/tiktok")
        self.headless = headless
        self.driver = None
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def _build_driver(self):
        opts = Options()
        user_data_dir = self.profiles_dir / self.profile_name
        user_data_dir.mkdir(parents=True, exist_ok=True)
        opts.add_argument(f"--user-data-dir={str(user_data_dir)}")
        if self.headless:
            opts.add_argument("--headless=new")
            opts.add_argument("--window-size=1280,900")
        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(120)
        self.driver = driver
        return driver

    def login_interactive(self):
        d = self._build_driver()
        d.get("https://www.tiktok.com/login")
        logger.info("Please complete login manually, the session will be kept in the profile directory.")
        input("Press Enter after finishing TikTok login...")
        return True

    def upload(self, video_path: Path, caption: str = "", tags: Optional[list] = None) -> bool:
        d = self.driver or self._build_driver()
        try:
            d.get("https://www.tiktok.com/upload?lang=en")
            WebDriverWait(d, 120).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type=file]")))
            file_input = d.find_element(By.CSS_SELECTOR, "input[type=file]")
            file_input.send_keys(str(video_path.resolve()))

            # Caption box
            try:
                WebDriverWait(d, 60).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable=true]")))
                cap_box = d.find_element(By.CSS_SELECTOR, "div[contenteditable=true]")
                full_caption = caption
                if tags:
                    full_caption = (caption + "\n" + " ".join(f"#{t}" for t in tags)).strip()
                cap_box.click()
                cap_box.clear() if hasattr(cap_box, "clear") else None
                cap_box.send_keys(full_caption)
            except Exception:
                logger.warning("Caption box not found; continuing...")

            # Publish button
            WebDriverWait(d, 300).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Post') or contains(., 'Upload')]")))
            btn = d.find_element(By.XPATH, "//button[contains(., 'Post') or contains(., 'Upload')]")
            btn.click()

            # Wait for completion
            time.sleep(10)
            logger.info("Upload triggered; verify on TikTok UI.")
            return True
        except Exception as e:
            logger.error(f"TikTok upload failed: {e}")
            return False
        finally:
            # keep browser open for session persistence unless headless
            if self.headless and self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
