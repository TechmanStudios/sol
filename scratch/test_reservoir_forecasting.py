#!/usr/bin/env python3
"""
SOL Physical Reservoir Computing Scaling Benchmark
===================================================
1. Generates the chaotic Mackey-Glass time series.
2. Spawns pocket manifolds (sizes N = 64, 128, 256) with native background connections.
3. Feeds the time series as a continuous wave drive into a high-degree source node:
   rho_sa(t) = 10.0 + drive_amplitude * u(t)
4. Simulates fluid wave propagation step-by-step under RK4 integration.
5. Collects the states (densities) of all nodes in the manifold.
6. Trains a linear readout weights vector using Ridge Regression on a training set.
7. Evaluates the forecasting accuracy (NRMSE, R2 score) on a testing set.
8. Demonstrates that forecasting accuracy scales positively with manifold size.
"""

import sys
import os
import math
import time
from pathlib import Path
import networkx as nx
import numpy as np

# Path configurations
_SOL_ROOT = Path(__file__).resolve().parent.parent

# Force bind tools/sol-core/telemetry.py to sys.modules['telemetry'] to prevent collisions
import importlib.util
telemetry_path = _SOL_ROOT / "tools" / "sol-core" / "telemetry.py"
spec = importlib.util.spec_from_file_location("telemetry", telemetry_path)
if spec and spec.loader:
    telemetry_mod = importlib.util.module_from_spec(spec)
    sys.modules["telemetry"] = telemetry_mod
    spec.loader.exec_module(telemetry_mod)
    telemetry_mod._TELEMETRY_ENABLED = False

sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA"))

from blank_config import BlankManifoldConfig
from blank_manifold_core import BlankManifoldCore
from sol_engine import SOLEngine

# ---------------------------------------------------------------------------
# Vectorized Substrate Compilation Patches (Imported for speed)
# ---------------------------------------------------------------------------
def optimized_build_edges(self):
    nodes = list(self.graph.nodes(data=True))
    node_count = len(nodes)
    if node_count == 0:
        return
    connection_threshold = 0.5
    coords = np.array([data["coords"] for node_id, data in nodes])
    dists = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    mask = (dists < connection_threshold) & (np.triu(np.ones(dists.shape), k=1) > 0)
    i_indices, j_indices = np.where(mask)
    for idx in range(len(i_indices)):
        i = i_indices[idx]
        j = j_indices[idx]
        self.graph.add_edge(nodes[i][0], nodes[j][0], weight=self.config.baseline_coupling, distance=float(dists[i, j]))
    isolates = list(nx.isolates(self.graph))
    if isolates:
        self._connect_isolates(isolates)
    if not nx.is_connected(self.graph):
        self._connect_components()

def optimized_connect_isolates(self, isolates):
    nodes_data = list(self.graph.nodes(data=True))
    for node_id in isolates:
        coords = np.array(self.graph.nodes[node_id]["coords"])
        nearest_node = None
        nearest_distance = float("inf")
        for candidate_id, data in nodes_data:
            if candidate_id == node_id:
                continue
            candidate_coords = np.array(data["coords"])
            distance = float(np.linalg.norm(coords - candidate_coords))
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_node = candidate_id
        if nearest_node is not None:
            self.graph.add_edge(node_id, nearest_node, weight=self.config.baseline_coupling, distance=nearest_distance, repaired=True)

def optimized_connect_components(self):
    components = list(nx.connected_components(self.graph))
    if len(components) <= 1:
        return
    for i in range(len(components) - 1):
        left = list(components[i])
        right = list(components[i+1])
        best_pair = None
        best_distance = float("inf")
        for left_node in left[:5]:
            left_coords = np.array(self.graph.nodes[left_node]["coords"])
            for right_node in right[:5]:
                right_coords = np.array(self.graph.nodes[right_node]["coords"])
                distance = float(np.linalg.norm(left_coords - right_coords))
                if distance < best_distance:
                    best_distance = distance
                    best_pair = (left_node, right_node)
        if best_pair:
            self.graph.add_edge(best_pair[0], best_pair[1], weight=self.config.baseline_coupling, distance=best_distance, repaired=True)

BlankManifoldCore._build_edges = optimized_build_edges
BlankManifoldCore._connect_isolates = optimized_connect_isolates
BlankManifoldCore._connect_components = optimized_connect_components

# ---------------------------------------------------------------------------
# Mackey-Glass Generator
# ---------------------------------------------------------------------------
def generate_mackey_glass(length=700, tau=17, seed=42):
    """Generates Mackey-Glass chaotic time-series using Euler discretization."""
    np.random.seed(seed)
    history = list(1.2 + 0.1 * np.random.randn(tau))
    x = history.copy()
    for _ in range(length + 200): # Warm up
        x_tau = x[-tau]
        x_t = x[-1]
        dx = (0.2 * x_tau) / (1.0 + x_tau**10) - 0.1 * x_t
        x.append(x_t + dx)
    
    # Return normalized time series to [0, 1] range
    u = np.array(x[200:])
    u_min, u_max = u.min(), u.max()
    return (u - u_min) / (u_max - u_min)

# ---------------------------------------------------------------------------
# Benchmark Logic
# ---------------------------------------------------------------------------
def evaluate_manifold_reservoir(N: int, u: np.ndarray, dt: float) -> dict:
    # 1. Spawn Pocket Manifold
    t0 = time.perf_counter()
    config = BlankManifoldConfig(base_node_count=N, topology_type="hyperbolic_uniform", dimensionality=3)
    secondary = BlankManifoldCore(config, seed=42)
    secondary_graph = secondary.generate_manifold()
    compile_time = (time.perf_counter() - t0) * 1000.0
    
    # Select highest-degree node as the input source
    nodes_by_degree = sorted(list(secondary_graph.nodes()), key=lambda n: (secondary_graph.degree(n), n), reverse=True)
    sa = nodes_by_degree[0]
    
    # 2. Initialize SOLEngine
    raw_nodes = [{"id": n, "label": n, "group": "bridge", "rho": 10.0} for n in secondary_graph.nodes]
    raw_edges = [{"from": u_edge, "to": v_edge, "w0": secondary_graph[u_edge][v_edge].get("weight", 0.1), "kind": "tax"} for u_edge, v_edge in secondary_graph.edges]
    
    # Low damping (0.01) to allow waves to reverberate and act as memory
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0, damping=0.01)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    engine.physics.conductance_min = 0.1  # Native coupling kept going!
    engine.physics.conductance_max = 5.0
    engine.physics.mhd_cfg = None
    engine.physics.jeans_cfg = None
    engine.physics.vort_cfg = None
    
    # 3. Simulate and collect reservoir states
    drive_amplitude = 1.0
    states = []
    
    t_start_sim = time.perf_counter()
    for t_idx in range(len(u)):
        # Drive input node dynamically
        engine.physics.node_by_id[sa]["rho"] = 10.0 + drive_amplitude * u[t_idx]
        engine.step(dt=dt)
        # Record density states of all nodes in reservoir
        states.append([n["rho"] for n in engine.physics.nodes])
        
    sim_time = (time.perf_counter() - t_start_sim) * 1000.0
    states = np.array(states) # Shape: (T, N)
    
    # 4. Readout Training & Testing Splits
    # Washout: 100 steps
    # Train: 100 to 450 (350 steps)
    # Test: 450 to 699 (249 steps)
    washout = 100
    train_end = 450
    
    X_train = states[washout:train_end]
    y_train = u[washout+1:train_end+1] # Predict u(t+1)
    
    X_test = states[train_end:-1]
    y_test = u[train_end+1:]
    
    # Hstack ones to include bias term
    X_train_bias = np.hstack([X_train, np.ones((X_train.shape[0], 1))])
    X_test_bias = np.hstack([X_test, np.ones((X_test.shape[0], 1))])
    
    # 5. Ridge Regression Readout Training: W = (X^T X + lambda I)^-1 X^T y
    n_features = X_train_bias.shape[1]
    reg_lambda = 1e-6
    W = np.linalg.solve(X_train_bias.T @ X_train_bias + reg_lambda * np.eye(n_features), X_train_bias.T @ y_train)
    
    # 6. Evaluation
    y_pred = X_test_bias @ W
    
    # NRMSE calculation
    mean_y_test = np.mean(y_test)
    rmse = np.sqrt(np.mean((y_test - y_pred)**2))
    nrmse = rmse / np.std(y_test)
    
    # R2 calculation
    ss_res = np.sum((y_test - y_pred)**2)
    ss_tot = np.sum((y_test - mean_y_test)**2)
    r2 = 1.0 - (ss_res / ss_tot)
    
    return {
        "N": N,
        "edges": len(raw_edges),
        "compile_time_ms": compile_time,
        "sim_time_ms": sim_time,
        "nrmse": nrmse,
        "r2": r2,
        "y_test": y_test,
        "y_pred": y_pred
    }

def main():
    print("==========================================================================", flush=True)
    print("  EXCITON-MOA PHYSICAL RESERVOIR COMPUTING BENCHMARK (MACKEY-GLASS)", flush=True)
    print("==========================================================================", flush=True)
    
    # Generate the time series
    u = generate_mackey_glass(length=700, tau=17, seed=42)
    print(f"Generated Mackey-Glass chaotic sequence of length {len(u)} steps.", flush=True)
    
    sizes = [64, 128, 256]
    dt = 0.08
    results = []
    
    for N in sizes:
        print(f"\n[BENCHMARK] Simulating Physical Reservoir on manifold size N = {N}...", flush=True)
        res = evaluate_manifold_reservoir(N, u, dt)
        print(f"  -> Manifold compiled in {res['compile_time_ms']:.2f} ms with {res['edges']} active connections.", flush=True)
        print(f"  -> Reservoir simulated in {res['sim_time_ms']:.2f} ms ({res['sim_time_ms']/len(u):.2f} ms/step).", flush=True)
        print(f"  -> Forecasting Results: NRMSE = {res['nrmse']:.6f} | R2 Score = {res['r2']*100.0:.4f}%", flush=True)
        results.append(res)
        
    print("\n==========================================================================", flush=True)
    print("  SUMMARY LEDGER", flush=True)
    print("==========================================================================", flush=True)
    print(f"{'Nodes (N)':<10} | {'Edges (E)':<10} | {'Compile (ms)':<15} | {'Sim (ms)':<15} | {'NRMSE':<12} | {'R2 Score (%)':<12}", flush=True)
    print("-" * 88, flush=True)
    for r in results:
        print(f"{r['N']:<10} | {r['edges']:<10} | {r['compile_time_ms']:<15.2f} | {r['sim_time_ms']:<15.2f} | {r['nrmse']:<12.6f} | {r['r2']*100.0:.4f}%", flush=True)
    print("==========================================================================", flush=True)

if __name__ == "__main__":
    main()
