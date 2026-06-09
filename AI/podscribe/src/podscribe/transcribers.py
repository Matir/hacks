import abc
import base64
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
    def __init__(self, endpoint_url: str, api_key: str, model: str, language: str = "en"):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model = model
        self.language = language

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
    def __init__(self, endpoint_url: str, api_key: str, model: str, language: str = "en"):
        if endpoint_url:
            endpoint_url = endpoint_url.rstrip("/")
            if endpoint_url.endswith("/audio/transcriptions"):
                logger.warning("Stripping '/audio/transcriptions' from endpoint_url.")
                endpoint_url = endpoint_url.removesuffix("/audio/transcriptions")
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model = model
        self.language = language

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
                    results.append(f"[{current_speaker}]: {' '.join(current_text)}")
                    current_speaker = speaker
                    current_text = [text]
            
            if current_speaker is not None and current_text:
                results.append(f"[{current_speaker}]: {' '.join(current_text)}")
                
            return "\n\n".join(results)
        
        text, speaker = self._transcribe_single_crisp(file_path)
        return f"[{speaker}]: {text}"

    def _transcribe_single_crisp(self, file_path: Path) -> tuple[str, str]:
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
                api_key=self.api_key or "dummy-key"
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
    model_lower = model.lower() if model else ""
    backend_lower = backend.lower() if backend else ""
    
    if "parakeet" in backend_lower or "parakeet" in model_lower:
        return "parakeet"
    if "whisper" in backend_lower or "whisper" in model_lower:
        return "whisper"
    
    return "default"

class CrispASRCLITranscriber(SpeakerAttributedMixin, BaseTranscriber):
    def __init__(self, binary_path: str, model: str, backend: str, diarize_method: str):
        self.binary_path = binary_path or "crispasr"
        self.model = model or "auto"
        self.backend = backend or "auto"
        self.diarize_method = diarize_method or "pyannote"
        
    def _transcribe_single(self, file_path: Path) -> str:
        import subprocess
        import tempfile
        import json
        import shlex
        
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
    def __init__(self, endpoint_url: str, api_key: str, model: str, language: str = "en", hotwords: str = ""):
        super().__init__(endpoint_url, api_key, model, language)
        self.hotwords = hotwords

    def _transcribe_single(self, file_path: Path) -> str:
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

            with httpx.Client(timeout=300.0) as client:
                response = client.post(
                    self.endpoint_url,
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    logger.error(f"VibeVoice Error: {response.status_code} - {response.text}")
                    response.raise_for_status()

                result = response.json()

                if isinstance(result, dict):
                    if "result" in result:
                        return result["result"]
                    elif "text" in result:
                        return result["text"]
                
                logger.warning(f"Unexpected VibeVoice response structure: {result}")
                return str(result)

        except Exception as e:
            logger.error(f"VibeVoice transcription failed: {e}")
            raise RuntimeError(f"VibeVoice transcription failed: {e}") from e
