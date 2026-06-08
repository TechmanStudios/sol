#!/usr/bin/env python3
import sys
from pathlib import Path
import math

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

def main():
    print("Running diagnostic trial with tracking (Tuned Resonators)...")
    val_X = 1  # Bit 0 active (Sine wave, period 10.0)
    phases = [0.0] * 16
    
    from test_logos_vm_level11_pdm_final import (
        UniversalManifold, SemanticManifold, MHRALevel11ProcessingManifold,
        Level11ManifoldGroup, Level11Sequencer, Instruction
    )
    
    baseline_rho = 15.0
    nodes = []
    edges = []
    basins = []
    
    for i in range(16):
        n_val, e_val, b_val = UniversalManifold.build_semantic_basin(f"Basin_Val{i}", num_nodes=10, start_idx=i*10)
        nodes.extend(n_val)
        edges.extend(e_val)
        basins.append(b_val)
        
    n_q, e_q, b_q = UniversalManifold.build_semantic_basin("Basin_Query", num_nodes=10, start_idx=160)
    nodes.extend(n_q)
    edges.extend(e_q)
    basins.append(b_q)
    
    semantic = SemanticManifold(nodes, edges, basins)
    for n in semantic.nodes:
        n["rho"] = baseline_rho * n.get("semanticMass", 1.0)
        
    processing = MHRALevel11ProcessingManifold(baseline_rho=baseline_rho)
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    group.prime_register('X', active=True, baseline_rho=baseline_rho)
    group.prime_register('Y', active=False, baseline_rho=baseline_rho)
    
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=120, settle_steps=15)
    sequencer.calibrated_phases = phases
    
    reg_name = "X"
    val = val_X
    other_reg = "Y"
    
    # Enable target register nodes and disable battery clamp
    for b in range(16):
        host = group.get_node(f"S_R{reg_name}_Bit{b}")
        bat = group.get_node(f"S_R{reg_name}_Bit{b}_B")
        group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
        group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
        bat["isBattery"] = False
        host["psi_bias"] = 0.0
        bat["psi_bias"] = 0.0
        
    # Open gate GATE_X_Bit0 to P_Bus0
    g_target = "GATE_X_Bit0"
    group.set_edge_connection(g_target, "P_Bus0", True)
    group.get_edge(g_target, "P_Bus0")["w0"] = 1.0
    
    amp = 8.0
    
    # Run 120 steps and print detail around 100-115
    for s in range(120):
        t = s * sequencer.dt
        
        # Drive gate X Bit 0
        omega, phase_val = sequencer.get_bit_params(0)
        val_psi = 0.3 * math.sin(omega * t + phase_val)
        group.get_node(g_target)["psi"] = val_psi
        group.get_node(g_target)["psi_bias"] = val_psi
        
        # Modulate P_Bus0
        src_rho0 = 15.0 + amp * math.sin(omega * t + phase_val)
        group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
        
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
        if 100 <= s <= 115:
            print(f"Step {s:3d}: P_Bus0={src_rho0:6.3f} | Host rho={group.get_node('S_RX_Bit0')['rho']:8.4f} | Bat rho={group.get_node('S_RX_Bit0_B')['rho']:8.4f}")

if __name__ == "__main__":
    main()
