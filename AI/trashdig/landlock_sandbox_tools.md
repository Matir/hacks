# Landlock Filesystem Sandbox for Python Tool Functions

## Problem

The existing `Sandbox` infrastructure (`MinijailSandbox`, `BxSandbox`) isolates **external subprocess commands**. Python-native tool functions (`read_file`, `list_files`, `find_files`, `get_ast_summary`, `ripgrep_search`, etc.) run directly in the main process with no filesystem restrictions. This design closes that gap.

---

## Scope

The following tools are targeted for wrapping:

- `read_file`
- `list_files`
- `find_files`
- `get_ast_summary`
- `ripgrep_search`
- `trace_variable_semantic`
- `trace_taint_cross_file`
- `get_scope_info`
- `get_symbol_definition`
- `find_references`
- `get_project_structure`

Tools that already delegate to `_run_sandboxed` (e.g. `bash_tool`, `semgrep_scan`) are excluded — the child process is already isolated by minijail/bx.

---

## Architecture

### Call Stack

```
@artifact_tool(max_chars=N)       ← outermost; has ToolContext, handles artifact saving
  @landlock_tool(timeout=30)      ← forks child, applies landlock, returns raw result
    def read_file(file_path: str) ← pure filesystem work in child; no ToolContext needed
```

`@landlock_tool` sits **inside** `@artifact_tool`. The child receives only picklable arguments (no `ToolContext`). The parent receives the raw result string and passes it up to `@artifact_tool` for truncation/artifact handling.

### Why this layering

`ToolContext` is a Google ADK object that cannot be pickled. It is only consumed by `@artifact_tool` (for `ctx.save_artifact()`), never by the tool function bodies themselves. Stripping it before forking is safe.

---

## Multiprocessing Model

### Fresh fork per call

A new child process is spawned for every tool invocation. There is no process pool. This gives strong isolation with no state leakage between calls and is compatible with landlock's irreversible `restrict_self()` semantics.

### Start method: `forkserver`

The main process is multithreaded (asyncio event loop, Textual TUI). Forking from a threaded process with `fork` risks deadlocks on mutexes held by other threads. Instead, `forkserver` is used:

- A clean forkserver process is started **after `load_config()` but before any threads are spawned** (before `asyncio.run()` / `app.run()`).
- All child processes are forked from the forkserver's clean, single-threaded state.
- The forkserver inherits the loaded config singleton, so `get_config()` works in children.

### Context initialization

Rather than using the global `multiprocessing.set_start_method()`, a module-level context object is used:

```python
# src/trashdig/sandbox/landlock_tool.py

import multiprocessing
_mp_context = multiprocessing.get_context('forkserver')  # default

def init_sandbox_mp_context(method: str = 'forkserver') -> None:
    """Call this once at startup before threads are spawned.

    In tests, call with method='spawn' to avoid requiring a live forkserver.
    """
    global _mp_context
    _mp_context = multiprocessing.get_context(method)
```

`main()` calls `init_sandbox_mp_context('forkserver')` immediately after `load_config()`.

#### Testing

A pytest fixture calls `init_sandbox_mp_context('spawn')` before any sandboxed test runs. `spawn` starts a fresh interpreter per call — slower, but correct and requiring no pre-initialized forkserver.

---

## IPC

Parent and child communicate over a `multiprocessing.Pipe` (a single-use connection pair, lower overhead than `Queue` for one-shot calls).

### Pipe deadlock avoidance

The parent must **not** call `child.join()` before draining the pipe. If the child writes a result larger than the OS pipe buffer (~64 KB on Linux), it will block waiting for the parent to read, while the parent blocks waiting for the child to exit — a deadlock. The fix: the parent reads from the pipe first, then joins.

```python
# parent side — read BEFORE join
if child_conn.poll(timeout=timeout):
    message = child_conn.recv()
else:
    child.kill()
    raise ToolTimeoutError(...)
child.join()
```

`poll(timeout)` blocks for at most `timeout` seconds waiting for data. If the child dies without writing (abnormal exit), `poll` returns `True` but `recv()` raises `EOFError` — the parent catches this and raises `SandboxError`.

### Message format

The child writes exactly one message:

```python
# success
conn.send(("ok", result))

# handled exception (e.g. PermissionError, FileNotFoundError)
conn.send(("err", exception, traceback_str))
```

If `exception` itself is not picklable (e.g. it holds a non-picklable object like a tree-sitter node), the child catches the pickle failure and sends a string fallback:

```python
try:
    conn.send(("err", exception, traceback_str))
except Exception:
    conn.send(("err", RuntimeError(f"{type(exception).__name__}: {exception}"), traceback_str))
```

### Parent handling

```python
tag, *payload = conn.recv()
if tag == "ok":
    return payload[0]
else:
    exc, tb_str = payload
    raise exc  # re-raises original exception, including PermissionError
    # tb_str is logged at DEBUG level for diagnostics
```

If the child terminates abnormally (non-zero `exitcode`, pipe raises `EOFError`), the parent raises `SandboxError` (see Error Handling below).

---

## Landlock Configuration

### Library

`python-landlock` is used. It handles:
- ABI version negotiation across kernel versions (landlock v1–v4)
- Graceful error on unsupported kernels
- Clean context manager API

Add to dependencies: `python-landlock`.

### Paths allowed in the child

| Path | Access |
|------|--------|
| `config.workspace_root` (only if `write=True`) | read_file + write_file + read_dir + make_dir + remove_dir + refer |
| `config.workspace_root` (default, `write=False`) | read_file + read_dir |
| each path in `extra_paths` (decorator arg) | read_file + read_dir |
| `sys.prefix`, `sys.exec_prefix` | read_file + read_dir |
| all entries in `sys.path` (at forkserver init time) | read_file + read_dir |
| `/proc/self` | read_file + read_dir |
| `/tmp` | read_file + write_file + read_dir + make_dir + remove_dir |
| `/dev` | read_file + read_dir (covers `/dev/null`, `/dev/urandom`, `/dev/random`) |

`sys.path` entries cover installed packages, the `.venv`, and the `src/` tree — necessary for any imports the tool function triggers in the child.

### `__pycache__` write suppression

Python attempts to write `.pyc` files to `__pycache__` directories on first import. Since `sys.path` entries are read-only, this would produce a `PermissionError` for any module imported lazily in the child (i.e., not already imported in the forkserver). To prevent this, the child sets:

```python
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
```

This must be set **before landlock is applied** (environment mutation is not a filesystem operation and is not affected by landlock).

### Kernel support policy

- **Linux, kernel ≥ 5.13 (landlock v1+)**: landlock applied; hard failure if `restrict_self()` fails.
- **Linux, old kernel**: raise `RuntimeError` unless `config.require_sandbox` is `False`, in which case log a warning and proceed unsandboxed.
- **Non-Linux (macOS, etc.)**: skip landlock silently, proceed unsandboxed.
  - `# TODO: find a filesystem sandboxing solution for non-Linux platforms`

---

## Decorator API

```python
@artifact_tool(max_chars=4000)
@landlock_tool(extra_paths=[], timeout=30)
def read_file(file_path: str, tool_context: Any = None) -> str:
    ...
```

### Signature

```python
def landlock_tool(
    extra_paths: list[str] | None = None,
    timeout: int = 30,
    write: bool = False,
) -> Callable:
    ...
```

- `extra_paths`: additional read-only paths beyond the workspace and Python runtime. Declared at definition time. Defaults to `[]`.
- `timeout`: per-call timeout in seconds. Defaults to 30.
- `write`: if `True`, grants read+write access to `workspace_root`. Defaults to `False` (read-only). Most filesystem tools only need to read; set `write=True` only for tools that explicitly modify the workspace.
- `workspace_dir`: always sourced from `get_config().workspace_root` at call time inside the child.

### Async

Only synchronous tool functions are supported. Applying `@landlock_tool` to a coroutine function raises `TypeError` at decoration time.

```
# TODO: support async tools via loop.run_in_executor() for non-blocking fork+join
```

### ToolContext stripping

`tool_context` and `ctx` kwargs are removed from the kwargs dict before the arguments are sent to the child. This is safe because none of the targeted tool functions use `tool_context` in their bodies.

---

## Error Handling

### Exception classes

```python
class SandboxError(RuntimeError):
    """Raised when the child process terminates abnormally."""
    def __init__(self, func_name: str, exitcode: int, stderr: str = ""):
        msg = f"{func_name} sandbox child exited with code {exitcode}"
        if stderr:
            msg += f"\n{stderr}"
        super().__init__(msg)
```

### Scenarios

| Scenario | Behaviour |
|----------|-----------|
| Tool raises `PermissionError` (landlock violation) | Re-raised as-is in parent |
| Tool raises any other exception | Re-raised as-is in parent |
| Child timeout | Child killed; `ToolTimeoutError` raised (subclass of `SandboxError`) |
| Child killed (OOM, signal) | `SandboxError(exitcode=-N, stderr=...)` raised |
| Child exits non-zero, pipe has data | Exception from pipe re-raised normally |
| Child exits non-zero, pipe empty | `SandboxError` with exitcode and any stderr captured |

---

## Child Process Execution Flow

```
1. child starts (forked from forkserver)
2. set PYTHONDONTWRITEBYTECODE=1 (before landlock, env mutation is not a FS op)
3. apply landlock ruleset via python-landlock
   - on failure: write ("err", RuntimeError(...), tb) to pipe and exit(1)
4. call func(*args, **kwargs_without_tool_context)
5. write ("ok", result) or ("err", exception, tb) to pipe
   - if exception is not picklable, send RuntimeError(str(exception)) fallback
6. exit(0)
```

---

## Parent Process Execution Flow

```
1. strip tool_context/ctx from kwargs
2. parent_conn, child_conn = _mp_context.Pipe(duplex=False)
3. spawn child via _mp_context.Process(target=_child_main, args=(...))
4. child.start()
5. child_conn.close()  # parent closes its write end immediately
6. if not parent_conn.poll(timeout=timeout):
     child.kill(); child.join(); raise ToolTimeoutError(...)
7. try:
     tag, *payload = parent_conn.recv()
   except EOFError:
     child.join()
     raise SandboxError(func.__name__, child.exitcode)
8. child.join()
9. if tag == "ok": return payload[0]
   else:
     exc, tb_str = payload
     log.debug("sandbox child traceback:\n%s", tb_str)
     raise exc
```

Reading from the pipe (step 6–7) happens **before** `child.join()` (step 8) to avoid the pipe buffer deadlock. `poll(timeout)` acts as the effective timeout gate.

---

## Integration Points

### `main.py`

```python
config = load_config(...)
from trashdig.sandbox.landlock_tool import init_sandbox_mp_context
init_sandbox_mp_context('forkserver')
# ... then asyncio.run() / app.run()
```

### Tool definitions

Replace the current pattern:

```python
@artifact_tool(max_chars=4000)
def read_file(file_path: str, tool_context: Any = None) -> str:
```

With:

```python
@artifact_tool(max_chars=4000)
@landlock_tool()          # read-only workspace access by default
def read_file(file_path: str, tool_context: Any = None) -> str:
```

Tools that write to the workspace (e.g. `save_findings`) use:

```python
@landlock_tool(write=True)
def some_writing_tool(...) -> str:
```

No changes to tool function bodies are required.

### `sandbox/__init__.py`

Export `landlock_tool` and `init_sandbox_mp_context` from the sandbox package.

---

## File Layout

```
src/trashdig/sandbox/
    __init__.py          ← add landlock_tool, init_sandbox_mp_context exports
    base.py              ← unchanged
    landlock_tool.py     ← new: decorator, child runner, mp context init
    minijail.py          ← unchanged
    bx.py                ← unchanged
    null.py              ← unchanged
```

---

## Open Questions / Future Work

- `# TODO: find a filesystem sandboxing solution for non-Linux platforms (macOS Sandbox profiles? pledge?)`
- `# TODO: support async tools via loop.run_in_executor() for non-blocking fork+join`
