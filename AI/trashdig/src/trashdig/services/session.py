"""ADK SessionService management for TrashDig."""

from google.adk.sessions.sqlite_session_service import SqliteSessionService


class SessionProvider:
    """Class-level provider for the global SessionService instance."""
    instance: SqliteSessionService | None = None


def init_session_service(db_path: str) -> SqliteSessionService:
    """Initialises the global SqliteSessionService.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        The initialised SqliteSessionService.
    """
    SessionProvider.instance = SqliteSessionService(db_path=db_path)
    return SessionProvider.instance


def get_session_service() -> SqliteSessionService:
    """Returns the global SqliteSessionService instance.

    Raises:
        RuntimeError: If the service has not been initialised.
    """
    if SessionProvider.instance is None:
        raise RuntimeError(
            "SessionService not initialised. Call init_session_service() first."
        )
    return SessionProvider.instance
