import sys
import os
import traceback
import base64
import asyncio
import numpy as np
import io
import soundfile as sf
import nest_asyncio
import re
import tempfile
import time  # ← added
from datetime import datetime, timedelta  # ← added
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions  # ← added
from azure.storage.blob import ContentSettings  # ← added for MP3 content type
from pydub import AudioSegment  # ← added for MP3 conversion

nest_asyncio.apply()  # ← Critical for RunPod

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

# ────────────────────── GLOBAL SINGLETON SERVICE (cold-start safe) ──────────────────────
tts_service = None

async def initialize_service_once():
    global tts_service
    if tts_service is not None:
        print("Service already initialized — reusing loaded model")
        return
    from api.src.services.tts_service import TTSService
    print("Creating TTSService and loading model (only once per worker lifetime)")
    tts_service = await TTSService.create()
    log.info("Initializing backend via service manager...")
    await tts_service.model_manager.initialize()
    log.info("Backend initialized.")
    model_path_abs = "/app/api/src/models/v1_0/kokoro-v1_0.pth"
    log.info(f"Loading model using absolute path via service manager: {model_path_abs}")
    await tts_service.model_manager.load_model(model_path_abs)
    log.info("Model loaded successfully via service manager using absolute path.")
    print("Kokoro model fully loaded and ready for all jobs!")

# ────────────────────── ASYNC HANDLER (keeps all your logging) ──────────────────────
async def handler(job):
    print("Handler called")
    log.info("Handler start")
    # This runs only on first job after cold start
    await initialize_service_once()

    try:
        inp = job["input"]
        # Accept both "text" and "prompt" keys
        text = (inp.get("text") or inp.get("prompt") or "").strip()
        voice_name = inp.get("voice", "af_bella")
        speed = float(inp.get("speed", 1.0))
        if not text:
            return {"error": "No text provided"}

        log.info(f"Received text length: {len(text)} characters.")
        log.info(f"TTS request initiated for voice={voice_name} speed={speed}")

        # --- USE THE CORRECT SERVICE FOR LONG FORM ---
        from api.src.services.streaming_audio_writer import StreamingAudioWriter
      
        # --- FIX 3: Initialize the writer with required arguments ---
        writer = StreamingAudioWriter(format="wav", sample_rate=22050)

        async def generate_audio_stream_long_form_service():
            all_chunks = []
          
            async for chunk in tts_service.generate_audio_stream(
                text=text,
                voice=voice_name,
                speed=speed,
                writer=writer,
                output_format=None  # None means return raw audio chunks for local assembly
            ):
                if chunk.audio is not None:
                    all_chunks.append(chunk.audio)
          
            if not all_chunks:
                raise ValueError("No audio generated from the service.")  # ← FIXED: was ValueValue
            return np.concatenate(all_chunks)

        # Call the new async function that uses the service manager
        audio_np = await generate_audio_stream_long_form_service()

        # The service returns float32 audio, convert to int16 for standard WAV writing
        with io.BytesIO() as wav_io:
            sf.write(wav_io, audio_np, 22050, format='WAV', subtype='PCM_16')
            wav_bytes = wav_io.getvalue()

        # Encode WAV bytes to Base64 directly (still computed for logging, but NOT returned)
        audio_b64 = base64.b64encode(wav_bytes).decode()

        # The output length bytes now reflect the larger WAV file size
        log.info(f"Generated {len(wav_bytes)} WAV bytes — SUCCESS!")
        log.info(f"audio_b64 length: {len(audio_b64)} characters (kept only in logs)")

        # ─────── CONVERT TO MP3 + UPLOAD TO AZURE + PLAYABLE SAS URL ───────
        try:
            wav_io = io.BytesIO(wav_bytes)
            audio = AudioSegment.from_wav(wav_io)
            mp3_io = io.BytesIO()
            audio.export(mp3_io, format="mp3", bitrate="128k")
            mp3_bytes = mp3_io.getvalue()

            AZURE_KEY = os.getenv("AZURE_STORAGE_KEY")
            if not AZURE_KEY:
                raise Exception("AZURE_STORAGE_KEY secret not found in RunPod environment!")

            STORAGE_ACCOUNT = "meditationttsstorage"
            CONTAINER_NAME = "narration-output"
            blob_name = f"kokoro_{job.get('id','temp')}_{int(time.time())}.mp3"

            connect_str = f"DefaultEndpointsProtocol=https;AccountName={STORAGE_ACCOUNT};AccountKey={AZURE_KEY};EndpointSuffix=core.windows.net"
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)

            log.info(f"Uploading {len(mp3_bytes)} bytes to Azure Blob: {blob_name}")
            blob_client.upload_blob(mp3_bytes, overwrite=True, content_settings=ContentSettings(content_type="audio/mpeg"))
            log.info("MP3 upload to Azure successful")

            sas_token = generate_blob_sas(
                account_name=STORAGE_ACCOUNT,
                container_name=CONTAINER_NAME,
                blob_name=blob_name,
                account_key=AZURE_KEY,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=1)
            )
            sas_url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}?{sas_token}"
            log.info(f"Generated 1-hour playable SAS URL: {sas_url}")

            # ←←← CRITICAL FIX: Flat return + NO audio_b64 → RunPod will deliver this every time
            return {
                "status": "success",
                "playable_url": sas_url,
                "file_name": blob_name,
                "length_bytes": len(mp3_bytes)
            }

        except Exception as azure_err:
            log.error(f"Azure upload failed: {str(azure_err)}")
            # ←←← Even on fallback: small payload only
            return {
                "status": "azure_failed",
                "error": str(azure_err),
                "wav_length_bytes": len(wav_bytes)
            }

    except Exception as e:
        err = f"HANDLER ERROR: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(err)
        log.error(err)
        return {"error": err}

# ────────────────────── START — 100% cold-start, zero idle cost ──────────────────────
print("Starting RunPod serverless worker...")
runpod.serverless.start({
    "handler": handler,  # ← now async
    "timeout": 1800      # 30 minutes max (perfect for 18–25 min audiobooks)
})
