FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

USER root

# Update package list and install pip (already there, but safe to keep)
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Activate the existing virtualenv and install everything we need
# → runpod + azure-storage-blob + your existing packages
RUN . /app/.venv/bin/activate && \
    uv pip install --no-cache runpod pydub nest-asyncio azure-storage-blob==12.23.1

WORKDIR /app

# Copy your updated handler.py (with Azure upload)
COPY handler.py .

EXPOSE 8000

# Run the handler directly (same as before)
CMD ["python", "-u", "handler.py"]
