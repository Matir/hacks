"""Tests for the landlock_tool sandbox decorator.

Module-level functions and decorated helpers below are picklable and safe to
send across processes with the ``spawn`` start method.  Functions defined
inside test methods are NOT picklable, so all subprocess-path tests use the
pre-decorated module-level helpers defined here.
"""

import sys
import time
from unittest.mock import MagicMock, patch

import pytest

import trashdig.sandbox.landlock_tool  # noqa: F401  # ensure submodule is in sys.modules
from trashdig.sandbox.landlock_tool import (
    SandboxError,
    ToolTimeoutError,
    init_sandbox_mp_context,
    landlock_tool,
)

# ---------------------------------------------------------------------------
# Module-level picklable helpers used by subprocess tests.
#
# Functions are decorated with @landlock_tool() here rather than inside test
# methods so that the underlying *func* passed to the child is a module-level
# object and therefore picklable by the ``spawn`` start method.
# get_config() is not called at decoration time — only when the wrapper is
# invoked — so mock patches applied in test bodies are in effect.
# ---------------------------------------------------------------------------


@landlock_tool()
def _sandboxed_string() -> str:
    """Return a fixed greeting — verifies a basic IPC round-trip."""
    return "hello from child"


@landlock_tool()
def _sandboxed_add(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b


@landlock_tool()
def _sandboxed_raises() -> None:
    """Raise ValueError — verifies exception propagation from child to parent."""
    raise ValueError("boom from child")


@landlock_tool()
def _sandboxed_check_tool_context(tool_context: object = None) -> str:
    """Return whether tool_context was passed into the child."""
    return "absent" if tool_context is None else "present"


@landlock_tool()
def _sandboxed_check_ctx(ctx: object = None) -> str:
    """Return whether ctx was passed into the child."""
    return "absent" if ctx is None else "present"


@landlock_tool(timeout=1)
def _sandboxed_sleeper() -> str:
    """Sleep for five minutes — triggers ToolTimeoutError."""
    time.sleep(300)
    return "never"


@landlock_tool()
def _sandboxed_greet(name: str = "World") -> str:
    """Return a greeting — verifies keyword-argument forwarding."""
    return f"Hello, {name}!"


@landlock_tool()
def _sandboxed_unpicklable() -> object:
    """Return a generator — verifies the non-picklable str() fallback path."""
    return (x for x in range(3))  # generators are not picklable


def _get_lt_module() -> object:
    """Return the actual landlock_tool module from sys.modules.

    A direct ``import trashdig.sandbox.landlock_tool as m`` resolves to the
    *function* ``landlock_tool`` re-exported from the ``trashdig.sandbox``
    package ``__init__``, not the submodule.  Using ``sys.modules`` bypasses
    that attribute-lookup shadow and always returns the module object.
    """
    return sys.modules["trashdig.sandbox.landlock_tool"]


# ---------------------------------------------------------------------------
# Exception class tests
# ---------------------------------------------------------------------------


class TestSandboxError:
    def test_message_without_stderr(self):
        err = SandboxError("my_func", 1)
        assert "my_func" in str(err)
        assert "code 1" in str(err)

    def test_message_with_stderr(self):
        err = SandboxError("my_func", -9, "OOM killer")
        assert "OOM killer" in str(err)

    def test_is_runtime_error(self):
        assert isinstance(SandboxError("f", 1), RuntimeError)


class TestToolTimeoutError:
    def test_message_contains_timeout(self):
        err = ToolTimeoutError("slow_func", 30)
        assert "slow_func" in str(err)
        assert "30s" in str(err)

    def test_is_sandbox_error(self):
        assert isinstance(ToolTimeoutError("f", 5), SandboxError)

    def test_timeout_attribute(self):
        err = ToolTimeoutError("f", 42)
        assert err.timeout == 42


# ---------------------------------------------------------------------------
# init_sandbox_mp_context
# ---------------------------------------------------------------------------


class TestInitSandboxMpContext:
    def test_updates_context(self):
        lt = _get_lt_module()
        init_sandbox_mp_context("spawn")
        assert lt._mp_context.get_start_method() == "spawn"  # type: ignore[union-attr]

    def test_updates_sys_path_snapshot(self):
        lt = _get_lt_module()
        init_sandbox_mp_context("spawn")
        assert lt._sys_path_snapshot == list(sys.path)  # type: ignore[union-attr]

    def test_restores_spawn_for_remaining_tests(self):
        """Leave the context as 'spawn' so subsequent subprocess tests work."""
        init_sandbox_mp_context("spawn")


# ---------------------------------------------------------------------------
# Decorator validation (no subprocess involved)
# ---------------------------------------------------------------------------


class TestLandlockToolDecorator:
    def test_raises_typeerror_on_coroutine(self):
        with pytest.raises(TypeError, match="coroutine"):

            @landlock_tool()
            async def bad():
                pass

    def test_preserves_function_name(self):
        @landlock_tool()
        def my_tool() -> str:
            return "x"

        assert my_tool.__name__ == "my_tool"

    def test_preserves_docstring(self):
        @landlock_tool()
        def documented() -> str:
            """My doc."""
            return "x"

        assert documented.__doc__ == "My doc."

    def test_skip_sandbox_env_calls_directly(self, monkeypatch):
        monkeypatch.setenv("TRASHDIG_SKIP_SANDBOX", "1")
        called_with: list[tuple] = []

        @landlock_tool()
        def capture(*args, **kwargs) -> str:
            called_with.append((args, kwargs))
            return "direct"

        result = capture("a", b=2)
        assert result == "direct"
        assert called_with == [(("a",), {"b": 2})]

    def test_skip_sandbox_passes_tool_context_through(self, monkeypatch):
        """When skipping, tool_context is forwarded as-is to the function."""
        monkeypatch.setenv("TRASHDIG_SKIP_SANDBOX", "1")
        ctx = MagicMock()

        @landlock_tool()
        def tool_with_ctx(tool_context=None) -> str:
            return "ctx_present" if tool_context is not None else "no_ctx"

        assert tool_with_ctx(tool_context=ctx) == "ctx_present"


# ---------------------------------------------------------------------------
# Subprocess execution tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def no_skip_sandbox(monkeypatch):
    """Remove TRASHDIG_SKIP_SANDBOX so @landlock_tool spawns a real child."""
    monkeypatch.delenv("TRASHDIG_SKIP_SANDBOX", raising=False)


@pytest.fixture()
def mock_config(tmp_path):
    """Provide a minimal Config mock whose workspace_root is a temp directory."""
    cfg = MagicMock()
    cfg.workspace_root = str(tmp_path)
    cfg.data = {"require_sandbox": False}
    return cfg


class TestSubprocessExecution:
    def test_returns_string_result(self, no_skip_sandbox, mock_config):
        with patch("trashdig.sandbox.landlock_tool.get_config", return_value=mock_config):
            assert _sandboxed_string() == "hello from child"

    def test_returns_integer_result(self, no_skip_sandbox, mock_config):
        with patch("trashdig.sandbox.landlock_tool.get_config", return_value=mock_config):
            assert _sandboxed_add(3, 4) == 7

    def test_exception_propagates_to_parent(self, no_skip_sandbox, mock_config):
        with patch("trashdig.sandbox.landlock_tool.get_config", return_value=mock_config):
            with pytest.raises(ValueError, match="boom from child"):
                _sandboxed_raises()

    def test_tool_context_kwarg_is_stripped(self, no_skip_sandbox, mock_config):
        """tool_context must not be forwarded to the child (not picklable)."""
        with patch("trashdig.sandbox.landlock_tool.get_config", return_value=mock_config):
            ctx = MagicMock()
            assert _sandboxed_check_tool_context(tool_context=ctx) == "absent"

    def test_ctx_kwarg_is_stripped(self, no_skip_sandbox, mock_config):
        """The ``ctx`` shorthand alias is also stripped."""
        with patch("trashdig.sandbox.landlock_tool.get_config", return_value=mock_config):
            ctx = MagicMock()
            assert _sandboxed_check_ctx(ctx=ctx) == "absent"

    def test_timeout_raises_tool_timeout_error(self, no_skip_sandbox, mock_config):
        with patch("trashdig.sandbox.landlock_tool.get_config", return_value=mock_config):
            with pytest.raises(ToolTimeoutError):
                _sandboxed_sleeper()

    def test_positional_args_forwarded(self, no_skip_sandbox, mock_config):
        with patch("trashdig.sandbox.landlock_tool.get_config", return_value=mock_config):
            assert _sandboxed_add(10, 20) == 30

    def test_keyword_args_forwarded(self, no_skip_sandbox, mock_config):
        with patch("trashdig.sandbox.landlock_tool.get_config", return_value=mock_config):
            assert _sandboxed_greet(name="pytest") == "Hello, pytest!"


# ---------------------------------------------------------------------------
# Child process environment tests
# ---------------------------------------------------------------------------


class TestChildEnvironment:
    def test_non_picklable_result_falls_back_to_str(self, no_skip_sandbox, mock_config):
        """If result is not picklable, child sends its str() representation."""
        with patch("trashdig.sandbox.landlock_tool.get_config", return_value=mock_config):
            result = _sandboxed_unpicklable()
            # The fallback sends str(generator), which contains "generator"
            assert isinstance(result, str)
            assert "generator" in result
