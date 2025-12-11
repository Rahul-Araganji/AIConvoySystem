
---

# 🚛 AI-Based Convoy Route Planning System

**Rule-Based Filtering • A* Routing • Priority Engine • Frontend UI**

This project is an AI-assisted **transport & road-space management system** designed for logistics and defense operations.
It produces an optimized convoy route using **rule-based constraints**, a **weighted priority model**, and a **custom A*** search engine.

---

## ⭐ Key Features

### **1. Convoy Priority Engine (Weighted Sum Model)**

Assigns priority scores based on:

* Mission type
* Urgency
* Civil impact zone
* Risk zone level
* Special flags (e.g., medical, VIP)

The score influences routing behavior and risk tolerance.

---

### **2. Rule-Based Filtering Engine**

Eliminates all road segments that violate operational constraints:

* Height / width restrictions
* Load capacity limits
* Convoy class compatibility
* Blocked / risky segments
* Traffic or weather penalties

Produces a detailed `filter_log` explaining every decision.

---

### **3. A* Routing Engine**

Computes the best path with multi-factor cost:

* Travel time
* Traffic penalty
* Risk penalty
* Priority allowance

Returns:

* Route nodes
* ETA
* Risk score
* Cost breakdown per segment

---

### **4. Planner Orchestrator**

Pipeline:

```
Convoy Input → Rule Filtering → A* Search → Final Route Plan
```

---

### **5. Backend API (Flask)**

Endpoint:

```
POST /plan_route
```

Returns:

* Filter log
* Route result
* ETA, risk, route nodes
* Summary for UI display

---

### **6. Frontend UI**

Simple HTML + JS interface:

* Input convoy data
* Send request to backend
* View route, logs, and summary

Perfect for live demo during judging.

---

## 📁 Project Structure

```
AIConvoySystem/
│
├── api.py                     # Backend API server
├── plan_route.py              # Pipeline orchestrator
├── filter_graph.py            # Rule-based graph filtering
├── routing_engine.py          # A* routing logic
├── rules_engine.py            # Central rules + scoring
│
├── frontend/
│   └── index.html             # Frontend UI for route planning
│
└── person3_world/
    ├── graph.json             # Road network
    ├── sample_convoy.json     # Example input
    ├── filtered_graph_*.json  # Generated outputs
    ├── filter_log_*.json
    ├── route_*.json
    └── plan_*.json
```

---

## ⚙️ Installation

```bash
python -m pip install flask networkx
```

(Optional but recommended: create a virtual environment.)

---

## 🚀 Running the System

### **1. Start the Backend**

```bash
python api.py
```

Backend will run on:

```
http://127.0.0.1:5001
```

---

### **2. Start the Frontend**

Open another terminal:

```bash
python -m http.server 8080
```

Then open in browser:

```
http://127.0.0.1:8080/frontend/index.html
```

---

## 🧪 Demo Steps (Judges’ Version)

1. Enter convoy details (class, height, weight, priority, origin/destination).
2. Click **Plan Route**.
3. UI shows:

   * **Filter Log** (why roads were rejected)
   * **Route Result** (A* output: nodes, ETA, risk)
   * **Summary** (clean explanation)
4. Modify convoy info → recompute and show different paths.

This demonstrates intelligence + explainability.

---

## 🧠 30-Second Project Explanation

> “We built an AI-aided convoy planning engine.
> It uses a **priority model** to score missions, a **rule engine** to reject unsafe routes, and a **custom A*** algorithm to generate the safest and fastest path.
> The result is a transparent, modular transport-planning tool with a live frontend demo.”

---

## 🏆 Why This Project Stands Out

* Fully explainable routing
* Realistic constraints (load, height, class, risk, traffic)
* Clean modular architecture
* Full end-to-end running system
* Live visual demo
* Extensible for dynamic re-routing or GIS maps

---

## 📌 Future Upgrades

* Real-time incident updates → automatic re-routing
* Multi-convoy deconfliction
* Load consolidation engine
* Integration with real maps (OSM/GIS)
* ML-based priority score tuning

---

## ✔️ End

This repository includes a complete, runnable AI-powered convoy planning system ready for demonstration.

---


