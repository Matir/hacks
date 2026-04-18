"""Shared utilities for the TrashDig agents package.

This subpackage contains shared types, helpers, callbacks, and JSON utilities
used across agent definitions. It is NOT for defining agents — those live
directly under ``trashdig.agents``.

Submodules
----------
types
    Shared enumerations and dataclasses (TaskType, TaskStatus, EngineState,
    Task, Hypothesis).
helpers
    Agent creation helpers (google_provider_extras, load_prompt) and
    general-purpose utilities (get_project_structure, read_file_content,
    run_agent, log_auth_info).
callbacks
    ADK-native callback handler (TrashDigCallback) for TUI integration,
    token accounting, and DB persistence.
json_utils
    LLM response parsing helpers (parse_json_response, extract_json_list).
"""

from trashdig.agents.utils.callbacks import TrashDigCallback
from trashdig.agents.utils.helpers import (
    describe_provider_auth,
    detect_frameworks,
    get_project_structure,
    get_response_text,
    google_provider_extras,
    load_prompt,
    log_auth_info,
    read_file_content,
    run_agent,
)
from trashdig.agents.utils.json_utils import extract_json_list, parse_json_response
from trashdig.agents.utils.types import EngineState, Hypothesis, Task, TaskStatus, TaskType

__all__ = [
    "EngineState",
    "Hypothesis",
    "Task",
    "TaskStatus",
    "TaskType",
    "TrashDigCallback",
    "describe_provider_auth",
    "detect_frameworks",
    "extract_json_list",
    "get_project_structure",
    "get_response_text",
    "google_provider_extras",
    "load_prompt",
    "log_auth_info",
    "parse_json_response",
    "read_file_content",
    "run_agent",
]
