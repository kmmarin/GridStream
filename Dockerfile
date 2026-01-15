FROM python:3.11-slim

# Install FFmpeg and system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default port for the main encoder (can be overridden in compose)
EXPOSE 8080
EXPOSE 8081

# Default command (The compose file overrides this for the viewer)
CMD ["python3", "app.py"]
