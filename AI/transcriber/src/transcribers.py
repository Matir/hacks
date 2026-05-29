import abc
import logging
from pathlib import Path
import httpx
from openai import OpenAI

logger = logging.getLogger(__name__)

class BaseTranscriber(abc.ABC):
    @abc.abstractmethod
    def transcribe(self, file_path: Path) -> str:
        """Transcribe the audio file and return the text transcript."""
        pass

class HuggingFaceTranscriber(BaseTranscriber):
    def __init__(self, endpoint_url: str, api_key: str, model: str):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model = model

    def transcribe(self, file_path: Path) -> str:
        if not self.endpoint_url:
            raise ValueError("Hugging Face endpoint URL must be configured.")

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # For large files, reading the whole file into memory might be heavy, 
        # but for ASR, we usually preprocess to 16k mono wav, which is relatively small.
        logger.info(f"Sending request to Hugging Face: {self.endpoint_url}")
        try:
            with open(file_path, "rb") as f:
                audio_data = f.read()

            # Using httpx for API call
            # Timeout is set long (e.g., 300s) as transcription can take time
            with httpx.Client(timeout=300.0) as client:
                response = client.post(
                    self.endpoint_url,
                    headers=headers,
                    content=audio_data
                )
                
                # Handle error status
                if response.status_code != 200:
                    logger.error(f"HF Error: {response.status_code} - {response.text}")
                    response.raise_for_status()
                
                result = response.json()
                
                # HF standard ASR returns {"text": "..."}
                if isinstance(result, dict) and "text" in result:
                    return result["text"]
                elif isinstance(result, list) and len(result) > 0 and "text" in result[0]:
                    return result[0]["text"]
                else:
                    # Fallback if structure is unexpected
                    logger.warning(f"Unexpected HF response structure: {result}")
                    return str(result)

        except Exception as e:
            logger.error(f"Hugging Face transcription failed: {e}")
            raise RuntimeError(f"Hugging Face transcription failed: {e}") from e

class OpenAICompatibleTranscriber(BaseTranscriber):
    def __init__(self, endpoint_url: str, api_key: str, model: str):
        if endpoint_url:
            endpoint_url = endpoint_url.rstrip("/")
            if endpoint_url.endswith("/audio/transcriptions"):
                logger.warning("Stripping '/audio/transcriptions' from endpoint_url.")
                endpoint_url = endpoint_url.removesuffix("/audio/transcriptions")
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model = model

    def transcribe(self, file_path: Path) -> str:
        if not self.endpoint_url:
            raise ValueError("OpenAI Compatible endpoint URL must be configured.")

        logger.info(f"Sending request to OpenAI-compatible endpoint: {self.endpoint_url}")
        try:
            # Initialize client with custom base_url
            client = OpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key or "dummy-key" # Some local vLLM/Baseten might not need a key but client requires one
            )

            with open(file_path, "rb") as audio_file:
                # Call standard transcribe endpoint
                # Using long timeout because model might need time
                transcript_response = client.audio.transcriptions.create(
                    model=self.model or "default",
                    file=audio_file,
                    response_format="text" # We can ask for text or json. "text" is simpler.
                )
            
            # If response_format is text, it usually returns a string.
            # If it returns an object, extract text.
            if isinstance(transcript_response, str):
                return transcript_response
            elif hasattr(transcript_response, "text"):
                return transcript_response.text
            else:
                logger.warning(f"Unexpected OpenAI-compatible response: {transcript_response}")
                return str(transcript_response)

        except Exception as e:
            logger.error(f"OpenAI-compatible transcription failed: {e}")
            raise RuntimeError(f"OpenAI-compatible transcription failed: {e}") from e
