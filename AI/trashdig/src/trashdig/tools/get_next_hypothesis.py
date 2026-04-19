import json
import sqlite3

from .base import get_config


def get_next_hypothesis(project_path: str, db_path: str | None = None) -> str:
    """Retrieves the next pending hypothesis from the database.

    Args:
        project_path: The root directory of the project.
        db_path: Path to the SQLite database. Defaults to config value.

    Returns:
        A JSON string containing the hypothesis details, or 'None' if no pending tasks.
    """
    if db_path is None:
        db_path = get_config().db_path
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM hypotheses WHERE project_path = ? AND status = 'pending' ORDER BY confidence DESC LIMIT 1",
                (project_path,)
            ).fetchone()

        if row:
            return json.dumps(dict(row))
        return "None"
    except Exception as e:
        return f"Error accessing database: {str(e)}"
