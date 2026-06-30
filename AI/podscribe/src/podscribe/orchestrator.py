import logging
import re
import threading
import traceback
from concurrent.futures import as_completed
from pathlib import Path
from typing import List

from podscribe.concurrency import LoggingThreadPoolExecutor as ThreadPoolExecutor
from podscribe.config import Config
from podscribe.post_processors import BasePostProcessor, GeminiPostProcessor, OpenAICompatiblePostProcessor
from podscribe.preprocessor import AudioPreprocessor
from podscribe.pricing import calculate_post_processing_cost, calculate_transcription_cost
from podscribe.rss_fetcher import RSSFetcher
from podscribe.state import StateManager
from podscribe.transcribers import (
    AssemblyAITranscriber,
    BaseTranscriber,
    CrispASRCLITranscriber,
    CrispASRTranscriber,
    HuggingFaceTranscriber,
    OpenAICompatibleTranscriber,
    SpeakerAttributedHuggingFaceTranscriber,
    SpeakerAttributedOpenAICompatibleTranscriber,
    VibeVoiceASRTranscriber,
)

logger = logging.getLogger(__name__)


def count_words_and_segments(transcript: str) -> tuple[int, int]:
    """Calculate the number of transcribed words and segments in a transcript.

    Excludes speaker labels (e.g. [Speaker 1]:) from the word count.
    """
    if not transcript.strip():
        return 0, 0

    # 1. Count segments (separated by double newlines)
    raw_segments = [s.strip() for s in transcript.split("\n\n") if s.strip()]
    num_segments = len(raw_segments)

    # 2. Count words
    # Remove speaker tags of the form "[Speaker Label]:" or "[Name]:"
    cleaned_transcript = re.sub(r'\[[^\]]+\]:', '', transcript)
    num_words = len(cleaned_transcript.split())

    return num_words, num_segments

class Orchestrator:
    """Coordinates the execution of the transcription and post-processing pipeline."""

    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}

    def __init__(self, config: Config, stage: str = "all"):
        """Initialize the pipeline orchestrator with configuration and target stage."""
        self.config = config
        if stage not in ("all", "transcribe", "postprocess"):
            raise ValueError(f"Invalid stage: {stage}. Must be 'all', 'transcribe', or 'postprocess'.")
        self.stage = stage

        # Resolve directories
        self.input_dir = Path(self.config.input_dir)
        self.output_dir = Path(self.config.output_dir)
        self.raw_transcripts_dir = self.output_dir / "raw_transcripts"
        self._lock = threading.Lock()
        self.transcribed_in_this_run: set[str] | None = None
        self.postprocessed_in_this_run: set[str] | None = None

        # Initialize state manager
        self.state_manager = StateManager(self.output_dir)

        # Initialize preprocessor
        self.preprocessor = AudioPreprocessor(
            enabled=self.config.preprocess_enabled,
            ffmpeg_path=self.config.ffmpeg_path,
            output_dir=self.output_dir,
            chunking_enabled=self.config.chunking_enabled,
            chunk_max_duration=self.config.chunk_max_duration,
            silence_threshold_db=self.config.silence_threshold_db,
            silence_duration=self.config.silence_duration
        )

        # Initialize clients
        self.transcriber = self._init_transcriber()
        self.post_processor = self._init_post_processor()

        # Load prompt template
        self.prompt_template = self._load_prompt_template()

    def _init_transcriber(self) -> BaseTranscriber:
        """Instantiate and configure the appropriate ASR transcriber provider based on config."""
        provider = self.config.transcriber_provider
        endpoint = self.config.transcriber_endpoint
        model = self.config.transcriber_model
        api_key = self.config.get_transcriber_api_key()
        language = self.config.language

        timeout = self.config.transcriber_timeout

        transcriber = None
        if provider == "huggingface":
            if self.config.enable_speaker_attribution:
                logger.info("Using speaker-attributed HuggingFace transcriber (assuming endpoint returns segments or chunks with speaker labels).")
                transcriber = SpeakerAttributedHuggingFaceTranscriber(endpoint_url=endpoint, api_key=api_key, model=model, language=language, timeout=timeout)
            else:
                transcriber = HuggingFaceTranscriber(endpoint_url=endpoint, api_key=api_key, model=model, language=language, timeout=timeout)
        elif provider == "openai_compatible":
            if self.config.enable_speaker_attribution:
                transcriber = SpeakerAttributedOpenAICompatibleTranscriber(endpoint_url=endpoint, api_key=api_key, model=model, language=language, timeout=timeout)
            else:
                transcriber = OpenAICompatibleTranscriber(endpoint_url=endpoint, api_key=api_key, model=model, language=language, timeout=timeout)
        elif provider == "crispasr":
            transcriber = CrispASRTranscriber(endpoint_url=endpoint, api_key=api_key, model=model, language=language, timeout=timeout)
        elif provider == "crispasr_cli":
            crispasr_path = self.config.transcriber_crispasr_path
            backend = self.config.transcriber_backend
            diarize_method = self.config.transcriber_diarize_method
            transcriber = CrispASRCLITranscriber(
                binary_path=crispasr_path,
                model=model or "auto",
                backend=backend,
                diarize_method=diarize_method
            )
        elif provider == "vibevoice":
            hotwords = self.config.hotwords
            transcriber = VibeVoiceASRTranscriber(
                endpoint_url=endpoint,
                api_key=api_key,
                model=model,
                language=language,
                hotwords=hotwords,
                timeout=timeout
            )
        elif provider == "assemblyai":
            transcriber = AssemblyAITranscriber(
                api_key=api_key,
                model=model,
                language=language,
                enable_speaker_attribution=self.config.enable_speaker_attribution,
                prompt_file=self.config.assemblyai_prompt_file,
                keyterms_file=self.config.assemblyai_keyterms_file,
            )
        else:
            raise ValueError(f"Unsupported transcriber provider: {provider}")

        try:
            transcriber.max_workers = int(getattr(self.config, "transcription_workers", 1))
        except (TypeError, ValueError):
            transcriber.max_workers = 1
        return transcriber

    def _init_post_processor(self) -> BasePostProcessor:
        """Instantiate and configure the appropriate LLM post-processor based on config."""
        provider = self.config.post_processor_provider
        model = self.config.post_processor_model
        endpoint = self.config.post_processor_endpoint
        api_key = self.config.get_post_processor_api_key()
        temp = self.config.post_processor_temperature

        if provider == "gemini":
            return GeminiPostProcessor(model=model, api_key=api_key, temperature=temp)
        elif provider == "openai_compatible":
            return OpenAICompatiblePostProcessor(endpoint_url=endpoint, api_key=api_key, model=model, temperature=temp)
        else:
            raise ValueError(f"Unsupported post-processor provider: {provider}")

    def _load_prompt_template(self) -> str:
        """Load the post-processing LLM instructions from the configured markdown prompt file."""
        prompt_path = Path(self.config.prompt_file)
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt template file not found: {prompt_path}")
        with open(prompt_path, "r") as f:
            return f.read()

    def find_files(self) -> List[Path]:
        """Scan input directory for supported files."""
        if not self.input_dir.exists():
            logger.warning(f"Input directory does not exist: {self.input_dir}")
            return []

        files = []
        for file_path in self.input_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                files.append(file_path)
        return files

    def check_dependencies(self):
        """Verify that system dependencies and required auth tokens are available."""
        import os
        for env_var, description in self.config.get_required_auth_env_vars(stage=self.stage):
            if not os.environ.get(env_var):
                raise RuntimeError(
                    f"Environment variable '{env_var}' ({description}) is not set."
                )

        if self.stage in ("all", "transcribe") and self.config.preprocess_enabled:
            if not self.preprocessor.is_ffmpeg_available():
                raise RuntimeError(
                    f"FFmpeg executable '{self.config.ffmpeg_path}' not found, but preprocessing is enabled. "
                    "Please install FFmpeg or set preprocess_enabled = false in config."
                )

    def _save_and_update_transcript_state(
        self,
        relative_path: str,
        raw_transcript: str,
        raw_transcript_path: Path,
        promote_status: bool = False,
    ) -> None:
        """Save a raw transcript to disk and update word/segment counts and status in state."""
        raw_transcript_path.parent.mkdir(parents=True, exist_ok=True)
        with open(raw_transcript_path, "w") as f:
            f.write(raw_transcript)
        num_words, num_segments = count_words_and_segments(raw_transcript)
        update_kwargs = {
            "raw_transcript_path": raw_transcript_path,
            "num_words": num_words,
            "num_segments": num_segments,
        }
        if promote_status:
            update_kwargs["status"] = "transcribed"
        self.state_manager.update_entry(relative_path, **update_kwargs)

    def _load_existing_transcript(
        self, relative_path: str, fallback_path: Path
    ) -> tuple[str, Path] | None:
        """Load an existing raw transcript from disk and promote state if present."""
        saved_path_str = self.state_manager.get_entry(relative_path).get("raw_transcript_path")
        raw_path = Path(saved_path_str) if saved_path_str else fallback_path
        if raw_path.exists():
            with open(raw_path, "r") as f:
                raw_transcript = f.read()
            num_words, num_segments = count_words_and_segments(raw_transcript)
            current_status = self.state_manager.get_entry(relative_path).get("status")
            update_kwargs = {
                "raw_transcript_path": raw_path,
                "num_words": num_words,
                "num_segments": num_segments,
            }
            if current_status in ("new", "preprocessed", "failed"):
                update_kwargs["status"] = "transcribed"
            self.state_manager.update_entry(relative_path, **update_kwargs)
            return raw_transcript, raw_path
        return None

    def _prepare_and_preprocess_file(self, file_path: Path) -> Path | None:
        """Calculate hash, check skip conditions, probe duration, and preprocess an audio file."""
        relative_path = file_path.name
        logger.info(f"--- Entering Stage: Preprocessing for {relative_path} ---")

        # 1. Calculate Hash
        file_hash = self.state_manager.get_file_hash(file_path)

        # Check if already processed for the target stage
        entry = self.state_manager.get_entry(relative_path)
        should_skip = False
        if entry.get("hash") == file_hash:
            status = entry.get("status")
            if self.stage == "all" and status == "completed":
                should_skip = True
            elif self.stage == "transcribe" and status in ("transcribed", "completed"):
                should_skip = True
            elif self.stage == "postprocess" and status == "completed":
                should_skip = True

        if should_skip:
            logger.info(f"Skipping {relative_path}: already processed for stage '{self.stage}' and unmodified.")
            return None

        # Retrieve or initialize state entry
        entry = self.state_manager.get_entry(relative_path)

        # If file has changed, reset state to start fresh
        if entry.get("hash") != file_hash:
            logger.info(f"File changed (or new). Resetting state for {relative_path}.")
            self.state_manager.update_entry(
                relative_path,
                hash=file_hash,
                status="new",
                preprocessed_path="",
                raw_transcript_path="",
                final_transcript_path="",
                error=""
            )
            entry = self.state_manager.get_entry(relative_path)

        # Get and store audio duration if needed
        if entry.get("status") not in ("transcribed", "completed") and self.stage != "postprocess":
            audio_duration = self.preprocessor.get_duration(file_path)
            self.state_manager.update_entry(relative_path, audio_duration=audio_duration)
        else:
            audio_duration = entry.get("audio_duration", 0.0)

        working_file = file_path

        # 2. Preprocess (if needed)
        if self.stage in ("all", "transcribe"):
            if entry.get("status") in ("new", "failed"):
                try:
                    working_file = self.preprocessor.preprocess(file_path, duration=audio_duration)
                    self.state_manager.update_entry(
                        relative_path,
                        status="preprocessed",
                        preprocessed_path=working_file
                    )
                except Exception as e:
                    self.state_manager.update_entry(relative_path, status="failed", error=f"Preprocessing: {str(e)}")
                    raise

            elif entry.get("preprocessed_path"):
                # Skip preprocessing, use previous result
                working_file = Path(entry["preprocessed_path"])
                is_missing = False
                if not working_file.exists():
                    is_missing = True
                elif working_file.is_dir():
                    # Ensure chunk directory is not empty
                    chunks = [f for f in working_file.iterdir() if f.is_file() and f.suffix.lower() == ".wav"]
                    if not chunks:
                        is_missing = True

                if is_missing:
                    logger.warning(f"Preprocessed file missing or empty chunk directory: {working_file}. Re-running.")
                    working_file = self.preprocessor.preprocess(file_path, duration=audio_duration)
                    self.state_manager.update_entry(relative_path, preprocessed_path=working_file)

        return working_file

    def _run_transcription_for_file(self, file_path: Path, working_file: Path) -> None:
        """Run or load transcription for a single prepared audio file."""
        relative_path = file_path.name
        raw_transcript_path = self.raw_transcripts_dir / f"{file_path.stem}_raw.txt"
        try:
            if self.stage == "postprocess":
                return

            logger.info(f"--- Entering Stage: Transcription for {relative_path} ---")
            if self.state_manager.get_entry(relative_path).get("status") == "preprocessed":
                logger.info(f"Transcriber: input={working_file.name}, output={raw_transcript_path.name}")
                raw_transcript = self.transcriber.transcribe(working_file)
                if self.transcribed_in_this_run is not None:
                    with self._lock:
                        self.transcribed_in_this_run.add(relative_path)
                self._save_and_update_transcript_state(
                    relative_path, raw_transcript, raw_transcript_path, promote_status=True
                )
            else:
                # Skip transcription, read saved file
                existing = self._load_existing_transcript(relative_path, raw_transcript_path)
                if not existing:
                    logger.warning(f"Raw transcript missing: {raw_transcript_path}. Re-running transcription.")
                    logger.info(f"Transcriber: input={working_file.name}, output={raw_transcript_path.name}")
                    raw_transcript = self.transcriber.transcribe(working_file)
                    if self.transcribed_in_this_run is not None:
                        with self._lock:
                            self.transcribed_in_this_run.add(relative_path)
                    self._save_and_update_transcript_state(
                        relative_path, raw_transcript, raw_transcript_path, promote_status=False
                    )
        except Exception as e:
            self.state_manager.update_entry(relative_path, status="failed", error=f"Transcription: {str(e)}")
            logger.error(f"Transcription failed for {relative_path}: {e}")
            logger.error(traceback.format_exc())

    def _run_postprocessing_for_file(self, file_path: Path) -> None:
        """Run post-processing for a single transcribed file."""
        relative_path = file_path.name
        raw_transcript_path = self.raw_transcripts_dir / f"{file_path.stem}_raw.txt"
        entry_status = self.state_manager.get_entry(relative_path).get("status")

        # If running full pipeline ("all"), only post-process if transcription succeeded
        if self.stage == "all" and entry_status != "transcribed":
            return

        try:
            existing = self._load_existing_transcript(relative_path, raw_transcript_path)
            if not existing:
                if self.stage == "postprocess":
                    raise FileNotFoundError(f"Raw transcript not found at {raw_transcript_path}. Cannot post-process without transcription.")
                return
            raw_transcript, _ = existing

            logger.info(f"--- Entering Stage: Post-processing for {relative_path} ---")
            entry_status = self.state_manager.get_entry(relative_path).get("status")
            if entry_status in ("transcribed", "failed"):
                final_transcript_path = self.output_dir / f"{file_path.stem}_final.md"
                logger.info(f"Post-processor: input={raw_transcript_path.name}, output={final_transcript_path.name}")
                context = {
                    "filename": file_path.name,
                    **self.config.prompt_context
                }
                final_transcript, token_usage = self.post_processor.post_process(
                    raw_transcript, self.prompt_template, context=context
                )

                # Save final transcript
                final_transcript_path = self.output_dir / f"{file_path.stem}_final.md"
                with open(final_transcript_path, "w") as f:
                    f.write(final_transcript)

                self.state_manager.update_entry(
                    relative_path,
                    status="completed",
                    final_transcript_path=final_transcript_path,
                    token_usage=token_usage.to_dict()
                )
                if self.postprocessed_in_this_run is not None:
                    with self._lock:
                        self.postprocessed_in_this_run.add(relative_path)
                logger.info(f"Successfully completed pipeline for {relative_path}")
            elif entry_status == "completed":
                logger.info(f"Post-processing already completed for {relative_path}")
        except Exception as e:
            err_prefix = "Post-processing setup" if self.stage == "postprocess" and isinstance(e, FileNotFoundError) else "Post-processing"
            self.state_manager.update_entry(relative_path, status="failed", error=f"{err_prefix}: {str(e)}")
            logger.error(f"{err_prefix} failed for {relative_path}: {e}")
            logger.error(traceback.format_exc())

    def run(self):
        """Execute the pipeline on all discovered files."""
        self.transcribed_in_this_run = set()
        self.postprocessed_in_this_run = set()
        self.check_dependencies()
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_transcripts_dir.mkdir(parents=True, exist_ok=True)

        # Download any new podcast episodes from configured RSS feeds
        feeds = self.config.rss_feeds
        if feeds:
            fetcher = RSSFetcher(self.input_dir)
            downloaded = fetcher.sync_feeds(feeds)
            if downloaded:
                logger.info(f"Downloaded {len(downloaded)} new episode(s) from RSS feeds.")

        files = self.find_files()
        if not files:
            logger.info(f"No supported audio files found in {self.input_dir}")
            return

        logger.info(f"Found {len(files)} files to process.")

        # Phase 1: Prepare and Preprocess all files
        prepared_items: list[tuple[Path, Path]] = []
        for file_path in files:
            relative_path = file_path.name
            logger.info(f"--- Preparing: {relative_path} ---")
            try:
                working_file = self._prepare_and_preprocess_file(file_path)
                if working_file is not None:
                    prepared_items.append((file_path, working_file))
            except Exception as e:
                logger.error(f"Error preparing {relative_path}: {e}")
                logger.error(traceback.format_exc())
                continue

        # Phase 2 & Phase 3: Transcribe and Post-process (pipelined concurrently when stage == 'all')
        try:
            t_workers = int(getattr(self.config, "transcription_workers", 1))
        except (TypeError, ValueError):
            t_workers = 1

        try:
            p_workers = int(getattr(self.config, "postprocessing_workers", 1))
        except (TypeError, ValueError):
            p_workers = 1

        if self.stage == "transcribe" and prepared_items:
            if t_workers > 1 and len(prepared_items) > 1:
                logger.info(f"Transcribing {len(prepared_items)} files concurrently with ThreadPoolExecutor (workers={t_workers})")
                with ThreadPoolExecutor(max_workers=t_workers, thread_name_prefix="transcribe") as executor:
                    list(executor.map(lambda item: self._run_transcription_for_file(item[0], item[1]), prepared_items))
            else:
                for file_path, working_file in prepared_items:
                    self._run_transcription_for_file(file_path, working_file)
            logger.info("All files have been transcribed.")

        elif self.stage == "postprocess" and prepared_items:
            if p_workers > 1 and len(prepared_items) > 1:
                logger.info(f"Post-processing {len(prepared_items)} files concurrently with ThreadPoolExecutor (workers={p_workers})")
                with ThreadPoolExecutor(max_workers=p_workers, thread_name_prefix="postprocess") as executor:
                    list(executor.map(lambda item: self._run_postprocessing_for_file(item[0]), prepared_items))
            else:
                for file_path, _ in prepared_items:
                    self._run_postprocessing_for_file(file_path)

        elif self.stage == "all" and prepared_items:
            if t_workers <= 1 and p_workers <= 1 and len(prepared_items) <= 1:
                for file_path, working_file in prepared_items:
                    self._run_transcription_for_file(file_path, working_file)
                logger.info("All files have been transcribed.")
                for file_path, _ in prepared_items:
                    self._run_postprocessing_for_file(file_path)
            else:
                logger.info(
                    f"Running pipelined execution with concurrent ThreadPoolExecutors "
                    f"(transcription_workers={t_workers}, postprocessing_workers={p_workers})"
                )
                with ThreadPoolExecutor(max_workers=t_workers, thread_name_prefix="transcribe") as t_executor, \
                     ThreadPoolExecutor(max_workers=p_workers, thread_name_prefix="postprocess") as p_executor:

                    postprocess_futures = []

                    def transcribe_and_dispatch(fp: Path, wf: Path):
                        self._run_transcription_for_file(fp, wf)
                        # Immediately submit to post-processing pool as soon as transcription finishes
                        return p_executor.submit(self._run_postprocessing_for_file, fp)

                    transcribe_futures = [
                        t_executor.submit(transcribe_and_dispatch, fp, wf)
                        for fp, wf in prepared_items
                    ]

                    for t_future in as_completed(transcribe_futures):
                        try:
                            p_future = t_future.result()
                            if p_future is not None:
                                postprocess_futures.append(p_future)
                        except Exception as e:
                            logger.error(f"Error in pipelined task dispatch: {e}")

                    logger.info("All files have been transcribed.")

                    for p_future in as_completed(postprocess_futures):
                        try:
                            p_future.result()
                        except Exception as e:
                            logger.error(f"Error in pipelined postprocessing: {e}")

        # 5. Print Summary Report
        if files:
            self.print_summary_report(files)

    def print_summary_report(self, files: List[Path]):
        total_files = len(files)
        completed_files = 0
        transcribed_files = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        total_post_processing_cost = 0.0
        total_transcription_duration = 0.0
        total_transcription_cost = 0.0
        total_words = 0
        total_segments = 0

        for file_path in files:
            entry = self.state_manager.get_entry(file_path.name)
            status = entry.get("status")

            # Transcription Stats (applicable if status is transcribed or completed and transcribed in this run)
            is_transcribed = status in ("transcribed", "completed")
            if self.transcribed_in_this_run is not None:
                is_transcribed = file_path.name in self.transcribed_in_this_run

            if is_transcribed:
                transcribed_files += 1
                duration = entry.get("audio_duration", 0.0)
                total_transcription_duration += duration

                provider = self.config.transcriber_provider
                endpoint = self.config.transcriber_endpoint
                enable_speaker_attribution = getattr(self.config, "enable_speaker_attribution", False)
                has_prompt = False
                has_keyterms = False
                if provider == "assemblyai":
                    prompt_file = getattr(self.config, "assemblyai_prompt_file", None)
                    if prompt_file and prompt_file.exists() and prompt_file.is_file():
                        try:
                            if prompt_file.read_text(encoding="utf-8").strip():
                                has_prompt = True
                        except Exception:
                            pass
                    keyterms_file = getattr(self.config, "assemblyai_keyterms_file", None)
                    if keyterms_file and keyterms_file.exists() and keyterms_file.is_file():
                        try:
                            keyterms = [line.strip() for line in keyterms_file.read_text(encoding="utf-8").splitlines() if line.strip()]
                            if keyterms:
                                has_keyterms = True
                        except Exception:
                            pass

                t_cost = calculate_transcription_cost(
                    provider,
                    duration,
                    endpoint,
                    enable_speaker_attribution=enable_speaker_attribution,
                    has_prompt=has_prompt,
                    has_keyterms=has_keyterms,
                )
                total_transcription_cost += t_cost

                # Extract words and segments with fallback
                num_words = entry.get("num_words")
                num_segments = entry.get("num_segments")
                if num_words is None or num_segments is None:
                    raw_path_str = entry.get("raw_transcript_path")
                    if raw_path_str and Path(raw_path_str).exists():
                        try:
                            with open(Path(raw_path_str), "r") as f:
                                raw_transcript = f.read()
                            num_words, num_segments = count_words_and_segments(raw_transcript)
                            self.state_manager.update_entry(
                                file_path.name,
                                num_words=num_words,
                                num_segments=num_segments
                            )
                        except Exception:
                            num_words, num_segments = 0, 0
                    else:
                        num_words, num_segments = 0, 0
                total_words += num_words
                total_segments += num_segments

            # LLM Stats (applicable if status is completed and postprocessed in this run)
            is_completed = status == "completed"
            if self.postprocessed_in_this_run is not None:
                is_completed = file_path.name in self.postprocessed_in_this_run

            if is_completed:
                completed_files += 1

                usage_dict = entry.get("token_usage", {})
                prompt = usage_dict.get("prompt_tokens", 0)
                completion = usage_dict.get("completion_tokens", 0)
                total = usage_dict.get("total_tokens", 0)

                total_prompt_tokens += prompt
                total_completion_tokens += completion
                total_tokens += total

                model = self.config.post_processor_model
                provider = self.config.post_processor_provider
                endpoint = self.config.post_processor_endpoint
                cost = calculate_post_processing_cost(
                    model,
                    prompt,
                    completion,
                    provider=provider,
                    endpoint_url=endpoint
                )
                total_post_processing_cost += cost

        total_cost = total_post_processing_cost + total_transcription_cost

        # Convert duration to readable format (HH:MM:SS)
        hrs = int(total_transcription_duration // 3600)
        mins = int((total_transcription_duration % 3600) // 60)
        secs = int(total_transcription_duration % 60)
        duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

        logger.info("==================================================")
        logger.info("                PODSCRIBE REPORT                  ")
        logger.info("==================================================")
        logger.info(f"Total Files Found: {total_files}")
        logger.info(f"Transcribed Files: {transcribed_files}")
        logger.info(f"Completed Files:   {completed_files}")
        logger.info(f"Audio Transcribed: {duration_str} ({total_transcription_duration:.2f}s)")
        logger.info(f"Transcribed Words: {total_words:,}")
        logger.info(f"Segments:          {total_segments:,}")
        logger.info(f"Total LLM Tokens:  {total_tokens:,} (Prompt: {total_prompt_tokens:,}, Completion: {total_completion_tokens:,})")
        logger.info("--------------------------------------------------")
        logger.info(f"ASR Cost ({self.config.transcriber_provider}):".ljust(30) + f"${total_transcription_cost:.4f}")
        logger.info(f"LLM Cost ({self.config.post_processor_model}):".ljust(30) + f"${total_post_processing_cost:.4f}")
        logger.info("Total Estimated Cost:".ljust(30) + f"${total_cost:.4f}")
        logger.info("==================================================")
