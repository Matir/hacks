from unittest.mock import patch

import pytest

import trashdig.metadata.languages
from trashdig.config import Config


@pytest.fixture(autouse=True)
def clear_language_cache():
    """Clear the tree-sitter language cache before each test.

    Some tests mock _get_ts_language to return a MagicMock, which gets stored
    in the module-level _LANGUAGE_CACHE.  Without clearing it, that stale mock
    leaks into subsequent tests that call _make_parser() directly and then fail
    with TypeError when tree_sitter.Parser receives a MagicMock instead of a
    real Language object.
    """
    trashdig.metadata.languages._LANGUAGE_CACHE.clear()
    yield
    trashdig.metadata.languages._LANGUAGE_CACHE.clear()


@pytest.fixture(autouse=True)
def mock_cfg():
    with patch("trashdig.config.get_config") as mock:
        c = Config()
        c.data["require_sandbox"] = False
        mock.return_value = c
        yield mock

@pytest.fixture
def temp_project(tmp_path):
    # Create a dummy project structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')")
    (tmp_path / "src" / "utils.py").write_text("def util(): pass")
    (tmp_path / "README.md").write_text("# My Project")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test(): pass")
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "app.js").write_text("console.log('web')")
    return tmp_path
