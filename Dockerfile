# Use NVIDIA's official CUDA image with Ubuntu
FROM nvidia/cuda:12.2.0-base-ubuntu22.04

# Install Python, FFmpeg, and NVIDIA's FFmpeg headers
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    libva-drm2 \
    libva2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the Flask port
EXPOSE 8080

# Command to run the application
CMD ["python3", "app.py"]
