import subprocess
from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path
from src.preprocessor import AudioPreprocessor

def test_is_ffmpeg_available():
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=Path("output"))
    
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/ffmpeg"
        assert preprocessor.is_ffmpeg_available() is True
        mock_which.assert_called_once_with("ffmpeg")
        
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        assert preprocessor.is_ffmpeg_available() is False

def test_preprocess_disabled():
    preprocessor = AudioPreprocessor(enabled=False, ffmpeg_path="ffmpeg", output_dir=Path("output"))
    input_file = Path("input/audio.mp3")
    
    # Should return original path without calling subprocess or checking ffmpeg
    with patch("shutil.which") as mock_which:
        with patch("subprocess.run") as mock_run:
            result = preprocessor.preprocess(input_file)
            assert result == input_file
            mock_which.assert_not_called()
            mock_run.assert_not_called()

def test_preprocess_ffmpeg_missing():
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=Path("output"))
    input_file = Path("input/audio.mp3")
    
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="FFmpeg executable 'ffmpeg' not found"):
            preprocessor.preprocess(input_file)

def test_preprocess_success(tmp_path):
    output_dir = tmp_path / "output"
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=output_dir)
    
    input_file = tmp_path / "audio.mp3"
    # Input file must exist or preprocessor might fail?
    # Actually preprocessor doesn't check if input file exists before running FFmpeg,
    # it lets FFmpeg fail if it doesn't. But for mock it doesn't matter.
    # We can mock subprocess.run.
    
    expected_output = output_dir / "preprocessed" / "audio_16k_mono.wav"
    
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            
            result = preprocessor.preprocess(input_file)
            
            assert result == expected_output
            
            # Verify correct FFmpeg command
            expected_cmd = [
                "ffmpeg",
                "-y",
                "-i", str(input_file),
                "-ar", "16000",
                "-ac", "1",
                str(expected_output)
            ]
            mock_run.assert_called_once_with(
                expected_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

def test_preprocess_failure(tmp_path):
    output_dir = tmp_path / "output"
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=output_dir)
    input_file = tmp_path / "audio.mp3"
    
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
        with patch("subprocess.run") as mock_run:
            # Simulate FFmpeg error
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1,
                cmd=["ffmpeg"],
                stderr="Some FFmpeg error"
            )
            
            with pytest.raises(RuntimeError, match="FFmpeg preprocessing failed for audio.mp3: Some FFmpeg error"):
                preprocessor.preprocess(input_file)
