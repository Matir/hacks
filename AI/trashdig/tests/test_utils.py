import os
import tempfile

from trashdig.agents.utils import (
    detect_frameworks,
    get_project_structure,
    read_file_content,
)


def test_get_project_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some files
        os.makedirs(os.path.join(tmpdir, "subdir"))
        with open(os.path.join(tmpdir, "file1.txt"), "w") as f:
            f.write("content1")
        with open(os.path.join(tmpdir, "subdir", "file2.txt"), "w") as f:
            f.write("content2")
        with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
            f.write("file1.txt\n")
            
        # Mock noisy dirs to avoid skipping them in tests if they are created
        # But here we don't create them.
        
        structure = get_project_structure(tmpdir)
        
        # .gitignore should be included unless ignored by itself
        assert ".gitignore" in structure
        assert os.path.join("subdir", "file2.txt") in structure
        assert "file1.txt" not in structure

def test_read_file_content():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
        tmp.write("Hello, World!")
        tmp_path = tmp.name
        
    try:
        content = read_file_content(tmp_path, max_chars=5)
        assert content == "Hello"
        
        content = read_file_content(tmp_path)
        assert content == "Hello, World!"
    finally:
        os.remove(tmp_path)

def test_read_file_content_error():
    assert read_file_content("non_existent_file.txt") == "[Error: Could not read file content]"

def test_detect_frameworks():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock requirements.txt
        req_path = os.path.join(tmpdir, "requirements.txt")
        with open(req_path, "w") as f:
            f.write("fastapi==0.100.0\nsqlalchemy==2.0.0\n")
            
        file_list = ["requirements.txt"]
        stack = detect_frameworks(file_list, project_root=tmpdir)
        
        assert "fastapi" in stack["web_frameworks"]
        assert "sqlalchemy" in stack["databases"]
        assert "flask" not in stack["web_frameworks"]

def test_detect_frameworks_no_files():
    stack = detect_frameworks([])
    assert all(len(v) == 0 for v in stack.values())
