import subprocess
from abc import ABC, abstractmethod

# Well-known credential/agent-socket variable names to strip outright, beyond
# what the substring patterns below already catch.
ENV_DENYLIST_EXACT: frozenset[str] = frozenset(
    {
        "SSH_AUTH_SOCK",
        "SSH_AGENT_PID",
        "GPG_AGENT_INFO",
        "GPG_TTY",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "KUBECONFIG",
        "DOCKER_AUTH_CONFIG",
        "NETRC",
    }
)

# Case-insensitive substrings that mark a variable as credential-shaped.
# Catches provider-specific vars (GEMINI_API_KEY, ANTHROPIC_API_KEY,
# GITHUB_TOKEN, NPM_TOKEN, ...) without enumerating every provider by name.
ENV_DENYLIST_SUBSTRINGS: tuple[str, ...] = (
    "API_KEY",
    "APIKEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "PRIVATE_KEY",
    "CREDENTIAL",
)


def filter_env(env: dict[str, str]) -> dict[str, str]:
    """Strips credential-shaped variables from an environment before it is handed to a sandboxed subprocess.

    Args:
        env: The candidate environment (e.g. a merge of os.environ with
            caller-supplied overrides).

    Returns:
        A copy of ``env`` with denylisted variables removed.
    """
    filtered = {}
    for key, value in env.items():
        upper = key.upper()
        if upper in ENV_DENYLIST_EXACT:
            continue
        if any(pattern in upper for pattern in ENV_DENYLIST_SUBSTRINGS):
            continue
        filtered[key] = value
    return filtered


class Sandbox(ABC):
    """Abstract base class for tool execution sandboxes."""

    def __init__(
        self,
        workspace_dir: str,
        allowlist: list[str] | None = None,
        env: dict[str, str] | None = None,
        network: bool = True,
    ):
        """Initializes the sandbox.

        Args:
            workspace_dir: The project root directory to allow write access.
            allowlist: Additional read-only paths to mount.
            env: Environment variables for the sandboxed process.
            network: Whether to allow network access.
        """
        self.workspace_dir = workspace_dir
        self.allowlist = allowlist or []
        self.env = env or {}
        self.network = network

    @abstractmethod
    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        cwd: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Runs a command inside the sandbox.

        Args:
            command: The command and its arguments.
            timeout: Execution timeout in seconds.
            cwd: The working directory inside the sandbox.

        Returns:
            A subprocess.CompletedProcess object.
        """
        pass
