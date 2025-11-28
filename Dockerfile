FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Switch to root so we can install packages
USER root

# The remsky image has Python 3.10 but NO pip and NO git → install them
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip git && \
    rm -rf /var/lib/apt/lists/*

# Install runpod using pip3 (pip does not exist yet)
RUN pip3 install --no-cache-dir runpod==0.8.0

# Switch back to the non-root user that the base image expects
# (this is important – otherwise uvicorn will refuse to start)
USER appuser

# Your proxy handler
WORKDIR /app
COPY handler.py .

# Only expose the RunPod port (Kokoro server stays internal on 8880)
EXPOSE 8000

# Start Kokoro server first (background), wait a few seconds, then start your handler
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8880 & sleep 12 && python -u handler.py"]
