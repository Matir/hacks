import logging
from pathlib import Path
import traceback
from typing import List

from podscribe.config import Config
from podscribe.state import StateManager
from podscribe.preprocessor import AudioPreprocessor
from podscribe.transcribers import HuggingFaceTranscriber, SpeakerAttributedHuggingFaceTranscriber, OpenAICompatibleTranscriber, SpeakerAttributedOpenAICompatibleTranscriber, CrispASRTranscriber, BaseTranscriber
from podscribe.post_processors import GeminiPostProcessor, OpenAICompatiblePostProcessor, BasePostProcessor, TokenUsage
from podscribe.pricing import calculate_post_processing_cost, calculate_transcription_cost
from podscribe.rss_fetcher import RSSFetcher

logger = logging.getLogger(__name__)

class Orchestrator:
    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}

    def __init__(self, config: Config, stage: str = "all"):
        self.config = config
        if stage not in ("all", "transcribe", "postprocess"):
            raise ValueError(f"Invalid stage: {stage}. Must be 'all', 'transcribe', or 'postprocess'.")
        self.stage = stage

        # Resolve directories
        self.input_dir = Path(self.config.input_dir)
        self.output_dir = Path(self.config.output_dir)
        self.raw_transcripts_dir = self.output_dir / "raw_transcripts"

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
        provider = self.config.transcriber_provider
        endpoint = self.config.transcriber_endpoint
        model = self.config.transcriber_model
        api_key = self.config.get_transcriber_api_key()

        if provider == "huggingface":
            if self.config.enable_speaker_attribution:
                logger.info("Using speaker-attributed HuggingFace transcriber (assuming endpoint returns segments or chunks with speaker labels).")
                return SpeakerAttributedHuggingFaceTranscriber(endpoint_url=endpoint, api_key=api_key, model=model)
            return HuggingFaceTranscriber(endpoint_url=endpoint, api_key=api_key, model=model)
        elif provider == "openai_compatible":
            if self.config.enable_speaker_attribution:
                return SpeakerAttributedOpenAICompatibleTranscriber(endpoint_url=endpoint, api_key=api_key, model=model)
            return OpenAICompatibleTranscriber(endpoint_url=endpoint, api_key=api_key, model=model)
        elif provider == "crispasr":
            return CrispASRTranscriber(endpoint_url=endpoint, api_key=api_key, model=model)
        else:
            raise ValueError(f"Unsupported transcriber provider: {provider}")

    def _init_post_processor(self) -> BasePostProcessor:
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
        """Verify that system dependencies are available if they will be needed."""
        if self.stage in ("all", "transcribe") and self.config.preprocess_enabled:
            if not self.preprocessor.is_ffmpeg_available():
                raise RuntimeError(
                    f"FFmpeg executable '{self.config.ffmpeg_path}' not found, but preprocessing is enabled. "
                    "Please install FFmpeg or set preprocess_enabled = false in config."
                )

    def run(self):
        """Execute the pipeline on all discovered files."""
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

        for file_path in files:
            relative_path = file_path.name
            logger.info(f"--- Processing: {relative_path} ---")

            try:
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
                    continue

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

                # Get and store audio duration
                audio_duration = self.preprocessor.get_duration(file_path)
                self.state_manager.update_entry(relative_path, audio_duration=audio_duration)

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


                # 3. Transcribe (if needed)
                raw_transcript = ""
                raw_transcript_path = self.raw_transcripts_dir / f"{file_path.stem}_raw.txt"

                if self.stage in ("all", "transcribe"):
                    if self.state_manager.get_entry(relative_path).get("status") == "preprocessed":
                        try:
                            raw_transcript = self.transcriber.transcribe(working_file)

                            # Save intermediate transcript
                            with open(raw_transcript_path, "w") as f:
                                f.write(raw_transcript)

                            self.state_manager.update_entry(
                                relative_path,
                                status="transcribed",
                                raw_transcript_path=raw_transcript_path
                            )
                        except Exception as e:
                            self.state_manager.update_entry(relative_path, status="failed", error=f"Transcription: {str(e)}")
                            raise
                    else:
                        # Skip transcription, read saved file
                        saved_path_str = self.state_manager.get_entry(relative_path).get("raw_transcript_path")
                        if saved_path_str:
                            raw_transcript_path = Path(saved_path_str)
                        if raw_transcript_path.exists():
                            with open(raw_transcript_path, "r") as f:
                                raw_transcript = f.read()
                        else:
                            logger.warning(f"Raw transcript missing: {raw_transcript_path}. Re-running transcription.")
                            raw_transcript = self.transcriber.transcribe(working_file)
                            with open(raw_transcript_path, "w") as f:
                                f.write(raw_transcript)
                            self.state_manager.update_entry(relative_path, raw_transcript_path=raw_transcript_path)
                else:
                    # self.stage == "postprocess"
                    # Load the raw transcript. Do not run transcriber.
                    try:
                        saved_path_str = self.state_manager.get_entry(relative_path).get("raw_transcript_path")
                        if saved_path_str:
                            raw_transcript_path = Path(saved_path_str)
                        if raw_transcript_path.exists():
                            with open(raw_transcript_path, "r") as f:
                                raw_transcript = f.read()

                            # If status was new or preprocessed, promote to transcribed since we verified the raw transcript exists
                            current_status = self.state_manager.get_entry(relative_path).get("status")
                            if current_status in ("new", "preprocessed"):
                                self.state_manager.update_entry(
                                    relative_path,
                                    status="transcribed",
                                    raw_transcript_path=raw_transcript_path
                                )
                        else:
                            raise FileNotFoundError(f"Raw transcript not found at {raw_transcript_path}. Cannot post-process without transcription.")
                    except Exception as e:
                        self.state_manager.update_entry(relative_path, status="failed", error=f"Post-processing setup: {str(e)}")
                        raise

                # 4. Post-process (if needed)
                if self.stage in ("all", "postprocess"):
                    if self.state_manager.get_entry(relative_path).get("status") == "transcribed":
                        try:
                            final_transcript, token_usage = self.post_processor.post_process(raw_transcript, self.prompt_template)

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
                            logger.info(f"Successfully completed pipeline for {relative_path}")
                        except Exception as e:
                            self.state_manager.update_entry(relative_path, status="failed", error=f"Post-processing: {str(e)}")
                            raise
                else:
                    if self.state_manager.get_entry(relative_path).get("status") == "transcribed":
                        logger.info(f"Successfully completed transcription stage for {relative_path}")

            except Exception as e:
                logger.error(f"Error processing {relative_path}: {e}")
                logger.error(traceback.format_exc())
                # Continue to the next file even if one fails
                continue

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

        for file_path in files:
            entry = self.state_manager.get_entry(file_path.name)
            status = entry.get("status")

            # Transcription Stats (applicable if status is transcribed or completed)
            if status in ("transcribed", "completed"):
                transcribed_files += 1
                duration = entry.get("audio_duration", 0.0)
                total_transcription_duration += duration

                provider = self.config.transcriber_provider
                endpoint = self.config.transcriber_endpoint
                t_cost = calculate_transcription_cost(provider, duration, endpoint)
                total_transcription_cost += t_cost

            # LLM Stats (applicable if status is completed)
            if status == "completed":
                completed_files += 1

                usage_dict = entry.get("token_usage", {})
                prompt = usage_dict.get("prompt_tokens", 0)
                completion = usage_dict.get("completion_tokens", 0)
                total = usage_dict.get("total_tokens", 0)

                total_prompt_tokens += prompt
                total_completion_tokens += completion
                total_tokens += total

                model = self.config.post_processor_model
                cost = calculate_post_processing_cost(model, prompt, completion)
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
        logger.info(f"Total LLM Tokens:  {total_tokens:,} (Prompt: {total_prompt_tokens:,}, Completion: {total_completion_tokens:,})")
        logger.info("--------------------------------------------------")
        logger.info(f"ASR Cost ({self.config.transcriber_provider}):".ljust(30) + f"${total_transcription_cost:.4f}")
        logger.info(f"LLM Cost ({self.config.post_processor_model}):".ljust(30) + f"${total_post_processing_cost:.4f}")
        logger.info(f"Total Estimated Cost:".ljust(30) + f"${total_cost:.4f}")
        logger.info("==================================================")
