FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Activate the base venv and install extra deps (fixes PATH/PEP 668)
USER root
RUN . /app/.venv/bin/activate && \
    pip install --no-cache-dir runpod==0.8.0

# Copy handler
WORKDIR /app
COPY handler.py .

EXPOSE 8880 8000
CMD ["python", "-u", "handler.py"]
