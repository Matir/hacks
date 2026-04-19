import json

from ..agents.utils.types import Hypothesis, TaskType
from ..services.database import get_database


def _validate_hypothesis(raw: object, index: int) -> str | None:
    """Return an error string if raw is not a valid hypothesis dict, else None."""
    if not isinstance(raw, dict):
        return f"item {index} is not an object"
    confidence = raw.get("confidence")
    if confidence is not None:
        try:
            conf_f = float(confidence)
        except (TypeError, ValueError):
            return f"item {index} confidence must be a number"
        if not 0.0 <= conf_f <= 1.0:
            return f"item {index} confidence {confidence!r} must be between 0 and 1"
    for f in ("target", "description"):
        val = raw.get(f)
        if val is not None and not isinstance(val, str):
            return f"item {index} field {f!r} must be a string"
    return None


def save_hypotheses(hypotheses_json: str, project_path: str, db_path: str | None = None) -> str:
    """Saves a list of follow-up hypotheses to the database.

    Args:
        hypotheses_json: A JSON string containing a list of hypothesis objects.
        project_path: The project root directory.
        db_path: Path to the SQLite database. Defaults to config value.

    Returns:
        A confirmation message.
    """
    try:
        data = json.loads(hypotheses_json)
        if not isinstance(data, list):
            data = [data]

        for i, item in enumerate(data):
            err = _validate_hypothesis(item, i)
            if err:
                return f"Error: invalid hypotheses JSON — {err}"

        db = get_database(db_path)
        count = 0
        for h in data:
            hypo = Hypothesis(
                type=TaskType.HUNT,
                target=h.get("target", ""),
                description=h.get("description", ""),
                confidence=h.get("confidence", 0.5),
            )
            db.save_hypothesis(project_path, hypo)
            count += 1
        return f"Saved {count} hypotheses."
    except Exception as e:
        return f"Error saving hypotheses: {str(e)}"
