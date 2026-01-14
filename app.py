from flask import Flask, render_template, request, redirect, url_for, jsonify
import subprocess
import threading
import os
import psutil
import json

app = Flask(__name__)

CONFIG_FILE = "streams.json"
streams = {} 

def save_to_disk():
    """Saves configuration to JSON file with sorted keys for readability"""
    data = {}
    for sid, s in streams.items():
        data[str(sid)] = {
            "id": int(sid),
            "fields": s["fields"],
            "saved": s.get("saved", True),
            "should_be_running": s.get("should_be_running", False)
        }
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4, sort_keys=True)

def load_from_disk():
    """Loads config and ensures all IDs are handled as integers"""
    global streams
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                content = f.read().strip()
                saved_data = json.loads(content) if content else {}
                
                for sid_str, s in saved_data.items():
                    sid_int = int(sid_str)
                    # Sync internal dict
                    streams[sid_int] = {
                        "id": sid_int,
                        "fields": s["fields"],
                        "saved": s.get("saved", True),
                        "should_be_running": s.get("should_be_running", False),
                        "proc": None, 
                        "log": [], 
                        "rtsp": None
                    }
                    if streams[sid_int].get("should_be_running"):
                        start_stream(streams[sid_int])
        except Exception as e:
            print(f"Error loading JSON: {e}")

def get_next_id():
    """
    Finds the first available hole in the ID sequence.
    Example: If IDs are 1, 2, 3, 7, 9 -> This returns 4.
    """
    existing_ids = sorted(streams.keys())
    if not existing_ids:
        return 1
    
    # Check for holes starting from 1
    candidate = 1
    while candidate in existing_ids:
        candidate += 1
    return candidate

def get_system_stats():
    """Captures CPU, RAM, and NVIDIA GPU metrics"""
    stats = {"cpu": psutil.cpu_percent(), "ram": psutil.virtual_memory().percent}
    try:
        gpu_out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"], 
            encoding='utf-8'
        )
        load, temp = gpu_out.strip().split(',')
        stats["gpu_load"] = f"{load.strip()}%"
        stats["gpu_temp"] = f"{temp.strip()}°C"
    except:
        stats["gpu_load"] = "N/A"
        stats["gpu_temp"] = "N/A"
    return stats

def read_ffmpeg_output(stream_id, proc):
    """Background thread to capture FFmpeg logs"""
    for line in proc.stderr:
        if stream_id in streams:
            streams[stream_id]["log"].append(line.rstrip())
            if len(streams[stream_id]["log"]) > 100:
                streams[stream_id]["log"].pop(0)

def build_ffmpeg_cmd(cfg):
    """Constructs the FFmpeg command for RTSP relay"""
    rtsp_url = f"{cfg['destination']}/{cfg['stream_name']}"
    v_codec = "h264_nvenc" if cfg["codec"] == "h264" else "hevc_nvenc" if cfg["codec"] == "hevc" else "copy"
    
    cmd = ["ffmpeg", "-y", "-rtsp_transport", "tcp", "-i", cfg["input"], "-c:v", v_codec]
    
    if cfg["codec"] != "copy":
        if cfg.get("bitrate"): cmd += ["-b:v", cfg["bitrate"] + "k"]
        if cfg.get("fps"): cmd += ["-r", cfg["fps"]]
    
    cmd += ["-f", "rtsp", "-rtsp_transport", "tcp", rtsp_url]
    return cmd, rtsp_url

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "add":
            sid = get_next_id()
            streams[sid] = {
                "id": sid, "proc": None, "log": [], "saved": True, 
                "fields": {
                    "destination": "rtsp://172.16.0.137:8554", 
                    "codec": "copy", 
                    "stream_name": f"stream_{sid}", 
                    "input": ""
                }
            }
            save_to_disk()
            return redirect(url_for("index", active_tab=sid))
        
        sid_val = request.form.get("stream_id")
        if not sid_val:
            return redirect(url_for("index"))
            
        sid = int(sid_val)
        s = streams.get(sid)
        if not s: return redirect(url_for("index"))

        if action in ["start", "save"]:
            s["fields"] = {k: request.form.get(k, "") for k in ["input", "codec", "destination", "stream_name"]}
            s["saved"] = True
            
            if action == "start":
                s["should_be_running"] = True
                start_stream(s)
            
            save_to_disk()
            
        elif action == "stop":
            s["should_be_running"] = False
            if s["proc"]: 
                s["proc"].terminate()
                s["proc"] = None
            save_to_disk()
            
        elif action == "delete":
            if s["proc"]: s["proc"].terminate()
            del streams[sid]
            save_to_disk()
            return redirect(url_for("index"))
            
        return redirect(url_for("index", active_tab=sid))
    
    return render_template("index.html", streams=streams, stats=get_system_stats())

def start_stream(s):
    if s["proc"]: s["proc"].terminate()
    try:
        cmd, rtsp = build_ffmpeg_cmd(s["fields"])
        s["proc"] = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)
        s["rtsp"] = rtsp
        threading.Thread(target=read_ffmpeg_output, args=(s["id"], s["proc"]), daemon=True).start()
    except Exception as e:
        s["log"].append(f"Error starting: {str(e)}")

@app.route("/api/stats")
def api_stats():
    return jsonify(get_system_stats())

@app.route("/api/logs/<int:sid>")
def api_logs(sid):
    if sid in streams:
        return jsonify({"log": streams[sid]["log"], "running": streams[sid]["proc"] is not None})
    return jsonify({"log": [], "running": False})

if __name__ == "__main__":
    load_from_disk()
    app.run(host="0.0.0.0", port=8080)
