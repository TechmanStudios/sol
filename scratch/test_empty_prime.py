#!/usr/bin/env python3
import sys
import os
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_tune_fdm_10 import run_fdm_trial, run_fdm_trial as original_run_trial

# Let's override the trial running function to set initial register pressure to baseline_rho
def run_fdm_trial_empty_prime(active_A: bool, active_B: bool, baseline_rho=10.0, phase_A=0.0, phase_B=0.0):
    from test_tune_fdm_10 import FDMProcessingManifold, FDMManifoldGroup, FDMSequencer, Instruction, UniversalManifold, SemanticManifold
    
    nodes_ina, edges_ina, basin_ina = UniversalManifold.build_semantic_basin("Basin_InA", num_nodes=10, start_idx=0)
    nodes_inb, edges_inb, basin_inb = UniversalManifold.build_semantic_basin("Basin_InB", num_nodes=10, start_idx=10)
    nodes_outa, edges_outa, basin_outa = UniversalManifold.build_semantic_basin("Basin_OutA", num_nodes=10, start_idx=20)
    nodes_outb, edges_outb, basin_outb = UniversalManifold.build_semantic_basin("Basin_OutB", num_nodes=10, start_idx=30)
    
    semantic = SemanticManifold(
        nodes=nodes_ina + nodes_inb + nodes_outa + nodes_outb,
        edges=edges_ina + edges_inb + edges_outa + edges_outb,
        basins=[basin_ina, basin_inb, basin_outa, basin_outb]
    )
    for n in semantic.nodes:
        n["rho"] = baseline_rho
    processing = FDMProcessingManifold(baseline_rho=baseline_rho)
    group = FDMManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    group.prime_basin("Basin_InA", active=active_A)
    group.prime_basin("Basin_InB", active=active_B)
    
    for b_name in ["Basin_InA", "Basin_InB"]:
        basin = group.semantic.basins[b_name]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            if nid == basin.hub_id:
                node["rho"] = 300.0
            else:
                node["rho"] = baseline_rho
                
    for b_name in ["Basin_OutA", "Basin_OutB"]:
        basin = group.semantic.basins[b_name]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline_rho
            
    group.prime_register('A', active=True)
    # Set register A pressure to baseline, battery to 0.0
    group.get_node("S_RA")["rho"] = baseline_rho
    group.get_node("S_RA_B")["rho"] = 0.0
    
    group.prime_register('B', active=False)
    group.prime_register('C', active=False)
    group.prime_register('D', active=False)
    
    sequencer = FDMSequencer(group, dt=0.08, baseline_rho=baseline_rho, phase_A=phase_A, phase_B=phase_B)
    sequencer.execute_instruction(Instruction("LOAD_FDM", [active_A, active_B]))
    sequencer.execute_instruction(Instruction("STORE_FDM", []))
    
    dest_A_id = group.semantic.basins["Basin_OutA"].bridge_id
    dest_B_id = group.semantic.basins["Basin_OutB"].bridge_id
    delta_A = group.get_node(dest_A_id)["rho"] - baseline_rho
    delta_B = group.get_node(dest_B_id)["rho"] - baseline_rho
    
    return delta_A, delta_B, sequencer.history

def main():
    baseline = 15.0
    steps = 8
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    print(f"Starting 2D phase sweep with empty register priming at baseline = {baseline}...")
    
    best_score = -1
    best_phases = None
    best_deltas = None
    
    for i, p_A in enumerate(phases):
        for j, p_B in enumerate(phases):
            try:
                d00_A, d00_B, h00 = run_fdm_trial_empty_prime(False, False, baseline, p_A, p_B)
                d10_A, d10_B, h10 = run_fdm_trial_empty_prime(True, False, baseline, p_A, p_B)
                d01_A, d01_B, h01 = run_fdm_trial_empty_prime(False, True, baseline, p_A, p_B)
                d11_A, d11_B, h11 = run_fdm_trial_empty_prime(True, True, baseline, p_A, p_B)
            except Exception as e:
                continue
                
            m00 = h00[-1]["min_active_register_mass"]
            m10 = h10[-1]["min_active_register_mass"]
            m01 = h01[-1]["min_active_register_mass"]
            m11 = h11[-1]["min_active_register_mass"]
            
            cond_00 = (d00_A < 0.1) and (d00_B < 0.1)
            cond_10 = (d10_A >= 0.2) and (d10_B < 0.1)
            cond_01 = (d01_A < 0.1) and (d01_B >= 0.2)
            cond_11 = (d11_A >= 0.2) and (d11_B >= 0.2)
            # Register mass safety threshold is 14.0
            cond_mass = min(m00, m10, m01, m11) >= 14.0
            
            passed_cases = sum([cond_00, cond_10, cond_01, cond_11, cond_mass])
            
            if passed_cases >= 4:
                print(f"FOUND Phases A={p_A:.3f}, B={p_B:.3f} | Score={passed_cases}/5")
                print(f"  00: A={d00_A:+.3f}, B={d00_B:+.3f}")
                print(f"  10: A={d10_A:+.3f}, B={d10_B:+.3f}")
                print(f"  01: A={d01_A:+.3f}, B={d01_B:+.3f}")
                print(f"  11: A={d11_A:+.3f}, B={d11_B:+.3f}")
                print(f"  Min Mass = {min(m00, m10, m01, m11):.1f}")
                
            if passed_cases > best_score:
                best_score = passed_cases
                best_phases = (p_A, p_B)
                best_deltas = (d00_A, d00_B, d10_A, d10_B, d01_A, d01_B, d11_A, d11_B)
                best_masses = (m00, m10, m01, m11)
                
    print("\n=== SWEEP COMPLETED ===")
    if best_phases:
        p_A, p_B = best_phases
        print(f"Best Phases: A = {p_A:.4f}, B = {p_B:.4f} (Score: {best_score}/5)")
        print(f"Deltas at best phases:")
        print(f"  Case 00: A={best_deltas[0]:+.4f}, B={best_deltas[1]:+.4f}")
        print(f"  Case 10: A={best_deltas[2]:+.4f}, B={best_deltas[3]:+.4f}")
        print(f"  Case 01: A={best_deltas[4]:+.4f}, B={best_deltas[5]:+.4f}")
        print(f"  Case 11: A={best_deltas[6]:+.4f}, B={best_deltas[7]:+.4f}")
        print(f"  Min active register mass (Cases 00, 10, 01, 11): {best_masses}")

if __name__ == "__main__":
    main()
