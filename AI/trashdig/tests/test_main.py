import os
from unittest.mock import MagicMock, patch

from trashdig.config import Config
from trashdig.main import main


@patch("trashdig.main.TrashDigApp")
@patch("trashdig.main.load_config")
@patch("sys.stdout.isatty", return_value=True)
def test_main_default_root(mock_isatty, mock_load_config, mock_app_class, tmp_path):
    mock_config = MagicMock()
    mock_config.workspace_root = os.path.abspath(".")
    mock_config.data_dir = str(tmp_path / ".trashdig")
    mock_load_config.return_value = mock_config
    mock_app_class.return_value = MagicMock()

    with patch("sys.argv", ["trashdig"]):
        main()

    mock_load_config.assert_called_once()
    mock_app_class.assert_called_once_with(
        config=mock_config,
        workspace_root=mock_config.workspace_root,
    )
    mock_app_class.return_value.run.assert_called_once()


@patch("trashdig.main.TrashDigApp")
@patch("trashdig.main.load_config")
@patch("sys.stdout.isatty", return_value=True)
def test_main_explicit_root(mock_isatty, mock_load_config, mock_app_class, tmp_path):
    mock_config = MagicMock()
    mock_config.workspace_root = str(tmp_path)
    mock_config.data_dir = str(tmp_path / ".trashdig")
    mock_load_config.return_value = mock_config
    mock_app_class.return_value = MagicMock()

    with patch("sys.argv", ["trashdig", str(tmp_path)]):
        main()

    mock_app_class.assert_called_once_with(
        config=mock_config,
        workspace_root=mock_config.workspace_root,
    )


@patch("trashdig.main.load_config")
@patch("trashdig.main.TrashDigApp")
def test_main_dump_config(mock_app_class, mock_load_config, capsys):
    mock_config = Config(rpm_limit=10)
    mock_load_config.return_value = mock_config

    with patch("sys.argv", ["trashdig", "--dump-config"]):
        try:
            main()
        except SystemExit:
            pass

    out, _ = capsys.readouterr()
    assert 'rpm_limit = 10' in out
    mock_app_class.assert_not_called()


@patch("trashdig.main.load_config")
@patch("trashdig.main.init_artifact_manager")
@patch("trashdig.main.Coordinator")
@patch("asyncio.run")
def test_main_batch_mode(mock_asyncio_run, mock_coordinator_class, mock_init_art, mock_load_config, tmp_path):
    mock_config = MagicMock()
    mock_config.rpm_limit = 10
    mock_config.tpm_limit = 1000
    mock_config.data_dir = str(tmp_path / ".trashdig")
    mock_load_config.return_value = mock_config
    mock_init_art.return_value = MagicMock()

    mock_coord = MagicMock()
    mock_coordinator_class.return_value = mock_coord
    mock_coord.findings = []
    mock_coord.total_cost = 0.0

    with patch("sys.argv", ["trashdig", "--batch", str(tmp_path)]):
        with patch("sys.stdout.isatty", return_value=True):
            main()

    mock_coordinator_class.assert_called_once()
    mock_asyncio_run.assert_called_once()


def test_main_invalid_dir(capsys):
    with patch("sys.argv", ["trashdig", "/no/such/path"]):
        try:
            main()
            assert False, "expected SystemExit"
        except SystemExit as e:
            assert e.code != 0
