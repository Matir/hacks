import logging
from pathlib import Path
import traceback
from typing import List

from src.config import Config
from src.state import StateManager
from src.preprocessor import AudioPreprocessor
from src.transcribers import HuggingFaceTranscriber, OpenAICompatibleTranscriber, BaseTranscriber
from src.post_processors import GeminiPostProcessor, OpenAICompatiblePostProcessor, BasePostProcessor

logger = logging.getLogger(__name__)

class Orchestrator:
    SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".webm", ".mp4"}

    def __init__(self, config: Config):
        self.config = config
        
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
            output_dir=self.output_dir
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
            return HuggingFaceTranscriber(endpoint_url=endpoint, api_key=api_key, model=model)
        elif provider == "openai_compatible":
            return OpenAICompatibleTranscriber(endpoint_url=endpoint, api_key=api_key, model=model)
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

    def run(self):
        """Execute the pipeline on all discovered files."""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_transcripts_dir.mkdir(parents=True, exist_ok=True)

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
                
                # Check if fully processed
                if self.state_manager.is_completed(relative_path, file_hash):
                    logger.info(f"Skipping {relative_path}: already completed and unmodified.")
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

                working_file = file_path

                # 2. Preprocess (if needed)
                if entry.get("status") in ("new", "failed"):
                    try:
                        working_file = self.preprocessor.preprocess(file_path)
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
                    if not working_file.exists():
                        logger.warning(f"Preprocessed file missing: {working_file}. Re-running.")
                        working_file = self.preprocessor.preprocess(file_path)
                        self.state_manager.update_entry(relative_path, preprocessed_path=working_file)

                # 3. Transcribe (if needed)
                raw_transcript = ""
                raw_transcript_path = self.raw_transcripts_dir / f"{file_path.stem}_raw.txt"

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
                            # We need to set state back to preprocessed and raise an error to loop back or just run it here.
                            # Simplest: raise error, user runs again, we recover. Or we handle it by re-transcribing:
                            raw_transcript = self.transcriber.transcribe(working_file)
                            with open(raw_transcript_path, "w") as f:
                                f.write(raw_transcript)
                            self.state_manager.update_entry(relative_path, raw_transcript_path=raw_transcript_path)

                # 4. Post-process (if needed)
                if self.state_manager.get_entry(relative_path).get("status") == "transcribed":
                    try:
                        final_transcript = self.post_processor.post_process(raw_transcript, self.prompt_template)
                        
                        # Save final transcript
                        final_transcript_path = self.output_dir / f"{file_path.stem}_final.md"
                        with open(final_transcript_path, "w") as f:
                            f.write(final_transcript)

                        self.state_manager.update_entry(
                            relative_path,
                            status="completed",
                            final_transcript_path=final_transcript_path
                        )
                        logger.info(f"Successfully completed pipeline for {relative_path}")
                    except Exception as e:
                        self.state_manager.update_entry(relative_path, status="failed", error=f"Post-processing: {str(e)}")
                        raise

            except Exception as e:
                logger.error(f"Error processing {relative_path}: {e}")
                logger.error(traceback.format_exc())
                # Continue to the next file even if one fails
                continue
