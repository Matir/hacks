import tomllib
import os
import tempfile
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class ProviderConfig:
    """Config settings for a model provider."""
    api_key: str | None = None
    base_url: str | None = None

@dataclass
class AgentConfig:
    """Config settings for an agent."""
    model: str = "gemini-2.0-flash"
    provider: str = "google"

@dataclass
class Config:
    """The main TrashDig configuration object."""
    interface: str = "textual"
    default_model: str = "gemini-2.0-flash"
    default_provider: str = "google"
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    data_dir: str = ".trashdig"
    db_path: str = ".trashdig/trashdig.db"
    rpm_limit: int | None = None
    tpm_limit: int | None = None

    def get_agent_config(self, name: str) -> AgentConfig:
        """Returns the config for a specific agent, falling back to defaults.

        Args:
            name: The name of the agent (e.g., "hunter").

        Returns:
            An AgentConfig instance.
        """
        if name in self.agents:
            return self.agents[name]
        return AgentConfig(model=self.default_model, provider=self.default_provider)

def _resolve_data_dir(data_dir: str, workspace_root: str) -> str:
    """Resolves tokens in the data_dir string.

    Tokens:
    - {workspace}: The workspace directory path.
    - {date}: YYYYMMDD.
    - {datetime}: YYYYMMDD-HHMMSS.
    - {tmpdir}: tempfile.gettempdir().
    - {name}: os.path.basename(workspace).
    """
    now = datetime.now()
    tokens = {
        "{workspace}": workspace_root,
        "{date}": now.strftime("%Y%m%d"),
        "{datetime}": now.strftime("%Y%m%d-%H%M%S"),
        "{tmpdir}": tempfile.gettempdir(),
        "{name}": os.path.basename(workspace_root.rstrip(os.sep)) or "root",
    }
    
    resolved = data_dir
    for token, value in tokens.items():
        resolved = resolved.replace(token, value)
    
    return os.path.abspath(resolved)

def load_config(file_path: str = "config.toml", data_dir: str | None = None, workspace_root: str = ".") -> Config:
    """Loads the TrashDig configuration from a TOML file.

    Args:
        file_path: Path to the configuration file.
        data_dir: Optional override for the data directory.
        workspace_root: The root directory of the workspace.

    Returns:
        A Config instance.
    """
    if not os.path.exists(file_path):
        # Even if config doesn't exist, we still respect data_dir
        c = Config()
        raw_data_dir = data_dir or os.path.join(workspace_root, ".trashdig")
        c.data_dir = _resolve_data_dir(raw_data_dir, workspace_root)
        c.db_path = os.path.join(c.data_dir, "trashdig.db")
        return c

    with open(file_path, "rb") as f:
        data = tomllib.load(f)

    ui_interface = data.get("ui", {}).get("interface", "textual")

    # Global Model Defaults
    global_model = data.get("model", "gemini-2.0-flash")
    global_provider = data.get("provider", "google")
    
    # Rate Limits
    rpm_limit = data.get("rate_limit", {}).get("rpm")
    tpm_limit = data.get("rate_limit", {}).get("tpm")

    # Load Agents
    agents_data = data.get("agents", {})
    agents = {}
    for name, agent_data in agents_data.items():
        if isinstance(agent_data, dict):
            agents[name] = AgentConfig(
                model=agent_data.get("model", global_model),
                provider=agent_data.get("provider", global_provider)
            )

    # Load Providers
    providers_data = data.get("providers", {})
    providers = {}
    for name, provider_data in providers_data.items():
        providers[name] = ProviderConfig(
            api_key=provider_data.get("api_key"),
            base_url=provider_data.get("base_url")
        )

    # Data directory priority:
    # 1. Argument data_dir (CLI flag)
    # 2. TOML database.data_dir
    # 3. Default ".trashdig" relative to workspace_root
    
    toml_data_dir = data.get("database", {}).get("data_dir")
    toml_db_path = data.get("database", {}).get("path")
    
    raw_data_dir = data_dir or toml_data_dir or os.path.join(workspace_root, ".trashdig")
    resolved_data_dir = _resolve_data_dir(raw_data_dir, workspace_root)

    if toml_db_path and not data_dir and not toml_data_dir:
        # If ONLY toml_db_path is provided, derive data_dir from it
        resolved_db_path = _resolve_data_dir(toml_db_path, workspace_root)
        resolved_data_dir = os.path.dirname(resolved_db_path) or ".trashdig"
    else:
        resolved_db_path = os.path.join(resolved_data_dir, "trashdig.db")

    return Config(
        interface=ui_interface,
        default_model=global_model,
        default_provider=global_provider,
        agents=agents,
        providers=providers,
        data_dir=resolved_data_dir,
        db_path=resolved_db_path,
        rpm_limit=rpm_limit,
        tpm_limit=tpm_limit,
    )

