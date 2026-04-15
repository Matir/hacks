"""Tests for the SQLite ProjectDatabase."""

import os
import tempfile

import pytest

from trashdig.services.database import ProjectDatabase, _args_hash
from trashdig.findings import Finding
from trashdig.agents.types import Hypothesis, TaskType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(tmp_path: str) -> ProjectDatabase:
    return ProjectDatabase(db_path=os.path.join(tmp_path, ".trashdig", "trashdig.db"))


def _make_finding(**kwargs) -> Finding:
    defaults = dict(
        title="SQL Injection",
        description="User input concatenated into query",
        severity="High",
        vulnerable_code="db.execute('SELECT * FROM users WHERE id=' + user_id)",
        file_path="app/routes.py",
        impact="Database exfiltration",
        exploitation_path="Send id=1 OR 1=1",
        remediation="Use parameterised queries",
        cwe_id="CWE-89",
    )
    defaults.update(kwargs)
    return Finding(**defaults)


def _make_hypothesis(target: str = "app/db.py", desc: str = "Trace user_id") -> Hypothesis:
    return Hypothesis(
        type=TaskType.HUNT,
        target=target,
        description=desc,
        confidence=0.75,
    )


# ---------------------------------------------------------------------------
# _args_hash
# ---------------------------------------------------------------------------

def test_args_hash_deterministic():
    args = {"pattern": "SELECT", "path": "."}
    assert _args_hash(args) == _args_hash(args)


def test_args_hash_order_independent():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert _args_hash(a) == _args_hash(b)


def test_args_hash_differs_for_different_args():
    assert _args_hash({"a": 1}) != _args_hash({"a": 2})


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def test_db_creates_directory_and_file():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "nested", "dir", "trashdig.db")
        ProjectDatabase(db_path=db_path)
        assert os.path.exists(db_path)


# ---------------------------------------------------------------------------
# Project profiles
# ---------------------------------------------------------------------------

def test_save_and_get_project_profile():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        profile = {"src/main.py": {"is_high_value": True}}
        db.save_project_profile("/proj", "Python/FastAPI", profile)

        result = db.get_project_profile("/proj")
        assert result is not None
        assert result["tech_stack"] == "Python/FastAPI"
        assert result["profile"] == profile
        assert "created_at" in result
        assert "updated_at" in result


def test_get_project_profile_missing_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        assert db.get_project_profile("/nonexistent") is None


def test_save_project_profile_upsert():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        db.save_project_profile("/proj", "Python", {"a": 1})
        db.save_project_profile("/proj", "Python/Django", {"b": 2})

        result = db.get_project_profile("/proj")
        assert result["tech_stack"] == "Python/Django"
        assert result["profile"] == {"b": 2}


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

def test_save_and_get_finding():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        finding = _make_finding()
        row_id = db.save_finding("/proj", finding)
        assert row_id > 0

        rows = db.get_findings("/proj")
        assert len(rows) == 1
        assert rows[0]["title"] == "SQL Injection"
        assert rows[0]["severity"] == "High"
        assert rows[0]["verification_status"] == "Unverified"


def test_save_finding_deduplication():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        finding = _make_finding()
        db.save_finding("/proj", finding)
        db.save_finding("/proj", finding)

        rows = db.get_findings("/proj")
        assert len(rows) == 1


def test_update_finding_status():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        finding = _make_finding()
        db.save_finding("/proj", finding)

        db.update_finding_status("/proj", finding.title, finding.file_path, "Verified", "exploit()")

        rows = db.get_findings("/proj")
        assert rows[0]["verification_status"] == "Verified"
        assert rows[0]["poc"] == "exploit()"


def test_findings_scoped_by_project():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        db.save_finding("/proj-a", _make_finding(title="FindingA"))
        db.save_finding("/proj-b", _make_finding(title="FindingB"))

        assert len(db.get_findings("/proj-a")) == 1
        assert db.get_findings("/proj-a")[0]["title"] == "FindingA"
        assert len(db.get_findings("/proj-b")) == 1


# ---------------------------------------------------------------------------
# Hypotheses
# ---------------------------------------------------------------------------

def test_save_and_get_hypothesis():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        hypo = _make_hypothesis()
        row_id = db.save_hypothesis("/proj", hypo)
        assert row_id > 0

        rows = db.get_hypotheses("/proj")
        assert len(rows) == 1
        assert rows[0]["target"] == "app/db.py"
        assert rows[0]["status"] == "pending"
        assert rows[0]["confidence"] == pytest.approx(0.75)


def test_update_hypothesis_status():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        hypo = _make_hypothesis()
        db.save_hypothesis("/proj", hypo)

        db.update_hypothesis_status(hypo.id, "completed", result={"finding_count": 2})

        rows = db.get_hypotheses("/proj")
        assert rows[0]["status"] == "completed"
        assert rows[0]["result"]["finding_count"] == 2


def test_save_hypothesis_ignore_duplicate_task_id():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        hypo = _make_hypothesis()
        db.save_hypothesis("/proj", hypo)
        db.save_hypothesis("/proj", hypo)  # same task_id — should not raise

        assert len(db.get_hypotheses("/proj")) == 1


def test_failed_hypothesis_persisted():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        hypo = _make_hypothesis()
        db.save_hypothesis("/proj", hypo)
        db.update_hypothesis_status(hypo.id, "failed")

        rows = db.get_hypotheses("/proj")
        assert rows[0]["status"] == "failed"


# ---------------------------------------------------------------------------
# Symbol map
# ---------------------------------------------------------------------------

def test_save_and_get_symbol():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        db.save_symbol("/proj", "fetch_user", "app/db.py", 42, "function")

        results = db.get_symbol("/proj", "fetch_user")
        assert len(results) == 1
        assert results[0]["file_path"] == "app/db.py"
        assert results[0]["line_number"] == 42
        assert results[0]["symbol_type"] == "function"


def test_get_symbol_unknown_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        assert db.get_symbol("/proj", "nonexistent") == []


def test_save_symbol_no_duplicate():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        db.save_symbol("/proj", "fn", "a.py", 1, "function")
        db.save_symbol("/proj", "fn", "a.py", 1, "function")  # duplicate, ignored

        assert len(db.get_symbol("/proj", "fn")) == 1


def test_save_symbol_multiple_locations():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        db.save_symbol("/proj", "fn", "a.py", 1, "function")
        db.save_symbol("/proj", "fn", "b.py", 10, "function")

        results = db.get_symbol("/proj", "fn")
        assert len(results) == 2


# ---------------------------------------------------------------------------
# Tool output cache
# ---------------------------------------------------------------------------

def test_cache_and_retrieve_tool_output():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        args = {"pattern": "SELECT", "path": "app/"}
        db.cache_tool_output("/proj", "ripgrep_search", args, "app/db.py:10: SELECT *")

        cached = db.get_cached_tool_output("/proj", "ripgrep_search", args)
        assert cached == "app/db.py:10: SELECT *"


def test_cache_miss_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        result = db.get_cached_tool_output("/proj", "ripgrep_search", {"x": "y"})
        assert result is None


def test_cache_replace_on_same_key():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        args = {"pattern": "foo"}
        db.cache_tool_output("/proj", "ripgrep_search", args, "first")
        db.cache_tool_output("/proj", "ripgrep_search", args, "second")

        assert db.get_cached_tool_output("/proj", "ripgrep_search", args) == "second"


def test_cache_scoped_by_project():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        args = {"pattern": "foo"}
        db.cache_tool_output("/proj-a", "ripgrep_search", args, "result-a")
        db.cache_tool_output("/proj-b", "ripgrep_search", args, "result-b")

        assert db.get_cached_tool_output("/proj-a", "ripgrep_search", args) == "result-a"
        assert db.get_cached_tool_output("/proj-b", "ripgrep_search", args) == "result-b"


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

def test_log_conversation():
    with tempfile.TemporaryDirectory() as tmp:
        db = _make_db(tmp)
        db.log_conversation(
            "/proj",
            "test_agent",
            "test prompt",
            "test response",
            [{"name": "tool", "args": {"a": 1}}],
            100,
            50,
        )

        with db._connect() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE agent_name = 'test_agent'").fetchone()
            assert row is not None
            assert row["project_path"] == "/proj"
            assert row["prompt"] == "test prompt"
            assert row["response"] == "test response"
            assert "tool" in row["tool_calls"]
            assert row["input_tokens"] == 100
            assert row["output_tokens"] == 50
            assert "timestamp" in row.keys()
