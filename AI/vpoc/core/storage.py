from typing import List
from sqlmodel import Session, create_engine, select, SQLModel
from core.models import Finding, ExecutionLog, TokenUsage


class StorageManager:
    """Manages persistence for a specific project workspace."""

    def __init__(self, db_path: str):
        """
        Initializes the StorageManager for a given project database.

        :param db_path: Path to the SQLite database file.
        """
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},  # Safe for SQLite with threading
        )
        self._initialize_database()

    def _initialize_database(self):
        """Creates tables if they do not exist and enables WAL mode."""
        SQLModel.metadata.create_all(self.engine)
        # Enable Write-Ahead Logging for better concurrency
        with self.engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")

    def add_finding(self, finding: Finding) -> Finding:
        """Adds a new finding or updates an existing one."""
        with Session(self.engine) as session:
            session.add(finding)
            session.commit()
            session.refresh(finding)
            return finding

    def get_findings_by_status(self, status: str) -> List[Finding]:
        """Retrieves all findings matching a specific status."""
        with Session(self.engine) as session:
            statement = select(Finding).where(Finding.status == status)
            return list(session.exec(statement).all())

    def log_execution(self, log: ExecutionLog) -> ExecutionLog:
        """Persists a PoC execution result."""
        with Session(self.engine) as session:
            session.add(log)
            session.commit()
            session.refresh(log)
            return log

    def track_token_usage(self, usage: TokenUsage) -> TokenUsage:
        """Records LLM token consumption for budgeting."""
        with Session(self.engine) as session:
            session.add(usage)
            session.commit()
            session.refresh(usage)
            return usage
