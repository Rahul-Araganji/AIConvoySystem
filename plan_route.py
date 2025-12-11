#!/usr/bin/env python3
"""
plan_route.py
Simple planner: runs filter_graph -> routing_engine on the filtered graph and emits a single plan file.

Usage:
  python plan_route.py --convoy person3_world/sample_convoy.json
  python plan_route.py --convoy person3_world/sample_convoy.json --out-prefix MYRUN
Outputs:
  - person3_world/plan_<convoy_id>.json  (contains filter_log + route result)
  - person3_world/filtered_graph_<convoy_id>.json (created by filter step)
  - person3_world/filter_log_<convoy_id>.json (created by filter step)
  - person3_world/route_<convoy_id>.json (created by routing step)
  - person3_world/route_log_<convoy_id>.json (created by routing step)
"""

import json
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
WORLD_DIR = REPO_ROOT / "person3_world"

# reuse existing modules
from rules_engine import segment_allowed_for_convoy
from routing_engine import compute_route  # compute_route(convoy, graph) -> result dict
from filter_graph import load_graph, save_json, filter_graph_for_convoy

def plan_for_convoy(convoy: dict, graph: dict, out_prefix: str = None):
    convoy_id = convoy.get("convoy_id", out_prefix or "convoy")
    prefix = out_prefix or convoy_id

    # 1) Filter graph using the same function as filter_graph.py
    filtered_graph, filter_log = filter_graph_for_convoy(convoy, graph)
    filtered_path = WORLD_DIR / f"filtered_graph_{prefix}.json"
    filter_log_path = WORLD_DIR / f"filter_log_{prefix}.json"
    save_json(filtered_graph, filtered_path)
    save_json(filter_log, filter_log_path)

    # 2) Run routing on filtered graph (A* expects the same graph structure)
    route_result = compute_route(convoy, filtered_graph)
    # compute_route already returns a dict with success or reason

    # 3) Save route result (compute_route does not save by itself when used as function)
    route_path = WORLD_DIR / f"route_{prefix}.json"
    route_log_path = WORLD_DIR / f"route_log_{prefix}.json"
    with open(route_path, "w", encoding="utf-8") as f:
        json.dump(route_result, f, indent=2)
    with open(route_log_path, "w", encoding="utf-8") as f:
        json.dump({"convoy_id": convoy_id, "result": route_result}, f, indent=2)

    # 4) Merge outputs into one plan file for convenience
    plan = {
        "convoy_id": convoy_id,
        "filter_log": filter_log,
        "route_result": route_result
    }
    plan_path = WORLD_DIR / f"plan_{prefix}.json"
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)

    return {
        "plan_path": str(plan_path),
        "filter_path": str(filtered_path),
        "filter_log_path": str(filter_log_path),
        "route_path": str(route_path),
        "route_log_path": str(route_log_path),
        "plan_summary": {
            "convoy_id": convoy_id,
            "route_success": route_result.get("success", False),
            "eta_minutes": route_result.get("eta_minutes"),
            "total_risk": route_result.get("total_risk")
        }
    }

def main():
    parser = argparse.ArgumentParser(description="Plan route for a convoy: filter graph + compute route.")
    parser.add_argument("--convoy", "-c", type=str, help="Path to convoy JSON file. If omitted reads from stdin.")
    parser.add_argument("--out-prefix", "-o", type=str, help="Optional prefix for output files.")
    args = parser.parse_args()

    if args.convoy:
        convoy = json.loads(Path(args.convoy).read_text(encoding="utf-8"))
    else:
        raw = sys.stdin.read()
        convoy = json.loads(raw)

    graph = load_graph()
    out = plan_for_convoy(convoy, graph, out_prefix=args.out_prefix)
    print("Plan files written:")
    for k, v in out.items():
        if k.endswith("_path") or k.endswith("_path"):
            print(f" - {k}: {v}")
    print("Plan summary:", out["plan_summary"])

if __name__ == "__main__":
    main()
