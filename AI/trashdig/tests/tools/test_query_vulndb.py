from unittest.mock import MagicMock, patch

from trashdig.tools.query_vulndb import query_vulndb


@patch("trashdig.tools.query_vulndb.get_vulndb_service", autospec=True)
def test_query_vulndb_no_results(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    mock_service.query.return_value = []

    result = query_vulndb("nonexistent_cwe")

    assert "No results found for query: nonexistent_cwe" in result
    mock_service.query.assert_called_once_with("nonexistent_cwe")


@patch("trashdig.tools.query_vulndb.get_vulndb_service", autospec=True)
def test_query_vulndb_with_results(mock_get_service):
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service

    mock_entry1 = MagicMock()
    mock_entry1.id = "CWE-123"
    mock_entry1.title = "Sample title"
    mock_entry1.category = "Sample Category"
    mock_entry1.severity = "high"
    mock_entry1.tags = ["tag1", "tag2"]
    mock_entry1.active_patterns = [
        {"name": "pattern1", "languages": ["python"], "pattern": "print($X)"}
    ]
    mock_entry1.get_content.return_value = "Content for CWE-123"

    mock_entry2 = MagicMock()
    mock_entry2.id = "CWE-456"
    mock_entry2.title = "Another title"
    mock_entry2.category = "Category 2"
    mock_entry2.severity = "low"
    mock_entry2.tags = ["tag3"]
    mock_entry2.active_patterns = None
    mock_entry2.get_content.return_value = "Content for CWE-456"

    mock_service.query.return_value = [mock_entry1, mock_entry2]

    result = query_vulndb("CWE-")

    assert "## CWE-123: Sample title" in result
    assert "**Category:** Sample Category | **Severity:** high" in result
    assert "**Tags:** tag1, tag2" in result
    assert "### Active Patterns (Semgrep)" in result
    assert "- **pattern1** (python)" in result
    assert "print($X)" in result
    assert "Content for CWE-123" in result

    assert "## CWE-456: Another title" in result
    assert "Content for CWE-456" in result

    mock_service.query.assert_called_once_with("CWE-")


@patch("trashdig.tools.query_vulndb.get_vulndb_service", autospec=True)
def test_query_vulndb_exception(mock_get_service):
    mock_get_service.side_effect = Exception("Service unavailable")

    result = query_vulndb("x")

    assert "Error querying VulnDB: Service unavailable" in result
