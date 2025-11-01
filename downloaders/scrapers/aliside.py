import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import re
from pathlib import Path
from core.utils.logging import info, success, error, safe_filename
import json


class AlisideScraper:
    def __init__(self, headless=True):
        """Initialize Aliside scraper with Selenium"""
        self.base_url = "https://www.aliside.com"
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        if self.driver:
            return
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,720")
        self.driver = webdriver.Chrome(options=options)

    def get_video_info(self, series_id):
        """Get video information from detail page"""
        self._init_driver()
        detail_url = f"{self.base_url}/detail/{series_id}"
        info(f"🔍 Mengakses: {detail_url}")

        try:
            self.driver.get(detail_url)
            time.sleep(3)  # Wait for page to load

            thumbnail_url = self._extract_thumbnail()
            title = self._extract_title()
            description = self._extract_description()
            episodes = self._extract_episodes(series_id)

            return {
                'id': series_id,
                'title': title,
                'description': description,
                'thumbnail': thumbnail_url,
                'episodes': episodes,
                'total_episodes': len(episodes),
                'detail_url': detail_url
            }

        except Exception as e:
            error(f"❌ Error getting video info: {e}")
            return None

    def _extract_thumbnail(self):
        """Extract thumbnail URL from page"""
        try:
            thumbnail_element = self.driver.find_element(
                By.CSS_SELECTOR, 
                'a.picture[data-v-477cdb0a]'
            )
            style = thumbnail_element.get_attribute('style')
            match = re.search(r'url\("(.+?)"\)', style)
            if match:
                thumbnail_url = match.group(1)
                success(f"📸 Thumbnail found: {thumbnail_url}")
                return thumbnail_url
            else:
                error("❌ Thumbnail URL not found in style attribute")
                return None

        except Exception as e:
            error(f"❌ Error extracting thumbnail: {e}")
            return None

    def _extract_title(self):
        """Extract title from page"""
        try:
            title_element = self.driver.find_element(
                By.CSS_SELECTOR,
                'h2[data-v-477cdb0a] font'
            )
            title = title_element.text.strip()
            success(f"📝 Title: {title}")
            return title

        except Exception as e:
            error(f"❌ Error extracting title: {e}")
            return "Unknown Title"

    def _extract_description(self):
        """Extract description from page"""
        try:
            desc_element = self.driver.find_element(
                By.CSS_SELECTOR,
                'span.cus_info[data-v-477cdb0a] font'
            )
            description = desc_element.text.strip()
            success(f"📄 Description extracted (length: {len(description)} chars)")
            return description

        except Exception as e:
            error(f"❌ Error extracting description: {e}")
            return "No description available"

    def _extract_episodes(self, series_id):
        """Extract episode list from page"""
        try:
            episodes = []
            play_lists = self.driver.find_elements(
                By.CSS_SELECTOR,
                'div.play-list-item[data-v-477cdb0a]'
            )
            info(f"🎬 Found {len(play_lists)} episode sources")

            for source_idx, play_list in enumerate(play_lists):
                episode_links = play_list.find_elements(
                    By.CSS_SELECTOR,
                    'a.play-link[data-v-477cdb0a]'
                )
                for episode_link in episode_links:
                    href = episode_link.get_attribute('href')
                    episode_text = episode_link.text.strip()
                    match = re.search(r'episode=(\d+)', href)
                    if match:
                        episode_num = int(match.group(1))
                        source_match = re.search(r'source=([A-F0-9]+)', href)
                        source = source_match.group(1) if source_match else f"source_{source_idx}"
                        episodes.append({
                            'number': episode_num + 1,
                            'title': episode_text,
                            'url': f"{self.base_url}{href}",
                            'source': source,
                            'relative_path': href
                        })

            unique_episodes = {}
            for ep in episodes:
                key = ep['number']
                if key not in unique_episodes:
                    unique_episodes[key] = ep
            sorted_episodes = sorted(unique_episodes.values(), key=lambda x: x['number'])
            success(f"✅ Extracted {len(sorted_episodes)} unique episodes")
            return sorted_episodes

        except Exception as e:
            error(f"❌ Error extracting episodes: {e}")
            return []

    def download_series(self, series_id, output_folder):
        try:
            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)
            video_info = self.get_video_info(series_id)
            if not video_info:
                return None
            self._save_metadata(video_info, output_folder)
            if video_info.get('thumbnail'):
                self._download_thumbnail(video_info['thumbnail'], output_folder)
            temp_concat_folder = output_folder / "temp_concat"
            temp_concat_folder.mkdir(parents=True, exist_ok=True)
            self._save_download_instructions(video_info, temp_concat_folder)
            info("📺 Aliside scraper completed metadata extraction")
            info("🔗 Episode URLs ready for manual download or yt-dlp integration")
            return temp_concat_folder

        except Exception as e:
            error(f"❌ Error downloading series: {e}")
            return None

    def _save_download_instructions(self, video_info, temp_folder):
        try:
            instructions_file = temp_folder / "download_instructions.txt"
            with open(instructions_file, 'w', encoding='utf-8') as f:
                f.write("ALISIDE EPISODE DOWNLOAD INSTRUCTIONS\n")
                f.write("="*50 + "\n\n")
                f.write(f"Series: {video_info['title']}\n")
                f.write(f"Total Episodes: {video_info['total_episodes']}\n\n")
                f.write("Use yt-dlp or manual download for each episode:\n\n")
                for ep in video_info['episodes']:
                    filename = f"{ep['number']:02d}.mp4"
                    f.write(f"Episode {ep['number']:02d}: {ep['title']}\n")
                    f.write(f"  URL: {ep['url']}\n")
                    f.write(f"  Output: {filename}\n")
                    f.write(f"  Command: yt-dlp -o '{filename}' '{ep['url']}'\n\n")
            success(f"📋 Download instructions saved: {instructions_file}")
        except Exception as e:
            error(f"❌ Error saving download instructions: {e}")

    def _save_metadata(self, video_info, output_folder):
        try:
            info_file = output_folder / "info.txt"
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"Title: {video_info['title']}\n\n")
                f.write("Description:\n")
                f.write(f"{video_info['description']}\n\n")
                f.write(f"Total Episodes: {video_info['total_episodes']}\n")
                f.write(f"Source: {video_info['detail_url']}\n")
                f.write(f"Series ID: {video_info['id']}\n")
            success(f"📄 Info saved: {info_file}")
            metadata_file = output_folder / "metadata.json"
            metadata = {
                'source': 'aliside.com',
                'series_id': video_info['id'],
                'title': video_info['title'],
                'description': video_info['description'],
                'thumbnail': video_info['thumbnail'],
                'total_episodes': video_info['total_episodes'],
                'detail_url': video_info['detail_url'],
                'episodes': video_info['episodes'],
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            success(f"💾 Metadata JSON saved: {metadata_file}")
        except Exception as e:
            error(f"❌ Error saving metadata: {e}")

    def _download_thumbnail(self, thumbnail_url, output_folder):
        try:
            response = requests.get(thumbnail_url, timeout=10)
            response.raise_for_status()
            thumbnail_file = output_folder / "thumbnail.jpg"
            with open(thumbnail_file, 'wb') as f:
                f.write(response.content)
            success(f"🖼️ Thumbnail downloaded: {thumbnail_file}")
        except Exception as e:
            error(f"❌ Error downloading thumbnail: {e}")

    def close(self):
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except Exception:
                pass

    def __del__(self):
        self.close()
