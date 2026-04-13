import asyncio
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Optional

import httpx


class SourceFetcherError(Exception):
    """Raised when source retrieval fails."""
    pass


class SourceFetcher:
    """Retrieves source code for analysis.

    Supports: Public Git shallow clones, Direct download URLs, and File uploads.
    Enforces a 100MB cap for URL and File retrievals.
    """

    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

    def __init__(self, workspace_dir: str) -> None:
        self.source_dir = Path(workspace_dir) / "source"

    async def fetch_git(self, repo_url: str) -> None:
        """
        Shallow clones a public git repository.
        
        :param repo_url: URL to the repository.
        """
        self.source_dir.mkdir(parents=True, exist_ok=True)
        # git clone --depth=1 <url> <dest>
        process = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth=1", repo_url, str(self.source_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise SourceFetcherError(f"Git clone failed: {stderr.decode()}")

    async def fetch_url(self, download_url: str) -> None:
        """
        Downloads and extracts a source archive.
        
        :param download_url: URL to the zip or tar archive.
        """
        self.source_dir.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                # Streaming download to enforce size cap
                async with client.stream("GET", download_url) as response:
                    response.raise_for_status()
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.MAX_FILE_SIZE:
                        raise SourceFetcherError(f"Download size exceeds 100MB cap ({content_length} bytes)")

                    archive_path = self.source_dir.parent / "source_archive"
                    downloaded_size = 0
                    with archive_path.open("wb") as f:
                        async for chunk in response.aiter_bytes():
                            downloaded_size += len(chunk)
                            if downloaded_size > self.MAX_FILE_SIZE:
                                raise SourceFetcherError("Download size exceeds 100MB cap during streaming")
                            f.write(chunk)
                
                self._extract_archive(archive_path)
            except Exception as e:
                raise SourceFetcherError(f"Download or extraction failed: {e}")
            finally:
                if archive_path.exists():
                    archive_path.unlink()

    def fetch_local(self, local_path: str) -> None:
        """
        Copies and/or extracts a local source file/directory.
        
        :param local_path: Path to the local source.
        """
        self.source_dir.mkdir(parents=True, exist_ok=True)
        path = Path(local_path)
        if not path.exists():
            raise SourceFetcherError(f"Local path does not exist: {local_path}")

        if path.is_dir():
            # Copy directory (respecting cap roughly by checking size first)
            total_size = sum(f.stat().st_size for f in path.glob("**/*") if f.is_file())
            if total_size > self.MAX_FILE_SIZE:
                raise SourceFetcherError(f"Source directory size {total_size} exceeds 100MB cap")
            shutil.copytree(path, self.source_dir, dirs_exist_ok=True)
        else:
            if path.stat().st_size > self.MAX_FILE_SIZE:
                raise SourceFetcherError(f"Source file size {path.stat().st_size} exceeds 100MB cap")
            self._extract_archive(path)

    def _extract_archive(self, archive_path: Path) -> None:
        """Extracts zip or tar archives into source_dir."""
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(self.source_dir)
        elif tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, "r:*") as tar_ref:
                tar_ref.extractall(self.source_dir)
        else:
            raise SourceFetcherError(f"Unsupported archive format for {archive_path.name}")
