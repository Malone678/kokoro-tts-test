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

# Force immediate printing
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("=== handler.py STARTED ===")
print(f"CWD: {os.getcwd()}")
print(f"Files in /app: {os.listdir('/app')}")

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

# Model is loaded automatically by the base image → no explicit load needed
model = None

def load_model():
    global model
    if model is None:
        print("Initializing Kokoro model (pre-loaded by base image)...")
        log.info("Model init start")
        try:
            from api.src.inference.kokoro_v1 import KokoroV1
            model = KokoroV1()          # ← This already loads the model!
            print("Kokoro model ready!")
            log.info("Model ready")
        except Exception as e:
            err = f"MODEL INIT FAILED: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
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

        # Run the async generator and collect chunks
        async def generate_audio():
            chunks = []
            async for chunk in kokoro.generate(text=text, voice=voice, speed=speed):
                if chunk.audio is not None:
                    chunks.append(chunk.audio)
            if not chunks:
                raise ValueError("No audio generated")
            return np.concatenate(chunks)

        audio_np = asyncio.get_event_loop().run_until_complete(generate_audio())

        # Convert to MP3 bytes
        with io.BytesIO() as wav_io:
            sf.write(wav_io, audio_np, samplerate=22050, format='WAV')
            wav_bytes = wav_io.getvalue()

        audio_seg = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        with io.BytesIO() as mp3_io:
            audio_seg.export(mp3_io, format="mp3")
            mp3_bytes = mp3_io.getvalue()

        audio_b64 = base64.b64encode(mp3_bytes).decode()

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

print("Starting serverless worker...")
runpod.serverless.start({"handler": handler})
