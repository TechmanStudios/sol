#!/usr/bin/env python3
"""
SOL Manifold Universal Logic Gates Proof
=======================================
Implements the entire universal logic suite (AND, OR, XOR, XNOR) on a 4-node
manifold (Source A, Source B, Source Bias, Mixer) using wave interferometry.
"""

import sys
import os
import math
from pathlib import Path

# Add sol-core path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools" / "sol-core"))

# Disable telemetry
os.environ["SOL_TELEMETRY_ENABLED"] = "false"

from sol_engine import SOLEngine

def build_universal_graph() -> tuple[list[dict], list[dict]]:
    # Three sources (A, B, and Bias) meet at Mixer
    raw_nodes = [
        {"id": "SourceA", "label": "SourceA", "group": "bridge", "rho": 10.0},
        {"id": "SourceB", "label": "SourceB", "group": "bridge", "rho": 10.0},
        {"id": "SourceBias", "label": "SourceBias", "group": "bridge", "rho": 10.0},
        {"id": "Mixer", "label": "Mixer", "group": "bridge", "rho": 10.0},
    ]
    raw_edges = [
        {"from": "SourceA", "to": "Mixer", "w0": 1.0, "kind": "tax"},
        {"from": "SourceB", "to": "Mixer", "w0": 1.0, "kind": "tax"},
        {"from": "SourceBias", "to": "Mixer", "w0": 1.0, "kind": "tax"},
    ]
    return raw_nodes, raw_edges

def run_gate_trial(A1: float, A2: float, ABias: float, theta1: float, theta2: float, thetaBias: float, dt: float, steps: int, c_press: float, damping: float) -> float:
    raw_nodes, raw_edges = build_universal_graph()
    engine = SOLEngine.from_graph(raw_nodes, raw_edges, c_press=c_press, damping=damping)
    engine.integration_mode = "rk4"
    engine.physics.psi_diffusion = 0.0
    engine.physics.conductance_gamma = 1.0
    engine.physics.mhd_cfg = None
    
    omega = 2.0 * math.pi / (12.0 * dt)
    
    mixer_rhos = []
    for s in range(steps):
        t = s * dt
        # Drive SourceA, SourceB, and SourceBias
        engine.physics.node_by_id["SourceA"]["rho"] = 10.0 + A1 * math.sin(omega * t + theta1)
        engine.physics.node_by_id["SourceB"]["rho"] = 10.0 + A2 * math.sin(omega * t + theta2)
        engine.physics.node_by_id["SourceBias"]["rho"] = 10.0 + ABias * math.sin(omega * t + thetaBias)
        
        engine.step(dt=dt, c_press=c_press, damping=damping)
        
        if s >= steps - 100:
            mixer_rhos.append(engine.physics.node_by_id["Mixer"]["rho"])
            
    return max(mixer_rhos) - min(mixer_rhos)

def evaluate_gate(gate_name: str, input_encoding: dict, bias_amplitude: float, bias_phase: float, threshold: float, invert: bool, dt: float, steps: int, c_press: float, damping: float) -> list[dict]:
    # Truth table combinations
    combos = [
        {"A": 0, "B": 0},
        {"A": 0, "B": 1},
        {"A": 1, "B": 0},
        {"A": 1, "B": 1},
    ]
    
    results = []
    for c in combos:
        phase_A = input_encoding[c["A"]]
        phase_B = input_encoding[c["B"]]
        
        # Measure Mixer wave amplitude
        amp = run_gate_trial(3.0, 3.0, bias_amplitude, phase_A, phase_B, bias_phase, dt, steps, c_press, damping)
        
        # Decide output
        raw_out = 1 if amp > threshold else 0
        gate_out = (1 - raw_out) if invert else raw_out
        
        # Expected truth values
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
        
    return results

def main():
    print("======================================================================")
    print("  SOL UNIVERSAL LOGIC GATES LEDGER (INTERFEROMETRIC)")
    print("======================================================================")
    
    dt = 0.08
    steps = 400
    c_press = 2.0
    damping = 0.2
    
    # 1. AND Gate Configuration
    # 0 -> phase 0, 1 -> phase pi. Bias = 3.0, phase pi. Threshold = 0.025. No inversion.
    print("\n--- AND Gate ---")
    and_results = evaluate_gate(
        gate_name="AND",
        input_encoding={0: 0.0, 1: math.pi},
        bias_amplitude=3.0,
        bias_phase=math.pi,
        threshold=0.025,
        invert=False,
        dt=dt, steps=steps, c_press=c_press, damping=damping
    )
    for r in and_results:
        print(f"  {r['A']} AND {r['B']} -> Amp: {r['amp']:.6f} -> Out: {r['out']} | Expected: {r['expected']} | {'OK' if r['match'] else 'FAIL'}")
        
    # 2. OR Gate Configuration
    # 0 -> phase pi, 1 -> phase 0. Bias = 3.0, phase pi. Threshold = 0.025. Invert output.
    print("\n--- OR Gate ---")
    or_results = evaluate_gate(
        gate_name="OR",
        input_encoding={0: math.pi, 1: 0.0},
        bias_amplitude=3.0,
        bias_phase=math.pi,
        threshold=0.025,
        invert=True,
        dt=dt, steps=steps, c_press=c_press, damping=damping
    )
    for r in or_results:
        print(f"  {r['A']} OR {r['B']}  -> Amp: {r['amp']:.6f} -> Out: {r['out']} | Expected: {r['expected']} | {'OK' if r['match'] else 'FAIL'}")

    # 3. XOR Gate Configuration
    # 0 -> phase 0, 1 -> phase pi. Bias = 0.0 (no bias). Threshold = 0.010. Invert output.
    print("\n--- XOR Gate ---")
    xor_results = evaluate_gate(
        gate_name="XOR",
        input_encoding={0: 0.0, 1: math.pi},
        bias_amplitude=0.0,
        bias_phase=0.0,
        threshold=0.010,
        invert=True,
        dt=dt, steps=steps, c_press=c_press, damping=damping
    )
    for r in xor_results:
        print(f"  {r['A']} XOR {r['B']} -> Amp: {r['amp']:.6f} -> Out: {r['out']} | Expected: {r['expected']} | {'OK' if r['match'] else 'FAIL'}")

    # 4. XNOR Gate Configuration
    # 0 -> phase 0, 1 -> phase pi. Bias = 0.0. Threshold = 0.010. No inversion.
    print("\n--- XNOR Gate ---")
    xnor_results = evaluate_gate(
        gate_name="XNOR",
        input_encoding={0: 0.0, 1: math.pi},
        bias_amplitude=0.0,
        bias_phase=0.0,
        threshold=0.010,
        invert=False,
        dt=dt, steps=steps, c_press=c_press, damping=damping
    )
    for r in xnor_results:
        print(f"  {r['A']} XNOR {r['B']} -> Amp: {r['amp']:.6f} -> Out: {r['out']} | Expected: {r['expected']} | {'OK' if r['match'] else 'FAIL'}")

    # Summary
    all_results = and_results + or_results + xor_results + xnor_results
    passed = all(r["match"] for r in all_results)
    print("\n======================================================================")
    print(f"  Universal Logic Gate Suite Validation: {'PASSED' if passed else 'FAILED'}")
    print("======================================================================")

if __name__ == "__main__":
    main()
