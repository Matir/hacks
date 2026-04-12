import datetime
import typing
from pathlib import Path

from sqlmodel import Session, col, create_engine, select, SQLModel

from core.models import BudgetConfig, GlobalTokenUsage, Project, ProjectStatus, _utcnow


class GlobalStorageManager:
    """Manages the global database at ~/.vpoc/global.db.

    Contains: Project records, BudgetConfig, and GlobalTokenUsage.
    """

    def __init__(self, db_path: typing.Optional[str] = None) -> None:
        """
        Initializes the GlobalStorageManager.

        :param db_path: Path to the SQLite database file. Defaults to ~/.vpoc/global.db.
        """
        if db_path is None:
            base_dir = Path.home() / ".vpoc"
            base_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(base_dir / "global.db")

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
    # Projects
    # ------------------------------------------------------------------

    def create_project(self, project_id: str, name: str) -> Project:
        """Creates a new project record."""
        project = Project(
            project_id=project_id,
            name=name,
            status=ProjectStatus.INITIALIZING,
        )
        with Session(self.engine) as session:
            session.add(project)
            session.commit()
            session.refresh(project)
            return project

    def get_project(self, project_id: str) -> typing.Optional[Project]:
        """Retrieves a project by its project_id."""
        with Session(self.engine) as session:
            statement = select(Project).where(Project.project_id == project_id)
            return session.exec(statement).first()

    def get_all_projects(self) -> typing.List[Project]:
        """Retrieves all projects, ordered by created_at descending."""
        with Session(self.engine) as session:
            statement = select(Project).order_by(col(Project.created_at).desc())
            return list(session.exec(statement).all())

    def update_project_status(self, project_id: str, status: ProjectStatus) -> Project:
        """Updates a project's status and refreshes its updated_at timestamp."""
        with Session(self.engine) as session:
            project = session.exec(
                select(Project).where(Project.project_id == project_id)
            ).first()
            if project is None:
                raise ValueError(f"Project {project_id} not found.")
            project.status = status
            project.updated_at = _utcnow()
            session.add(project)
            session.commit()
            session.refresh(project)
            return project

    # ------------------------------------------------------------------
    # Budget configuration
    # ------------------------------------------------------------------

    def set_budget_limit(self, project_id: str, daily_limit: int) -> BudgetConfig:
        """Sets or updates the daily token budget for a project."""
        with Session(self.engine) as session:
            existing = session.exec(
                select(BudgetConfig).where(BudgetConfig.project_id == project_id)
            ).first()
            if existing:
                existing.daily_limit = daily_limit
                existing.updated_at = _utcnow()
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing
            else:
                config = BudgetConfig(project_id=project_id, daily_limit=daily_limit)
                session.add(config)
                session.commit()
                session.refresh(config)
                return config

    def get_budget_limit(self, project_id: str) -> typing.Optional[BudgetConfig]:
        """Retrieves the budget config for a project."""
        with Session(self.engine) as session:
            return session.exec(
                select(BudgetConfig).where(BudgetConfig.project_id == project_id)
            ).first()

    # ------------------------------------------------------------------
    # Token usage tracking
    # ------------------------------------------------------------------

    def track_token_usage(
        self,
        project_id: str,
        agent_name: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
    ) -> GlobalTokenUsage:
        """Records LLM token consumption for budgeting."""
        usage = GlobalTokenUsage(
            project_id=project_id,
            agent_name=agent_name,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
        with Session(self.engine) as session:
            session.add(usage)
            session.commit()
            session.refresh(usage)
            return usage

    def get_daily_token_usage(self, project_id: str) -> int:
        """Returns the total tokens used today for a project."""
        today_start = datetime.datetime.now(datetime.UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        with Session(self.engine) as session:
            statement = (
                select(GlobalTokenUsage)
                .where(GlobalTokenUsage.project_id == project_id)
                .where(GlobalTokenUsage.timestamp >= today_start)
            )
            usages = list(session.exec(statement).all())
            return sum(u.tokens_in + u.tokens_out for u in usages)
