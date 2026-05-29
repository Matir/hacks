import json
import pytest
from pathlib import Path
from podscribe.state import StateManager

def test_state_manager_init_and_save(tmp_path):
    state_mgr = StateManager(tmp_path)
    assert state_mgr.state_file == tmp_path / "state.json"
    assert state_mgr.state == {}
    
    # File should not exist yet if we haven't saved anything
    # Wait, StateManager.__init__ calls load(), which creates output_dir,
    # but doesn't write state.json if it doesn't exist.
    assert not state_mgr.state_file.exists()

def test_state_manager_update_and_load(tmp_path):
    # 1. Create entry and update
    state_mgr = StateManager(tmp_path)
    
    # Test default entry
    entry = state_mgr.get_entry("file1.mp3")
    assert entry["status"] == "new"
    assert entry["hash"] == ""
    
    # Update entry
    state_mgr.update_entry(
        "file1.mp3",
        hash="123456",
        status="preprocessed",
        preprocessed_path=Path("output/preprocessed/file1.wav")
    )
    
    # Check in-memory
    assert state_mgr.state["file1.mp3"]["hash"] == "123456"
    assert state_mgr.state["file1.mp3"]["status"] == "preprocessed"
    # Path should be converted to string in state
    assert state_mgr.state["file1.mp3"]["preprocessed_path"] == "output/preprocessed/file1.wav"
    
    # Check file exists and has content
    assert state_mgr.state_file.exists()
    with open(state_mgr.state_file, "r") as f:
        saved_data = json.load(f)
        assert saved_data["file1.mp3"]["hash"] == "123456"

    # 2. Load in a new instance
    new_state_mgr = StateManager(tmp_path)
    assert new_state_mgr.state["file1.mp3"]["hash"] == "123456"
    assert new_state_mgr.state["file1.mp3"]["status"] == "preprocessed"
    
    # Verify path conversions
    entry = new_state_mgr.get_entry("file1.mp3")
    assert entry["preprocessed_path"] == "output/preprocessed/file1.wav"

def test_state_manager_get_file_hash(tmp_path):
    dummy_file = tmp_path / "test.txt"
    dummy_file.write_text("hello world")
    
    state_mgr = StateManager(tmp_path)
    expected_hash = "5eb63bbbe01eeed093cb22bb8f5acdc3"  # md5 of "hello world"
    assert state_mgr.get_file_hash(dummy_file) == expected_hash

def test_state_manager_is_completed(tmp_path):
    state_mgr = StateManager(tmp_path)
    
    assert not state_mgr.is_completed("file1.mp3", "123456")
    
    # Incomplete status
    state_mgr.update_entry("file1.mp3", hash="123456", status="preprocessed")
    assert not state_mgr.is_completed("file1.mp3", "123456")
    
    # Completed status but wrong hash
    state_mgr.update_entry("file1.mp3", hash="123456", status="completed")
    assert not state_mgr.is_completed("file1.mp3", "wrong_hash")
    
    # Completed and matching hash
    assert state_mgr.is_completed("file1.mp3", "123456")

def test_state_manager_corrupt_json(tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text("invalid json{")
    
    # Init should handle corruption and start fresh
    state_mgr = StateManager(tmp_path)
    assert state_mgr.state == {}
