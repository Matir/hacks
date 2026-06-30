import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from podscribe.config import Config
from podscribe.orchestrator import Orchestrator
from podscribe.post_processors import GeminiPostProcessor, OpenAICompatiblePostProcessor, TokenUsage
from podscribe.transcribers import (
    CrispASRCLITranscriber,
    HuggingFaceTranscriber,
    OpenAICompatibleTranscriber,
    SpeakerAttributedOpenAICompatibleTranscriber,
    VibeVoiceASRTranscriber,
)

# Setup logging
logging.basicConfig(level=logging.INFO)

@pytest.fixture
def mock_config(tmp_path):
    # Create a dummy prompt file
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("Format this: {{TRANSCRIPT}}")

    config = MagicMock(spec=Config)
    config.input_dir = tmp_path / "input"
    config.output_dir = tmp_path / "output"
    config.prompt_file = prompt_file
    config.preprocess_enabled = True
    config.ffmpeg_path = "ffmpeg"
    config.transcriber_provider = "huggingface"
    config.transcriber_endpoint = "https://hf.co"
    config.transcriber_model = "model"
    config.get_transcriber_api_key.return_value = "key"
    config.post_processor_provider = "gemini"
    config.post_processor_model = "gemini-model"
    config.get_post_processor_api_key.return_value = "key"
    config.post_processor_temperature = 0.2
    config.rss_feeds = [] # Skip RSS by default
    config.prompt_context = {}
    return config

def test_orchestrator_find_files(mock_config):
    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)

    # Create some files
    (input_dir / "file1.mp3").write_text("audio")
    (input_dir / "file2.wav").write_text("audio")
    (input_dir / "unsupported.txt").write_text("text")
    (input_dir / "nested").mkdir()
    (input_dir / "nested/nested.mp3").write_text("audio") # Should not scan subdirectories

    with patch.object(Orchestrator, "_init_transcriber"), patch.object(Orchestrator, "_init_post_processor"):
        orchestrator = Orchestrator(mock_config)
        files = orchestrator.find_files()

        # Should find file1.mp3 and file2.wav, ignoring nested and unsupported
        filenames = {f.name for f in files}
        assert filenames == {"file1.mp3", "file2.wav"}

def test_orchestrator_run_full_success(mock_config, tmp_path):
    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create an input file
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio_content")

    # Setup mocks for components
    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

        # Setup transcriber mock
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "raw transcript text"
        mock_init_t.return_value = mock_transcriber

        # Setup post-processor mock
        mock_post_processor = MagicMock()
        mock_post_processor.post_process.return_value = ("polished markdown text", TokenUsage(10, 5, 15))
        mock_init_p.return_value = mock_post_processor

        # Setup preprocessor mock instance
        mock_preprocessor = mock_preprocessor_class.return_value
        preprocessed_file = mock_config.output_dir / "preprocessed" / "podcast_16k_mono.wav"
        mock_preprocessor.preprocess.return_value = preprocessed_file
        mock_preprocessor.get_duration.return_value = 120.0

        # Instantiate and run Orchestrator
        orchestrator = Orchestrator(mock_config)
        orchestrator.run()

        # --- Verifications ---
        # 1. Preprocessor should have been called
        mock_preprocessor.preprocess.assert_called_once_with(input_file, duration=120.0)

        # 2. Transcriber should have been called with the preprocessed file
        mock_transcriber.transcribe.assert_called_once_with(preprocessed_file)

        # 3. Intermediate raw transcript should be saved
        raw_transcript_file = mock_config.output_dir / "raw_transcripts" / "podcast_raw.txt"
        assert raw_transcript_file.exists()
        assert raw_transcript_file.read_text() == "raw transcript text"

        # 4. Post-processor should have been called with raw transcript and prompt template
        mock_post_processor.post_process.assert_called_once_with(
            "raw transcript text",
            "Format this: {{TRANSCRIPT}}",
            context={"filename": "podcast.mp3"}
        )

        # 5. Final transcript should be saved
        final_transcript_file = mock_config.output_dir / "podcast_final.md"
        assert final_transcript_file.exists()
        assert final_transcript_file.read_text() == "polished markdown text"

        # 6. State should be "completed"
        state_file = mock_config.output_dir / "state.json"
        assert state_file.exists()
        import json
        with open(state_file, "r") as f:
            state = json.load(f)
            assert state["podcast.mp3"]["status"] == "completed"
            assert state["podcast.mp3"]["preprocessed_path"] == str(preprocessed_file)
            assert state["podcast.mp3"]["raw_transcript_path"] == str(raw_transcript_file)
            assert state["podcast.mp3"]["final_transcript_path"] == str(final_transcript_file)
            assert state["podcast.mp3"]["audio_duration"] == 120.0
            assert state["podcast.mp3"]["token_usage"] == {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
            assert state["podcast.mp3"]["num_words"] == 3
            assert state["podcast.mp3"]["num_segments"] == 1

def test_orchestrator_run_skips_completed(mock_config, tmp_path):
    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio_content")

    # Setup mocks
    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

        mock_transcriber = MagicMock()
        mock_init_t.return_value = mock_transcriber
        mock_post_processor = MagicMock()
        mock_init_p.return_value = mock_post_processor
        mock_preprocessor = mock_preprocessor_class.return_value

        # First, pre-populate state.json to mark the file as completed with matching hash
        import hashlib
        file_hash = hashlib.md5(b"fake_audio_content").hexdigest()

        output_dir = mock_config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        state_file = output_dir / "state.json"

        state_data = {
            "podcast.mp3": {
                "hash": file_hash,
                "status": "completed",
                "preprocessed_path": "output/preprocessed/podcast_16k_mono.wav",
                "raw_transcript_path": "output/raw_transcripts/podcast_raw.txt",
                "final_transcript_path": "output/podcast_final.md"
            }
        }
        import json
        with open(state_file, "w") as f:
            json.dump(state_data, f)

        orchestrator = Orchestrator(mock_config)
        orchestrator.run()

        # Verification: All component calls should have been skipped
        mock_preprocessor.preprocess.assert_not_called()
        mock_transcriber.transcribe.assert_not_called()
        mock_post_processor.post_process.assert_not_called()

def test_orchestrator_run_resumes_from_transcribed(mock_config, tmp_path):
    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio_content")

    # Setup mocks
    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

        mock_transcriber = MagicMock()
        mock_init_t.return_value = mock_transcriber

        mock_post_processor = MagicMock()
        mock_post_processor.post_process.return_value = ("polished markdown text", TokenUsage(20, 10, 30))
        mock_init_p.return_value = mock_post_processor
        mock_preprocessor = mock_preprocessor_class.return_value
        mock_preprocessor.get_duration.return_value = 120.0

        # Pre-populate state.json: status is "transcribed"
        # Also, the raw transcript file must exist because Orchestrator will try to read it!
        import hashlib
        file_hash = hashlib.md5(b"fake_audio_content").hexdigest()

        output_dir = mock_config.output_dir
        raw_transcripts_dir = output_dir / "raw_transcripts"
        raw_transcripts_dir.mkdir(parents=True, exist_ok=True)

        raw_transcript_file = raw_transcripts_dir / "podcast_raw.txt"
        raw_transcript_file.write_text("saved raw transcript")

        # Create fake preprocessed file so it exists
        preprocessed_file = output_dir / "preprocessed" / "podcast_16k_mono.wav"
        preprocessed_file.parent.mkdir(parents=True, exist_ok=True)
        preprocessed_file.write_text("fake preprocessed")

        state_file = output_dir / "state.json"
        state_data = {
            "podcast.mp3": {
                "hash": file_hash,
                "status": "transcribed",
                "preprocessed_path": str(preprocessed_file),
                "raw_transcript_path": str(raw_transcript_file),
                "final_transcript_path": ""
            }
        }
        import json
        with open(state_file, "w") as f:
            json.dump(state_data, f)

        orchestrator = Orchestrator(mock_config)
        orchestrator.run()

        # Verification:
        # 1. Preprocessor and Transcriber should be skipped
        mock_preprocessor.preprocess.assert_not_called()
        mock_transcriber.transcribe.assert_not_called()

        # 2. Post-processor should be called with the read transcript
        mock_post_processor.post_process.assert_called_once_with(
            "saved raw transcript",
            "Format this: {{TRANSCRIPT}}",
            context={"filename": "podcast.mp3"}
        )

        # 3. Final output saved
        final_transcript_file = output_dir / "podcast_final.md"
        assert final_transcript_file.exists()
        assert final_transcript_file.read_text() == "polished markdown text"

def test_orchestrator_run_handles_error_and_continues(mock_config, tmp_path):
    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)

    # Create TWO input files
    file1 = input_dir / "file1.mp3"
    file1.write_text("audio1")
    file2 = input_dir / "file2.mp3"
    file2.write_text("audio2")

    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "raw transcript"
        mock_init_t.return_value = mock_transcriber

        mock_post_processor = MagicMock()
        mock_post_processor.post_process.return_value = ("polished text", TokenUsage(5, 2, 7))
        mock_init_p.return_value = mock_post_processor

        # Preprocessor mock
        mock_preprocessor = mock_preprocessor_class.return_value
        mock_preprocessor.get_duration.return_value = 120.0

        # Configure preprocessor to FAIL on file1, but succeed on file2
        def preprocess_side_effect(file_path, duration=None):
            if file_path.name == "file1.mp3":
                raise RuntimeError("Preprocessing failed for file1")
            return mock_config.output_dir / "preprocessed" / f"{file_path.stem}.wav"

        mock_preprocessor.preprocess.side_effect = preprocess_side_effect

        orchestrator = Orchestrator(mock_config)
        orchestrator.run()

        # Verification:
        # 1. Preprocessor was called for both
        assert mock_preprocessor.preprocess.call_count == 2

        # 2. Transcriber and post-processor only called for file2
        mock_transcriber.transcribe.assert_called_once()
        mock_post_processor.post_process.assert_called_once()

        # 3. State checks
        state_file = mock_config.output_dir / "state.json"
        import json
        with open(state_file, "r") as f:
            state = json.load(f)
            assert state["file1.mp3"]["status"] == "failed"
            assert "Preprocessing: Preprocessing failed for file1" in state["file1.mp3"]["error"]
            assert state["file2.mp3"]["status"] == "completed"

def test_orchestrator_init_transcribers(mock_config):
    # 1. Test HF init
    mock_config.transcriber_provider = "huggingface"
    mock_config.enable_speaker_attribution = False
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        assert isinstance(orchestrator.transcriber, HuggingFaceTranscriber)

    # 2. Test HF with speaker attribution warning
    mock_config.transcriber_provider = "huggingface"
    mock_config.enable_speaker_attribution = True
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        assert isinstance(orchestrator.transcriber, HuggingFaceTranscriber)

    # 3. Test OpenAI init
    mock_config.transcriber_provider = "openai_compatible"
    mock_config.enable_speaker_attribution = False
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        assert isinstance(orchestrator.transcriber, OpenAICompatibleTranscriber)

    # 4. Test Speaker-Attributed OpenAI init
    mock_config.transcriber_provider = "openai_compatible"
    mock_config.enable_speaker_attribution = True
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        assert isinstance(orchestrator.transcriber, SpeakerAttributedOpenAICompatibleTranscriber)

    # 5. Test CrispASR CLI init
    mock_config.transcriber_provider = "crispasr_cli"
    mock_config.transcriber_crispasr_path = "/path/to/crispasr"
    mock_config.transcriber_backend = "whisper"
    mock_config.transcriber_diarize_method = "pyannote"
    mock_config.transcriber_model = "my-model.gguf"
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        assert isinstance(orchestrator.transcriber, CrispASRCLITranscriber)
        assert orchestrator.transcriber.binary_path == "/path/to/crispasr"
        assert orchestrator.transcriber.model == "my-model.gguf"
        assert orchestrator.transcriber.backend == "whisper"
        assert orchestrator.transcriber.diarize_method == "pyannote"

    # 6. Test VibeVoice init
    mock_config.transcriber_provider = "vibevoice"
    mock_config.hotwords = "hello, world"
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        assert isinstance(orchestrator.transcriber, VibeVoiceASRTranscriber)
        assert orchestrator.transcriber.hotwords == "hello, world"

def test_orchestrator_init_post_processors(mock_config):
    # 1. Test Gemini init
    mock_config.post_processor_provider = "gemini"
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        assert isinstance(orchestrator.post_processor, GeminiPostProcessor)

    # 2. Test OpenAI init
    mock_config.post_processor_provider = "openai_compatible"
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        assert isinstance(orchestrator.post_processor, OpenAICompatiblePostProcessor)

def test_orchestrator_unsupported_providers(mock_config):
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        # Unsupported transcriber
        mock_config.transcriber_provider = "invalid_provider"
        with pytest.raises(ValueError, match="Unsupported transcriber provider"):
            Orchestrator(mock_config)

        # Reset transcriber, test unsupported post-processor
        mock_config.transcriber_provider = "huggingface"
        mock_config.post_processor_provider = "invalid_provider"
        with pytest.raises(ValueError, match="Unsupported post-processor provider"):
            Orchestrator(mock_config)

def test_orchestrator_run_with_rss_feeds(mock_config):
    mock_config.rss_feeds = [{"url": "https://example.com/feed.xml"}]

    with patch.object(Orchestrator, "_init_transcriber"), \
         patch.object(Orchestrator, "_init_post_processor"), \
         patch("podscribe.orchestrator.AudioPreprocessor"), \
         patch("podscribe.orchestrator.RSSFetcher") as mock_fetcher_class:

        mock_fetcher = mock_fetcher_class.return_value
        # Simulate downloaded files
        mock_fetcher.sync_feeds.return_value = [Path("input/new_episode.mp3")]

        # Mock find_files to return empty so it stops after sync
        with patch.object(Orchestrator, "find_files", return_value=[]):
            orchestrator = Orchestrator(mock_config)
            orchestrator.run()

            # Verify RSSFetcher was created with correct input_dir
            mock_fetcher_class.assert_called_once_with(mock_config.input_dir)
            # Verify sync_feeds was called with correct feeds config
            mock_fetcher.sync_feeds.assert_called_once_with(mock_config.rss_feeds)

def test_orchestrator_prompt_file_not_found(mock_config):
    mock_config.prompt_file = "non_existent_prompt.md"
    with pytest.raises(FileNotFoundError, match="Prompt template file not found"):
        Orchestrator(mock_config)

def test_orchestrator_find_files_non_existent_input_dir(mock_config):
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        orchestrator.input_dir = Path("non_existent_directory_path_1234")
        # find_files should return []
        assert orchestrator.find_files() == []

def test_orchestrator_run_preprocessed_file_missing(mock_config, tmp_path):
    from podscribe.state import StateManager

    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio")

    # Preprocessed path inside state
    missing_preprocessed_file = tmp_path / "podcast_preprocessed.wav"

    # Set state as preprocessed but delete file
    state_mgr = StateManager(mock_config.output_dir)
    file_hash = state_mgr.get_file_hash(input_file)
    state_mgr.update_entry(
        "podcast.mp3",
        hash=file_hash,
        status="preprocessed",
        preprocessed_path=missing_preprocessed_file
    )

    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

         mock_preprocessor = mock_preprocessor_class.return_value
         mock_preprocessor.get_duration.return_value = 120.0
         new_preprocessed_file = tmp_path / "new_preprocessed.wav"
         new_preprocessed_file.write_text("fake_preprocessed")
         mock_preprocessor.preprocess.return_value = new_preprocessed_file

         mock_transcriber = MagicMock()
         mock_transcriber.transcribe.return_value = "raw transcript"
         mock_init_t.return_value = mock_transcriber

         mock_post_processor = MagicMock()
         mock_post_processor.post_process.return_value = ("final markdown", TokenUsage(0, 0, 0))
         mock_init_p.return_value = mock_post_processor

         orchestrator = Orchestrator(mock_config)
         orchestrator.run()

         # Verify preprocess was called again to recreate the file!
         mock_preprocessor.preprocess.assert_called_once_with(input_file, duration=120.0)
         state_mgr.load()
         assert state_mgr.get_entry("podcast.mp3")["preprocessed_path"] == str(new_preprocessed_file)

def test_orchestrator_run_transcription_failure(mock_config, tmp_path):
    from podscribe.state import StateManager

    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio")

    state_mgr = StateManager(mock_config.output_dir)
    file_hash = state_mgr.get_file_hash(input_file)

    # Prepopulate to preprocessed to bypass preprocessing mock serialize issue
    state_mgr.update_entry(
        "podcast.mp3",
        hash=file_hash,
        status="preprocessed",
        preprocessed_path=input_file
    )

    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

         mock_preprocessor = mock_preprocessor_class.return_value
         mock_preprocessor.get_duration.return_value = 120.0

         mock_transcriber = MagicMock()
         mock_transcriber.transcribe.side_effect = Exception("ASR down")
         mock_init_t.return_value = mock_transcriber

         mock_init_p.return_value = MagicMock()

         orchestrator = Orchestrator(mock_config)
         # Should complete loop gracefully despite individual file failure
         orchestrator.run()

         state_mgr.load()
         entry = state_mgr.get_entry("podcast.mp3")
         assert entry["status"] == "failed"
         assert "Transcription:" in entry["error"]

def test_orchestrator_run_post_processing_failure(mock_config, tmp_path):
    from podscribe.state import StateManager

    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio")

    state_mgr = StateManager(mock_config.output_dir)
    file_hash = state_mgr.get_file_hash(input_file)

    # Pre-populate state to "transcribed" with raw_transcript_path and hash
    raw_transcript_path = mock_config.output_dir / "raw_transcripts" / "podcast_raw.txt"
    raw_transcript_path.parent.mkdir(parents=True, exist_ok=True)
    raw_transcript_path.write_text("raw transcript")
    state_mgr.update_entry(
        "podcast.mp3",
        hash=file_hash,
        status="transcribed",
        raw_transcript_path=raw_transcript_path
    )

    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

         mock_preprocessor = mock_preprocessor_class.return_value
         mock_preprocessor.get_duration.return_value = 120.0

         mock_init_t.return_value = MagicMock()

         mock_post_processor = MagicMock()
         mock_post_processor.post_process.side_effect = Exception("Rate limit")
         mock_init_p.return_value = mock_post_processor

         orchestrator = Orchestrator(mock_config)
         orchestrator.run()

         state_mgr.load()
         entry = state_mgr.get_entry("podcast.mp3")
         assert entry["status"] == "failed"
         assert "Post-processing:" in entry["error"]

def test_orchestrator_run_raw_transcript_missing(mock_config, tmp_path):
    from podscribe.state import StateManager

    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio")

    state_mgr = StateManager(mock_config.output_dir)
    file_hash = state_mgr.get_file_hash(input_file)

    # Setup pre-existing transcribed state but delete transcript file, and set preprocessed_path
    missing_raw_path = mock_config.output_dir / "raw_transcripts" / "podcast_raw.txt"
    state_mgr.update_entry(
        "podcast.mp3",
        hash=file_hash,
        status="transcribed",
        preprocessed_path=input_file,
        raw_transcript_path=missing_raw_path
    )

    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

         mock_preprocessor = mock_preprocessor_class.return_value
         mock_preprocessor.get_duration.return_value = 120.0
         mock_preprocessor.preprocess.return_value = input_file

         mock_transcriber = MagicMock()
         mock_transcriber.transcribe.return_value = "new transcript"
         mock_init_t.return_value = mock_transcriber

         mock_post_processor = MagicMock()
         mock_post_processor.post_process.return_value = ("final MD", TokenUsage(1, 1, 2))
         mock_init_p.return_value = mock_post_processor

         orchestrator = Orchestrator(mock_config)
         orchestrator.run()

         # Verify transcribe was called to recreate the missing file
         mock_transcriber.transcribe.assert_called_once()
         assert missing_raw_path.exists()
         assert missing_raw_path.read_text() == "new transcript"

def test_orchestrator_run_stage_transcribe(mock_config, tmp_path):
    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio_content")

    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "raw transcript text"
        mock_init_t.return_value = mock_transcriber

        mock_post_processor = MagicMock()
        mock_init_p.return_value = mock_post_processor

        mock_preprocessor = mock_preprocessor_class.return_value
        preprocessed_file = mock_config.output_dir / "preprocessed" / "podcast_16k_mono.wav"
        mock_preprocessor.preprocess.return_value = preprocessed_file
        mock_preprocessor.get_duration.return_value = 120.0

        # Run with stage="transcribe"
        orchestrator = Orchestrator(mock_config, stage="transcribe")
        orchestrator.run()

        # Verifications
        mock_preprocessor.preprocess.assert_called_once_with(input_file, duration=120.0)
        mock_transcriber.transcribe.assert_called_once_with(preprocessed_file)
        mock_post_processor.post_process.assert_not_called()

        # Intermediate raw transcript should be saved
        raw_transcript_file = mock_config.output_dir / "raw_transcripts" / "podcast_raw.txt"
        assert raw_transcript_file.exists()
        assert raw_transcript_file.read_text() == "raw transcript text"

        # Final transcript should NOT be saved
        final_transcript_file = mock_config.output_dir / "podcast_final.md"
        assert not final_transcript_file.exists()

        # State should be "transcribed"
        state_file = mock_config.output_dir / "state.json"
        assert state_file.exists()
        import json
        with open(state_file, "r") as f:
            state = json.load(f)
            assert state["podcast.mp3"]["status"] == "transcribed"
            assert state["podcast.mp3"]["preprocessed_path"] == str(preprocessed_file)
            assert state["podcast.mp3"]["raw_transcript_path"] == str(raw_transcript_file)
            assert state["podcast.mp3"]["final_transcript_path"] == ""

def test_orchestrator_run_stage_postprocess_success(mock_config, tmp_path):
    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio_content")

    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

        mock_transcriber = MagicMock()
        mock_init_t.return_value = mock_transcriber

        mock_post_processor = MagicMock()
        mock_post_processor.post_process.return_value = ("polished markdown text", TokenUsage(10, 5, 15))
        mock_init_p.return_value = mock_post_processor

        mock_preprocessor = mock_preprocessor_class.return_value
        mock_preprocessor.get_duration.return_value = 120.0

        # Setup pre-existing raw transcript
        raw_transcript_file = mock_config.output_dir / "raw_transcripts" / "podcast_raw.txt"
        raw_transcript_file.parent.mkdir(parents=True, exist_ok=True)
        raw_transcript_file.write_text("saved raw transcript")

        # Run with stage="postprocess"
        orchestrator = Orchestrator(mock_config, stage="postprocess")
        orchestrator.run()

        # Verifications
        mock_preprocessor.preprocess.assert_not_called()
        mock_transcriber.transcribe.assert_not_called()
        mock_post_processor.post_process.assert_called_once_with(
            "saved raw transcript",
            "Format this: {{TRANSCRIPT}}",
            context={"filename": "podcast.mp3"}
        )

        # Final transcript should be saved
        final_transcript_file = mock_config.output_dir / "podcast_final.md"
        assert final_transcript_file.exists()
        assert final_transcript_file.read_text() == "polished markdown text"

        # State should be "completed"
        state_file = mock_config.output_dir / "state.json"
        import json
        with open(state_file, "r") as f:
            state = json.load(f)
            assert state["podcast.mp3"]["status"] == "completed"
            assert state["podcast.mp3"]["raw_transcript_path"] == str(raw_transcript_file)
            assert state["podcast.mp3"]["final_transcript_path"] == str(final_transcript_file)

def test_orchestrator_run_stage_postprocess_when_failed_status(mock_config, tmp_path):
    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio_content")

    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

        mock_transcriber = MagicMock()
        mock_init_t.return_value = mock_transcriber

        mock_post_processor = MagicMock()
        mock_post_processor.post_process.return_value = ("polished markdown text", TokenUsage(10, 5, 15))
        mock_init_p.return_value = mock_post_processor

        mock_preprocessor = mock_preprocessor_class.return_value
        mock_preprocessor.get_duration.return_value = 120.0

        raw_transcript_file = mock_config.output_dir / "raw_transcripts" / "podcast_raw.txt"
        raw_transcript_file.parent.mkdir(parents=True, exist_ok=True)
        raw_transcript_file.write_text("saved raw transcript")

        # Create pre-existing state with status="failed" (e.g. from previous failed post-processing)
        state_file = mock_config.output_dir / "state.json"
        import hashlib
        import json
        file_hash = hashlib.sha256(input_file.read_bytes()).hexdigest()
        state_file.write_text(json.dumps({
            "podcast.mp3": {
                "hash": file_hash,
                "status": "failed",
                "raw_transcript_path": str(raw_transcript_file)
            }
        }))

        orchestrator = Orchestrator(mock_config, stage="postprocess")
        orchestrator.run()

        mock_post_processor.post_process.assert_called_once()
        with open(state_file, "r") as f:
            state = json.load(f)
            assert state["podcast.mp3"]["status"] == "completed"

def test_orchestrator_run_stage_postprocess_missing_raw(mock_config, tmp_path):
    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio_content")

    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

        mock_transcriber = MagicMock()
        mock_init_t.return_value = mock_transcriber
        mock_post_processor = MagicMock()
        mock_init_p.return_value = mock_post_processor
        mock_preprocessor = mock_preprocessor_class.return_value
        mock_preprocessor.get_duration.return_value = 120.0

        # Run with stage="postprocess" (raw transcript is NOT created)
        orchestrator = Orchestrator(mock_config, stage="postprocess")
        orchestrator.run()

        # Verifications
        mock_preprocessor.preprocess.assert_not_called()
        mock_transcriber.transcribe.assert_not_called()
        mock_post_processor.post_process.assert_not_called()

        # State should be "failed"
        state_file = mock_config.output_dir / "state.json"
        assert state_file.exists()
        import json
        with open(state_file, "r") as f:
            state = json.load(f)
            assert state["podcast.mp3"]["status"] == "failed"
            assert "Post-processing setup: Raw transcript not found" in state["podcast.mp3"]["error"]

def test_orchestrator_run_dependencies_check_missing_ffmpeg(mock_config):
    # Setup mock config with preprocess enabled and stage 'all' (default)
    mock_config.preprocess_enabled = True

    with patch.object(Orchestrator, "_init_transcriber"), \
         patch.object(Orchestrator, "_init_post_processor"), \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class:

        mock_preprocessor = mock_preprocessor_class.return_value
        # Simulate ffmpeg NOT available
        mock_preprocessor.is_ffmpeg_available.return_value = False

        orchestrator = Orchestrator(mock_config)

        with pytest.raises(RuntimeError, match="FFmpeg executable 'ffmpeg' not found, but preprocessing is enabled"):
            orchestrator.run()

def test_orchestrator_run_dependencies_check_missing_ffmpeg_but_disabled(mock_config):
    # Setup mock config with preprocess DISABLED
    mock_config.preprocess_enabled = False

    with patch.object(Orchestrator, "_init_transcriber"), \
         patch.object(Orchestrator, "_init_post_processor"), \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class, \
         patch.object(Orchestrator, "find_files", return_value=[]):

        mock_preprocessor = mock_preprocessor_class.return_value
        # Simulate ffmpeg NOT available
        mock_preprocessor.is_ffmpeg_available.return_value = False

        orchestrator = Orchestrator(mock_config)
        # Should NOT raise RuntimeError because preprocessing is disabled
        orchestrator.run()

def test_orchestrator_run_dependencies_check_missing_ffmpeg_stage_postprocess(mock_config):
    # Setup mock config with preprocess enabled, but stage is 'postprocess'
    mock_config.preprocess_enabled = True

    with patch.object(Orchestrator, "_init_transcriber"), \
         patch.object(Orchestrator, "_init_post_processor"), \
         patch("podscribe.orchestrator.AudioPreprocessor") as mock_preprocessor_class, \
         patch.object(Orchestrator, "find_files", return_value=[]):

        mock_preprocessor = mock_preprocessor_class.return_value
        # Simulate ffmpeg NOT available
        mock_preprocessor.is_ffmpeg_available.return_value = False

        orchestrator = Orchestrator(mock_config, stage="postprocess")
        # Should NOT raise RuntimeError because stage is 'postprocess' (FFmpeg not needed)
        orchestrator.run()

def test_count_words_and_segments():
    from podscribe.orchestrator import count_words_and_segments

    # Empty
    assert count_words_and_segments("") == (0, 0)
    assert count_words_and_segments("   \n ") == (0, 0)

    # Non-speaker-attributed single paragraph
    assert count_words_and_segments("Hello world transcript.") == (3, 1)

    # Non-speaker-attributed multiple paragraphs
    assert count_words_and_segments("Hello world.\n\nThis is paragraph two.") == (6, 2)

    # Speaker-attributed
    transcript = "[Speaker 1]: Hello there.\n\n[Speaker 2]: Hi! How are you?"
    assert count_words_and_segments(transcript) == (6, 2)

    # Speaker-attributed with more complex name
    transcript_complex = "[Speaker A. Name]: Yes.\n\n[Speaker B]: No."
    assert count_words_and_segments(transcript_complex) == (2, 2)

def test_print_summary_report_logs_words_and_segments(mock_config, tmp_path, caplog):
    import logging
    caplog.set_level(logging.INFO)

    with patch.object(Orchestrator, "_init_transcriber"), \
         patch.object(Orchestrator, "_init_post_processor"):
        orchestrator = Orchestrator(mock_config)

        # Populate state.json with 2 entries
        orchestrator.state_manager.update_entry(
            "file1.mp3",
            status="completed",
            audio_duration=60.0,
            num_words=100,
            num_segments=10,
            token_usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )
        orchestrator.state_manager.update_entry(
            "file2.mp3",
            status="transcribed",
            audio_duration=120.0,
            num_words=250,
            num_segments=25
        )

        orchestrator.print_summary_report([Path("file1.mp3"), Path("file2.mp3")])

        log_text = caplog.text
        assert "Transcribed Words: 350" in log_text
        assert "Segments:          35" in log_text

def test_print_summary_report_logs_words_and_segments_fallback(mock_config, tmp_path, caplog):
    import logging
    caplog.set_level(logging.INFO)

    with patch.object(Orchestrator, "_init_transcriber"), \
         patch.object(Orchestrator, "_init_post_processor"):
        orchestrator = Orchestrator(mock_config)

        # Write dummy raw transcript files
        raw_dir = tmp_path / "output" / "raw_transcripts"
        raw_dir.mkdir(parents=True, exist_ok=True)

        raw_file1 = raw_dir / "file1_raw.txt"
        raw_file1.write_text("[Speaker 1]: Hello world.\n\n[Speaker 2]: Hey.") # 3 words, 2 segments

        raw_file2 = raw_dir / "file2_raw.txt"
        raw_file2.write_text("Just plain transcript text.") # 4 words, 1 segment

        # Populate state with missing num_words/num_segments but valid raw_transcript_path
        orchestrator.state_manager.update_entry(
            "file1.mp3",
            status="completed",
            audio_duration=60.0,
            raw_transcript_path=raw_file1,
            token_usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )
        orchestrator.state_manager.update_entry(
            "file2.mp3",
            status="transcribed",
            audio_duration=120.0,
            raw_transcript_path=raw_file2
        )

        # Before print, state shouldn't have the counts
        assert "num_words" not in orchestrator.state_manager.get_entry("file1.mp3")

        orchestrator.print_summary_report([Path("file1.mp3"), Path("file2.mp3")])

        log_text = caplog.text
        assert "Transcribed Words: 7" in log_text
        assert "Segments:          3" in log_text

        # State should be updated now
        entry1 = orchestrator.state_manager.get_entry("file1.mp3")
        assert entry1["num_words"] == 3
        assert entry1["num_segments"] == 2

