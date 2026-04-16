import json

from ..findings import Finding
from ..services.database import get_database


def save_findings(findings_json: str, project_path: str, db_path: str | None = None) -> str:
    """Saves a list of findings to the database.

    Args:
        findings_json: A JSON string containing a list of finding objects.
        project_path: The project root directory.
        db_path: Path to the SQLite database. Defaults to config value.

    Returns:
        A confirmation message.
    """
    try:
        data = json.loads(findings_json)
        if not isinstance(data, list):
            data = [data]

        count = 0
        db = get_database(db_path)
        for raw in data:
            finding = Finding(
                title=raw.get("title", "Untitled"),
                description=raw.get("description", "N/A"),
                severity=raw.get("severity", "N/A"),
                vulnerable_code=raw.get("vulnerable_code", "N/A"),
                file_path=raw.get("file_path", "N/A"),
                impact=raw.get("impact", "N/A"),
                exploitation_path=raw.get("exploitation_path", "N/A"),
                remediation=raw.get("remediation", "N/A"),
                cwe_id=raw.get("cwe_id"),
            )
            db.save_finding(project_path, finding)
            count += 1
        return f"Saved {count} findings."
    except Exception as e:
        return f"Error saving findings: {str(e)}"
