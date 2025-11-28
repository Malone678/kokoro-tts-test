FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Switch to root to install packages system-wide
USER root

# Install runpod into the container’s main Python environment
RUN pip install --no-cache-dir runpod==0.8.0

# Go back to the normal user (appuser) that the base image expects
USER appuser

# Copy your proxy handler
WORKDIR /app
COPY handler.py .

# Expose only the RunPod port (Kokoro runs on 8880 internally)
EXPOSE 8000

# Start BOTH services correctly:
# 1. Kokoro FastAPI on port 8880 (background)
# 2. Your RunPod handler on port 8000 (foreground)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8880 & sleep 10 && python -u handler.py"]
