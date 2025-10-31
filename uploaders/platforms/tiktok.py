"""
Enhance TikTokUploader: profile selection, wait-for-processing, retries
"""

from pathlib import Path
from typing import Optional, List
import time

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
            opts.add_argument("--window-size=1440,900")
        d = webdriver.Chrome(options=opts)
        d.set_page_load_timeout(180)
        self.driver = d
        return d

    def login_interactive(self):
        d = self._build_driver()
        d.get("https://www.tiktok.com/login")
        logger.info("Silakan login, sesi akan tersimpan di profile.")
        input("Tekan Enter setelah login selesai...")
        return True

    def _wait_processing(self, d, timeout=420):
        """Heuristik menunggu proses upload/processing selesai sebelum Post."""
        try:
            WebDriverWait(d, timeout).until(
                EC.any_of(
                    EC.presence_of_element_located((By.XPATH, "//button[.//span[contains(., 'Post')]]")),
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Post') or contains(., 'Upload') or contains(., 'Publis') ]")),
                )
            )
        except Exception:
            logger.warning("Menunggu Post timeout; lanjut mencoba klik tombol jika ada.")

    def _set_caption(self, d, caption: str, tags: Optional[List[str]]):
        full_caption = caption
        if tags:
            full_caption = (caption + "\n" + " ".join(f"#{t}" for t in tags)).strip()
        try:
            WebDriverWait(d, 90).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable=true]")))
            box = d.find_element(By.CSS_SELECTOR, "div[contenteditable=true]")
            box.click()
            box.send_keys(full_caption)
        except Exception:
            logger.warning("Gagal set caption, melanjutkan...")

    def upload(self, video_path: Path, caption: str = "", tags: Optional[List[str]] = None, retries: int = 3) -> bool:
        d = self.driver or self._build_driver()
        try:
            d.get("https://www.tiktok.com/upload?lang=en")
            WebDriverWait(d, 180).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type=file]")))
            file_input = d.find_element(By.CSS_SELECTOR, "input[type=file]")
            file_input.send_keys(str(video_path.resolve()))

            self._set_caption(d, caption, tags)
            self._wait_processing(d)

            # Retry klik tombol Post
            for attempt in range(1, retries + 1):
                try:
                    btn = WebDriverWait(d, 60).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Post') or contains(., 'Upload') or contains(., 'Publish') ]"))
                    )
                    btn.click()
                    time.sleep(8)
                    logger.info("Post diklik, cek notifikasi sukses di UI.")
                    return True
                except Exception as e:
                    logger.warning(f"Percobaan klik Post {attempt}/{retries} gagal: {e}")
                    time.sleep(5)
            return False
        except Exception as e:
            logger.error(f"TikTok upload error: {e}")
            return False
        finally:
            if self.headless and self.driver:
                try:
                    self.driver.quit()
                except:  # noqa
                    pass
