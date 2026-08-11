from trashdig.tools.base import filter_by_gitignore


def test_filter_by_gitignore_basic(tmp_path):
    (tmp_path / ".gitignore").write_text("*.log\nsecret/\n")
    files = ["src/main.py", "app.log", "secret/key.pem", "README.md"]
    filtered = filter_by_gitignore(files, workspace_root=str(tmp_path))
    assert filtered == ["README.md", "src/main.py"]


def test_filter_by_gitignore_no_gitignore(tmp_path):
    files = ["src/main.py", "README.md"]
    filtered = filter_by_gitignore(files, workspace_root=str(tmp_path))
    assert sorted(filtered) == sorted(files)
