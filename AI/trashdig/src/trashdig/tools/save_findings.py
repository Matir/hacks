import json

from ..findings import Finding
from ..services.database import get_database

_VALID_SEVERITIES = frozenset({"critical", "high", "medium", "low", "info", "n/a"})
_STRING_FIELDS = ("title", "description", "file_path", "impact", "exploitation_path",
                  "remediation", "vulnerable_code")


def _validate_finding(raw: object, index: int) -> str | None:
    """Return an error string if raw is not a valid finding dict, else None."""
    if not isinstance(raw, dict):
        return f"item {index} is not an object"
    severity = raw.get("severity")
    if severity is not None and str(severity).lower() not in _VALID_SEVERITIES:
        return f"item {index} has invalid severity {severity!r}"
    for f in _STRING_FIELDS:
        val = raw.get(f)
        if val is not None and not isinstance(val, str):
            return f"item {index} field {f!r} must be a string"
    return None


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

        for i, item in enumerate(data):
            err = _validate_finding(item, i)
            if err:
                return f"Error: invalid findings JSON — {err}"

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
