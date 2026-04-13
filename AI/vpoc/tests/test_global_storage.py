import os
import tempfile
import pytest
from core.models import Project, ProjectStatus, GlobalTokenUsage, BudgetConfig
from core.global_storage import GlobalStorageManager

@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "global.db")
        manager = GlobalStorageManager(db_path)
        yield manager

def test_project_crud(storage):
    # Create
    proj = storage.create_project("test-proj", "Test Project")
    assert proj.project_id == "test-proj"
    assert proj.status == ProjectStatus.INITIALIZING
    
    # Get
    retrieved = storage.get_project("test-proj")
    assert retrieved.id == proj.id
    
    # Update status
    updated = storage.update_project_status("test-proj", ProjectStatus.RUNNING)
    assert updated.status == ProjectStatus.RUNNING
    
    # List
    projects = storage.get_all_projects()
    assert len(projects) == 1
    assert projects[0].project_id == "test-proj"

def test_token_usage_tracking(storage):
    storage.track_token_usage(
        project_id="p1",
        agent_name="agent1",
        model="model1",
        tokens_in=100,
        tokens_out=50
    )
    
    usage = storage.get_daily_token_usage("p1")
    assert usage == 150
    
    # Different project
    assert storage.get_daily_token_usage("p2") == 0

def test_budget_config(storage):
    # Set first
    storage.set_budget_limit("p1", 5000)
    config = storage.get_budget_limit("p1")
    assert config.daily_limit == 5000
    
    # Update
    storage.set_budget_limit("p1", 10000)
    config = storage.get_budget_limit("p1")
    assert config.daily_limit == 10000
