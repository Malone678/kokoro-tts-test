import runpod
import requests
import base64
import json

def handler(event):
    input_data = event['input']
    tts_payload = {
        "model": "kokoro",
        "input": input_data.get('text', ''),
        "voice": input_data.get('voice', 'af_bella'),
        "speed": input_data.get('speed', 1.0),
        "response_format": "mp3"
    }
    # Proxy to remsy's baked FastAPI endpoint (runs on localhost:8880)
    response = requests.post("http://localhost:8880/v1/audio/speech", json=tts_payload)
    response.raise_for_status()
    audio_bytes = response.content
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    return {
        "output": {
            "status": "success",
            "audio_b64": audio_b64,
            "length_bytes": len(audio_bytes)
        }
    }

runpod.serverless.start({"handler": handler})
