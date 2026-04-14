import os
from unittest.mock import patch, MagicMock
from trashdig.main import main


@patch("trashdig.main.TrashDigApp")
@patch("trashdig.main.load_config")
def test_main_default_root(mock_load_config, mock_app_class):
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config
    mock_app_class.return_value = MagicMock()

    with patch("sys.argv", ["trashdig"]):
        main()

    mock_load_config.assert_called_once()
    mock_app_class.assert_called_once_with(
        config=mock_config,
        workspace_root=os.path.abspath("."),
    )
    mock_app_class.return_value.run.assert_called_once()


@patch("trashdig.main.TrashDigApp")
@patch("trashdig.main.load_config")
def test_main_explicit_root(mock_load_config, mock_app_class, tmp_path):
    mock_config = MagicMock()
    mock_load_config.return_value = mock_config
    mock_app_class.return_value = MagicMock()

    with patch("sys.argv", ["trashdig", str(tmp_path)]):
        main()

    mock_app_class.assert_called_once_with(
        config=mock_config,
        workspace_root=str(tmp_path),
    )


@patch("trashdig.main.load_config")
@patch("trashdig.main.TrashDigApp")
def test_main_dump_config(mock_app_class, mock_load_config, capsys):
    from trashdig.config import Config
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


def test_main_invalid_dir(capsys):
    with patch("sys.argv", ["trashdig", "/no/such/path"]):
        try:
            main()
            assert False, "expected SystemExit"
        except SystemExit as e:
            assert e.code != 0
