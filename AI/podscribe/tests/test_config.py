import pytest
from pathlib import Path
from podscribe.config import Config

def test_config_load_valid(tmp_path):
    # Create a dummy config file
    config_content = """
    [paths]
    input_dir = "custom_input"
    output_dir = "custom_output"
    prompt_file = "custom_prompt.md"

    [preprocessing]
    enabled = false
    ffmpeg_path = "/usr/bin/ffmpeg"
    chunking_enabled = true
    chunk_max_duration = 180
    silence_threshold_db = -25
    silence_duration = 0.8

    [transcriber]
    provider = "openai_compatible"
    endpoint_url = "https://custom-asr.com/v1/audio/transcriptions"
    model = "custom-model"
    api_key_env = "CUSTOM_ASR_KEY"
    enable_speaker_attribution = true
    language = "es"

    [post_processor]
    provider = "gemini"
    model = "gemini-2.5-flash"
    endpoint_url = "https://openrouter.ai/api/v1"
    api_key_env = "CUSTOM_GEMINI_KEY"
    temperature = 0.5

    [[rss.feeds]]
    url = "https://example.com/feed1.rss"
    max_episodes = 5

    [[rss.feeds]]
    url = "https://example.com/feed2.rss"
    """
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)

    # Load config
    config = Config(config_file)

    # Verify properties
    assert config.input_dir == Path("custom_input")
    assert config.output_dir == Path("custom_output")
    assert config.prompt_file == Path("custom_prompt.md")
    assert config.preprocess_enabled is False
    assert config.chunking_enabled is True
    assert config.chunk_max_duration == 180
    assert config.silence_threshold_db == -25
    assert config.silence_duration == 0.8
    assert config.ffmpeg_path == "/usr/bin/ffmpeg"
    assert config.transcriber_provider == "openai_compatible"
    assert config.transcriber_endpoint == "https://custom-asr.com/v1/audio/transcriptions"
    assert config.transcriber_model == "custom-model"
    assert config.enable_speaker_attribution is True
    assert config.language == "es"
    
    # Test API key retrieval (requires env var setting)
    import os
    os.environ["CUSTOM_ASR_KEY"] = "secret-asr-key"
    assert config.get_transcriber_api_key() == "secret-asr-key"
    
    assert config.post_processor_provider == "gemini"
    assert config.post_processor_model == "gemini-2.5-flash"
    assert config.post_processor_endpoint == "https://openrouter.ai/api/v1"
    assert config.post_processor_temperature == 0.5
    
    os.environ["CUSTOM_GEMINI_KEY"] = "secret-gemini-key"
    assert config.get_post_processor_api_key() == "secret-gemini-key"

    # Verify RSS feeds
    feeds = config.rss_feeds
    assert len(feeds) == 2
    assert feeds[0]["url"] == "https://example.com/feed1.rss"
    assert feeds[0]["max_episodes"] == 5
    assert feeds[1]["url"] == "https://example.com/feed2.rss"
    assert "max_episodes" not in feeds[1]

def test_config_defaults(tmp_path):
    # Empty config
    config_file = tmp_path / "config.toml"
    config_file.write_text("")

    config = Config(config_file)

    assert config.input_dir == Path("input")
    assert config.output_dir == Path("output")
    assert config.prompt_file == Path("prompts/post_process.md")
    assert config.preprocess_enabled is True
    assert config.ffmpeg_path == "ffmpeg"
    assert config.transcriber_provider == "huggingface"
    assert config.transcriber_endpoint == ""
    assert config.transcriber_model == ""
    assert config.enable_speaker_attribution is False
    assert config.language == "en"
    assert config.get_transcriber_api_key() == ""  # Default env HF_API_KEY not set
    assert config.post_processor_provider == "gemini"
    assert config.post_processor_model == ""
    assert config.post_processor_endpoint == ""
    assert config.post_processor_temperature == 0.2
    assert config.rss_feeds == []

def test_config_missing_file():
    with pytest.raises(FileNotFoundError):
        Config("non_existent_file.toml")
