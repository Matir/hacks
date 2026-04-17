from trashdig.tools.detect_language import detect_language

def test_detect_language_file(temp_project):
    assert detect_language(str(temp_project / "src" / "main.py")) == "python"
    assert detect_language(str(temp_project / "web" / "app.js")) == "javascript"
    assert detect_language(str(temp_project / "README.md")) == "markdown"

def test_detect_language_directory(temp_project):
    res = detect_language(str(temp_project))
    assert "python: 60.0% (3 files)" in res
    assert "javascript: 20.0% (1 files)" in res
    assert "markdown: 20.0% (1 files)" in res
