import sys
from unittest.mock import patch, MagicMock
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
