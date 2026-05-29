from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import httpx
from src.transcribers import HuggingFaceTranscriber, OpenAICompatibleTranscriber

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
    with patch("src.transcribers.OpenAI") as mock_openai_class:
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
        # File is opened in transcribe(), so we check it's a file object
        assert hasattr(call_args["file"], "read")

def test_openai_transcribe_dummy_key_fallback(tmp_path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake_audio")
    
    # Empty API key
    transcriber = OpenAICompatibleTranscriber(
        endpoint_url="http://localhost:8000/v1",
        api_key="",
        model="model"
    )
    
    with patch("src.transcribers.OpenAI") as mock_openai_class:
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
    
    with patch("src.transcribers.OpenAI") as mock_openai_class:
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
    
    with patch("src.transcribers.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        # Simulate API error
        mock_client.audio.transcriptions.create.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError, match="OpenAI-compatible transcription failed: API Error"):
            transcriber.transcribe(audio_file)
