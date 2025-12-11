#!/usr/bin/env python3
"""
routing_engine.py (A* version)
NetworkX-based routing engine using A* with an admissible heuristic derived from the graph's distance_km.
EdgeCost = base_time_min + soft_modifier - priority_allowance.

Usage:
  python routing_engine.py --convoy person3_world/sample_convoy.json
Outputs:
  - person3_world/route_<convoy_id>.json
  - person3_world/route_log_<convoy_id>.json
"""

import json
from pathlib import Path
import argparse
import sys

try:
    import networkx as nx
except Exception as e:
    print("networkx not installed. Run: pip install networkx", file=sys.stderr)
    raise

from rules_engine import apply_soft_rules, PRIORITY_ALLOWANCE_MINUTES_FACTOR

REPO_ROOT = Path(__file__).resolve().parent
WORLD_DIR = REPO_ROOT / "person3_world"
GRAPH_PATH = WORLD_DIR / "graph.json"


def load_graph(path=GRAPH_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_graph(graph: dict):
    """
    Build a NetworkX DiGraph from graph.json structure.
    Create bidirectional edges for each segment; include distance_km and base_time_min attributes.
    """
    G = nx.DiGraph()
    for node in graph.get("nodes", []):
        node_id = node.get("node_id")
        G.add_node(node_id, **node)

    for seg in graph.get("segments", []):
        u = seg["from_node"]
        v = seg["to_node"]
        attrs = dict(seg)
        # add forward and reverse (assume symmetric for demo)
        G.add_edge(u, v, **attrs)
        rev = dict(seg)
        rev["segment_id"] = seg.get("segment_id", f"{u}-{v}") + "_rev"
        # swap from/to in reverse attributes for clarity
        rev["from_node"], rev["to_node"] = v, u
        G.add_edge(v, u, **rev)
    return G


def compute_min_time_per_km(graph: dict):
    """
    Compute optimistic lower bound of time-per-km across all edges:
      min( base_time_min / distance_km )
    If some edges have distance_km==0, handle safely by ignoring those.
    """
    min_ratio = None
    for seg in graph.get("segments", []):
        try:
            d = float(seg.get("distance_km", 0.0))
            t = float(seg.get("base_time_min", 0.0))
            if d > 0:
                ratio = t / d
                if min_ratio is None or ratio < min_ratio:
                    min_ratio = ratio
        except Exception:
            continue
    # fallback if not found
    return float(min_ratio) if min_ratio is not None else 1.0


def precompute_shortest_distance_km(graph: dict):
    """
    Precompute shortest distance_km between all pairs using networkx (Dijkstra on distance_km).
    Returns: dict-of-dicts: dist[u][v] = shortest distance_km (float)
    """
    G = nx.DiGraph()
    for node in graph.get("nodes", []):
        node_id = node.get("node_id")
        G.add_node(node_id)
    for seg in graph.get("segments", []):
        u = seg["from_node"]
        v = seg["to_node"]
        d = float(seg.get("distance_km", 0.0))
        # add both directions for distance metric
        G.add_edge(u, v, distance_km=d)
        G.add_edge(v, u, distance_km=d)
    # compute all-pairs shortest path length (distance_km)
    length = dict(nx.all_pairs_dijkstra_path_length(G, weight="distance_km"))
    return length  # dict: {u: {v: dist_km, ...}, ...}


def edge_cost_for_convoy(convoy: dict, edge_attrs: dict):
    """
    Compute EdgeCost in minutes-equivalent for this convoy on this edge.
    formula:
        base_time_min + soft_modifier - priority_allowance
    """
    base_time = float(edge_attrs.get("base_time_min", 0.0))
    soft = apply_soft_rules(convoy, edge_attrs)
    priority_score = float(convoy.get("priority_score", 0.0))
    priority_allowance = (priority_score / 100.0) * float(PRIORITY_ALLOWANCE_MINUTES_FACTOR)
    raw_cost = base_time + soft - priority_allowance
    cost = max(0.1, raw_cost)
    return cost


def compute_route(convoy: dict, graph: dict):
    """
    Compute best path from convoy['origin'] to convoy['destination'] using A*.
    Returns result dict similar to prior version.
    """
    # build the graph and useful structures
    G = build_graph(graph)
    origin = convoy.get("origin")
    destination = convoy.get("destination")
    if origin not in G.nodes or destination not in G.nodes:
        return {"success": False, "reason": "invalid_origin_or_destination", "origin": origin, "destination": destination}

    # precompute shortest distance_km between nodes for heuristic
    dist_km_all = precompute_shortest_distance_km(graph)
    min_time_per_km = compute_min_time_per_km(graph)

    # define heuristic function for networkx.astar_path: h(u) = min_time_per_km * shortest_distance_km[u][destination]
    def heuristic(u, v=destination):
        try:
            dkm = dist_km_all.get(u, {}).get(v, float("inf"))
            if dkm == float("inf"):
                return 0.0
            return float(min_time_per_km) * float(dkm)
        except Exception:
            return 0.0

    # annotate edges with computed cost for this convoy
    for u, v, data in G.edges(data=True):
        if data.get("is_blocked", False):
            data["cost"] = float("inf")
        else:
            data["cost"] = edge_cost_for_convoy(convoy, data)

    # Use networkx astar_path with 'cost' as edge weight and provided heuristic
    try:
        path_nodes = nx.astar_path(G, source=origin, target=destination, heuristic=heuristic, weight="cost")
    except nx.NetworkXNoPath:
        return {"success": False, "reason": "no_path", "origin": origin, "destination": destination}

    # collect route metrics
    route_segments = []
    eta = 0.0
    total_risk = 0.0
    cost_breakdown = []
    for i in range(len(path_nodes) - 1):
        u = path_nodes[i]
        v = path_nodes[i + 1]
        edge = G[u][v]
        seg_id = edge.get("segment_id", f"{u}-{v}")
        seg_base = float(edge.get("base_time_min", 0.0))
        seg_cost = float(edge.get("cost", seg_base))
        seg_risk = float(edge.get("risk_level", 0.0))
        eta += seg_cost
        total_risk += seg_risk
        route_segments.append({
            "segment_id": seg_id,
            "from": u,
            "to": v,
            "base_time_min": seg_base,
            "computed_cost": seg_cost,
            "risk_level": seg_risk
        })
        cost_breakdown.append({"segment": seg_id, "cost": seg_cost, "risk": seg_risk})

    result = {
        "success": True,
        "convoy_id": convoy.get("convoy_id"),
        "origin": origin,
        "destination": destination,
        "route_nodes": path_nodes,
        "route_segments": route_segments,
        "eta_minutes": round(eta, 2),
        "total_risk": round(total_risk, 3),
        "cost_breakdown": cost_breakdown
    }
    return result


def save_route_result(convoy_id: str, result: dict):
    prefix = convoy_id or "convoy"
    route_path = WORLD_DIR / f"route_{prefix}.json"
    log_path = WORLD_DIR / f"route_log_{prefix}.json"
    with open(route_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"convoy_id": convoy_id, "result": result}, f, indent=2)
    return route_path, log_path


def main():
    parser = argparse.ArgumentParser(description="Compute route for convoy using routing_engine (A*).")
    parser.add_argument("--convoy", "-c", type=str, help="Path to convoy JSON file. If omitted reads from stdin.")
    parser.add_argument("--graph", "-g", type=str, help="Optional graph JSON to use (default person3_world/graph.json)")
    args = parser.parse_args()

    if args.convoy:
        convoy = json.loads(Path(args.convoy).read_text(encoding="utf-8"))
    else:
        raw = sys.stdin.read()
        convoy = json.loads(raw)

    graph_path = Path(args.graph) if args.graph else GRAPH_PATH
    graph = json.loads(graph_path.read_text(encoding="utf-8"))

    res = compute_route(convoy, graph)
    convoy_id = convoy.get("convoy_id", "convoy")
    route_path, log_path = save_route_result(convoy_id, res)
    print(f"Route written to: {route_path}")
    print(f"Log written to: {log_path}")
    if not res.get("success"):
        print("Routing failed:", res.get("reason"))


if __name__ == "__main__":
    main()
