from core.scrapers.base import BaseScraper
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List

from playwright.sync_api import sync_playwright
from core.utils.logging import get_logger

logger = get_logger(__name__)

class DuanjuScraper(BaseScraper):
    def __init__(self, headless: bool = True):
        super().__init__(headless)

    def _slugify(self, text: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9\-_]+", "-", text.strip())
        return re.sub(r"-+", "-", s).strip("-").lower() or "series"

    def _yt_dlp(self, url: str, out_dir: Path) -> Optional[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        template = str(out_dir / "%(title).180B-%(id)s.%(ext)s")
        cmd = [
            "yt-dlp", "-f", "best",
            "--no-playlist",
            "-o", template,
            url,
        ]
        try:
            subprocess.run(cmd, check=True)
            vids = sorted(out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
            return vids[0] if vids else None
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            return None

    def _concat_if_many(self, episodes_dir: Path, output_path: Path) -> Optional[Path]:
        parts = sorted(episodes_dir.glob("*.mp4"))
        if not parts:
            return None
        if len(parts) == 1:
            shutil.copy2(parts[0], output_path)
            return output_path
        list_file = episodes_dir / "_concat.txt"
        list_file.write_text("\n".join([f"file '{p.as_posix()}'" for p in parts]), encoding="utf-8")
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", str(output_path)
        ]
        subprocess.run(cmd, check=True)
        try:
            list_file.unlink()
        except Exception:
            pass
        return output_path if output_path.exists() else None

    def download_series(self, url_or_id: str, output_dir: Path) -> Optional[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)

        series_url = url_or_id if url_or_id.startswith("http") else f"https://duanju.example/series/{url_or_id}"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            logger.info(f"Opening series page: {series_url}")
            page.goto(series_url, wait_until="domcontentloaded")

            title = page.title() or "series"
            slug = self._slugify(title)
            series_root = output_dir / slug
            episodes_dir = series_root / "temp_episodes"
            episodes_dir.mkdir(parents=True, exist_ok=True)

            episode_links: List[str] = []
            try:
                els = page.query_selector_all("a[href*='episode'], .episode a, .episodes a")
                for el in els:
                    href = el.get_attribute("href")
                    if href and href not in episode_links:
                        if href.startswith("http"):
                            episode_links.append(href)
                        else:
                            base = page.url.rstrip("/")
                            if href.startswith("/"):
                                episode_links.append(base.split("/", 3)[0] + "//" + base.split("/", 3)[2] + href)
                            else:
                                episode_links.append(base + "/" + href)
            except Exception as e:
                logger.warning(f"Episode selector failed: {e}")

            if not episode_links:
                logger.warning("No episode links found; attempting direct download of provided URL")
                out = self._yt_dlp(series_url, episodes_dir)
                if not out:
                    return None
            else:
                logger.info(f"Found {len(episode_links)} episode candidates")
                for idx, ep_url in enumerate(episode_links, 1):
                    logger.info(f"Downloading episode {idx}/{len(episode_links)}: {ep_url}")
                    self._yt_dlp(ep_url, episodes_dir)

            combined = series_root / "combined_video.mp4"
            result = self._concat_if_many(episodes_dir, combined)
            context.close()
            browser.close()
            return result or combined if combined.exists() else None
