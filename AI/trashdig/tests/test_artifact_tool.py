import os
import shutil
import pytest
from trashdig.tools import artifact_tool, init_artifact_manager, _ARTIFACT_DIR

@pytest.fixture
def temp_artifact_dir(tmp_path):
    """Provides a temporary artifact directory for tests."""
    data_dir = tmp_path / ".trashdig"
    init_artifact_manager(str(data_dir))
    yield data_dir / "artifacts"
    # Cleanup after test
    if data_dir.exists():
        shutil.rmtree(data_dir)

def test_artifact_tool_no_truncation():
    """Test that artifact_tool does not truncate small output."""
    @artifact_tool(max_chars=100)
    def small_tool():
        return "small output"
    
    result = small_tool()
    assert result == "small output"
    assert "[TRUNCATED]" not in result

def test_artifact_tool_truncation(temp_artifact_dir):
    """Test that artifact_tool truncates large output and saves an artifact."""
    large_content = "A" * 200
    
    @artifact_tool(max_chars=100)
    def large_tool():
        return large_content
    
    result = large_tool()
    
    assert "[TRUNCATED: Showing first 100 characters]" in result
    assert "Output truncated for context efficiency." in result
    assert "Full output saved as artifact:" in result
    assert "Total Size: 200 characters." in result
    
    # Extract path from result
    import re
    match = re.search(r"Full output saved as artifact: (.*\.txt)", result)
    assert match is not None
    artifact_path = match.group(1)
    
    # Verify file exists and has correct content
    assert os.path.exists(artifact_path)
    with open(artifact_path, "r", encoding="utf-8") as f:
        assert f.read() == large_content

def test_artifact_tool_non_string_result():
    """Test that artifact_tool handles non-string results gracefully."""
    @artifact_tool(max_chars=10)
    def non_string_tool():
        return 12345
    
    result = non_string_tool()
    assert result == 12345

def test_init_artifact_manager(tmp_path):
    """Test that init_artifact_manager correctly sets the directory."""
    data_dir = tmp_path / "custom_data"
    init_artifact_manager(str(data_dir))
    
    from trashdig.tools import _ARTIFACT_DIR
    assert _ARTIFACT_DIR == os.path.join(str(data_dir), "artifacts")
    assert os.path.isdir(_ARTIFACT_DIR)

def test_artifact_tool_stable_filename(temp_artifact_dir):
    """Test that the same content produces the same artifact filename (hash stability)."""
    content = "Stable content for hashing"
    
    @artifact_tool(max_chars=5)
    def my_tool():
        return content

    result_a = my_tool()
    result_b = my_tool()
    
    import re
    path_a = re.search(r"artifact: (.*\.txt)", result_a).group(1)
    path_b = re.search(r"artifact: (.*\.txt)", result_b).group(1)
    
    assert path_a == path_b

@pytest.mark.anyio
async def test_artifact_tool_async(temp_artifact_dir):
    """Test that artifact_tool correctly handles async functions."""
    large_content = "B" * 150
    
    @artifact_tool(max_chars=50)
    async def async_tool():
        return large_content
    
    result = await async_tool()
    
    assert "[TRUNCATED: Showing first 50 characters]" in result
    assert "Full output saved as artifact:" in result
    
    import re
    match = re.search(r"Full output saved as artifact: (.*\.txt)", result)
    artifact_path = match.group(1)
    
    with open(artifact_path, "r", encoding="utf-8") as f:
        assert f.read() == large_content
