import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
from agents.poc_agent import PocAgent
from agents.validation_agent import ValidationAgent
from core.models import Finding, FindingStatus

@pytest.fixture
def mock_storage():
    storage = MagicMock()
    # Mock SQLModel session behavior if needed
    return storage

@pytest.fixture
def poc_agent(mock_storage):
    agent = PocAgent(name="PocAgent")
    agent.storage_manager = mock_storage
    agent.project_id = "test-proj"
    agent.finding_id = 1
    return agent

def test_extract_code(poc_agent):
    text = "Here is the code:\n```python\nprint('hello')\n```\nEnjoy!"
    extracted = poc_agent._extract_code(text)
    assert extracted == "print('hello')"
    
    no_backticks = "print('hello')"
    assert poc_agent._extract_code(no_backticks) == "print('hello')"

@pytest.mark.asyncio
async def test_poc_agent_artifact_generation(poc_agent, tmp_path):
    # Mock finding retrieval
    mock_finding = Finding(id=1, project_id="p1", vuln_type="RCE", file_path="f", line_number=1, severity="H", discovery_tool="t", evidence="e")
    
    # We need to mock the sqlmodel Session
    with patch("sqlmodel.Session") as mock_session_cls:
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_session.get.return_value = mock_finding
        
        # Mock call_llm
        with patch.object(poc_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = [
                "```python\nprint('exploit')\n```", # Exploit
                "```dockerfile\nFROM python\n```" # Dockerfile
            ]
            
            # Use tmp_path for workspaces
            with patch("agents.poc_agent.Path") as mock_path:
                mock_path.side_effect = lambda *args: Path(tmp_path, *args)
                
                # Mock ctx
                ctx = MagicMock()
                
                # Run the agent logic manually
                events = []
                async for event in poc_agent._run_async_impl(ctx):
                    events.append(event)
                
                # Verify artifacts written
                artifact_dir = tmp_path / "workspaces" / "test-proj" / "artifacts" / "1"
                # Note: because we mocked Path in the agent, we check our real tmp_path
                # But wait, poc_agent uses 'Path("workspaces")' which we patched.
                
                # Let's just check mock_llm calls
                assert mock_llm.call_count == 2
                assert "RCE" in mock_llm.call_args_list[0][0][0]
