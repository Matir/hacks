import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from src.config import Config
from src.orchestrator import Orchestrator
from src.transcribers import HuggingFaceTranscriber, OpenAICompatibleTranscriber
from src.post_processors import GeminiPostProcessor, OpenAICompatiblePostProcessor

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
         patch("src.orchestrator.AudioPreprocessor") as mock_preprocessor_class:
         
        # Setup transcriber mock
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "raw transcript text"
        mock_init_t.return_value = mock_transcriber
        
        # Setup post-processor mock
        mock_post_processor = MagicMock()
        mock_post_processor.post_process.return_value = "polished markdown text"
        mock_init_p.return_value = mock_post_processor
        
        # Setup preprocessor mock instance
        mock_preprocessor = mock_preprocessor_class.return_value
        preprocessed_file = mock_config.output_dir / "preprocessed" / "podcast_16k_mono.wav"
        mock_preprocessor.preprocess.return_value = preprocessed_file
        
        # Instantiate and run Orchestrator
        orchestrator = Orchestrator(mock_config)
        orchestrator.run()
        
        # --- Verifications ---
        # 1. Preprocessor should have been called
        mock_preprocessor.preprocess.assert_called_once_with(input_file)
        
        # 2. Transcriber should have been called with the preprocessed file
        mock_transcriber.transcribe.assert_called_once_with(preprocessed_file)
        
        # 3. Intermediate raw transcript should be saved
        raw_transcript_file = mock_config.output_dir / "raw_transcripts" / "podcast_raw.txt"
        assert raw_transcript_file.exists()
        assert raw_transcript_file.read_text() == "raw transcript text"
        
        # 4. Post-processor should have been called with raw transcript and prompt template
        mock_post_processor.post_process.assert_called_once_with(
            "raw transcript text",
            "Format this: {{TRANSCRIPT}}"
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

def test_orchestrator_run_skips_completed(mock_config, tmp_path):
    input_dir = mock_config.input_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    input_file = input_dir / "podcast.mp3"
    input_file.write_text("fake_audio_content")
    
    # Setup mocks
    with patch.object(Orchestrator, "_init_transcriber") as mock_init_t, \
         patch.object(Orchestrator, "_init_post_processor") as mock_init_p, \
         patch("src.orchestrator.AudioPreprocessor") as mock_preprocessor_class:
         
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
         patch("src.orchestrator.AudioPreprocessor") as mock_preprocessor_class:
         
        mock_transcriber = MagicMock()
        mock_init_t.return_value = mock_transcriber
        
        mock_post_processor = MagicMock()
        mock_post_processor.post_process.return_value = "polished markdown text"
        mock_init_p.return_value = mock_post_processor
        mock_preprocessor = mock_preprocessor_class.return_value
        
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
            "Format this: {{TRANSCRIPT}}"
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
         patch("src.orchestrator.AudioPreprocessor") as mock_preprocessor_class:
         
        mock_transcriber = MagicMock()
        mock_transcriber.transcribe.return_value = "raw transcript"
        mock_init_t.return_value = mock_transcriber
        
        mock_post_processor = MagicMock()
        mock_post_processor.post_process.return_value = "polished text"
        mock_init_p.return_value = mock_post_processor
        
        # Preprocessor mock
        mock_preprocessor = mock_preprocessor_class.return_value
        
        # Configure preprocessor to FAIL on file1, but succeed on file2
        def preprocess_side_effect(file_path):
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
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        assert isinstance(orchestrator.transcriber, HuggingFaceTranscriber)
        
    # 2. Test OpenAI init
    mock_config.transcriber_provider = "openai_compatible"
    with patch.object(Orchestrator, "_load_prompt_template", return_value=""):
        orchestrator = Orchestrator(mock_config)
        assert isinstance(orchestrator.transcriber, OpenAICompatibleTranscriber)

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
         patch("src.orchestrator.RSSFetcher") as mock_fetcher_class:
         
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
