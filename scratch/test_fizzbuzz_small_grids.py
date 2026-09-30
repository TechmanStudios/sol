#!/usr/bin/env python3
"""
SOL ICAC FizzBuzz Small Grids Experiment (1 to 100)
===================================================
1. Spawns pocket manifolds (nSpawn) of sizes N = 9, 16, 36, 64.
2. Selects 7 high-degree hub nodes for the logic gate circuit.
3. Surgically adds logic waveguide edges and uses Exciton-MoA to guide/carve weights.
4. Drives phase-modulated waves representing modulo-3 and modulo-5 states.
5. Performs wave-interferometric decision checking for Fizz, Buzz, FizzBuzz, and Numbers.
6. Evaluates the full FizzBuzz test from n = 1 to 100.
7. Logs accuracy and benchmarks execution times to study cross-talk and phase leakage.
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
def run_fizzbuzz_trial(engine: SOLEngine, sa: str, sb: str, sbias: str, mixer: str,
                       phase_a: float, phase_b: float, phase_bias: float,
                       dt: float, steps: int) -> float:
    engine.restore_baseline()
    omega = 2.0 * math.pi / (12.0 * dt)
    mixer_rhos = []
    
    for s in range(steps):
        t = s * dt
        engine.physics.node_by_id[sa]["rho"] = 10.0 + 3.0 * math.sin(omega * t + phase_a)
        engine.physics.node_by_id[sb]["rho"] = 10.0 + 3.0 * math.sin(omega * t + phase_b)
        engine.physics.node_by_id[sbias]["rho"] = 10.0 + 3.0 * math.sin(omega * t + phase_bias)
        
        engine.step(dt=dt)
        
        if s >= steps - 15:
            mixer_rhos.append(engine.physics.node_by_id[mixer]["rho"])
            
    return max(mixer_rhos) - min(mixer_rhos)

def run_fizzbuzz_small_grids():
    print("==========================================================================", flush=True)
    print("  nSPAWN FIZZBUZZ SMALL GRIDS SCALING EXPERIMENT (1 to 100)", flush=True)
    print("==========================================================================", flush=True)
    
    sizes = [9, 16, 36, 64]
    summary_ledger = []
    
    for N in sizes:
        print(f"\n[SIZE SWEEP] Testing FizzBuzz on manifold size N = {N}...", flush=True)
        
        # 1. Spawn Pocket Manifold
        t0 = time.perf_counter()
        config = BlankManifoldConfig(base_node_count=N, topology_type="hyperbolic_uniform", dimensionality=3)
        secondary = BlankManifoldCore(config, seed=42)
        secondary_graph = secondary.generate_manifold()
        compile_time = (time.perf_counter() - t0) * 1000.0
        print(f"  -> Generated in {compile_time:.2f} ms. Nodes: {secondary_graph.number_of_nodes()}, Edges: {secondary_graph.number_of_edges()}", flush=True)
        
        # 2. Select circuit nodes (top 7 degree hubs)
        nodes_by_degree = sorted(list(secondary_graph.nodes()), key=lambda n: secondary_graph.degree(n), reverse=True)
        sa, sb, sbias, m_fb, m_f, m_b, m_num = nodes_by_degree[:7]
        
        # Surgically add edges if not present to compile the logic circuit
        logic_connections = 0
        for mixer in [m_fb, m_f, m_b, m_num]:
            for input_node in [sa, sb, sbias]:
                if not secondary_graph.has_edge(input_node, mixer):
                    secondary_graph.add_edge(input_node, mixer, weight=0.1)
                    logic_connections += 1
        print(f"  -> Surgical compilation: added {logic_connections} waveguide edges.", flush=True)
        
        # 3. Simulate autonomous wormhole seeding of Exciton-MoA
        t_seed_start = time.perf_counter()
        giants = [
            "The Statistician", "The Optimizer", "The N-Body Solver",
            "The Graph Navigator", "The Linear Algebraist", "The Aligner", "The Integrator"
        ]
        seeded_nodes = [sa, sb, sbias, m_fb, m_f, m_b, m_num]
        for idx, node_id in enumerate(seeded_nodes):
            giant_name = giants[idx]
            secondary_graph.nodes[node_id]["dominant_giant"] = giant_name
            secondary_graph.nodes[node_id]["resonance_accumulator"] = 2.0  # active & high resonance
            secondary_graph.nodes[node_id]["semantic_mode"] = np.array([1.0, 1.0])
            secondary_graph.nodes[node_id]["state_vector"] = np.array([0.0, 0.0, 0.0])
            
        seed_latency = (time.perf_counter() - t_seed_start) * 1000.0
        
        # Ignite Exciton Engine to carve logic highway
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
        
        # 5. Evaluate FizzBuzz for n = 1 to 100
        passed_count = 0
        total_count = 100
        dt = 0.08
        steps = 30
        
        t_eval_start = time.perf_counter()
        
        print(f"  -> Evaluating full FizzBuzz loop (n = 1..100)...", flush=True)
        for n in range(1, total_count + 1):
            is3 = (n % 3 == 0)
            is5 = (n % 5 == 0)
            
            # Expected string outcome
            if is3 and is5:
                expected = "FizzBuzz"
            elif is3:
                expected = "Fizz"
            elif is5:
                expected = "Buzz"
            else:
                expected = "Num"
                
            # Run the 4 trials
            # FizzBuzz Mixer (m_fb)
            fb_amp = run_fizzbuzz_trial(engine, sa, sb, sbias, m_fb,
                                        math.pi if is3 else 0.0,
                                        math.pi if is5 else 0.0,
                                        math.pi, dt, steps)
            
            # Fizz Mixer (m_f) - inverts Input5
            f_amp = run_fizzbuzz_trial(engine, sa, sb, sbias, m_f,
                                       math.pi if is3 else 0.0,
                                       0.0 if is5 else math.pi,
                                       math.pi, dt, steps)
            
            # Buzz Mixer (m_b) - inverts Input3
            b_amp = run_fizzbuzz_trial(engine, sa, sb, sbias, m_b,
                                       0.0 if is3 else math.pi,
                                       math.pi if is5 else 0.0,
                                       math.pi, dt, steps)
            
            # Num Mixer (m_num) - inverts both
            num_amp = run_fizzbuzz_trial(engine, sa, sb, sbias, m_num,
                                         0.0 if is3 else math.pi,
                                         0.0 if is5 else math.pi,
                                         math.pi, dt, steps)
            
            # Determine physical winner
            amplitudes = {
                "FizzBuzz": fb_amp,
                "Fizz": f_amp,
                "Buzz": b_amp,
                "Num": num_amp
            }
            winner = max(amplitudes, key=amplitudes.get)
            match = (winner == expected)
            if match:
                passed_count += 1
                
            # Log first 15 numbers to check pattern details
            if n <= 15:
                actual_print = f"{n} -> "
                if winner == "FizzBuzz": actual_print += "FizzBuzz"
                elif winner == "Fizz": actual_print += "Fizz"
                elif winner == "Buzz": actual_print += "Buzz"
                else: actual_print += str(n)
                print(f"    n={n:2d} | Expected: {expected:8s} | Winner: {winner:8s} | {actual_print:8s} | Match: {match}", flush=True)
                
        eval_time = (time.perf_counter() - t_eval_start) * 1000.0
        accuracy = (passed_count / total_count) * 100.0
        print(f"  -> Modulo Decision Accuracy (1-100): {accuracy:.1f}% ({passed_count}/{total_count} correct)", flush=True)
        
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
    print("  SUMMARY LEDGER (SMALL GRIDS 1-100)", flush=True)
    print("==========================================================================", flush=True)
    print(f"{'Nodes (N)':<10} | {'Edges (E)':<10} | {'Compile (ms)':<15} | {'Eval 100 (ms)':<15} | {'Euler Step (ms)':<15} | {'Accuracy':<10}", flush=True)
    print("-" * 88, flush=True)
    for r in summary_ledger:
        print(f"{r['N']:<10} | {r['edges']:<10} | {r['compile_time_ms']:<15.2f} | {r['eval_time_ms']:<15.2f} | {r['step_ms']:<15.2f} | {r['accuracy']:.1f}%", flush=True)
    print("==========================================================================", flush=True)

if __name__ == "__main__":
    run_fizzbuzz_small_grids()
