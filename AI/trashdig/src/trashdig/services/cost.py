import json
import logging
import os
import urllib.request
from typing import Any

from trashdig.config import get_config

logger = logging.getLogger(__name__)


class CostTracker:
    """Tracks LLM usage costs across models in USD."""

    # Default rates per 1 million tokens (USD)
    # Used if remote fetch and cache both fail.
    DEFAULT_RATES = {
        "gemini-2.0-flash": {"input": 0.15, "output": 0.60},
        "gemini-2.0-pro-exp": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    }

    PRICING_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
    CACHE_FILENAME = "model_prices.json"

    def __init__(self, rates: dict[str, Any] | None = None):
        """Initializes the CostTracker.

        Args:
            rates: Optional dictionary of model rates. If not provided,
                it will attempt to load from cache or remote.
        """
        self.total_cost: float = 0.0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.rates: dict[str, Any] = rates or {}

        if not self.rates:
            self.load_rates()

    def load_rates(self) -> None:
        """Loads rates from cache or remote URL."""
        config = get_config()
        cache_path = config.resolve_data_path(self.CACHE_FILENAME)

        # Try remote first to get latest
        try:
            logger.info("Fetching latest LLM pricing from LiteLLM...")
            with urllib.request.urlopen(self.PRICING_URL, timeout=10) as response:
                remote_data = json.loads(response.read().decode("utf-8"))
                self.rates = remote_data
                # Cache it
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, "w") as f:
                    json.dump(remote_data, f)
                logger.info("Successfully updated pricing cache.")
                return
        except Exception as e:
            logger.warning("Failed to fetch remote pricing: %s", e)

        # Try local cache
        if os.path.exists(cache_path):
            try:
                with open(cache_path) as f:
                    self.rates = json.load(f)
                logger.info("Loaded pricing from local cache.")
                return
            except Exception as e:
                logger.warning("Failed to load pricing cache: %s", e)

        # Fallback to hardcoded defaults
        logger.warning("Using hardcoded default pricing.")

    def _get_cost_from_info(self, info: dict[str, Any], input_tokens: int, output_tokens: int) -> float:
        """Calculates cost from a rate info dictionary.

        Handles both LiteLLM format and legacy DEFAULT_RATES format.
        """
        # LiteLLM format: input_cost_per_token
        if "input_cost_per_token" in info:
            input_price = info.get("input_cost_per_token", 0)
            output_price = info.get("output_cost_per_token", 0)
            return (input_tokens * input_price) + (output_tokens * output_price)

        # Legacy/Internal format: {"input": cost_per_1M, "output": cost_per_1M}
        if "input" in info:
            input_price = info.get("input", 0) / 1_000_000.0
            output_price = info.get("output", 0) / 1_000_000.0
            return (input_tokens * input_price) + (output_tokens * output_price)

        return 0.0

    def record_usage(self, model_name: str, input_tokens: int, output_tokens: int) -> None:
        """Records usage for a specific model and updates the total cost.

        Args:
            model_name: The name of the model used.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # 1. Try exact match in loaded rates
        rate_info = self.rates.get(model_name)
        if not rate_info and not model_name.startswith("gemini/"):
            rate_info = self.rates.get(f"gemini/{model_name}")

        if rate_info:
            self.total_cost += self._get_cost_from_info(rate_info, input_tokens, output_tokens)
            return

        # 2. Try prefix match in loaded rates
        for key, val in self.rates.items():
            if model_name.startswith(key) or (
                not model_name.startswith("gemini/") and f"gemini/{model_name}".startswith(key)
            ):
                self.total_cost += self._get_cost_from_info(val, input_tokens, output_tokens)
                return

        # 3. Fallback to DEFAULT_RATES
        rate = self.DEFAULT_RATES.get(model_name)
        if not rate:
            for key, val in self.DEFAULT_RATES.items():
                if model_name.startswith(key):
                    rate = val
                    break

        if rate:
            self.total_cost += self._get_cost_from_info(rate, input_tokens, output_tokens)

    def get_total_cost(self) -> float:
        """Returns the total accumulated cost in USD.

        Returns:
            The total cost as a float.
        """
        return self.total_cost
