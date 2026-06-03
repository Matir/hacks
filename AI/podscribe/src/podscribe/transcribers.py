import abc
import inspect
import logging
from pathlib import Path
import httpx
from openai import OpenAI
import re

logger = logging.getLogger(__name__)

class BaseTranscriber(abc.ABC):
    @abc.abstractmethod
    def transcribe(self, file_path: Path) -> str:
        """Transcribe the audio file/directory and return the text transcript."""
        pass

class SpeakerAttributedMixin:
    def transcribe(self, file_path: Path) -> str:
        if file_path.is_dir():
            logger.info(f"Processing speaker-attributed chunks sequentially in directory: {file_path}")
            chunks = sorted([f for f in file_path.iterdir() if f.is_file() and f.suffix.lower() == ".wav"])
            results = []
            for chunk in chunks:
                sig = inspect.signature(self._transcribe_single)
                if "prompt" in sig.parameters:
                    prompt = "\n\n".join(results) if results else ""
                    text = self._transcribe_single(chunk, prompt=prompt)
                else:
                    text = self._transcribe_single(chunk)
                results.append(text)
            return "\n\n".join(results)
        return self._transcribe_single(file_path)

    def format_speaker_segments(self, segments: list) -> str:
        if not segments:
            return ""

        lines = []
        current_speaker = None
        current_speaker_text = []

        for segment in segments:
            if isinstance(segment, dict):
                speaker = segment.get("speaker")
                if speaker is None:
                    speaker = segment.get("speaker_id")
                if speaker is None:
                    speaker = segment.get("speaker_label")
                text = segment.get("text", "").strip()
            else:
                speaker = getattr(segment, "speaker", None)
                if speaker is None:
                    speaker = getattr(segment, "speaker_id", None)
                if speaker is None:
                    speaker = getattr(segment, "speaker_label", None)
                text = getattr(segment, "text", "").strip()

            if not text:
                continue

            # Format speaker identifier cleanly
            if isinstance(speaker, (int, float)):
                speaker_label = f"Speaker {speaker}"
            elif isinstance(speaker, str) and speaker.isdigit():
                speaker_label = f"Speaker {speaker}"
            else:
                speaker_label = speaker or "Speaker Unknown"
            speaker_label = str(speaker_label)

            if current_speaker is None:
                current_speaker = speaker_label
                current_speaker_text.append(text)
            elif current_speaker == speaker_label:
                current_speaker_text.append(text)
            else:
                lines.append(f"[{current_speaker}]: {' '.join(current_speaker_text)}")
                current_speaker = speaker_label
                current_speaker_text = [text]

        if current_speaker is not None and current_speaker_text:
            lines.append(f"[{current_speaker}]: {' '.join(current_speaker_text)}")

        return "\n\n".join(lines)

class HuggingFaceTranscriber(BaseTranscriber):
    def __init__(self, endpoint_url: str, api_key: str, model: str):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model = model

    def transcribe(self, file_path: Path) -> str:
        if file_path.is_dir():
            logger.info(f"Processing chunks sequentially in directory: {file_path}")
            chunks = sorted([f for f in file_path.iterdir() if f.is_file() and f.suffix.lower() == ".wav"])
            results = []
            for chunk in chunks:
                results.append(self._transcribe_single(chunk))
            return " ".join(results)
        return self._transcribe_single(file_path)

    def _transcribe_single(self, file_path: Path) -> str:
        logger.debug(f"Sending audio chunk {file_path.name} to Hugging Face ASR pipeline")
        if not self.endpoint_url:
            raise ValueError("Hugging Face endpoint URL must be configured.")

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(f"Sending request to Hugging Face: {self.endpoint_url}")
        try:
            with open(file_path, "rb") as f:
                audio_data = f.read()

            with httpx.Client(timeout=300.0) as client:
                response = client.post(
                    self.endpoint_url,
                    headers=headers,
                    content=audio_data
                )

                if response.status_code != 200:
                    logger.error(f"HF Error: {response.status_code} - {response.text}")
                    response.raise_for_status()

                result = response.json()

                if isinstance(result, dict) and "text" in result:
                    return result["text"]
                elif isinstance(result, list) and len(result) > 0 and "text" in result[0]:
                    return result[0]["text"]
                else:
                    logger.warning(f"Unexpected HF response structure: {result}")
                    return str(result)

        except Exception as e:
            logger.error(f"Hugging Face transcription failed: {e}")
            raise RuntimeError(f"Hugging Face transcription failed: {e}") from e

class SpeakerAttributedHuggingFaceTranscriber(SpeakerAttributedMixin, HuggingFaceTranscriber):
    def _transcribe_single(self, file_path: Path) -> str:
        logger.debug(f"Sending audio chunk {file_path.name} to speaker-attributed Hugging Face ASR pipeline")
        if not self.endpoint_url:
            raise ValueError("Hugging Face endpoint URL must be configured.")

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(f"Sending request to speaker-attributed Hugging Face: {self.endpoint_url}")
        try:
            with open(file_path, "rb") as f:
                audio_data = f.read()

            with httpx.Client(timeout=300.0) as client:
                response = client.post(
                    self.endpoint_url,
                    headers=headers,
                    content=audio_data
                )

                if response.status_code != 200:
                    logger.error(f"HF Error: {response.status_code} - {response.text}")
                    response.raise_for_status()

                result = response.json()

                # Check for segments or chunks
                segments = None
                if isinstance(result, dict):
                    segments = result.get("segments") or result.get("chunks")

                if segments:
                    return self.format_speaker_segments(segments)

                # Fallback to standard parsing
                if isinstance(result, dict) and "text" in result:
                    return result["text"]
                elif isinstance(result, list) and len(result) > 0 and "text" in result[0]:
                    return result[0]["text"]
                else:
                    logger.warning(f"Unexpected HF response structure: {result}")
                    return str(result)

        except Exception as e:
            logger.error(f"Speaker attributed Hugging Face transcription failed: {e}")
            raise RuntimeError(f"Speaker attributed Hugging Face transcription failed: {e}") from e

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
        if file_path.is_dir():
            logger.info(f"Processing chunks sequentially in directory: {file_path}")
            chunks = sorted([f for f in file_path.iterdir() if f.is_file() and f.suffix.lower() == ".wav"])
            results = []
            for chunk in chunks:
                prompt = " ".join(results) if results else ""
                text = self._transcribe_single(chunk, prompt=prompt)
                results.append(text)
            return " ".join(results)
        return self._transcribe_single(file_path)

    def _transcribe_single(self, file_path: Path, prompt: str = "") -> str:
        logger.debug(f"Sending audio chunk {file_path.name} to OpenAI-compatible ASR pipeline")
        if not self.endpoint_url:
            raise ValueError("OpenAI Compatible endpoint URL must be configured.")

        logger.info(f"Sending request to OpenAI-compatible endpoint: {self.endpoint_url}")
        try:
            client = OpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key or "dummy-key"
            )

            extra_body = {}
            if prompt:
                extra_body["prefix_text"] = prompt

            with open(file_path, "rb") as audio_file:
                transcript_response = client.audio.transcriptions.create(
                    model=self.model or "default",
                    file=audio_file,
                    response_format="text",
                    prompt=prompt or None,
                    extra_body=extra_body if extra_body else None
                )

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

class SpeakerAttributedOpenAICompatibleTranscriber(SpeakerAttributedMixin, OpenAICompatibleTranscriber):
    def _transcribe_single(self, file_path: Path, prompt: str = "") -> str:
        logger.debug(f"Sending audio chunk {file_path.name} to speaker-attributed OpenAI-compatible ASR pipeline")
        if not self.endpoint_url:
            raise ValueError("OpenAI Compatible endpoint URL must be configured.")

        logger.info(f"Sending request to speaker-attributed OpenAI-compatible endpoint: {self.endpoint_url}")
        try:
            client = OpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key or "dummy-key"
            )

            extra_body = {"diarize": True}
            if prompt:
                extra_body["prefix_text"] = prompt

            with open(file_path, "rb") as audio_file:
                transcript_response = client.audio.transcriptions.create(
                    model=self.model or "default",
                    file=audio_file,
                    response_format="verbose_json",
                    prompt=prompt or None,
                    extra_body=extra_body
                )

            if isinstance(transcript_response, str):
                return transcript_response

            # Extract segments (handles both standard objects and dicts if parsed differently)
            segments = getattr(transcript_response, "segments", None)
            if isinstance(transcript_response, dict):
                segments = transcript_response.get("segments")

            if not segments:
                if hasattr(transcript_response, "text"):
                    return transcript_response.text
                elif isinstance(transcript_response, dict) and "text" in transcript_response:
                    return transcript_response["text"]
                return str(transcript_response)

            return self.format_speaker_segments(segments)

        except Exception as e:
            logger.error(f"Speaker attributed OpenAI-compatible transcription failed: {e}")
            raise RuntimeError(f"Speaker attributed OpenAI-compatible transcription failed: {e}") from e

class CrispASRTranscriber(OpenAICompatibleTranscriber):
    def transcribe(self, file_path: Path) -> str:
        if file_path.is_dir():
            logger.info(f"Processing CrispASR chunks sequentially in directory: {file_path}")
            chunks = sorted([f for f in file_path.iterdir() if f.is_file() and f.suffix.lower() == ".wav"])
            results = []
            current_speaker = None
            current_text = []
            
            for chunk in chunks:
                text, speaker = self._transcribe_single_crisp(chunk)
                if not text:
                    continue
                
                if current_speaker is None:
                    current_speaker = speaker
                    current_text.append(text)
                elif current_speaker == speaker:
                    current_text.append(text)
                else:
                    speaker_label = f"[{current_speaker}]: " if current_speaker else ""
                    results.append(f"{speaker_label}{' '.join(current_text)}")
                    current_speaker = speaker
                    current_text = [text]
            
            if current_speaker is not None and current_text:
                speaker_label = f"[{current_speaker}]: " if current_speaker else ""
                results.append(f"{speaker_label}{' '.join(current_text)}")
                
            return "\n\n".join(results)
        
        text, speaker = self._transcribe_single_crisp(file_path)
        if speaker:
            return f"[{speaker}]: {text}"
        return text

    def _transcribe_single_crisp(self, file_path: Path) -> tuple[str, str]:
        logger.debug(f"Sending audio chunk {file_path.name} to CrispASR pipeline")
        if not self.endpoint_url:
            raise ValueError("CrispASR endpoint URL must be configured.")

        logger.info(f"Sending request to CrispASR endpoint: {self.endpoint_url}")
        try:
            client = OpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key or "dummy-key"
            )

            with open(file_path, "rb") as audio_file:
                raw_response = client.audio.transcriptions.with_raw_response.create(
                    model=self.model or "default",
                    file=audio_file,
                    response_format="json",
                )
                
                response_json = raw_response.http_response.json()
                text = response_json.get("text", "").strip()
                speaker = response_json.get("speaker", "").strip()
                return text, speaker

        except Exception as e:
            logger.error(f"CrispASR transcription failed: {e}")
            raise RuntimeError(f"CrispASR transcription failed: {e}") from e
