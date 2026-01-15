# GridStream

**GridStream** is a high-performance, web-based FFmpeg orchestrator and multi-view dashboard. It is designed to manage, transcode, and monitor multiple RTSP/RTMP streams through a centralized interface.

Built for efficiency, GridStream allows you to relay video feeds while keeping a close eye on system performance and stream health.

## ✨ Key Features

* **Dual-App Architecture:** Separate interfaces for **Encoder Management** (Port 8080) and **Multi-View Monitoring** (Port 8081).
* **Hardware Acceleration:** Native support for **NVIDIA NVENC** (H264/HEVC).
    * *Note: NVIDIA hardware is optional. If no GPU is present, streams can be set to "Copy" codec or modified for CPU encoding.*
* **Reactive Multi-Viewer:** A dedicated viewer with a persistent sidebar, "Open All" capabilities, and real-time stream inventory updates.
* **Custom Layouts:** Create, save, and delete custom camera grids. GridStream remembers your last active view even after a browser refresh.
* **Real-time Diagnostics:** Monitor CPU, RAM, and NVIDIA GPU load/temperature alongside raw FFmpeg console logs.
* **Auto-Healing:** Background monitoring automatically restarts crashed streams marked as "Should be running."
* **Persistent Storage:** All configurations and layouts are saved to JSON files, ensuring your setup survives container restarts.

---

## 🚀 Getting Started
### Accessing the Apps
Encoder Dashboard: http://<ip-address>:8080 — Add, edit, and start your FFmpeg processes.

Reactive Viewer: http://<ip-address>:8081 — Build and save your multi-camera monitoring grids.

🛠 Configuration
streams.json: Stores the master list of camera inputs, encoder settings (bitrate, fps, codec), and current run-state.

layouts.json: Stores your custom-named viewer grids, allowing you to switch between "Security Desk," "Outside Perimeter," or "Workroom" views instantly.

state.json: Automatically tracks which streams are currently visible on your Viewer dashboard to restore your session upon reload.

📝 Usage Notes
Codec Support: When adding a stream, selecting h264 or hevc will trigger nvenc hardware acceleration. Use copy for zero-latency, low-CPU relaying.

Network: Ensure the destination RTSP URL is reachable by your Media Server (e.g., MediaMTX) to allow the Viewer to generate HLS segments.

### Prerequisites
* Docker and Docker Compose.
* **For NVIDIA Encoding:**
    * An NVIDIA GPU with latest drivers.
    * [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed.
### To install without NVIDIA
Comment out these lines in the docker compose file

#    deploy:
#      resources:
#        reservations:
#          devices:
#            - driver: nvidia
#              count: all
#              capabilities: [gpu, video]

### Installation

```bash
git clone https://github.com/kmmarin/GridStream.git
cd GridStream
docker compose build
docker compose up -d
