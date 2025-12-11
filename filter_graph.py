#!/usr/bin/env python3
"""
filter_graph.py
Small utility to apply rules_engine.segment_allowed_for_convoy() to the person3_world/graph.json
Usage:
  # 1) using a convoy json file
  python filter_graph.py --convoy person3_world/sample_convoy.json

  # 2) or pass raw JSON on stdin:
  cat some_convoy.json | python filter_graph.py

Output:
  - writes person3_world/filtered_graph_<convoy_id>.json (nodes + allowed segments)
  - writes person3_world/filter_log_<convoy_id>.json (reasons for exclusions)
"""

import json
import argparse
import sys
from pathlib import Path

# import from rules_engine (assumes rules_engine.py exists in repo root)
from rules_engine import segment_allowed_for_convoy

REPO_ROOT = Path(__file__).resolve().parent
WORLD_DIR = REPO_ROOT / "person3_world"
GRAPH_PATH = WORLD_DIR / "graph.json"

def load_graph():
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def filter_graph_for_convoy(convoy: dict, graph: dict):
    # copy nodes as-is
    nodes = graph.get("nodes", [])
    segments = graph.get("segments", [])

    allowed_segments = []
    excluded_segments = []

    for seg in segments:
        allowed, reason = segment_allowed_for_convoy(convoy, seg)
        if allowed:
            allowed_segments.append(seg)
        else:
            excluded = dict(seg)
            excluded["_rejection_reason"] = reason
            excluded_segments.append(excluded)

    filtered = {"nodes": nodes, "segments": allowed_segments}
    log = {"convoy_id": convoy.get("convoy_id", "unknown"),
           "allowed_count": len(allowed_segments),
           "excluded_count": len(excluded_segments),
           "excluded_segments": excluded_segments}
    return filtered, log

def main():
    parser = argparse.ArgumentParser(description="Filter graph.json for a given convoy using rules_engine.")
    parser.add_argument("--convoy", "-c", type=str, help="Path to convoy JSON file. If omitted reads from stdin.")
    parser.add_argument("--out-prefix", "-o", type=str, default=None, help="Optional output prefix (default uses convoy_id).")
    args = parser.parse_args()

    # read convoy
    if args.convoy:
        convoy_path = Path(args.convoy)
        if not convoy_path.exists():
            print(f"Convoy file not found: {convoy_path}", file=sys.stderr)
            sys.exit(2)
        convoy = json.loads(convoy_path.read_text(encoding="utf-8"))
    else:
        # read from stdin
        raw = sys.stdin.read()
        if not raw.strip():
            print("No convoy input provided on stdin. Provide --convoy or pipe JSON.", file=sys.stderr)
            sys.exit(2)
        convoy = json.loads(raw)

    # load graph
    graph = load_graph()

    filtered_graph, log = filter_graph_for_convoy(convoy, graph)

    prefix = args.out_prefix or convoy.get("convoy_id", "convoy")
    filtered_path = WORLD_DIR / f"filtered_graph_{prefix}.json"
    log_path = WORLD_DIR / f"filter_log_{prefix}.json"

    save_json(filtered_graph, filtered_path)
    save_json(log, log_path)

    print(f"Filtered graph written to: {filtered_path}")
    print(f"Filter log written to: {log_path}")
    print(f"Allowed segments: {log['allowed_count']}, Excluded: {log['excluded_count']}")

if __name__ == "__main__":
    main()
