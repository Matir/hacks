import abc
import base64
import inspect
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import assemblyai as aai
import httpx
import openai
from openai import OpenAI
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

def is_transcription_retryable_exception(exception: Exception) -> bool:
    """Determine whether an exception during transcription should trigger a retry (e.g. rate limits, timeouts)."""
    # Unwrap RuntimeError if it was wrapped
    cause = exception.__cause__ if isinstance(exception, RuntimeError) and exception.__cause__ else exception

    # Check httpx exceptions
    if isinstance(cause, (httpx.TimeoutException, httpx.NetworkError)):
        return True

    if isinstance(cause, httpx.HTTPStatusError):
        # 429 (Rate Limit), 502 (Bad Gateway), 503 (Service Unavailable), 504 (Gateway Timeout)
        return cause.response.status_code in (429, 502, 503, 504)

    # Check OpenAI exceptions
    if isinstance(cause, (openai.APITimeoutError, openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)):
        return True
    if isinstance(cause, openai.APIStatusError):
        if cause.status_code in (429, 502, 503, 504):
            return True

    return False

class BaseTranscriber(abc.ABC):
    """Abstract base class defining the interface for all ASR transcribers."""

    @abc.abstractmethod
    def transcribe(self, file_path: Path) -> str:
        """Transcribe the audio file/directory and return the text transcript."""
        pass

    def _transcribe_directory(
        self, file_path: Path, join_char: str = " ", pass_prompt: bool = False
    ) -> str:
        """Transcribe all WAV chunk files in a directory sequentially or concurrently and join their texts."""
        chunks = sorted([f for f in file_path.iterdir() if f.is_file() and f.suffix.lower() == ".wav"])
        if not chunks:
            return ""

        max_workers = getattr(self, "max_workers", 1)
        if max_workers > 1:
            logger.info(f"Processing {len(chunks)} chunks concurrently in directory: {file_path} (workers={max_workers})")
            def worker(chunk: Path) -> str:
                if pass_prompt and inspect.signature(self._transcribe_single).parameters.get("prompt"):
                    return self._transcribe_single(chunk, prompt="")
                return self._transcribe_single(chunk)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(worker, chunks))
            return join_char.join(results)

        logger.info(f"Processing chunks sequentially in directory: {file_path}")
        results = []
        for chunk in chunks:
            if pass_prompt and inspect.signature(self._transcribe_single).parameters.get("prompt"):
                prompt = join_char.join(results) if results else ""
                text = self._transcribe_single(chunk, prompt=prompt)
            else:
                text = self._transcribe_single(chunk)
            results.append(text)
        return join_char.join(results)

class SpeakerAttributedMixin:
    """Mixin providing sequential directory processing and speaker attribution formatting."""

    def transcribe(self, file_path: Path) -> str:
        """Transcribe an audio file or sequentially process a directory of chunks with speaker labels."""
        if file_path.is_dir():
            return self._transcribe_directory(file_path, join_char="\n\n", pass_prompt=True)
        return self._transcribe_single(file_path)

    def format_speaker_segments(self, segments: list) -> str:
        """Format a list of raw segment dictionaries into a speaker-attributed dialogue transcript."""
        if not segments:
            return ""

        lines = []
        current_speaker = None
        current_speaker_text = []

        for segment in segments:
            if isinstance(segment, dict):
                speaker = segment.get("speaker")
                if speaker is None:
                    speaker = segment.get("Speaker")
                if speaker is None:
                    speaker = segment.get("speaker_id")
                if speaker is None:
                    speaker = segment.get("speaker_label")

                text = segment.get("text")
                if text is None:
                    text = segment.get("Content")
                if text is None:
                    text = segment.get("content")
                text = (text or "").strip()
            else:
                speaker = getattr(segment, "speaker", None)
                if speaker is None:
                    speaker = getattr(segment, "Speaker", None)
                if speaker is None:
                    speaker = getattr(segment, "speaker_id", None)
                if speaker is None:
                    speaker = getattr(segment, "speaker_label", None)

                text = getattr(segment, "text", None)
                if text is None:
                    text = getattr(segment, "Content", None)
                if text is None:
                    text = getattr(segment, "content", None)
                text = (text or "").strip()

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
    """Transcriber client that connects to standard HuggingFace Inference API endpoints."""

    def __init__(self, endpoint_url: str, api_key: str, model: str, language: str = "en", timeout: float = 300.0):
        """Initialize the HuggingFace API transcriber client."""
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model = model
        self.language = language
        self.timeout = timeout

    def transcribe(self, file_path: Path) -> str:
        """Transcribe an audio file or sequentially process a chunk directory."""
        if file_path.is_dir():
            return self._transcribe_directory(file_path, join_char=" ", pass_prompt=False)
        return self._transcribe_single(file_path)

    def _handle_error_response(self, response: httpx.Response, prefix: str = "HF"):
        """Extract and log structured API errors from HTTP responses."""
        error_msg = response.text
        try:
            err_json = response.json()
            if isinstance(err_json, dict) and "error" in err_json:
                error_msg = err_json["error"]
        except Exception:
            pass
        logger.error(f"{prefix} Error: {response.status_code} - {error_msg}")
        response.raise_for_status()

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=30),
        retry=retry_if_exception(is_transcription_retryable_exception)
    )
    def _transcribe_single(self, file_path: Path) -> str:
        """Send a single audio chunk to the HuggingFace ASR endpoint with exponential retry."""
        logger.debug(f"Sending audio chunk {file_path.name} to Hugging Face ASR pipeline")
        if not self.endpoint_url:
            raise ValueError("Hugging Face endpoint URL must be configured.")

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(f"Sending request to Hugging Face: {self.endpoint_url}")
        response: httpx.Response | None = None
        try:
            with open(file_path, "rb") as audio_file:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.endpoint_url,
                        headers=headers,
                        content=audio_file
                    )

            if response is None:
                raise ValueError("expected a response object")

            if response.status_code != 200:
                self._handle_error_response(response, "HF")

            result = response.json()

            if isinstance(result, dict) and "text" in result:
                return result["text"]
            elif isinstance(result, list) and len(result) > 0 and "text" in result[0]:
                return result[0]["text"]
            else:
                logger.warning(f"Unexpected HF response structure: {result}")
                return str(result)

        except Exception as e:
            if is_transcription_retryable_exception(e):
                logger.warning(f"Hugging Face transcription attempt failed: {e}. Retrying...")
            else:
                logger.error(f"Hugging Face transcription failed: {e}")
            raise RuntimeError(f"Hugging Face transcription failed: {e}") from e

class SpeakerAttributedHuggingFaceTranscriber(SpeakerAttributedMixin, HuggingFaceTranscriber):
    """HuggingFace transcriber that formats response segments with speaker attribution."""
    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=30),
        retry=retry_if_exception(is_transcription_retryable_exception)
    )
    def _transcribe_single(self, file_path: Path) -> str:
        """Send audio to a speaker-attributed HuggingFace endpoint and parse segment speaker labels."""
        logger.debug(f"Sending audio chunk {file_path.name} to speaker-attributed Hugging Face ASR pipeline")
        if not self.endpoint_url:
            raise ValueError("Hugging Face endpoint URL must be configured.")

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(f"Sending request to speaker-attributed Hugging Face: {self.endpoint_url}")
        try:
            with open(file_path, "rb") as audio_file:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.endpoint_url,
                        headers=headers,
                        content=audio_file
                    )

                if response.status_code != 200:
                    self._handle_error_response(response, "HF")

                result = response.json()

                # Check for segments or chunks
                segments = None
                if isinstance(result, dict):
                    segments = result.get("segments") or result.get("chunks")
                    if not segments:
                        # Fallback: scan for any list of dicts in the values
                        for val in result.values():
                            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                                segments = val
                                break
                elif isinstance(result, list):
                    segments = result

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
            if is_transcription_retryable_exception(e):
                logger.warning(f"Speaker attributed Hugging Face transcription attempt failed: {e}. Retrying...")
            else:
                logger.error(f"Speaker attributed Hugging Face transcription failed: {e}")
            raise RuntimeError(f"Speaker attributed Hugging Face transcription failed: {e}") from e

class OpenAICompatibleTranscriber(BaseTranscriber):
    """Transcriber client utilizing the OpenAI Python SDK for /audio/transcriptions endpoints."""

    def __init__(self, endpoint_url: str, api_key: str, model: str, language: str = "en", timeout: float = 300.0):
        """Initialize the OpenAI-compatible ASR client."""
        if endpoint_url:
            endpoint_url = endpoint_url.rstrip("/")
            if endpoint_url.endswith("/audio/transcriptions"):
                logger.warning("Stripping '/audio/transcriptions' from endpoint_url.")
                endpoint_url = endpoint_url.removesuffix("/audio/transcriptions")
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model = model
        self.language = language
        self.timeout = timeout

    def transcribe(self, file_path: Path) -> str:
        """Transcribe audio file or directory of chunks, passing prior transcript text as prompt."""
        if file_path.is_dir():
            return self._transcribe_directory(file_path, join_char=" ", pass_prompt=True)
        return self._transcribe_single(file_path)

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=30),
        retry=retry_if_exception(is_transcription_retryable_exception)
    )
    def _transcribe_single(self, file_path: Path, prompt: str = "") -> str:
        """Send a single audio chunk to the OpenAI-compatible endpoint with exponential retry."""
        logger.debug(f"Sending audio chunk {file_path.name} to OpenAI-compatible ASR pipeline")
        if not self.endpoint_url:
            raise ValueError("OpenAI Compatible endpoint URL must be configured.")

        logger.info(f"Sending request to OpenAI-compatible endpoint: {self.endpoint_url}")
        try:
            client = OpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key or "dummy-key",
                timeout=self.timeout
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
                    extra_body=extra_body if extra_body else None,
                    language=self.language
                )

            if isinstance(transcript_response, str):
                return transcript_response
            elif hasattr(transcript_response, "text"):
                return transcript_response.text
            else:
                logger.warning(f"Unexpected OpenAI-compatible response: {transcript_response}")
                return str(transcript_response)

        except Exception as e:
            if is_transcription_retryable_exception(e):
                logger.warning(f"OpenAI-compatible transcription attempt failed: {e}. Retrying...")
            else:
                logger.error(f"OpenAI-compatible transcription failed: {e}")
            raise RuntimeError(f"OpenAI-compatible transcription failed: {e}") from e

class SpeakerAttributedOpenAICompatibleTranscriber(SpeakerAttributedMixin, OpenAICompatibleTranscriber):
    """OpenAI-compatible transcriber requesting diarization and parsing speaker labels."""

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=30),
        retry=retry_if_exception(is_transcription_retryable_exception)
    )
    def _transcribe_single(self, file_path: Path, prompt: str = "") -> str:
        """Send audio chunk requesting verbose JSON with diarization enabled."""
        logger.debug(f"Sending audio chunk {file_path.name} to speaker-attributed OpenAI-compatible ASR pipeline")
        if not self.endpoint_url:
            raise ValueError("OpenAI Compatible endpoint URL must be configured.")

        logger.info(f"Sending request to speaker-attributed OpenAI-compatible endpoint: {self.endpoint_url}")
        try:
            client = OpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key or "dummy-key",
                timeout=self.timeout
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
                    extra_body=extra_body,
                    language=self.language
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
            if is_transcription_retryable_exception(e):
                logger.warning(f"Speaker attributed OpenAI-compatible transcription attempt failed: {e}. Retrying...")
            else:
                logger.error(f"Speaker attributed OpenAI-compatible transcription failed: {e}")
            raise RuntimeError(f"Speaker attributed OpenAI-compatible transcription failed: {e}") from e

class CrispASRTranscriber(OpenAICompatibleTranscriber):
    """Transcriber for specialized CrispASR OpenAI-compatible servers returning segment speaker IDs."""

    def transcribe(self, file_path: Path) -> str:
        """Transcribe audio chunk or directory, merging consecutive chunks from the same speaker."""
        if file_path.is_dir():
            chunks = sorted([f for f in file_path.iterdir() if f.is_file() and f.suffix.lower() == ".wav"])
            max_workers = getattr(self, "max_workers", 1)
            if max_workers > 1:
                logger.info(f"Processing {len(chunks)} CrispASR chunks concurrently in directory: {file_path} (workers={max_workers})")
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    chunk_results = list(executor.map(self._transcribe_single_crisp, chunks))
            else:
                logger.info(f"Processing CrispASR chunks sequentially in directory: {file_path}")
                chunk_results = [self._transcribe_single_crisp(chunk) for chunk in chunks]

            results = []
            current_speaker = None
            current_text = []

            for text, speaker in chunk_results:
                if not text:
                    continue

                if current_speaker is None:
                    current_speaker = speaker
                    current_text.append(text)
                elif current_speaker == speaker:
                    current_text.append(text)
                else:
                    results.append(f"[{current_speaker}]: {' '.join(current_text)}")
                    current_speaker = speaker
                    current_text = [text]

            if current_speaker is not None and current_text:
                results.append(f"[{current_speaker}]: {' '.join(current_text)}")

            return "\n\n".join(results)

        text, speaker = self._transcribe_single_crisp(file_path)
        return f"[{speaker}]: {text}"

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=30),
        retry=retry_if_exception(is_transcription_retryable_exception)
    )
    def _transcribe_single_crisp(self, file_path: Path) -> tuple[str, str]:
        """Send a single chunk requesting verbose JSON and extract (text, speaker)."""
        logger.debug(f"Sending audio chunk {file_path.name} to CrispASR pipeline")
        if not self.endpoint_url:
            raise ValueError("CrispASR endpoint URL must be configured.")

        logger.debug(
            f"CrispASR Request: url={self.endpoint_url}, "
            f"model={self.model or 'default'}, "
            f"response_format=verbose_json, "
            f"diarize=True, "
            f"language={self.language}, "
            f"file={file_path.name}"
        )

        logger.info(f"Sending request to CrispASR endpoint: {self.endpoint_url}")
        try:
            client = OpenAI(
                base_url=self.endpoint_url,
                api_key=self.api_key or "dummy-key",
                timeout=self.timeout
            )

            with open(file_path, "rb") as audio_file:
                raw_response = client.audio.transcriptions.with_raw_response.create(
                    model=self.model or "default",
                    file=audio_file,
                    response_format="verbose_json",
                    extra_body={"diarize": True},
                    language=self.language
                )

                response_json = raw_response.http_response.json()
                logger.debug(f"CrispASR Response: {response_json}")
                text = response_json.get("text", "").strip()
                speaker = response_json.get("speaker", "").strip() or "Speaker Unknown"
                return text, speaker

        except Exception as e:
            if is_transcription_retryable_exception(e):
                logger.warning(f"CrispASR transcription attempt failed: {e}. Retrying...")
            else:
                logger.error(f"CrispASR transcription failed: {e}")
            raise RuntimeError(f"CrispASR transcription failed: {e}") from e

CRISPASR_MODEL_FAMILY_SETTINGS = {
    "parakeet": {
        "cmd_template": '"{binary_path}" -m "{model}" --backend "{backend}" -f "{file_path}" {diarize_flags} -ojf -of "{output_path}"',
        "diarize_flags": '--diarize --diarize-method "{diarize_method}" --sherpa-segment-model auto --diarize-embedder auto',
        "json_segments_key": "segments",
        "json_text_key": "text",
        "json_speaker_key": "speaker",
    },
    "whisper": {
        "cmd_template": '"{binary_path}" -m "{model}" --backend "{backend}" -f "{file_path}" {diarize_flags} -ojf -of "{output_path}"',
        "diarize_flags": '--diarize --diarize-method "{diarize_method}" --sherpa-segment-model auto --diarize-embedder auto',
        "json_segments_key": "segments",
        "json_text_key": "text",
        "json_speaker_key": "speaker",
    },
    "default": {
        "cmd_template": '"{binary_path}" -m "{model}" --backend "{backend}" -f "{file_path}" {diarize_flags} -ojf -of "{output_path}"',
        "diarize_flags": '--diarize --diarize-method "{diarize_method}" --sherpa-segment-model auto --diarize-embedder auto',
        "json_segments_key": "segments",
        "json_text_key": "text",
        "json_speaker_key": "speaker",
    }
}

def _detect_model_family(model: str, backend: str) -> str:
    """Identify the CLI model family ('parakeet', 'whisper', or 'default') from model and backend strings."""
    model_lower = model.lower() if model else ""
    backend_lower = backend.lower() if backend else ""

    if "parakeet" in backend_lower or "parakeet" in model_lower:
        return "parakeet"
    if "whisper" in backend_lower or "whisper" in model_lower:
        return "whisper"

    return "default"

class CrispASRCLITranscriber(SpeakerAttributedMixin, BaseTranscriber):
    """Transcriber executing local CrispASR command-line binary inside a temporary workspace."""

    def __init__(self, binary_path: str, model: str, backend: str, diarize_method: str):
        """Initialize CLI transcriber parameters."""
        self.binary_path = binary_path or "crispasr"
        self.model = model or "auto"
        self.backend = backend or "auto"
        self.diarize_method = diarize_method or "pyannote"

    def _transcribe_single(self, file_path: Path) -> str:
        """Execute local CrispASR CLI subprocess on a single chunk and parse output JSON."""
        import json
        import shlex
        import subprocess
        import tempfile

        family = _detect_model_family(self.model, self.backend)
        settings = CRISPASR_MODEL_FAMILY_SETTINGS.get(family, CRISPASR_MODEL_FAMILY_SETTINGS["default"])

        with tempfile.TemporaryDirectory(prefix="podscribe_crispasr_") as tmpdir:
            output_prefix = Path(tmpdir) / "transcribed"
            json_path = Path(tmpdir) / "transcribed.json"

            diarize_flags = ""
            if self.diarize_method != "none":
                diarize_flags = settings["diarize_flags"].format(
                    diarize_method=self.diarize_method
                )

            cmd_str = settings["cmd_template"].format(
                binary_path=self.binary_path,
                model=self.model,
                backend=self.backend,
                file_path=str(file_path),
                diarize_flags=diarize_flags,
                output_path=str(output_prefix)
            )

            cmd = shlex.split(cmd_str)

            logger.info(f"Running CrispASR CLI: {' '.join(cmd)}")
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                logger.debug(f"CrispASR CLI stdout: {result.stdout}")
                logger.debug(f"CrispASR CLI stderr: {result.stderr}")
            except subprocess.CalledProcessError as e:
                logger.error(f"CrispASR CLI failed with exit code {e.returncode}")
                logger.error(f"CrispASR CLI stderr: {e.stderr}")
                raise RuntimeError(f"CrispASR CLI failed: {e.stderr}") from e

            if not json_path.exists():
                raise FileNotFoundError(f"CrispASR CLI did not produce expected JSON file at {json_path}")

            with open(json_path, "r") as f:
                data = json.load(f)

            if self.diarize_method == "none":
                text_key = settings.get("json_text_key", "text")
                if text_key in data:
                    return data[text_key].strip()
                segments_key = settings.get("json_segments_key", "segments")
                segments = data.get(segments_key, [])
                return " ".join([seg.get(text_key, "").strip() for seg in segments])
            else:
                segments_key = settings.get("json_segments_key", "segments")
                segments = data.get(segments_key, [])

                mapped_segments = []
                text_key = settings.get("json_segment_text_key") or settings.get("json_text_key", "text")
                speaker_key = settings.get("json_segment_speaker_key") or settings.get("json_speaker_key", "speaker")

                for seg in segments:
                    mapped_segments.append({
                        "speaker": seg.get(speaker_key),
                        "text": seg.get(text_key, "")
                    })

                return self.format_speaker_segments(mapped_segments)

class VibeVoiceASRTranscriber(HuggingFaceTranscriber):
    """Transcriber for VibeVoice endpoints accepting base64-encoded audio and optional hotwords."""

    def __init__(self, endpoint_url: str, api_key: str, model: str, language: str = "en", hotwords: str = "", timeout: float = 300.0):
        """Initialize VibeVoice client parameters."""
        super().__init__(endpoint_url, api_key, model, language, timeout=timeout)
        self.hotwords = hotwords

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1.5, min=2, max=30),
        retry=retry_if_exception(is_transcription_retryable_exception)
    )
    def _transcribe_single(self, file_path: Path) -> str:
        """Encode audio to base64 and POST JSON payload to VibeVoice endpoint."""
        logger.debug(f"Sending audio chunk {file_path.name} to VibeVoice ASR pipeline")
        if not self.endpoint_url:
            raise ValueError("VibeVoice endpoint URL must be configured.")

        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(f"Sending request to VibeVoice: {self.endpoint_url}")
        try:
            with open(file_path, "rb") as f:
                audio_bytes = f.read()
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            payload = {
                "inputs": audio_b64,
                "parameters": {}
            }
            if self.hotwords:
                payload["parameters"]["hotwords"] = self.hotwords

            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.endpoint_url,
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    self._handle_error_response(response, "VibeVoice")

                result = response.json()

                if isinstance(result, dict):
                    if "result" in result:
                        return result["result"]
                    elif "text" in result:
                        return result["text"]

                logger.warning(f"Unexpected VibeVoice response structure: {result}")
                return str(result)

        except Exception as e:
            if is_transcription_retryable_exception(e):
                logger.warning(f"VibeVoice transcription attempt failed: {e}. Retrying...")
            else:
                logger.error(f"VibeVoice transcription failed: {e}")
            raise RuntimeError(f"VibeVoice transcription failed: {e}") from e


class AssemblyAITranscriber(SpeakerAttributedMixin, BaseTranscriber):
    """Transcriber integrating with official AssemblyAI API, supporting prompts, keyterms, and diarization."""

    def __init__(
        self,
        api_key: str,
        model: str = "universal-3-pro",
        language: str = "en",
        enable_speaker_attribution: bool = True,
        prompt_file: str | Path = "prompts/assemblyai.md",
        keyterms_file: str | Path = "prompts/keyterms.txt",
    ):
        """Initialize AssemblyAI parameters and prompt/keyterm paths."""
        self.api_key = api_key
        self.model = model or "universal-3-pro"
        self.language = language
        self.enable_speaker_attribution = enable_speaker_attribution
        self.prompt_file = Path(prompt_file)
        self.keyterms_file = Path(keyterms_file)

    def _transcribe_single(self, file_path: Path) -> str:
        """Execute AssemblyAI transcription with prompt/keyterm boosting and return attributed text."""
        logger.debug(f"Sending audio file {file_path.name} to AssemblyAI")
        if not self.api_key:
            raise ValueError("AssemblyAI API key must be configured.")

        # Configure the AssemblyAI client settings
        aai.settings.api_key = self.api_key

        # Build fallback list
        speech_models = [self.model]
        if self.model == "universal-3-pro" and "universal-2" not in speech_models:
            speech_models.append("universal-2")

        # Set up configuration parameters
        config_params = {
            "speech_models": speech_models,
            "speaker_labels": self.enable_speaker_attribution,
        }

        if self.language and self.language.lower() != "auto":
            config_params["language_code"] = self.language
        else:
            config_params["language_detection"] = True

        if self.prompt_file.exists() and self.prompt_file.is_file():
            try:
                prompt_content = self.prompt_file.read_text(encoding="utf-8").strip()
                if prompt_content:
                    config_params["prompt"] = prompt_content
            except Exception as e:
                logger.warning(f"Failed to read AssemblyAI prompt file {self.prompt_file}: {e}")

        if self.keyterms_file.exists() and self.keyterms_file.is_file():
            try:
                keyterms = [
                    line.strip()
                    for line in self.keyterms_file.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                if keyterms:
                    config_params["keyterms_prompt"] = keyterms
                    config_params["word_boost"] = keyterms
            except Exception as e:
                logger.warning(f"Failed to read AssemblyAI keyterms file {self.keyterms_file}: {e}")

        config = aai.TranscriptionConfig(**config_params)

        try:
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe(str(file_path))

            if transcript.status == aai.TranscriptStatus.error:
                logger.error(f"AssemblyAI Error: {transcript.error}")
                raise RuntimeError(
                    f"AssemblyAI transcription failed: {transcript.error}"
                )

            if self.enable_speaker_attribution and transcript.utterances:
                return self.format_speaker_segments(transcript.utterances)

            return transcript.text or ""

        except Exception as e:
            logger.error(f"AssemblyAI transcription failed: {e}")
            raise RuntimeError(f"AssemblyAI transcription failed: {e}") from e
