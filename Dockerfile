FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

USER root

# 1. Make sure system python/pip exist (just in case)
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip && \
    rm -rf /var/lib/apt/lists/*

# 2. Install runpod into the existing uv-managed virtual environment using uv (not pip!)
RUN . /app/.venv/bin/activate && \
    uv pip install --no-cache runpod==0.8.0

WORKDIR /app
COPY handler.py .

EXPOSE 8000
CMD ["python", "-u", "handler.py"]
