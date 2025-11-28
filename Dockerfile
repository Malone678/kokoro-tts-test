FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Install system deps for pip3 (fixes "pip not found" and PEP 668)
# It seems these might already be in the base image, but it's safe to keep for compatibility.
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip git curl && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Install RunPod SDK (no-cache to avoid cache issues)
# Using --break-system-packages is necessary in newer Debian/Ubuntu images
RUN pip install --no-cache-dir --break-system-packages runpod==0.8.0

# Copy the proxy handler
WORKDIR /app
COPY handler.py .

EXPOSE 8000

# Start ONLY the handler. The handler.py script manages the FastAPI server internally.
CMD ["python", "-u", "handler.py"]
