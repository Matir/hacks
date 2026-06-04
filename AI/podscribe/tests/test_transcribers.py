from pathlib import Path
from unittest.mock import patch, MagicMock
import httpx
import pytest
from podscribe.transcribers import HuggingFaceTranscriber, SpeakerAttributedHuggingFaceTranscriber, OpenAICompatibleTranscriber, SpeakerAttributedOpenAICompatibleTranscriber, CrispASRTranscriber, CrispASRCLITranscriber

# ----------------------------------------------------------------------
# Hugging Face Transcriber Tests
# ----------------------------------------------------------------------

def test_hf_transcriber_init():
    transcriber = HuggingFaceTranscriber(
        endpoint_url="https://api-inference.huggingface.co/models/model",
        api_key="hf_key",
        model="model"
    )
    assert transcriber.endpoint_url == "https://api-inference.huggingface.co/models/model"
    assert transcriber.api_key == "hf_key"
    assert transcriber.model == "model"

def test_hf_transcriber_missing_url():
    transcriber = HuggingFaceTranscriber(endpoint_url="", api_key="", model="")
    with pytest.raises(ValueError, match="Hugging Face endpoint URL must be configured"):
        transcriber.transcribe(Path("dummy.wav"))

def test_hf_transcribe_success(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio_data")
    
    endpoint = "https://api-inference.huggingface.co/models/model"
    transcriber = HuggingFaceTranscriber(endpoint_url=endpoint, api_key="hf_key", model="model")
    
    # Mock httpx post
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simulate standard HF response
        mock_response.json.return_value = {"text": "hello world transcript"}
        mock_client.post.return_value = mock_response
        
        result = transcriber.transcribe(audio_file)
        
        assert result == "hello world transcript"
        mock_client.post.assert_called_once_with(
            endpoint,
            headers={"Authorization": "Bearer hf_key"},
            content=b"fake_audio_data"
        )

def test_hf_transcribe_list_response(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio_data")
    
    transcriber = HuggingFaceTranscriber(endpoint_url="https://api.hf.co", api_key="key", model="model")
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        # HF sometimes returns a list with one dict
        mock_response.json.return_value = [{"text": "transcript in list"}]
        mock_client.post.return_value = mock_response
        
        result = transcriber.transcribe(audio_file)
        assert result == "transcript in list"

def test_hf_transcribe_failure(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    transcriber = HuggingFaceTranscriber(endpoint_url="https://api.hf.co", api_key="key", model="model")
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        # raise_for_status raising HTTPStatusError is simulated
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message="500 Error",
            request=MagicMock(),
            response=mock_response
        )
        mock_client.post.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Hugging Face transcription failed"):
            transcriber.transcribe(audio_file)


# ----------------------------------------------------------------------
# OpenAI Compatible Transcriber Tests
# ----------------------------------------------------------------------

def test_openai_transcriber_url_sanitization():
    # Standard base URL should remain unchanged
    t1 = OpenAICompatibleTranscriber("https://api.baseten.co/v1", "key", "model")
    assert t1.endpoint_url == "https://api.baseten.co/v1"
    
    # Trailing slash should be stripped
    t2 = OpenAICompatibleTranscriber("https://api.baseten.co/v1/", "key", "model")
    assert t2.endpoint_url == "https://api.baseten.co/v1"
    
    # Trailing /audio/transcriptions should be stripped
    t3 = OpenAICompatibleTranscriber("https://api.baseten.co/v1/audio/transcriptions", "key", "model")
    assert t3.endpoint_url == "https://api.baseten.co/v1"
    
    # Trailing /audio/transcriptions/ with slash should be stripped
    t4 = OpenAICompatibleTranscriber("https://api.baseten.co/v1/audio/transcriptions/", "key", "model")
    assert t4.endpoint_url == "https://api.baseten.co/v1"

def test_openai_transcribe_success(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    transcriber = OpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="my-key",
        model="granite-speech"
    )
    
    # Mock the OpenAI client
    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        
        # Mock client.audio.transcriptions.create
        mock_transcriptions = mock_client.audio.transcriptions
        mock_response = MagicMock()
        mock_response.text = "openai transcript output"
        mock_transcriptions.create.return_value = mock_response
        
        result = transcriber.transcribe(audio_file)
        
        assert result == "openai transcript output"
        mock_openai_class.assert_called_once_with(
            base_url="https://api.baseten.co/v1",
            api_key="my-key"
        )
        # Verify create arguments
        mock_transcriptions.create.assert_called_once()
        call_args = mock_transcriptions.create.call_args[1]
        assert call_args["model"] == "granite-speech"
        assert call_args["response_format"] == "text"
        assert call_args["language"] == "en"
        # File is opened in transcribe(), so we check it's a file object
        assert hasattr(call_args["file"], "read")

def test_openai_transcribe_custom_language(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    transcriber = OpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="my-key",
        model="granite-speech",
        language="es"
    )
    
    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_transcriptions = mock_client.audio.transcriptions
        mock_response = MagicMock()
        mock_response.text = "spanish transcript"
        mock_transcriptions.create.return_value = mock_response
        
        result = transcriber.transcribe(audio_file)
        
        assert result == "spanish transcript"
        call_args = mock_transcriptions.create.call_args[1]
        assert call_args["language"] == "es"

def test_openai_transcribe_dummy_key_fallback(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    # Empty API key
    transcriber = OpenAICompatibleTranscriber(
        endpoint_url="http://localhost:8000/v1",
        api_key="",
        model="model"
    )
    
    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_client.audio.transcriptions.create.return_value = "transcript"
        
        transcriber.transcribe(audio_file)
        
        # Should use "dummy-key" fallback
        mock_openai_class.assert_called_once_with(
            base_url="http://localhost:8000/v1",
            api_key="dummy-key"
        )

def test_hf_transcribe_unexpected_response(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    transcriber = HuggingFaceTranscriber(endpoint_url="https://api.hf.co", api_key="key", model="model")
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Unexpected JSON structure (not a dict with "text" or list with "text")
        mock_response.json.return_value = {"error_or_something_else": "value"}
        mock_client.post.return_value = mock_response
        
        # Should fallback to returning str(result)
        result = transcriber.transcribe(audio_file)
        assert "error_or_something_else" in result

def test_openai_transcribe_missing_url():
    transcriber = OpenAICompatibleTranscriber(endpoint_url="", api_key="key", model="model")
    with pytest.raises(ValueError, match="OpenAI Compatible endpoint URL must be configured"):
        transcriber.transcribe(Path("dummy.wav"))

def test_openai_transcribe_unexpected_response(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    transcriber = OpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model"
    )
    
    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        # Return something that is neither str nor has .text attribute
        mock_client.audio.transcriptions.create.return_value = {"unexpected": "dict"}
        
        result = transcriber.transcribe(audio_file)
        assert "unexpected" in result

def test_openai_transcribe_failure(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    transcriber = OpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model"
    )
    
    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        # Simulate API error
        mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError, match="OpenAI-compatible transcription failed: API Error"):
            transcriber.transcribe(audio_file)

# ----------------------------------------------------------------------
# Speaker Attributed OpenAI Compatible Transcriber Tests
# ----------------------------------------------------------------------

def test_speaker_attributed_transcribe_success_dict(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_response = MagicMock()
        # Return a mock segments list where segments are dicts
        mock_response.segments = [
            {"speaker": "0", "text": " Hello "},
            {"speaker": "0", "text": " there. "},
            {"speaker": "1", "text": " Hi!"},
            {"speaker": "0", "text": " How are things?"}
        ]
        mock_client.audio.transcriptions.create.return_value = mock_response

        result = transcriber.transcribe(audio_file)
        # Should group consecutive segments by same speaker
        assert result == "[Speaker 0]: Hello there.\n\n[Speaker 1]: Hi!\n\n[Speaker 0]: How are things?"
        
        # Verify verbose_json format and diarize options were passed
        call_args = mock_client.audio.transcriptions.create.call_args[1]
        assert call_args["response_format"] == "verbose_json"
        assert call_args["extra_body"] == {"diarize": True}
        assert call_args["language"] == "en"

def test_speaker_attributed_transcribe_custom_language(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model",
        language="es"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_response = MagicMock()
        mock_response.segments = [
            {"speaker": "0", "text": "Hola amigo"}
        ]
        mock_client.audio.transcriptions.create.return_value = mock_response

        result = transcriber.transcribe(audio_file)
        assert result == "[Speaker 0]: Hola amigo"
        
        call_args = mock_client.audio.transcriptions.create.call_args[1]
        assert call_args["language"] == "es"

def test_speaker_attributed_transcribe_success_objects(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_response = MagicMock()
        
        # Return a mock segments list where segments are objects
        seg1 = MagicMock()
        seg1.speaker = None
        seg1.speaker_id = "Speaker A"
        seg1.text = "Hello"

        seg2 = MagicMock()
        seg2.speaker = None
        seg2.speaker_id = None
        seg2.speaker_label = "Speaker B"
        seg2.text = "Hey"

        mock_response.segments = [seg1, seg2]
        mock_client.audio.transcriptions.create.return_value = mock_response

        result = transcriber.transcribe(audio_file)
        assert result == "[Speaker A]: Hello\n\n[Speaker B]: Hey"

def test_speaker_attributed_transcribe_missing_url():
    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(endpoint_url="", api_key="key", model="model")
    with pytest.raises(ValueError, match="OpenAI Compatible endpoint URL must be configured"):
        transcriber.transcribe(Path("dummy.wav"))

def test_speaker_attributed_transcribe_fallback_text(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_response = MagicMock()
        # No segments
        mock_response.segments = None
        mock_response.text = "fallback raw text"
        mock_client.audio.transcriptions.create.return_value = mock_response

        result = transcriber.transcribe(audio_file)
        assert result == "fallback raw text"

def test_speaker_attributed_transcribe_failure(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_client.audio.transcriptions.create.side_effect = Exception("Rate limit")

        with pytest.raises(RuntimeError, match="Speaker attributed OpenAI-compatible transcription failed"):
            transcriber.transcribe(audio_file)

def test_speaker_attributed_transcribe_raw_string(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        # API returns a direct string response
        mock_client.audio.transcriptions.create.return_value = "direct raw string transcript"

        result = transcriber.transcribe(audio_file)
        assert result == "direct raw string transcript"

def test_speaker_attributed_transcribe_dict_response(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        # API returns a dictionary response
        mock_client.audio.transcriptions.create.return_value = {
            "segments": [
                {"speaker": 0, "text": "Hello"},
                {"speaker": 1.0, "text": "Hi"}
            ]
        }

        result = transcriber.transcribe(audio_file)
        assert result == "[Speaker 0]: Hello\n\n[Speaker 1.0]: Hi"

def test_speaker_attributed_transcribe_no_segments_fallbacks(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        
        # 1. Test dictionary response with 'text' field but no segments
        mock_client.audio.transcriptions.create.return_value = {
            "text": "fallback text in dict"
        }
        result = transcriber.transcribe(audio_file)
        assert result == "fallback text in dict"

        # 2. Test raw dictionary fallback
        mock_client.audio.transcriptions.create.return_value = {
            "unknown_key": "value"
        }
        result = transcriber.transcribe(audio_file)
        assert "unknown_key" in result

def test_speaker_attributed_transcribe_empty_and_ignored_segments(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(
        endpoint_url="https://api.baseten.co/v1",
        api_key="key",
        model="model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_response = MagicMock()
        
        # Mix of empty text, no speaker, float/int speaker label, and ignored text
        mock_response.segments = [
            {"speaker": None, "text": "  "}, # ignored
            {"speaker": None, "text": "Hello"}, # Speaker Unknown
            {"speaker": 1, "text": ""}, # ignored
            {"speaker": "Bob", "text": "Howdy"} # string name
        ]
        mock_client.audio.transcriptions.create.return_value = mock_response

        result = transcriber.transcribe(audio_file)
        assert result == "[Speaker Unknown]: Hello\n\n[Bob]: Howdy"

# ----------------------------------------------------------------------
# Sequential Directory Transcribing & Rolling Context Tests
# ----------------------------------------------------------------------

def test_hf_transcribe_directory(tmp_path):
    dir_path = tmp_path / "chunks"
    dir_path.mkdir()
    
    # Create two chunk files
    (dir_path / "chunk_001.wav").write_bytes(b"audio1")
    (dir_path / "chunk_002.wav").write_bytes(b"audio2")
    
    transcriber = HuggingFaceTranscriber(endpoint_url="https://api.hf.co", api_key="key", model="model")
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        
        # Configure successive responses
        resp1 = MagicMock()
        resp1.status_code = 200
        resp1.json.return_value = {"text": "Hello"}
        
        resp2 = MagicMock()
        resp2.status_code = 200
        resp2.json.return_value = {"text": "world"}
        
        mock_client.post.side_effect = [resp1, resp2]
        
        result = transcriber.transcribe(dir_path)
        assert result == "Hello world"
        assert mock_client.post.call_count == 2

def test_openai_transcribe_directory_rolling_context(tmp_path):
    dir_path = tmp_path / "chunks"
    dir_path.mkdir()
    (dir_path / "chunk_001.wav").write_bytes(b"audio1")
    (dir_path / "chunk_002.wav").write_bytes(b"audio2")
    (dir_path / "chunk_003.wav").write_bytes(b"audio3")
    
    transcriber = OpenAICompatibleTranscriber(endpoint_url="https://api.baseten.co/v1", api_key="key", model="model")
    
    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        
        # Mock standard text return value
        mock_client.audio.transcriptions.create.side_effect = [
            "First chunk text.",
            "Second chunk text.",
            "Third chunk text."
        ]
        
        result = transcriber.transcribe(dir_path)
        assert result == "First chunk text. Second chunk text. Third chunk text."
        
        # Verify rolling context was passed
        assert mock_client.audio.transcriptions.create.call_count == 3
        calls = mock_client.audio.transcriptions.create.call_args_list
        
        # First call: no prompt/prefix_text
        assert calls[0][1]["prompt"] is None
        assert calls[0][1]["extra_body"] is None
        
        # Second call: receives first transcript as prompt/prefix_text
        assert calls[1][1]["prompt"] == "First chunk text."
        assert calls[1][1]["extra_body"] == {"prefix_text": "First chunk text."}

        # Third call: receives first + second transcript as prompt/prefix_text
        assert calls[2][1]["prompt"] == "First chunk text. Second chunk text."
        assert calls[2][1]["extra_body"] == {"prefix_text": "First chunk text. Second chunk text."}

def test_speaker_attributed_transcribe_directory_rolling_context(tmp_path):
    dir_path = tmp_path / "chunks"
    dir_path.mkdir()
    (dir_path / "chunk_001.wav").write_bytes(b"audio1")
    (dir_path / "chunk_002.wav").write_bytes(b"audio2")
    (dir_path / "chunk_003.wav").write_bytes(b"audio3")
    
    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(endpoint_url="https://api.baseten.co/v1", api_key="key", model="model")
    
    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        
        # Return mock segments (dicts)
        mock_resp1 = {
            "segments": [{"speaker": 0, "text": "Hello David"}]
        }
        mock_resp2 = {
            "segments": [{"speaker": 1, "text": "Hi Sarah"}]
        }
        mock_resp3 = {
            "segments": [{"speaker": 0, "text": "Welcome back"}]
        }
        mock_client.audio.transcriptions.create.side_effect = [mock_resp1, mock_resp2, mock_resp3]
        
        result = transcriber.transcribe(dir_path)
        assert result == "[Speaker 0]: Hello David\n\n[Speaker 1]: Hi Sarah\n\n[Speaker 0]: Welcome back"
        
        # Verify rolling context preserves the "[Speaker 0]: " tags
        assert mock_client.audio.transcriptions.create.call_count == 3
        calls = mock_client.audio.transcriptions.create.call_args_list
        
        assert calls[0][1]["prompt"] is None
        
        # Second call should receive "[Speaker 0]: Hello David" (speaker tag kept)
        assert calls[1][1]["prompt"] == "[Speaker 0]: Hello David"
        assert calls[1][1]["extra_body"] == {"diarize": True, "prefix_text": "[Speaker 0]: Hello David"}

        # Third call should receive entire accumulated transcript so far
        assert calls[2][1]["prompt"] == "[Speaker 0]: Hello David\n\n[Speaker 1]: Hi Sarah"
        assert calls[2][1]["extra_body"] == {"diarize": True, "prefix_text": "[Speaker 0]: Hello David\n\n[Speaker 1]: Hi Sarah"}

def test_hf_transcribe_debug_logging(tmp_path, caplog):
    import logging
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio_data")
    
    transcriber = HuggingFaceTranscriber(endpoint_url="https://api.hf.co", api_key="key", model="model")
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "hello"}
        mock_client.post.return_value = mock_response
        
        # Test with INFO level (should NOT show debug log)
        with caplog.at_level(logging.INFO):
            transcriber.transcribe(audio_file)
            assert not any("Sending audio chunk" in record.message for record in caplog.records)
            
        caplog.clear()
        
        # Test with DEBUG level (should show debug log)
        with caplog.at_level(logging.DEBUG):
            transcriber.transcribe(audio_file)
            assert any("Sending audio chunk test.wav to Hugging Face ASR pipeline" in record.message for record in caplog.records)

def test_openai_transcribe_debug_logging(tmp_path, caplog):
    import logging
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio_data")
    
    transcriber = OpenAICompatibleTranscriber(endpoint_url="https://api.openai.com/v1", api_key="key", model="model")
    
    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_client.audio.transcriptions.create.return_value = MagicMock(text="hello")
        
        # Test with INFO level (should NOT show debug log)
        with caplog.at_level(logging.INFO):
            transcriber.transcribe(audio_file)
            assert not any("Sending audio chunk" in record.message for record in caplog.records)
            
        caplog.clear()
        
        # Test with DEBUG level (should show debug log)
        with caplog.at_level(logging.DEBUG):
            transcriber.transcribe(audio_file)
            assert any("Sending audio chunk test.wav to OpenAI-compatible ASR pipeline" in record.message for record in caplog.records)

def test_speaker_attributed_openai_transcribe_debug_logging(tmp_path, caplog):
    import logging
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio_data")
    
    transcriber = SpeakerAttributedOpenAICompatibleTranscriber(endpoint_url="https://api.openai.com/v1", api_key="key", model="model")
    
    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_client.audio.transcriptions.create.return_value = MagicMock(text="hello", segments=[])
        
        # Test with INFO level (should NOT show debug log)
        with caplog.at_level(logging.INFO):
            transcriber.transcribe(audio_file)
            assert not any("Sending audio chunk" in record.message for record in caplog.records)
            
        caplog.clear()
        
        # Test with DEBUG level (should show debug log)
        with caplog.at_level(logging.DEBUG):
            transcriber.transcribe(audio_file)
            assert any("Sending audio chunk test.wav to speaker-attributed OpenAI-compatible ASR pipeline" in record.message for record in caplog.records)

def test_speaker_attributed_hf_transcriber_init():
    transcriber = SpeakerAttributedHuggingFaceTranscriber(
        endpoint_url="https://api-inference.huggingface.co/models/model",
        api_key="hf_key",
        model="model"
    )
    assert transcriber.endpoint_url == "https://api-inference.huggingface.co/models/model"
    assert transcriber.api_key == "hf_key"
    assert transcriber.model == "model"

def test_speaker_attributed_hf_transcribe_success_segments(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    transcriber = SpeakerAttributedHuggingFaceTranscriber(
        endpoint_url="https://api.hf.co", api_key="key", model="model"
    )
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "segments": [
                {"speaker": 0, "text": "Hello"},
                {"speaker": 1, "text": "Hi there"},
                {"speaker": 0, "text": "How are you?"}
            ]
        }
        mock_client.post.return_value = mock_response
        
        result = transcriber.transcribe(audio_file)
        assert result == "[Speaker 0]: Hello\n\n[Speaker 1]: Hi there\n\n[Speaker 0]: How are you?"

def test_speaker_attributed_hf_transcribe_success_chunks(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    transcriber = SpeakerAttributedHuggingFaceTranscriber(
        endpoint_url="https://api.hf.co", api_key="key", model="model"
    )
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "chunks": [
                {"speaker": "SPEAKER_A", "text": "Line one"},
                {"speaker": "SPEAKER_B", "text": "Line two"},
                {"speaker": "SPEAKER_A", "text": "Line three"}
            ]
        }
        mock_client.post.return_value = mock_response
        
        result = transcriber.transcribe(audio_file)
        assert result == "[SPEAKER_A]: Line one\n\n[SPEAKER_B]: Line two\n\n[SPEAKER_A]: Line three"

def test_speaker_attributed_hf_transcribe_fallback(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    transcriber = SpeakerAttributedHuggingFaceTranscriber(
        endpoint_url="https://api.hf.co", api_key="key", model="model"
    )
    
    with patch("httpx.Client") as mock_client_class:
        mock_client = mock_client_class.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "raw text response without speaker attribution"}
        mock_client.post.return_value = mock_response
        
        result = transcriber.transcribe(audio_file)
        assert result == "raw text response without speaker attribution"

# ----------------------------------------------------------------------
# CrispASR Transcriber Tests
# ----------------------------------------------------------------------

def test_crispasr_transcribe_success_single_file(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = CrispASRTranscriber(
        endpoint_url="https://api.crispasr.ai/v1",
        api_key="crisp-key",
        model="crisp-model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        
        # Mock raw response
        mock_raw_response = MagicMock()
        mock_raw_response.http_response.json.return_value = {
            "text": "Hello world from CrispASR",
            "speaker": "Alice"
        }
        
        mock_client.audio.transcriptions.with_raw_response.create.return_value = mock_raw_response

        result = transcriber.transcribe(audio_file)
        assert result == "[Alice]: Hello world from CrispASR"
        
        mock_openai_class.assert_called_once_with(
            base_url="https://api.crispasr.ai/v1",
            api_key="crisp-key"
        )
        
        call_args = mock_client.audio.transcriptions.with_raw_response.create.call_args[1]
        assert call_args["model"] == "crisp-model"
        assert call_args["response_format"] == "verbose_json"
        assert call_args["extra_body"] == {"diarize": True}
        assert call_args["language"] == "en"

def test_crispasr_transcribe_custom_language(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = CrispASRTranscriber(
        endpoint_url="https://api.crispasr.ai/v1",
        api_key="crisp-key",
        model="crisp-model",
        language="es"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        
        mock_raw_response = MagicMock()
        mock_raw_response.http_response.json.return_value = {
            "text": "Hola mundo",
            "speaker": "Alice"
        }
        mock_client.audio.transcriptions.with_raw_response.create.return_value = mock_raw_response

        result = transcriber.transcribe(audio_file)
        assert result == "[Alice]: Hola mundo"
        
        call_args = mock_client.audio.transcriptions.with_raw_response.create.call_args[1]
        assert call_args["language"] == "es"

def test_crispasr_transcribe_success_directory(tmp_path):
    dir_path = tmp_path / "chunks"
    dir_path.mkdir()
    (dir_path / "chunk_001.wav").write_bytes(b"audio1")
    (dir_path / "chunk_002.wav").write_bytes(b"audio2")
    (dir_path / "chunk_003.wav").write_bytes(b"audio3")

    transcriber = CrispASRTranscriber(
        endpoint_url="https://api.crispasr.ai/v1",
        api_key="crisp-key",
        model="crisp-model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        
        # Mock successive raw responses
        resp1 = MagicMock()
        resp1.http_response.json.return_value = {"text": "Hello", "speaker": "Alice"}
        
        resp2 = MagicMock()
        resp2.http_response.json.return_value = {"text": "How are you?", "speaker": "Alice"}
        
        # Speaker change
        resp3 = MagicMock()
        resp3.http_response.json.return_value = {"text": "I am fine.", "speaker": "Bob"}
        
        mock_client.audio.transcriptions.with_raw_response.create.side_effect = [resp1, resp2, resp3]

        result = transcriber.transcribe(dir_path)
        # Alice's segments should be merged, Bob's should be separate
        assert result == "[Alice]: Hello How are you?\n\n[Bob]: I am fine."
        assert mock_client.audio.transcriptions.with_raw_response.create.call_count == 3

def test_crispasr_transcribe_no_speaker(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = CrispASRTranscriber(
        endpoint_url="https://api.crispasr.ai/v1",
        api_key="crisp-key",
        model="crisp-model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        
        mock_raw_response = MagicMock()
        # Missing speaker tag
        mock_raw_response.http_response.json.return_value = {
            "text": "Hello world no speaker"
        }
        
        mock_client.audio.transcriptions.with_raw_response.create.return_value = mock_raw_response

        result = transcriber.transcribe(audio_file)
        assert result == "[Speaker Unknown]: Hello world no speaker"

def test_crispasr_transcribe_failure(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = CrispASRTranscriber(
        endpoint_url="https://api.crispasr.ai/v1",
        api_key="crisp-key",
        model="crisp-model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_client.audio.transcriptions.with_raw_response.create.side_effect = Exception("Crisp Error")

        with pytest.raises(RuntimeError, match="CrispASR transcription failed: Crisp Error"):
            transcriber.transcribe(audio_file)

def test_crispasr_transcribe_debug_logging(tmp_path, caplog):
    import logging
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")

    transcriber = CrispASRTranscriber(
        endpoint_url="https://api.crispasr.ai/v1",
        api_key="crisp-key",
        model="crisp-model"
    )

    with patch("podscribe.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_raw_response = MagicMock()
        mock_raw_response.http_response.json.return_value = {
            "text": "Hello",
            "speaker": "Alice"
        }
        mock_client.audio.transcriptions.with_raw_response.create.return_value = mock_raw_response

        # Test with INFO level (should NOT show debug log)
        with caplog.at_level(logging.INFO):
            transcriber.transcribe(audio_file)
            assert not any("CrispASR Request:" in record.message for record in caplog.records)
            assert not any("CrispASR Response:" in record.message for record in caplog.records)

        caplog.clear()

        # Test with DEBUG level (should show debug log)
        with caplog.at_level(logging.DEBUG):
            transcriber.transcribe(audio_file)
            assert any("CrispASR Request: url=https://api.crispasr.ai/v1, model=crisp-model, response_format=verbose_json, diarize=True, language=en, file=test.wav" in record.message for record in caplog.records)
            assert any("CrispASR Response: {'text': 'Hello', 'speaker': 'Alice'}" in record.message for record in caplog.records)


# ----------------------------------------------------------------------
# CrispASR CLI Transcriber Tests
# ----------------------------------------------------------------------

def test_crispasr_cli_init():
    t = CrispASRCLITranscriber(
        binary_path="/usr/bin/crispasr",
        model="model.gguf",
        backend="whisper",
        diarize_method="pyannote"
    )
    assert t.binary_path == "/usr/bin/crispasr"
    assert t.model == "model.gguf"
    assert t.backend == "whisper"
    assert t.diarize_method == "pyannote"

def test_crispasr_cli_init_defaults():
    t = CrispASRCLITranscriber(binary_path="", model="", backend="", diarize_method="")
    assert t.binary_path == "crispasr"
    assert t.model == "auto"
    assert t.backend == "auto"
    assert t.diarize_method == "pyannote"

def test_detect_model_family():
    from podscribe.transcribers import _detect_model_family
    assert _detect_model_family("some-parakeet-model.gguf", "auto") == "parakeet"
    assert _detect_model_family("auto", "parakeet") == "parakeet"
    assert _detect_model_family("whisper-tiny.gguf", "auto") == "whisper"
    assert _detect_model_family("auto", "whisper") == "whisper"
    assert _detect_model_family("unknown", "auto") == "default"

def test_crispasr_cli_transcribe_success_diarize(tmp_path):
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"audio")

    transcriber = CrispASRCLITranscriber(
        binary_path="crispasr",
        model="parakeet-model",
        backend="parakeet",
        diarize_method="pyannote"
    )

    def side_effect(cmd, *args, **kwargs):
        of_idx = cmd.index("-of")
        output_prefix = cmd[of_idx + 1]
        json_path = Path(f"{output_prefix}.json")
        mock_data = {
            "text": "Hello world.",
            "segments": [
                {"text": "Hello", "speaker": "Alice"},
                {"text": "world.", "speaker": "Alice"}
            ]
        }
        import json
        json_path.write_text(json.dumps(mock_data))
        return MagicMock(returncode=0, stdout="OK", stderr="")

    with patch("subprocess.run", side_effect=side_effect) as mock_run:
        result = transcriber.transcribe(audio_file)
        assert result == "[Alice]: Hello world."
        
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "crispasr"
        assert "-m" in cmd
        assert cmd[cmd.index("-m") + 1] == "parakeet-model"
        assert "--backend" in cmd
        assert cmd[cmd.index("--backend") + 1] == "parakeet"
        assert "-f" in cmd
        assert cmd[cmd.index("-f") + 1] == str(audio_file)
        
        # Diarize flags
        assert "--diarize" in cmd
        assert "--diarize-method" in cmd
        assert cmd[cmd.index("--diarize-method") + 1] == "pyannote"
        assert "--sherpa-segment-model" in cmd
        assert cmd[cmd.index("--sherpa-segment-model") + 1] == "auto"
        assert "--diarize-embedder" in cmd
        assert cmd[cmd.index("--diarize-embedder") + 1] == "auto"

def test_crispasr_cli_transcribe_success_no_diarize(tmp_path):
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"audio")

    transcriber = CrispASRCLITranscriber(
        binary_path="crispasr",
        model="whisper-model",
        backend="whisper",
        diarize_method="none"
    )

    def side_effect(cmd, *args, **kwargs):
        of_idx = cmd.index("-of")
        output_prefix = cmd[of_idx + 1]
        json_path = Path(f"{output_prefix}.json")
        mock_data = {
            "text": "Hello world without diarization.",
            "segments": [
                {"text": "Hello world without diarization."}
            ]
        }
        import json
        json_path.write_text(json.dumps(mock_data))
        return MagicMock(returncode=0, stdout="OK", stderr="")

    with patch("subprocess.run", side_effect=side_effect) as mock_run:
        result = transcriber.transcribe(audio_file)
        assert result == "Hello world without diarization."
        
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        # Diarize flags should be omitted
        assert "--diarize" not in cmd
        assert "--diarize-method" not in cmd

def test_crispasr_cli_transcribe_failure_exit_code(tmp_path):
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"audio")

    transcriber = CrispASRCLITranscriber(binary_path="crispasr", model="model", backend="backend", diarize_method="pyannote")

    import subprocess
    # subprocess.run should raise CalledProcessError when check=True and exit code is non-zero
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(returncode=1, cmd="crispasr", stderr="CLI Error")):
        with pytest.raises(RuntimeError, match="CrispASR CLI failed: CLI Error"):
            transcriber.transcribe(audio_file)

def test_crispasr_cli_transcribe_failure_missing_json(tmp_path):
    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"audio")

    transcriber = CrispASRCLITranscriber(binary_path="crispasr", model="model", backend="backend", diarize_method="pyannote")

    # subprocess.run succeeds but does NOT write JSON file
    with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as mock_run:
        with pytest.raises(FileNotFoundError, match="CrispASR CLI did not produce expected JSON file"):
            transcriber.transcribe(audio_file)
