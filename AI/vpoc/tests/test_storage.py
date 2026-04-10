import os
import pytest
import tempfile
from core.models import Finding
from core.storage import StorageManager

def test_storage_manager_lifecycle():
    """Verifies that findings can be stored and retrieved."""
    # Use a temporary directory for the database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = StorageManager(db_path)
        
        # 1. Create a finding
        finding = Finding(
            project_id="test_proj",
            vuln_type="SQLI",
            file_path="src/api.py",
            line_number=42,
            severity="HIGH",
            discovery_tool="semgrep",
            evidence="SELECT * FROM users WHERE id = " + " + id",
            llm_rationale="The id parameter is directly concatenated into the SQL query."
        )
        
        # 2. Add to storage
        stored = manager.add_finding(finding)
        assert stored.id is not None
        assert stored.status == "POTENTIAL"
        
        # 3. Retrieve by status
        findings = manager.get_findings_by_status("POTENTIAL")
        assert len(findings) == 1
        assert findings[0].vuln_type == "SQLI"
        assert findings[0].project_id == "test_proj"
