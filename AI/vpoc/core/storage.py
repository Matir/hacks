import typing
from sqlmodel import Session, col, create_engine, select, SQLModel
from core.models import (
    AgentCheckpoint,
    ExecutionLog,
    Finding,
    FindingStatus,
    HintLog,
    ReconResult,
    _utcnow,
)


class StorageManager:
    """Manages persistence for a specific project workspace."""

    def __init__(self, db_path: str) -> None:
        """
        Initializes the StorageManager for a given project database.

        :param db_path: Path to the SQLite database file.
        """
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Creates tables if they do not exist and enables WAL mode."""
        SQLModel.metadata.create_all(self.engine)
        with self.engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")

    # ------------------------------------------------------------------
    # Findings
    # ------------------------------------------------------------------

    def add_finding(self, finding: Finding) -> Finding:
        """Adds a new finding or updates an existing one."""
        with Session(self.engine) as session:
            session.add(finding)
            session.commit()
            session.refresh(finding)
            return finding

    def get_findings_by_status(self, status: FindingStatus) -> typing.List[Finding]:
        """Retrieves all findings matching a specific status."""
        with Session(self.engine) as session:
            statement = select(Finding).where(Finding.status == status)
            return list(session.exec(statement).all())

    def update_finding_status(self, finding_id: int, status: FindingStatus) -> Finding:
        """Updates the status of a finding and refreshes its updated_at timestamp.

        :param finding_id: Primary key of the finding to update.
        :param status: The new status to apply.
        :raises ValueError: If no finding with the given ID exists.
        """
        with Session(self.engine) as session:
            finding = session.get(Finding, finding_id)
            if finding is None:
                raise ValueError(f"Finding {finding_id} not found.")
            finding.status = status
            finding.updated_at = _utcnow()
            session.add(finding)
            session.commit()
            session.refresh(finding)
            return finding

    # ------------------------------------------------------------------
    # Execution logs
    # ------------------------------------------------------------------

    def log_execution(self, log: ExecutionLog) -> ExecutionLog:
        """Persists a PoC execution result."""
        with Session(self.engine) as session:
            session.add(log)
            session.commit()
            session.refresh(log)
            return log

    # ------------------------------------------------------------------
    # Agent checkpoints
    # ------------------------------------------------------------------

    def save_checkpoint(self, checkpoint: AgentCheckpoint) -> AgentCheckpoint:
        """Persists or updates an agent checkpoint row."""
        with Session(self.engine) as session:
            checkpoint.updated_at = _utcnow()
            session.add(checkpoint)
            session.commit()
            session.refresh(checkpoint)
            return checkpoint

    def get_checkpoints(self, agent_name: str) -> typing.List[AgentCheckpoint]:
        """Returns all checkpoint rows for the given agent."""
        with Session(self.engine) as session:
            statement = select(AgentCheckpoint).where(
                AgentCheckpoint.agent_name == agent_name
            )
            return list(session.exec(statement).all())

    def clear_checkpoints(self, agent_name: str) -> None:
        """Removes all checkpoint rows for the given agent (e.g. on fresh start)."""
        with Session(self.engine) as session:
            statement = select(AgentCheckpoint).where(
                AgentCheckpoint.agent_name == agent_name
            )
            for row in session.exec(statement).all():
                session.delete(row)
            session.commit()

    # ------------------------------------------------------------------
    # Hint log
    # ------------------------------------------------------------------

    def add_hint(self, hint: HintLog) -> HintLog:
        """Persists a user hint or quick-action command."""
        with Session(self.engine) as session:
            session.add(hint)
            session.commit()
            session.refresh(hint)
            return hint

    def get_hints(self, project_id: str) -> typing.List[HintLog]:
        """Returns all hints and commands for the given project, oldest first."""
        with Session(self.engine) as session:
            statement = (
                select(HintLog)
                .where(HintLog.project_id == project_id)
                .order_by(col(HintLog.timestamp))
            )
            return list(session.exec(statement).all())

    # ------------------------------------------------------------------
    # Recon results
    # ------------------------------------------------------------------

    def add_recon_result(self, result: ReconResult) -> ReconResult:
        """Adds a new recon result to the project database."""
        with Session(self.engine) as session:
            session.add(result)
            session.commit()
            session.refresh(result)
            return result

    def get_recon_results(self, project_id: str) -> typing.List[ReconResult]:
        """Retrieves all recon results for the project."""
        with Session(self.engine) as session:
            statement = select(ReconResult).where(ReconResult.project_id == project_id)
            return list(session.exec(statement).all())
