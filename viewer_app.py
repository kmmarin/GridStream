from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

# Path to the shared config file
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
            # Only show streams intended to be running
            if config.get("should_be_running"):
                fields = config.get("fields", {})
                available.append({
                    "id": sid,
                    "name": fields.get("stream_name", f"Stream {sid}"),
                    "source": fields.get("destination", ""), # Using destination as the ID/Source
                    "preview_url": f"/preview/gs_{sid}.m3u8"
                })
        return jsonify(available)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
