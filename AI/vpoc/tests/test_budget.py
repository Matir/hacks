import os
import tempfile
import pytest
from unittest.mock import MagicMock
from core.budget import BudgetManager, BudgetExhaustedError
from core.global_storage import GlobalStorageManager
from core.events import EventBus

@pytest.fixture
def budget_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "global.db")
        global_storage = GlobalStorageManager(db_path)
        event_bus = MagicMock(spec=EventBus)
        manager = BudgetManager(global_storage, event_bus)
        yield manager

@pytest.mark.asyncio
async def test_check_budget_pass(budget_manager):
    # Default is 1M, should pass
    await budget_manager.check_budget("p1", 500)

@pytest.mark.asyncio
async def test_check_budget_exhausted(budget_manager):
    # Set limit low
    budget_manager.global_storage.set_budget_limit("p1", 100)
    
    # Track some usage
    budget_manager.record_usage("p1", "agent", "model", 60, 50) # 110 total
    
    with pytest.raises(BudgetExhaustedError):
        await budget_manager.check_budget("p1", 10)

@pytest.mark.asyncio
async def test_record_usage(budget_manager):
    budget_manager.record_usage("p1", "agent", "model", 100, 200)
    assert budget_manager.global_storage.get_daily_token_usage("p1") == 300
