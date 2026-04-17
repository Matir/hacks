import json
import pytest
from unittest.mock import MagicMock, patch
from trashdig.tools.save_findings import save_findings

@pytest.fixture
def mock_db():
    db = MagicMock()
    with patch("trashdig.tools.save_findings.get_database", autospec=True, return_value=db):
        yield db

def test_save_findings(mock_db):
    findings = [
        {"title": "SQLi", "severity": "High", "file_path": "a.py"},
        {"title": "XSS"}
    ]
    res = save_findings(json.dumps(findings), "/tmp/proj")
    assert "Saved 2 findings" in res
    assert mock_db.save_finding.call_count == 2

def test_save_findings_single_object(mock_db):
    finding = {"title": "SQLi"}
    res = save_findings(json.dumps(finding), "/tmp/proj")
    assert "Saved 1 findings" in res
    mock_db.save_finding.assert_called_once()

def test_save_findings_error():
    res = save_findings("invalid json", "/tmp/proj")
    assert "Error saving findings" in res
