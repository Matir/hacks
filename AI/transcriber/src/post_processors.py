import abc
import logging
from openai import OpenAI
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class BasePostProcessor(abc.ABC):
    @abc.abstractmethod
    def post_process(self, transcript: str, prompt_template: str) -> str:
        """Post-process the transcript using the LLM and return the polished text."""
        pass

class GeminiPostProcessor(BasePostProcessor):
    def __init__(self, model: str, api_key: str, temperature: float):
        self.model = model
        self.api_key = api_key
        self.temperature = temperature

    def post_process(self, transcript: str, prompt_template: str) -> str:
        if not self.model:
            raise ValueError("Gemini model must be configured.")

        logger.info(f"Sending request to Gemini: {self.model}")
        try:
            # Initialize Gemini client
            # If api_key is empty, it will try to look up GEMINI_API_KEY in env automatically,
            # but passing it explicitly is safer.
            client = genai.Client(api_key=self.api_key)
            
            # Prepare prompt by injecting transcript
            prompt = prompt_template.replace("{{TRANSCRIPT}}", transcript)

            config = types.GenerateContentConfig(
                temperature=self.temperature,
            )

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )

            if response.text:
                return response.text
            else:
                raise RuntimeError("Empty response from Gemini.")

        except Exception as e:
            logger.error(f"Gemini post-processing failed: {e}")
            raise RuntimeError(f"Gemini post-processing failed: {e}") from e

class OpenAICompatiblePostProcessor(BasePostProcessor):
    def __init__(self, endpoint_url: str, api_key: str, model: str, temperature: float):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def post_process(self, transcript: str, prompt_template: str) -> str:
        if not self.endpoint_url:
            raise ValueError("OpenAI-compatible endpoint URL must be configured.")
        if not self.model:
            raise ValueError("OpenAI-compatible model must be configured.")

        logger.info(f"Sending request to OpenAI-compatible LLM ({self.model}) via: {self.endpoint_url}")
        try:
            # Works for OpenAI, OpenRouter, Local vLLM, DeepSeek, etc.
            client = OpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key
            )

            prompt = prompt_template.replace("{{TRANSCRIPT}}", transcript)

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )

            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    return content
                else:
                    raise RuntimeError("Empty content in response from OpenAI-compatible API.")
            else:
                raise RuntimeError("No choices returned from OpenAI-compatible API.")

        except Exception as e:
            logger.error(f"OpenAI-compatible post-processing failed: {e}")
            raise RuntimeError(f"OpenAI-compatible post-processing failed: {e}") from e
