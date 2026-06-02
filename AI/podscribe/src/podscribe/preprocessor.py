import shutil
import subprocess
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)

class AudioPreprocessor:
    def __init__(self, enabled: bool, ffmpeg_path: str, output_dir: Path,
                 chunking_enabled: bool = False, chunk_max_duration: int = 300,
                 silence_threshold_db: int = -30, silence_duration: float = 0.5):
        self.enabled = enabled
        self.ffmpeg_path = ffmpeg_path
        self.output_dir = Path(output_dir)
        self.preprocess_dir = self.output_dir / "preprocessed"
        self.chunking_enabled = chunking_enabled
        self.chunk_max_duration = chunk_max_duration
        self.silence_threshold_db = silence_threshold_db
        self.silence_duration = silence_duration

    def is_ffmpeg_available(self) -> bool:
        """Check if ffmpeg executable is available."""
        return shutil.which(self.ffmpeg_path) is not None

    def _detect_silence_midpoints(self, file_path: Path) -> tuple[list[float], float]:
        """
        Runs a fast pass using ffmpeg silencedetect filter to discover silence midpoints
        and retrieve the total audio duration in seconds.
        """
        cmd = [
            self.ffmpeg_path,
            "-i", str(file_path),
            "-af", f"silencedetect=noise={self.silence_threshold_db}dB:d={self.silence_duration}",
            "-f", "null",
            "-"
        ]

        logger.info(f"Detecting silent periods in {file_path.name}...")
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg silence detection failed. Stderr: {e.stderr}")
            raise RuntimeError(f"FFmpeg silence detection failed for {file_path.name}: {e.stderr}") from e

        # Reconstruct silence midpoints and total duration chronologically
        midpoints = []
        total_duration = 0.0
        current_start = None
        first_event_is_end = True

        for line in result.stderr.splitlines():
            # Parse duration with optional/arbitrary decimal precision
            duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?", line)
            if duration_match:
                hrs = int(duration_match.group(1))
                mins = int(duration_match.group(2))
                secs = int(duration_match.group(3))
                if duration_match.group(4):
                    decimals_str = duration_match.group(4)
                    precision = len(decimals_str)
                    fractional = int(decimals_str) / (10 ** precision)
                else:
                    fractional = 0.0
                total_duration = hrs * 3600 + mins * 60 + secs + fractional

            # Parse silence events chronologically
            start_match = re.search(r"silence_start: (\d+\.?\d*)", line)
            if start_match:
                current_start = float(start_match.group(1))
                first_event_is_end = False

            end_match = re.search(r"silence_end: (\d+\.?\d*)", line)
            if end_match:
                end_time = float(end_match.group(1))
                if first_event_is_end:
                    # Audio started in silence
                    start_time = 0.0
                    first_event_is_end = False
                else:
                    start_time = current_start if current_start is not None else end_time
                
                midpoints.append((start_time + end_time) / 2)
                current_start = None

        # Handle case where audio ends in silence
        if current_start is not None and total_duration > current_start:
            midpoints.append((current_start + total_duration) / 2)

        return sorted(midpoints), total_duration


    def _calculate_split_points(self, midpoints: list[float], total_duration: float) -> list[float]:
        """
        Calculates the optimal split times so that no segment exceeds self.chunk_max_duration,
        cutting at silence midpoints where possible, otherwise doing hard cuts.
        """
        split_points = []
        last_split = 0.0

        while last_split + self.chunk_max_duration < total_duration:
            target_time = last_split + self.chunk_max_duration
            
            # Find silence pauses between last split and target duration
            candidates = [m for m in midpoints if last_split < m < target_time]
            if not candidates:
                best_split = target_time
            else:
                # Choose latest silence midpoint before limit
                best_split = max(candidates)

            split_points.append(best_split)
            last_split = best_split

        return split_points

    def preprocess(self, file_path: Path) -> Path:
        """
        Converts audio file to 16kHz, mono, WAV using FFmpeg.
        If chunking is enabled, splits the audio at silence midpoints and returns
        a directory containing all generated chunk files.
        """
        if not self.enabled:
            logger.info("Preprocessing is disabled. Using original file path.")
            return file_path

        if not self.is_ffmpeg_available():
            raise RuntimeError(
                f"FFmpeg executable '{self.ffmpeg_path}' not found. "
                "Please install FFmpeg or disable preprocessing in config.toml."
            )

        self.preprocess_dir.mkdir(parents=True, exist_ok=True)

        if not self.chunking_enabled:
            # Standard single-file preprocessing
            output_path = self.preprocess_dir / f"{file_path.stem}_16k_mono.wav"
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(file_path),
                "-ar", "16000",
                "-ac", "1",
                str(output_path)
            ]
            logger.info(f"Preprocessing {file_path.name} -> {output_path.name}")
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"FFmpeg failed. Stderr: {e.stderr}")
                raise RuntimeError(f"FFmpeg preprocessing failed for {file_path.name}: {e.stderr}") from e
            return output_path

        # Chunking-enabled pipeline
        output_dir = self.preprocess_dir / f"{file_path.stem}_chunks"
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Detect silence midpoints and total duration
        midpoints, total_duration = self._detect_silence_midpoints(file_path)
        split_points = self._calculate_split_points(midpoints, total_duration)

        if not split_points:
            # Less than max duration: downmix to single chunk
            output_path = output_dir / "chunk_000.wav"
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(file_path),
                "-ar", "16000",
                "-ac", "1",
                str(output_path)
            ]
            logger.info(f"Preprocessing single chunk: {file_path.name} -> {output_path.name}")
        else:
            # Split into silent segments
            cmd = [
                self.ffmpeg_path,
                "-y",
                "-i", str(file_path),
                "-f", "segment",
                "-segment_times", ",".join(f"{t:.3f}" for t in split_points),
                "-ar", "16000",
                "-ac", "1",
                str(output_dir / "chunk_%03d.wav")
            ]
            logger.info(f"Splitting {file_path.name} into {len(split_points) + 1} chunks inside {output_dir.name}...")

        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg chunking failed. Stderr: {e.stderr}")
            raise RuntimeError(f"FFmpeg chunking failed for {file_path.name}: {e.stderr}") from e

        return output_dir

    def get_duration(self, file_path: Path) -> float:
        """Get duration of audio file in seconds using FFmpeg."""
        if not self.is_ffmpeg_available():
            logger.warning("FFmpeg not available, cannot determine audio duration locally.")
            return 0.0

        cmd = [
            self.ffmpeg_path,
            "-i", str(file_path),
            "-f", "null",
            "-"
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False # ffmpeg returns non-zero often for null muxer info
            )
            # Parse duration from stderr
            for line in result.stderr.splitlines():
                duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?", line)
                if duration_match:
                    hrs = int(duration_match.group(1))
                    mins = int(duration_match.group(2))
                    secs = int(duration_match.group(3))
                    decimals_str = duration_match.group(4) if duration_match.group(4) else ""
                    if decimals_str:
                        fractional = int(decimals_str) / (10 ** len(decimals_str))
                    else:
                        fractional = 0.0
                    return hrs * 3600 + mins * 60 + secs + fractional
        except Exception as e:
            logger.error(f"Failed to get audio duration for {file_path.name}: {e}")
            
        return 0.0
