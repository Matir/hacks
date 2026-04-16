from typing import Any


def exit_loop(tool_context: Any) -> str:
    """Exits the current autonomous loop. Call this when no more targets remain.

    Args:
        tool_context: The ADK ToolContext (injected automatically).

    Returns:
        A confirmation message.
    """
    # ADK uses 'escalate' to break out of a LoopAgent
    if hasattr(tool_context, "actions"):
        tool_context.actions.escalate = True
    return "Loop exit requested."
