import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import UniversalManifold, SemanticManifold, ManifoldGroup, Instruction
from test_logos_vm_level10_mhra import MHRADualProcessingManifold, MHRAManifoldGroup, MHRASequencer

def run_pdm_trial(query_A: bool, query_B: bool, phase_A=0.0, phase_B=0.5*math.pi, w0_B=10.0):
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
            
    group.prime_register('A', active=query_A)
    if query_A:
        group.get_node("S_RA")["rho"] = 15.0
        group.get_node("S_RA_B")["rho"] = 0.0
        
    group.prime_register('B', active=query_B)
    if query_B:
        group.get_node("S_RB")["rho"] = 15.0
        group.get_node("S_RB_B")["rho"] = 0.0
        
    group.prime_register('C', active=False)
    group.prime_register('D', active=False)
    
    omega = 2 * math.pi / (10 * 0.08)
    sequencer = MHRASequencer(group, dt=0.08, baseline_rho=15.0, 
                              phase_A=phase_A, phase_B=phase_B, 
                              phi_in_A=0.0, phi_in_B=0.5*math.pi, null_period=13.0)
    
    if query_A:
        sequencer.execute_instruction(Instruction("LOAD_QUERY", ["A", "A"]))
    if query_B:
        # Cosine load manually
        reg_name = "B"
        reg_host_id = f"S_R{reg_name}"
        reg_bat_id = f"S_R{reg_name}_B"
        gate_id = f"GATE_{reg_name}"
        
        group.engine.write_enable("P_Bus")
        group.engine.write_enable(reg_host_id)
        group.engine.write_enable(reg_bat_id)
        group.engine.write_enable("Gate_MatchA")
        group.engine.write_enable("Gate_MatchB")
        for nid in group.semantic.basins["Basin_Query"].node_ids:
            group.engine.write_enable(nid)
            
        group.set_edge_connection("P_Bus", "Gate_MatchA", False)
        group.set_edge_connection("P_Bus", "Gate_MatchB", False)
        
        other_reg = "A"
        group.get_node(f"GATE_{other_reg}")["psi_bias"] = -1.0
        group.set_edge_connection(f"GATE_{other_reg}", "P_Bus", False)
        
        for s in range(60):
            t = len(sequencer.history) * sequencer.dt
            group.set_edge_connection(q_basin.bridge_id, "P_Bus", True)
            group.get_edge(q_basin.bridge_id, "P_Bus")["w0"] = 10.0
            
            group.get_node(gate_id)["psi_bias"] = 1.0
            group.set_edge_connection(gate_id, "P_Bus", True)
            group.get_edge(gate_id, "P_Bus")["w0"] = 10.0
            
            amp = 8.0
            src_rho = 15.0 + amp * math.sin(sequencer.omega_A * t + 0.5 * math.pi)
            group.get_node(q_basin.bridge_id)["rho"] = src_rho
            
            group.engine.step(dt=sequencer.dt, damping=0.0)
            sequencer.record_telemetry()
            
        for s in range(15):
            group.set_edge_connection(q_basin.bridge_id, "P_Bus", False)
            group.get_node(gate_id)["psi_bias"] = -1.0
            group.set_edge_connection(gate_id, "P_Bus", False)
            group.engine.step(dt=sequencer.dt, damping=0.0)
            sequencer.record_telemetry()
            
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
        group.get_node("Gate_MatchB")["psi"] = math.sin(sequencer.omega_A * t + phase_B)
        
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
    delta_A = group.get_node(dest_A_id)["rho"] - 15.0
    delta_B = group.get_node(dest_B_id)["rho"] - 15.0
    
    return delta_A, delta_B

def main():
    print("Sweeping PDM phase space to find a working orthogonal phase alignment...")
    
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    # Sweep w0_B from 2.0 to 10.0
    for w0_B in [2.0, 5.0, 10.0]:
        print(f"\n--- Checking w0_B = {w0_B} ---")
        for phase_A in phases:
            for phase_B in phases:
                # 1. Verify Case A
                dA_A, dB_A = run_pdm_trial(True, False, phase_A, phase_B, w0_B)
                if dA_A < 0.2 or dB_A >= 0.1:
                    continue
                    
                # 2. Verify Case B
                dA_B, dB_B = run_pdm_trial(False, True, phase_A, phase_B, w0_B)
                if dB_B < 0.2 or dA_B >= 0.1:
                    continue
                    
                # 3. Verify Case C
                dA_C, dB_C = run_pdm_trial(True, True, phase_A, phase_B, w0_B)
                if dA_C < 0.2 or dB_C < 0.2:
                    continue
                    
                print(f"*** SUCCESSFUL PDM ALIGNMENT FOUND ***")
                print(f"w0_B = {w0_B}")
                print(f"phase_A = {phase_A:.6f} ({phase_A/math.pi:.4f} * pi)")
                print(f"phase_B = {phase_B:.6f} ({phase_B/math.pi:.4f} * pi)")
                print(f"Case A: dA_A={dA_A:+.4f}, dB_A={dB_A:+.4f}")
                print(f"Case B: dA_B={dA_B:+.4f}, dB_B={dB_B:+.4f}")
                print(f"Case C: dA_C={dA_C:+.4f}, dB_C={dB_C:+.4f}")
                return
                
    print("Sweep complete. No orthogonal phase alignments found.")

if __name__ == "__main__":
    main()
