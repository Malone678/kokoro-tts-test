import runpod
import base64
import os
import sys

# Add the 'src' directory to the Python path so we can import internal modules
sys.path.append(os.path.join(os.getcwd(), 'api', 'src'))

# Import the necessary backend class directly from the pre-baked image's code
from inference.kokoro_v1 import KokoroV1 

# Initialize the model backend once globally, outside the handler function
# This is crucial for GPU apps to load the model just once during cold start.
model_backend = KokoroV1() 

def handler(event):
    input_data = event['input']
    text = input_data.get('text', '')
    voice = input_data.get('voice', 'af_bella')
    speed = input_data.get('speed', 1.0)
    
    # Call the internal Python function directly, no requests.post needed
    # The generate_audio_bytes function handles the TTS generation
    audio_bytes = model_backend.generate_audio_bytes(
        text=text, 
        voice=voice, 
        speed=speed,
        response_format="mp3"
    )

    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    return {
        "output": {
            "status": "success",
            "audio_b64": audio_b64,
            "length_bytes": len(audio_bytes)
        }
    }

# This starts the RunPod serverless worker.
runpod.serverless.start({"handler": handler})
