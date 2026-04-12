import datetime
import enum
import typing
from sqlmodel import SQLModel, Field


class FindingStatus(str, enum.Enum):
    """Lifecycle states for a security finding."""

    POTENTIAL = "POTENTIAL"
    SCREENED = "SCREENED"
    REJECTED = "REJECTED"
    POC_GENERATING = "POC_GENERATING"
    POC_READY = "POC_READY"
    POC_FAILED = "POC_FAILED"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    INCONCLUSIVE = "INCONCLUSIVE"
    AWAITING_HUMAN = "AWAITING_HUMAN"


class ProjectStatus(str, enum.Enum):
    """Status of a project in the global database."""

    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


# Fixed impact weight table used for priority score calculation.
# priority_score = IMPACT_WEIGHT[vuln_type] * llm_confidence + RECENCY_BONUS
IMPACT_WEIGHT: typing.Dict[str, int] = {
    "RCE": 100,
    "SQLi": 80,
    "SSRF": 70,
    "AuthBypass": 70,
    "XSS": 40,
    "InfoDisclosure": 20,
}

RECENCY_BONUS: int = 5


def _utcnow() -> datetime.datetime:
    """Returns the current UTC time as a timezone-aware datetime."""
    return datetime.datetime.now(datetime.UTC)


class Finding(SQLModel, table=True):
    """Stores potential and validated security findings."""

    id: typing.Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True)
    vuln_type: str = Field(index=True)
    file_path: str
    line_number: int
    severity: str
    status: FindingStatus = Field(default=FindingStatus.POTENTIAL, index=True)
    discovery_tool: str
    evidence: str
    llm_rationale: typing.Optional[str] = None
    priority_score: typing.Optional[float] = None
    llm_confidence: typing.Optional[float] = None
    cvss_score: typing.Optional[float] = None
    cvss_vector: typing.Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=_utcnow)
    updated_at: datetime.datetime = Field(default_factory=_utcnow)


class ExecutionLog(SQLModel, table=True):
    """Logs the results of PoC and validation executions."""

    id: typing.Optional[int] = Field(default=None, primary_key=True)
    finding_id: int = Field(foreign_key="finding.id")
    timestamp: datetime.datetime = Field(default_factory=_utcnow)
    docker_image_id: typing.Optional[str] = None
    exploit_script_path: typing.Optional[str] = None
    success: bool
    exit_code: typing.Optional[int] = None
    output_log: typing.Optional[str] = None


class AgentCheckpoint(SQLModel, table=True):
    """Stores per-agent resumption state for stateless re-entry after a crash.

    Source Review Agent uses one row per file per tool with
    stage="FILE_COMPLETE" and state_json containing file path, tool name,
    and any finding IDs produced.
    """

    id: typing.Optional[int] = Field(default=None, primary_key=True)
    agent_name: str = Field(index=True)
    finding_id: typing.Optional[int] = Field(
        default=None, foreign_key="finding.id", index=True
    )
    stage: str
    state_json: str  # JSON blob; schema is agent-specific
    updated_at: datetime.datetime = Field(default_factory=_utcnow)


class HintLog(SQLModel, table=True):
    """Persists user hints and quick-action commands for audit trail and resumption."""

    id: typing.Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True)
    event_type: str  # "hint" or "command"
    content: str  # Free-form hint text or command name
    args_json: typing.Optional[str] = None  # JSON-encoded args for commands
    timestamp: datetime.datetime = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Global storage models (stored in ~/.vpoc/global.db)
# ---------------------------------------------------------------------------


class Project(SQLModel, table=True):
    """Represents a security review project in the global database."""

    id: typing.Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True, unique=True)
    name: str
    status: ProjectStatus = Field(default=ProjectStatus.INITIALIZING, index=True)
    created_at: datetime.datetime = Field(default_factory=_utcnow)
    updated_at: datetime.datetime = Field(default_factory=_utcnow)


class BudgetConfig(SQLModel, table=True):
    """Stores the live daily token budget limit per project.

    Resets at midnight UTC. The live limit can be updated via UI
    without editing config files.
    """

    id: typing.Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True, unique=True)
    daily_limit: int  # Token count
    updated_at: datetime.datetime = Field(default_factory=_utcnow)


class GlobalTokenUsage(SQLModel, table=True):
    """Tracks LLM token usage across all projects for budgeting.

    Stored in global.db and queried by date for daily budget totals.
    """

    id: typing.Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True)
    agent_name: str
    model: str
    tokens_in: int
    tokens_out: int
    timestamp: datetime.datetime = Field(default_factory=_utcnow)
