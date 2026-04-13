import functools
import os
import typing
from pathlib import Path

import tomli
from pydantic import ValidationError

from core.models import ProjectConfig, ServerConfig


class PromptRenderError(Exception):
    """Raised when a prompt template is missing required placeholders."""
    pass


class PromptLoader:
    """Loads and caches prompt templates from .md files."""

    def __init__(self, prompts_dir: str = "prompts") -> None:
        self.prompts_dir = Path(prompts_dir)

    @functools.lru_cache(maxsize=128)
    def load_prompt(self, agent_name: str, prompt_name: typing.Optional[str] = None) -> str:
        """
        Loads a prompt template from file.
        
        :param agent_name: Name of the agent.
        :param prompt_name: Optional sub-prompt name.
        :return: Raw prompt template string.
        """
        if prompt_name:
            prompt_path = self.prompts_dir / agent_name / f"{prompt_name}.md"
        else:
            prompt_path = self.prompts_dir / f"{agent_name}.md"

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template not found at {prompt_path}")

        return prompt_path.read_text(encoding="utf-8")

    def render(self, template: str, **kwargs: typing.Any) -> str:
        """
        Renders a template with the given placeholders.
        
        :param template: The raw template string.
        :param kwargs: Placeholder values.
        :return: Rendered prompt string.
        :raises PromptRenderError: If a placeholder is missing.
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise PromptRenderError(f"Missing required placeholder: {e}")


class LanguageDetector:
    """Detects primary project language(s) by extension counting."""

    VENDORED_DIRS = {
        "vendor", "node_modules", ".git", ".github", "venv", ".venv",
        "third_party", "build", "dist", "target"
    }

    EXTENSION_MAP = {
        ".php": "PHP",
        ".c": "C/C++",
        ".cpp": "C/C++",
        ".h": "C/C++",
        ".go": "Go",
        ".rs": "Rust",
        ".lua": "Lua",
    }

    def detect(self, source_path: str) -> typing.List[str]:
        """
        Detects languages where file count > 5% of total non-vendored files.
        
        :param source_path: Root of the source code.
        :return: Ranked list of detected languages.
        """
        counts: typing.Dict[str, int] = {}
        total_files = 0

        source_root = Path(source_path)
        for root, dirs, files in os.walk(source_root):
            # Prune vendored directories
            dirs[:] = [d for d in dirs if d not in self.VENDORED_DIRS]

            for file in files:
                ext = Path(file).suffix.lower()
                if ext in self.EXTENSION_MAP:
                    lang = self.EXTENSION_MAP[ext]
                    counts[lang] = counts.get(lang, 0) + 1
                    total_files += 1

        if total_files == 0:
            return []

        # Filter by 5% threshold
        detected = [
            lang for lang, count in counts.items()
            if (count / total_files) >= 0.05
        ]

        # Return ranked by count descending
        return sorted(detected, key=lambda l: counts[l], reverse=True)


class ConfigLoader:
    """Loads and validates TOML configuration files."""

    @staticmethod
    def load_server_config(path: str = "config.toml") -> ServerConfig:
        """Loads and validates the global server config."""
        p = Path(path)
        if not p.exists():
            return ServerConfig()
        
        with p.open("rb") as f:
            data = tomli.load(f).get("server", {})
            return ServerConfig(**data)

    @staticmethod
    def load_project_config(path: str) -> ProjectConfig:
        """Loads and validates a per-project config."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Project config not found at {path}")

        with p.open("rb") as f:
            data = tomli.load(f)
            return ProjectConfig(**data)
