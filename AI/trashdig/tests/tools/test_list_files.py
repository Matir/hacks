from trashdig.tools.list_files import list_files


def test_list_files_basic(temp_project):
    res = list_files(str(temp_project))
    assert "F" in res
    assert "D" in res
    assert "README.md" in res
    assert "src" in res

def test_list_files_recursive(temp_project):
    res = list_files(str(temp_project), recursive=True)
    assert "src/main.py" in res
    assert "web/app.js" in res
