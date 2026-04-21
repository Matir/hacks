from unittest.mock import MagicMock

from google.adk.tools import ToolContext

from trashdig.tools.exit_loop import exit_loop


def test_exit_loop():
    mock_ctx = MagicMock(spec=ToolContext)
    mock_ctx.actions = MagicMock()
    res = exit_loop(mock_ctx)
    assert res == "Loop exit requested."
    assert mock_ctx.actions.escalate is True

def test_exit_loop_no_actions():
    # Should not crash if actions attribute is missing
    res = exit_loop(object())
    assert res == "Loop exit requested."
