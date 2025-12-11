# rules_engine.py
# Person 2 will import and use these helper functions in routing_engine.py or app.py
# Keep this file small and dependency-free so it is easy to test and integrate.

from typing import Tuple, Dict, Any

# Tuning constants (edit in tuning_log.md instead of hardcoding later)
RISK_HARD_LIMIT = 0.95
PRIORITY_ALLOWANCE_MINUTES_FACTOR = 8.0  # used by routing to compute priority allowance (backend)
TRAFFIC_PENALTY = {0: 0, 1: 5, 2: 15}  # minutes-equivalent penalty for traffic levels
RISK_PENALTY_FACTOR = 20.0  # multiply risk_level by this to get minutes-equivalent
CIVIL_IMPACT_PENALTY = {"Low": 0.0, "Medium": 5.0, "High": 15.0}

def apply_hard_rules(convoy: Dict[str, Any], segment: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Returns (allowed, reason). If allowed==False, reason contains the rule name.
    convoy: object with keys like 'convoy_class','weight_tons','height_m','width_m','priority_class','special_flags'
    segment: object with keys like 'max_load_tons','max_height_m','max_width_m','allowed_convoy_classes','is_blocked','risk_level','civil_impact'
    """
    # 1. Blocked segment
    if segment.get("is_blocked", False):
        return False, "blocked_segment"

    # 2. Load capacity
    if "weight_tons" in convoy and "max_load_tons" in segment:
        try:
            if float(convoy["weight_tons"]) > float(segment["max_load_tons"]):
                return False, "load_capacity_exceeded"
        except Exception:
            pass

    # 3. Height / Width clearance
    if "height_m" in convoy and "max_height_m" in segment:
        try:
            if float(convoy["height_m"]) > float(segment["max_height_m"]):
                return False, "height_clearance"
        except Exception:
            pass

    if "width_m" in convoy and "max_width_m" in segment:
        try:
            if float(convoy["width_m"]) > float(segment["max_width_m"]):
                return False, "width_clearance"
        except Exception:
            pass

    # 4. Convoy class allowed
    allowed = segment.get("allowed_convoy_classes", ["Light", "Medium", "Heavy"])
    convoy_class = convoy.get("convoy_class", "Light")
    if convoy_class not in allowed:
        return False, "convoy_class_not_allowed"

    # 5. Extreme risk hard cutoff
    if "risk_level" in segment:
        try:
            if float(segment["risk_level"]) >= RISK_HARD_LIMIT:
                # allow emergency medical override
                if convoy.get("priority_class") == "P1" and convoy.get("special_flags") and "medical" in convoy.get("special_flags"):
                    # allow but still flag: emergency_medical_override
                    return True, "emergency_medical_override"
                return False, "high_risk_cutoff"
        except Exception:
            pass

    # 6. Extreme weather + sensitivity
    # (backend should set segment["is_blocked"] when weather blocks; this is a safety net)
    if segment.get("weather_sensitivity", 0.0) >= 0.5 and segment.get("weather_blocked", False):
        return False, "weather_blocked"

    # default allowed
    return True, None


def apply_soft_rules(convoy: Dict[str, Any], segment: Dict[str, Any]) -> float:
    """
    Returns a numeric weight modifier (positive number) that backend will ADD to the EdgeCost.
    Higher modifier -> less desirable.
    Soft rules:
      - traffic_level penalty
      - risk penalty (proportional to risk_level)
      - civil impact penalty depending on priority_class
    """
    weight = 0.0

    # traffic penalty (minutes-equivalent)
    traffic_level = int(segment.get("traffic_level", 0))
    weight += TRAFFIC_PENALTY.get(traffic_level, 0)

    # risk penalty (minutes-equivalent)
    risk_level = float(segment.get("risk_level", 0.0))
    weight += risk_level * RISK_PENALTY_FACTOR

    # civil impact penalty (higher for P3)
    civil = segment.get("civil_impact", "Low")
    base_civil_pen = CIVIL_IMPACT_PENALTY.get(civil, 0.0)

    priority = convoy.get("priority_class", "P3")
    if priority == "P1":
        # P1 less penalized
        weight += base_civil_pen * 0.2
    elif priority == "P2":
        weight += base_civil_pen * 0.6
    else:  # P3
        weight += base_civil_pen

    # special flags: medical convoys get preference (reduce weight)
    flags = convoy.get("special_flags", []) or []
    if "medical" in flags:
        weight -= 10.0  # a flat preference; tuning can change this

    # ensure non-negative
    if weight < 0:
        weight = 0.0

    return weight


def segment_allowed_for_convoy(convoy: Dict[str, Any], segment: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Convenience wrapper: applies hard rules first, returns (allowed, reason).
    If allowed==False -> backend must skip the edge.
    """
    allowed, reason = apply_hard_rules(convoy, segment)
    return allowed, reason


# Quick test helpers (not executed on import)
if __name__ == "__main__":
    # tiny local sanity test
    sample_convoy = {"convoy_class": "Heavy", "weight_tons": 22.0, "height_m": 3.2, "width_m": 3.5, "priority_class": "P2", "special_flags": []}
    sample_segment = {"segment_id": "F-G", "max_load_tons": 20, "max_height_m": 3.0, "max_width_m": 3.2, "allowed_convoy_classes": ["Light"], "is_blocked": False, "risk_level": 0.3, "traffic_level": 2, "civil_impact": "High"}
    print("Hard allowed?", apply_hard_rules(sample_convoy, sample_segment))
    print("Soft weight:", apply_soft_rules(sample_convoy, sample_segment))
