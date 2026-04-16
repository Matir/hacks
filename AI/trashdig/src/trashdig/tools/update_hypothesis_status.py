import sqlite3
from datetime import datetime
from typing import Optional

from .base import get_config


def update_hypothesis_status(task_id: str, status: str, db_path: Optional[str] = None) -> str:
    """Updates the status of a hypothesis (e.g., to 'completed' or 'failed').

    Args:
        task_id: The unique ID of the hypothesis task.
        status: The new status (e.g., 'completed', 'failed').
        db_path: Path to the SQLite database. Defaults to config value.

    Returns:
        A confirmation message.
    """
    if db_path is None:
        db_path = get_config().db_path
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE hypotheses SET status = ?, updated_at = ? WHERE task_id = ?",
            (status, datetime.now().isoformat(), task_id)
        )
        conn.commit()
        conn.close()
        return f"Hypothesis {task_id} updated to {status}."
    except Exception as e:
        return f"Error updating database: {str(e)}"
