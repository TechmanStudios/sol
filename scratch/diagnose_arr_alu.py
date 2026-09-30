#!/usr/bin/env python3
import sys
import os
import math
from pathlib import Path
import networkx as nx
import numpy as np

_SOL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SOL_ROOT / "tools" / "sol-core"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA" / "hardWare"))
sys.path.insert(0, str(_SOL_ROOT / "Frontier_OS" / "Exciton-MoA" / "firmWare" / "ExcitonEngine"))

# Force bind telemetry to prevent collisions
import importlib.util
telemetry_path = _SOL_ROOT / "tools" / "sol-core" / "telemetry.py"
spec = importlib.util.spec_from_file_location("telemetry", telemetry_path)
if spec and spec.loader:
    telemetry_mod = importlib.util.module_from_spec(spec)
    sys.modules["telemetry"] = telemetry_mod
    spec.loader.exec_module(telemetry_mod)
    telemetry_mod._TELEMETRY_ENABLED = False

from blank_config import BlankManifoldConfig
from blank_manifold_core import BlankManifoldCore
from excitons import ExcitonEngine
from sol_engine import SOLEngine

# Vectorized patches
def optimized_build_edges(self):
    nodes = sorted(list(self.graph.nodes(data=True)), key=lambda x: x[0])
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
    isolates = sorted(list(nx.isolates(self.graph)))
    if isolates:
        self._connect_isolates(isolates)
    if not nx.is_connected(self.graph):
        self._connect_components()

def optimized_connect_isolates(self, isolates):
    nodes_data = sorted(list(self.graph.nodes(data=True)), key=lambda x: x[0])
    for node_id in sorted(list(isolates)):
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
    components = sorted([sorted(list(c)) for c in nx.connected_components(self.graph)], key=lambda x: x[0])
    if len(components) <= 1:
        return
    for i in range(len(components) - 1):
        left = components[i]
        right = components[i+1]
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

def compile_hierarchical_manifold(prefix: str, size: int, seed: int):
    config = BlankManifoldConfig(base_node_count=size, topology_type="hyperbolic_uniform", dimensionality=3)
    core = BlankManifoldCore(config, seed=seed)
    graph = core.generate_manifold()
    nodes_by_degree = sorted(list(graph.nodes()), key=lambda n: (graph.degree(n), n), reverse=True)
    sa, sb, mixer = nodes_by_degree[:3]
    graph.add_edge(sa, mixer, weight=156.25)
    graph.add_edge(sb, mixer, weight=156.25)
    exciton_engine = ExcitonEngine(core)
    exciton_engine.graph_navigator_isolate_waveguides(sources=[sa, sb], mixer=mixer, background_weight=0.001)
    
    raw_nodes = []
    for n in graph.nodes:
        raw_nodes.append({
            "id": f"{prefix}_{n}",
            "label": f"{prefix}_{n}",
            "group": "bridge",
            "semanticMass": graph.nodes[n].get("semanticMass", 1.0)
        })
        
    raw_edges = []
    for u, v in graph.edges:
        raw_edges.append({
            "from": f"{prefix}_{u}",
            "to": f"{prefix}_{v}",
            "w0": graph[u][v].get("weight", 0.1),
            "kind": "tax"
        })
        
    return raw_nodes, raw_edges, f"{prefix}_{sa}", f"{prefix}_{sb}", f"{prefix}_{mixer}"

def run_trial(input_A, input_B, gate_type: str):
    nodes_p, edges_p, sa_p, sb_p, mixer_p = compile_hierarchical_manifold("parent", 64, 42)
    nodes_cA, edges_cA, sa_cA, sb_cA, mixer_cA = compile_hierarchical_manifold("childA", 32, 149)
    nodes_cB, edges_cB, sa_cB, sb_cB, mixer_cB = compile_hierarchical_manifold("childB", 32, 200)
    nodes_cC, edges_cC, sa_cC, sb_cC, mixer_cC = compile_hierarchical_manifold("childC", 32, 300)
    
    batteryA_id = "childA_node_0000"
    batteryB_id = "childB_node_0000"
    batteryC_id = "childC_node_0000"
    
    edges_cA.append({"from": mixer_cA, "to": batteryA_id, "w0": 10.0, "kind": "tax"})
    edges_cB.append({"from": mixer_cB, "to": batteryB_id, "w0": 10.0, "kind": "tax"})
    edges_cC.append({"from": mixer_cC, "to": batteryC_id, "w0": 10.0, "kind": "tax"})
    
    wormhole_A = [{"from": mixer_p, "to": sa_cA, "w0": 156.25, "kind": "tax"}]
    wormhole_B = [{"from": mixer_p, "to": sa_cB, "w0": 156.25, "kind": "tax"}]
    wormhole_C = [{"from": mixer_p, "to": sa_cC, "w0": 156.25, "kind": "tax"}]
    
    nodes_all = nodes_p + nodes_cA + nodes_cB + nodes_cC
    edges_all = edges_p + edges_cA + edges_cB + edges_cC + wormhole_A + wormhole_B + wormhole_C
    
    nodes_cloned = [dict(n) for n in nodes_all]
    
    # Initialize psi
    for n in nodes_cloned:
        if n["id"].startswith("parent_"):
            n["psi_bias"] = 1.0
            n["psi"] = 1.0
        else:
            n["psi_bias"] = -0.05
            n["psi"] = -0.05
            
    for n in nodes_cloned:
        if n["id"] in (batteryA_id, batteryB_id, batteryC_id):
            n["isBattery"] = True
            n["b_state"] = -1
            n["b_charge"] = 0.0
            n["psi_bias"] = -0.05
            n["psi"] = -0.05
            
    engine = SOLEngine.from_graph(nodes_cloned, edges_all, c_press=2.0, damping=0.01)
    engine.physics.conductance_max = 200.0
    engine.physics.conductance_min = 0.0
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 1.2
    engine.physics.conductance_gamma = 1.0
    engine.physics.battery_cfg = {
        "qMax": 60.0,
        "qThresh": 5.0,
        "leakLambda": 0.02,
        "avalancheGain": 6.0,
        "resonanceBoost": 8.0,
        "dampingClamp": 0.05,
        "flipThreshold": 0.65,
        "collapseFactor": 0.10,
        "resonanceDrive": 2.5,
        "dampingDrag": 0.2,
        "diodeResonanceOut": 1.25,
        "diodeResonanceIn": 0.80,
        "diodeDampingOut": 0.25,
        "diodeDampingIn": 1.00
    }
    
    dt = 0.08
    omega_drive = 2.0 * math.pi / (24.0 * dt)
    freqA = 3.2725
    freqB = 6.0000
    amp = 3.0
    
    should_trigger = False
    
    for s in range(350):
        t = s * dt
        # Phase 1: Write Phase (0-100)
        if s < 100:
            w0_A = 156.25 if input_A else 0.001
            w0_B = 156.25 if input_B else 0.001
            w0_C = 0.001
            
            engine.physics.node_by_id[sa_p]["rho"] = 10.0 + 0.1 * math.sin(omega_drive * t + 0.26)
            engine.physics.node_by_id[sb_p]["rho"] = 10.0 + 0.1 * math.sin(omega_drive * t + 0.26)
            
            t0 = 3.0
            sigma = 1.5
            envelope = math.exp(-((t - t0) ** 2) / (2.0 * sigma ** 2))
            if input_A:
                soliton_val_A = amp * math.sin(freqA * t) * envelope
                engine.physics.node_by_id[sb_cA]["rho"] = 10.0 + soliton_val_A
                engine.physics.node_by_id[sb_cA]["psi"] = 1.0
            if input_B:
                soliton_val_B = amp * math.sin(freqB * t) * envelope
                engine.physics.node_by_id[sb_cB]["rho"] = 10.0 + soliton_val_B
                engine.physics.node_by_id[sb_cB]["psi"] = 1.0
                
            for edge in engine.physics.edges:
                if edge["from"] == mixer_p and edge["to"] == sa_cA:
                    edge["w0"] = w0_A
                if edge["from"] == mixer_p and edge["to"] == sa_cB:
                    edge["w0"] = w0_B
                if edge["from"] == mixer_p and edge["to"] == sa_cC:
                    edge["w0"] = w0_C
                    
        # Phase 2: Decoupled Hold (100-150)
        elif 100 <= s < 150:
            for edge in engine.physics.edges:
                if edge["from"] == mixer_p and (edge["to"] in (sa_cA, sa_cB, sa_cC)):
                    edge["w0"] = 0.001
                    
        # Phase 3: ALU Compute Phase (150-250)
        elif 150 <= s < 250:
            if s == 150:
                # Read the input register states
                latched_A = engine.physics.node_by_id[batteryA_id]["b_state"] == 1.0
                latched_B = engine.physics.node_by_id[batteryB_id]["b_state"] == 1.0
                
                if gate_type == "OR":
                    should_trigger = latched_A or latched_B
                elif gate_type == "AND":
                    should_trigger = latched_A and latched_B
                    
            if should_trigger:
                # Drive positive belief locally inside child C
                engine.physics.node_by_id[sb_cC]["psi"] = 1.0
                
            for edge in engine.physics.edges:
                if edge["from"] == mixer_p and edge["to"] == sa_cC:
                    edge["w0"] = 156.25
                elif edge["from"] == mixer_p and (edge["to"] in (sa_cA, sa_cB)):
                    edge["w0"] = 0.001
                    
        # Phase 4: Hold C (250-300)
        elif 250 <= s < 300:
            for edge in engine.physics.edges:
                if edge["from"] == mixer_p and (edge["to"] in (sa_cA, sa_cB, sa_cC)):
                    edge["w0"] = 0.001
                    
        # Phase 5: Readout C (300-350)
        else:
            for edge in engine.physics.edges:
                if edge["from"] == mixer_p and edge["to"] == sa_cC:
                    edge["w0"] = 156.25
                elif edge["from"] == mixer_p and (edge["to"] in (sa_cA, sa_cB)):
                    edge["w0"] = 0.001
                    
        engine.step(dt=dt)
        
    latched = engine.physics.node_by_id[batteryC_id]["b_state"] == 1.0
    return latched

def main():
    print("Evaluating Gated ALU for OR Configuration:")
    print("------------------------------------------")
    for A, B in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        latched = run_trial(A, B, "OR")
        print(f"  Inputs: A={A}, B={B} -> Register C Latched (OR): {latched}")
        
    print("\nEvaluating Gated ALU for AND Configuration:")
    print("-------------------------------------------")
    for A, B in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        latched = run_trial(A, B, "AND")
        print(f"  Inputs: A={A}, B={B} -> Register C Latched (AND): {latched}")

if __name__ == "__main__":
    main()
