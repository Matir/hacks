import os
import tomllib
from pathlib import Path
from typing import Any, Dict


class Config:
    """Parses and exposes pipeline settings from TOML configuration files."""

    def __init__(self, config_path: str | Path = "config.toml"):
        """Initialize configuration reader and load TOML data."""
        self.config_path = Path(config_path)
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Read and decode TOML configuration file from disk."""
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
    def prompts_dir(self) -> Path:
        return Path(self.data.get("paths", {}).get("prompts_dir", "prompts"))

    @property
    def prompt_file(self) -> Path:
        default_path = self.prompts_dir / "post_process.md"
        return Path(self.data.get("paths", {}).get("prompt_file", default_path))

    @property
    def assemblyai_prompt_file(self) -> Path:
        default_path = self.prompts_dir / "assemblyai.md"
        return Path(
            self.data.get("paths", {}).get(
                "assemblyai_prompt_file",
                self.data.get("transcriber", {}).get("assemblyai_prompt_file", default_path),
            )
        )

    @property
    def assemblyai_keyterms_file(self) -> Path:
        default_path = self.prompts_dir / "keyterms.txt"
        return Path(
            self.data.get("paths", {}).get(
                "assemblyai_keyterms_file",
                self.data.get("transcriber", {}).get("assemblyai_keyterms_file", default_path),
            )
        )

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

    @property
    def hotwords(self) -> str:
        return str(self.data.get("transcriber", {}).get("hotwords", ""))

    @property
    def transcriber_timeout(self) -> float:
        return float(self.data.get("transcriber", {}).get("timeout", 300.0))

    def get_transcriber_api_key_env(self) -> str | None:
        if "api_key_env" in self.data.get("transcriber", {}):
            return str(self.data["transcriber"]["api_key_env"])
        provider = self.transcriber_provider.lower()
        if provider == "assemblyai":
            return "ASSEMBLYAI_API_KEY"
        elif provider == "crispasr":
            return "CRISPASR_API_KEY"
        elif provider == "openai_compatible":
            return "OPENAI_API_KEY"
        elif provider == "crispasr_cli":
            return None
        return "HF_API_KEY"

    def get_transcriber_api_key(self) -> str:
        env_var = self.get_transcriber_api_key_env()
        return os.environ.get(env_var, "") if env_var else ""

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

    def get_post_processor_api_key_env(self) -> str | None:
        if "api_key_env" in self.data.get("post_processor", {}):
            return str(self.data["post_processor"]["api_key_env"])
        provider = self.post_processor_provider.lower()
        if provider == "openai_compatible":
            return "OPENAI_API_KEY"
        return "GEMINI_API_KEY"

    def get_post_processor_api_key(self) -> str:
        env_var = self.get_post_processor_api_key_env()
        return os.environ.get(env_var, "") if env_var else ""

    def get_required_auth_env_vars(self, stage: str = "all") -> list[tuple[str, str]]:
        """Identify required authentication environment variables based on configured providers and target stage."""
        required = []

        if stage in ("all", "transcribe"):
            t_provider = self.transcriber_provider.lower()
            t_endpoint = self.transcriber_endpoint.lower()
            is_local_t = t_endpoint.startswith("http://localhost") or t_endpoint.startswith("http://127.0.0.1")
            env_var = self.get_transcriber_api_key_env()

            if env_var:
                if t_provider == "assemblyai":
                    required.append((env_var, "AssemblyAI transcription API key"))
                elif t_provider in ("huggingface", "vibevoice", "openai_compatible", "crispasr"):
                    if "api_key_env" in self.data.get("transcriber", {}) or (t_endpoint and not is_local_t):
                        required.append((env_var, f"{t_provider} transcription API key"))

        if stage in ("all", "postprocess"):
            p_provider = self.post_processor_provider.lower()
            p_endpoint = self.post_processor_endpoint.lower()
            is_local_p = p_endpoint.startswith("http://localhost") or p_endpoint.startswith("http://127.0.0.1")
            env_var = self.get_post_processor_api_key_env()

            if env_var:
                if p_provider == "gemini":
                    required.append((env_var, "Gemini post-processing API key"))
                elif p_provider == "openai_compatible":
                    if "api_key_env" in self.data.get("post_processor", {}) or (p_endpoint and not is_local_p):
                        required.append((env_var, "OpenAI-compatible post-processing API key"))

        return required

    @property
    def rss_feeds(self) -> list[dict]:
        return list(self.data.get("rss", {}).get("feeds", []))

    @property
    def prompt_context(self) -> Dict[str, Any]:
        return dict(self.data.get("prompt_context", {}))

    def dump(self) -> str:
        """Render a formatted, human-readable summary of the current configuration."""
        lines = [
            "==================================================",
            "                PODSCRIBE CONFIGURATION           ",
            "==================================================",
            f"Config File:             {self.config_path}",
            "",
            "--- Paths ---",
            f"Input Directory:         {self.input_dir}",
            f"Output Directory:        {self.output_dir}",
            f"Prompts Directory:       {self.prompts_dir}",
            f"Prompt Template:         {self.prompt_file}",
            "",
            "--- Preprocessing ---",
            f"Enabled:                 {self.preprocess_enabled}",
            f"FFmpeg Path:             {self.ffmpeg_path}",
            f"Chunking Enabled:        {self.chunking_enabled}",
            f"Max Chunk Duration:      {self.chunk_max_duration}s" if self.chunking_enabled else "Max Chunk Duration:      N/A",
            f"Silence Threshold:       {self.silence_threshold_db} dB" if self.chunking_enabled else "Silence Threshold:       N/A",
            f"Silence Duration:        {self.silence_duration}s" if self.chunking_enabled else "Silence Duration:        N/A",
            "",
            "--- Transcriber (ASR) ---",
            f"Provider:                {self.transcriber_provider}",
            f"Model:                   {self.transcriber_model}",
            f"Endpoint URL:            {self.transcriber_endpoint}",
            f"Speaker Attribution:     {self.enable_speaker_attribution}",
            f"Language:                {self.language}",
            f"API Key Env Var:         {self.get_transcriber_api_key_env() or 'N/A'}",
            f"API Key Present:         {'Yes' if self.get_transcriber_api_key() else 'No'}",
            f"Timeout:                 {self.transcriber_timeout}s",
        ]

        # Add provider-specific keys if they exist
        if self.transcriber_provider == "crispasr_cli":
            lines.extend([
                f"CrispASR Path:           {self.transcriber_crispasr_path}",
                f"CrispASR Backend:        {self.transcriber_backend}",
                f"Diarize Method:          {self.transcriber_diarize_method}",
            ])
        elif self.transcriber_provider == "vibevoice":
            lines.extend([
                f"Hotwords:                {self.hotwords}",
            ])
        elif self.transcriber_provider == "assemblyai":
            lines.extend([
                f"AssemblyAI Prompt File:  {self.assemblyai_prompt_file}",
                f"AssemblyAI Keyterms File:{self.assemblyai_keyterms_file}",
            ])

        lines.extend([
            "",
            "--- Post-Processor (Editor) ---",
            f"Provider:                {self.post_processor_provider}",
            f"Model:                   {self.post_processor_model}",
            f"Endpoint URL:            {self.post_processor_endpoint}",
            f"Temperature:             {self.post_processor_temperature}",
            f"API Key Env Var:         {self.get_post_processor_api_key_env() or 'N/A'}",
            f"API Key Present:         {'Yes' if self.get_post_processor_api_key() else 'No'}",
        ])

        if self.rss_feeds:
            lines.extend([
                "",
                "--- RSS Feeds ---",
            ])
            for feed in self.rss_feeds:
                lines.append(f"- URL: {feed.get('url')} (Max: {feed.get('max_episodes', 'Unlimited')})")

        if self.prompt_context:
            lines.extend([
                "",
                "--- Prompt Context ---",
            ])
            for k, v in self.prompt_context.items():
                lines.append(f"{k}: {v}")

        lines.append("==================================================")
        return "\n".join(lines)
