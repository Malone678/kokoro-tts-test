import runpod
import base64
import os
import sys
import logging  # For RunPod-visible logs

# Setup RunPod logger (logs show in dashboard!)
runpod_logger = runpod.Logger()  # This is key—plain print() won't appear

# Try to add paths (your original attempts)
sys.path.append(os.path.join(os.getcwd(), 'api', 'src'))
sys.path.append(os.path.join(os.getcwd(), 'src'))  # Fallback for inference dir

# Global model (lazy-load on first request)
model_backend = None

def load_model():
    global model_backend
    if model_backend is None:
        try:
            runpod_logger.info("Starting KokoroV1 model load...")
            from inference.kokoro_v1 import KokoroV1  # Your import
            model_backend = KokoroV1()
            runpod_logger.info("Model loaded successfully!")
        except ImportError as ie:
            runpod_logger.error(f"Import error: {ie}")
            raise
        except Exception as e:
            runpod_logger.error(f"Model init failed: {e}")
            raise
    return model_backend

def handler(event):
    try:
        runpod_logger.info("Handler started")
        input_data = event['input']
        text = input_data.get('text', '')
        voice = input_data.get('voice', 'af_bella')
        speed = input_data.get('speed', 1.0)

        if not text.strip():
            return {"error": "Missing or empty 'text' in input"}

        # Load model if not already
        model_backend = load_model()

        # Generate audio
        runpod_logger.info(f"Generating audio for text: {text[:50]}...")
        audio_bytes = model_backend.generate_audio_bytes(
            text=text,
            voice=voice,
            speed=speed,
            response_format="mp3"
        )
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        runpod_logger.info("Audio generated successfully")
        return {
            "output": {
                "status": "success",
                "audio_b64": audio_b64,
                "length_bytes": len(audio_bytes)
            }
        }
    except Exception as e:
        runpod_logger.error(f"Handler error: {str(e)}")
        return {"error": str(e)}  # Graceful fail—job marks as FAILED but logs the why

# Start the serverless worker
runpod.serverless.start({"handler": handler})
