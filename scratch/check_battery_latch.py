#!/usr/bin/env python3
import sys
import os
import math
import json
from pathlib import Path
import networkx as nx
import numpy as np

_SOL_ROOT = Path(__file__).resolve().parent.parent

# Force bind telemetry to prevent collisions
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
from excitons import ExcitonEngine
from sol_engine import SOLEngine

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

def test():
    nodes_p, edges_p, sa_p, sb_p, mixer_p = compile_hierarchical_manifold("parent", 64, 42)
    nodes_c, edges_c, sa_c, sb_c, mixer_c = compile_hierarchical_manifold("child", 32, 149)
    
    battery_node_id = "child_node_0000"
    edges_c.append({"from": mixer_c, "to": battery_node_id, "w0": 10.0, "kind": "tax"})  # Lower coupling so charging is slower/controlled
    
    wormhole_edges = [{"from": mixer_p, "to": sa_c, "w0": 156.25, "kind": "tax"}]
    
    nodes_all = nodes_p + nodes_c
    edges_all = edges_p + edges_c + wormhole_edges
    
    # Initialize psi of parent nodes to 1.0, child nodes to -1.0
    for n in nodes_all:
        if n["id"].startswith("parent_"):
            n["psi_bias"] = 1.0
            n["psi"] = 1.0
        else:
            n["psi_bias"] = -1.0
            n["psi"] = -1.0
            
    # Configure battery node specifically
    for n in nodes_all:
        if n["id"] == battery_node_id:
            n["isBattery"] = True
            n["b_state"] = -1
            n["b_charge"] = 0.0
            n["psi_bias"] = -1.0
            n["psi"] = -1.0
            
    dt = 0.08
    damping = 0.01
    freq = 3.2725
    amp = 3.0
    
    engine = SOLEngine.from_graph(nodes_all, edges_all, c_press=2.0, damping=damping)
    engine.physics.conductance_max = 200.0
    engine.physics.conductance_min = 0.0
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.6  # Enable psi diffusion!
    engine.physics.conductance_gamma = 1.0
    
    engine.physics.battery_cfg = {
        "qMax": 20.0,
        "qThresh": 5.0,
        "leakLambda": 0.02,
        "avalancheGain": 1.5,
        "resonanceBoost": 2.5,
        "dampingClamp": 0.15,
        "flipThreshold": 0.65,
        "collapseFactor": 0.10,
        "resonanceDrive": 2.5,
        "dampingDrag": 0.2,
        "diodeResonanceOut": 1.25,
        "diodeResonanceIn": 0.80,
        "diodeDampingOut": 0.25,
        "diodeDampingIn": 1.00
    }
    
    omega_drive = 2.0 * math.pi / (24.0 * dt)
    
    for s in range(350):
        t = s * dt
        if s == 100:
            for edge in engine.physics.edges:
                if edge["from"] == mixer_p and edge["to"] == sa_c:
                    edge["w0"] = 0.001
        if s == 200:
            for edge in engine.physics.edges:
                if edge["from"] == mixer_p and edge["to"] == sa_c:
                    edge["w0"] = 156.25
                    
        if s <= 100:
            engine.physics.node_by_id[sa_p]["rho"] = 10.0 + 0.1 * math.sin(omega_drive * t + 0.26)
            engine.physics.node_by_id[sb_p]["rho"] = 10.0 + 0.1 * math.sin(omega_drive * t + 0.26)
            
            t0 = 3.0
            sigma = 1.5
            envelope = math.exp(-((t - t0) ** 2) / (2.0 * sigma ** 2))
            soliton_val = amp * math.sin(freq * t) * envelope
            engine.physics.node_by_id[sb_c]["rho"] = 10.0 + soliton_val
            # Inject positive psi with the soliton!
            engine.physics.node_by_id[sb_c]["psi"] = 1.0
            
        engine.step(dt=dt)
        
        b = engine.physics.node_by_id[battery_node_id]
        if s % 10 == 0 or b["b_state"] == 1:
            print(f"Step {s:03d} | charge={b['b_charge']:.4f} | state={b['b_state']} | mixer_c_psi={engine.physics.node_by_id[mixer_c]['psi']:.4f} | mixer_c_rho={engine.physics.node_by_id[mixer_c]['rho']:.4f}")
            if b["b_state"] == 1:
                # print remaining steps
                for fs in range(s+1, 350):
                    engine.step(dt=dt)
                    if fs % 10 == 0 or fs == 349:
                        print(f"Step {fs:03d} | charge={b['b_charge']:.4f} | state={b['b_state']} | mixer_c_psi={engine.physics.node_by_id[mixer_c]['psi']:.4f} | mixer_c_rho={engine.physics.node_by_id[mixer_c]['rho']:.4f}")
                break

if __name__ == "__main__":
    test()
