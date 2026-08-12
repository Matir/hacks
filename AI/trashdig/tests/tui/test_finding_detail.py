from unittest.mock import MagicMock

import pytest

from trashdig.findings import Finding
from trashdig.tui.app import TrashDigApp
from trashdig.tui.screens.finding_detail import FindingDetailScreen


@pytest.mark.anyio
async def test_finding_detail_screen():
    finding = Finding(
        title="SQL Injection",
        description="SQLi allows exfiltration",
        severity="high",
        vulnerable_code="SELECT * FROM users WHERE id = $_GET['id']",
        file_path="src/api.js",
        impact="Data loss",
        remediation="Use prepared statements",
        cwe_id="CWE-89",
        exploitation_path="Taint trace",
        poc="curl 'http://...?id=1 UNION SELECT'",
    )

    app = TrashDigApp()
    app.coordinator = MagicMock()
    app.coordinator.project_path = "/tmp"
    app.coordinator.db = MagicMock()
    app.refresh_status = MagicMock()

    async with app.run_test(size=(120, 180)) as pilot:
        screen = FindingDetailScreen(finding)
        app.push_screen(screen)
        await pilot.pause()

        screen.action_back()
        await pilot.pause()

        app.push_screen(screen)
        await pilot.pause()

        screen.query_one("#btn_confirm").press()
        await pilot.pause()
        assert finding.verification_status == "Confirmed"
        app.coordinator.db.save_finding.assert_called_with("/tmp", finding)

        screen.query_one("#btn_fp").press()
        await pilot.pause()
        assert finding.verification_status == "False Positive"

        screen.query_one("#btn_fixed").press()
        await pilot.pause()
        assert finding.verification_status == "Fixed"
