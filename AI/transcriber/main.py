import argparse
import logging
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

from src.config import Config
from src.orchestrator import Orchestrator

# Environment variables loaded via python-dotenv

def setup_logging(output_dir: Path):
    """Configure logging to output to both stdout and a file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = output_dir / "pipeline.log"

    # Define format
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Audio Transcription & Post-Processing Pipeline")
    parser.add_argument(
        "-c", "--config",
        default="config.toml",
        help="Path to the TOML configuration file (default: config.toml)"
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

    # 3. Setup Logging (requires output directory from config)
    setup_logging(Path(config.output_dir))

    logging.info("Starting Audio Transcription & Post-Processing Pipeline")
    
    # 4. Run Orchestrator
    try:
        orchestrator = Orchestrator(config)
        orchestrator.run()
    except Exception as e:
        logging.critical(f"Pipeline failed with an unhandled error: {e}")
        sys.exit(1)

    logging.info("Pipeline finished execution.")

if __name__ == "__main__":
    main()
