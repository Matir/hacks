from unittest.mock import patch, MagicMock
import pytest
from podscribe.post_processors import GeminiPostProcessor, OpenAICompatiblePostProcessor

# ----------------------------------------------------------------------
# Gemini Post Processor Tests
# ----------------------------------------------------------------------

def test_gemini_post_processor_init():
    proc = GeminiPostProcessor(model="gemini-2.5-flash", api_key="gem_key", temperature=0.3)
    assert proc.model == "gemini-2.5-flash"
    assert proc.api_key == "gem_key"
    assert proc.temperature == 0.3

def test_gemini_post_processor_missing_model():
    proc = GeminiPostProcessor(model="", api_key="key", temperature=0.1)
    with pytest.raises(ValueError, match="Gemini model must be configured"):
        proc.post_process("raw text", "template")

def test_gemini_post_process_success():
    proc = GeminiPostProcessor(model="gemini-2.5-flash", api_key="gem_key", temperature=0.3)
    prompt_template = "Clean this: {{TRANSCRIPT}}"
    raw_transcript = "uh hello like world"
    
    with patch("podscribe.post_processors.genai.Client") as mock_genai_client_class:
        mock_client = mock_genai_client_class.return_value
        mock_models = mock_client.models
        mock_response = MagicMock()
        mock_response.text = "Hello World"
        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 10
        mock_usage.candidates_token_count = 5
        mock_usage.total_token_count = 15
        mock_response.usage_metadata = mock_usage
        mock_models.generate_content.return_value = mock_response
        
        text, usage = proc.post_process(raw_transcript, prompt_template)
        
        assert text == "Hello World"
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 5
        assert usage.total_tokens == 15
        mock_genai_client_class.assert_called_once_with(api_key="gem_key")
        
        # Verify generate_content call
        mock_models.generate_content.assert_called_once()
        call_args = mock_models.generate_content.call_args[1]
        assert call_args["model"] == "gemini-2.5-flash"
        assert call_args["contents"] == "Clean this: uh hello like world"
        # Verify config temperature
        config_arg = call_args["config"]
        assert config_arg.temperature == 0.3

def test_gemini_post_process_key_fallback():
    # Empty API key to test fallback to None
    proc = GeminiPostProcessor(model="gemini-model", api_key="", temperature=0.2)
    
    with patch("podscribe.post_processors.genai.Client") as mock_genai_client_class:
        mock_client = mock_genai_client_class.return_value
        mock_response = MagicMock(text="output")
        mock_usage = MagicMock()
        mock_usage.prompt_token_count = 0
        mock_usage.candidates_token_count = 0
        mock_usage.total_token_count = 0
        mock_response.usage_metadata = mock_usage
        mock_client.models.generate_content.return_value = mock_response
        
        proc.post_process("raw", "temp {{TRANSCRIPT}}")
        
        # Should pass None so SDK falls back to env
        mock_genai_client_class.assert_called_once_with(api_key=None)


# ----------------------------------------------------------------------
# OpenAI Compatible Post Processor Tests
# ----------------------------------------------------------------------

def test_openai_post_processor_url_sanitization():
    # Standard base URL should remain unchanged
    p1 = OpenAICompatiblePostProcessor("https://openrouter.ai/api/v1", "key", "model", 0.2)
    assert p1.endpoint_url == "https://openrouter.ai/api/v1"
    
    # Trailing /chat/completions should be stripped
    p2 = OpenAICompatiblePostProcessor("https://openrouter.ai/api/v1/chat/completions", "key", "model", 0.2)
    assert p2.endpoint_url == "https://openrouter.ai/api/v1"

def test_openai_post_process_success():
    proc = OpenAICompatiblePostProcessor(
        endpoint_url="https://openrouter.ai/api/v1",
        api_key="op-key",
        model="meta-llama/llama-3-70b-instruct",
        temperature=0.5
    )
    prompt_template = "Format: {{TRANSCRIPT}}"
    raw_transcript = "raw transcript data"
    
    with patch("podscribe.post_processors.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_chat = mock_client.chat
        mock_response = MagicMock()
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 20
        mock_usage.completion_tokens = 10
        mock_usage.total_tokens = 30
        mock_response.usage = mock_usage
        
        # Mock nested choice structure
        mock_choice = MagicMock()
        mock_choice.message.content = "formatted output"
        mock_response.choices = [mock_choice]
        mock_chat.completions.create.return_value = mock_response
        
        text, usage = proc.post_process(raw_transcript, prompt_template)
        
        assert text == "formatted output"
        assert usage.prompt_tokens == 20
        assert usage.completion_tokens == 10
        assert usage.total_tokens == 30
        mock_openai_class.assert_called_once_with(
            base_url="https://openrouter.ai/api/v1",
            api_key="op-key"
        )
        # Verify completions call
        mock_chat.completions.create.assert_called_once_with(
            model="meta-llama/llama-3-70b-instruct",
            messages=[
                {"role": "user", "content": "Format: raw transcript data"}
            ],
            temperature=0.5
        )

def test_openai_post_process_dummy_key_fallback():
    # Empty key for local LLM
    proc = OpenAICompatiblePostProcessor(
        endpoint_url="http://localhost:8000/v1",
        api_key="",
        model="local-model",
        temperature=0.1
    )
    
    with patch("podscribe.post_processors.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_choice = MagicMock()
        mock_choice.message.content = "output"
        mock_response = MagicMock(choices=[mock_choice])
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 0
        mock_usage.completion_tokens = 0
        mock_usage.total_tokens = 0
        mock_response.usage = mock_usage
        mock_client.chat.completions.create.return_value = mock_response
        
        proc.post_process("raw", "temp {{TRANSCRIPT}}")
        
        # Should use "dummy-key" fallback
        mock_openai_class.assert_called_once_with(
            base_url="http://localhost:8000/v1",
            api_key="dummy-key"
        )

def test_gemini_post_process_empty_response():
    proc = GeminiPostProcessor(model="gemini-2.5-flash", api_key="key", temperature=0.3)
    
    with patch("podscribe.post_processors.genai.Client") as mock_genai_client_class:
        mock_client = mock_genai_client_class.return_value
        mock_models = mock_client.models
        mock_response = MagicMock()
        mock_response.text = None # Empty response
        mock_models.generate_content.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Empty response from Gemini"):
            proc.post_process("raw", "temp {{TRANSCRIPT}}")

def test_gemini_post_process_failure():
    proc = GeminiPostProcessor(model="gemini-2.5-flash", api_key="key", temperature=0.3)
    
    with patch("podscribe.post_processors.genai.Client") as mock_genai_client_class:
        mock_client = mock_genai_client_class.return_value
        mock_client.models.generate_content.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError, match="Gemini post-processing failed: API Error"):
            proc.post_process("raw", "temp {{TRANSCRIPT}}")

def test_openai_post_process_validation():
    # Missing URL
    p1 = OpenAICompatiblePostProcessor(endpoint_url="", api_key="key", model="model", temperature=0.1)
    with pytest.raises(ValueError, match="OpenAI-compatible endpoint URL must be configured"):
        p1.post_process("raw", "temp {{TRANSCRIPT}}")
        
    # Missing Model
    p2 = OpenAICompatiblePostProcessor(endpoint_url="http://localhost", api_key="key", model="", temperature=0.1)
    with pytest.raises(ValueError, match="OpenAI-compatible model must be configured"):
        p2.post_process("raw", "temp {{TRANSCRIPT}}")

def test_openai_post_process_empty_content():
    proc = OpenAICompatiblePostProcessor(
        endpoint_url="http://localhost",
        api_key="key",
        model="model",
        temperature=0.1
    )
    
    with patch("podscribe.post_processors.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_choice = MagicMock()
        mock_choice.message.content = None # Empty content
        mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
        
        with pytest.raises(RuntimeError, match="Empty content in response from OpenAI-compatible API"):
            proc.post_process("raw", "temp {{TRANSCRIPT}}")

def test_openai_post_process_no_choices():
    proc = OpenAICompatiblePostProcessor(
        endpoint_url="http://localhost",
        api_key="key",
        model="model",
        temperature=0.1
    )
    
    with patch("podscribe.post_processors.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.return_value = MagicMock(choices=[]) # No choices
        
        with pytest.raises(RuntimeError, match="No choices returned from OpenAI-compatible API"):
            proc.post_process("raw", "temp {{TRANSCRIPT}}")

def test_openai_post_process_failure():
    proc = OpenAICompatiblePostProcessor(
        endpoint_url="http://localhost",
        api_key="key",
        model="model",
        temperature=0.1
    )
    
    with patch("podscribe.post_processors.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        with pytest.raises(RuntimeError, match="OpenAI-compatible post-processing failed: API Error"):
            proc.post_process("raw", "temp {{TRANSCRIPT}}")

def test_gemini_post_process_with_context():
    proc = GeminiPostProcessor(model="gemini-2.5-flash", api_key="gem_key", temperature=0.3)
    prompt_template = "Clean this: {{TRANSCRIPT}} for {{podcast_name}} hosted by {{host}}."
    raw_transcript = "uh hello like world"
    context = {
        "podcast_name": "Tech Talk",
        "host": "Alice"
    }
    
    with patch("podscribe.post_processors.genai.Client") as mock_genai_client_class:
        mock_client = mock_genai_client_class.return_value
        mock_models = mock_client.models
        mock_response = MagicMock(text="Hello World")
        mock_response.usage_metadata = MagicMock(prompt_token_count=10, candidates_token_count=5, total_token_count=15)
        mock_models.generate_content.return_value = mock_response
        
        text, usage = proc.post_process(raw_transcript, prompt_template, context=context)
        
        assert text == "Hello World"
        mock_models.generate_content.assert_called_once()
        call_args = mock_models.generate_content.call_args[1]
        assert call_args["contents"] == "Clean this: uh hello like world for Tech Talk hosted by Alice."

def test_openai_post_process_with_context():
    proc = OpenAICompatiblePostProcessor(
        endpoint_url="https://openrouter.ai/api/v1",
        api_key="op-key",
        model="meta-llama/llama-3-70b-instruct",
        temperature=0.5
    )
    prompt_template = "Format: {{TRANSCRIPT}} for {{podcast_name}}."
    raw_transcript = "raw transcript data"
    context = {
        "podcast_name": "Tech Talk"
    }
    
    with patch("podscribe.post_processors.OpenAI") as mock_openai_class:
        mock_client = mock_openai_class.return_value
        mock_chat = mock_client.chat
        mock_response = MagicMock()
        mock_response.usage = MagicMock(prompt_tokens=20, completion_tokens=10, total_tokens=30)
        mock_choice = MagicMock()
        mock_choice.message.content = "formatted output"
        mock_response.choices = [mock_choice]
        mock_chat.completions.create.return_value = mock_response
        
        text, usage = proc.post_process(raw_transcript, prompt_template, context=context)
        
        assert text == "formatted output"
        mock_chat.completions.create.assert_called_once_with(
            model="meta-llama/llama-3-70b-instruct",
            messages=[
                {"role": "user", "content": "Format: raw transcript data for Tech Talk."}
            ],
            temperature=0.5
        )
