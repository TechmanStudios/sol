#!/usr/bin/env python3
"""
Verification Script: Exciton-MoA Graph Navigator & Statistician ICAC Operators
==============================================================================
1. Waveguide Isolation Verification (The Graph Navigator):
   - Compiles a manifold with a primary waveguide layout:
     * sa -> mixer (1 hop)
     * sb -> node_Y -> mixer (2 hops)
   - Adds background connections (sa -> node_Y, sb -> mixer) of weight 20.0 to create multipath scattering.
   - Run 1: Un-isolated. The background paths scramble phases, degrading constructive wave addition.
   - Run 2: Isolated using Graph Navigator. dampens background connections to 0.01, restoring wave addition.
2. Capacitance Tuning Verification (The Statistician):
   - Runs a high-amplitude wave drive (amplitude = 8.0) into the mixer (default semanticMass = 1.0).
   - Measures logarithmic pressure saturation / harmonic distortion (2*omega vs omega amplitude ratio).
   - Run 3: Tunes mixer capacitance to 20.0 using the Statistician operator. Verifies reduced harmonic distortion.
"""

import sys
import os
import math
import time
from pathlib import Path
import networkx as nx

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

def compute_dft_amplitude(signal: list[float], dt: float, omega: float) -> float:
    n = len(signal)
    if n == 0:
        return 0.0
    mean_val = sum(signal) / n
    ac_signal = [x - mean_val for x in signal]
    cos_sum = 0.0
    sin_sum = 0.0
    for idx, val in enumerate(ac_signal):
        t = idx * dt
        cos_sum += val * math.cos(omega * t)
        sin_sum += val * math.sin(omega * t)
    return math.sqrt(((2.0 / n) * cos_sum)**2 + ((2.0 / n) * sin_sum)**2)

def run_simulation(secondary, sa_phase: float, sb_phase: float, drive_amp: float, dt: float, steps: int) -> tuple[float, list[float]]:
    raw_nodes = [{"id": n, "label": n, "group": "bridge", "rho": 10.0} for n in secondary.graph.nodes]
    # Keep track of custom semanticMass defined on nodes
    for rn in raw_nodes:
        rn["semanticMass"] = secondary.graph.nodes[rn["id"]].get("semanticMass", 1.0)
        
    raw_edges = [{"from": u, "to": v, "w0": secondary.graph[u][v]["weight"], "kind": "tax"} for u, v in secondary.graph.edges]
    
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=2.0, damping=0.01)
    engine.physics.conductance_max = 200.0
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    engine.physics.mhd_cfg = None
    engine.physics.jeans_cfg = None
    engine.physics.vort_cfg = None
    
    omega = 2.0 * math.pi / (24.0 * dt)
    mixer_rhos = []
    
    for s in range(steps):
        t = s * dt
        engine.physics.node_by_id["sa"]["rho"] = 10.0 + drive_amp * math.sin(omega * t + sa_phase)
        engine.physics.node_by_id["sb"]["rho"] = 10.0 + drive_amp * math.sin(omega * t + sb_phase)
        engine.step(dt=dt)
        if s >= steps - 120:
            mixer_rhos.append(engine.physics.node_by_id["mixer"]["rho"])
            
    amplitude = max(mixer_rhos) - min(mixer_rhos)
    return amplitude, mixer_rhos

def test_giants_enhancements():
    print("==========================================================================")
    print("  EXCITON-MOA ICAC ENHANCEMENTS: GRAPH NAVIGATOR & STATISTICIAN PROOF")
    print("==========================================================================")
    
    # 1. Compile Substrate Graph
    config = BlankManifoldConfig(base_node_count=6, topology_type="hyperbolic_uniform", dimensionality=3)
    secondary = BlankManifoldCore(config, seed=42)
    secondary.graph = nx.Graph()
    
    # Primary waveguide nodes and background nodes
    nodes = ["sa", "sb", "node_Y", "mixer", "node_Z", "node_W"]
    for n in nodes:
        secondary.graph.add_node(n, coords=[0.0, 0.0, 0.0], mass=1.0)
        
    # Set waveguide edges (weight = 156.25 for speed = 1.0 hop/step)
    secondary.graph.add_edge("sa", "mixer", weight=156.25)
    secondary.graph.add_edge("sb", "node_Y", weight=156.25)
    secondary.graph.add_edge("node_Y", "mixer", weight=156.25)
    
    # Add random background/cross-coupling connections to simulate multipath noise (longer than primary paths)
    secondary.graph.add_edge("sa", "node_Z", weight=30.0)
    secondary.graph.add_edge("sb", "node_Z", weight=30.0)
    secondary.graph.add_edge("node_Z", "node_W", weight=30.0)
    secondary.graph.add_edge("node_W", "mixer", weight=30.0)
    
    print("  -> Manifold initialized with primary waveguides and background paths:")
    print("     * sa -> mixer (1 hop) | sb -> node_Y -> mixer (2 hops)")
    print("     * Background cross-paths: sa -> node_Z -> node_W -> mixer (3 hops), sb -> node_Z -> node_W -> mixer (3 hops)")
    
    dt = 0.08
    steps = 400
    drive_amp = 3.0
    omega = 2.0 * math.pi / (24.0 * dt)
    
    exciton_engine = ExcitonEngine(secondary)
    
    # 2. Get Aligner's phase corrections (from shortest paths)
    corrections = exciton_engine.aligner_icac_phase_alignment(sources=["sa", "sb"], mixer="mixer", omega=omega, dt=dt)
    print(f"\n  [ALIGNER] Calculated corrections: sa={corrections['sa']:.4f} rad, sb={corrections['sb']:.4f} rad")
    
    # Trial A: Un-isolated background paths (base noise)
    print("\n  [TRIAL A] Running simulation with un-isolated background paths...", flush=True)
    amp_unisolated, _ = run_simulation(secondary, corrections["sa"], corrections["sb"], drive_amp, dt, steps)
    print(f"    -> Mixer Oscillation Amplitude: {amp_unisolated:.6f}")
    
    # Trial B: Graph Navigator Waveguide Isolation
    print("\n  [TRIAL B] Activating Graph Navigator active operator...", flush=True)
    dampened = exciton_engine.graph_navigator_isolate_waveguides(sources=["sa", "sb"], mixer="mixer", background_weight=0.001)
    print(f"    -> Waveguides isolated. Dampened {dampened} background edges to weight=0.001.")
    
    # Verify weights are updated
    assert secondary.graph["sa"]["node_Z"]["weight"] == 0.001
    assert secondary.graph["node_W"]["mixer"]["weight"] == 0.001
    print("    * Verified background edge weights are successfully set to 0.001.")
    
    # Run simulation again on isolated graph
    amp_isolated, _ = run_simulation(secondary, corrections["sa"], corrections["sb"], drive_amp, dt, steps)
    print(f"    -> Mixer Oscillation Amplitude: {amp_isolated:.6f}")
    
    coherence_boost = (amp_isolated / max(1e-6, amp_unisolated) - 1.0) * 100.0
    print(f"    -> Signal Coherence Boost from Isolation: +{coherence_boost:.1f}%")
    
    # 3. Capacitance Tuning (The Statistician)
    print("\n  [TRIAL C] Testing Capacitance Tuning (The Statistician)...", flush=True)
    print("    * Injecting high-amplitude wave drive (amplitude = 8.0) to induce saturation.")
    high_amp = 8.0
    
    # Run 1: default mass = 1.0 (highly saturated mixer pressure)
    _, mixer_rhos_sat = run_simulation(secondary, corrections["sa"], corrections["sb"], high_amp, dt, steps)
    amp_fund_sat = compute_dft_amplitude(mixer_rhos_sat, dt, omega)
    amp_harm_sat = compute_dft_amplitude(mixer_rhos_sat, dt, 2.0 * omega)
    hdr_sat = amp_harm_sat / max(1e-6, amp_fund_sat)
    print(f"    * Default mass=1.0: Fundamental Amp={amp_fund_sat:.6f} | Harmonic Amp={amp_harm_sat:.6f}")
    print(f"      -> Harmonic Distortion Ratio (2*w/w): {hdr_sat:.4f}")
    
    # Call Statistician to tune capacitance of mixer
    print("    * Activating Statistician active operator to tune mixer capacitance to 20.0...")
    exciton_engine.statistician_tune_capacitance(nodes=["mixer"], target_mass=20.0)
    assert secondary.graph.nodes["mixer"]["semanticMass"] == 20.0
    print("    * Verified mixer node semanticMass is set to 20.0.")
    
    # Run 2: tuned mass = 20.0 (highly linear pressure)
    _, mixer_rhos_lin = run_simulation(secondary, corrections["sa"], corrections["sb"], high_amp, dt, steps)
    amp_fund_lin = compute_dft_amplitude(mixer_rhos_lin, dt, omega)
    amp_harm_lin = compute_dft_amplitude(mixer_rhos_lin, dt, 2.0 * omega)
    hdr_lin = amp_harm_lin / max(1e-6, amp_fund_lin)
    print(f"    * Tuned mass=20.0: Fundamental Amp={amp_fund_lin:.6f} | Harmonic Amp={amp_harm_lin:.6f}")
    print(f"      -> Harmonic Distortion Ratio (2*w/w): {hdr_lin:.4f}")
    
    distortion_reduction = (1.0 - hdr_lin / max(1e-6, hdr_sat)) * 100.0
    print(f"    -> Harmonic Distortion Reduction: {distortion_reduction:.1f}%")
    
    # 4. Assertions for Verification
    navigator_passed = coherence_boost > 12.0  # Waveguide isolation must boost amplitude by at least 12%
    statistician_passed = distortion_reduction > 50.0  # Distortion must drop by at least 50%
    
    print("\n==========================================================================")
    print("  VERIFICATION METRICS")
    print("==========================================================================")
    print(f"  Graph Navigator Waveguide Isolation:   {'PASSED' if navigator_passed else 'FAILED'} (+{coherence_boost:.1f}% boost)")
    print(f"  Statistician Capacitance Tuning:       {'PASSED' if statistician_passed else 'FAILED'} ({distortion_reduction:.1f}% reduction)")
    
    overall_passed = navigator_passed and statistician_passed
    print(f"  Overall Status: {'PASSED' if overall_passed else 'FAILED'}")
    
    if overall_passed:
        print("\n  [STATUS] SUCCESS: Graph Navigator and Statistician operators verified!")
    else:
        print("\n  [STATUS] FAILED: Active operators failed to meet performance bounds.")
    print("==========================================================================")
    
    if not overall_passed:
        sys.exit(1)

if __name__ == "__main__":
    test_giants_enhancements()
