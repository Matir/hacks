import json

from ..agents.utils.types import Hypothesis, TaskType
from ..services.database import get_database


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
