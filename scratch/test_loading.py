#!/usr/bin/env python3
import sys
from pathlib import Path
import math

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

def main():
    print("Testing if LOAD_16 pumps mass into active resonators starting from baseline...")
    val_X = 1  # Bit 0 active
    
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
    group.engine.physics.conductance_max = 4000.0
    group.engine.physics.conductance_gamma = 6.0
    
    # Prime registers to inactive/baseline state (15.0 on host/battery, NOT 300.0)
    for reg in ['X', 'Y']:
        for b in range(16):
            host = group.get_node(f"S_R{reg}_Bit{b}")
            bat = group.get_node(f"S_R{reg}_Bit{b}_B")
            host["rho"] = baseline_rho
            bat["rho"] = baseline_rho
            host["psi"] = -1.0
            bat["psi"] = -1.0
            host["psi_bias"] = -1.0
            bat["psi_bias"] = -1.0
            bat["isBattery"] = False
            
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=120, settle_steps=15)
    
    # Run LOAD_16
    reg_name = "X"
    val = val_X
    
    # Open gates and write-enable target register
    for b in range(16):
        host = group.get_node(f"S_R{reg_name}_Bit{b}")
        bat = group.get_node(f"S_R{reg_name}_Bit{b}_B")
        group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
        group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
        host["psi_bias"] = 0.0
        bat["psi_bias"] = 0.0
        
    for b in range(16):
        lane = b // 8
        g_target = f"GATE_{reg_name}_Bit{b}"
        if (val & (1 << b)):
            group.set_edge_connection(g_target, f"P_Bus{lane}", True)
            group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 1.0
        else:
            group.get_node(g_target)["psi_bias"] = -1.0
            group.set_edge_connection(g_target, f"P_Bus{lane}", False)
            
    amp = 8.0
    
    for s in range(150):
        t = s * sequencer.dt
        
        # Drive active gate
        for b in range(16):
            if (val & (1 << b)):
                omega, phase_val = sequencer.get_bit_params(b)
                val_psi = 0.3 * math.sin(omega * t + phase_val)
                g_target = f"GATE_{reg_name}_Bit{b}"
                group.get_node(g_target)["psi"] = val_psi
                group.get_node(g_target)["psi_bias"] = val_psi
                
        # Modulate Bus
        num_active0 = sum(1 for b in range(8) if (val & (1 << b)))
        src_rho0 = 15.0
        if num_active0 > 0:
            sum_sin0 = 0.0
            for b in range(8):
                if (val & (1 << b)):
                    omega, phase_val = sequencer.get_bit_params(b)
                    sum_sin0 += math.sin(omega * t + phase_val)
            src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
            
        group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
        
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
        if s % 20 == 0 or s > 140:
            h0 = group.get_node("S_RX_Bit0")["rho"]
            b0 = group.get_node("S_RX_Bit0_B")["rho"]
            h1 = group.get_node("S_RX_Bit1")["rho"]
            b1 = group.get_node("S_RX_Bit1_B")["rho"]
            print(f"Step {s:3d}: Bus0={src_rho0:5.2f} | X_Bit0 (Active)={h0:6.2f}/{b0:6.2f} | X_Bit1 (Inactive)={h1:6.2f}/{b1:6.2f}")

if __name__ == "__main__":
    main()
