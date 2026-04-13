import os
import tempfile
import pytest
from pathlib import Path
from core.utils import PromptLoader, LanguageDetector, ConfigLoader, PromptRenderError
from core.models import ServerConfig, ProjectConfig

def test_prompt_loader():
    """Verifies that PromptLoader loads and renders templates correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir)
        agent_file = prompts_dir / "test_agent.md"
        agent_file.write_text("Hello {name}!", encoding="utf-8")
        
        loader = PromptLoader(prompts_dir=str(prompts_dir))
        template = loader.load_prompt("test_agent")
        assert template == "Hello {name}!"
        
        rendered = loader.render(template, name="World")
        assert rendered == "Hello World!"
        
        with pytest.raises(PromptRenderError):
            loader.render(template) # Missing name

def test_language_detector():
    """Verifies that LanguageDetector identifies languages correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        source_dir = Path(tmpdir)
        # Create some files
        (source_dir / "api.php").touch()
        (source_dir / "utils.py").touch() # Not in extension map yet, will add or skip
        # Let's use ones from extension map
        (source_dir / "main.c").touch()
        (source_dir / "main.h").touch()
        
        # Extension map: .php, .c, .cpp, .h, .go, .rs, .lua
        # 1 php, 2 C/C++
        detector = LanguageDetector()
        languages = detector.detect(str(source_dir))
        
        assert "C/C++" in languages
        assert "PHP" in languages
        # C/C++ has 2 files, PHP has 1. C/C++ should be first
        assert languages[0] == "C/C++"

def test_config_loader():
    """Verifies that ConfigLoader loads TOML files correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.toml"
        config_path.write_text('[server]\nhost = "0.0.0.0"\nport = 9000', encoding="utf-8")
        
        server_config = ConfigLoader.load_server_config(str(config_path))
        assert server_config.host == "0.0.0.0"
        assert server_config.port == 9000
        
        # Test default
        empty_config = ConfigLoader.load_server_config("/non/existent/path")
        assert empty_config.host == "127.0.0.1" # Default
