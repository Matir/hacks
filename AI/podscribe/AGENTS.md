# Logical Agents in the Transcription Pipeline

This document defines the logical "Agents" that make up the transcription and post-processing pipeline. Although implemented as Python modules, structuring them as agents helps define clear boundaries, responsibilities, and interfaces.

---

## 1. Orchestrator Agent (The Pipeline Coordinator)

*   **Role:** Coordinates the execution of the pipeline from end to end.
*   **Responsibilities:**
    *   Loads configuration (`config.toml`) and performs fail-fast verification on required API authentication environment variables before starting.
    *   Manages system state (`state.json`) with thread-safe locking (`RLock`) to ensure durability and support resumes.
    *   Scans the input directory for new audio files or downloads them via RSS feed synchronization.
    *   Manages pipelined parallel execution using multi-worker thread pools (`LoggingThreadPoolExecutor`), running post-processing concurrently as soon as each file completes transcription while monitoring queue backlog depths.
    *   Saves final outputs and prints detailed accounting reports isolating exact current-run audio duration and cost metrics.
*   **Tools:**
    *   `StateManager`: For reading/writing `state.json`.
    *   `LoggingThreadPoolExecutor`: For concurrent execution and queue monitoring.
    *   `os`/`pathlib`: For file system traversal.

---

## 2. Preprocessor Agent (The Audio Engineer)

*   **Role:** Ensures audio files are optimized for the ASR model.
*   **Responsibilities:**
    *   Detects input file formats and probes audio duration.
    *   Uses `ffmpeg` to convert inputs to the standard format required by ASR models (**16kHz, mono, WAV**).
    *   Supports optional silence-based audio chunking (`chunking_enabled`, `silence_threshold_db`) to partition long audio recordings into smaller files for restrictive API endpoints.
    *   Reduces file size before upload, saving bandwidth and costs.
*   **Tools:**
    *   `ffmpeg` CLI (via Python `subprocess`).

---

## 3. Transcription Agent (The ASR Specialist)

*   **Role:** Converts audio tracks into speaker-attributed text.
*   **Responsibilities:**
    *   Communicates with the configured ASR endpoint (Hugging Face, AssemblyAI, CrispASR, OpenAI, etc.).
    *   Handles API authentication and payload transmission.
    *   Extracts the raw text output, preserving native speaker tags (e.g., `[Speaker 1]`).
    *   Supports speaker diarization/attribution mode, custom prompt contexts, and keyterm prompting (e.g. AssemblyAI vocabulary boosting).
    *   Processes chunked audio files concurrently across worker threads and concatenates results seamlessly.
*   **Tools:**
    *   `httpx` / `requests` / official provider SDKs: For API communication.
    *   Swappable API Client Backends (`HuggingFaceTranscriber`, `OpenAICompatibleTranscriber`, `SpeakerAttributedOpenAICompatibleTranscriber`, `CrispASRTranscriber`, `AssemblyAITranscriber`).

---

## 4. Editor Agent (The Post-Processor)

*   **Role:** Transforms raw, messy transcripts into polished, readable documents.
*   **Responsibilities:**
    *   Loads the post-processing instructions from a markdown template inside the configured `prompts_dir`.
    *   Constructs the prompt containing the raw transcript and filename context.
    *   Invokes a Text LLM (Gemini or OpenAI-compatible routers) to clean up filler words, format logical paragraphs, and output Markdown.
*   **Tools:**
    *   `google-genai` SDK (for Gemini).
    *   `openai` SDK (for OpenAI-compatible models).
    *   `prompts/post_process.md`: The custom instruction set.

---

## Running Tests & Checks

To verify your changes, run code linting and unit tests. Due to virtual environment path settings and import discovery, future agents should follow these instructions:

1. **PYTHONPATH**: Ensure the `src` directory is included in your `PYTHONPATH` so Python can resolve the `podscribe` package.
2. **Virtual Environment Python Module**: Run `ruff` and `pytest` using the interpreter within the local `.venv` directory to avoid path issues.

Use the following command from the project root directory:
```bash
./.venv/bin/ruff check src/ tests/ && PYTHONPATH=src ./.venv/bin/python -m pytest
```

