FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Only thing we need: install runpod into the image's existing virtual environment
RUN . /app/.venv/bin/activate && \
    pip install --no-cache-dir runpod==0.8.0

WORKDIR /app
COPY handler.py .

EXPOSE 8000
CMD ["python", "-u", "handler.py"]
