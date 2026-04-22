from unittest.mock import MagicMock

import pytest
from google.adk.tools import FunctionTool

from trashdig.services.permissions import PermissionManager


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

def test_wrap_non_tool():
    pm = PermissionManager()
    not_a_tool = "string"
    assert pm.wrap_tool(not_a_tool) == "string"

def test_tool_decorator_sync():
    pm = PermissionManager()

    @pm.tool_decorator
    def my_tool(x: int = 1):
        return x

    assert my_tool(10) == 10
    assert my_tool() == 1

@pytest.mark.anyio
async def test_tool_decorator_async():
    pm = PermissionManager()

    @pm.tool_decorator
    async def my_tool(x: int = 1):
        return x

    assert await my_tool(10) == 10
    assert await my_tool() == 1

def test_tool_decorator_denied():
    mock_confirm = MagicMock(return_value=False)
    pm = PermissionManager(on_confirm=mock_confirm)
    pm.sensitive_tools.add("my_tool")

    @pm.tool_decorator
    def my_tool(command: str):
        return f"Running {command}"

    assert "Permission denied" in my_tool(command="ls")

def test_argument_binding_failure():
    # This covers the 'except TypeError' block in wrap_tool/tool_decorator
    pm = PermissionManager()

    def sync_tool(a, b):
        return a + b

    tool = FunctionTool(sync_tool)
    wrapped = pm.wrap_tool(tool)

    # Passing wrong number of arguments to trigger TypeError in bind()
    # But note that the wrapped function itself will still be called with these args
    # so we need to be careful. The bind() failure just falls back to tool_args = kwargs.
    with pytest.raises(TypeError):
        wrapped.func(1, 2, 3)
