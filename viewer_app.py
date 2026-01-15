from flask import Flask, render_template, jsonify, request
import json, os

app = Flask(__name__)

CONFIG_FILE = "streams.json"
LAYOUTS_FILE = "layouts.json"
STATE_FILE = "state.json"

def load_json(fp, default):
    if os.path.exists(fp):
        with open(fp, "r") as f:
            try: return json.load(f)
            except: return default
    return default

@app.route("/")
def index(): return render_template("viewer.html")

@app.route("/api/available_streams")
def get_streams():
    data = load_json(CONFIG_FILE, {})
    available = []
    for sid, config in data.items():
        if config.get("should_be_running"):
            f = config.get("fields", {})
            dest = f.get("destination", "rtsp://localhost:8554")
            s_name = f.get("stream_name", "unknown")
            host = dest.split("://")[1].split(":")[0] if "://" in dest else "localhost"
            hls_url = f"http://{host}:8888/{s_name}/index.m3u8"
            available.append({
                "id": sid, "name": s_name, "url": hls_url,
                "display_info": f"Server: {dest} | Path: /{s_name}"
            })
    return jsonify(available)

@app.route("/api/layouts", methods=["GET", "POST"])
def manage_layouts():
    layouts = load_json(LAYOUTS_FILE, {})
    if request.method == "POST":
        layouts[request.json['name']] = request.json['streams']
        with open(LAYOUTS_FILE, "w") as f: json.dump(layouts, f, indent=4)
        return jsonify({"status": "success"})
    return jsonify(layouts)

@app.route("/api/delete_layout", methods=["POST"])
def delete_layout():
    layouts = load_json(LAYOUTS_FILE, {})
    name = request.json.get('name')
    if name in layouts:
        del layouts[name]
        with open(LAYOUTS_FILE, "w") as f: json.dump(layouts, f, indent=4)
    return jsonify({"status": "deleted"})

@app.route("/api/state", methods=["GET", "POST"])
def manage_state():
    if request.method == "POST":
        with open(STATE_FILE, "w") as f: json.dump(request.json, f)
        return jsonify({"status": "saved"})
    return jsonify(load_json(STATE_FILE, {"streams": []}))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
