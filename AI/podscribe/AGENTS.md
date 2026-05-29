# Logical Agents in the Transcription Pipeline

This document defines the logical "Agents" that make up the transcription and post-processing pipeline. Although implemented as Python modules, structuring them as agents helps define clear boundaries, responsibilities, and interfaces.

---

## 1. Orchestrator Agent (The Pipeline Coordinator)

*   **Role:** Coordinates the execution of the pipeline from end to end.
*   **Responsibilities:**
    *   Loads configuration (`config.toml`).
    *   Manages system state (`state.json`) to ensure durability and support resumes.
    *   Scans the input directory for new files.
    *   Sequentially invokes the Preprocessor, Transcription, and Editor agents for each file.
    *   Saves final outputs and updates the state.
*   **Tools:**
    *   `StateManager`: For reading/writing `state.json`.
    *   `os`/`pathlib`: For file system traversal.

---

## 2. Preprocessor Agent (The Audio Engineer)

*   **Role:** Ensures audio files are optimized for the ASR model.
*   **Responsibilities:**
    *   Detects input file formats.
    *   Uses `ffmpeg` to convert inputs to the standard format required by Granite Speech (**16kHz, mono, WAV**).
    *   Reduces file size before upload, saving bandwidth and costs.
*   **Tools:**
    *   `ffmpeg` CLI (via Python `subprocess`).

---

## 3. Transcription Agent (The ASR Specialist)

*   **Role:** Converts audio tracks into speaker-attributed text.
*   **Responsibilities:**
    *   Communicates with the configured ASR endpoint (Hugging Face, Baseten, etc.).
    *   Handles API authentication and payload transmission.
    *   Extracts the raw text output, preserving the native speaker tags (e.g., `[Speaker 1]`).
    *   Supports speaker diarization/attribution mode based on user configuration, automatically invoking segment-level transcription APIs and reconstructing dialogues tagged with speaker IDs.
*   **Tools:**
    *   `httpx` / `requests`: For API communication.
    *   Swappable API Client Backends (`HuggingFaceTranscriber`, `OpenAICompatibleTranscriber`, `SpeakerAttributedOpenAICompatibleTranscriber`).

---

## 4. Editor Agent (The Post-Processor)

*   **Role:** Transforms raw, messy transcripts into polished, readable documents.
*   **Responsibilities:**
    *   Loads the post-processing instructions from a markdown template.
    *   Constructs the prompt containing the raw transcript.
    *   Invokes a Text LLM (Gemini or OpenAI) to:
        *   Clean up filler words (um, uh, like).
        *   Format into logical paragraphs.
        *   Correct technical terms or names using contextual clues.
        *   Format output in Markdown.
*   **Tools:**
    *   `google-genai` SDK (for Gemini).
    *   `openai` SDK (for OpenAI-compatible models).
    *   `prompts/post_process.md`: The custom instruction set.
