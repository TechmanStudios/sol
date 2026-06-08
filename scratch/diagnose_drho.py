#!/usr/bin/env python3
import sys
from pathlib import Path
import math

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

def main():
    val_X = 1
    
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
    for n in processing.nodes:
        if n["group"] == "processing" and n["id"].startswith("S_R"):
            n["semanticMass"] = 1.0
            n["semanticMass0"] = 1.0
            n["rho"] = baseline_rho
            
    for e in processing.edges:
        if e["from"].startswith("S_R") and e["to"].endswith("_B"):
            parts = e["from"].split("Bit")
            b = int(parts[1])
            b_local = b % 8
            f_idx = b_local // 2
            p = [10.0, 14.0, 18.0, 22.0][f_idx]
            dt = 0.08
            omega = (2 * math.pi) / (p * dt)
            w0_tuned = 0.5 * (omega ** 2)
            e["w0"] = w0_tuned
            
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    group.engine.physics.conductance_max = 1000.0
    group.engine.physics.conductance_gamma = 6.0
    
    # Set to baseline
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
    
    # 1 step of LOAD_16
    reg_name = "X"
    val = val_X
    other_reg = "Y"
    
    for b in range(16):
        host = group.get_node(f"S_R{reg_name}_Bit{b}")
        bat = group.get_node(f"S_R{reg_name}_Bit{b}_B")
        group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
        group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
        host["psi_bias"] = 0.0
        bat["psi_bias"] = 0.0
        
        group.engine.write_lock(f"S_R{other_reg}_Bit{b}")
        group.engine.write_lock(f"S_R{other_reg}_Bit{b}_B")
        
    for b in range(16):
        group.engine.write_enable(f"Gate_Match{b}")
        lane = b // 8
        group.set_edge_connection(f"P_Bus{lane}", f"Gate_Match{b}", False)
        
    for nid in group.semantic.basins["Basin_Query"].node_ids:
        group.engine.write_enable(nid)
        
    for b in range(16):
        lane = b // 8
        g_target = f"GATE_{reg_name}_Bit{b}"
        if (val & (1 << b)):
            group.set_edge_connection(g_target, f"P_Bus{lane}", True)
            group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 1.0
        else:
            group.get_node(g_target)["psi_bias"] = -1.0
            group.set_edge_connection(g_target, f"P_Bus{lane}", False)
            
    # Print edges connected to GATE_X_Bit1 and S_RX_Bit1
    print("Edges from/to GATE_X_Bit1:")
    for e in group.engine.physics.edges:
        if e["from"] == "GATE_X_Bit1" or e["to"] == "GATE_X_Bit1":
            print(f"  {e['from']} -> {e['to']} | w0={e['w0']} | connection=({e['from_idx']}, {e['to_idx']})")
            
    print("Edges from/to S_RX_Bit1:")
    for e in group.engine.physics.edges:
        if e["from"] == "S_RX_Bit1" or e["to"] == "S_RX_Bit1":
            print(f"  {e['from']} -> {e['to']} | w0={e['w0']} | connection=({e['from_idx']}, {e['to_idx']})")
            
    # Step 1
    t = 0.0
    group.get_node("P_Bus0")["rho"] = 15.0
    group.engine.step(dt=sequencer.dt, damping=0.0)
    
    print("After 1 step:")
    print(f"  P_Bus0={group.get_node('P_Bus0')['rho']:.4f}")
    print(f"  GATE_X_Bit1={group.get_node('GATE_X_Bit1')['rho']:.4f}")
    print(f"  S_RX_Bit1={group.get_node('S_RX_Bit1')['rho']:.4f}")
    print(f"  S_RX_Bit1_B={group.get_node('S_RX_Bit1_B')['rho']:.4f}")

if __name__ == "__main__":
    main()
