# app.py
from flask import Flask, request, jsonify, send_from_directory
from priority_engine import compute_priority
import uuid
import json
import os
from datetime import datetime

STORE_FILE = "requests_store.json"
FRONTEND_DIR = "frontend"

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/frontend")

def load_store():
    if not os.path.exists(STORE_FILE):
        return []
    with open(STORE_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_store(data):
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

def normalize_request_payload(payload: dict) -> dict:
    out = {
        "request_id": payload.get("request_id") or f"REQ-{uuid.uuid4().hex[:8].upper()}",
        "origin": payload.get("origin", ""),
        "destination": payload.get("destination", ""),
        "mission_type": payload.get("mission_type", "Routine"),
        "urgency": payload.get("urgency", "P3"),
        "convoy_class": payload.get("convoy_class", ""),
        "risk_zone": payload.get("risk_zone", "Low"),
        "civil_impact": payload.get("civil_impact", "Low"),
        "earliest_start": payload.get("earliest_start", ""),
        "latest_arrival": payload.get("latest_arrival", ""),
        "special_flags": payload.get("special_flags") or [],
        "requested_by": payload.get("requested_by", ""),
        "created_at": datetime.utcnow().isoformat()
    }
    if not isinstance(out["special_flags"], list):
        out["special_flags"] = [out["special_flags"]]
    return out

@app.route("/")
def index():
    # serve the UI
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/request", methods=["POST"])
def create_request():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"JSON payload required"}), 400

    req = normalize_request_payload(payload)
    store = load_store()
    # check duplicate ID
    if any(r.get("request_id") == req["request_id"] for r in store):
        return jsonify({"error":"request_id already exists"}), 400

    # compute priority
    priority_info = compute_priority({
        "request_id": req["request_id"],
        "mission_type": req["mission_type"],
        "urgency": req["urgency"],
        "risk_zone": req["risk_zone"],
        "civil_impact": req["civil_impact"],
        "special_flags": req["special_flags"]
    })
    req["priority"] = priority_info
    store.append(req)
    save_store(store)
    return jsonify(req), 201

@app.route("/requests", methods=["GET"])
def list_requests():
    store = load_store()
    # update priority (in case config changed) and sort by score
    for r in store:
        r["priority"] = compute_priority({
            "request_id": r["request_id"],
            "mission_type": r.get("mission_type", "Routine"),
            "urgency": r.get("urgency", "P3"),
            "risk_zone": r.get("risk_zone", "Low"),
            "civil_impact": r.get("civil_impact", "Low"),
            "special_flags": r.get("special_flags", [])
        })
    sorted_store = sorted(store, key=lambda x: x["priority"]["score"], reverse=True)
    return jsonify(sorted_store)

@app.route("/request/<request_id>", methods=["GET"])
def get_request(request_id):
    store = load_store()
    row = next((r for r in store if r.get("request_id") == request_id), None)
    if not row:
        return jsonify({"error":"not found"}), 404
    row["priority"] = compute_priority({
        "request_id": row["request_id"],
        "mission_type": row.get("mission_type", "Routine"),
        "urgency": row.get("urgency", "P3"),
        "risk_zone": row.get("risk_zone", "Low"),
        "civil_impact": row.get("civil_impact", "Low"),
        "special_flags": row.get("special_flags", [])
    })
    return jsonify(row)

@app.route("/request/<request_id>", methods=["DELETE"])
def delete_request(request_id):
    """
    Delete a request from store (used when convoy is completed/removed).
    """
    store = load_store()
    new_store = [r for r in store if r.get("request_id") != request_id]
    if len(new_store) == len(store):
        return jsonify({"error": "not found"}), 404
    save_store(new_store)
    return jsonify({"deleted": request_id}), 200

if __name__ == "__main__":
    if not os.path.exists(STORE_FILE):
        save_store([])
    app.run(host="127.0.0.1", port=5000, debug=True)
