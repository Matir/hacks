import pytest
from unittest.mock import MagicMock, patch
from trashdig.services.permissions import PermissionManager
from google.adk.tools import FunctionTool
from trashdig.config import Config

def test_permission_manager_allowed_by_default():
    pm = PermissionManager()
    assert pm.is_allowed("some_tool", {"arg1": "val1"}) is True

def test_permission_manager_sensitive_tool_no_callback():
    pm = PermissionManager()
    # bash_tool is sensitive
    assert pm.is_allowed("bash_tool", {"command": "ls"}) is True

def test_permission_manager_sensitive_tool_with_callback_allow():
    mock_confirm = MagicMock(return_value=True)
    pm = PermissionManager(on_confirm=mock_confirm)
    assert pm.is_allowed("bash_tool", {"command": "ls"}) is True
    mock_confirm.assert_called_once_with("bash_tool", {"command": "ls"})

def test_permission_manager_sensitive_tool_with_callback_deny():
    mock_confirm = MagicMock(return_value=False)
    pm = PermissionManager(on_confirm=mock_confirm)
    assert pm.is_allowed("bash_tool", {"command": "ls"}) is False
    mock_confirm.assert_called_once_with("bash_tool", {"command": "ls"})

def test_wrap_tool_sync():
    def sync_tool(name: str):
        return f"Hello {name}"
    
    pm = PermissionManager()
    tool = FunctionTool(sync_tool)
    wrapped_tool = pm.wrap_tool(tool)
    
    assert wrapped_tool.name == "sync_tool"
    assert wrapped_tool.func("world") == "Hello world"

def test_wrap_tool_sync_denied():
    def sync_tool(command: str):
        return f"Running {command}"
    
    mock_confirm = MagicMock(return_value=False)
    pm = PermissionManager(on_confirm=mock_confirm)
    pm.sensitive_tools.add("sync_tool") # Force it to be sensitive for test
    
    tool = FunctionTool(sync_tool)
    wrapped_tool = pm.wrap_tool(tool)
    
    result = wrapped_tool.func(command="ls")
    assert "Permission denied" in result
    mock_confirm.assert_called_once()

@pytest.mark.anyio
async def test_wrap_tool_async():
    async def async_tool(name: str):
        return f"Hello {name}"
    
    pm = PermissionManager()
    tool = FunctionTool(async_tool)
    wrapped_tool = pm.wrap_tool(tool)
    
    assert wrapped_tool.name == "async_tool"
    result = await wrapped_tool.func("world")
    assert result == "Hello world"

@pytest.mark.anyio
async def test_wrap_tool_async_denied():
    async def async_tool(command: str):
        return f"Running {command}"
    
    mock_confirm = MagicMock(return_value=False)
    pm = PermissionManager(on_confirm=mock_confirm)
    pm.sensitive_tools.add("async_tool")
    
    tool = FunctionTool(async_tool)
    wrapped_tool = pm.wrap_tool(tool)
    
    result = await wrapped_tool.func(command="ls")
    assert "Permission denied" in result
    mock_confirm.assert_called_once()

def test_wrap_tools():
    def tool1(): return "1"
    def tool2(): return "2"
    
    pm = PermissionManager()
    tools = [FunctionTool(tool1), FunctionTool(tool2)]
    wrapped_tools = pm.wrap_tools(tools)
    
    assert len(wrapped_tools) == 2
    assert wrapped_tools[0].func() == "1"
    assert wrapped_tools[1].func() == "2"
