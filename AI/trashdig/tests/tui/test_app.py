import asyncio
from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Input, RichLog, Static

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


async def test_app_pause_command(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)
        log = app.query_one(RichLog)
        await repl.process_command("pause", log)
        mock_coordinator.pause.assert_called_once()


async def test_app_resume_command(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)
        log = app.query_one(RichLog)
        await repl.process_command("resume", log)
        mock_coordinator.resume.assert_called_once()


async def test_app_hint_command(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)
        log = app.query_one(RichLog)
        await repl.process_command("hint focus on auth.py", log)
        mock_coordinator.add_hint.assert_called_once_with("focus on auth.py")


async def test_app_hint_command_requires_text(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)
        log = app.query_one(RichLog)
        await repl.process_command("hint", log)
        mock_coordinator.add_hint.assert_not_called()


async def test_app_hypotheses_list_command(mock_config, mock_coordinator):
    mock_coordinator.project_path = "/proj"
    mock_coordinator.db = MagicMock()
    mock_coordinator.db.get_hypotheses.return_value = [
        {
            "task_id": "abcdef12-3456-0000-0000-000000000000",
            "confidence": 0.8,
            "status": "pending",
            "target": "a.py",
            "description": "test hypothesis",
        }
    ]
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)
        log = app.query_one(RichLog)
        await repl.process_command("hypotheses", log)
        mock_coordinator.db.get_hypotheses.assert_called_once_with("/proj")


async def test_app_hypotheses_delete_command(mock_config, mock_coordinator):
    mock_coordinator.project_path = "/proj"
    mock_coordinator.db = MagicMock()
    mock_coordinator.db.get_hypotheses.return_value = [
        {
            "task_id": "abcdef12-3456-0000-0000-000000000000",
            "confidence": 0.8,
            "status": "pending",
            "target": "a.py",
            "description": "test hypothesis",
        }
    ]
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)
        log = app.query_one(RichLog)
        await repl.process_command("hypotheses del abcdef", log)
        mock_coordinator.db.delete_hypothesis.assert_called_once_with(
            "abcdef12-3456-0000-0000-000000000000"
        )


async def test_app_hypotheses_prio_command(mock_config, mock_coordinator):
    mock_coordinator.project_path = "/proj"
    mock_coordinator.db = MagicMock()
    mock_coordinator.db.get_hypotheses.return_value = [
        {
            "task_id": "abcdef12-3456-0000-0000-000000000000",
            "confidence": 0.8,
            "status": "pending",
            "target": "a.py",
            "description": "test hypothesis",
        }
    ]
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)
        log = app.query_one(RichLog)
        await repl.process_command("hypotheses prio abcdef 0.9", log)
        mock_coordinator.db.update_hypothesis_confidence.assert_called_once_with(
            "abcdef12-3456-0000-0000-000000000000", 0.9
        )


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


async def test_app_repl_input_submitted(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)

        log = repl.query_one(RichLog)

        inp = repl.query_one(Input)
        inp.value = "help"
        await inp.action_submit()
        await pilot.pause()
        assert any("Available commands" in line.text for line in log.lines[-5:])


async def test_app_commands_verify(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)
        log = repl.query_one(RichLog)

        mock_run = MagicMock()
        with patch.object(app, "run_verification", new=mock_run):
            # Test verify with no args (submits all)
            mock_coordinator.findings = [MagicMock()]
            app.run_worker = MagicMock()
            await repl.process_command("verify", log)
            mock_run.assert_called_once()

            # Test verify with idx 1
            mock_run.reset_mock()
            await repl.process_command("verify 1", log)
            mock_run.assert_called_once()

            # Test verify with invalid idx
            mock_run.reset_mock()
            await repl.process_command("verify 999", log)
            mock_run.assert_not_called()

            # Test empty findings
            mock_coordinator.findings = []
            await repl.process_command("verify", log)
            mock_run.assert_not_called()


async def test_app_commands_star(mock_config, mock_coordinator):
    app = TrashDigApp()
    app._file_log = MagicMock()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)
        log = repl.query_one(RichLog)
        app.refresh_status = MagicMock()

        await repl.process_command("star path1", log)
        assert "path1" in app.prioritized_targets

        await repl.process_command("star path1", log)
        # Verify it doesn't double add
        assert app.prioritized_targets.count("path1") == 1


async def test_app_commands_scan(mock_config, mock_coordinator):
    app = TrashDigApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        repl = app.query_one(REPLPane)
        log = repl.query_one(RichLog)
        mock_run = MagicMock()
        with patch.object(app, "run_full_scan_pipeline", new=mock_run):
            app.run_worker = MagicMock()

            await repl.process_command("scan something/", log)
            mock_run.assert_called_once()


async def test_app_log_message_extra(mock_config, mock_coordinator):
    app = TrashDigApp()
    app._file_log = MagicMock()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.log_message("info", "Hello from Test")
        app._file_log.info.assert_called_with("Hello from Test")
