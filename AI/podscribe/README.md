# Audio Transcription & Post-Processing Pipeline

A modular, robust, and stateful Python command-line pipeline to ingest audio/video files, transcribe them using highly efficient ASR models (like IBM Granite Speech 4.1 with native speaker attribution), and format/clean them using text LLMs (Gemini, OpenRouter, OpenAI).

## Features

-   **Modular Architecture:** Swappable components for ASR transcription hosts and text LLM providers.
-   **Native Speaker Attribution & AssemblyAI Support:** Pre-optimized to leverage the **IBM Granite Speech 4.1 2B Plus** model for producing speaker-tagged text directly without PyAnnote alignment. Also supports **CrispASR** and **AssemblyAI** (supporting speaker diarization, custom vocabulary keyterms, and prompting).
-   **Pipelined Concurrency:** Employs multi-worker ThreadPool execution with queue depth monitoring to run post-processing concurrently as soon as each file completes transcription.
-   **Local Audio Preprocessing & Chunking:** Integrated system `ffmpeg` utility automatically extracts audio tracks from video, downsamples media to optimal **16kHz mono WAV** files prior to upload, and can split long recordings on silence boundaries (`chunking_enabled`).
-   **RSS / Podcast Feed Sync:** Automatically downloads new podcast episodes from any number of configured RSS feeds before processing begins. Episodes already present in the input directory are skipped, so re-running is always safe.
-   **Resilient State Management:** Uses a `state.json` registry with thread-safe locking to track processing status (`preprocessed`, `transcribed`, `completed`) and file MD5 hashes. Runs can be interrupted and safely resumed without repeating expensive transcription calls or duplicating work.
-   **OpenRouter & Gemini Out-of-the-Box:** Pre-configured support for OpenAI-compatible LLM routers (like OpenRouter) and direct Gemini SDK connections.
-   **UV Environment Management:** Pre-configured using `uv` for fast package isolation and auto-managed CPython toolchains.

---

## Prerequisites

1.  **Python:** Managed automatically by `uv` (targets Python `3.14.x` inside the virtual environment).
2.  **FFmpeg:** Must be installed on your local system and accessible in your system's PATH (required if preprocessing is enabled in `config.toml`).
    *   **Linux:** `sudo apt install ffmpeg`
    *   **macOS:** `brew install ffmpeg`

---

## Getting Started

### 1. Environment Setup
Ensure you have `uv` installed. If not, install it via:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Clone/navigate to your directory and sync the virtual environment:
```bash
uv sync
```

### 2. Configuration

#### Copy the Environment File
Create a local `.env` file to store your API keys safely:
```bash
cp .env.example .env
```
Open `.env` and insert your relevant API keys:
```env
# If using Hugging Face for transcribing
HF_API_KEY="your-huggingface-token"

# If using AssemblyAI for transcribing
ASSEMBLYAI_API_KEY="your-assemblyai-key"

# If using OpenRouter for post-processing
OPENROUTER_API_KEY="your-openrouter-key"

# If using Gemini directly
GEMINI_API_KEY="your-gemini-key"
```

#### Edit config.toml
Adjust the pipeline behaviors in `config.toml`. By default, it is set up to use Hugging Face for ASR transcription, and OpenRouter for Markdown post-processing:

```toml
[paths]
input_dir = "input"
output_dir = "output"
prompts_dir = "prompts"
prompt_file = "prompts/post_process.md"

[concurrency]
transcription_workers = 2
postprocessing_workers = 2

[preprocessing]
enabled = true
ffmpeg_path = "ffmpeg"
chunking_enabled = false

[transcriber]
provider = "huggingface"
endpoint_url = "https://api-inference.huggingface.co/models/ibm-granite/granite-speech-4.1-2b-plus"
model = "ibm-granite/granite-speech-4.1-2b-plus"
api_key_env = "HF_API_KEY"

# Example for AssemblyAI:
# provider = "assemblyai"
# enable_speaker_attribution = true
# api_key_env = "ASSEMBLYAI_API_KEY"
# assemblyai_prompt_file = "prompts/assemblyai_prompt.txt"
# assemblyai_keyterms_file = "prompts/assemblyai_keyterms.txt"

[post_processor]
provider = "openai_compatible"
endpoint_url = "https://openrouter.ai/api/v1"
model = "google/gemini-2.5-pro"  # Or your model of choice on OpenRouter
api_key_env = "OPENROUTER_API_KEY"
temperature = 0.2
```

#### RSS Feed Sync (optional)

To automatically pull podcast episodes before each run, add one or more `[[rss.feeds]]` entries to `config.toml`:

```toml
[[rss.feeds]]
url = "https://example.com/podcast.rss"
# max_episodes = 10  # optional: limit to the N most recent episodes
```

Multiple feeds are supported — add additional `[[rss.feeds]]` blocks. On each run, the pipeline fetches every configured feed and downloads any episodes whose filename is not already present in `input/`. Standard podcast RSS (`<enclosure>`) and `<media:content>` formats are both handled.

---

## Usage

1.  Drop your media files (supports `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`, `.webm`, and video `.mp4`) into the `input/` directory.
2.  Execute the pipeline:
    ```bash
    uv run podscribe
    ```

### CLI Flags
- `--stage <all|transcribe|postprocess>`: Run only specific stages of the pipeline.
- `--language <lang>`: Override the transcription language (e.g. `en`, `es`).
- `--log-level <DEBUG|INFO|WARNING|ERROR>`: Set the logging verbosity.
- `--log-file <path>`: Log output directly to a file instead of stdio.
- `--alsologtostderr`: When `--log-file` is configured, also duplicate log output to stderr.
- `--dump-config`: Print the resolved configuration dictionary and exit.
- `--rss-download-only`: Only sync configured RSS podcast feeds and exit without running transcription.

---

## Understanding Pipeline Outputs

Upon running the pipeline, the `output` directory is generated containing:
-   **`output/state.json`**: Contains state and hashes of all processed files. Do not delete if you wish to resume incomplete pipeline runs.
-   **`output/pipeline.log`**: Complete runtime logging of errors and successes.
-   **`output/preprocessed/`**: Temporary 16kHz mono `.wav` copies of your ingested audio.
-   **`output/raw_transcripts/`**: Intermediate raw `.txt` files containing speaker tags directly from the ASR endpoint (e.g., `[Speaker 1]`).
-   **`output/[filename]_final.md`**: The final polished, Markdown-formatted transcripts styled according to your editing instructions.

---

## Customizing the Post-Processing Prompt
You can alter the instructions given to the Text LLM by editing:
`prompts/post_process.md`

Ensure you leave the `{{TRANSCRIPT}}` placeholder intact, as this is where the orchestrator injects the raw text.
