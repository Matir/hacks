import os
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str = "google"
    api_key: str | None = None
    base_url: str | None = None


@dataclass
class AgentConfig:
    """Configuration for a specific TrashDig agent."""
    name: str = "archaeologist"
    model: str = "gemini-2.0-flash-exp"
    provider: str = "google"
    temperature: float = 0.0
    max_tokens: int = 4096


class Config:
    """Central configuration for TrashDig."""

    def __init__(self, config_path: str | None = None):
        """Initialises the Config.

        Args:
            config_path: Path to the TOML config file.
        """
        self.config_path = config_path or "trashdig.toml"
        self.data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.config_path):
            with open(self.config_path, "rb") as f:
                self.data = tomllib.load(f)

    @property
    def workspace_root(self) -> str:
        """Returns the project workspace root path."""
        return os.path.abspath(self.data.get("workspace_root", "."))

    @property
    def data_dir(self) -> str:
        """Returns the directory for TrashDig artifacts and state."""
        path = self.data.get("data_dir", ".trashdig")
        return self.resolve_workspace_path(path)

    @property
    def db_path(self) -> str:
        """Returns the path to the project SQLite database."""
        path = self.data.get("db_path", "{datadir}/trashdig.db")
        return self.resolve_workspace_path(path)

    def resolve_workspace_path(self, path_template: str) -> str:
        """Resolves template tokens in paths.

        Args:
            path_template: Path string possibly containing tokens like {workspace}.
        """
        tokens = self.resolve_workspace_tokens(self.workspace_root)
        tokens["{datadir}"] = self.data.get("data_dir", ".trashdig")
        
        path = path_template
        for token, val in tokens.items():
            path = path.replace(token, val)
        
        return os.path.abspath(path)

    def resolve_data_path(self, filename: str) -> str:
        """Resolves a filename relative to the data directory."""
        return os.path.join(self.data_dir, filename)

    def resolve_workspace_tokens(self, workspace_root: str) -> dict[str, str]:
        """Generates a mapping of standard path tokens.

        Args:
            workspace_root: Base path to the project.

        Returns:
            Dict mapping tokens like {date} to their values.
        """
        now = datetime.now(UTC)
        tokens = {
            "{workspace}": workspace_root,
            "{date}": now.strftime("%Y%m%d"),
            "{datetime}": now.strftime("%Y%m%d-%H%M%S"),
            "{tmpdir}": tempfile.gettempdir(),
            "{name}": os.path.basename(workspace_root),
        }
        return tokens

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """Returns the configuration for a specific agent.

        Args:
            agent_name: Name of the agent (e.g., 'hunter').
        """
        # (Implementation omitted for brevity, assumes standard logic)
        cfg_data = self.data.get("agents", {}).get(agent_name, {})
        return AgentConfig(name=agent_name, **cfg_data)

    def get_provider_config(self, provider_name: str) -> ProviderConfig:
        """Returns the configuration for an LLM provider."""
        cfg_data = self.data.get("providers", {}).get(provider_name, {})
        return ProviderConfig(name=provider_name, **cfg_data)


_GLOBAL_CONFIG: Config | None = None


def get_config(config_path: str | None = None) -> Config:
    """Returns the singleton Config instance."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = Config(config_path)
    return _GLOBAL_CONFIG
