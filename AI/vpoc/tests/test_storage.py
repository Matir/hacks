import os
import tempfile
import pytest
from core.models import AgentCheckpoint, Finding, FindingStatus, HintLog
from core.storage import StorageManager


def test_storage_manager_lifecycle():
    """Verifies that findings can be stored and retrieved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = StorageManager(db_path)

        finding = Finding(
            project_id="test_proj",
            vuln_type="SQLI",
            file_path="src/api.py",
            line_number=42,
            severity="HIGH",
            discovery_tool="semgrep",
            evidence="SELECT * FROM users WHERE id = " + " + id",
            llm_rationale="The id parameter is directly concatenated into the SQL query.",
        )

        stored = manager.add_finding(finding)
        assert stored.id is not None
        assert stored.status == FindingStatus.POTENTIAL

        findings = manager.get_findings_by_status(FindingStatus.POTENTIAL)
        assert len(findings) == 1
        assert findings[0].vuln_type == "SQLI"
        assert findings[0].project_id == "test_proj"


def test_update_finding_status():
    """Verifies that finding status transitions are persisted correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = StorageManager(db_path)

        finding = Finding(
            project_id="proj",
            vuln_type="XSS",
            file_path="src/view.py",
            line_number=10,
            severity="MEDIUM",
            discovery_tool="semgrep",
            evidence="innerHTML = userInput",
        )
        stored = manager.add_finding(finding)
        assert stored.status == FindingStatus.POTENTIAL

        updated = manager.update_finding_status(stored.id, FindingStatus.SCREENED)
        assert updated.status == FindingStatus.SCREENED

        # Verify the change is reflected in a fresh query.
        screened = manager.get_findings_by_status(FindingStatus.SCREENED)
        assert len(screened) == 1
        assert screened[0].id == stored.id

        potential = manager.get_findings_by_status(FindingStatus.POTENTIAL)
        assert len(potential) == 0


def test_update_finding_status_missing_raises():
    """Verifies that updating a non-existent finding raises ValueError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = StorageManager(db_path)

        with pytest.raises(ValueError, match="Finding 999 not found"):
            manager.update_finding_status(999, FindingStatus.SCREENED)


def test_agent_checkpoint_crud():
    """Verifies save, retrieve, and clear operations for AgentCheckpoint."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = StorageManager(db_path)

        cp = AgentCheckpoint(
            agent_name="source_review",
            stage="FILE_COMPLETE",
            state_json='{"file": "src/api.py", "tool": "semgrep", "finding_ids": []}',
        )
        saved = manager.save_checkpoint(cp)
        assert saved.id is not None

        checkpoints = manager.get_checkpoints("source_review")
        assert len(checkpoints) == 1
        assert checkpoints[0].stage == "FILE_COMPLETE"

        # A different agent should see no checkpoints.
        assert manager.get_checkpoints("poc_agent") == []

        manager.clear_checkpoints("source_review")
        assert manager.get_checkpoints("source_review") == []


def test_hint_log_crud():
    """Verifies add and retrieve operations for HintLog."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = StorageManager(db_path)

        hint = HintLog(
            project_id="proj-1",
            event_type="hint",
            content="Focus on authentication endpoints",
        )
        saved = manager.add_hint(hint)
        assert saved.id is not None

        command = HintLog(
            project_id="proj-1",
            event_type="command",
            content="PRIORITIZE_RCE",
            args_json="{}",
        )
        manager.add_hint(command)

        hints = manager.get_hints("proj-1")
        assert len(hints) == 2
        assert hints[0].event_type == "hint"
        assert hints[1].event_type == "command"

        # Different project should see nothing.
        assert manager.get_hints("proj-2") == []
