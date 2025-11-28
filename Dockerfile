FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Switch to root so we can install packages
USER root

# The base image already has python3 and pip3 globally — just install runpod
RUN pip3 install --no-cache-dir runpod==0.8.0

# Copy your handler
WORKDIR /app
COPY handler.py .

# Run as the original non-root user (optional but clean)
# USER 1000   # <-- uncomment if you want non-root (works either way)

EXPOSE 8880 8000
CMD ["python", "-u", "handler.py"]
