import abc
import logging

from google import genai
from google.genai import types
from openai import OpenAI

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

class GeminiPostProcessor(BasePostProcessor):
    """Post-processor client utilizing Google Gemini LLMs."""

    def __init__(self, model: str, api_key: str, temperature: float):
        """Initialize Gemini client parameters."""
        self.model = model
        self.api_key = api_key
        self.temperature = temperature

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

            config = types.GenerateContentConfig(
                temperature=self.temperature,
            )

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

            if response.text:
                return response.text, usage
            else:
                raise RuntimeError("Empty response from Gemini.")

        except Exception as e:
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
                content = response.choices[0].message.content
                if content:
                    return content, usage
                else:
                    raise RuntimeError("Empty content in response from OpenAI-compatible API.")
            else:
                raise RuntimeError("No choices returned from OpenAI-compatible API.")

        except Exception as e:
            logger.error(f"OpenAI-compatible post-processing failed: {e}")
            raise RuntimeError(f"OpenAI-compatible post-processing failed: {e}") from e
