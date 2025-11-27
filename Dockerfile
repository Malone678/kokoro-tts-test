FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY handler.py .

EXPOSE 8880 8000  # Kokoro + RunPod ports
CMD ["python", "-u", "handler.py"]