import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from trashdig.scripts.seed_vulndb import seed_vuln


@pytest.mark.anyio
@patch("trashdig.scripts.seed_vulndb.run_agent")
@patch("trashdig.scripts.seed_vulndb.load_prompt")
async def test_seed_vuln_success(mock_load_prompt, mock_run_agent, tmp_path):
    mock_load_prompt.return_value = "Prompt for {cwe_id}"
    mock_run_agent.return_value = """{
  "id": "CWE-123",
  "title": "Test CWE",
  "category": "Test",
  "severity": "high",
  "tags": ["test"]
}---CONTENT---# Markdown Content"""

    agent = MagicMock()
    session_service = MagicMock()
    semaphore = asyncio.Semaphore(1)
    file_lock = asyncio.Lock()

    await seed_vuln(agent, "CWE-123", session_service, str(tmp_path), semaphore, file_lock)

    # Check if files were created
    content_file = tmp_path / "content" / "cwe_123.md"
    assert content_file.exists()
    assert content_file.read_text() == "# Markdown Content"

    metadata_file = tmp_path / "metadata.json"
    assert metadata_file.exists()
    with open(metadata_file) as f:
        meta = json.load(f)
    assert len(meta) == 1
    assert meta[0]["id"] == "CWE-123"


@pytest.mark.anyio
@patch("trashdig.scripts.seed_vulndb.run_agent")
@patch("trashdig.scripts.seed_vulndb.load_prompt")
async def test_seed_vuln_missing_separator(mock_load_prompt, mock_run_agent, tmp_path):
    mock_load_prompt.return_value = "Prompt for {cwe_id}"
    mock_run_agent.return_value = "No separator here"

    agent = MagicMock()
    session_service = MagicMock()
    semaphore = asyncio.Semaphore(1)
    file_lock = asyncio.Lock()

    await seed_vuln(agent, "CWE-123", session_service, str(tmp_path), semaphore, file_lock)

    # No files should be created
    assert not (tmp_path / "metadata.json").exists()


@pytest.mark.anyio
@patch("trashdig.scripts.seed_vulndb.run_agent")
@patch("trashdig.scripts.seed_vulndb.load_prompt")
async def test_seed_vuln_bad_json(mock_load_prompt, mock_run_agent, tmp_path):
    mock_load_prompt.return_value = "Prompt for {cwe_id}"
    mock_run_agent.return_value = "Bad JSON---CONTENT---# Markdown Content"

    agent = MagicMock()
    session_service = MagicMock()
    semaphore = asyncio.Semaphore(1)
    file_lock = asyncio.Lock()

    await seed_vuln(agent, "CWE-123", session_service, str(tmp_path), semaphore, file_lock)

    # No files should be created
    assert not (tmp_path / "metadata.json").exists()
