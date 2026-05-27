# Transcription Pipeline Task List (TODO)

This document outlines remaining tasks to transition the prototype transcription pipeline to a robust, production-ready workflow.

---

## Phase 1: Local Environment & Setup
- [ ] **Configure Environment Variables:** Copy `.env.example` to `.env` and populate:
    - [ ] `HF_API_KEY` (for Hugging Face prototype)
    - [ ] `OPENROUTER_API_KEY` (for OpenRouter post-processing)
- [ ] **Install System FFmpeg:** Ensure `ffmpeg` is installed on the host machine and accessible in the system PATH.
    - *Verification Command:* `ffmpeg -version`
- [ ] **Prepare Input Data:** Drop a short test audio file (e.g. `.mp3`, `.m4a`, `.wav`) into the `input/` directory.

---

## Phase 2: Testing & Validation
- [ ] **Verify Preprocessing:** Run the pipeline and check `output/preprocessed/` to confirm `ffmpeg` successfully downsamples files to **16kHz, mono, WAV**.
- [ ] **Validate Granite speech ASR (Hugging Face):** 
    - [ ] Verify the raw transcript is captured.
    - [ ] Confirm if IBM Granite Speech 4.1 output format matches the standard HF structure (`{"text": "..."}`) or if custom parsing is needed for native speaker tags.
- [ ] **Validate OpenRouter LLM Integration:**
    - [ ] Test prompt formatting inside `prompts/post_process.md`.
    - [ ] Confirm that OpenRouter successfully accepts the transcript, formats it, and returns a clean markdown output.
- [ ] **Test State Persistence:** Interrupt a pipeline run mid-processing, resume it, and verify that:
    - [ ] Preprocessed files are skipped if hashes match.
    - [ ] Transcriptions are skipped if `raw_transcript_path` exists and status is `transcribed`.

---

## Phase 3: Robustness & Production Hardening
- [ ] **Add Retries and Rate-Limit Handling:** 
    - [ ] Integrate backoff strategies (e.g. using `tenacity` which was installed via `uv`) to handle standard API rate limits (`429`) and transient connection errors.
- [ ] **Support Large Files:** Add chunking or streaming if audio files exceed maximum payload limits of the selected Hugging Face endpoint.
- [ ] **Verify Baseten / Modal Transition:**
    - [ ] If moving from HF prototype to production Baseten, deploy the Granite model using Truss.
    - [ ] Update `config.toml` with Baseten's OpenAI-compatible transcription endpoint.
