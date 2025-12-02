#!/usr/bin/env python3
import sys
import os
import traceback
import base64
import asyncio
import numpy as np
import io
from pydub import AudioSegment
import soundfile as sf
import nest_asyncio
import re
import tempfile 
from api.src.core.config import settings # Import settings to get the model name

nest_asyncio.apply()                     # ← Critical for RunPod

# Immediate logging
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("=== handler.py STARTED ===")
print(f"CWD: {os.getcwd()}")
print(f"Files in /app: {os.listdir('/app')}")

# Rely on PYTHONPATH=/app:/app/api from RunPod environment variables
print("Relying on PYTHONPATH=/app:/app/api from RunPod environment variables")

# RunPod setup
try:
    import runpod
    from runpod import RunPodLogger
    log = RunPodLogger()
    print("runpod imported successfully")
    log.info("RunPod Logger ready")
except Exception as e:
    print(f"RUNPOD IMPORT FAILED: {e}")
    sys.exit(1)

# Model management is handled by the service now, so no global model variable or load_model function is needed.

def handler(job):
    print("Handler called")
    log.info("Handler start")
    try:
        inp = job["input"]
        text = inp.get("text", "").strip()
        voice_name = inp.get("voice", "af_bella")
        speed = float(inp.get("speed", 1.0))

        if not text:
            return {"error": "No text provided"}

        log.info(f"Received text length: {len(text)} characters.")
        log.info(f"TTS request initiated for voice={voice_name} speed={speed}")

        # --- USE THE CORRECT SERVICE FOR LONG FORM ---
        from api.src.services.tts_service import TTSService
        from api.src.services.streaming_audio_writer import StreamingAudioWriter
        
        # We must await the 'create' method first to initialize managers
        # We use asyncio.run because this handler function is synchronous at the top level
        initialized_service = asyncio.run(TTSService.create())
        
        # --- FIX 1: Explicitly load the model via the manager (solves "Backend not initialized") ---
        # Get the default model name from the settings object, defaulting to "v1_0" if not set
        model_name = settings.default_model_code or "v1_0" 
        log.info(f"Loading model '{model_name}' via service manager...")
        asyncio.run(initialized_service.model_manager.load_model(model_name))
        log.info(f"Model '{model_name}' loaded successfully via service manager.")
        # --- END FIX 1 ---
        
        # --- FIX 2: Initialize the writer with required arguments (solves writer errors) ---
        writer = StreamingAudioWriter(format="wav", sample_rate=22050)

        async def generate_audio_stream_long_form_service():
            all_chunks = []
            
            # The generate_audio_stream handles all chunking internally
            async for chunk in initialized_service.generate_audio_stream(
                text=text, 
                voice=voice_name, # Pass the name, the service resolves the path
                speed=speed,
                writer=writer, # Pass the initialized writer instance
                output_format=None # None means return raw audio chunks for local assembly
            ):
                if chunk.audio is not None:
                    all_chunks.append(chunk.audio)
            
            if not all_chunks:
                raise ValueError("No audio generated from the service.")
            # The service returns float32 audio, convert to int16 for standard WAV/MP3 conversion
            return np.concatenate(all_chunks)

        # Call the new async function that uses the service manager
        audio_np = asyncio.run(generate_audio_stream_long_form_service())
        # --- END SERVICE CALL ---

        # The service returns float32 audio, convert to int16 for standard WAV/MP3 conversion
        # We use soundfile's 'subtype' parameter to control this
        with io.BytesIO() as wav_io:
            sf.write(wav_io, audio_np, 22050, format='WAV', subtype='PCM_16')
            wav_bytes = wav_io.getvalue()

        audio_seg = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        with io.BytesIO() as mp3_io:
            audio_seg.export(mp3_io, format="mp3")
            mp3_bytes = mp3_io.getvalue()

        audio_b64 = base64.b64encode(mp3_bytes).decode()

        log.info(f"Generated {len(mp3_bytes)} MP3 bytes — SUCCESS!")
        return {
            "output": {
                "status": "success",
                "audio_b64": audio_b64,
                "length_bytes": len(mp3_bytes)
            }
        }

    except Exception as e:
        err = f"HANDLER ERROR: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(err)
        log.error(err)
        return {"error": err}

print("Starting RunPod serverless worker...")
runpod.serverless.start({"handler": handler})



