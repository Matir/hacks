# Granite Speech OpenAI-Compatible Transcription Server

This is a standalone FastAPI-based audio transcription server designed to expose the `ibm-granite/granite-speech-4.1-2b-plus` model as an OpenAI-compatible `/v1/audio/transcriptions` endpoint.

## Requirements

- Python 3.9+
- CUDA-enabled GPU (highly recommended for performance, though CPU is supported)
- Packages in `requirements.txt`

## Setup & Run

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   python server.py
   ```
   By default, the server starts on `http://0.0.0.0:8000`.

### Environment Variables

You can customize the server's behavior using environment variables:

- `MODEL_NAME`: The HF model repository (defaults to `ibm-granite/granite-speech-4.1-2b-plus`).
- `SYSTEM_PROMPT`: Custom system prompt for the Granite conversational context.
- `USER_PROMPT`: Default transcription instruction prompt (defaults to `"Transcribe the audio."`).
- `HOST`: Host bind address (defaults to `0.0.0.0`).
- `PORT`: Port to bind (defaults to `8000`).

## Docker Setup

You can build and run the server within a Docker container. This handles all system dependencies like `ffmpeg` and `libsndfile` automatically.

### 1. Build the Docker Image
```bash
docker build -t granite-speech-server .
```

### 2. Run on CPU
```bash
docker run -d \
  -p 8000:8000 \
  --name granite-speech \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  granite-speech-server
```
*Note: Mounting the huggingface cache directory (`-v ~/.cache/huggingface...`) is recommended so the model weights do not have to be re-downloaded every time you start the container.*

### 3. Run on GPU (Requires NVIDIA Container Toolkit)
```bash
docker run -d \
  -p 8000:8000 \
  --name granite-speech \
  --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  granite-speech-server
```

## API Usage

The server exposes an OpenAI-compatible endpoint at `/v1/audio/transcriptions`.

### 1. cURL Example

```bash
curl http://localhost:8000/v1/audio/transcriptions \
  -H "Authorization: Bearer empty" \
  -F "file=@/path/to/audio.wav" \
  -F "model=ibm-granite/granite-speech-4.1-2b-plus"
```

### 2. Python OpenAI Client Example

You can use the official `openai` Python package to interact with this server:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="ignored"
)

with open("/path/to/audio.wav", "rb") as audio_file:
    transcript = client.audio.transcriptions.create(
        model="ibm-granite/granite-speech-4.1-2b-plus",
        file=audio_file,
        response_format="json" # Options: json, text, verbose_json
    )

print(transcript.text)
```

### 3. Custom IBM Granite Prompting

Granite Speech is an interactive dialogue-based audio model. You can optionally pass a custom instruction using the `user_prompt` form field to direct how the audio is processed (e.g., translation, answering spoken questions, summarizing):

```bash
curl http://localhost:8000/v1/audio/transcriptions \
  -F "file=@/path/to/audio.wav" \
  -F "user_prompt=Translate this audio into Spanish."
```
