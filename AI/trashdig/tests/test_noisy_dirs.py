from unittest.mock import patch

from trashdig.agents.utils.helpers import get_project_structure
from trashdig.config import DEFAULT_NOISY_DIRS, Config


def test_noisy_dirs_defaults():
    cfg = Config(config_path="nonexistent.toml")
    assert cfg.noisy_dirs == DEFAULT_NOISY_DIRS


def test_noisy_dirs_add():
    cfg = Config(config_path="nonexistent.toml")
    cfg.data = {"recon": {"add_noisy_dirs": ["custom_noise"]}}
    assert "custom_noise" in cfg.noisy_dirs
    assert ".git" in cfg.noisy_dirs


def test_noisy_dirs_remove():
    cfg = Config(config_path="nonexistent.toml")
    cfg.data = {"recon": {"remove_noisy_dirs": ["tests"]}}
    assert "tests" not in cfg.noisy_dirs
    assert ".git" in cfg.noisy_dirs


def test_get_project_structure_respects_config(tmp_path):
    # Setup temp project
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("test")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("main")
    (tmp_path / "custom_ignored").mkdir()
    (tmp_path / "custom_ignored" / "ignore.me").write_text("ignore")

    # Mock config to remove 'tests' from noisy_dirs and add 'custom_ignored'
    with patch("trashdig.agents.utils.helpers.get_config") as mock_get_config:
        mock_cfg = patch("trashdig.config.Config").start()
        mock_cfg.workspace_root = str(tmp_path)
        mock_cfg.noisy_dirs = {
            ".git",
            "node_modules",
            "dist",
            "vendor",
            "__pycache__",
            ".venv",
            "findings",
            "custom_ignored",
        }
        mock_get_config.return_value = mock_cfg

        files = get_project_structure(str(tmp_path))

        # 'tests/test_main.py' should be INCLUDED because we removed 'tests' from noisy_dirs
        assert "tests/test_main.py" in files
        # 'custom_ignored/ignore.me' should be EXCLUDED
        assert "custom_ignored/ignore.me" not in files
        # 'src/main.py' should be INCLUDED
        assert "src/main.py" in files

