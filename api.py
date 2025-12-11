# api.py — minimal Flask wrapper that exposes planner without touching app.py
from flask import Flask, request, jsonify
import json
import traceback
from pathlib import Path
from flask_cors import CORS

# local imports (these exist in repo)
from filter_graph import load_graph
from plan_route import plan_for_convoy

from flask import send_from_directory
import os



app = Flask(__name__)

# serve the frontend index at root
@app.route("/", methods=["GET"])
def serve_index():
    # if file exists under ./frontend/index.html
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    return send_from_directory(frontend_dir, "index.html")

@app.route("/plan_route", methods=["POST"])
def plan_route_endpoint():
    try:
        convoy = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400
    if not convoy or not isinstance(convoy, dict):
        return jsonify({"error": "Convoy JSON expected in request body"}), 400
    try:
        graph = load_graph()
        out = plan_for_convoy(convoy, graph)
        plan_path = out.get("plan_path")
        if plan_path:
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_json = json.load(f)
            return jsonify(plan_json)
        else:
            return jsonify({"error": "planner_failed", "detail": out}), 500
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500

if __name__ == "__main__":
    # dev server; change host/port if needed
    app.run(host="0.0.0.0", port=5001, debug=True)
