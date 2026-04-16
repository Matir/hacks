

class CostTracker:
    """Tracks LLM usage costs across models in USD."""

    # Default rates per 1 million tokens (USD)
    # Rates: (input_cost_per_1M, output_cost_per_1M)
    DEFAULT_RATES = {
        "gemini-2.0-flash": {"input": 0.15, "output": 0.60},
        "gemini-2.0-pro-exp": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    }

    def __init__(self, rates: dict[str, dict[str, float]] | None = None):
        """Initializes the CostTracker.

        Args:
            rates: Optional dictionary of model rates. If not provided,
                DEFAULT_RATES will be used.
        """
        self.rates = rates or self.DEFAULT_RATES
        self.total_cost: float = 0.0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0

    def record_usage(self, model_name: str, input_tokens: int, output_tokens: int) -> None:
        """Records usage for a specific model and updates the total cost.

        Args:
            model_name: The name of the model used.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        rate = self.rates.get(model_name)
        
        # If no exact match, try to find a prefix match (e.g., 'gemini-2.0-flash-001')
        if not rate:
            for key, val in self.rates.items():
                if model_name.startswith(key):
                    rate = val
                    break
        
        if not rate:
            # If still not found, we can't track cost for this model
            return

        input_cost = (input_tokens / 1_000_000.0) * rate["input"]
        output_cost = (output_tokens / 1_000_000.0) * rate["output"]
        self.total_cost += input_cost + output_cost

    def get_total_cost(self) -> float:
        """Returns the total accumulated cost in USD.

        Returns:
            The total cost as a float.
        """
        return self.total_cost
