from typing import Dict
import json
import os

# default (fallback) maps
DEFAULT_CONFIG = {
    "URGENCY_MAP": {"P1": 100, "P2": 70, "P3": 40},
    "MISSION_MAP": {
        "Medical": 40,
        "Ammo": 35,
        "Fuel": 30,
        "TroopMove": 25,
        "Routine": 10
    },
    "RISK_MAP": {"High": 30, "Medium": 20, "Low": 10},
    "CIVIL_MAP": {"High": 30, "Medium": 20, "Low": 10},
    "SPECIAL_MAP": {"medical": 30, "VIP": 20, "training": -10, "no-night": 0},
    "WEIGHTS": {"wU": 0.5, "wM": 0.2, "wR": 0.2, "wC": 0.1}
}

CONFIG_PATH = "config.json"

def load_config():
    """
    Load config.json if present; otherwise return DEFAULT_CONFIG.
    Returns dict of maps and weights.
    """
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # minimal sanity: ensure WEIGHTS exist
            if "WEIGHTS" not in cfg:
                cfg["WEIGHTS"] = DEFAULT_CONFIG["WEIGHTS"]
            return cfg
        except Exception as e:
            print(f"[priority_engine] failed to load config.json ({e}), using defaults.")
            return DEFAULT_CONFIG
    else:
        return DEFAULT_CONFIG

def compute_priority(request: Dict) -> Dict:
    """
    Compute PriorityScore for a request using current config.
    Returns dict: { request_id, score, label, components }
    """
    cfg = load_config()
    URGENCY_MAP = cfg.get("URGENCY_MAP", DEFAULT_CONFIG["URGENCY_MAP"])
    MISSION_MAP = cfg.get("MISSION_MAP", DEFAULT_CONFIG["MISSION_MAP"])
    RISK_MAP = cfg.get("RISK_MAP", DEFAULT_CONFIG["RISK_MAP"])
    CIVIL_MAP = cfg.get("CIVIL_MAP", DEFAULT_CONFIG["CIVIL_MAP"])
    SPECIAL_MAP = cfg.get("SPECIAL_MAP", DEFAULT_CONFIG["SPECIAL_MAP"])
    WEIGHTS = cfg.get("WEIGHTS", DEFAULT_CONFIG["WEIGHTS"])

    U = URGENCY_MAP.get(request.get("urgency", "P3"), 40)
    M = MISSION_MAP.get(request.get("mission_type", "Routine"), 10)
    R = RISK_MAP.get(request.get("risk_zone", "Low"), 10)
    C = CIVIL_MAP.get(request.get("civil_impact", "Low"), 10)
    flags = request.get("special_flags", []) or []
    S = sum(SPECIAL_MAP.get(f, 0) for f in flags)

    raw = WEIGHTS["wU"] * U + WEIGHTS["wM"] * M + WEIGHTS["wR"] * R - WEIGHTS["wC"] * C + S
    score = int(max(0, min(100, round(raw))))
    if score >= 80:
        label = "P1"
    elif score >= 50:
        label = "P2"
    else:
        label = "P3"

    return {
        "request_id": request.get("request_id"),
        "score": score,
        "label": label,
        "components": {
            "U": U, "M": M, "R": R, "C": C, "S": S, "raw": raw
        }
    }

# debug run
if __name__ == "__main__":
    demo = {
        "request_id": "REQ-DEMO-1",
        "mission_type": "Medical",
        "urgency": "P1",
        "risk_zone": "High",
        "civil_impact": "Low",
        "special_flags": ["medical"]
    }
    import json
    print(json.dumps(compute_priority(demo), indent=2))
