from unittest.mock import MagicMock, patch

from trashdig.agents.utils.types import Hypothesis, TaskType
from trashdig.services.database import get_database
from trashdig.tools.update_hypothesis_status import update_hypothesis_status


def test_update_hypothesis_status(tmp_path):
    db_path = str(tmp_path / "test.db")
    db = get_database(db_path=db_path)
    hypo = Hypothesis(type=TaskType.HUNT, target="app.py",
                      description="test", confidence=0.8)
    db.save_hypothesis("/proj", hypo)
    task_id = db.get_hypotheses("/proj")[0]["task_id"]

    res = update_hypothesis_status(task_id, "completed", db_path=db_path)
    assert "updated to completed" in res
    assert db.get_hypotheses("/proj")[0]["status"] == "completed"


def test_update_hypothesis_status_delegates_to_pool(tmp_path):
    mock_db = MagicMock()
    with patch("trashdig.tools.update_hypothesis_status.get_database",
               autospec=True, return_value=mock_db):
        res = update_hypothesis_status("task-x", "failed")
    mock_db.update_hypothesis_status.assert_called_once_with("task-x", "failed")
    assert "updated to failed" in res


def test_update_hypothesis_status_error():
    res = update_hypothesis_status("task1", "completed",
                                   db_path="/nonexistent/path/db.db")
    assert "Error updating database" in res
