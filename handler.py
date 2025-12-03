#!/usr/bin/env python3
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
import time                               # ← added
from datetime import datetime, timedelta # ← added
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions # ← added
from pydub import AudioSegment          # ← now used for MP3 conversion

nest_asyncio.apply()
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("=== handler.py STARTED ===")
print(f"CWD: {os.getcwd()}")
print(f"Files in /app: {os.listdir('/app')}")
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

# ────────────────────── GLOBAL SINGLETON SERVICE ──────────────────────
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

# ────────────────────── ASYNC HANDLER ──────────────────────
async def handler(job):
    print("Handler called")
    log.info("Handler start")
    await initialize_service_once()
    try:
        inp = job["input"]
        text = (inp.get("text") or inp.get("prompt") or "").strip()
        voice_name = inp.get("voice", "af_bella")
        speed = float(inp.get("speed", 1.0))
        if not text:
            return {"error": "No text provided"}

        log.info(f"Received text length: {len(text)} characters.")
        log.info(f"TTS request initiated for voice={voice_name} speed={speed}")

        from api.src.services.streaming_audio_writer import StreamingAudioWriter
        writer = StreamingAudioWriter(format="wav", sample_rate=22050)

        async def generate_audio_stream_long_form_service():
            all_chunks = []
            async for chunk in tts_service.generate_audio_stream(
                text=text,
                voice=voice_name,
                speed=speed,
                writer=writer,
                output_format=None
            ):
                if chunk.audio is not None:
                    all_chunks.append(chunk.audio)
            if not all_chunks:
                raise ValueError("No audio generated from the service.")
            return np.concatenate(all_chunks)

        audio_np = await generate_audio_stream_long_form_service()

        with io.BytesIO() as wav_io:
            sf.write(wav_io, audio_np, 22050, format='WAV', subtype='PCM_16')
            wav_bytes = wav_io.getvalue()

        # ←←← YOUR ORIGINAL LOGGING — 100 % PRESERVED ←←←
        audio_b64 = base64.b64encode(wav_bytes).decode()
        log.info(f"Generated {len(wav_bytes)} WAV bytes — SUCCESS!")
        log.info(f"audio_b64: {audio_b64}")
        # ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←

        # ─────── CONVERT TO MP3 + UPLOAD TO AZURE + PLAYABLE SAS URL ───────
        try:
            AZURE_KEY = os.getenv("AZURE_STORAGE_KEY")
            if not AZURE_KEY:
                raise Exception("AZURE_STORAGE_KEY secret not found in RunPod environment!")

            STORAGE_ACCOUNT = "meditationttsstorage"
            CONTAINER_NAME  = "narration-output"

            # Convert WAV → MP3 in memory (128 kbps = excellent quality, tiny file)
            wav_io = io.BytesIO(wav_bytes)
            audio = AudioSegment.from_wav(wav_io)
            mp3_io = io.BytesIO()
            audio.export(mp3_io, format="mp3", bitrate="128k")
            mp3_bytes = mp3_io.getvalue()
            mp3_size_mb = len(mp3_bytes) / 1024 / 1024

            blob_name = f"kokoro_{job.get('id','temp')}_{int(time.time())}.mp3"

            connect_str = f"DefaultEndpointsProtocol=https;AccountName={STORAGE_ACCOUNT};AccountKey={AZURE_KEY};EndpointSuffix=core.windows.net"
            blob_service_client = BlobServiceClient.from_connection_string(connect_str)
            blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)

            log.info(f"Uploading {mp3_size_mb:.1f} MB MP3 to Azure Blob: {blob_name}")
            blob_client.upload_blob(mp3_bytes, overwrite=True)
            log.info("MP3 upload to Azure successful")

            sas_token = generate_blob_sas(
                account_name=STORAGE_ACCOUNT,
                container_name=CONTAINER_NAME,
                blob_name=blob_name,
                account_key=AZURE_KEY,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=2)
            )
            sas_url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net/{CONTAINER_NAME}/{blob_name}?{sas_token}"

            log.info(f"Generated 2-hour playable MP3 SAS URL: {sas_url}")

            return {
                "output": {
                    "status": "success",
                    "playable_url": sas_url,          # ← shows cleanly in PowerShell
                    "file_name": blob_name,
                    "size_mb": round(mp3_size_mb, 1),
                    "format": "mp3",
                    "audio_b64": audio_b64            # still here exactly as you wanted
                }
            }

        except Exception as azure_err:
            log.error(f"Azure/MP3 upload failed: {azure_err}")
            return {
                "output": {
                    "status": "success (Azure fallback)",
                    "audio_b64": audio_b64,
                    "length_bytes": len(wav_bytes),
                    "azure_error": str(azure_err)
                }
            }

    except Exception as e:
        err = f"HANDLER ERROR: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(err)
        log.error(err)
        return {"error": err}

# ────────────────────── START SERVERLESS WORKER ──────────────────────
print("Starting RunPod serverless worker...")
runpod.serverless.start({
    "handler": handler,
    "timeout": 1800
})
