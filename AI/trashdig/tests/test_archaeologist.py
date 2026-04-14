import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.agents.archaeologist import ArchaeologistAgent, create_archaeologist_agent
from trashdig.config import AgentConfig
from google.adk.agents import LlmAgent


def test_create_archaeologist_agent():
    """Tests that the archaeologist agent is created correctly."""
    config = AgentConfig(model="test-model", provider="test-provider")
    with patch("trashdig.agents.archaeologist.load_prompt", return_value="Archaeologist Agent Prompt"):
        agent = create_archaeologist_agent(config=config)
        assert isinstance(agent, LlmAgent)
        assert agent.name == "archaeologist"
        assert agent.model == "test-model"
        assert "Archaeologist Agent Prompt" in agent.instruction


@pytest.mark.anyio
@patch("trashdig.agents.archaeologist.get_project_structure")
@patch("trashdig.agents.archaeologist.detect_frameworks")
@patch("trashdig.agents.archaeologist.run_prompt", new_callable=AsyncMock)
async def test_archaeologist_scan_project(mock_run_prompt, mock_detect, mock_get_struct):
    mock_get_struct.return_value = ["src/main.py", "README.md"]
    mock_detect.return_value = {"web_frameworks": ["fastapi"]}
    mock_run_prompt.return_value = (
        '```json\n'
        '{"mapping": {"src/main.py": {"summary": "Main entry point", "is_high_value": true}}, "hypotheses": []}\n'
        '```'
    )

    agent = ArchaeologistAgent(name="archaeologist", model="gemini-2.0-flash")
    result = await agent.scan_project(".")

    assert "mapping" in result
    assert "src/main.py" in result["mapping"]
    assert result["mapping"]["src/main.py"]["is_high_value"] is True
    mock_run_prompt.assert_called_once()


@pytest.mark.anyio
@patch("trashdig.agents.archaeologist.get_project_structure")
@patch("trashdig.agents.archaeologist.detect_frameworks")
@patch("trashdig.agents.archaeologist.run_prompt", new_callable=AsyncMock)
async def test_archaeologist_scan_project_json_error(mock_run_prompt, mock_detect, mock_get_struct):
    mock_get_struct.return_value = ["src/main.py"]
    mock_detect.return_value = {}
    mock_run_prompt.return_value = "Invalid JSON response"

    agent = ArchaeologistAgent(name="archaeologist", model="gemini-2.0-flash")
    result = await agent.scan_project(".")

    assert "error" in result
    assert "Failed to parse Archaeologist response" in result["error"]
    assert result["raw"] == "Invalid JSON response"
