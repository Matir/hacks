import json
from unittest.mock import MagicMock, patch
from trashdig.tools.query_cwe_database import query_cwe_database

@patch("json.load")
@patch("builtins.open")
def test_query_cwe_database(mock_open, mock_json_load):
    mock_json_load.return_value = [
        {
            "cwe_id": "CWE-79",
            "title": "XSS",
            "description": "Cross-site Scripting",
            "examples": [{"language": "python", "vulnerable_code": "print(userInput)"}]
        }
    ]

    result = query_cwe_database("XSS")
    assert "CWE-79: XSS" in result
    assert "Cross-site Scripting" in result
    assert "Vulnerable Example (python):" in result

def test_query_cwe_database_no_results():
    with patch("builtins.open", MagicMock()), patch("json.load", return_value=[]):
        result = query_cwe_database("nonexistent")
        assert "No results found" in result
