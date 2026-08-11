from unittest.mock import patch

from trashdig.tools.get_project_structure import get_project_structure


@patch("trashdig.tools.get_project_structure._get_struct", autospec=True)
def test_get_project_structure(mock_get_struct):
    mock_get_struct.return_value = ["a.py", "b.py"]
    res = get_project_structure(".")
    assert res == "a.py\nb.py"


def test_get_project_structure_with_gitignore(temp_project):
    (temp_project / ".gitignore").write_text("web/\n")
    res = get_project_structure(str(temp_project))
    assert "src/main.py" in res
    assert "web/app.js" not in res

