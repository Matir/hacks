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

def test_load_config_global_defaults(tmp_path):
    """Tests loading config with global model and provider defaults."""
    config_content = """
    model = "global-model"
    provider = "global-provider"

    [agents.archaeologist]
    # Should use global defaults
    
    [agents.hunter]
    model = "hunter-model"
    # Should use global provider default
    """
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)

    config = load_config(str(config_file))
    assert config.default_model == "global-model"
    assert config.default_provider == "global-provider"
    
    # Check archaeologist (inherited)
    assert config.agents["archaeologist"].model == "global-model"
    assert config.agents["archaeologist"].provider == "global-provider"
    
    # Check hunter (partial override)
    assert config.agents["hunter"].model == "hunter-model"
    assert config.agents["hunter"].provider == "global-provider"
    
    # Check get_agent_config for non-existent agent
    validator_cfg = config.get_agent_config("validator")
    assert validator_cfg.model == "global-model"
    assert validator_cfg.provider == "global-provider"

def test_load_config_priority(tmp_path, monkeypatch):
    """Tests that trashdig.toml is preferred over config.toml."""
    monkeypatch.chdir(tmp_path)
    
    config_toml = tmp_path / "config.toml"
    config_toml.write_text('model = "from-config"')
    
    trashdig_toml = tmp_path / "trashdig.toml"
    trashdig_toml.write_text('model = "from-trashdig"')
    
    # Should load trashdig.toml
    config = load_config()
    assert config.default_model == "from-trashdig"
    
    # Remove trashdig.toml, should load config.toml
    trashdig_toml.unlink()
    config = load_config()
    assert config.default_model == "from-config"
