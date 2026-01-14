# GridStream

**GridStream** is a high-performance, web-based FFmpeg orchestrator designed to manage multiple RTSP/RTMP streams with full **NVIDIA NVENC** hardware acceleration. 



Built for efficiency, GridStream allows you to transcode, relay, and monitor multiple video feeds through a single dashboard while keeping CPU usage minimal by offloading video processing to the GPU.

## ✨ Key Features

* **NVIDIA NVENC Integration:** Fully optimized for H.264 and HEVC (H.265) hardware encoding.
* **Real-time Dashboard:** Monitor System CPU, RAM, and Network usage alongside NVIDIA GPU load and temperature.
* **Live Stream Previews:** Side-by-side view of a fixed-size (320x200) live HLS preview and raw FFmpeg console output.
* **Auto-Healing:** A background monitor automatically restarts any failed or crashed streams if they were marked as "Started."
* **Persistent Configuration:** All stream settings are saved to `streams.json`, allowing the system to automatically resume active streams after a reboot.
* **Global Controls:** Start all saved encoders or stop every active stream with one click.

## 🚀 Getting Started

### Prerequisites
* An NVIDIA GPU with the latest drivers.
* [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed.
* Docker and Docker Compose.

### Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/kmmarin/GridStream.git](https://github.com/kmmarin/GridStream.git)
   cd GridStream
   docker compose up -d --build
   docker compose up -d
