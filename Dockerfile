FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Switch to root to install packages (required for this base image)
USER root

# Upgrade pip and install our deps (force break PEP 668 – safe in container)
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir runpod requests fastapi uvicorn pydantic --break-system-packages

# Copy our handler
WORKDIR /app
COPY handler.py .

# Stay as root (Kokoro image works fine as root in serverless)
EXPOSE 8880 8000
CMD ["python", "-u", "handler.py"]
