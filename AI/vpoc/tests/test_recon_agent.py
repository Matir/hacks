import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
from agents.recon_agent import ReconAgent
from core.models import ReconResult

@pytest.fixture
def recon_agent():
    agent = ReconAgent(name="ReconAgent")
    agent.storage_manager = MagicMock()
    agent.project_id = "test-proj"
    return agent

@pytest.mark.asyncio
async def test_recon_agent_mapping(recon_agent, tmp_path):
    # Setup mock source dir
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "routes.rb").write_text("get '/login'")
    
    with patch("agents.recon_agent.Path") as mock_path:
        mock_path.side_effect = lambda *args: Path(tmp_path, *args)
        
        with patch.object(recon_agent, "call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = json.dumps({
                "entry_points": [{"path": "/login", "method": "GET", "priority": "HIGH"}],
                "high_value_files": ["app/controllers/auth.rb"]
            })
            
            ctx = MagicMock()
            async for event in recon_agent._run_async_impl(ctx):
                pass
            
            # Verify results added to storage
            assert recon_agent.storage_manager.add_recon_result.call_count >= 2
            calls = recon_agent.storage_manager.add_recon_result.call_args_list
            # Entry point
            assert any(c[0][0].result_type == "ENTRY_POINT" for c in calls)
            # High value file
            assert any(c[0][0].result_type == "HIGH_VALUE_FILE" for c in calls)
