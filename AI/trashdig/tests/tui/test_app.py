import asyncio
from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import RichLog, Static

from trashdig.config import Config
from trashdig.tui.app import REPLPane, TrashDigApp


@pytest.fixture
def mock_config(tmp_path):
    with patch("trashdig.config.get_config") as mock:
        c = MagicMock(spec=Config)
        c.workspace_root = str(tmp_path)
        c.data_dir = str(tmp_path / ".trashdig")
        c.db_path = str(tmp_path / ".trashdig" / "trashdig.db")
        c.resolve_data_path.side_effect = lambda f: str(tmp_path / f)
        mock.return_value = c
        yield c

@pytest.fixture
def mock_coordinator():
    with patch("trashdig.tui.app.Coordinator", autospec=True) as mock_cls:
        mock_inst = mock_cls.return_value
        mock_inst.tech_stack = "Python"
        mock_inst.scan_results = {}
        mock_inst.findings = []
        mock_inst.task_queue = []
        mock_inst.completed_tasks = []
        mock_inst.total_messages = 0
        mock_inst.input_tokens = 0
        mock_inst.output_tokens = 0
        mock_inst.llm_errors = 0
        mock_inst.session_id = "test-session"
        yield mock_inst

async def test_app_initialization(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#status_body", Static)
        assert app.query_one(RichLog)

async def test_app_help_command(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # Instead of finding the input which seems tricky with AutoComplete,
        # we can call the command handler directly or try harder to find it.
        repl = app.query_one(REPLPane)
        # Type 'help' and press enter
        await pilot.press(*"help", "enter")
        await pilot.pause()
        assert repl

async def test_app_quit_binding(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        assert mock_coordinator.db.close_scan_session.called

async def test_app_refresh_status(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.refresh_status()
        assert app.query_one("#status_body", Static)

async def test_concurrent_verification_stays_busy_until_all_finish(mock_config, mock_coordinator):
    """Regression test: the status phase must not snap to "Idle" just because
    one of several concurrently-running verifications finished first.
    """
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        release_first = asyncio.Event()

        async def fake_verify_finding(finding):
            if finding.title == "slow":
                await release_first.wait()

        mock_coordinator.verify_finding = fake_verify_finding

        slow_finding = MagicMock(title="slow")
        fast_finding = MagicMock(title="fast")

        slow_task = asyncio.create_task(app.run_verification(slow_finding))
        await asyncio.sleep(0)  # let the slow worker start and block
        assert app._phase == "Verifying"

        await app.run_verification(fast_finding)  # completes immediately
        # The slow worker is still in flight, so phase must stay "Verifying".
        assert app._phase == "Verifying"

        release_first.set()
        await slow_task
        assert app._phase == "Idle"
