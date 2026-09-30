import sys
import math
import time
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import UniversalManifold, SemanticManifold, ManifoldGroup, Instruction
from test_logos_vm_level10_mhra import MHRADualProcessingManifold, MHRAManifoldGroup, MHRASequencer, run_mhra_trial

def run_diagnostic_case(query_A, query_B, w0_B=10.0):
    nodes_q, edges_q, basin_q = UniversalManifold.build_semantic_basin("Basin_Query", num_nodes=10, start_idx=0)
    nodes_val_a, edges_val_a, basin_val_a = UniversalManifold.build_semantic_basin("Basin_ValA", num_nodes=10, start_idx=10)
    nodes_val_b, edges_val_b, basin_val_b = UniversalManifold.build_semantic_basin("Basin_ValB", num_nodes=10, start_idx=20)
    
    for e in edges_val_a + edges_val_b:
        if e["w0"] == 1.5:
            e["w0"] = 0.3
            
    semantic = SemanticManifold(
        nodes=nodes_q + nodes_val_a + nodes_val_b,
        edges=edges_q + edges_val_a + edges_val_b,
        basins=[basin_q, basin_val_a, basin_val_b]
    )
    for n in semantic.nodes:
        n["rho"] = 15.0
        
    processing = MHRADualProcessingManifold(baseline_rho=15.0)
    group = MHRAManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    # Prime basins
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 300.0
        else:
            node["rho"] = 15.0
            
    for b_name in ["Basin_ValA", "Basin_ValB"]:
        basin = group.semantic.basins[b_name]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = 15.0
            
    # Prime both registers
    active_reg_A = (query_A != "NULL")
    active_reg_B = (query_B != "NULL")
    
    group.prime_register('A', active=active_reg_A)
    if active_reg_A:
        group.get_node("S_RA")["rho"] = 15.0
        group.get_node("S_RA_B")["rho"] = 0.0
        
    group.prime_register('B', active=active_reg_B)
    if active_reg_B:
        group.get_node("S_RB")["rho"] = 15.0
        group.get_node("S_RB_B")["rho"] = 0.0
        
    group.prime_register('C', active=False)
    group.prime_register('D', active=False)
    
    # Use calibrated phases
    phase_A = 2.356194490192345
    phase_B = 0.0
    phi_in_A = 1.5707963267948966
    phi_in_B = 1.5707963267948966
    
    sequencer = MHRASequencer(group, dt=0.08, baseline_rho=15.0, 
                              phase_A=phase_A, phase_B=phase_B, 
                              phi_in_A=phi_in_A, phi_in_B=phi_in_B, null_period=13.0)
    
    if query_A != "NULL":
        sequencer.execute_instruction(Instruction("LOAD_QUERY", ["A", query_A]))
    if query_B != "NULL":
        sequencer.execute_instruction(Instruction("LOAD_QUERY", ["B", query_B]))
        
    # Execute query
    group.engine.write_enable("P_Bus")
    group.engine.write_enable("S_RA")
    group.engine.write_enable("S_RA_B")
    group.engine.write_enable("S_RB")
    group.engine.write_enable("S_RB_B")
    group.engine.write_enable("Gate_MatchA")
    group.engine.write_enable("Gate_MatchB")
    
    group.get_node("S_RA")["psi_bias"] = 0.0
    group.get_node("S_RA_B")["psi_bias"] = 0.0
    group.get_node("S_RB")["psi_bias"] = 0.0
    group.get_node("S_RB_B")["psi_bias"] = 0.0
    group.get_node("GATE_A")["psi_bias"] = 0.0
    group.get_node("GATE_B")["psi_bias"] = 0.0
    group.get_node("P_Bus")["psi_bias"] = 0.0
    group.get_node("Gate_MatchA")["psi_bias"] = 0.0
    group.get_node("Gate_MatchB")["psi_bias"] = 0.0
    
    group.set_edge_connection("P_Bus", "Gate_MatchA", True)
    group.set_edge_connection("P_Bus", "Gate_MatchB", True)
    group.get_edge("P_Bus", "Gate_MatchA")["w0"] = 10.0
    group.get_edge("P_Bus", "Gate_MatchB")["w0"] = w0_B
    
    for nid in group.semantic.basins["Basin_ValA"].node_ids:
        group.engine.write_enable(nid)
        group.get_node(nid)["psi_bias"] = 0.0
    for nid in group.semantic.basins["Basin_ValB"].node_ids:
        group.engine.write_enable(nid)
        group.get_node(nid)["psi_bias"] = 0.0
        
    active_regs = []
    for reg in ['A', 'B']:
        bat = group.get_node(f"S_R{reg}_B")
        if bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.1:
            active_regs.append(reg)
            
    for s in range(120):
        t = len(sequencer.history) * sequencer.dt
        for reg in ['A', 'B']:
            gate_id = f"GATE_{reg}"
            if reg in active_regs:
                group.get_node(gate_id)["psi_bias"] = 1.0
                group.set_edge_connection(gate_id, "P_Bus", True)
                group.get_edge(gate_id, "P_Bus")["w0"] = 10.0
            else:
                group.get_node(gate_id)["psi_bias"] = -1.0
                group.set_edge_connection(gate_id, "P_Bus", False)
                
        group.set_edge_connection("Gate_MatchA", group.semantic.basins["Basin_ValA"].bridge_id, True)
        group.set_edge_connection("Gate_MatchB", group.semantic.basins["Basin_ValB"].bridge_id, True)
        group.get_edge("Gate_MatchA", group.semantic.basins["Basin_ValA"].bridge_id)["w0"] = 10.0
        group.get_edge("Gate_MatchB", group.semantic.basins["Basin_ValB"].bridge_id)["w0"] = w0_B
        
        group.get_node("Gate_MatchA")["psi"] = math.sin(sequencer.omega_A * t + phase_A)
        group.get_node("Gate_MatchB")["psi"] = math.sin(sequencer.omega_B * t + phase_B)
        
        group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
    for s in range(20):
        group.get_node("GATE_A")["psi_bias"] = -1.0
        group.get_node("GATE_B")["psi_bias"] = -1.0
        group.set_edge_connection("GATE_A", "P_Bus", False)
        group.set_edge_connection("GATE_B", "P_Bus", False)
        group.set_edge_connection("Gate_MatchA", group.semantic.basins["Basin_ValA"].bridge_id, False)
        group.set_edge_connection("Gate_MatchB", group.semantic.basins["Basin_ValB"].bridge_id, False)
        group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
    dest_A_id = group.semantic.basins["Basin_ValA"].bridge_id
    dest_B_id = group.semantic.basins["Basin_ValB"].bridge_id
    hub_A_id = group.semantic.basins["Basin_ValA"].hub_id
    hub_B_id = group.semantic.basins["Basin_ValB"].hub_id
    
    delta_A_bridge = group.get_node(dest_A_id)["rho"] - 15.0
    delta_B_bridge = group.get_node(dest_B_id)["rho"] - 15.0
    delta_A_hub = group.get_node(hub_A_id)["rho"] - 15.0
    delta_B_hub = group.get_node(hub_B_id)["rho"] - 15.0
    
    return delta_A_bridge, delta_B_bridge, delta_A_hub, delta_B_hub

def main():
    cases = [
        {"query_A": "A", "query_B": "NULL", "name": "Case A (Head A active [Key A], Head B silent)"},
        {"query_A": "NULL", "query_B": "B",    "name": "Case B (Head A silent, Head B active [Key B])"},
        {"query_A": "A", "query_B": "B",    "name": "Case C (Parallel Superimposed Recall [Key A + Key B])"},
        {"query_A": "PHASE_REV_A", "query_B": "NULL", "name": "Case D (Head A Phase-Reversed Key A, Head B silent)"},
        {"query_A": "NULL", "query_B": "NULL", "name": "Case E (Both heads silent/null)"}
    ]
    
    # Let's test with w0_B = 10.0 (original) and w0_B = 3.0 (balanced)
    for w0_B in [10.0, 3.0]:
        print(f"\n=======================================================")
        print(f"  TESTING WITH w0_B = {w0_B}")
        print(f"=======================================================")
        for c in cases:
            dA_br, dB_br, dA_hb, dB_hb = run_diagnostic_case(c["query_A"], c["query_B"], w0_B=w0_B)
            print(f"{c['name']}:")
            print(f"  Bridge Deltas: delta_A={dA_br:+.4f}, delta_B={dB_br:+.4f}")
            print(f"  Hub Deltas:    delta_A={dA_hb:+.4f}, delta_B={dB_hb:+.4f}")

if __name__ == "__main__":
    main()
