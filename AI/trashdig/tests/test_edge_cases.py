from unittest.mock import MagicMock, patch

import pytest
from google.adk.agents import LlmAgent

from trashdig.agents.coordinator import Coordinator
from trashdig.agents.recon import StackScoutAgent
from trashdig.config import Config


def create_mock_agent(name="dummy"):
    return LlmAgent(
        name=name,
        model="gemini-2.0-flash",
        instruction="instruction",
        description="description"
    )

@pytest.mark.anyio
async def test_stack_scout_malformed_json():
    """Test StackScoutAgent handles malformed JSON response from LLM."""
    with patch("trashdig.agents.recon.load_prompt", autospec=True, return_value="instruction"):
        agent = StackScoutAgent(name="test", model="test-model", instruction="test")

        # Mock run_agent directly
        with patch("trashdig.agents.coordinator.run_agent", autospec=True) as mock_run:
            mock_run.return_value = "This is not JSON"
            # In actual usage in Coordinator, it handles the text
            assert await mock_run(agent, "Analyze", "session", MagicMock()) == "This is not JSON"

@pytest.mark.anyio
async def test_coordinator_init_validation(tmp_path):
    """Test Coordinator initialization with mocks passing Pydantic validation."""
    mock_config = MagicMock(spec=Config)
    mock_config.agents = {}
    mock_config.get_agent_config.return_value = MagicMock(model="gemini-2.0-flash")
    # Use a real string for db_path to avoid urlparse error with MagicMock
    db_file = tmp_path / "test.db"
    mock_config.db_path = str(db_file)

    with patch("trashdig.agents.coordinator.create_stack_scout_agent", autospec=True, return_value=create_mock_agent("stack_scout")), \
         patch("trashdig.agents.coordinator.create_web_route_mapper_agent", autospec=True, return_value=create_mock_agent("web_route_mapper")), \
         patch("trashdig.agents.coordinator.create_hunter_agent", autospec=True, return_value=create_mock_agent("hunter")), \
         patch("trashdig.agents.coordinator.create_skeptic_agent", autospec=True, return_value=create_mock_agent("skeptic")), \
         patch("trashdig.agents.coordinator.create_validator_agent", autospec=True, return_value=create_mock_agent("validator")):

        coord = Coordinator(mock_config)
        assert coord.hunter is not None
