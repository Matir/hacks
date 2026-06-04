import os
import tomllib
from pathlib import Path
from typing import Any, Dict

class Config:
    def __init__(self, config_path: str | Path = "config.toml"):
        self.config_path = Path(config_path)
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, "rb") as f:
            self.data = tomllib.load(f)

    @property
    def input_dir(self) -> Path:
        return Path(self.data.get("paths", {}).get("input_dir", "input"))

    @property
    def output_dir(self) -> Path:
        return Path(self.data.get("paths", {}).get("output_dir", "output"))

    @property
    def prompt_file(self) -> Path:
        return Path(self.data.get("paths", {}).get("prompt_file", "prompts/post_process.md"))

    @property
    def preprocess_enabled(self) -> bool:
        return bool(self.data.get("preprocessing", {}).get("enabled", True))

    @property
    def chunking_enabled(self) -> bool:
        return bool(self.data.get("preprocessing", {}).get("chunking_enabled", False))

    @property
    def chunk_max_duration(self) -> int:
        return int(self.data.get("preprocessing", {}).get("chunk_max_duration", 300))

    @property
    def silence_threshold_db(self) -> int:
        return int(self.data.get("preprocessing", {}).get("silence_threshold_db", -30))

    @property
    def silence_duration(self) -> float:
        return float(self.data.get("preprocessing", {}).get("silence_duration", 0.5))

    @property
    def ffmpeg_path(self) -> str:
        return str(self.data.get("preprocessing", {}).get("ffmpeg_path", "ffmpeg"))

    @property
    def transcriber_provider(self) -> str:
        return str(self.data.get("transcriber", {}).get("provider", "huggingface"))

    @property
    def transcriber_endpoint(self) -> str:
        return str(self.data.get("transcriber", {}).get("endpoint_url", ""))

    @property
    def transcriber_model(self) -> str:
        return str(self.data.get("transcriber", {}).get("model", ""))

    @property
    def enable_speaker_attribution(self) -> bool:
        return bool(self.data.get("transcriber", {}).get("enable_speaker_attribution", False))

    @property
    def transcriber_crispasr_path(self) -> str:
        return str(self.data.get("transcriber", {}).get("crispasr_path", "crispasr"))

    @property
    def transcriber_backend(self) -> str:
        return str(self.data.get("transcriber", {}).get("backend", "auto"))

    @property
    def transcriber_diarize_method(self) -> str:
        return str(self.data.get("transcriber", {}).get("diarize_method", "pyannote"))

    @property
    def language(self) -> str:
        return str(self.data.get("transcriber", {}).get("language", "en"))

    def get_transcriber_api_key(self) -> str:
        env_var = self.data.get("transcriber", {}).get("api_key_env", "HF_API_KEY")
        return os.environ.get(env_var, "")

    @property
    def post_processor_provider(self) -> str:
        return str(self.data.get("post_processor", {}).get("provider", "gemini"))

    @property
    def post_processor_model(self) -> str:
        return str(self.data.get("post_processor", {}).get("model", ""))

    @property
    def post_processor_endpoint(self) -> str:
        return str(self.data.get("post_processor", {}).get("endpoint_url", ""))

    @property
    def post_processor_temperature(self) -> float:
        return float(self.data.get("post_processor", {}).get("temperature", 0.2))

    def get_post_processor_api_key(self) -> str:
        env_var = self.data.get("post_processor", {}).get("api_key_env", "GEMINI_API_KEY")
        return os.environ.get(env_var, "")

    @property
    def rss_feeds(self) -> list[dict]:
        return list(self.data.get("rss", {}).get("feeds", []))

    @property
    def prompt_context(self) -> Dict[str, Any]:
        return dict(self.data.get("prompt_context", {}))
