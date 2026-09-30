import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer, BasinConfig
)
from test_logos_vm_level10_mhra import MHRADualProcessingManifold, MHRAManifoldGroup, MHRASequencer

def main():
    nodes_q, edges_q, basin_q = UniversalManifold.build_semantic_basin("Basin_Query", num_nodes=10, start_idx=0)
    nodes_val_a, edges_val_a, basin_val_a = UniversalManifold.build_semantic_basin("Basin_ValA", num_nodes=10, start_idx=10)
    nodes_val_b, edges_val_b, basin_val_b = UniversalManifold.build_semantic_basin("Basin_ValB", num_nodes=10, start_idx=20)
    
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
    group.prime_register('A', active=True)
    group.get_node("S_RA")["rho"] = 15.0
    group.get_node("S_RA_B")["rho"] = 0.0
    
    group.prime_register('B', active=True)
    group.get_node("S_RB")["rho"] = 15.0
    group.get_node("S_RB_B")["rho"] = 0.0
    
    group.prime_register('C', active=False)
    group.prime_register('D', active=False)
    
    # Use calibrated phases from test
    phase_A = 2.356194490192345
    phase_B = 0.0
    phi_in_A = 1.5707963267948966
    phi_in_B = 1.5707963267948966
    
    sequencer = MHRASequencer(group, dt=0.08, baseline_rho=15.0, 
                              phase_A=phase_A, phase_B=phase_B, 
                              phi_in_A=phi_in_A, phi_in_B=phi_in_B, null_period=13.0)
    
    print("--- Executing LOAD_QUERY A ---")
    sequencer.execute_instruction(Instruction("LOAD_QUERY", ["A", "A"]))
    
    print("\n--- Executing LOAD_QUERY B ---")
    sequencer.execute_instruction(Instruction("LOAD_QUERY", ["B", "B"]))
    
    # Custom step-by-step query execution
    print("\n--- Starting QUERY_MHRA (Step-by-step telemetry) ---")
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
    group.get_edge("P_Bus", "Gate_MatchB")["w0"] = 3.0
    
    for nid in group.semantic.basins["Basin_ValA"].node_ids:
        group.engine.write_enable(nid)
        group.get_node(nid)["psi_bias"] = 0.0
    for nid in group.semantic.basins["Basin_ValB"].node_ids:
        group.engine.write_enable(nid)
        group.get_node(nid)["psi_bias"] = 0.0
        
    print(f"Step | P_Bus rho | MatchA psi/rho | MatchB psi/rho | ValA bridge/hub | ValB bridge/hub")
    print("-" * 90)
    
    for s in range(120):
        t = len(sequencer.history) * sequencer.dt
        for reg in ['A', 'B']:
            gate_id = f"GATE_{reg}"
            group.get_node(gate_id)["psi_bias"] = 1.0
            group.set_edge_connection(gate_id, "P_Bus", True)
            group.get_edge(gate_id, "P_Bus")["w0"] = 10.0
            
        group.set_edge_connection("Gate_MatchA", group.semantic.basins["Basin_ValA"].bridge_id, True)
        group.set_edge_connection("Gate_MatchB", group.semantic.basins["Basin_ValB"].bridge_id, True)
        group.get_edge("Gate_MatchA", group.semantic.basins["Basin_ValA"].bridge_id)["w0"] = 10.0
        group.get_edge("Gate_MatchB", group.semantic.basins["Basin_ValB"].bridge_id)["w0"] = 3.0
        
        group.get_node("Gate_MatchA")["psi"] = math.sin(sequencer.omega_A * t + phase_A)
        group.get_node("Gate_MatchB")["psi"] = math.sin(sequencer.omega_B * t + phase_B)
        
        group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
        if s % 10 == 0 or s == 119:
            bus_rho = group.get_node("P_Bus")["rho"]
            mA = group.get_node("Gate_MatchA")
            mB = group.get_node("Gate_MatchB")
            bA_bridge = group.get_node(group.semantic.basins["Basin_ValA"].bridge_id)["rho"]
            bA_hub = group.get_node(group.semantic.basins["Basin_ValA"].hub_id)["rho"]
            bB_bridge = group.get_node(group.semantic.basins["Basin_ValB"].bridge_id)["rho"]
            bB_hub = group.get_node(group.semantic.basins["Basin_ValB"].hub_id)["rho"]
            print(f"{s:4d} | {bus_rho:9.2f} | {mA['psi']:+5.2f} / {mA['rho']:5.2f} | {mB['psi']:+5.2f} / {mB['rho']:5.2f} | {bA_bridge:6.2f} / {bA_hub:5.2f} | {bB_bridge:6.2f} / {bB_hub:5.2f}")

    # Settle for 20 steps
    for s in range(20):
        group.get_node("GATE_A")["psi_bias"] = -1.0
        group.get_node("GATE_B")["psi_bias"] = -1.0
        group.set_edge_connection("GATE_A", "P_Bus", False)
        group.set_edge_connection("GATE_B", "P_Bus", False)
        group.set_edge_connection("Gate_MatchA", group.semantic.basins["Basin_ValA"].bridge_id, False)
        group.set_edge_connection("Gate_MatchB", group.semantic.basins["Basin_ValB"].bridge_id, False)
        group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
    print("-" * 90)
    dest_A_id = group.semantic.basins["Basin_ValA"].bridge_id
    dest_B_id = group.semantic.basins["Basin_ValB"].bridge_id
    delta_A = group.get_node(dest_A_id)["rho"] - 15.0
    delta_B = group.get_node(dest_B_id)["rho"] - 15.0
    print(f"Final deltas: delta_A = {delta_A:+.4f}, delta_B = {delta_B:+.4f}")

if __name__ == "__main__":
    main()
