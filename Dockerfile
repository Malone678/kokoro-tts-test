FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip && \
    rm -rf /var/lib/apt/lists/*

RUN . /app/.venv/bin/activate && \
    uv pip install --no-cache runpod pydub nest-asyncio

WORKDIR /app
COPY handler.py .

EXPOSE 8000
CMD ["python", "-u", "handler.py"]
