import os
import logging
from unittest.mock import MagicMock, patch
import pytest
from trashdig.agents.utils.helpers import (
    google_provider_extras,
    describe_provider_auth,
    log_auth_info,
    get_project_structure,
    read_file_content,
    detect_frameworks,
    get_response_text,
    load_prompt,
    run_agent
)

def test_google_provider_extras():
    assert google_provider_extras("openai") == {"google_search_tool": None, "generate_content_config": None}
    res = google_provider_extras("google")
    assert res["google_search_tool"] is not None
    assert res["generate_content_config"] is not None

def test_describe_provider_auth_google(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCP_PROJECT", raising=False)
    
    # Mocking os.path.exists for well_known ADC
    with patch("os.path.exists", return_value=False):
        lines = describe_provider_auth("google", None)
        assert any("no explicit source detected" in l for l in lines)

    # Test with API key
    mock_cfg = MagicMock()
    mock_cfg.api_key = "secret"
    lines = describe_provider_auth("google", mock_cfg)
    assert any("API key from config.toml" in l for l in lines)

def test_describe_provider_auth_generic(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    lines = describe_provider_auth("openai", None)
    assert any("no API key found" in l for l in lines)
    
    monkeypatch.setenv("OPENAI_API_KEY", "sk-...")
    lines = describe_provider_auth("openai", None)
    assert any("API key from OPENAI_API_KEY" in l for l in lines)

def test_log_auth_info():
    mock_config = MagicMock()
    mock_agent = MagicMock()
    mock_agent.provider = "google"
    mock_config.agents = {"agent1": mock_agent}
    mock_config.get_provider_config.return_value = None
    
    logger = MagicMock()
    log_auth_info(mock_config, logger)
    assert logger.info.called

def test_get_project_structure(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / ".gitignore").write_text("*.pyc\n.venv/")
    (tmp_path / "main.pyc").write_text("binary")
    (tmp_path / ".venv").mkdir()
    
    files = get_project_structure(str(tmp_path))
    assert "src/main.py" in files
    assert "main.pyc" not in files
    assert ".venv" not in files

def test_read_file_content(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    assert read_file_content(str(f)) == "hello world"
    assert read_file_content(str(f), max_chars=5) == "hello"
    assert "[Error" in read_file_content("nonexistent")

def test_detect_frameworks(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\nsqlalchemy")
    file_list = ["requirements.txt"]
    stack = detect_frameworks(file_list, project_root=str(tmp_path))
    assert "fastapi" in stack["web_frameworks"]
    assert "sqlalchemy" in stack["databases"]

def test_get_response_text():
    resp = MagicMock()
    part1 = MagicMock()
    part1.text = "Hello "
    part2 = MagicMock()
    part2.text = "World"
    resp.content.parts = [part1, part2]
    assert get_response_text(resp) == "Hello World"
    
    assert get_response_text(None) == ""

def test_load_prompt(tmp_path):
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", MagicMock()) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "prompt content"
        content = load_prompt("test.md")
        assert content == "prompt content"

    with patch("os.path.exists", return_value=False):
        with pytest.raises(FileNotFoundError):
            load_prompt("missing.md")

@pytest.mark.anyio
async def test_run_agent():
    from trashdig.agents.utils.helpers import run_agent
    mock_agent = MagicMock()
    mock_agent.name = "test_agent"
    mock_session_service = MagicMock()
    
    # Mock Runner.run_async to yield an event
    mock_event = MagicMock()
    mock_event.content.parts = [MagicMock(text="response")]
    
    async def mock_run_async(*args, **kwargs):
        yield mock_event
        
    with patch("trashdig.agents.utils.helpers.Runner") as mock_runner_cls:
        mock_runner = mock_runner_cls.return_value
        mock_runner.run_async.side_effect = mock_run_async
        
        result = await run_agent(mock_agent, "prompt", "session", mock_session_service)
        assert result == "response"
