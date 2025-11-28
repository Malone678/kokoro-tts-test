FROM ghcr.io/remsky/kokoro-fastapi-gpu:latest

# Install Python and pip first (base image missing them in PATH)
USER root
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*
RUN ln -s /usr/bin/python3 /usr/bin/python  # Symlink for compatibility
RUN python -m pip install --upgrade pip

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY handler.py .

EXPOSE 8880 8000
CMD ["python", "-u", "handler.py"]
