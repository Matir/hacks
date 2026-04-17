import sqlite3
import pytest
from trashdig.tools.update_hypothesis_status import update_hypothesis_status

def test_update_hypothesis_status(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE hypotheses (task_id TEXT, status TEXT, updated_at TEXT)")
    conn.execute("INSERT INTO hypotheses (task_id, status) VALUES ('task1', 'pending')")
    conn.commit()
    conn.close()

    res = update_hypothesis_status("task1", "completed", db_path=str(db_path))
    assert "updated to completed" in res

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT status FROM hypotheses WHERE task_id='task1'").fetchone()
    assert row[0] == "completed"
    conn.close()

def test_update_hypothesis_status_error():
    res = update_hypothesis_status("task1", "completed", db_path="/nonexistent/path/db.db")
    assert "Error updating database" in res
