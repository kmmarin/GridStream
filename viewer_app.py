from flask import Flask, render_template, jsonify, request
import json
import os

app = Flask(__name__)

# Paths to the shared config files
CONFIG_FILE = "streams.json"
LAYOUTS_FILE = "layouts.json"
STATE_FILE = "state.json"

def load_json(filepath, default):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try:
                return json.load(f)
            except:
                return default
    return default

@app.route("/")
def index():
    return render_template("viewer.html")

@app.route("/api/available_streams")
def get_streams():
    """Fetches active streams from the encoder's config"""
    data = load_json(CONFIG_FILE, {})
    available = []
    for sid, config in data.items():
        # Only show streams that are currently enabled/running
        if config.get("should_be_running"):
            f = config.get("fields", {})
            dest = f.get("destination", "")
            
            # Extract IP/Host from destination (rtsp://172.16.0.137:8554 -> 172.16.0.137)
            try:
                host = dest.split("://")[1].split(":")[0]
            except:
                host = "localhost"
                
            # Construct the HLS URL for the browser player
            hls_url = f"http://{host}:8888/{f.get('stream_name')}/index.m3u8"
            
            available.append({
                "id": sid, 
                "name": f.get("stream_name"), 
                "url": hls_url, 
                "source": f.get("input")
            })
    return jsonify(available)

@app.route("/api/layouts", methods=["GET", "POST"])
def manage_layouts():
    """Saves and loads named grid presets"""
    layouts = load_json(LAYOUTS_FILE, {})
    if request.method == "POST":
        data = request.json
        layouts[data['name']] = data['streams']
        with open(LAYOUTS_FILE, "w") as f:
            json.dump(layouts, f, indent=4)
        return jsonify({"status": "success"})
    return jsonify(layouts)

@app.route("/api/state", methods=["GET", "POST"])
def manage_state():
    """Remembers what is currently on the user's screen"""
    if request.method == "POST":
        state = request.json
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
        return jsonify({"status": "saved"})
    return jsonify(load_json(STATE_FILE, {"streams": []}))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
