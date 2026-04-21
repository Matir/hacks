from unittest.mock import patch

from trashdig.agents.code_investigator import CodeInvestigatorAgent, create_code_investigator_agent
from trashdig.config import AgentConfig


@patch("trashdig.agents.code_investigator.load_prompt", autospec=True)
@patch("google.adk.agents.LlmAgent.__init__", autospec=True)
def test_create_code_investigator_agent(mock_init, mock_load):
    """Verifies that the Code Investigator agent is created with the expected config."""
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model", provider="google")
    agent = create_code_investigator_agent(config)

    assert agent is not None
    # The actual tool checks are handled by test_agent_tools.py,
    # but we can verify the agent's identity here.
    assert isinstance(agent, CodeInvestigatorAgent)


def test_code_investigator_tool_composition():
    """Verifies that create_code_investigator_agent assembles the expected tools."""
    # We use a real-ish config but patch load_prompt
    with patch("trashdig.agents.code_investigator.load_prompt", return_value="instruction"):
        agent = create_code_investigator_agent()

    # Check for core analysis tools
    tool_names = {getattr(t, "name", str(t)) for t in agent.tools}

    expected_subset = {
        "ripgrep_search",
        "read_file",
        "get_ast_summary",
        "trace_taint_cross_file",
        "get_symbol_definition",
        "get_project_structure"
    }

    for tool in expected_subset:
        assert tool in tool_names
