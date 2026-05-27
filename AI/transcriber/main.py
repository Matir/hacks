import logging
import os
from pathlib import Path
import sys

from src.config import Config
from src.orchestrator import Orchestrator

def load_dotenv(dotenv_path: str = ".env"):
    """Simple, zero-dependency .env file loader."""
    path = Path(dotenv_path)
    if path.exists():
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ[key] = val
        print("Loaded environment variables from .env")

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
    # 1. Load .env if present (contains keys like HF_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY)
    load_dotenv()

    # 2. Load Config
    try:
        config = Config("config.toml")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure 'config.toml' exists in the current directory.")
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
