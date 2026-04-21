import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class TaskType(Enum):
    """Enumeration of task types for agents."""
    SCAN = auto()           # StackScout mapping
    HUNT = auto()           # Hunter deep-dive
    VERIFY = auto()         # Validator PoC
    RESOLVE_SYMBOL = auto() # Follow definition
    TAINT_TRACE = auto()    # Follow variable

class TaskStatus(Enum):
    """Enumeration of possible task states."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()

class EngineState(Enum):
    """Enumeration of global engine states."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING_FOR_TOOLS = "WAITING_FOR_TOOLS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class Task:
    """A unit of work for an agent.

    Attributes:
        type: The type of task (SCAN, HUNT, etc.).
        target: The target file path or identifier for the task.
        context: A dictionary containing additional metadata or state for the task.
        task_id: A unique identifier for the task.
        status: The current status of the task execution.
        parent_id: Optional ID of the task that spawned this one.
        result: The result data generated after completion.
    """
    type: TaskType
    target: str
    context: dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    parent_id: str | None = None
    result: Any = None

@dataclass
class Hypothesis(Task):
    """A specific vulnerability hypothesis to be tested.

    Attributes:
        description: A text description of the potential vulnerability to hunt for.
        confidence: The agent's confidence level in this hypothesis (0.0 to 1.0).
    """
    description: str = ""
    confidence: float = 0.0 # 0.0 to 1.0
