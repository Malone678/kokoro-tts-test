FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Switch to root and unblock pip (fixes PEP 668 / externally-managed error)
USER root
RUN rm -f /usr/lib/python3.*/EXTERNALLY-MANAGED

# Install deps (no requirements.txt needed – direct for faster build)
RUN pip install --no-cache-dir runpod==0.8.0 requests==2.32.3 fastapi==0.115.0 uvicorn==0.30.6 pydantic==2.9.2

# Copy handler
WORKDIR /app
COPY handler.py .

EXPOSE 8880 8000
CMD ["python", "-u", "handler.py"]
