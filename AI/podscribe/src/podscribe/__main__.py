import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from podscribe.config import Config
from podscribe.orchestrator import Orchestrator
from podscribe.rss_fetcher import RSSFetcher

# Environment variables loaded via python-dotenv

def setup_logging(output_dir: Path, log_level_str: str = "INFO"):
    """Configure logging to output to both stdout and a file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "pipeline.log"

    # Parse log level
    numeric_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Define format including thread name and thread ID for concurrency tracking
    log_format = "%(asctime)s [%(levelname)s] [%(threadName)s:%(thread)d] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

def main():
    """Parse CLI arguments, verify authentication environment variables, and run the transcription orchestrator."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Audio Transcription & Post-Processing Pipeline")
    parser.add_argument(
        "-c", "--config",
        default="config.toml",
        help="Path to the TOML configuration file (default: config.toml)"
    )
    parser.add_argument(
        "--stage",
        choices=["all", "transcribe", "postprocess"],
        default="all",
        help="Specify which stage of the pipeline to run: 'transcribe' (preprocessing + transcription), 'postprocess' (only LLM cleaning/formatting), or 'all' (default)"
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Specify the language for transcription (e.g. 'en', 'es'). Defaults to config file value or 'en'."
    )
    parser.add_argument(
        "--log-level",
        type=str.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    parser.add_argument(
        "--dump-config",
        action="store_true",
        help="Dump the resolved configuration and exit"
    )
    parser.add_argument(
        "--rss-download-only",
        action="store_true",
        help="Only download source material from configured RSS feeds and exit"
    )
    args = parser.parse_args()

    # 1. Load .env if present (contains keys like HF_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY)
    load_dotenv()

    # 2. Load Config
    try:
        config = Config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Please ensure '{args.config}' exists.")
        sys.exit(1)

    if args.language is not None:
        if "transcriber" not in config.data:
            config.data["transcriber"] = {}
        config.data["transcriber"]["language"] = args.language

    # Handle configuration dumping
    if args.dump_config:
        print(config.dump())
        sys.exit(0)

    # 3. Setup Logging (requires output directory from config)
    setup_logging(Path(config.output_dir), log_level_str=args.log_level)

    if args.rss_download_only:
        if not config.rss_feeds:
            logging.error("No RSS feeds configured in %s", args.config)
            print("Error: No RSS feeds configured.", file=sys.stderr)
            sys.exit(1)

        logging.info("Running in RSS download-only mode.")
        fetcher = RSSFetcher(Path(config.input_dir))
        try:
            downloaded = fetcher.sync_feeds(config.rss_feeds, raise_on_error=True)
            logging.info(f"RSS download completed successfully. Downloaded {len(downloaded)} file(s).")
            sys.exit(0)
        except Exception as e:
            logging.error(f"RSS download failed: {e}")
            print(f"Error: RSS download failed: {e}", file=sys.stderr)
            sys.exit(1)

    logging.info("Starting Audio Transcription & Post-Processing Pipeline")

    # Check if required environment variables for authentication are set before beginning work
    missing_env_vars = []
    for env_var, description in config.get_required_auth_env_vars(stage=args.stage):
        if not os.environ.get(env_var):
            missing_env_vars.append((env_var, description))

    if missing_env_vars:
        for env_var, description in missing_env_vars:
            msg = f"Error: Environment variable '{env_var}' ({description}) is not set."
            logging.error(msg)
            print(msg, file=sys.stderr)
        sys.exit(1)

    # 4. Run Orchestrator
    try:
        orchestrator = Orchestrator(config, stage=args.stage)
        orchestrator.run()
    except Exception as e:
        logging.critical(f"Pipeline failed with an unhandled error: {e}")
        sys.exit(1)

    logging.info("Pipeline finished execution.")

if __name__ == "__main__":
    main()
