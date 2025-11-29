#!/usr/bin/env python3
import sys
import os
import traceback

# Force immediate output flush (shows in RunPod even on early crash)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Earliest prints: Log startup BEFORE imports
print("=== WORKER SPIN-UP: handler.py executing ===")
print(f"Current dir: {os.getcwd()}")
print(f"Files here: {os.listdir('.')}")
print(f"Python sys.path: {sys.path}")

# Add path early (for /app/api/src/inference)
base_path = os.path.join(os.getcwd(), "api", "src")
sys.path.insert(0, base_path)
print(f"Added path: {base_path}")
print(f"Files in api/src/inference: {os.listdir(os.path.join(base_path, 'inference')) if os.path.exists(os.path.join(base_path, 'inference')) else 'DIR MISSING'}")

try:
    print("Importing runpod...")
    import runpod
    from runpod import RunPodLogger  # Official logger (fixes silent logs)
    log = RunPodLogger()
    print("runpod imported!")
    log.info("Logger initialized")
except Exception as e:
    print(f"IMPORT CRASH: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}")
    sys.exit(1)

# Global model
model = None

def load_model():
    global model
    if model is None:
        print("Loading model...")
        log.info("Model load start")
        try:
            from inference.kokoro_v1 import KokoroV1
            model = KokoroV1()
            print("Model loaded!")
            log.info("Model loaded OK")
        except Exception as e:
            error = f"MODEL CRASH: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            print(error)
            log.error(error)
            raise
    return model

def handler(job):
    print("=== HANDLER RUNNING ===")
    log.info("Handler start")
    try:
        job_input = job["input"]
        text = job_input.get("text", "").strip()
        voice = job_input.get("voice", "af_bella")
        speed = float(job_input.get("speed", 1.0))

        if not text:
            return {"error": "No text"}

        print(f"Gen: {text[:60]}... | voice: {voice} | speed: {speed}")
        log.info(f"Gen request: {text[:60]}...")

        kokoro = load_model()

        import base64
        audio_bytes = kokoro.generate_audio_bytes(text=text, voice=voice, speed=speed, response_format="mp3")
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        print(f"SUCCESS: {len(audio_bytes)} bytes")
        log.info("Success")
        return {"output": {"status": "success", "audio_b64": audio_b64, "length_bytes": len(audio_bytes)}}
    except Exception as e:
        error = f"HANDLER CRASH: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(error)
        log.error(error)
        return {"error": error}

print("Starting serverless...")
try:
    runpod.serverless.start({"handler": handler})
except Exception as e:
    error = f"START CRASH: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}")
    print(error)
    log.error(error)
    sys.exit(1)
