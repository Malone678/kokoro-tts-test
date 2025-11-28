FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Install system deps (pip3 alias if missing; matches remsky's apt setup)
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip git && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Install Python deps with pip3 (explicit, as in remsky's Dockerfile)
RUN pip3 install --no-cache-dir runpod==0.8.0 requests==2.32.3 fastapi==0.115.0 uvicorn==0.30.6 pydantic==2.9.2

# Copy handler
WORKDIR /app
COPY handler.py .

EXPOSE 8880 8000
CMD ["python", "-u", "handler.py"]
