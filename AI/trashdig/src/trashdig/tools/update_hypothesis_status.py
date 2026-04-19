from ..services.database import get_database


def update_hypothesis_status(task_id: str, status: str, db_path: str | None = None) -> str:
    """Updates the status of a hypothesis (e.g., to 'completed' or 'failed').

    Args:
        task_id: The unique ID of the hypothesis task.
        status: The new status (e.g., 'completed', 'failed').
        db_path: Path to the SQLite database. Defaults to config value.

    Returns:
        A confirmation message.
    """
    try:
        get_database(db_path).update_hypothesis_status(task_id, status)
        return f"Hypothesis {task_id} updated to {status}."
    except Exception as e:
        return f"Error updating database: {str(e)}"
