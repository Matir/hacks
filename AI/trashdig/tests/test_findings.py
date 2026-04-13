import os
import tempfile
from trashdig.findings import Finding

def test_finding_to_markdown():
    finding = Finding(
        title="Test Finding",
        description="A test description",
        severity="High",
        vulnerable_code="print('vulnerable')",
        file_path="src/main.py",
        impact="Test impact",
        exploitation_path="Test path",
        remediation="Test remediation",
        cwe_id="CWE-79",
        poc="print('poc')"
    )
    
    md = finding.to_markdown()
    assert "# Test Finding" in md
    assert "**Severity:** High" in md
    assert "**CWE:** CWE-79" in md
    assert "## Description" in md
    assert "A test description" in md
    assert "## Proof of Concept" in md
    assert "print('poc')" in md
    assert "```py\nprint('vulnerable')\n```" in md
    assert "## Impact" in md
    assert "Test impact" in md

def test_finding_save():
    finding = Finding(
        title="Test Save",
        description="A test description",
        severity="Medium",
        vulnerable_code="code",
        file_path="test.py",
        impact="impact",
        exploitation_path="path",
        remediation="remediation"
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = finding.save(tmpdir)
        assert os.path.exists(path)
        assert os.path.basename(path).startswith("Test_Save_")
        with open(path, "r") as f:
            content = f.read()
            assert "# Test Save" in content
            
def test_finding_save_creates_dir():
    finding = Finding(
        title="Test Dir Create",
        description="A test description",
        severity="Medium",
        vulnerable_code="code",
        file_path="test.py",
        impact="impact",
        exploitation_path="path",
        remediation="remediation"
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = os.path.join(tmpdir, "new_findings_dir")
        path = finding.save(output_dir)
        assert os.path.exists(output_dir)
        assert os.path.exists(path)
