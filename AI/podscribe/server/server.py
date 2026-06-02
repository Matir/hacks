import io
import os
import re
from typing import Optional
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from contextlib import asynccontextmanager
import torch
import librosa
import soundfile as sf
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

MODEL_NAME = os.getenv("MODEL_NAME", "ibm-granite/granite-speech-4.1-2b-plus")
DEFAULT_SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT", 
    "Knowledge Cutoff Date: April 2024.\nToday's Date: December 19, 2024.\nYou are Granite, developed by IBM. You are a helpful AI assistant"
)
DEFAULT_USER_PROMPT = os.getenv("USER_PROMPT", "Transcribe the audio.")

# Global variables for model and processor
model = None
processor = None
tokenizer = None
device = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, processor, tokenizer, device
    print(f"Loading model: {MODEL_NAME}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    processor = AutoProcessor.from_pretrained(MODEL_NAME)
    tokenizer = processor.tokenizer
    
    torch_dtype = torch.bfloat16 if device == "cuda" else torch.float32
    print(f"Using dtype: {torch_dtype}")
    
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        MODEL_NAME,
        device_map=device,
        torch_dtype=torch_dtype
    )
    model.eval()
    print("Model loaded successfully!")
    yield
    print("Shutting down...")

app = FastAPI(
    title="Granite Speech API Server",
    description="OpenAI-compatible audio transcription API using ibm-granite/granite-speech-4.1-2b-plus",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/v1/models")
async def list_models():
    """List the available models."""
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "created": 1700000000,
                "owned_by": "ibm"
            }
        ]
    }

import threading
import gc

# Threading lock to prevent concurrent GPU execution (avoids CUDA OOM)
inference_lock = threading.Lock()

@app.post("/v1/audio/transcriptions")
def transcribe_audio(
    file: UploadFile = File(...),
    model_name: str = Form(None, alias="model"),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),  # Used as prefix_text to guide transcription style/continuation
    response_format: Optional[str] = Form("json"),
    temperature: Optional[float] = Form(None),
    user_prompt: Optional[str] = Form(None, description="Custom instruction for Granite Speech model"),
):
    if model is None or processor is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet.")
    
    # Read file content synchronously since FastAPI runs normal 'def' in a thread pool
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file.")
        
    try:
        # Load audio and resample to the model's expected sampling rate (typically 16kHz)
        target_sr = getattr(processor.feature_extractor, "sampling_rate", 16000)
        
        # librosa.load works with file-like objects
        audio_data, sr = librosa.load(io.BytesIO(content), sr=target_sr)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse audio file: {str(e)}. Please ensure it is a valid audio format (WAV, MP3, etc.)"
        )

    # Determine prompts
    system_prompt = DEFAULT_SYSTEM_PROMPT
    inst_prompt = user_prompt if user_prompt else DEFAULT_USER_PROMPT
    prefix_text = prompt
    
    print(f"Transcribing audio (length: {len(audio_data)/target_sr:.2f}s) with user prompt: '{inst_prompt}', prefix_text: '{prefix_text}'")

    try:
        # Use lock to prevent concurrent execution on GPU
        with inference_lock:
            text = run_transcription(audio_data, inst_prompt, system_prompt, prefix_text)
    except Exception as e:
        print(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=f"Error during transcription: {str(e)}")
    finally:
        # Proactively clean up memory
        if device == "cuda":
            gc.collect()
            torch.cuda.empty_cache()

    # Handle different response formats
    if response_format == "text":
        return PlainTextResponse(text)
    elif response_format == "verbose_json":
        return JSONResponse(
            content={
                "text": text,
                "task": "transcribe",
                "language": language or "english",
                "duration": len(audio_data) / target_sr,
                "segments": [
                    {
                        "id": 0,
                        "seek": 0,
                        "start": 0.0,
                        "end": len(audio_data) / target_sr,
                        "text": text,
                        "tokens": [],
                        "temperature": temperature or 0.0,
                        "avg_logprob": 0.0,
                        "compression_ratio": 0.0,
                        "no_speech_prob": 0.0
                    }
                ]
            }
        )
    else:
        # default "json"
        return JSONResponse(content={"text": text})

@torch.inference_mode()
def run_transcription(audio, prompt, system_prompt, prefix_text=None, max_new_tokens=2000):
    chat = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    extra = {"prefix_text": prefix_text} if prefix_text is not None else {}
    
    prompt_text = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True, **extra)
    
    # Process inputs and run generation
    inputs = processor(prompt_text, audio, device=device, return_tensors="pt").to(device)
    
    outputs = model.generate(
        **inputs, 
        max_new_tokens=max_new_tokens, 
        do_sample=False, 
        num_beams=1
    )
    
    new_tokens = outputs[0, inputs["input_ids"].shape[-1]:]
    output_text = tokenizer.decode(new_tokens, add_special_tokens=False, skip_special_tokens=True)
    return output_text

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting server on {host}:{port}...")
    uvicorn.run(app, host=host, port=port)
