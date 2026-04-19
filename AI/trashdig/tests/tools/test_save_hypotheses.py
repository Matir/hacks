import json
from unittest.mock import MagicMock, patch

import pytest

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


def test_save_hypotheses_item_not_dict(mock_db):
    res = save_hypotheses(json.dumps(["a", "b"]), "/tmp/proj")
    assert "invalid hypotheses JSON" in res
    mock_db.save_hypothesis.assert_not_called()


def test_save_hypotheses_confidence_out_of_range(mock_db):
    hypo = {"target": "a.py", "confidence": 1.5}
    res = save_hypotheses(json.dumps(hypo), "/tmp/proj")
    assert "invalid hypotheses JSON" in res
    assert "confidence" in res
    mock_db.save_hypothesis.assert_not_called()


def test_save_hypotheses_confidence_negative(mock_db):
    hypo = {"target": "a.py", "confidence": -0.1}
    res = save_hypotheses(json.dumps(hypo), "/tmp/proj")
    assert "invalid hypotheses JSON" in res
    mock_db.save_hypothesis.assert_not_called()


def test_save_hypotheses_confidence_not_a_number(mock_db):
    hypo = {"target": "a.py", "confidence": "high"}
    res = save_hypotheses(json.dumps(hypo), "/tmp/proj")
    assert "invalid hypotheses JSON" in res
    mock_db.save_hypothesis.assert_not_called()


def test_save_hypotheses_non_string_target(mock_db):
    hypo = {"target": 42, "description": "desc"}
    res = save_hypotheses(json.dumps(hypo), "/tmp/proj")
    assert "invalid hypotheses JSON" in res
    mock_db.save_hypothesis.assert_not_called()


def test_save_hypotheses_boundary_confidence(mock_db):
    for conf in (0.0, 1.0):
        mock_db.reset_mock()
        hypo = {"target": "f.py", "confidence": conf}
        res = save_hypotheses(json.dumps(hypo), "/tmp/proj")
        assert "Saved 1 hypotheses" in res, f"confidence {conf} should be valid"
