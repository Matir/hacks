import tomllib
import os
import tempfile
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, Any, List

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
    require_sandbox: bool = True
    max_parallel_tasks: int = 3

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

def _resolve_path(path: str, workspace_root: str) -> str:
    """Resolves tokens in a path string.

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
    
    resolved = path
    for token, value in tokens.items():
        resolved = resolved.replace(token, value)
    
    return os.path.abspath(resolved)

def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges two dictionaries."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged

def _find_user_config() -> str | None:
    """Search for the first valid user configuration file."""
    # 1. TRASHDIG_USER_CONFIG env var
    env_config = os.environ.get("TRASHDIG_USER_CONFIG")
    if env_config and os.path.exists(env_config):
        return env_config

    # 2. XDG_CONFIG_HOME/trashdig/trashdig.toml
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        path = os.path.join(xdg_config, "trashdig", "trashdig.toml")
        if os.path.exists(path):
            return path
    
    # 3. $HOME/.config/trashdig/trashdig.toml
    home = os.path.expanduser("~")
    path = os.path.join(home, ".config", "trashdig", "trashdig.toml")
    if os.path.exists(path):
        return path

    # 4. $HOME/.trashdig.toml
    path = os.path.join(home, ".trashdig.toml")
    if os.path.exists(path):
        return path

    return None

def _find_project_config(
    flag_config: str | None, 
    data_dir: str, 
    workspace_root: str
) -> str | None:
    """Search for the first valid project configuration file."""
    # 1. --config flag
    if flag_config and os.path.exists(flag_config):
        return flag_config

    # 2. {data_directory}/trashdig.toml
    path = os.path.join(data_dir, "trashdig.toml")
    if os.path.exists(path):
        return path

    # 3. {workspace}/.trashdig.toml
    path = os.path.join(workspace_root, ".trashdig.toml")
    if os.path.exists(path):
        return path

    # 4. {workspace}/trashdig.toml
    path = os.path.join(workspace_root, "trashdig.toml")
    if os.path.exists(path):
        return path

    return None

def _parse_toml_to_config_data(file_path: str) -> Dict[str, Any]:
    """Reads a TOML file and returns its content as a dictionary."""
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "rb") as f:
        return tomllib.load(f)

def load_config(
    config_flag: str | None = None, 
    data_dir_flag: str | None = None, 
    workspace_root: str = "."
) -> Config:
    """Layered configuration loader.

    1. Finds and loads a User Config.
    2. Resolves the data directory.
    3. Finds and loads a Project Config.
    4. Merges Project Config into User Config.
    5. Returns a unified Config object.
    """
    workspace_root = os.path.abspath(workspace_root)
    
    # Load User Config
    user_config_path = _find_user_config()
    user_data = _parse_toml_to_config_data(user_config_path) if user_config_path else {}

    # Resolve Data Directory
    # Priority: Flag > User Config > Default
    toml_user_data_dir = user_data.get("database", {}).get("data_dir")
    raw_data_dir = data_dir_flag or toml_user_data_dir or os.path.join(workspace_root, ".trashdig")
    resolved_data_dir = _resolve_path(raw_data_dir, workspace_root)

    # Load Project Config
    project_config_path = _find_project_config(config_flag, resolved_data_dir, workspace_root)
    project_data = _parse_toml_to_config_data(project_config_path) if project_config_path else {}

    # Deep merge project settings into user settings
    final_data = _deep_merge(user_data, project_data)

    # Build Config object from merged data
    ui_interface = final_data.get("ui", {}).get("interface", "textual")
    global_model = final_data.get("model", "gemini-2.0-flash")
    global_provider = final_data.get("provider", "google")
    rpm_limit = final_data.get("rate_limit", {}).get("rpm")
    tpm_limit = final_data.get("rate_limit", {}).get("tpm")
    require_sandbox = final_data.get("security", {}).get("require_sandbox", True)
    max_parallel = final_data.get("concurrency", {}).get("max_parallel_tasks", 3)

    # Load Agents
    agents_data = final_data.get("agents", {})
    agents = {}
    for name, agent_data in agents_data.items():
        if isinstance(agent_data, dict):
            agents[name] = AgentConfig(
                model=agent_data.get("model", global_model),
                provider=agent_data.get("provider", global_provider)
            )

    # Load Providers
    providers_data = final_data.get("providers", {})
    providers = {}
    for name, provider_data in providers_data.items():
        providers[name] = ProviderConfig(
            api_key=provider_data.get("api_key"),
            base_url=provider_data.get("base_url")
        )

    # Database Path Resolution (Post-Merge)
    toml_db_path = final_data.get("database", {}).get("path")
    if toml_db_path:
        resolved_db_path = _resolve_path(toml_db_path, workspace_root)
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
        require_sandbox=require_sandbox,
        max_parallel_tasks=max_parallel,
    )

_config: Config | None = None

def get_config() -> Config:
    """Returns the global configuration object, loading it if necessary."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
