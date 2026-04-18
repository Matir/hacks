import json
import pytest
from unittest.mock import MagicMock, patch
from trashdig.agents.utils.types import TaskType
from trashdig.tools.save_hypotheses import save_hypotheses

@pytest.fixture
def mock_db():
    db = MagicMock()
    with patch("trashdig.tools.save_hypotheses.get_database", autospec=True, return_value=db):
        yield db

def test_save_hypotheses(mock_db):
    hypos = [
        {"target": "a.py", "description": "desc1", "confidence": 0.9},
        {"target": "b.py", "description": "desc2"}
    ]
    res = save_hypotheses(json.dumps(hypos), "/tmp/proj")
    assert "Saved 2 hypotheses" in res
    assert mock_db.save_hypothesis.call_count == 2
    
    # Verify TaskType.HUNT was used
    args = mock_db.save_hypothesis.call_args_list[0][0]
    assert args[1].type == TaskType.HUNT

def test_save_hypotheses_error():
    res = save_hypotheses("invalid json", "/tmp/proj")
    assert "Error saving hypotheses" in res
