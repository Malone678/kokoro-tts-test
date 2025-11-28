FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Install system deps for pip3 (fixes "pip not found" and PEP 668)
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip git curl && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Install RunPod SDK
RUN pip install --no-cache-dir --break-system-packages runpod==0.8.0

# Copy the proxy handler
WORKDIR /app
COPY handler.py .

# Start Kokoro FastAPI server in background (port 8880), then your handler (port 8000)
EXPOSE 8880 8000
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port 8880 & sleep 5 && python -u handler.py"]
