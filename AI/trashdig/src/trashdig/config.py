import tomllib
import os
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
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)

def load_config(file_path: str = "config.toml") -> Config:
    """Loads the TrashDig configuration from a TOML file.

    Args:
        file_path: Path to the configuration file.

    Returns:
        A Config instance.
    """
    if not os.path.exists(file_path):
        return Config()

    with open(file_path, "rb") as f:
        data = tomllib.load(f)

    ui_interface = data.get("ui", {}).get("interface", "textual")
    
    # Load Agents
    agents_data = data.get("agents", {})
    agents = {}
    for name, agent_data in agents_data.items():
        agents[name] = AgentConfig(
            model=agent_data.get("model", "gemini-2.0-flash"),
            provider=agent_data.get("provider", "google")
        )

    # Load Providers
    providers_data = data.get("providers", {})
    providers = {}
    for name, provider_data in providers_data.items():
        providers[name] = ProviderConfig(
            api_key=provider_data.get("api_key"),
            base_url=provider_data.get("base_url")
        )

    return Config(
        interface=ui_interface,
        agents=agents,
        providers=providers
    )
