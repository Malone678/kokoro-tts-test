#!/usr/bin/env python3
import sys
import os
import traceback
import base64

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
    from runpod import RunPodLogger  # Correct for latest runpod (1.x)
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
            # Absolute import that works in RunPod serverless
            from api.src.inference.kokoro_v1 import KokoroV1
            model = KokoroV1()
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

        log.info(f"TTS request: {text[:60]}... voice={voice}")

        kokoro = load_model()
        audio_bytes = kokoro.generate_audio_bytes(
            text=text, voice=voice, speed=speed, response_format="mp3"
        )
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        log.info(f"Generated {len(audio_bytes)} bytes")
        return {
            "output": {
                "status": "success",
                "audio_b64": audio_b64,
                "length_bytes": len(audio_bytes)
            }
        }

    except Exception as e:
        err = f"HANDLER ERROR: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(err)
        log.error(err)
        return {"error": err}

print("Starting runpod.serverless.start()...")
runpod.serverless.start({"handler": handler})
