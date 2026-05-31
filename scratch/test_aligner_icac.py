#!/usr/bin/env python3
"""
Verification Script: Exciton-MoA Aligner ICAC Phase Delay Compensation
======================================================================
1. Compiles an isolated 3-node waveguide network:
   - Source A connects to Mixer via 2 hops: sa -> node_X -> mixer
   - Source B connects to Mixer via 3 hops: sb -> node_Y -> node_Z -> mixer
2. Calls the new ExcitonEngine Aligner operator: aligner_icac_phase_alignment()
   to calculate the phase advance corrections needed to compensate for propagation delays.
3. Executes two simulation trials in the SOLEngine using stable RK4 integration:
   - Trial A: Phase-Aligned (Aligner Active)
   - Trial B: Unaligned (Both sources driven at 0 phase)
4. Measures the Mixer amplitude to verify constructive phase-coherent interference.
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
from excitons import ExcitonEngine
from sol_engine import SOLEngine

def run_addition_trial(engine: SOLEngine, sa: str, sb: str, mixer: str,
                       phase_a: float, phase_b: float, dt: float, steps: int) -> float:
    engine.restore_baseline()
    # Fundamental period of 12 steps
    omega = 2.0 * math.pi / (12.0 * dt)
    mixer_rhos = []
    
    # Drive both sources at 3.0 amplitude with specific phases
    for s in range(steps):
        t = s * dt
        engine.physics.node_by_id[sa]["rho"] = 10.0 + 3.0 * math.sin(omega * t + phase_a)
        engine.physics.node_by_id[sb]["rho"] = 10.0 + 3.0 * math.sin(omega * t + phase_b)
        
        engine.step(dt=dt)
        
        if s >= steps - 5:
            print(f"      Step {s:3d} | SourceA: {engine.physics.node_by_id['sa']['rho']:.6f} | node_Y: {engine.physics.node_by_id['node_Y']['rho']:.6f} | Mixer: {engine.physics.node_by_id['mixer']['rho']:.6f}", flush=True)
            
        # Capture Mixer rho in steady state
        if s >= steps - 100:
            mixer_rhos.append(engine.physics.node_by_id[mixer]["rho"])
            
    return max(mixer_rhos) - min(mixer_rhos)

def test_aligner_icac():
    print("==========================================================================")
    print("  EXCITON-MOA ALIGNER GIANT: ACTIVE ICAC PHASE COMPENSATION PROOF")
    print("==========================================================================")
    
    # 1. Compile Isolated Substrate Graph
    config = BlankManifoldConfig(base_node_count=4, topology_type="hyperbolic_uniform", dimensionality=3)
    secondary = BlankManifoldCore(config, seed=42)
    secondary.graph = nx.Graph()
    
    # Add nodes representing the layout
    nodes = ["sa", "sb", "node_Y", "mixer"]
    for n in nodes:
        secondary.graph.add_node(n, coords=[0.0, 0.0, 0.0], mass=1.0)
        
    # Compile asymmetrical waveguides with weight = 156.25 to make v = 1/dt
    # sa -> mixer (1 hop)
    secondary.graph.add_edge("sa", "mixer", weight=156.25)
    # sb -> node_Y -> mixer (2 hops)
    secondary.graph.add_edge("sb", "node_Y", weight=156.25)
    secondary.graph.add_edge("node_Y", "mixer", weight=156.25)
    
    print("  -> Isolated asymmetrical waveguides compiled.")
    print("     * Source A -> mixer (1 hop)")
    print("     * Source B -> node_Y -> mixer (2 hops)")
    
    # 2. Simulate wormhole seeding of the Aligner Giant
    exciton_engine = ExcitonEngine(secondary)
    
    # Define frequency and time step (slower period of 24 steps to reduce filtering attenuation)
    dt = 0.08
    steps = 400
    omega = 2.0 * math.pi / (24.0 * dt)
    
    # 3. Call active Aligner operator to calculate propagation delay phase adjustments
    t_start = time.perf_counter()
    corrections = exciton_engine.aligner_icac_phase_alignment(sources=["sa", "sb"], mixer="mixer", omega=omega, dt=dt)
    calc_time = (time.perf_counter() - t_start) * 1000.0
    
    print(f"\n  [ALIGNER OPERATION] Executed in {calc_time:.4f} ms.")
    print(f"    * Calculated correction for Source A (1 hop): {corrections['sa']:.4f} rad (+1 step lead)")
    print(f"    * Calculated correction for Source B (2 hops): {corrections['sb']:.4f} rad (+2 steps lead)")
    
    # 4. Prepare SOLEngine in stable RK4 integration mode with minimal damping
    raw_nodes = [{"id": n, "label": n, "group": "bridge", "rho": 10.0} for n in secondary.graph.nodes]
    raw_edges = [{"from": u, "to": v, "w0": secondary.graph[u][v]["weight"], "kind": "tax"} for u, v in secondary.graph.edges]
    
    # Set c_press=2.0 and damping=0.01 for clean wave propagation
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0, damping=0.01)
    engine.physics.conductance_max = 200.0
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    engine.physics.mhd_cfg = None
    engine.physics.jeans_cfg = None
    engine.physics.vort_cfg = None
    engine.save_baseline()
    
    # 5. Run Trial 1: Aligner Phase-Aligned (Constructive Alignment)
    print("\n  Running Trial 1: Phase-Aligned (Aligner active)...", flush=True)
    amp_aligned = run_addition_trial(engine, "sa", "sb", "mixer", corrections["sa"], corrections["sb"], dt, steps)
    print(f"    -> Mixer Oscillation Amplitude (Peak-to-Peak): {amp_aligned:.6f}", flush=True)
    
    # 6. Run Trial 2: Unaligned (Both driven at phase = 0.0)
    print("\n  Running Trial 2: Unaligned (Both driven at phase = 0.0)...", flush=True)
    amp_unaligned = run_addition_trial(engine, "sa", "sb", "mixer", 0.0, 0.0, dt, steps)
    print(f"    -> Mixer Oscillation Amplitude (Peak-to-Peak): {amp_unaligned:.6f}", flush=True)
    
    # 7. Analyze Improvement
    ratio = amp_aligned / max(1e-6, amp_unaligned)
    pct_increase = (ratio - 1.0) * 100.0
    print("\n==========================================================================")
    print("  VERIFICATION METRICS")
    print("==========================================================================")
    print(f"  Phase-Aligned Amplitude:   {amp_aligned:.6f}")
    print(f"  Unaligned Amplitude:       {amp_unaligned:.6f}")
    print(f"  Signal Coherence Boost:    +{pct_increase:.1f}%")
    
    passed = pct_increase > 1.0  # Coherence boost should be positive and measurable
    print(f"  Status: {'PASSED' if passed else 'FAILED'}")
    
    if passed:
        print("\n  [STATUS] SUCCESS: Aligner giant successfully aligned propagation delays!")
        print("  Constructive phase coherence verified on asymmetrical waveguides.")
    else:
        print("\n  [STATUS] FAILED: Wave interference did not show a coherence boost.")
    print("==========================================================================")

if __name__ == "__main__":
    test_aligner_icac()
