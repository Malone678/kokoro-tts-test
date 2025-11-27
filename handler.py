import runpod
import json
import requests
from pydantic import BaseModel

class TTSRequest(BaseModel):
    text: str  # Your 15-min script here
    voice: str = "af_bella"  # Default voice
    speed: float = 1.0

def generate_tts(text: str, voice: str = "af_bella", speed: float = 1.0) -> bytes:
    # Internal call to Kokoro endpoint (runs on same container)
    payload = {
        "model": "kokoro",
        "input": text,
        "voice": voice,
        "response_format": "mp3",
        "speed": speed
    }
    response = requests.post("http://localhost:8880/v1/audio/speech", json=payload)
    response.raise_for_status()
    return response.content  # MP3 bytes

def handler(event):
    try:
        data = json.loads(event['input'])
        req = TTSRequest(**data)
        audio_bytes = generate_tts(req.text, req.voice, req.speed)
        # Return base64 or direct bytes; for test, return success
        return {
            "output": {
                "status": "success",
                "audio_length_bytes": len(audio_bytes),
                "message": "15-min audio generated!"
            },
            "delay_time": 0  # For async
        }
    except Exception as e:
        return {"output": {"error": str(e)}, "delay_time": 0}

# Start serverless
runpod.serverless.start({"handler": handler})