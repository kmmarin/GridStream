from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import subprocess
import threading
import os
import itertools
import psutil
import json
import time

app = Flask(__name__)

# GridStream Configuration
PREVIEW_DIR = "/tmp/gridstream_preview"
CONFIG_FILE = "streams.json"
os.makedirs(PREVIEW_DIR, exist_ok=True)

stream_id_counter = itertools.count(1)
streams = {} 

def save_to_disk():
    """Persists GridStream configurations to streams.json"""
    if os.path.isdir(CONFIG_FILE): return
    data = {}
    for sid, s in streams.items():
        data[sid] = {
            "id": s["id"],
            "fields": s["fields"],
            "saved": s.get("saved", False),
            "show_preview": s.get("show_preview", True),
            "show_console": s.get("show_console", True),
            "should_be_running": s.get("should_be_running", False)
        }
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_from_disk():
    """Initializes GridStream from existing config on startup"""
    global streams, stream_id_counter
    if os.path.exists(CONFIG_FILE) and os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved_data = json.load(f)
                highest_id = 0
                for sid, s in saved_data.items():
                    sid_int = int(sid)
                    streams[sid_int] = {
                        **s, "proc": None, "log": [], "rtsp": None, 
                        "preview": None, "cmd": None, "error": None
                    }
                    if sid_int > highest_id: highest_id = sid_int
                    if streams[sid_int].get("should_be_running"):
                        start_stream(streams[sid_int])
                stream_id_counter = itertools.count(highest_id + 1)
        except Exception as e:
            print(f"GridStream Load Error: {e}")

def get_system_stats():
    stats = {"cpu": psutil.cpu_percent(), "ram": psutil.virtual_memory().percent, 
             "net_sent": round(psutil.net_io_counters().bytes_sent / (1024 * 1024), 2),
             "gpu_load": "N/A", "gpu_temp": "N/A"}
    try:
        gpu_out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
            encoding='utf-8'
        )
        load, temp = gpu_out.strip().split(',')
        stats["gpu_load"] = f"{load.strip()}%"; stats["gpu_temp"] = f"{temp.strip()}°C"
    except: pass 
    return stats

def auto_restart_monitor():
    """GridStream Heartbeat: Ensures persistent streams stay alive"""
    while True:
        time.sleep(10)
        for s in list(streams.values()):
            if s.get("should_be_running") and (s.get("proc") is None or s["proc"].poll() is not None):
                start_stream(s)

def read_ffmpeg_output(stream_id, proc):
    for line in proc.stderr:
        if stream_id in streams:
            streams[stream_id]["log"].append(line.rstrip())
            if len(streams[stream_id]["log"]) > 300: streams[stream_id]["log"].pop(0)

def build_ffmpeg_cmd(cfg, stream_id):
    rtsp_url = f"{cfg['destination']}/{cfg['stream_name']}.sdp"
    preview_file = f"gs_{stream_id}.m3u8"
    preview_path = f"{PREVIEW_DIR}/{preview_file}"
    
    v_codec = "h264_nvenc" if cfg["codec"] == "h264" else "hevc_nvenc" if cfg["codec"] == "hevc" else "copy"
    cmd = ["ffmpeg", "-y", "-i", cfg["input"], "-c:v", v_codec]
    if cfg["codec"] != "copy":
        if cfg.get("bitrate"): cmd += ["-b:v", cfg["bitrate"] + "k"]
        if cfg.get("fps"): cmd += ["-r", cfg["fps"]]
    
    cmd += ["-f", "rtsp", rtsp_url, "-f", "hls", "-hls_time", "1", "-hls_list_size", "3", 
            "-hls_flags", "delete_segments+append_list+temp_file", preview_path]
    return cmd, rtsp_url, preview_file

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "start_all":
            for s in streams.values():
                if s["saved"]:
                    s["should_be_running"] = True
                    start_stream(s)
            save_to_disk()
            return redirect(url_for("index", active_tab="dashboard"))
        
        if action == "stop_all":
            for s in streams.values():
                s["should_be_running"] = False
                stop_stream(s)
            save_to_disk()
            return redirect(url_for("index", active_tab="dashboard"))

        if action == "add":
            sid = next(stream_id_counter)
            streams[sid] = {"id": sid, "proc": None, "log": [], "saved": False, "rtsp": None, 
                            "preview": None, "cmd": None, "error": None, "show_preview": True, 
                            "show_console": True, "should_be_running": False,
                            "fields": {"destination": "rtsp://localhost:8554", "codec": "copy", "stream_name": f"stream_{sid}", "input": "", "bitrate": "", "fps": ""}}
            save_to_disk()
            return redirect(url_for("index", active_tab=sid))
        
        sid_raw = request.form.get("stream_id")
        if not sid_raw: return redirect(url_for("index"))
        sid = int(sid_raw)
        stream = streams[sid]
        
        if action == "start":
            stream["fields"] = {k: request.form.get(k, "") for k in ["input", "codec", "bitrate", "fps", "destination", "stream_name"]}
            stream["should_be_running"] = True
            start_stream(stream)
            save_to_disk()
        elif action == "stop":
            stream["should_be_running"] = False
            stop_stream(stream)
            save_to_disk()
        elif action == "save":
            stream["fields"] = {k: request.form.get(k, "") for k in ["input", "codec", "bitrate", "fps", "destination", "stream_name"]}
            stream["saved"] = True
            save_to_disk()
        elif action == "toggle_preview":
            stream["show_preview"] = not stream.get("show_preview", True)
            save_to_disk()
        elif action == "toggle_console":
            stream["show_console"] = not stream.get("show_console", True)
            save_to_disk()
        elif action == "delete":
            stop_stream(stream)
            streams.pop(sid, None)
            save_to_disk()
            return redirect(url_for("index", active_tab="dashboard"))
        return redirect(url_for("index", active_tab=sid))
    return render_template("index.html", streams=streams, active_tab=request.args.get('active_tab', 'dashboard'))

def start_stream(stream):
    stop_stream(stream)
    try:
        cmd, rtsp, preview = build_ffmpeg_cmd(stream["fields"], stream["id"])
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
        stream.update({"proc": proc, "cmd": " ".join(cmd), "rtsp": rtsp, "preview": preview, "log": []})
        threading.Thread(target=read_ffmpeg_output, args=(stream["id"], proc), daemon=True).start()
    except Exception as e:
        stream["error"] = str(e)

def stop_stream(stream):
    if stream.get("proc"):
        stream["proc"].terminate()
        stream["proc"] = None

# API ENDPOINT FOR GRIDSTREAMVIEWER
@app.route("/api/streams")
def api_list_streams():
    """Returns a list of active streams for the Mosaic Viewer"""
    active_streams = []
    for sid, s in streams.items():
        # Check if process is running and HLS preview exists
        if s.get("proc") and s["proc"].poll() is None and s.get("preview"):
            active_streams.append({
                "id": sid,
                "name": s["fields"]["stream_name"],
                "preview_url": f"/preview/{s['preview']}"
            })
    return jsonify(active_streams)

@app.route("/api/stats")
def api_stats():
    active_map = {sid: (s["proc"] is not None and s["proc"].poll() is None) for sid, s in streams.items()}
    return jsonify({"system": get_system_stats(), "active_count": sum(active_map.values()), "active_map": active_map})

@app.route("/logs/<int:sid>")
def logs(sid):
    return jsonify(streams[sid]["log"]) if sid in streams else jsonify([])

@app.route("/preview/<path:filename>")
def preview(filename):
    return send_from_directory(PREVIEW_DIR, filename)

if __name__ == "__main__":
    load_from_disk()
    threading.Thread(target=auto_restart_monitor, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
