import abc
import logging

import httpx
import openai
from google import genai
from google.genai import errors, types
from openai import OpenAI
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class TokenUsage:
    """Represents token consumption metrics returned by LLM providers."""

    def __init__(self, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0):
        """Initialize token consumption statistics."""
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens

    def to_dict(self) -> dict:
        """Serialize token statistics to a dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TokenUsage':
        """Deserialize token statistics from a dictionary."""
        if not data:
            return cls()
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0)
        )


def is_post_processing_retryable_exception(exception: Exception) -> bool:
    """Determine whether an exception during post-processing should trigger a retry (e.g. rate limits, timeouts, 503)."""
    cause = exception.__cause__ if isinstance(exception, RuntimeError) and exception.__cause__ else exception

    # Check httpx exceptions
    if isinstance(cause, (httpx.TimeoutException, httpx.NetworkError)):
        return True

    if isinstance(cause, httpx.HTTPStatusError):
        return cause.response.status_code in (429, 502, 503, 504)

    # Check OpenAI exceptions
    if isinstance(cause, (openai.APITimeoutError, openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)):
        return True
    if isinstance(cause, openai.APIStatusError):
        if cause.status_code in (429, 502, 503, 504):
            return True

    # Check Google GenAI exceptions
    if isinstance(cause, errors.APIError):
        if cause.code in (429, 502, 503, 504):
            return True

    return False


class BasePostProcessor(abc.ABC):
    """Abstract base class defining the interface for LLM post-processors."""

    @abc.abstractmethod
    def post_process(self, transcript: str, prompt_template: str, context: dict = None) -> tuple[str, TokenUsage]:
        """Post-process the transcript using the LLM and return the polished text and token usage."""
        pass

    def _render_prompt(self, transcript: str, prompt_template: str, context: dict = None) -> str:
        """Render a Jinja2 prompt template injecting the transcript and additional metadata context."""
        from jinja2 import Template
        template = Template(prompt_template)
        render_context = {
            "transcript": transcript,
            "TRANSCRIPT": transcript,  # Backwards compatibility
        }
        if context:
            render_context.update(context)
        return template.render(**render_context)

def _format_empty_gemini_response_error(response) -> str:
    """Extract diagnostic information from a Gemini response when text output is empty."""
    details = []

    pf = getattr(response, "prompt_feedback", None)
    if pf and getattr(pf, "block_reason", None):
        details.append(f"prompt_feedback.block_reason={pf.block_reason}")

    candidates = getattr(response, "candidates", None)
    if not candidates:
        details.append("no candidates returned")
    else:
        candidate = candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason:
            details.append(f"finish_reason={finish_reason}")

        finish_message = getattr(candidate, "finish_message", None)
        if finish_message:
            details.append(f"finish_message={finish_message!r}")

        safety_ratings = getattr(candidate, "safety_ratings", None)
        if safety_ratings:
            flagged = []
            for r in safety_ratings:
                is_blocked = getattr(r, "blocked", False)
                prob = getattr(r, "probability", None)
                prob_str = str(prob) if prob else ""
                if is_blocked or "HIGH" in prob_str or "MEDIUM" in prob_str:
                    category = getattr(r, "category", "")
                    flagged.append(f"{category}={prob_str}")
            if flagged:
                details.append(f"flagged_safety_ratings=[{', '.join(flagged)}]")

        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if parts:
            thought_parts = [p for p in parts if getattr(p, "thought", False)]
            has_non_thought_text = any(
                isinstance(getattr(p, "text", None), str)
                and getattr(p, "text", "")
                and not getattr(p, "thought", False)
                for p in parts
            )
            if thought_parts and not has_non_thought_text:
                details.append("candidate contains thought parts but no final text")

    if details:
        return f"Empty response from Gemini ({'; '.join(details)})."
    return "Empty response from Gemini."


class GeminiPostProcessor(BasePostProcessor):
    """Post-processor client utilizing Google Gemini LLMs."""

    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float,
        safety_settings: list | str | dict | None = "OFF",
        thinking_budget: int | None = None,
        max_output_tokens: int | None = 16384,
    ):
        """Initialize Gemini client parameters."""
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.safety_settings = "OFF" if safety_settings is None else safety_settings
        self.thinking_budget = thinking_budget
        self.max_output_tokens = 16384 if max_output_tokens is None else max_output_tokens

    def _parse_safety_settings(self, settings: list | str | dict) -> list[types.SafetySetting]:
        """Convert safety settings configuration into google.genai types.SafetySetting list."""
        if isinstance(settings, str):
            val = settings.upper().strip()
            if val == "OFF":
                threshold = types.HarmBlockThreshold.OFF
            elif val == "BLOCK_NONE":
                threshold = types.HarmBlockThreshold.BLOCK_NONE
            elif val == "BLOCK_ONLY_HIGH":
                threshold = types.HarmBlockThreshold.BLOCK_ONLY_HIGH
            elif val == "BLOCK_MEDIUM_AND_ABOVE":
                threshold = types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
            elif val == "BLOCK_LOW_AND_ABOVE":
                threshold = types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE
            else:
                raise ValueError(f"Unsupported safety threshold string: {settings}")

            categories = [
                types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
            ]
            return [types.SafetySetting(category=cat, threshold=threshold) for cat in categories]
        elif isinstance(settings, list):
            result = []
            for item in settings:
                if isinstance(item, types.SafetySetting):
                    result.append(item)
                elif isinstance(item, dict):
                    cat = item.get("category")
                    thresh = item.get("threshold")
                    result.append(types.SafetySetting(category=cat, threshold=thresh))
            return result
        return []

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=30),
        retry=retry_if_exception(is_post_processing_retryable_exception)
    )
    def post_process(self, transcript: str, prompt_template: str, context: dict = None) -> tuple[str, TokenUsage]:
        """Send the rendered transcript prompt to Gemini and return polished Markdown text."""
        if not self.model:
            raise ValueError("Gemini model must be configured.")

        logger.info(f"Sending request to Gemini: {self.model}")
        try:
            # Initialize Gemini client
            client = genai.Client(api_key=self.api_key or None)

            # Prepare prompt by rendering template
            prompt = self._render_prompt(transcript, prompt_template, context)

            config_kwargs = {
                "temperature": self.temperature,
            }
            if self.max_output_tokens is not None:
                config_kwargs["max_output_tokens"] = self.max_output_tokens

            if self.thinking_budget is not None:
                config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=self.thinking_budget)

            if self.safety_settings is not None:
                parsed_safety = self._parse_safety_settings(self.safety_settings)
                if parsed_safety:
                    config_kwargs["safety_settings"] = parsed_safety

            config = types.GenerateContentConfig(**config_kwargs)

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )

            usage = TokenUsage()
            if response.usage_metadata:
                usage.prompt_tokens = response.usage_metadata.prompt_token_count or 0
                usage.completion_tokens = response.usage_metadata.candidates_token_count or 0
                usage.total_tokens = response.usage_metadata.total_token_count or 0

            response_text = None
            try:
                response_text = response.text
            except Exception as text_err:
                logger.warning(f"Error accessing response.text: {text_err}")

            if response_text:
                return response_text, usage
            else:
                err_msg = _format_empty_gemini_response_error(response)
                raise RuntimeError(err_msg)

        except Exception as e:
            if is_post_processing_retryable_exception(e):
                logger.warning(f"Gemini post-processing attempt failed: {e}. Retrying...")
            else:
                logger.error(f"Gemini post-processing failed: {e}")
            raise RuntimeError(f"Gemini post-processing failed: {e}") from e

class OpenAICompatiblePostProcessor(BasePostProcessor):
    """Post-processor client connecting to OpenAI or OpenRouter-style /chat/completions API endpoints."""

    def __init__(self, endpoint_url: str, api_key: str, model: str, temperature: float):
        """Initialize OpenAI-compatible client parameters."""
        if endpoint_url:
            endpoint_url = endpoint_url.rstrip("/")
            if endpoint_url.endswith("/chat/completions"):
                logger.warning("Stripping '/chat/completions' from endpoint_url.")
                endpoint_url = endpoint_url.removesuffix("/chat/completions")
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=30),
        retry=retry_if_exception(is_post_processing_retryable_exception)
    )
    def post_process(self, transcript: str, prompt_template: str, context: dict = None) -> tuple[str, TokenUsage]:
        """Send the rendered transcript prompt to an OpenAI-compatible chat endpoint and return polished text."""
        if not self.endpoint_url:
            raise ValueError("OpenAI-compatible endpoint URL must be configured.")
        if not self.model:
            raise ValueError("OpenAI-compatible model must be configured.")

        logger.info(f"Sending request to OpenAI-compatible LLM ({self.model}) via: {self.endpoint_url}")
        try:
            client = OpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key or "dummy-key"
            )

            prompt = self._render_prompt(transcript, prompt_template, context)

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )

            usage = TokenUsage()
            if response.usage:
                usage.prompt_tokens = response.usage.prompt_tokens or 0
                usage.completion_tokens = response.usage.completion_tokens or 0
                usage.total_tokens = response.usage.total_tokens or 0

            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                content = getattr(choice.message, "content", None)
                if content:
                    return content, usage
                else:
                    finish_reason = getattr(choice, "finish_reason", None)
                    details = f" (finish_reason={finish_reason})" if finish_reason else ""
                    raise RuntimeError(f"Empty content in response from OpenAI-compatible API{details}.")
            else:
                raise RuntimeError("No choices returned from OpenAI-compatible API.")

        except Exception as e:
            if is_post_processing_retryable_exception(e):
                logger.warning(f"OpenAI-compatible post-processing attempt failed: {e}. Retrying...")
            else:
                logger.error(f"OpenAI-compatible post-processing failed: {e}")
            raise RuntimeError(f"OpenAI-compatible post-processing failed: {e}") from e
