from unittest.mock import MagicMock

import pytest
from textual.widgets import DataTable, Input

from trashdig.findings import Finding
from trashdig.tui.app import TrashDigApp
from trashdig.tui.screens.finding_detail import FindingDetailScreen
from trashdig.tui.screens.findings import FindingsScreen


@pytest.mark.anyio
async def test_findings_screen():
    findings = [
        Finding(
            title="SQL Injection",
            description="SQLi allows exfiltration",
            severity="high",
            vulnerable_code="SELECT",
            file_path="src/api.js",
            impact="Data loss",
            remediation="Fix it",
            cwe_id="CWE-89",
            exploitation_path="Taint trace",
            poc="",
        ),
        Finding(
            title="XSS",
            description="Reflected XSS",
            severity="medium",
            vulnerable_code="<script>",
            file_path="src/index.html",
            impact="Session hijack",
            remediation="Encode",
            cwe_id="CWE-79",
            exploitation_path="Trace",
            poc="",
        ),
    ]

    app = TrashDigApp()
    app.coordinator = MagicMock()
    app.coordinator.findings = findings

    async with app.run_test(size=(120, 80)) as pilot:
        screen = FindingsScreen()
        app.push_screen(screen)
        await pilot.pause()

        # Test table population
        table = screen.query_one(DataTable)
        assert table.row_count == 2

        # Test search filtering
        search_input = screen.query_one(Input)
        search_input.value = "XSS"
        await pilot.pause()
        assert table.row_count == 1

        # Test row selection
        table.move_cursor(row=0)
        screen.action_select_finding()
        await pilot.pause()

        # Detail screen should be pushed
        assert isinstance(app.screen, FindingDetailScreen)
        assert app.screen.finding.title == "XSS"

        # Back out
        app.pop_screen()
        await pilot.pause()

        # Test row selected event
        class MockEvent:
            cursor_row = 0

        screen.on_data_table_row_selected(MockEvent())
        await pilot.pause()
        assert isinstance(app.screen, FindingDetailScreen)
        assert app.screen.finding.title == "XSS"

        # Test back action
        app.pop_screen()
        await pilot.pause()
        assert isinstance(app.screen, FindingsScreen)
        screen.action_back()
        await pilot.pause()
        assert not isinstance(app.screen, FindingsScreen)
