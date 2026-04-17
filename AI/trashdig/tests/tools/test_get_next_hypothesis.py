import json
import sqlite3
import pytest
from trashdig.tools.get_next_hypothesis import get_next_hypothesis

def test_get_next_hypothesis(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE hypotheses (task_id TEXT, project_path TEXT, status TEXT, confidence REAL)")
    conn.execute("INSERT INTO hypotheses (task_id, project_path, status, confidence) VALUES ('t1', '/p', 'pending', 0.8)")
    conn.execute("INSERT INTO hypotheses (task_id, project_path, status, confidence) VALUES ('t2', '/p', 'pending', 0.9)")
    conn.commit()
    conn.close()

    res = get_next_hypothesis("/p", db_path=str(db_path))
    data = json.loads(res)
    assert data["task_id"] == "t2" # Highest confidence

def test_get_next_hypothesis_none(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE hypotheses (task_id TEXT, project_path TEXT, status TEXT, confidence REAL)")
    conn.commit()
    conn.close()

    res = get_next_hypothesis("/p", db_path=str(db_path))
    assert res == "None"

def test_get_next_hypothesis_error():
    res = get_next_hypothesis("/p", db_path="/nonexistent/db.db")
    assert "Error accessing database" in res
