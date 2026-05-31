#!/usr/bin/env python3
"""
SOL ICAC Fibonacci Scaling Experiment
=====================================
1. Spawns pocket manifolds (nSpawn) of sizes N = 64, 256, 1024, 2048.
2. Selects 3 high-degree hub nodes for the addition circuit (Source A, Source B, Mixer).
3. Surgically adds direct symmetrical waveguide edges with high weight (w0 = 5.0).
4. Simulates autonomous wormhole seeding of the Giants.
5. Calibrates the waveguide gain factor.
6. Computes the Fibonacci sequence (F0 to F20) using physical constructive interference.
7. Logs accuracy and scales metrics.
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
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA" / "hardWare"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA" / "firmWare" / "ExcitonEngine"))

from blank_config import BlankManifoldConfig
from blank_manifold_core import BlankManifoldCore

# ---------------------------------------------------------------------------
# Monkey Patch BlankManifoldCore & ExcitonEngine
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

from excitons import ExcitonEngine

def optimized_graph_navigator_hyperbolic_flow(self, epicenter_id: str):
    neighbors = list(self.manifold.neighbors(epicenter_id))
    local_cycles = [
        (epicenter_id, neighbors[i], neighbors[j])
        for i in range(len(neighbors))
        for j in range(i + 1, len(neighbors))
        if self.manifold.has_edge(neighbors[i], neighbors[j])
    ]
    residual_flux_total = 0.0
    if local_cycles:
        unique_edges = set()
        for a, b, c in local_cycles:
            for u, v in [(a, b), (b, c), (c, a)]:
                unique_edges.add(tuple(sorted((u, v))))
        for u, v in unique_edges:
            self.manifold[u][v]["residual_flux"] = self.manifold[u][v].get("residual_flux", 0.0) + 0.5
            self.manifold[u][v]["weight"] = self.manifold[u][v].get("weight", 0.1) * 0.8
            residual_flux_total += self.manifold[u][v]["residual_flux"]
    return float(len(local_cycles)), float(residual_flux_total)

ExcitonEngine._graph_navigator_hyperbolic_flow = optimized_graph_navigator_hyperbolic_flow

from sol_engine import SOLEngine

# ---------------------------------------------------------------------------
# Trial & Evaluator functions
# ---------------------------------------------------------------------------
def run_addition_trial(engine: SOLEngine, sa: str, sb: str, mixer: str,
                       amp_a: float, amp_b: float, dt: float, steps: int) -> float:
    engine.restore_baseline()
    omega = 2.0 * math.pi / (12.0 * dt)
    mixer_rhos = []
    
    # Run integration steps
    for s in range(steps):
        t = s * dt
        # Drive Source A and Source B in-phase (constructive interference)
        engine.physics.node_by_id[sa]["rho"] = 10.0 + amp_a * math.sin(omega * t)
        engine.physics.node_by_id[sb]["rho"] = 10.0 + amp_b * math.sin(omega * t)
        
        engine.step(dt=dt)
        
        # Log Mixer rho in steady state (last 15 steps)
        if s >= steps - 15:
            mixer_rhos.append(engine.physics.node_by_id[mixer]["rho"])
            
    # Return measured peak-to-peak oscillation amplitude
    return max(mixer_rhos) - min(mixer_rhos)

def run_fibonacci_scaling_sweep():
    print("==========================================================================", flush=True)
    print("  nSPAWN FIBONACCI WAVE-INTERFEROMETRIC SCALING SWEEP", flush=True)
    print("==========================================================================", flush=True)
    
    sizes = [64, 256, 1024, 2048]
    summary_ledger = []
    
    # True Fibonacci numbers to evaluate against: F0 to F20 (21 elements)
    true_fib = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765]
    
    for N in sizes:
        print(f"\n[SIZE SWEEP] Testing Fibonacci addition on manifold size N = {N}...", flush=True)
        
        # 1. Spawn Pocket Manifold
        t0 = time.perf_counter()
        config = BlankManifoldConfig(base_node_count=N, topology_type="hyperbolic_uniform", dimensionality=3)
        secondary = BlankManifoldCore(config, seed=42)
        secondary_graph = secondary.generate_manifold()
        compile_time = (time.perf_counter() - t0) * 1000.0
        print(f"  -> Generated in {compile_time:.2f} ms. Nodes: {secondary_graph.number_of_nodes()}, Edges: {secondary_graph.number_of_edges()}", flush=True)
        
        # 2. Select circuit nodes (top 3 degree hubs for A + B -> Mixer)
        nodes_by_degree = sorted(list(secondary_graph.nodes()), key=lambda n: secondary_graph.degree(n), reverse=True)
        sa, sb, mixer = nodes_by_degree[:3]
        
        # Surgically overwrite/add direct symmetrical edges with high weight
        secondary_graph.add_edge(sa, mixer, weight=5.0)
        secondary_graph.add_edge(sb, mixer, weight=5.0)
        print(f"  -> Symmetrical addition conduits compiled: {sa} -> {mixer} and {sb} -> {mixer} (w = 5.0)", flush=True)
        
        # 3. Simulate autonomous wormhole seeding of Exciton-MoA
        t_seed_start = time.perf_counter()
        giants = ["The Statistician", "The Optimizer", "The N-Body Solver"]
        seeded_nodes = [sa, sb, mixer]
        for idx, node_id in enumerate(seeded_nodes):
            giant_name = giants[idx]
            secondary_graph.nodes[node_id]["dominant_giant"] = giant_name
            secondary_graph.nodes[node_id]["resonance_accumulator"] = 2.0
            secondary_graph.nodes[node_id]["semantic_mode"] = np.array([1.0, 1.0])
            secondary_graph.nodes[node_id]["state_vector"] = np.array([0.0, 0.0, 0.0])
            
        seed_latency = (time.perf_counter() - t_seed_start) * 1000.0
        
        # Ignite Exciton Engine to stabilize the waveguide routing
        exciton_engine = ExcitonEngine(secondary)
        exciton_engine.ignite_excitons(np.array([10.0, 10.0, 10.0]))
        
        # 4. Prepare SOLEngine
        raw_nodes = [{"id": n, "label": n, "group": "bridge", "rho": 10.0} for n in secondary_graph.nodes]
        raw_edges = [{"from": u, "to": v, "w0": secondary_graph[u][v].get("weight", 0.1), "kind": "tax"} for u, v in secondary_graph.edges]
        
        engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0, damping=0.2)
        engine.integration_mode = "forward_euler"
        engine.physics.psi_diffusion = 0.0
        engine.physics.conductance_gamma = 1.0
        engine.physics.mhd_cfg = None
        engine.physics.jeans_cfg = None
        engine.physics.vort_cfg = None
        engine.save_baseline()
        
        # 5. Calibrate Symmetrical Waveguide Gain
        dt = 0.08
        steps = 30
        
        # Drive Source A with 0.1 amplitude, Source B with 0.0
        v_a = run_addition_trial(engine, sa, sb, mixer, 0.1, 0.0, dt, steps)
        # Drive Source B with 0.1 amplitude, Source A with 0.0
        v_b = run_addition_trial(engine, sa, sb, mixer, 0.0, 0.1, dt, steps)
        
        symmetry_diff = abs(v_a - v_b) / max(1e-6, max(v_a, v_b))
        gain = (v_a + v_b) / 0.2  # Average gain per unit amplitude
        
        print(f"  -> Calibration: Gain = {gain:.6f}, Symmetry Mismatch = {symmetry_diff*100.0:.2f}%", flush=True)
        
        # 6. Compute Fibonacci sequence F0 to F20 (21 elements)
        computed_fib = [0, 1]
        t_eval_start = time.perf_counter()
        
        print("  -> Computing Fibonacci sequence...", flush=True)
        print(f"    n= 0 | Expected: 0 | Computed: 0 | Match: True", flush=True)
        print(f"    n= 1 | Expected: 1 | Computed: 1 | Match: True", flush=True)
        
        passed_count = 2  # F0 and F1 are hardcoded boundary conditions
        
        for n in range(2, len(true_fib)):
            f_prev1 = computed_fib[n-1]
            f_prev2 = computed_fib[n-2]
            
            # 1. Analog scaling: map inputs to safe log-safe amplitudes (max sum = 0.2)
            max_val = max(f_prev1, f_prev2)
            k_scale = 0.1 / max(max_val, 1.0)
            
            amp_a = f_prev1 * k_scale
            amp_b = f_prev2 * k_scale
            
            # 2. Run SOL physics simulation to perform wave addition
            v_mixer = run_addition_trial(engine, sa, sb, mixer, amp_a, amp_b, dt, steps)
            
            # 3. De-scale and round output
            raw_sum = v_mixer / (gain * k_scale)
            computed_val = int(round(raw_sum))
            computed_fib.append(computed_val)
            
            match = (computed_val == true_fib[n])
            if match:
                passed_count += 1
                
            print(f"    n={n:2d} | Expected: {true_fib[n]:4d} | Computed: {computed_val:4d} | Raw: {raw_sum:8.2f} | Match: {match}", flush=True)
            
        eval_time = (time.perf_counter() - t_eval_start) * 1000.0
        accuracy = (passed_count / len(true_fib)) * 100.0
        print(f"  -> Fibonacci Sequence Accuracy: {accuracy:.1f}% ({passed_count}/{len(true_fib)} correct)", flush=True)
        
        # Profile single step time
        t_step = time.perf_counter()
        engine.step(dt=dt)
        step_time = (time.perf_counter() - t_step) * 1000.0
        
        summary_ledger.append({
            "N": N,
            "edges": len(raw_edges),
            "compile_time_ms": compile_time,
            "seed_latency_ms": seed_latency,
            "eval_time_ms": eval_time,
            "step_ms": step_time,
            "accuracy": accuracy
        })
        
    print("\n==========================================================================", flush=True)
    print("  SUMMARY LEDGER", flush=True)
    print("==========================================================================", flush=True)
    print(f"{'Nodes (N)':<10} | {'Edges (E)':<10} | {'Compile (ms)':<15} | {'Eval (ms)':<15} | {'Euler Step (ms)':<15} | {'Accuracy':<10}", flush=True)
    print("-" * 88, flush=True)
    for r in summary_ledger:
        print(f"{r['N']:<10} | {r['edges']:<10} | {r['compile_time_ms']:<15.2f} | {r['eval_time_ms']:<15.2f} | {r['step_ms']:<15.2f} | {r['accuracy']:.1f}%", flush=True)
    print("==========================================================================", flush=True)

if __name__ == "__main__":
    run_fibonacci_scaling_sweep()
