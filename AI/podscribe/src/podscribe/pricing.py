"""Pricing information and cost calculation for AI models."""

import logging

logger = logging.getLogger(__name__)

# Prices are per 1,000,000 tokens in USD (as of early 2026)
LLM_PRICING = {
    # Gemini Models
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},

    # OpenAI Models
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}

# Transcription pricing (per minute in USD)
TRANSCRIPTION_PRICING = {
    "openai": 0.006,           # OpenAI Whisper API
    "assemblyai": 0.0035,      # AssemblyAI Universal-3 Pro ($0.21/hr)
    "huggingface": 0.0,        # Assuming self-hosted/free endpoint unless specified
    "openai_compatible": 0.0,  # Assuming self-hosted (local vLLM/Whisper)
}

def calculate_post_processing_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    provider: str = "",
    endpoint_url: str = ""
) -> float:
    """Calculate the cost of post-processing in USD."""
    if not model:
        return 0.0

    try:
        from genai_prices import Usage, calc_price

        provider_id = None
        provider_lower = provider.lower() if provider else ""
        endpoint_lower = endpoint_url.lower() if endpoint_url else ""

        if provider_lower == "gemini":
            provider_id = "google"
        elif provider_lower == "openai_compatible":
            if "openrouter.ai" in endpoint_lower:
                provider_id = "openrouter"
            elif "api.openai.com" in endpoint_lower:
                provider_id = "openai"

        usage = Usage(input_tokens=prompt_tokens, output_tokens=completion_tokens)
        price_calculation = calc_price(
            usage=usage,
            model_ref=model,
            provider_id=provider_id
        )
        return float(price_calculation.total_price)
    except LookupError as e:
        logger.debug(f"Model not found in genai-prices, falling back to local pricing: {e}")
    except Exception as e:
        logger.warning(f"Error calling genai-prices: {e}. Falling back to local pricing.")

    # Try to find a matching model key (case-insensitive, substring match)
    pricing = None
    model_lower = model.lower()
    for key in LLM_PRICING:
        if key in model_lower:
            pricing = LLM_PRICING[key]
            break

    if not pricing:
        logger.warning(f"No pricing found for model: {model}. Cost will be 0.0.")
        return 0.0

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost

def calculate_transcription_cost(provider: str, duration_seconds: float, endpoint_url: str = "") -> float:
    """Calculate the cost of transcription in USD."""
    if not provider or duration_seconds <= 0:
        return 0.0

    provider_lower = provider.lower()

    # If using openai_compatible but endpoint is official OpenAI, treat as openai pricing
    if provider_lower == "openai_compatible" and endpoint_url and "api.openai.com" in endpoint_url:
        provider_lower = "openai"

    rate_per_minute = TRANSCRIPTION_PRICING.get(provider_lower, 0.0)
    duration_minutes = duration_seconds / 60.0
    return duration_minutes * rate_per_minute
