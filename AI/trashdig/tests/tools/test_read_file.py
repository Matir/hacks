from trashdig.tools.read_file import read_file


def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    assert read_file(str(f)) == "hello world"

def test_read_file_error():
    res = read_file("/nonexistent/file")
    assert "Error reading file" in res
