import subprocess
from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path
from podscribe.preprocessor import AudioPreprocessor

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

def test_detect_silence_midpoints():
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=Path("output"))
    
    mock_stderr = """
    Input #0, mp3, from 'audio.mp3':
      Duration: 00:10:00.50, start: 0.000000, bitrate: 128 kb/s
    [silencedetect @ 0x...] silence_start: 100.0
    [silencedetect @ 0x...] silence_end: 102.0 | silence_duration: 2.0
    [silencedetect @ 0x...] silence_start: 250.0
    [silencedetect @ 0x...] silence_end: 253.0 | silence_duration: 3.0
    """
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr=mock_stderr, returncode=0)
        
        midpoints, duration = preprocessor._detect_silence_midpoints(Path("audio.mp3"))
        
        assert duration == 600.50  # 10 mins * 60 + 0.50 secs
        # midpoints: (100+102)/2 = 101, (250+253)/2 = 251.5
        assert midpoints == [101.0, 251.5]

def test_detect_silence_midpoints_unbalanced():
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=Path("output"))
    
    # Unbalanced case:
    # - Starts in silence (silence_end at 5.0 with no start)
    # - Normal silence at [100.0, 105.0]
    # - Ends in silence (silence_start at 500.0 with no end)
    mock_stderr = """
    Input #0, wav, from 'audio.wav':
      Duration: 00:10:00.00, start: 0.000000, bitrate: 256 kb/s
    [silencedetect @ 0x...] silence_end: 5.0 | silence_duration: 5.0
    [silencedetect @ 0x...] silence_start: 100.0
    [silencedetect @ 0x...] silence_end: 105.0 | silence_duration: 5.0
    [silencedetect @ 0x...] silence_start: 500.0
    """
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr=mock_stderr, returncode=0)
        
        midpoints, duration = preprocessor._detect_silence_midpoints(Path("audio.wav"))
        
        assert duration == 600.0
        # Expected midpoints:
        # 1. Starts in silence -> [0, 5.0] -> 2.5
        # 2. Normal silence -> [100.0, 105.0] -> 102.5
        # 3. Ends in silence -> [500.0, 600.0] -> 550.0
        assert midpoints == [2.5, 102.5, 550.0]

def test_detect_silence_duration_parsing():
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=Path("output"))
    
    # Test case 1: 3 decimals in duration
    mock_stderr_1 = "  Duration: 00:01:30.123, start: 0.00, bitrate: 128 kb/s"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr=mock_stderr_1, returncode=0)
        _, duration = preprocessor._detect_silence_midpoints(Path("audio.wav"))
        assert duration == 90.123

    # Test case 2: No decimals in duration
    mock_stderr_2 = "  Duration: 00:01:30, start: 0.00, bitrate: 128 kb/s"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr=mock_stderr_2, returncode=0)
        _, duration = preprocessor._detect_silence_midpoints(Path("audio.wav"))
        assert duration == 90.0

def test_calculate_split_points():
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=Path("output"), chunk_max_duration=100)
    
    # Case 1: Silence available
    midpoints = [40.0, 90.0, 150.0, 195.0]
    total_duration = 250.0
    
    splits = preprocessor._calculate_split_points(midpoints, total_duration)
    # 1st target: 100 -> nearest silence before 100 is 90.0
    # 2nd target: 90 + 100 = 190 -> nearest silence before 190 is 150.0
    # remaining (250 - 150 = 100) is <= 100, so no more splits are needed!
    assert splits == [90.0, 150.0]
    
    # Case 2: Hard cut fallback (no silence pauses)
    midpoints = []
    splits = preprocessor._calculate_split_points(midpoints, total_duration)
    assert splits == [100.0, 200.0]

def test_preprocess_chunking_single_chunk(tmp_path):
    output_dir = tmp_path / "output"
    preprocessor = AudioPreprocessor(
        enabled=True,
        ffmpeg_path="ffmpeg",
        output_dir=output_dir,
        chunking_enabled=True,
        chunk_max_duration=300
    )
    input_file = tmp_path / "audio.mp3"
    
    # Pre-create the chunk directory to cover the directory exists/cleanup block
    chunks_dir = output_dir / "preprocessed" / "audio_chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    
    # Mock silence detection to return short duration (150s, no splits)
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch.object(AudioPreprocessor, "_detect_silence_midpoints", return_value=([], 150.0)), \
         patch("subprocess.run") as mock_run:
         
         mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
         
         result = preprocessor.preprocess(input_file)
         
         # Should return the chunks directory
         assert result == output_dir / "preprocessed" / "audio_chunks"
         # Verify single downmix chunk command
         expected_cmd = [
             "ffmpeg", "-y", "-i", str(input_file),
             "-ar", "16000", "-ac", "1",
             str(result / "chunk_000.wav")
         ]
         mock_run.assert_called_once_with(expected_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

def test_preprocess_chunking_multiple_chunks(tmp_path):
    output_dir = tmp_path / "output"
    preprocessor = AudioPreprocessor(
        enabled=True,
        ffmpeg_path="ffmpeg",
        output_dir=output_dir,
        chunking_enabled=True,
        chunk_max_duration=100
    )
    input_file = tmp_path / "audio.mp3"
    
    # Mock silence detection and split times: splits at [90.0, 180.0]
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch.object(AudioPreprocessor, "_detect_silence_midpoints", return_value=([90.0, 180.0], 250.0)), \
         patch("subprocess.run") as mock_run:
         
         mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
         
         result = preprocessor.preprocess(input_file)
         
         assert result == output_dir / "preprocessed" / "audio_chunks"
         expected_cmd = [
             "ffmpeg", "-y", "-i", str(input_file),
             "-f", "segment", "-segment_times", "90.000,180.000",
             "-ar", "16000", "-ac", "1",
             str(result / "chunk_%03d.wav")
         ]
         mock_run.assert_called_once_with(expected_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

def test_detect_silence_failure():
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=Path("output"))
    
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["ffmpeg"], stderr="Detect failed")
        with pytest.raises(RuntimeError, match="FFmpeg silence detection failed for audio.mp3: Detect failed"):
            preprocessor._detect_silence_midpoints(Path("audio.mp3"))

def test_preprocess_chunking_failure(tmp_path):
    output_dir = tmp_path / "output"
    preprocessor = AudioPreprocessor(
        enabled=True,
        ffmpeg_path="ffmpeg",
        output_dir=output_dir,
        chunking_enabled=True,
        chunk_max_duration=100
    )
    input_file = tmp_path / "audio.mp3"
    
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch.object(AudioPreprocessor, "_detect_silence_midpoints", return_value=([], 150.0)), \
         patch("subprocess.run") as mock_run:
         
         mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["ffmpeg"], stderr="Split failed")
         with pytest.raises(RuntimeError, match="FFmpeg chunking failed for audio.mp3: Split failed"):
             preprocessor.preprocess(input_file)

def test_get_duration_success():
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=Path("output"))
    mock_stderr = "  Duration: 00:05:30.25, start: 0.00, bitrate: 128 kb/s"
    
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr=mock_stderr, returncode=0)
        
        duration = preprocessor.get_duration(Path("audio.mp3"))
        assert duration == 330.25  # 5 mins * 60 + 30.25 secs
        mock_run.assert_called_once_with(
            ["ffmpeg", "-i", "audio.mp3", "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )

def test_get_duration_no_ffmpeg():
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=Path("output"))
    
    with patch("shutil.which", return_value=None):
        duration = preprocessor.get_duration(Path("audio.mp3"))
        assert duration == 0.0

def test_get_duration_failure():
    preprocessor = AudioPreprocessor(enabled=True, ffmpeg_path="ffmpeg", output_dir=Path("output"))
    
    with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
         patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("FFmpeg crashed")
        
        duration = preprocessor.get_duration(Path("audio.mp3"))
        assert duration == 0.0
