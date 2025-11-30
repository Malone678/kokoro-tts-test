FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

USER root

# Install system pip (safe)
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Install runpod and pydub (for MP3 conversion) into the uv venv
RUN . /app/.venv/bin/activate && \
    uv pip install --no-cache runpod pydub

WORKDIR /app
COPY handler.py .

EXPOSE 8000
CMD ["python", "-u", "handler.py"]
