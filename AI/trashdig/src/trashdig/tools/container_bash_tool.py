import os
import subprocess

from trashdig.utils import is_binary_available

from .base import artifact_tool, get_config
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
    docker_available = is_binary_available("docker")

    if not docker_available:
        if get_config().require_sandbox and os.environ.get("TRASHDIG_SKIP_SANDBOX") != "1":
            raise RuntimeError(
                "Docker not found. Strict containerization is required by configuration. "
                "Install Docker or set 'security.require_sandbox = false' in trashdig.toml to proceed."
            )
        return "[Warning: Docker not found. Falling back to host bash_tool]\n\n" + bash_tool(command, timeout)

    # Use a temporary container to run the command
    # We mount the current project directory read-only for context if needed,
    # but the command runs in a scratch space.
    project_root = os.getcwd()
    cmd = [
        "docker", "run", "--rm",
        "--network", "none", # Isolate network by default
        "-v", f"{project_root}:/app:ro",
        "-w", "/tmp",  # noqa: S108
        image,
        "bash", "-c", command
    ]

    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        output: list[str] = []
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
