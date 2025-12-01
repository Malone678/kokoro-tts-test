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
import tempfile # Needed to create a temporary directory path
nest_asyncio.apply()                     # ← Critical for RunPod

# ... (omitted imports and logging setup for brevity) ...

# RunPod setup (omitted for brevity)
try:
    import runpod
    from runpod import RunPodLogger
    log = RunPodLogger()
    # ... (omitted) ...
except Exception as e:
    # ... (omitted) ...

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

        # --- USE THE CORRECT SERVICE FOR LONG FORM AND ADD WRITER FIX ---
        from api.src.services.tts_service import TTSService
        from api.src.services.streaming_audio_writer import StreamingAudioWriter
        
        # Instantiate the service directly.
        # We must await the 'create' method first to initialize managers
        initialized_service = asyncio.run(TTSService.create())
        
        # Create a dummy writer instance using a temporary file path
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, "temp_audio_output")
        writer = StreamingAudioWriter(output_path=temp_file_path)

        async def generate_audio_stream_long_form_service():
            all_chunks = []
            
            # The generate_audio_stream handles all chunking internally
            async for chunk in initialized_service.generate_audio_stream(
                text=text, 
                voice=voice_name, # Pass the name, the service resolves the path
                speed=speed,
                writer=writer, # <-- PASS THE DUMMY WRITER INSTANCE HERE
                output_format=None # None means return raw audio chunks for local assembly
            ):
                if chunk.audio is not None:
                    all_chunks.append(chunk.audio)
            
            if not all_chunks:
                raise ValueError("No audio generated from the service.")
            return np.concatenate(all_chunks)

        # Call the new async function that uses the service manager
        audio_np = asyncio.run(generate_audio_stream_long_form_service())
        # --- END SERVICE CALL ---

        # ... (rest of MP3 conversion and return statement) ...
        with io.BytesIO() as wav_io:
            # The service returns float32 audio, convert to int16 for standard WAV/MP3 conversion
            # We use soundfile's 'subtype' parameter to control this
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


