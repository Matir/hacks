"""ADK SessionService management for TrashDig."""

from google.adk.sessions.sqlite_session_service import SqliteSessionService

_session_service: SqliteSessionService | None = None


def init_session_service(db_path: str) -> SqliteSessionService:
    """Initialises the global SqliteSessionService.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        The initialised SqliteSessionService.
    """
    global _session_service  # noqa: PLW0603
    _session_service = SqliteSessionService(db_path=db_path)
    return _session_service


def get_session_service() -> SqliteSessionService:
    """Returns the global SqliteSessionService instance.

    Raises:
        RuntimeError: If the service has not been initialised.
    """
    if _session_service is None:
        raise RuntimeError(
            "SessionService not initialised. Call init_session_service() first."
        )
    return _session_service
