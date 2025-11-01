from core.scrapers.base import BaseScraper
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
import time
import re
from pathlib import Path
from core.utils.logging import info, success, error
import json
import time

class DiaryScraper(BaseScraper):
    BASE = "https://diarypsikologi.id"

    def scrape_drama_page(self, drama_id: str):
        url = f"{self.BASE}/drama/{drama_id}"
        info(f"Diary: accessing {url}")
        
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
        except Exception as e:
            error(f"Diary: cannot access page: {e}")
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        thumb_tag = soup.select_one("img.film_bookCover__YRcsa")
        thumbnail_url = thumb_tag['src'] if thumb_tag else None

        title_tag = soup.select_one("h1.film_bookName__ys_T3")
        title = title_tag.text.strip() if title_tag else "Unknown Title"

        desc_tag = soup.select_one("p.film_pcIntro__BB1Ox")
        description = desc_tag.text.strip() if desc_tag else ""

        episode_list = []
        items = soup.select("div.pcSeries_listItem__sd0Xp")
        for idx, item in enumerate(items, start=1):
            link_tag = item.select_one("a.pcSeries_imgBox___UvIY")
            if not link_tag:
                continue
            href = link_tag.get("href")
            if not href or not href.startswith("/video/"):
                continue
            path = href.lstrip("/video/")

            ep_num_tag = item.select_one("a.pcSeries_rightIntro__UFC_8 span.pcSeries_pageNum__xkXBk")
            ep_num = ep_num_tag.text.strip() if ep_num_tag else f"{idx:02d}"

            ep_title_tag = item.select_one("a.pcSeries_rightIntro__UFC_8 span.pcSeries_title__R9vip")
            ep_title = ep_title_tag.text.strip() if ep_title_tag else ""

            episode_list.append({
                "path": path,
                "episode_number": ep_num,
                "episode_title": ep_title,
                "index": idx
            })

        info(f"Diary: Found title='{title}', {len(episode_list)} episodes")
        return {
            "thumbnail": thumbnail_url,
            "title": title,
            "description": description,
            "episodes": episode_list
        }

    def get_real_video_url_selenium(self, video_path: str):
        url_page = f"{self.BASE}/video/{video_path}"
        info(f"Diary: accessing video page: {url_page}")

        chrome_options = self._get_chrome_options()

        driver = None
        try:
            driver = self._init_external_driver(chrome_options)
            driver.get(url_page)
            time.sleep(5)
            logs = driver.get_log('performance')
            mp4_urls = set()
            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']
                    if ('Network.responseReceived' == log['method'] or 'Network.requestWillBeSent' == log['method']):
                        params = log.get('params', {})
                        request = params.get('request', {})
                        url = request.get('url', '')
                        if url.endswith('.mp4'):
                            mp4_urls.add(url)
                except Exception:
                    pass
            if mp4_urls:
                video_url = list(mp4_urls)[0]
                success(f"Diary: Found MP4 URL: {video_url}")
                return video_url
            else:
                error("Diary: No MP4 URLs found in network logs")
                return None
        except Exception as e:
            error(f"Diary selenium error: {e}")
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _get_chrome_options(self):
        from selenium import webdriver
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        return options

    def _init_external_driver(self, options):
        from selenium import webdriver
        return webdriver.Chrome(options=options)

    def download_thumbnail(self, thumbnail_url: str, folder_path: Path):
        if not thumbnail_url:
            info("Diary: No thumbnail available")
            return False
        try:
            import requests
            response = requests.get(thumbnail_url, stream=True, timeout=20)
            response.raise_for_status()
            filename = thumbnail_url.split("/")[-1].split("?")[0]
            file_path = folder_path / filename
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(8192):
                    f.write(chunk)
            success(f"Diary: Thumbnail downloaded to {file_path}")
            return True
        except Exception as e:
            error(f"Diary: Failed to download thumbnail: {e}")
            return False

    def download_file_with_resume(self, url: str, file_path: Path, max_retries: int = 5):
        info(f"Diary: Starting download from: {url}")
        import requests
        headers = {"User-Agent": "Mozilla/5.0"}
        session = requests.Session()
        downloaded = 0
        if file_path.exists():
            downloaded = file_path.stat().st_size
            info(f"Diary: Resuming download from {downloaded} bytes")
        for attempt in range(max_retries):
            try:
                range_header = {'Range': f'bytes={downloaded}-'}
                headers.update(range_header)
                with session.get(url, headers=headers, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    total_size = None
                    if 'content-length' in r.headers:
                        total_size = downloaded + int(r.headers['content-length'])
                    mode = "ab" if downloaded else "wb"
                    with open(file_path, mode) as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size:
                                    progress = int(50 * downloaded / total_size)
                                    print(f"\r[{'=' * progress}{' ' * (50 - progress)}] {downloaded}/{total_size} bytes", end="")
                print(f"\nDiary: Download complete: {file_path}")
                return True
            except Exception as e:
                error(f"Diary: Download attempt {attempt+1} failed: {e}")
                time.sleep(5)
        error(f"Diary: Failed to download after {max_retries} attempts")
        return False

    def download_series(self, drama_id: str, dest_folder: Path):
        info("Diary: Starting series download (scraping only)")
        dest_folder.mkdir(parents=True, exist_ok=True)
        drama_info = self.scrape_drama_page(drama_id)
        if not drama_info:
            error("Diary: Failed to get drama info")
            return None
        title = drama_info.get("title", "Unknown_Title")
        clean_title = "".join(x for x in title if (x.isalnum() or x in " _-")).strip()
        info_path = dest_folder / "info.txt"
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(f"Title: {drama_info.get('title', '')}\n\n")
            f.write("Description:\n")
            f.write(drama_info.get('description', '').strip() + "\n")
        success(f"Diary: Info saved to {info_path}")
        thumb_url = drama_info.get("thumbnail")
        if thumb_url:
            self.download_thumbnail(thumb_url, dest_folder)
        temp_concat_folder = dest_folder / "temp_concat"
        temp_concat_folder.mkdir(parents=True, exist_ok=True)
        episodes = drama_info.get("episodes", [])
        if not episodes:
            error("Diary: No episodes found")
            return None
        success(f"Diary: Found {len(episodes)} episodes to download")
        for idx, ep in enumerate(episodes, start=1):
            ep_path = ep["path"]
            ep_num = ep.get("episode_number", f"{idx:02d}")
            ep_title = ep.get("episode_title", "")
            info(f"Diary: Processing {idx:02d}.mp4 ({idx}/{len(episodes)}): {ep_title}")
            real_video_url = self.get_real_video_url_selenium(ep_path)
            if not real_video_url:
                error(f"Diary: Failed to get video URL for episode {ep_num}")
                continue
            filename = f"{idx:02d}.mp4"
            video_file_path = temp_concat_folder / filename
            if not self.download_file_with_resume(real_video_url, video_file_path):
                error(f"Diary: Failed to download episode {ep_num}")
                continue
        success(f"Diary: All episodes downloaded to {temp_concat_folder}")
        return temp_concat_folder

    def get_episode_count(self, drama_id: str) -> int:
        drama_info = self.scrape_drama_page(drama_id)
        if drama_info and drama_info.get("episodes"):
            return len(drama_info["episodes"])
        return 0
