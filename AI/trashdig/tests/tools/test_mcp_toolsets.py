from unittest.mock import MagicMock, patch

import pytest

from trashdig.config import Config, McpServerConfig
from trashdig.tools.mcp_toolsets import _toolset_from_config, build_mcp_toolsets


@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    srv1 = McpServerConfig(
        name="server1",
        transport="stdio",
        command="python",
        args=["-m", "mcp_server"],
        agents=["agent1"]
    )
    srv2 = McpServerConfig(
        name="server2",
        transport="sse",
        url="http://localhost:8000/sse",
        agents=[]
    )
    config.mcp_servers = [srv1, srv2]
    return config

def test_build_mcp_toolsets(mock_config):
    with patch("trashdig.tools.mcp_toolsets.McpToolset") as mock_toolset:
        toolsets = build_mcp_toolsets(mock_config, "agent1")
        assert len(toolsets) == 2

        toolsets = build_mcp_toolsets(mock_config, "agent2")
        assert len(toolsets) == 1
        assert toolsets[0] == mock_toolset.return_value

def test_toolset_from_config_stdio():
    srv = McpServerConfig(
        name="test",
        transport="stdio",
        command="cmd"
    )
    with patch("trashdig.tools.mcp_toolsets.McpToolset") as mock_toolset, \
         patch("trashdig.tools.mcp_toolsets.StdioConnectionParams") as mock_params:
        result = _toolset_from_config(srv)
        assert result is not None
        mock_params.assert_called_once()

def test_toolset_from_config_sse():
    srv = McpServerConfig(
        name="test",
        transport="sse",
        url="http://url"
    )
    with patch("trashdig.tools.mcp_toolsets.McpToolset") as mock_toolset, \
         patch("trashdig.tools.mcp_toolsets.SseConnectionParams") as mock_params:
        result = _toolset_from_config(srv)
        assert result is not None
        mock_params.assert_called_once()

def test_toolset_from_config_http():
    srv = McpServerConfig(
        name="test",
        transport="http",
        url="http://url"
    )
    with patch("trashdig.tools.mcp_toolsets.McpToolset") as mock_toolset, \
         patch("trashdig.tools.mcp_toolsets.StreamableHTTPConnectionParams") as mock_params:
        result = _toolset_from_config(srv)
        assert result is not None
        mock_params.assert_called_once()

def test_toolset_from_config_invalid():
    srv = McpServerConfig(name="test", transport="unknown")
    assert _toolset_from_config(srv) is None

    srv = McpServerConfig(name="test", transport="stdio") # Missing command
    assert _toolset_from_config(srv) is None

    srv = McpServerConfig(name="test", transport="sse") # Missing url
    assert _toolset_from_config(srv) is None

def test_toolset_from_config_exception():
    srv = McpServerConfig(name="test", transport="stdio", command="cmd")
    with patch("trashdig.tools.mcp_toolsets.McpToolset", side_effect=Exception("fail")):
        assert _toolset_from_config(srv) is None
