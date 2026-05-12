"""Tests for the VulnDB service."""

import json

from trashdig.services.vulndb import VulnDBService


def test_vulndb_loading(tmp_path):  # type: ignore[no-untyped-def]
    """Test loading vulnerability data from a directory."""
    # Setup mock vulndb
    db_dir = tmp_path / "vulndb"
    db_dir.mkdir()
    content_dir = db_dir / "content"
    content_dir.mkdir()

    metadata = [
        {
            "id": "TEST-01",
            "title": "Test Vulnerability",
            "category": "Test",
            "severity": "High",
            "tags": ["test"],
            "active_patterns": [{"name": "Test Pattern", "pattern": "test()"}],
            "content_path": "content/test_01.md",
        }
    ]
    (db_dir / "metadata.json").write_text(json.dumps(metadata))
    (content_dir / "test_01.md").write_text("# Test Content")

    service = VulnDBService(extra_dirs=[str(db_dir)])

    entry = service.get_entry("TEST-01")
    assert entry is not None
    assert entry.title == "Test Vulnerability"
    assert entry.get_content() == "# Test Content"


def test_vulndb_query():  # type: ignore[no-untyped-def]
    """Test querying the built-in vulnerability data."""
    # This tests the built-in data (since we just seeded it)
    service = VulnDBService()
    results = service.query("SQL Injection")
    assert len(results) > 0
    assert any(r.id == "CWE-89" for r in results)


def test_vulndb_override(tmp_path):  # type: ignore[no-untyped-def]
    """Test overriding built-in data with extra directories."""
    # Setup original vulndb
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    (base_dir / "content").mkdir()
    (base_dir / "metadata.json").write_text(
        json.dumps(
            [
                {
                    "id": "VULN-01",
                    "title": "Base",
                    "category": "Base",
                    "severity": "Low",
                    "content_path": "content/v1.md",
                }
            ]
        )
    )
    (base_dir / "content" / "v1.md").write_text("Base Content")

    # Setup override vulndb
    over_dir = tmp_path / "over"
    over_dir.mkdir()
    (over_dir / "content").mkdir()
    (over_dir / "metadata.json").write_text(
        json.dumps(
            [
                {
                    "id": "VULN-01",
                    "title": "Override",
                    "category": "Over",
                    "severity": "High",
                    "content_path": "content/v1.md",
                }
            ]
        )
    )
    (over_dir / "content" / "v1.md").write_text("Override Content")

    # We need to mock the built-in dir to avoid loading real data for this test if possible,
    # but VulnDBService.__init__ loads it automatically.
    # For simplicity, we just check that extra_dirs takes precedence.
    service = VulnDBService(extra_dirs=[str(base_dir), str(over_dir)])

    entry = service.get_entry("VULN-01")
    assert entry.title == "Override"
    assert entry.get_content() == "Override Content"
