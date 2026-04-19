"""Factory for building ADK McpToolset instances from TrashDig config."""

import logging

from google.adk.tools.mcp_tool.mcp_session_manager import (
    SseConnectionParams,
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

from trashdig.config import Config, McpServerConfig

logger = logging.getLogger(__name__)


def build_mcp_toolsets(config: Config, agent_name: str) -> list[McpToolset]:
    """Return McpToolset instances for MCP servers scoped to *agent_name*.

    Servers whose ``agents`` list is empty are given to all agents.  Servers
    that list specific agent names are only given to those agents.
    """
    toolsets = []
    for srv in config.mcp_servers:
        if srv.agents and agent_name not in srv.agents:
            continue
        toolset = _toolset_from_config(srv)
        if toolset is not None:
            toolsets.append(toolset)
    return toolsets


def _toolset_from_config(srv: McpServerConfig) -> McpToolset | None:
    tool_filter: list[str] | None = srv.tool_filter or None

    try:
        if srv.transport == "stdio":
            if not srv.command:
                logger.error("MCP server %r: stdio transport requires 'command'", srv.name)
                return None
            connection_params = StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=srv.command,
                    args=srv.args or [],
                    env=srv.env or None,
                ),
                timeout=srv.timeout if srv.timeout is not None else 5.0,
            )

        elif srv.transport == "sse":
            if not srv.url:
                logger.error("MCP server %r: sse transport requires 'url'", srv.name)
                return None
            connection_params = SseConnectionParams(
                url=srv.url,
                timeout=srv.timeout if srv.timeout is not None else 5.0,
            )

        elif srv.transport == "http":
            if not srv.url:
                logger.error("MCP server %r: http transport requires 'url'", srv.name)
                return None
            connection_params = StreamableHTTPConnectionParams(
                url=srv.url,
                timeout=srv.timeout if srv.timeout is not None else 5.0,
            )

        else:
            logger.error("MCP server %r: unknown transport %r", srv.name, srv.transport)
            return None

        return McpToolset(
            connection_params=connection_params,
            tool_filter=tool_filter,
            tool_name_prefix=f"mcp_{srv.name}_",
        )

    except Exception:
        logger.exception("Failed to build McpToolset for server %r", srv.name)
        return None
