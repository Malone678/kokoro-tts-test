import runpod
import base64
import os
import sys

# This is the ONLY logger that actually appears in RunPod's Logs tab
logger = runpod.Logger()

# Add the correct path so Python can find inference/kokoro_v1.py
sys.path.append(os.path.join(os.getcwd(), "api", "src"))

# Global model — lazy loaded
model = None

def load_model():
    global model
    if model is None:
        logger.info("Starting Kokoro model load...")
        try:
            from inference.kokoro_v1 import KokoroV1
            model = KokoroV1()
            logger.info("Kokoro model loaded successfully!")
        except Exception as e:
            logger.error(f"MODEL LOAD FAILED: {str(e)}")
            raise  # This will bubble up and be caught in handler()
    return model

def handler(job):
    try:
        job_input = job["input"]
        text = job_input.get("text", "").strip()
        voice = job_input.get("voice", "af_bella")
        speed = float(job_input.get("speed", 1.0))

        if not text:
            return {"error": "No text provided"}

        logger.info(f"Request → text: '{text[:60]}...' | voice: {voice} | speed: {speed}")

        kokoro = load_model()

        audio_bytes = kokoro.generate_audio_bytes(
            text=text,
            voice=voice,
            speed=speed,
            response_format="mp3"
        )

        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        logger.info(f"Success! Audio length: {len(audio_bytes)} bytes")
        return {
            "output": {
                "status": "success",
                "audio_b64": audio_b64,
                "length_bytes": len(audio_bytes)
            }
        }

    # ←←← THIS IS THE IMPORTANT PART YOU ASKED FOR ←←←
    except Exception as e:
        error_msg = f"HANDLER CRASHED → {type(e).__name__}: {str(e)}"
        logger.error(error_msg)
        # This return makes the job show as FAILED (red) but with your exact error message
        return {"error": error_msg}

# Start serverless worker
runpod.serverless.start({"handler": handler})
