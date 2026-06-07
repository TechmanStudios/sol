#!/usr/bin/env python3
import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_resonator import (
    MHRALevel11ProcessingManifold, Level11ManifoldGroup, SemanticManifold, UniversalManifold,
    run_level11_trial
)

def evaluate_w0(w0_val: float):
    # Temporarily patch the w0 value in MHRALevel11ProcessingManifold
    original_init = MHRALevel11ProcessingManifold.__init__
    
    def patched_init(self_manifold, baseline_rho=15.0):
        self_manifold.nodes = []
        self_manifold.edges = []
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                host_id = f"S_R{reg}{lane}"
                bat_id = f"S_R{reg}{lane}_B"
                self_manifold.nodes.extend([
                    {"id": host_id, "label": f"Register{reg}_Lane{lane}_Host", "group": "processing", "rho": baseline_rho * 20.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0},
                    {"id": bat_id, "label": f"Register{reg}_Lane{lane}_Battery", "group": "processing", "rho": baseline_rho * 20.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0}
                ])
                self_manifold.edges.append({"from": host_id, "to": bat_id, "w0": w0_val})
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                gate_id = f"GATE_{reg}{lane}"
                self_manifold.nodes.append(
                    {"id": gate_id, "label": f"Gate_{reg}{lane}", "group": "bridge", "rho": baseline_rho, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0}
                )
        self_manifold.nodes.extend([
            {"id": "P_Bus0", "label": "Shared_Bus_Lane0", "group": "processing", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0},
            {"id": "P_Bus1", "label": "Shared_Bus_Lane1", "group": "processing", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0}
        ])
        for reg in ['X', 'Y']:
            self_manifold.edges.extend([
                {"from": f"S_R{reg}0", "to": f"GATE_{reg}0", "w0": 5.0},
                {"from": f"GATE_{reg}0", "to": "P_Bus0", "w0": 5.0, "kind": "wormhole", "background": False},
                {"from": f"S_R{reg}1", "to": f"GATE_{reg}1", "w0": 5.0},
                {"from": f"GATE_{reg}1", "to": "P_Bus1", "w0": 5.0, "kind": "wormhole", "background": False}
            ])
        for i in range(16):
            gate_id = f"Gate_Match{i}"
            self_manifold.nodes.append(
                {"id": gate_id, "label": gate_id, "group": "bridge", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0}
            )
            bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
            self_manifold.edges.append(
                {"from": bus_lane, "to": gate_id, "w0": 5.0, "kind": "wormhole", "background": False}
            )
            
    import test_logos_vm_level11_resonator
    test_logos_vm_level11_resonator.MHRALevel11ProcessingManifold.__init__ = patched_init
    
    baseline = 15.0
    query_steps = 120
    settle_steps = 0
    
    phases = [2 * math.pi * i / 12 for i in range(12)]
    periods = [10.0, 14.0, 18.0, 22.0]
    
    results = {}
    for f_idx in range(4):
        p = periods[f_idx]
        bit_sine = 2 * f_idx
        bit_cosine = 2 * f_idx + 1
        
        max_delta_sine = -float('inf')
        max_delta_cosine = -float('inf')
        
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[bit_sine] = ph
            deltas, _ = run_level11_trial(1 << bit_sine, 0, temp_phases, baseline, query_steps, settle_steps)
            if deltas[bit_sine] > max_delta_sine:
                max_delta_sine = deltas[bit_sine]
                
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[bit_cosine] = ph
            deltas, _ = run_level11_trial(1 << bit_cosine, 0, temp_phases, baseline, query_steps, settle_steps)
            if deltas[bit_cosine] > max_delta_cosine:
                max_delta_cosine = deltas[bit_cosine]
                
        results[p] = (max_delta_sine, max_delta_cosine)
        
    # Restore original init
    test_logos_vm_level11_resonator.MHRALevel11ProcessingManifold.__init__ = original_init
    return results

def main():
    w0_values = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]
    print(f"Sweeping host-battery w0 values...", flush=True)
    for w0 in w0_values:
        print(f"\nEvaluating w0 = {w0}...", flush=True)
        res = evaluate_w0(w0)
        all_ok = True
        for p, (ds, dc) in res.items():
            print(f"  Period {p:4.1f}: Sine max_delta = {ds:+.4f} | Cosine max_delta = {dc:+.4f}", flush=True)
            if ds < 0.2 or dc < 0.2:
                all_ok = False
        if all_ok:
            print(f"*** SUCCESS: w0 = {w0} successfully calibrated all 8 channels with positive deltas >= 0.2 ***", flush=True)

if __name__ == "__main__":
    main()
