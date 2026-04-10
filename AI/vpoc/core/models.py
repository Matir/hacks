import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Finding(SQLModel, table=True):
    """Stores potential and validated security findings."""

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True)
    vuln_type: str = Field(index=True)
    file_path: str
    line_number: int
    severity: str
    status: str = Field(default="POTENTIAL", index=True)
    discovery_tool: str
    evidence: str
    llm_rationale: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class ExecutionLog(SQLModel, table=True):
    """Logs the results of PoC and validation executions."""

    id: Optional[int] = Field(default=None, primary_key=True)
    finding_id: int = Field(foreign_key="finding.id")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    docker_image_id: Optional[str] = None
    exploit_script_path: Optional[str] = None
    success: bool
    exit_code: Optional[int] = None
    output_log: Optional[str] = None


class TokenUsage(SQLModel, table=True):
    """Tracks LLM token usage for budgeting and cost control."""

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: str = Field(index=True)
    agent_name: str
    model: str
    tokens_in: int
    tokens_out: int
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
