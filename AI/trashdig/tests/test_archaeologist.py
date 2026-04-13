from trashdig.agents.archaeologist import create_archaeologist_agent
from trashdig.config import AgentConfig
from google.adk.agents import LlmAgent

def test_create_archaeologist_agent():
    """Tests that the archaeologist agent is created correctly."""
    config = AgentConfig(model="test-model", provider="test-provider")
    agent = create_archaeologist_agent(config=config)
    assert isinstance(agent, LlmAgent)
    assert agent.name == "archaeologist"
    assert agent.model == "test-model"
    assert "Archaeologist Agent Prompt" in agent.instruction
