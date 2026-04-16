import os
import subprocess
from typing import List
from .base import artifact_tool
from .bash_tool import bash_tool

@artifact_tool(max_chars=5000)
def container_bash_tool(command: str, image: str = "python:3.11-slim", timeout: int = 60) -> str:
    """Executes a bash command or script inside a temporary Docker container.
    This provides an isolated environment for running Proof of Concepts.

    Args:
        command: The command to execute.
        image: The Docker image to use (e.g., 'python:3.11-slim', 'node:lts-slim').
        timeout: Execution timeout in seconds.

    Returns:
        The output of the command or an error message.
    """
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "[Warning: Docker not found. Falling back to host bash_tool]\n\n" + bash_tool(command, timeout)

    # Use a temporary container to run the command
    # We mount the current project directory read-only for context if needed,
    # but the command runs in a scratch space.
    project_root = os.getcwd()
    cmd = [
        "docker", "run", "--rm",
        "--network", "none", # Isolate network by default
        "-v", f"{project_root}:/app:ro",
        "-w", "/tmp",
        image,
        "bash", "-c", command
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
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
    except subprocess.TimeoutExpired:
        return "Error: Container execution timed out."
    except Exception as e:
        return f"Error executing command in container: {str(e)}"
