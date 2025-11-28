FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Install system deps if needed (base has Python/pip)
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
COPY handler.py .

# Switch back to non-root for security (matches base)
USER appuser  # Or whatever non-root user base uses; fallback to root if error

EXPOSE 8880 8000
CMD ["python", "-u", "handler.py"]
