#!/usr/bin/env python3
import sys
import os
import traceback
import base64
import asyncio
import numpy as np
from pydub import AudioSegment
import soundfile as sf  # For numpy to WAV

# Force immediate printing
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("=== handler.py STARTED ===")
print(f"CWD: {os.getcwd()}")
print(f"Files in /app: {os.listdir('/app')}")

# Add the correct path
sys.path.insert(0, os.path.join(os.getcwd(), "api", "src"))
print("Added /app/api/src to sys.path")

try:
    import runpod
    from runpod import RunPodLogger
    log = RunPodLogger()
    print("runpod imported successfully")
    log.info("RunPod Logger ready")
except Exception as e:
    print(f"RUNPOD IMPORT FAILED: {str(e)}")
    sys.exit(1)

model = None

def load_model():
    global model
    if model is None:
        print("Loading Kokoro model...")
        log.info("Model load start")
        try:
            from api.src.inference.kokoro_v1 import KokoroV1
            model = KokoroV1()
            # Call load_model if needed (from code, it's async but we call sync for simplicity)
            asyncio.run(model.load_model("kokoro-v1.0"))  # Use default model path
            print("Kokoro model loaded!")
            log.info("Model loaded successfully")
        except Exception as e:
            err = f"MODEL LOAD FAILED: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            print(err)
            log.error(err)
            raise
    return model

def handler(job):
    print("Handler called")
    log.info("Handler start")
    try:
        inp = job["input"]
        text = inp.get("text", "").strip()
        voice = inp.get("voice", "af_bella")
        speed = float(inp.get("speed", 1.0))
        if not text:
            return {"error": "No text provided"}
        log.info(f"TTS request: {text[:60]}... voice={voice} speed={speed}")
        kokoro = load_model()

        # Run the async generate and collect chunks
        async def get_audio():
            chunks = []
            async for chunk in kokoro.generate(text=text, voice=voice, speed=speed):
                if chunk.audio is not None:
                    chunks.append(chunk.audio)
            if chunks:
                full_audio = np.concatenate(chunks)
                return full_audio
            raise ValueError("No audio generated")

        full_audio = asyncio.run(get_audio())

        # Convert numpy to WAV bytes (Kokoro is 22050 Hz mono)
        with io.BytesIO() as wav_buffer:
            sf.write(wav_buffer, full_audio, 22050, format='WAV')
            wav_bytes = wav_buffer.getvalue()

        # Convert WAV to MP3 bytes
        audio = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        with io.BytesIO() as mp3_buffer:
            audio.export(mp3_buffer, format="mp3")
            mp3_bytes = mp3_buffer.getvalue()

        audio_b64 = base64.b64encode(mp3_bytes).decode("utf-8")
        log.info(f"Generated {len(mp3_bytes)} MP3 bytes")
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

print("Starting runpod.serverless.start()...")
runpod.serverless.start({"handler": handler})
