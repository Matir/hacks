import sys
from unittest.mock import MagicMock, patch

import pytest

from podscribe.__main__ import main
from podscribe.config import Config


@patch("podscribe.__main__.Orchestrator")
@patch("podscribe.__main__.Config")
@patch("podscribe.__main__.setup_logging")
@patch("podscribe.__main__.load_dotenv")
def test_main_arguments(mock_load_dotenv, mock_setup_logging, mock_config_class, mock_orchestrator_class, tmp_path):
    # Setup mock config
    mock_config = MagicMock(spec=Config)
    mock_config.output_dir = str(tmp_path / "output")
    mock_config.data = {"transcriber": {}}
    mock_config_class.return_value = mock_config

    # Setup orchestrator mock
    mock_orchestrator = MagicMock()
    mock_orchestrator_class.return_value = mock_orchestrator

    # Call main with custom language CLI argument
    test_args = ["podscribe", "--config", "my_config.toml", "--language", "es", "--stage", "transcribe"]
    with patch.object(sys, "argv", test_args):
        main()

    # Verify Config was instantiated with the correct config path
    mock_config_class.assert_called_once_with("my_config.toml")

    # Verify that language was set on config.data
    assert mock_config.data["transcriber"]["language"] == "es"

    # Verify Orchestrator was called with stage and the overridden config
    mock_orchestrator_class.assert_called_once_with(mock_config, stage="transcribe")
    mock_orchestrator.run.assert_called_once()

@patch("podscribe.__main__.Config")
@patch("podscribe.__main__.load_dotenv")
@patch("builtins.print")
def test_main_dump_config(mock_print, mock_load_dotenv, mock_config_class):
    mock_config = MagicMock(spec=Config)
    mock_config.dump.return_value = "DUMMY DUMPED CONFIGURATION"
    mock_config_class.return_value = mock_config

    test_args = ["podscribe", "--config", "my_config.toml", "--dump-config"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()

    # Verify program exited with 0
    assert excinfo.value.code == 0

    # Verify config.dump() was called
    mock_config.dump.assert_called_once()

    # Verify print was called with the dump output
    mock_print.assert_called_once_with("DUMMY DUMPED CONFIGURATION")

@patch("podscribe.__main__.Orchestrator")
@patch("podscribe.__main__.Config")
@patch("podscribe.__main__.setup_logging")
@patch("podscribe.__main__.load_dotenv")
def test_main_log_level_case_insensitive(mock_load_dotenv, mock_setup_logging, mock_config_class, mock_orchestrator_class, tmp_path):
    from pathlib import Path
    mock_config = MagicMock(spec=Config)
    mock_config.output_dir = str(tmp_path / "output")
    mock_config.data = {"transcriber": {}}
    mock_config_class.return_value = mock_config

    mock_orchestrator = MagicMock()
    mock_orchestrator_class.return_value = mock_orchestrator

    # Call main with lowercase log level
    test_args = ["podscribe", "--log-level", "debug"]
    with patch.object(sys, "argv", test_args):
        main()

    # Verify setup_logging was called with uppercase "DEBUG"
    mock_setup_logging.assert_called_once_with(
        Path(mock_config.output_dir), log_level_str="DEBUG", log_file=None, alsologtostderr=False
    )

@patch("podscribe.__main__.RSSFetcher")
@patch("podscribe.__main__.setup_logging")
@patch("podscribe.__main__.Config")
@patch("podscribe.__main__.load_dotenv")
def test_main_rss_download_only_success(mock_load_dotenv, mock_config_class, mock_setup_logging, mock_fetcher_class, tmp_path):
    mock_config = MagicMock(spec=Config)
    mock_config.output_dir = str(tmp_path / "output")
    mock_config.input_dir = str(tmp_path / "input")
    mock_config.rss_feeds = [{"url": "https://example.com/feed.xml"}]
    mock_config_class.return_value = mock_config

    mock_fetcher = MagicMock()
    mock_fetcher.sync_feeds.return_value = [tmp_path / "input/ep1.mp3"]
    mock_fetcher_class.return_value = mock_fetcher

    test_args = ["podscribe", "--rss-download-only"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 0
    mock_fetcher.sync_feeds.assert_called_once_with(mock_config.rss_feeds, raise_on_error=True)

@patch("podscribe.__main__.setup_logging")
@patch("podscribe.__main__.Config")
@patch("podscribe.__main__.load_dotenv")
def test_main_rss_download_only_no_feeds(mock_load_dotenv, mock_config_class, mock_setup_logging, tmp_path):
    mock_config = MagicMock(spec=Config)
    mock_config.output_dir = str(tmp_path / "output")
    mock_config.rss_feeds = []
    mock_config_class.return_value = mock_config

    test_args = ["podscribe", "--rss-download-only"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1

@patch("podscribe.__main__.RSSFetcher")
@patch("podscribe.__main__.setup_logging")
@patch("podscribe.__main__.Config")
@patch("podscribe.__main__.load_dotenv")
def test_main_rss_download_only_error(mock_load_dotenv, mock_config_class, mock_setup_logging, mock_fetcher_class, tmp_path):
    mock_config = MagicMock(spec=Config)
    mock_config.output_dir = str(tmp_path / "output")
    mock_config.input_dir = str(tmp_path / "input")
    mock_config.rss_feeds = [{"url": "https://example.com/feed.xml"}]
    mock_config_class.return_value = mock_config

    mock_fetcher = MagicMock()
    mock_fetcher.sync_feeds.side_effect = Exception("Network Error")
    mock_fetcher_class.return_value = mock_fetcher

    test_args = ["podscribe", "--rss-download-only"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1

@patch("podscribe.__main__.setup_logging")
@patch("podscribe.__main__.Config")
@patch("podscribe.__main__.load_dotenv")
def test_main_missing_auth_token(mock_load_dotenv, mock_config_class, mock_setup_logging, tmp_path, monkeypatch):
    mock_config = MagicMock(spec=Config)
    mock_config.output_dir = str(tmp_path / "output")
    mock_config.get_required_auth_env_vars.return_value = [("REQUIRED_SECRET_KEY", "test purpose")]
    mock_config_class.return_value = mock_config

    monkeypatch.delenv("REQUIRED_SECRET_KEY", raising=False)

    test_args = ["podscribe", "--stage", "all"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()

    assert excinfo.value.code == 1

def test_setup_logging_no_file(tmp_path):
    import logging

    from podscribe.__main__ import setup_logging
    root = logging.getLogger()
    setup_logging(tmp_path, log_file=None, alsologtostderr=True)
    # When no file is configured, logs to stdout only (alsologtostderr is a no-op)
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0], logging.StreamHandler)
    assert root.handlers[0].stream == sys.stdout

def test_setup_logging_with_file_no_stderr(tmp_path):
    import logging

    from podscribe.__main__ import setup_logging
    log_file = tmp_path / "custom.log"
    root = logging.getLogger()
    setup_logging(tmp_path, log_file=log_file, alsologtostderr=False)
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0], logging.FileHandler)

def test_setup_logging_with_file_and_stderr(tmp_path):
    import logging

    from podscribe.__main__ import setup_logging
    log_file = tmp_path / "custom.log"
    root = logging.getLogger()
    setup_logging(tmp_path, log_file=log_file, alsologtostderr=True)
    assert len(root.handlers) == 2
    types = {type(h) for h in root.handlers}
    assert logging.FileHandler in types
    assert logging.StreamHandler in types
