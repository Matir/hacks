import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}
MEDIA_NS = "http://search.yahoo.com/mrss/"


class RSSFetcher:
    def __init__(self, input_dir: Path):
        self.input_dir = input_dir
        self._cleanup_temp_files()

    def _cleanup_temp_files(self):
        """Scan input_dir for any leftover .download.tmp files and remove them."""
        if not self.input_dir.exists():
            return
        
        logger.info(f"Checking for leftover temporary files in {self.input_dir}...")
        for temp_file in self.input_dir.glob("*.download.tmp"):
            try:
                logger.info(f"Removing leftover temporary file: {temp_file.name}")
                temp_file.unlink()
            except Exception as e:
                logger.error(f"Failed to remove leftover temporary file {temp_file}: {e}")

    def _sanitize_filename(self, name: str) -> str:
        name = re.sub(r"[^\w\s.-]", "", name)
        name = re.sub(r"\s+", "_", name.strip())
        return name[:200]

    def _filename_from_url(self, url: str) -> str | None:
        path = Path(urlparse(url).path)
        if path.suffix.lower() in AUDIO_EXTENSIONS:
            return path.name
        return None

    def fetch_episodes(self, feed_url: str, max_episodes: int | None = None) -> list[dict]:
        """Parse an RSS feed and return a list of episode dicts (title, url, filename)."""
        logger.info(f"Fetching RSS feed: {feed_url}")
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            response = client.get(feed_url, headers={"User-Agent": "transcriber-rss/1.0"})
            response.raise_for_status()

        root = ET.fromstring(response.text)
        channel = root.find("channel")
        if channel is None:
            logger.warning("No <channel> element found in RSS feed")
            return []

        episodes = []
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            media_url = self._extract_media_url(item)
            if not media_url:
                continue

            filename = self._filename_from_url(media_url)
            if not filename:
                safe_title = self._sanitize_filename(title) if title else "episode"
                filename = f"{safe_title}.mp3"

            episodes.append({"title": title, "url": media_url, "filename": filename})
            if max_episodes is not None and len(episodes) >= max_episodes:
                break

        logger.info(f"Found {len(episodes)} episodes in feed")
        return episodes

    def _extract_media_url(self, item: ET.Element) -> str | None:
        enclosure = item.find("enclosure")
        if enclosure is not None:
            enc_type = enclosure.get("type", "")
            enc_url = enclosure.get("url", "")
            if enc_url and (enc_type.startswith("audio/") or enc_type.startswith("video/")):
                return enc_url

        media_content = item.find(f"{{{MEDIA_NS}}}content")
        if media_content is not None:
            url = media_content.get("url", "")
            if url and Path(urlparse(url).path).suffix.lower() in AUDIO_EXTENSIONS:
                return url

        return None

    def download_missing(self, episodes: list[dict]) -> list[Path]:
        """Download any episodes not already present in input_dir."""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        downloaded = []

        for episode in episodes:
            dest = self.input_dir / episode["filename"]
            if dest.exists():
                logger.debug(f"Already exists, skipping: {episode['filename']}")
                continue

            temp_dest = dest.with_suffix(dest.suffix + ".download.tmp")
            logger.info(f"Downloading: {episode['title']} -> {episode['filename']} (via temp file)")
            try:
                with httpx.Client(follow_redirects=True, timeout=600) as client:
                    with client.stream("GET", episode["url"]) as response:
                        response.raise_for_status()
                        with open(temp_dest, "wb") as f:
                            for chunk in response.iter_bytes(chunk_size=65536):
                                f.write(chunk)
                
                # Rename to final destination only after successful download
                temp_dest.rename(dest)
                logger.info(f"Downloaded: {episode['filename']}")
                downloaded.append(dest)
            except Exception as e:
                logger.error(f"Failed to download {episode['filename']}: {e}")
            finally:
                if temp_dest.exists():
                    try:
                        logger.info(f"Cleaning up temporary download file: {temp_dest.name}")
                        temp_dest.unlink()
                    except Exception as cleanup_err:
                        logger.error(f"Failed to clean up temp file {temp_dest}: {cleanup_err}")

        return downloaded

    def sync_feeds(self, feeds: list[dict]) -> list[Path]:
        """Fetch all configured feeds and download missing episodes."""
        all_downloaded = []
        for feed in feeds:
            url = feed.get("url", "")
            if not url:
                logger.warning("RSS feed entry missing 'url', skipping")
                continue
            max_episodes = feed.get("max_episodes")
            try:
                episodes = self.fetch_episodes(url, max_episodes=max_episodes)
                downloaded = self.download_missing(episodes)
                all_downloaded.extend(downloaded)
            except Exception as e:
                logger.error(f"Error processing RSS feed {url}: {e}")
        return all_downloaded
