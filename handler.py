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
    # This block was empty and causing the error
    print(f"RUNPOD IMPORT FAILED: {e}")
    sys.exit(1)

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

        # --- USE THE CORRECT SERVICE FOR LONG FORM AND ADD WRITER FIX ---
        from api.src.services.tts_service import TTSService
        from api.src.services.streaming_audio_writer import StreamingAudioWriter
        
        # We must await the 'create' method first to initialize managers
        initialized_service = asyncio.run(TTSService.create())
        
        # --- FIX: Initialize the writer WITHOUT the output_path argument ---
        writer = StreamingAudioWriter()

        async def generate_audio_stream_long_form_service():
            all_chunks = []
            
            async for chunk in initialized_service.generate_audio_stream(
                text=text, 
                voice=voice_name, 
                speed=speed,
                writer=writer, # This is now the correctly initialized writer
                output_format=None
            ):
                if chunk.audio is not None:
                    all_chunks.append(chunk.audio)
            
            if not all_chunks:
                raise ValueError("No audio generated from the service.")
            return np.concatenate(all_chunks)

        # Call the new async function that uses the service manager
        audio_np = asyncio.run(generate_audio_stream_long_form_service())
        # --- END SERVICE CALL ---

        # The service returns float32 audio, convert to int16 for standard WAV/MP3 conversion
        # We use soundfile's 'subtype' parameter to control this
        with io.BytesIO() as wav_io:
            sf.write(wav_io, audio_np, 22050, format='WAV', subtype='PCM_16')
            wav_bytes = wav_io.getvalue()

        # This section converts to MP3 and creates the Base64 string for the playable file
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

