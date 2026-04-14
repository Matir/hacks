import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.agents.utils import get_project_structure, read_file_content, detect_frameworks, run_prompt

def test_get_project_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some files
        os.makedirs(os.path.join(tmpdir, "subdir"))
        with open(os.path.join(tmpdir, "file1.txt"), "w") as f:
            f.write("content1")
        with open(os.path.join(tmpdir, "subdir", "file2.txt"), "w") as f:
            f.write("content2")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write("file1.txt\n")
            
        # Mock noisy dirs to avoid skipping them in tests if they are created
        # But here we don't create them.
        
        structure = get_project_structure(tmpdir)
        
        # .gitignore should be included unless ignored by itself
        assert ".gitignore" in structure
        assert os.path.join("subdir", "file2.txt") in structure
        assert "file1.txt" not in structure

def test_read_file_content():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp.write("Hello, World!")
        tmp_path = tmp.name
        
    try:
        content = read_file_content(tmp_path, max_chars=5)
        assert content == "Hello"
        
        content = read_file_content(tmp_path)
        assert content == "Hello, World!"
    finally:
        os.remove(tmp_path)

def test_read_file_content_error():
    assert read_file_content("non_existent_file.txt") == "[Error: Could not read file content]"

def test_detect_frameworks():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock requirements.txt
        req_path = os.path.join(tmpdir, "requirements.txt")
        with open(req_path, "w") as f:
            f.write("fastapi==0.100.0\nsqlalchemy==2.0.0\n")
            
        file_list = ["requirements.txt"]
        stack = detect_frameworks(file_list, project_root=tmpdir)
        
        assert "fastapi" in stack["web_frameworks"]
        assert "sqlalchemy" in stack["databases"]
        assert "flask" not in stack["web_frameworks"]

def test_detect_frameworks_no_files():
    stack = detect_frameworks([])
    assert all(len(v) == 0 for v in stack.values())


# ---------------------------------------------------------------------------
# run_prompt
# ---------------------------------------------------------------------------

@pytest.mark.anyio
@patch("trashdig.rate_limiter.get_rate_limiter", return_value=None)
async def test_run_prompt_returns_final_text(mock_limiter):
    """run_prompt collects the final response text from the ADK event stream."""
    import google.genai.types as types

    # Build a fake final event
    mock_part = MagicMock()
    mock_part.text = "hello from agent"
    mock_content = MagicMock()
    mock_content.parts = [mock_part]
    mock_event = MagicMock()
    mock_event.is_final_response.return_value = True
    mock_event.content = mock_content
    mock_event.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5)

    async def fake_run_async(**kwargs):
        yield mock_event

    mock_session = MagicMock()
    mock_session.id = "session-1"

    mock_runner = MagicMock()
    mock_runner.run_async = fake_run_async

    mock_agent = MagicMock()
    mock_agent.name = "test-agent"

    with patch("trashdig.agents.utils.Runner", return_value=mock_runner) as _mock_runner_cls, \
         patch("trashdig.agents.utils.InMemorySessionService") as mock_svc_cls:
        mock_svc = AsyncMock()
        mock_svc.create_session = AsyncMock(return_value=mock_session)
        mock_svc_cls.return_value = mock_svc

        result = await run_prompt(mock_agent, "do something")

    assert result["text"] == "hello from agent"
    assert result["input_tokens"] == 10
    assert result["output_tokens"] == 5


@pytest.mark.anyio
@patch("trashdig.rate_limiter.get_rate_limiter", return_value=None)
async def test_run_prompt_no_final_event_returns_empty(mock_limiter):
    """run_prompt returns empty string when no final response event is produced."""
    mock_event = MagicMock()
    mock_event.is_final_response.return_value = False
    mock_event.usage_metadata = None
    mock_event.response = None
    mock_event.raw_response = None
    mock_event.content = None

    async def fake_run_async(**kwargs):
        yield mock_event

    mock_session = MagicMock()
    mock_session.id = "session-1"

    mock_runner = MagicMock()
    mock_runner.run_async = fake_run_async

    mock_agent = MagicMock()
    mock_agent.name = "test-agent"

    with patch("trashdig.agents.utils.Runner", return_value=mock_runner) as _mock_runner_cls, \
         patch("trashdig.agents.utils.InMemorySessionService") as mock_svc_cls:
        mock_svc = AsyncMock()
        mock_svc.create_session = AsyncMock(return_value=mock_session)
        mock_svc_cls.return_value = mock_svc

        result = await run_prompt(mock_agent, "do something")

    assert result["text"] == ""
