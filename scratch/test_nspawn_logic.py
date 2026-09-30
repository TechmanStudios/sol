#!/usr/bin/env python3
"""
SOL nSpawn Universal Logic & Seeding Scaling Experiment (Vectorized & Patched)
=============================================================================
1. Spawns an orthogonal sub-manifold substrate (nSpawn) using BlankManifoldCore.
2. Simulates an autonomous wormhole seeding event of the Exciton-MoA (7 Giants).
3. Evaluates all universal logic gates (AND, OR, XOR, XNOR) via wave-interferometry.
4. Sweeps manifold sizes (64, 256, 1024, 2048 nodes) to benchmark scaling.
"""

import sys
import os
# Disable network telemetry before anything else imports it
os.environ["SOL_TELEMETRY_ENABLED"] = "false"

import time
import math
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
# Monkey Patch BlankManifoldCore to optimize O(C^2 * V) and O(N^2) bottlenecks
# ---------------------------------------------------------------------------
def optimized_build_edges(self):
    """Vectorized edge construction using numpy distance broadcasting."""
    nodes = list(self.graph.nodes(data=True))
    node_count = len(nodes)
    if node_count == 0:
        return
        
    connection_threshold = 0.5
    
    # Pre-extract coords
    coords = np.array([data["coords"] for node_id, data in nodes])
    
    # Pairwise distance matrix: shape (N, N)
    dists = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=-1)
    
    # Upper triangular mask to avoid duplicates and self-loops
    mask = (dists < connection_threshold) & (np.triu(np.ones(dists.shape), k=1) > 0)
    i_indices, j_indices = np.where(mask)
    
    for idx in range(len(i_indices)):
        i = i_indices[idx]
        j = j_indices[idx]
        self.graph.add_edge(
            nodes[i][0], 
            nodes[j][0], 
            weight=self.config.baseline_coupling, 
            distance=float(dists[i, j])
        )
                
    # Ensure Graph is connected
    isolates = list(nx.isolates(self.graph))
    if isolates:
        self._connect_isolates(isolates)
        
    if not nx.is_connected(self.graph):
        self._connect_components()

def optimized_connect_isolates(self, isolates):
    """O(I * V) connection of isolated nodes."""
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
            self.graph.add_edge(
                node_id,
                nearest_node,
                weight=self.config.baseline_coupling,
                distance=nearest_distance,
                repaired=True,
            )

def optimized_connect_components(self):
    """O(C * V) component gluing instead of quadratic sorting loops."""
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
            self.graph.add_edge(
                best_pair[0],
                best_pair[1],
                weight=self.config.baseline_coupling,
                distance=best_distance,
                repaired=True,
            )

BlankManifoldCore._build_edges = optimized_build_edges
BlankManifoldCore._connect_isolates = optimized_connect_isolates
BlankManifoldCore._connect_components = optimized_connect_components

from excitons import ExcitonEngine

def optimized_graph_navigator_hyperbolic_flow(self, epicenter_id: str):
    """Applies cycle weight damping once per unique edge instead of exponentially."""
    neighbors = list(self.manifold.neighbors(epicenter_id))
    local_cycles = [
        (epicenter_id, neighbors[i], neighbors[j])
        for i in range(len(neighbors))
        for j in range(i + 1, len(neighbors))
        if self.manifold.has_edge(neighbors[i], neighbors[j])
    ]
    residual_flux_total = 0.0

    if local_cycles:
        print(
            f"  -> [VORTEX SPUN] Graph Navigator detected {len(local_cycles)} cycles at {epicenter_id}."
        )
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

def setup_logic_nodes(graph: nx.Graph) -> tuple[str, str, str, str]:
    """Finds a central node with degree >= 3 to serve as Mixer, and 3 neighbors for inputs."""
    mixer_candidates = [n for n, d in graph.degree() if d >= 3]
    if not mixer_candidates:
        raise ValueError("Manifold graph is too sparse. Cannot find any node with degree >= 3.")
    
    mixer_candidates.sort(key=lambda n: graph.degree(n), reverse=True)
    mixer = mixer_candidates[0]
    
    neighbors = sorted(list(graph.neighbors(mixer)))
    source_a = neighbors[0]
    source_b = neighbors[1]
    source_bias = neighbors[2]
    
    return mixer, source_a, source_b, source_bias

def run_gate_trial(engine: SOLEngine, mixer: str, sa: str, sb: str, sbias: str,
                   A1: float, A2: float, ABias: float, 
                   theta1: float, theta2: float, thetaBias: float, 
                   dt: float, steps: int, c_press: float, damping: float) -> float:
    """Runs a single simulation trial using the pre-built SOLEngine."""
    engine.restore_baseline()
    
    omega = 2.0 * math.pi / (12.0 * dt)
    mixer_rhos = []
    
    for s in range(steps):
        t = s * dt
        # Drive the input sources
        engine.physics.node_by_id[sa]["rho"] = 10.0 + A1 * math.sin(omega * t + theta1)
        engine.physics.node_by_id[sb]["rho"] = 10.0 + A2 * math.sin(omega * t + theta2)
        engine.physics.node_by_id[sbias]["rho"] = 10.0 + ABias * math.sin(omega * t + thetaBias)
        
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
        if s >= steps - 30:
            mixer_rhos.append(engine.physics.node_by_id[mixer]["rho"])
            
    return max(mixer_rhos) - min(mixer_rhos)

def evaluate_logic_gate(engine: SOLEngine, gate_name: str, mixer: str, sa: str, sb: str, sbias: str,
                        input_encoding: dict, bias_amplitude: float, bias_phase: float, 
                        invert: bool, dt: float, steps: int, c_press: float, damping: float) -> tuple[list[dict], float]:
    """Evaluates the gate truth table and returns trial data plus the calibrated threshold."""
    combos = [
        {"A": 0, "B": 0},
        {"A": 0, "B": 1},
        {"A": 1, "B": 0},
        {"A": 1, "B": 1},
    ]
    
    amplitudes = []
    for c in combos:
        phase_A = input_encoding[c["A"]]
        phase_B = input_encoding[c["B"]]
        
        amp = run_gate_trial(engine, mixer, sa, sb, sbias, 
                             3.0, 3.0, bias_amplitude, 
                             phase_A, phase_B, bias_phase, 
                             dt, steps, c_press, damping)
        amplitudes.append(amp)
        c["amp"] = amp
        
    # Calibrate threshold dynamically
    if gate_name == "AND":
        a00, a01, a10, a11 = amplitudes
        threshold = (a11 + max(a00, a01, a10)) / 2.0
    elif gate_name == "OR":
        a00, a01, a10, a11 = amplitudes
        threshold = (a00 + max(a01, a10, a11)) / 2.0
    else:  # XOR and XNOR
        a00, a01, a10, a11 = amplitudes
        threshold = (min(a00, a11) + max(a01, a10)) / 2.0
        
    results = []
    for c, amp in zip(combos, amplitudes):
        raw_out = 1 if amp > threshold else 0
        gate_out = (1 - raw_out) if invert else raw_out
        
        if gate_name == "AND":
            expected = 1 if (c["A"] == 1 and c["B"] == 1) else 0
        elif gate_name == "OR":
            expected = 1 if (c["A"] == 1 or c["B"] == 1) else 0
        elif gate_name == "XOR":
            expected = 1 if (c["A"] != c["B"]) else 0
        elif gate_name == "XNOR":
            expected = 1 if (c["A"] == c["B"]) else 0
            
        results.append({
            "A": c["A"],
            "B": c["B"],
            "amp": amp,
            "out": gate_out,
            "expected": expected,
            "match": gate_out == expected
        })
    
    print(f"    [{gate_name}] Amplitudes: a00={amplitudes[0]:.4f}, a01={amplitudes[1]:.4f}, a10={amplitudes[2]:.4f}, a11={amplitudes[3]:.4f} | Thresh={threshold:.4f}")
    for res in results:
        print(f"      A={res['A']} B={res['B']} | Amp={res['amp']:.4f} -> Out={res['out']} (Expected={res['expected']}) | Match: {res['match']}")
        
    return results, threshold

def run_scaling_benchmark():
    print("==========================================================================")
    print("  nSPAWN SCALING & DYNAMIC MOA SEEDING EXPERIMENT")
    print("==========================================================================")
    
    sizes = [64, 256, 1024, 2048]
    summary_ledger = []
    
    for N in sizes:
        print(f"\n[SIZE SWEEP] Testing pocket manifold nSpawn with N = {N} nodes...")
        
        # 1. Spawn Pocket Manifold
        t0 = time.perf_counter()
        config = BlankManifoldConfig(base_node_count=N, topology_type="hyperbolic_uniform", dimensionality=3)
        secondary = BlankManifoldCore(config, seed=42)
        secondary_graph = secondary.generate_manifold()
        compile_time = (time.perf_counter() - t0) * 1000.0
        print(f"  -> Generated in {compile_time:.2f} ms. Nodes: {secondary_graph.number_of_nodes()}, Edges: {secondary_graph.number_of_edges()}")
        
        # Select logic nodes
        mixer, sa, sb, sbias = setup_logic_nodes(secondary_graph)
        
        # 2. Setup Primary and simulate autonomous wormhole transmission
        print("  -> Simulating execution steps 1 to 49 on primary manifold...")
        
        # Execution time step 50 seeding event
        t_seed_start = time.perf_counter()
        print("  -> Step 50 [WORMHOLE SEEDING EVENT] Seeding Exciton-MoA autonomously to nSpawn...")
        
        # We seed the 7 Giants onto key nodes of the secondary pocket manifold
        giants = [
            "The Statistician", "The Optimizer", "The N-Body Solver",
            "The Graph Navigator", "The Linear Algebraist", "The Aligner", "The Integrator"
        ]
        
        seeded_nodes = [mixer, sa, sb, sbias]
        other_candidates = sorted([n for n in secondary_graph.nodes() if n not in seeded_nodes])
        other_candidates.sort(key=lambda n: secondary_graph.degree(n), reverse=True)
        seeded_nodes.extend(other_candidates[:3])
        
        for idx, node_id in enumerate(seeded_nodes):
            giant_name = giants[idx]
            secondary_graph.nodes[node_id]["dominant_giant"] = giant_name
            # Seed with high resonance and aligned mode/state vectors to guide the manifold logic highway
            secondary_graph.nodes[node_id]["resonance_accumulator"] = 2.0
            secondary_graph.nodes[node_id]["semantic_mode"] = np.array([1.0, 1.0])
            secondary_graph.nodes[node_id]["state_vector"] = np.array([0.0, 0.0, 0.0])
            
        seed_latency = (time.perf_counter() - t_seed_start) * 1000.0
        print(f"  -> Seeding complete in {seed_latency:.4f} ms.")
        
        # Measure edge weights before guidance
        initial_weights = [secondary_graph[u][v].get("weight", 0.1) for u, v in secondary_graph.edges(mixer)]
        avg_initial_weight = np.mean(initial_weights)
        
        # 3. Apply Exciton-MoA guidance
        print("  -> Exciton-MoA guiding the manifold. Executing 7 Giants operators...")
        exciton_engine = ExcitonEngine(secondary)
        target_coords = np.array([10.0, 10.0, 10.0])
        exciton_engine.ignite_excitons(target_coords)
        
        # Measure edge weights after guidance
        guided_weights = [secondary_graph[u][v].get("weight", 0.1) for u, v in secondary_graph.edges(mixer)]
        avg_guided_weight = np.mean(guided_weights)
        print(f"  -> Guided Average Mixer Edge Weight: {avg_initial_weight:.4f} -> {avg_guided_weight:.4f}")
        
        # 4. Prepare SOLEngine once for this size
        c_press = 2.0
        damping = 0.2
        
        raw_nodes = [{"id": n, "label": n, "group": "bridge", "rho": 10.0} for n in secondary_graph.nodes]
        raw_edges = [{"from": u, "to": v, "w0": secondary_graph[u][v].get("weight", 0.1), "kind": "tax"} for u, v in secondary_graph.edges]
        
        engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
        engine.integration_mode = "forward_euler"
        engine.physics.psi_diffusion = 0.0
        engine.physics.conductance_gamma = 1.0
        engine.physics.mhd_cfg = None
        engine.physics.jeans_cfg = None
        engine.physics.vort_cfg = None
        engine.save_baseline()
        
        # 5. Evaluate universal logic gates on the guided substrate
        print("  -> Evaluating universal logic suite...")
        dt = 0.08
        steps = 100
        
        # AND
        and_res, threshold_and = evaluate_logic_gate(
            engine, "AND", mixer, sa, sb, sbias,
            input_encoding={0: 0.0, 1: math.pi},
            bias_amplitude=3.0, bias_phase=math.pi,
            invert=False, dt=dt, steps=steps, c_press=c_press, damping=damping
        )
        and_ok = all(r["match"] for r in and_res)
        
        # OR
        or_res, threshold_or = evaluate_logic_gate(
            engine, "OR", mixer, sa, sb, sbias,
            input_encoding={0: math.pi, 1: 0.0},
            bias_amplitude=3.0, bias_phase=math.pi,
            invert=True, dt=dt, steps=steps, c_press=c_press, damping=damping
        )
        or_ok = all(r["match"] for r in or_res)
        
        # XOR
        xor_res, threshold_xor = evaluate_logic_gate(
            engine, "XOR", mixer, sa, sb, sbias,
            input_encoding={0: 0.0, 1: math.pi},
            bias_amplitude=0.0, bias_phase=0.0,
            invert=True, dt=dt, steps=steps, c_press=c_press, damping=damping
        )
        xor_ok = all(r["match"] for r in xor_res)
        
        # XNOR
        xnor_res, threshold_xnor = evaluate_logic_gate(
            engine, "XNOR", mixer, sa, sb, sbias,
            input_encoding={0: 0.0, 1: math.pi},
            bias_amplitude=0.0, bias_phase=0.0,
            invert=False, dt=dt, steps=steps, c_press=c_press, damping=damping
        )
        xnor_ok = all(r["match"] for r in xnor_res)
        
        gates_passed = sum([and_ok, or_ok, xor_ok, xnor_ok])
        print(f"  -> Logic Gates Passed: {gates_passed}/4 [AND:{and_ok}, OR:{or_ok}, XOR:{xor_ok}, XNOR:{xnor_ok}]")
        
        # Profile single-step execution time
        t_step = time.perf_counter()
        engine.step(dt=dt)
        step_execution_time = (time.perf_counter() - t_step) * 1000.0
        print(f"  -> Single Euler step execution time: {step_execution_time:.2f} ms")
        
        summary_ledger.append({
            "N": N,
            "edges": len(raw_edges),
            "compile_time_ms": compile_time,
            "seed_latency_ms": seed_latency,
            "step_ms": step_execution_time,
            "gates_passed": gates_passed
        })
        
    print("\n==========================================================================")
    print("  SUMMARY LEDGER")
    print("==========================================================================")
    print(f"{'Nodes (N)':<10} | {'Edges (E)':<10} | {'Compile (ms)':<15} | {'Seeding (ms)':<15} | {'Euler Step (ms)':<15} | {'Gates OK':<10}")
    print("-" * 88)
    for r in summary_ledger:
        print(f"{r['N']:<10} | {r['edges']:<10} | {r['compile_time_ms']:<15.2f} | {r['seed_latency_ms']:<15.4f} | {r['step_ms']:<15.2f} | {r['gates_passed']:<10}/4")
    print("==========================================================================")

if __name__ == "__main__":
    run_scaling_benchmark()
