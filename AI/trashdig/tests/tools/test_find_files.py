from trashdig.tools.find_files import find_files


def test_find_files_basic(temp_project):
    res = find_files("*.py", str(temp_project))
    assert "src/main.py" in res
    assert "src/utils.py" in res
    assert "tests/test_main.py" in res
    assert "app.js" not in res

def test_find_files_non_recursive(temp_project):
    res = find_files("*.md", str(temp_project), recursive=False)
    assert "README.md" in res

    res = find_files("*.py", str(temp_project), recursive=False)
    assert res == ""
