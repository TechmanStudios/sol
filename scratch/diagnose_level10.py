import sys
import os
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level10_mhra import run_mhra_trial, MHRAManifoldGroup, MHRASequencer, MHRADualProcessingManifold, SemanticManifold, UniversalManifold, Instruction

def run_diagnose_10():
    print("Running diagnostic trial for Level 10 MHRA...")
    baseline = 15.0
    
    nodes_q, edges_q, basin_q = UniversalManifold.build_semantic_basin("Basin_Query", num_nodes=10, start_idx=0)
    nodes_val_a, edges_val_a, basin_val_a = UniversalManifold.build_semantic_basin("Basin_ValA", num_nodes=10, start_idx=10)
    nodes_val_b, edges_val_b, basin_val_b = UniversalManifold.build_semantic_basin("Basin_ValB", num_nodes=10, start_idx=20)
    
    semantic = SemanticManifold(
        nodes=nodes_q + nodes_val_a + nodes_val_b,
        edges=edges_q + edges_val_a + edges_val_b,
        basins=[basin_q, basin_val_a, basin_val_b]
    )
    for n in semantic.nodes:
        n["rho"] = baseline
        
    processing = MHRADualProcessingManifold(baseline_rho=baseline)
    group = MHRAManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    # Prime basins
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 300.0
        else:
            node["rho"] = baseline
            
    for b_name in ["Basin_ValA", "Basin_ValB"]:
        basin = group.semantic.basins[b_name]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline
            
    # Case A: query_A = "A", query_B = "NULL"
    group.prime_register('A', active=True)
    group.get_node("S_RA")["rho"] = baseline
    group.get_node("S_RA_B")["rho"] = 0.0
    
    group.prime_register('B', active=False)
    group.prime_register('C', active=False)
    group.prime_register('D', active=False)
    
    phase_A = 0.39269908169872414
    phase_B = 0.39269908169872414
    phi_in_A = 1.5707963267948966
    phi_in_B = 1.5707963267948966
    
    sequencer = MHRASequencer(group, dt=0.08, baseline_rho=baseline, phase_A=phase_A, phase_B=phase_B, phi_in_A=phi_in_A, phi_in_B=phi_in_B, null_period=13.0)
    
    # Execute LOAD_QUERY for head A manually to print progress
    inst = Instruction("LOAD_QUERY", ["A", "A"])
    reg_name = "A"
    query_type = "A"
    reg_host_id = f"S_R{reg_name}"
    reg_bat_id = f"S_R{reg_name}_B"
    gate_id = f"GATE_{reg_name}"
    
    sequencer.group.engine.write_enable("P_Bus")
    sequencer.group.engine.write_enable(reg_host_id)
    sequencer.group.engine.write_enable(reg_bat_id)
    sequencer.group.engine.write_enable("Gate_MatchA")
    sequencer.group.engine.write_enable("Gate_MatchB")
    for nid in sequencer.group.semantic.basins["Basin_Query"].node_ids:
        sequencer.group.engine.write_enable(nid)
        
    sequencer.group.set_edge_connection("P_Bus", "Gate_MatchA", False)
    sequencer.group.set_edge_connection("P_Bus", "Gate_MatchB", False)
    
    other_reg = "B"
    sequencer.group.get_node(f"GATE_{other_reg}")["psi_bias"] = -1.0
    sequencer.group.set_edge_connection(f"GATE_{other_reg}", "P_Bus", False)
    
    print("Tracing step-by-step LOAD_QUERY phase (Level 10)...")
    print(f"{'Step':5s} | {'S_RA Host + Battery':30s} | {'P_Bus rho':10s} | {'Query Basin rho':15s}")
    
    for s in range(60):
        t = len(sequencer.history) * sequencer.dt
        sequencer.group.set_edge_connection(sequencer.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus", True)
        sequencer.group.get_edge(sequencer.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus")["w0"] = 10.0
        
        sequencer.group.get_node(gate_id)["psi_bias"] = 1.0
        sequencer.group.set_edge_connection(gate_id, "P_Bus", True)
        sequencer.group.get_edge(gate_id, "P_Bus")["w0"] = 10.0
        
        amp = 8.0
        src_rho = sequencer.baseline_rho + amp * math.sin(sequencer.omega_A * t + sequencer.phi_in_A)
        sequencer.group.get_node(sequencer.group.semantic.basins["Basin_Query"].bridge_id)["rho"] = src_rho
        
        sequencer.group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
        if s % 10 == 0:
            ra = sequencer.group.get_node("S_RA")["rho"]
            ra_psi = sequencer.group.get_node("S_RA")["psi"]
            ra_bat_rho = sequencer.group.get_node("S_RA_B")["rho"]
            ra_bat_psi = sequencer.group.get_node("S_RA_B")["psi"]
            pbus = sequencer.group.get_node("P_Bus")["rho"]
            qbr = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_Query"].bridge_id)["rho"]
            print(f"L{s:2d}  | {ra:7.1f}(psi={ra_psi:5.2f})+{ra_bat_rho:7.1f}(psi={ra_bat_psi:5.2f}) | {pbus:10.2f} | {qbr:15.2f}")
            
    print("\nTracing step-by-step SETTLE phase (Level 10)...")
    for s in range(15):
        sequencer.group.set_edge_connection(sequencer.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus", False)
        sequencer.group.get_node(gate_id)["psi_bias"] = -1.0
        sequencer.group.set_edge_connection(gate_id, "P_Bus", False)
        sequencer.group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
        ra = sequencer.group.get_node("S_RA")["rho"]
        ra_psi = sequencer.group.get_node("S_RA")["psi"]
        ra_bat_rho = sequencer.group.get_node("S_RA_B")["rho"]
        ra_bat_psi = sequencer.group.get_node("S_RA_B")["psi"]
        pbus = sequencer.group.get_node("P_Bus")["rho"]
        print(f"S{s:2d}  | {ra:7.1f}(psi={ra_psi:5.2f})+{ra_bat_rho:7.1f}(psi={ra_bat_psi:5.2f}) | {pbus:10.2f}")
        
    # Exec simultaneous recall manually:
    sequencer.group.engine.write_enable("P_Bus")
    sequencer.group.engine.write_enable("S_RA")
    sequencer.group.engine.write_enable("S_RA_B")
    sequencer.group.engine.write_enable("S_RB")
    sequencer.group.engine.write_enable("S_RB_B")
    sequencer.group.engine.write_enable("Gate_MatchA")
    sequencer.group.engine.write_enable("Gate_MatchB")
    
    sequencer.group.get_node("S_RA")["psi_bias"] = 0.0
    sequencer.group.get_node("S_RA_B")["psi_bias"] = 0.0
    sequencer.group.get_node("S_RB")["psi_bias"] = 0.0
    sequencer.group.get_node("S_RB_B")["psi_bias"] = 0.0
    sequencer.group.get_node("GATE_A")["psi_bias"] = 0.0
    sequencer.group.get_node("GATE_B")["psi_bias"] = 0.0
    sequencer.group.get_node("P_Bus")["psi_bias"] = 0.0
    sequencer.group.get_node("Gate_MatchA")["psi_bias"] = 0.0
    sequencer.group.get_node("Gate_MatchB")["psi_bias"] = 0.0
    
    sequencer.group.set_edge_connection("P_Bus", "Gate_MatchA", True)
    sequencer.group.set_edge_connection("P_Bus", "Gate_MatchB", True)
    sequencer.group.get_edge("P_Bus", "Gate_MatchA")["w0"] = 10.0
    sequencer.group.get_edge("P_Bus", "Gate_MatchB")["w0"] = 2.0
    
    for nid in sequencer.group.semantic.basins["Basin_ValA"].node_ids:
        sequencer.group.engine.write_enable(nid)
        sequencer.group.get_node(nid)["psi_bias"] = 0.0
    for nid in sequencer.group.semantic.basins["Basin_ValB"].node_ids:
        sequencer.group.engine.write_enable(nid)
        sequencer.group.get_node(nid)["psi_bias"] = 0.0
        
    active_regs = ["A"]
    
    print("\nTracing step-by-step query phase (Level 10)...")
    print(f"{'Step':5s} | {'S_RA Host + Battery':30s} | {'P_Bus rho':10s} | {'ValA_Bridge':11s} | {'ValA_Hub':10s} | {'ValB_Bridge':11s} | {'ValB_Hub':10s} | {'GateA psi':10s} | {'GateB psi':10s}")
    
    for s in range(120):
        t = len(sequencer.history) * sequencer.dt
        for reg in ['A', 'B']:
            gate_id = f"GATE_{reg}"
            if reg in active_regs:
                sequencer.group.get_node(gate_id)["psi_bias"] = 1.0
                sequencer.group.set_edge_connection(gate_id, "P_Bus", True)
                sequencer.group.get_edge(gate_id, "P_Bus")["w0"] = 10.0
            else:
                sequencer.group.get_node(gate_id)["psi_bias"] = -1.0
                sequencer.group.set_edge_connection(gate_id, "P_Bus", False)
                
        sequencer.group.set_edge_connection("Gate_MatchA", sequencer.group.semantic.basins["Basin_ValA"].bridge_id, True)
        sequencer.group.set_edge_connection("Gate_MatchB", sequencer.group.semantic.basins["Basin_ValB"].bridge_id, True)
        sequencer.group.get_edge("Gate_MatchA", sequencer.group.semantic.basins["Basin_ValA"].bridge_id)["w0"] = 10.0
        sequencer.group.get_edge("Gate_MatchB", sequencer.group.semantic.basins["Basin_ValB"].bridge_id)["w0"] = 2.0
        
        sequencer.group.get_node("Gate_MatchA")["psi"] = math.sin(sequencer.omega_A * t + sequencer.phase_A)
        sequencer.group.get_node("Gate_MatchB")["psi"] = math.sin(sequencer.omega_B * t + sequencer.phase_B)
        
        sequencer.group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
        if s % 10 == 0 or s < 10:
            ra = sequencer.group.get_node("S_RA")["rho"]
            ra_bat_rho = sequencer.group.get_node("S_RA_B")["rho"]
            ra_bat_state = sequencer.group.get_node("S_RA_B").get("b_state", 0)
            ra_bat_charge = sequencer.group.get_node("S_RA_B").get("b_charge", 0.0)
            pbus = sequencer.group.get_node("P_Bus")["rho"]
            valA_br = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_ValA"].bridge_id)["rho"]
            valA_hb = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_ValA"].hub_id)["rho"]
            valB_br = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_ValB"].bridge_id)["rho"]
            valB_hb = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_ValB"].hub_id)["rho"]
            
            gateA_psi = sequencer.group.get_node("Gate_MatchA")["psi"]
            gateB_psi = sequencer.group.get_node("Gate_MatchB")["psi"]
            
            print(f"{s:5d} | {ra:7.1f}+{ra_bat_rho:7.1f} (state={ra_bat_state:2d}, chg={ra_bat_charge:4.2f}) | {pbus:10.2f} | {valA_br:11.2f} | {valA_hb:10.2f} | {valB_br:11.2f} | {valB_hb:10.2f} | {gateA_psi:10.4f} | {gateB_psi:10.4f}")

if __name__ == "__main__":
    run_diagnose_10()

if __name__ == "__main__":
    run_diagnose_10()
