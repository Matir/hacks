import os
import tomllib
from trashdig.config import load_config, Config, AgentConfig

def test_load_config_defaults():
    """Tests loading config when the file doesn't exist."""
    # Ensure config.toml doesn't exist in the current directory for this test
    # Or mock the file path
    config = load_config("non_existent_config.toml")
    assert config.interface == "textual"
    assert len(config.agents) == 0

def test_load_config_from_file(tmp_path):
    """Tests loading config from a valid TOML file."""
    config_content = """
    [ui]
    interface = "textual"

    [agents.archaeologist]
    model = "custom-model"
    provider = "openrouter"

    [agents.hunter]
    model = "gemini-2.0-flash"
    """
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))
    assert config.interface == "textual"
    assert config.agents["archaeologist"].model == "custom-model"
    assert config.agents["archaeologist"].provider == "openrouter"
    assert config.agents["hunter"].model == "gemini-2.0-flash"
    assert config.agents["hunter"].provider == "google" # Default
