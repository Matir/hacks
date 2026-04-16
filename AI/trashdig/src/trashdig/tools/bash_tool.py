from typing import List
from .base import artifact_tool, _run_sandboxed

@artifact_tool(max_chars=5000)
def bash_tool(command: str, timeout: int = 30) -> str:
    """Executes a bash command or script and returns the output.

    Args:
        command: The bash command to execute.
        timeout: Execution timeout in seconds.

    Returns:
        A formatted string containing stdout, stderr, and the exit code.
    """
    # Note: Bash commands need to be executed through a shell
    cmd = ["bash", "-c", command]
    try:
        # Defaults to network=False in run_sandboxed
        result = _run_sandboxed(cmd, timeout=timeout)
        output: List[str] = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        if not output:
            output.append(f"Command exited with code {result.returncode} (No output)")
        else:
            output.append(f"Exit Code: {result.returncode}")
        return "\n\n".join(output)
    except Exception as e:
        return f"Error executing command: {str(e)}"
