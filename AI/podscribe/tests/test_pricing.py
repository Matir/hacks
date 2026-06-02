import pytest
from podscribe.pricing import calculate_post_processing_cost, calculate_transcription_cost

def test_calculate_post_processing_cost_gemini_flash():
    # gemini-2.5-flash: input 0.075/1M, output 0.30/1M
    # 1M input tokens = $0.075
    # 1M output tokens = $0.30
    cost = calculate_post_processing_cost("gemini-2.5-flash", 1_000_000, 1_000_000)
    assert pytest.approx(cost) == 0.375

    # Substring matching (e.g., with "latest" or other suffixes)
    cost_suffix = calculate_post_processing_cost("gemini-2.5-flash-latest", 100_000, 50_000)
    expected = (100_000 / 1_000_000) * 0.075 + (50_000 / 1_000_000) * 0.30
    assert pytest.approx(cost_suffix) == expected

def test_calculate_post_processing_cost_unknown_model(caplog):
    cost = calculate_post_processing_cost("unknown-model", 100, 100)
    assert cost == 0.0
    assert "No pricing found for model: unknown-model" in caplog.text

def test_calculate_post_processing_cost_empty():
    assert calculate_post_processing_cost("", 100, 100) == 0.0

def test_calculate_transcription_cost():
    # openai: 0.006 / minute
    # 10 minutes (600 seconds) = $0.06
    cost = calculate_transcription_cost("openai", 600)
    assert pytest.approx(cost) == 0.06

    # Free provider
    assert calculate_transcription_cost("huggingface", 600) == 0.0
    assert calculate_transcription_cost("unknown", 600) == 0.0
    
    # openai_compatible with official endpoint
    cost_compat = calculate_transcription_cost("openai_compatible", 600, "https://api.openai.com/v1")
    assert pytest.approx(cost_compat) == 0.06

    # openai_compatible with local endpoint
    cost_local = calculate_transcription_cost("openai_compatible", 600, "http://localhost:8000/v1")
    assert cost_local == 0.0

    # Zero/negative duration
    assert calculate_transcription_cost("openai", 0) == 0.0
    assert calculate_transcription_cost("openai", -10) == 0.0
