from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any, Optional
import uuid

class TaskType(Enum):
    SCAN = auto()           # Archaeologist mapping
    HUNT = auto()           # Hunter deep-dive
    VERIFY = auto()         # Validator PoC
    RESOLVE_SYMBOL = auto() # Follow definition
    TAINT_TRACE = auto()    # Follow variable

class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()

@dataclass
class Task:
    """A unit of work for an agent."""
    type: TaskType
    target: str
    context: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    parent_id: Optional[str] = None
    result: Any = None

@dataclass
class Hypothesis(Task):
    """A specific vulnerability hypothesis to be tested."""
    description: str = ""
    confidence: float = 0.0 # 0.0 to 1.0
