from trashdig.tools.read_file import read_file


def test_read_file(tmp_path, mock_cfg):
    mock_cfg.return_value.data["workspace_root"] = str(tmp_path)
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    assert read_file(str(f)) == "hello world"

def test_read_file_error(mock_cfg):
    res = read_file("/nonexistent/file")
    assert "Error reading file" in res

def test_read_file_outside_workspace(tmp_path, mock_cfg):
    mock_cfg.return_value.data["workspace_root"] = str(tmp_path / "workspace")
    (tmp_path / "workspace").mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    res = read_file(str(outside))
    assert "resolves outside the workspace root" in res
