import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import httpx
from podscribe.rss_fetcher import RSSFetcher

# Configure logging for tests to see the outputs if needed
logging.basicConfig(level=logging.INFO)

def test_sanitize_filename():
    fetcher = RSSFetcher(Path("dummy_dir"))
    assert fetcher._sanitize_filename("Episode 1: Hello World!") == "Episode_1_Hello_World"
    assert fetcher._sanitize_filename("What's Up?") == "Whats_Up"
    # Trim length
    long_title = "a" * 300
    assert len(fetcher._sanitize_filename(long_title)) == 200

def test_filename_from_url():
    fetcher = RSSFetcher(Path("dummy_dir"))
    assert fetcher._filename_from_url("https://example.com/audio/ep1.mp3") == "ep1.mp3"
    assert fetcher._filename_from_url("https://example.com/audio/ep1.mp3?query=123") == "ep1.mp3"
    assert fetcher._filename_from_url("https://example.com/audio/no_extension") is None
    assert fetcher._filename_from_url("https://example.com/audio/image.jpg") is None

def test_cleanup_temp_files_on_init(tmp_path):
    # Create some leftover temp files and some good files
    good_file = tmp_path / "episode1.mp3"
    good_file.write_text("good")
    
    temp_file1 = tmp_path / "episode1.mp3.download.tmp"
    temp_file1.write_text("partial")
    
    temp_file2 = tmp_path / "other.wav.download.tmp"
    temp_file2.write_text("partial2")
    
    # Initialize fetcher. It should automatically clean them up.
    fetcher = RSSFetcher(tmp_path)
    
    assert good_file.exists()
    assert not temp_file1.exists()
    assert not temp_file2.exists()

def test_fetch_episodes_success():
    feed_url = "https://example.com/podcast.xml"
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
      <channel>
        <title>Test Podcast</title>
        <item>
          <title>Episode 1: Standard Enclosure</title>
          <enclosure url="https://example.com/ep1.mp3" type="audio/mpeg" />
        </item>
        <item>
          <title>Episode 2: Media Content</title>
          <media:content url="https://example.com/ep2.m4a" />
        </item>
        <item>
          <title>Episode 3: No Audio</title>
          <enclosure url="https://example.com/ep3.png" type="image/png" />
        </item>
      </channel>
    </rss>
    """
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.text = mock_xml
        mock_client.get.return_value = mock_response
        
        fetcher = RSSFetcher(Path("dummy_dir"))
        episodes = fetcher.fetch_episodes(feed_url)
        
        assert len(episodes) == 2
        assert episodes[0]["title"] == "Episode 1: Standard Enclosure"
        assert episodes[0]["url"] == "https://example.com/ep1.mp3"
        assert episodes[0]["filename"] == "ep1.mp3"
        
        assert episodes[1]["title"] == "Episode 2: Media Content"
        assert episodes[1]["url"] == "https://example.com/ep2.m4a"
        assert episodes[1]["filename"] == "ep2.m4a"

def test_download_missing_success(tmp_path):
    episodes = [
        {"title": "Episode 1", "url": "https://example.com/ep1.mp3", "filename": "ep1.mp3"}
    ]
    
    # Mock httpx stream
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_stream = MagicMock()
        mock_client.stream.return_value = mock_stream
        mock_response = mock_stream.__enter__.return_value
        mock_response.iter_bytes.return_value = [b"bytechunk1", b"bytechunk2"]
        
        fetcher = RSSFetcher(tmp_path)
        downloaded = fetcher.download_missing(episodes)
        
        dest_file = tmp_path / "ep1.mp3"
        assert len(downloaded) == 1
        assert downloaded[0] == dest_file
        assert dest_file.exists()
        assert dest_file.read_bytes() == b"bytechunk1bytechunk2"
        
        # Temp file should be cleaned up (it was renamed, so it shouldn't exist)
        temp_file = tmp_path / "ep1.mp3.download.tmp"
        assert not temp_file.exists()

def test_download_missing_already_exists(tmp_path):
    # Create existing file
    dest_file = tmp_path / "ep1.mp3"
    dest_file.write_text("already here")
    
    episodes = [
        {"title": "Episode 1", "url": "https://example.com/ep1.mp3", "filename": "ep1.mp3"}
    ]
    
    with patch("httpx.Client") as mock_client_class:
        fetcher = RSSFetcher(tmp_path)
        downloaded = fetcher.download_missing(episodes)
        
        # Should skip download
        assert len(downloaded) == 0
        mock_client_class.assert_not_called()
        assert dest_file.read_text() == "already here"

def test_download_missing_failure_cleanup(tmp_path):
    episodes = [
        {"title": "Episode 1", "url": "https://example.com/ep1.mp3", "filename": "ep1.mp3"}
    ]
    
    # Mock httpx stream to raise error mid-download
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_stream = MagicMock()
        mock_client.stream.return_value = mock_stream
        mock_response = mock_stream.__enter__.return_value
        
        # Simulate network failure during iteration
        def raise_network_error(*args, **kwargs):
            yield b"some_bytes"
            raise httpx.ReadTimeout("Timeout!")
            
        mock_response.iter_bytes.side_effect = raise_network_error
        
        fetcher = RSSFetcher(tmp_path)
        downloaded = fetcher.download_missing(episodes)
        
        # Should return empty downloaded list
        assert len(downloaded) == 0
        
        # Final file should not exist
        dest_file = tmp_path / "ep1.mp3"
        assert not dest_file.exists()
        
        # Temp file should have been cleaned up by the finally block
        temp_file = tmp_path / "ep1.mp3.download.tmp"
        assert not temp_file.exists()

def test_fetch_episodes_empty_title():
    feed_url = "https://example.com/podcast.xml"
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <!-- Missing Title -->
          <!-- Enclosure URL has no extension to force title fallback -->
          <enclosure url="https://example.com/ep1-no-ext" type="audio/mpeg" />
        </item>
      </channel>
    </rss>
    """
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.text = mock_xml
        mock_client.get.return_value = mock_response
        
        fetcher = RSSFetcher(Path("dummy_dir"))
        episodes = fetcher.fetch_episodes(feed_url)
        
        assert len(episodes) == 1
        assert episodes[0]["title"] == ""
        assert episodes[0]["filename"] == "episode.mp3" # Fallback title used

def test_sync_feeds_success(tmp_path):
    feeds = [
        {"url": "https://example.com/feed.xml", "max_episodes": 1}
    ]
    
    # Mock fetch_episodes and download_missing
    with patch.object(RSSFetcher, "fetch_episodes") as mock_fetch, \
         patch.object(RSSFetcher, "download_missing") as mock_download:
         
        mock_fetch.return_value = [{"title": "Ep1", "url": "http://ep1", "filename": "ep1.mp3"}]
        mock_download.return_value = [tmp_path / "ep1.mp3"]
        
        fetcher = RSSFetcher(tmp_path)
        result = fetcher.sync_feeds(feeds)
        
        assert len(result) == 1
        assert result[0] == tmp_path / "ep1.mp3"
        mock_fetch.assert_called_once_with("https://example.com/feed.xml", max_episodes=1)
        mock_download.assert_called_once()

def test_sync_feeds_missing_url(tmp_path):
    feeds = [
        {"max_episodes": 5} # Missing URL
    ]
    
    with patch.object(RSSFetcher, "fetch_episodes") as mock_fetch:
        fetcher = RSSFetcher(tmp_path)
        result = fetcher.sync_feeds(feeds)
        assert len(result) == 0
        mock_fetch.assert_not_called()

def test_sync_feeds_error_handling(tmp_path):
    feeds = [
        {"url": "https://example.com/feed.xml"}
    ]
    
    with patch.object(RSSFetcher, "fetch_episodes") as mock_fetch:
        # Simulate XML parse error
        mock_fetch.side_effect = Exception("Parse Error")
        
        fetcher = RSSFetcher(tmp_path)
        # Should handle exception and return empty list (not crash)
        result = fetcher.sync_feeds(feeds)
        assert len(result) == 0

def test_download_missing_cleanup_failure_log(tmp_path):
    episodes = [
        {"title": "Episode 1", "url": "https://example.com/ep1.mp3", "filename": "ep1.mp3"}
    ]
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_stream = MagicMock()
        mock_client.stream.return_value = mock_stream
        mock_response = mock_stream.__enter__.return_value
        mock_response.iter_bytes.side_effect = Exception("Download Error")
        
        fetcher = RSSFetcher(tmp_path)
        
        # Mock Path.unlink to fail during cleanup of temp file
        with patch.object(Path, "unlink") as mock_unlink:
            mock_unlink.side_effect = Exception("Permission Denied")
            
            # This should run without crashing, logging the cleanup error.
            # temp_dest is created by open(), so it will exist and trigger unlink.
            downloaded = fetcher.download_missing(episodes)
            assert len(downloaded) == 0
            # Verify unlink was attempted
            mock_unlink.assert_called_once()

def test_cleanup_temp_files_failure(tmp_path):
    # Create a temp file to trigger cleanup
    temp_file = tmp_path / "episode.mp3.download.tmp"
    temp_file.write_text("partial")
    
    # Mock Path.unlink to fail
    with patch.object(Path, "unlink") as mock_unlink:
        mock_unlink.side_effect = Exception("Cannot delete")
        # This should complete without raising error
        fetcher = RSSFetcher(tmp_path)
        mock_unlink.assert_called_once()

def test_fetch_episodes_no_channel():
    # Feed without channel tag
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <not_channel>
        <item>
          <title>Episode</title>
        </item>
      </not_channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.text = mock_xml
        mock_client.get.return_value = mock_response
        
        fetcher = RSSFetcher(Path("dummy"))
        result = fetcher.fetch_episodes(feed_url)
        assert result == []

def test_fetch_episodes_max_episodes_limit():
    # Feed with 3 items
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>Ep 1</title>
          <enclosure url="https://example.com/ep1.mp3" type="audio/mpeg" />
        </item>
        <item>
          <title>Ep 2</title>
          <enclosure url="https://example.com/ep2.mp3" type="audio/mpeg" />
        </item>
        <item>
          <title>Ep 3</title>
          <enclosure url="https://example.com/ep3.mp3" type="audio/mpeg" />
        </item>
      </channel>
    </rss>
    """
    feed_url = "https://example.com/feed.xml"
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.text = mock_xml
        mock_client.get.return_value = mock_response
        
        fetcher = RSSFetcher(Path("dummy"))
        # Call with max_episodes=2
        result = fetcher.fetch_episodes(feed_url, max_episodes=2)
        assert len(result) == 2
        assert result[0]["title"] == "Ep 1"
        assert result[1]["title"] == "Ep 2"
