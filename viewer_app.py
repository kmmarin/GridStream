from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

CONFIG_FILE = "streams.json"

@app.route("/")
def index():
    return render_template("viewer.html")

@app.route("/api/available_streams")
def get_streams():
    if not os.path.exists(CONFIG_FILE):
        return jsonify([])

    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            
        available = []
        for sid, config in data.items():
            # Only show streams that are actually set to be running
            if config.get("should_be_running"):
                fields = config.get("fields", {})
                stream_name = fields.get("stream_name", "")
                destination = fields.get("destination", "")

                # Logic: Convert RTSP dest to HLS URL
                # If dest is rtsp://172.16.0.137:8554, HLS is http://172.16.0.137:8888/stream_name
                if "://" in destination:
                    parts = destination.split("://")[1].split(":")[0]
                    hls_url = f"http://{parts}:8888/{stream_name}/index.m3u8"
                    
                    available.append({
                        "id": sid,
                        "name": stream_name,
                        "url": hls_url
                    })
        return jsonify(available)
    except Exception as e:
        print(f"Viewer Error: {e}")
        return jsonify([])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
