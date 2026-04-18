import os
import tempfile
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def _find_user_config() -> str | None:
    """Searches for a user-level config file in ~/.config/trashdig/."""
    user_config = os.path.expanduser("~/.config/trashdig/trashdig.toml")
    return user_config if os.path.exists(user_config) else None


def _find_project_config() -> str | None:
    """Searches for a project config file, preferring .trashdig.toml."""
    for name in (".trashdig.toml", "trashdig.toml"):
        if os.path.exists(name):
            return name
    return None


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


@dataclass
class Config:
    """Central configuration for TrashDig."""
    config_path: str = "trashdig.toml"
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.config_path is None:
            self.config_path = "trashdig.toml"
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.config_path):
            with open(self.config_path, "rb") as f:
                self.data = tomllib.load(f)

    @property
    def require_sandbox(self) -> bool:
        """Whether to require sandboxing for tool execution."""
        return self.data.get("require_sandbox", True)

    @property
    def rpm_limit(self) -> int | None:
        """Requests per minute limit for LLM calls."""
        return self.data.get("rpm_limit")

    @property
    def tpm_limit(self) -> int | None:
        """Tokens per minute limit for LLM calls."""
        return self.data.get("tpm_limit")

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

    @property
    def interface(self) -> str:
        """Returns the UI interface type."""
        return self.data.get("ui", {}).get("interface", "textual")

    @property
    def default_model(self) -> str:
        """Returns the default model name."""
        return self.data.get("model", "gemini-2.0-flash")

    @property
    def default_provider(self) -> str:
        """Returns the default provider name."""
        return self.data.get("provider", "google")

    @property
    def agents(self) -> dict[str, AgentConfig]:
        """Returns all agent configurations."""
        result = {}
        for name, cfg in self.data.get("agents", {}).items():
            result[name] = AgentConfig(
                name=name,
                model=cfg.get("model", self.default_model),
                provider=cfg.get("provider", self.default_provider),
            )
        return result

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """Returns the configuration for a specific agent.

        Args:
            agent_name: Name of the agent (e.g., 'hunter').
        """
        cfg_data = self.data.get("agents", {}).get(agent_name, {})
        return AgentConfig(
            name=agent_name,
            model=cfg_data.get("model", self.default_model),
            provider=cfg_data.get("provider", self.default_provider),
        )

    def get_provider_config(self, provider_name: str) -> ProviderConfig:
        """Returns the configuration for an LLM provider."""
        cfg_data = self.data.get("providers", {}).get(provider_name, {})
        return ProviderConfig(name=provider_name, **cfg_data)


_GLOBAL_CONFIG: Config | None = None


def get_config(config_path: str | None = None) -> Config:
    """Returns the singleton Config instance."""
    global _GLOBAL_CONFIG  # noqa: PLW0603
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = Config(config_path or "trashdig.toml")
    return _GLOBAL_CONFIG


def load_config(
    config_path: str | None = None,
    config_flag: str | None = None,
    data_dir_flag: str | None = None,
    workspace_root: str | None = None,
) -> Config:
    """Creates and returns a fresh Config instance (not cached)."""
    # Check for user config first
    user_cfg = _find_user_config()

    if config_path is None:
        config_path = config_flag or _find_project_config()

    # Load base config (project or specified path)
    cfg = Config(config_path=config_path or "")

    # Apply overrides from flags
    if data_dir_flag:
        cfg.data["data_dir"] = data_dir_flag
    if workspace_root:
        cfg.data["workspace_root"] = workspace_root

    # Merge user config if it exists (project config takes priority)
    if user_cfg and config_path != user_cfg:
        user_data: dict[str, Any] = {}
        if os.path.exists(user_cfg):
            with open(user_cfg, "rb") as f:
                user_data = tomllib.load(f)
        # User config provides defaults; project config overrides
        merged = {**user_data, **cfg.data}
        cfg.data = merged

    return cfg
