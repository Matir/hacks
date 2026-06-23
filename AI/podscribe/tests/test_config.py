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
    hotwords = "testing, hotwords"

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

    [prompt_context]
    podcast_name = "My Podcast"
    host = "John Doe"
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
    assert config.hotwords == "testing, hotwords"
    
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

    # Verify prompt_context
    assert config.prompt_context == {"podcast_name": "My Podcast", "host": "John Doe"}

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
    assert config.hotwords == ""
    assert config.get_transcriber_api_key() == ""  # Default env HF_API_KEY not set
    assert config.post_processor_provider == "gemini"
    assert config.post_processor_model == ""
    assert config.post_processor_endpoint == ""
    assert config.post_processor_temperature == 0.2
    assert config.rss_feeds == []
    assert config.prompt_context == {}

def test_config_missing_file():
    with pytest.raises(FileNotFoundError):
        Config("non_existent_file.toml")

def test_config_dump(tmp_path):
    import os
    config_content = """
    [paths]
    input_dir = "custom_input"
    output_dir = "custom_output"
    prompt_file = "custom_prompt.md"

    [preprocessing]
    enabled = true
    chunking_enabled = true
    chunk_max_duration = 180

    [transcriber]
    provider = "crispasr_cli"
    model = "custom-model"
    crispasr_path = "/usr/bin/crispasr"
    backend = "whisper"
    diarize_method = "pyannote"
    api_key_env = "CUSTOM_ASR_KEY"

    [post_processor]
    provider = "gemini"
    model = "gemini-2.5-flash"
    api_key_env = "CUSTOM_GEMINI_KEY"

    [[rss.feeds]]
    url = "https://example.com/feed.rss"
    max_episodes = 5

    [prompt_context]
    podcast_name = "My Podcast"
    """
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)

    config = Config(config_file)
    
    # Test without keys set in env
    if "CUSTOM_ASR_KEY" in os.environ:
        del os.environ["CUSTOM_ASR_KEY"]
    if "CUSTOM_GEMINI_KEY" in os.environ:
        del os.environ["CUSTOM_GEMINI_KEY"]
        
    dump_str = config.dump()
    assert "custom_input" in dump_str
    assert "custom_output" in dump_str
    assert "custom_prompt.md" in dump_str
    assert "Enabled:                 True" in dump_str
    assert "Chunking Enabled:        True" in dump_str
    assert "Max Chunk Duration:      180s" in dump_str
    assert "Provider:                crispasr_cli" in dump_str
    assert "CrispASR Path:           /usr/bin/crispasr" in dump_str
    assert "CrispASR Backend:        whisper" in dump_str
    assert "API Key Present:         No" in dump_str

    # Test with keys set in env
    os.environ["CUSTOM_ASR_KEY"] = "some-key"
    os.environ["CUSTOM_GEMINI_KEY"] = "another-key"
    
    dump_str_with_keys = config.dump()
    assert "API Key Present:         Yes" in dump_str_with_keys
    
    # Clean up env
    del os.environ["CUSTOM_ASR_KEY"]
    del os.environ["CUSTOM_GEMINI_KEY"]

def test_config_dump_covers_all_properties(tmp_path):
    import inspect
    from podscribe.config import Config
    
    # 1. Get all properties defined on Config
    properties = [
        name for name, member in inspect.getmembers(Config)
        if isinstance(member, property)
    ]
    
    # 2. Define mappings of properties to their expected dump substrings
    general_properties = {
        "input_dir": "Input Directory:",
        "output_dir": "Output Directory:",
        "prompt_file": "Prompt Template:",
        "preprocess_enabled": "Enabled:",
        "chunking_enabled": "Chunking Enabled:",
        "chunk_max_duration": "Max Chunk Duration:",
        "silence_threshold_db": "Silence Threshold:",
        "silence_duration": "Silence Duration:",
        "ffmpeg_path": "FFmpeg Path:",
        "transcriber_provider": "Provider:",
        "transcriber_endpoint": "Endpoint URL:",
        "transcriber_model": "Model:",
        "enable_speaker_attribution": "Speaker Attribution:",
        "language": "Language:",
        "post_processor_provider": "Provider:",
        "post_processor_model": "Model:",
        "post_processor_endpoint": "Endpoint URL:",
        "post_processor_temperature": "Temperature:",
        "rss_feeds": "RSS Feeds",
        "prompt_context": "Prompt Context"
    }
    
    crispasr_properties = {
        "transcriber_crispasr_path": "CrispASR Path:",
        "transcriber_backend": "CrispASR Backend:",
        "transcriber_diarize_method": "Diarize Method:"
    }
    
    vibevoice_properties = {
        "hotwords": "Hotwords:"
    }
    
    # 3. Verify that every property defined on Config is in exactly one mapping
    all_mapped = {**general_properties, **crispasr_properties, **vibevoice_properties}
    for prop in properties:
        assert prop in all_mapped, (
            f"Property '{prop}' is defined on Config but is not tracked in any test mapping. "
            f"Please add it to the appropriate mapping (general, crispasr, or vibevoice) "
            f"and ensure it is rendered in Config.dump()."
        )
        
    # 4. Helper to verify a configuration's dump
    def verify_dump(config_content: str, expected_fields: dict, unexpected_fields: dict):
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        config = Config(config_file)
        dump_str = config.dump()
        
        # All expected fields must be present
        for prop, substring in expected_fields.items():
            assert substring in dump_str, (
                f"Expected substring '{substring}' (for property '{prop}') "
                f"was not found in Config.dump() output:\n{dump_str}"
            )
            
        # All unexpected fields must NOT be present
        for prop, substring in unexpected_fields.items():
            assert substring not in dump_str, (
                f"Unexpected substring '{substring}' (for property '{prop}') "
                f"was found in Config.dump() output, but shouldn't be:\n{dump_str}"
            )

    # Scenario A: crispasr_cli provider
    crispasr_content = """
    [preprocessing]
    chunking_enabled = true
    [transcriber]
    provider = "crispasr_cli"
    [[rss.feeds]]
    url = "https://example.com/feed.rss"
    [prompt_context]
    podcast_name = "My Podcast"
    """
    verify_dump(
        config_content=crispasr_content,
        expected_fields={**general_properties, **crispasr_properties},
        unexpected_fields=vibevoice_properties
    )

    # Scenario B: vibevoice provider
    vibevoice_content = """
    [preprocessing]
    chunking_enabled = true
    [transcriber]
    provider = "vibevoice"
    [[rss.feeds]]
    url = "https://example.com/feed.rss"
    [prompt_context]
    podcast_name = "My Podcast"
    """
    verify_dump(
        config_content=vibevoice_content,
        expected_fields={**general_properties, **vibevoice_properties},
        unexpected_fields=crispasr_properties
    )

    # Scenario C: standard huggingface provider
    huggingface_content = """
    [preprocessing]
    chunking_enabled = true
    [transcriber]
    provider = "huggingface"
    [[rss.feeds]]
    url = "https://example.com/feed.rss"
    [prompt_context]
    podcast_name = "My Podcast"
    """
    verify_dump(
        config_content=huggingface_content,
        expected_fields=general_properties,
        unexpected_fields={**crispasr_properties, **vibevoice_properties}
    )
