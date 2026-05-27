import shutil
import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class AudioPreprocessor:
    def __init__(self, enabled: bool, ffmpeg_path: str, output_dir: Path):
        self.enabled = enabled
        self.ffmpeg_path = ffmpeg_path
        self.output_dir = Path(output_dir)
        self.preprocess_dir = self.output_dir / "preprocessed"

    def is_ffmpeg_available(self) -> bool:
        """Check if ffmpeg executable is available."""
        return shutil.which(self.ffmpeg_path) is not None

    def preprocess(self, file_path: Path) -> Path:
        """
        Converts audio file to 16kHz, mono, WAV using FFmpeg.
        If preprocessing is disabled or ffmpeg is missing (and config allows fallback), 
        returns the original path.
        """
        if not self.enabled:
            logger.info("Preprocessing is disabled. Using original file.")
            return file_path

        if not self.is_ffmpeg_available():
            raise RuntimeError(
                f"FFmpeg executable '{self.ffmpeg_path}' not found. "
                "Please install FFmpeg or disable preprocessing in config.toml."
            )

        self.preprocess_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.preprocess_dir / f"{file_path.stem}_16k_mono.wav"

        # If output already exists, we could skip, but Orchestrator handles state checks.
        # We will overwrite it if we got here to ensure a clean run.
        cmd = [
            self.ffmpeg_path,
            "-y",             # Overwrite output file
            "-i", str(file_path),
            "-ar", "16000",   # 16kHz
            "-ac", "1",       # 1 channel (mono)
            str(output_path)
        ]

        logger.info(f"Preprocessing {file_path.name} -> {output_path.name}")
        try:
            # Redirect stdout/stderr to capture errors
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed. Stderr: {e.stderr}")
            raise RuntimeError(f"FFmpeg preprocessing failed for {file_path.name}: {e.stderr}") from e

        return output_path
