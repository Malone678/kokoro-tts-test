FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Install extra deps directly to venv pip (no activate – fixes PATH in RUN)
USER root
RUN /app/.venv/bin/pip install --no-cache-dir runpod==0.8.0

# Copy handler
WORKDIR /app
COPY handler.py .

EXPOSE 8880 8000
CMD ["python", "-u", "handler.py"]
