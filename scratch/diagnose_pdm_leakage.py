#!/usr/bin/env python3
import sys
from pathlib import Path
import math

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

def main():
    print("Running diagnostic trial with tracking of QUERY_16...")
    val_X = 1  # Bit 0 active (Sine wave, period 10.0), other bits flat
    
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
    
    # Prime basins
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 300.0
        else:
            node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    # Prime registers
    group.prime_register('X', active=True, baseline_rho=baseline_rho)
    group.prime_register('Y', active=False, baseline_rho=baseline_rho)
    
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=120, settle_steps=15)
    
    # 1. LOAD_16
    print("\n--- Executing LOAD_16 ---")
    sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    
    # 2. QUERY_16
    print("\n--- Executing QUERY_16 ---")
    # Instead of running sequencer.execute_instruction, we inline it to print step-by-step
    
    # Reset bus and matching gate densities to 15.0 at query start to clear transients
    group.get_node("P_Bus0")["rho"] = baseline_rho
    group.get_node("P_Bus1")["rho"] = baseline_rho
    for b in range(16):
        group.get_node(f"Gate_Match{b}")["rho"] = baseline_rho
        
    active_regs = ["X"]
    
    # Write-enable all processing nodes, batteries isBattery=False
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
    for reg in ['X', 'Y']:
        for b in range(16):
            group.engine.write_enable(f"S_R{reg}_Bit{b}")
            group.engine.write_enable(f"S_R{reg}_Bit{b}_B")
            group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = False
            
    # Match gates connect to P_Bus0/1
    for b in range(16):
        gate_id = f"Gate_Match{b}"
        group.engine.write_enable(gate_id)
        lane = b // 8
        group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
        f_idx = (b % 8) // 2
        group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = sequencer.match_weights[f_idx]
        group.get_node(gate_id)["psi_bias"] = 0.0
        
    # Neutralize belief gradients for host/battery/buses
    for reg in ['X', 'Y']:
        for b in range(16):
            group.get_node(f"S_R{reg}_Bit{b}")["psi_bias"] = 0.0
            group.get_node(f"S_R{reg}_Bit{b}_B")["psi_bias"] = 0.0
    group.get_node("P_Bus0")["psi_bias"] = 0.0
    group.get_node("P_Bus1")["psi_bias"] = 0.0
    
    # Enable value basins
    for b in range(16):
        basin = group.semantic.basins[f"Basin_Val{b}"]
        for nid in basin.node_ids:
            group.engine.write_enable(nid)
            group.get_node(nid)["psi_bias"] = 0.0
            
    for s in range(120):
        t = len(sequencer.history) * sequencer.dt
        # Set register access gates based on active registers
        for reg in ['X', 'Y']:
            for b in range(16):
                lane = b // 8
                g_active = f"GATE_{reg}_Bit{b}"
                
                if reg in active_regs:
                    omega, phase_val = sequencer.get_bit_params(b)
                    val_psi = 0.3 * math.sin(omega * t + phase_val)
                    group.get_node(g_active)["psi"] = val_psi
                    group.get_node(g_active)["psi_bias"] = val_psi
                    group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                    group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 1.0
                else:
                    group.get_node(g_active)["psi_bias"] = -1.0
                    group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                    
        # Set match gate outputs and connect to value basins
        for b in range(16):
            gate_id = f"Gate_Match{b}"
            dest_basin_id = f"Basin_Val{b}"
            
            group.set_edge_connection(gate_id, group.semantic.basins[dest_basin_id].bridge_id, True)
            f_idx = (b % 8) // 2
            group.get_edge(gate_id, group.semantic.basins[dest_basin_id].bridge_id)["w0"] = sequencer.match_weights[f_idx]
            
            # Drive match gate reference phase
            omega, phase_val = sequencer.get_bit_params(b)
            val_psi = 0.3 * math.sin(omega * t + phase_val)
            group.get_node(gate_id)["psi"] = val_psi
            group.get_node(gate_id)["psi_bias"] = val_psi
            
        group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
        if s % 10 == 0 or s > 110:
            p_bus = group.get_node("P_Bus0")["rho"]
            h_reg = group.get_node("S_RX_Bit0")["rho"]
            b_reg = group.get_node("S_RX_Bit0_B")["rho"]
            g_match0 = group.get_node("Gate_Match0")["rho"]
            basin0 = group.get_node(group.semantic.basins["Basin_Val0"].bridge_id)["rho"]
            basin1 = group.get_node(group.semantic.basins["Basin_Val1"].bridge_id)["rho"]
            print(f"Step {s:3d}: Bus0={p_bus:6.2f} | X_Bit0={h_reg:6.2f}/{b_reg:6.2f} | Match0={g_match0:6.2f} | Val0_bridge={basin0:6.2f} | Val1_bridge={basin1:6.2f}")

if __name__ == "__main__":
    main()
