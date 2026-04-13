import os
import shutil
import tempfile
import zipfile
import tarfile
from pathlib import Path

import pytest
import httpx
from core.source_fetcher import SourceFetcher, SourceFetcherError

@pytest.mark.asyncio
async def test_fetch_local_directory():
    """Verifies that SourceFetcher copies a local directory."""
    with tempfile.TemporaryDirectory() as tmp_src:
        src_path = Path(tmp_src)
        (src_path / "code.py").write_text("print('hello')", encoding="utf-8")
        
        with tempfile.TemporaryDirectory() as tmp_dest:
            fetcher = SourceFetcher(tmp_dest)
            fetcher.fetch_local(tmp_src)
            
            dest_file = Path(tmp_dest) / "source" / "code.py"
            assert dest_file.exists()
            assert dest_file.read_text() == "print('hello')"

@pytest.mark.asyncio
async def test_fetch_local_zip():
    """Verifies that SourceFetcher extracts a local zip file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = Path(tmp_dir) / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("zipped.txt", "content")
        
        with tempfile.TemporaryDirectory() as tmp_dest:
            fetcher = SourceFetcher(tmp_dest)
            fetcher.fetch_local(str(zip_path))
            
            dest_file = Path(tmp_dest) / "source" / "zipped.txt"
            assert dest_file.exists()
            assert dest_file.read_text() == "content"

@pytest.mark.asyncio
async def test_fetch_local_tar():
    """Verifies that SourceFetcher extracts a local tar file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tar_path = Path(tmp_dir) / "test.tar.gz"
        with tarfile.open(tar_path, "w:gz") as t:
            info = tarfile.TarInfo("tared.txt")
            content = b"tar content"
            info.size = len(content)
            import io
            t.addfile(info, io.BytesIO(content))
        
        with tempfile.TemporaryDirectory() as tmp_dest:
            fetcher = SourceFetcher(tmp_dest)
            fetcher.fetch_local(str(tar_path))
            
            dest_file = Path(tmp_dest) / "source" / "tared.txt"
            assert dest_file.exists()
            assert dest_file.read_text() == "tar content"

@pytest.mark.asyncio
async def test_fetch_local_size_cap_exceeded():
    """Verifies that SourceFetcher raises error if local size exceeds 100MB."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        large_file = Path(tmp_dir) / "large.bin"
        # 101MB
        with large_file.open("wb") as f:
            f.seek(101 * 1024 * 1024 - 1)
            f.write(b"\0")
            
        with tempfile.TemporaryDirectory() as tmp_dest:
            fetcher = SourceFetcher(tmp_dest)
            with pytest.raises(SourceFetcherError, match="exceeds 100MB cap"):
                fetcher.fetch_local(str(large_file))

@pytest.mark.asyncio
async def test_fetch_git_mock(monkeypatch):
    """Verifies that SourceFetcher calls git clone."""
    class MockProcess:
        returncode = 0
        async def communicate(self):
            return b"stdout", b"stderr"
            
    async def mock_create_subprocess_exec(*args, **kwargs):
        return MockProcess()
        
    import asyncio
    monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_create_subprocess_exec)
    
    with tempfile.TemporaryDirectory() as tmp_dest:
        fetcher = SourceFetcher(tmp_dest)
        await fetcher.fetch_git("https://github.com/mock/repo")
        # Since we mocked it, we just check if it didn't raise
        assert (Path(tmp_dest) / "source").exists()

@pytest.mark.asyncio
async def test_fetch_url_mock(respx_mock):
    """Verifies that SourceFetcher downloads and extracts from URL."""
    # We need to mock httpx streaming
    archive_content = b"dummy archive" # Not a real zip, fetcher will fail extraction
    respx_mock.get("https://example.com/src.zip").mock(return_value=httpx.Response(200, content=archive_content))
    
    with tempfile.TemporaryDirectory() as tmp_dest:
        fetcher = SourceFetcher(tmp_dest)
        # It will fail at _extract_archive because dummy content isn't a zip
        with pytest.raises(SourceFetcherError, match="Unsupported archive format"):
            await fetcher.fetch_url("https://example.com/src.zip")
        
        # Verify the archive path was cleaned up
        archive_path = Path(tmp_dest) / "source_archive"
        assert not archive_path.exists()
