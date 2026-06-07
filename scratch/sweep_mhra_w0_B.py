import sys
import math
import time
import multiprocessing
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import UniversalManifold, SemanticManifold, ManifoldGroup, Instruction
from test_logos_vm_level10_mhra import MHRADualProcessingManifold, MHRAManifoldGroup, MHRASequencer

def run_mhra_trial_custom(query_A, query_B, w0_B, phase_A, phase_B, phi_in_A, phi_in_B, null_period):
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
    
    sequencer = MHRASequencer(group, dt=0.08, baseline_rho=15.0, 
                              phase_A=phase_A, phase_B=phase_B, 
                              phi_in_A=phi_in_A, phi_in_B=phi_in_B, null_period=null_period)
    
    if query_A != "NULL":
        sequencer.execute_instruction(Instruction("LOAD_QUERY", ["A", query_A]))
    if query_B != "NULL":
        sequencer.execute_instruction(Instruction("LOAD_QUERY", ["B", query_B]))
        
    # Execute query with custom w0_B
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
    delta_A = group.get_node(dest_A_id)["rho"] - 15.0
    delta_B = group.get_node(dest_B_id)["rho"] - 15.0
    
    return delta_A, delta_B, sequencer.history

def check_combination(args):
    w0_B, phase_A, phi_in_A, phase_B, phi_in_B, null_period = args
    
    # 1. Verify Case C (Parallel Superimposed Recall)
    dA_C, dB_C, hist_C = run_mhra_trial_custom("A", "B", w0_B, phase_A, phase_B, phi_in_A, phi_in_B, null_period)
    min_mass_C = hist_C[-1]["min_active_register_mass"]
    if dA_C < 0.2 or dB_C < 0.2 or min_mass_C < 14.0:
        return None
        
    # 2. Verify Case A (A active, B silent)
    dA_A, dB_A, hist_A = run_mhra_trial_custom("A", "NULL", w0_B, phase_A, phase_B, phi_in_A, phi_in_B, null_period)
    min_mass_A = hist_A[-1]["min_active_register_mass"]
    if dA_A < 0.2 or dB_A >= 0.1 or min_mass_A < 14.0:
        return None
        
    # 3. Verify Case B (A silent, B active)
    dA_B, dB_B, hist_B = run_mhra_trial_custom("NULL", "B", w0_B, phase_A, phase_B, phi_in_A, phi_in_B, null_period)
    min_mass_B = hist_B[-1]["min_active_register_mass"]
    if dB_B < 0.2 or dA_B >= 0.1 or min_mass_B < 14.0:
        return None
        
    # 4. Verify Case D (Phase-reversed rejection)
    dA_D, dB_D, hist_D = run_mhra_trial_custom("PHASE_REV_A", "NULL", w0_B, phase_A, phase_B, phi_in_A, phi_in_B, null_period)
    if dA_D >= 0.1 or dB_D >= 0.1:
        return None
        
    # 5. Verify Case E (Both silent)
    dA_E, dB_E, hist_E = run_mhra_trial_custom("NULL", "NULL", w0_B, phase_A, phase_B, phi_in_A, phi_in_B, null_period)
    if dA_E >= 0.1 or dB_E >= 0.1:
        return None
        
    return {
        "w0_B": w0_B,
        "phase_A": phase_A, "phi_in_A": phi_in_A,
        "phase_B": phase_B, "phi_in_B": phi_in_B,
        "null_period": null_period,
        "dA_A": dA_A, "dB_A": dB_A,
        "dA_B": dA_B, "dB_B": dB_B,
        "dA_C": dA_C, "dB_C": dB_C,
        "dA_D": dA_D, "dB_D": dB_D,
        "min_mass": min(min_mass_C, min_mass_A, min_mass_B)
    }

def main():
    num_processes = 3
    print(f"Starting parameter sweep (w0_B and 4D phases) using {num_processes} processes...")
    
    # coarse phase search (8 steps)
    steps = 8
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    # We sweep w0_B through several candidate values
    w0_B_values = [4.0, 5.0, 6.0, 8.0, 10.0]
    null_periods = [13.0, 15.0]
    
    for w0_B in w0_B_values:
        for np in null_periods:
            print(f"\n--- Sweeping with w0_B = {w0_B}, null_period = {np} ---")
            tasks = []
            for phase_A in phases:
                for phi_in_A in phases:
                    for phase_B in phases:
                        for phi_in_B in phases:
                            tasks.append((w0_B, phase_A, phi_in_A, phase_B, phi_in_B, np))
                            
            print(f"Total tasks: {len(tasks)}")
            
            with multiprocessing.Pool(processes=num_processes) as pool:
                for result in pool.imap_unordered(check_combination, tasks):
                    if result is not None:
                        print(f"\n*** SUCCESSFUL SOLUTION FOUND ***")
                        print(f"w0_B     = {result['w0_B']:.2f}")
                        print(f"phase_A  = {result['phase_A']:.6f} ({result['phase_A']/math.pi:.4f} * pi)")
                        print(f"phi_in_A = {result['phi_in_A']:.6f} ({result['phi_in_A']/math.pi:.4f} * pi)")
                        print(f"phase_B  = {result['phase_B']:.6f} ({result['phase_B']/math.pi:.4f} * pi)")
                        print(f"phi_in_B = {result['phi_in_B']:.6f} ({result['phi_in_B']/math.pi:.4f} * pi)")
                        print(f"null_period = {result['null_period']}")
                        print(f"Case A: dA_A={result['dA_A']:+.4f}, dB_A={result['dB_A']:+.4f}")
                        print(f"Case B: dA_B={result['dA_B']:+.4f}, dB_B={result['dB_B']:+.4f}")
                        print(f"Case C: dA_C={result['dA_C']:+.4f}, dB_C={result['dB_C']:+.4f}")
                        print(f"Case D: dA_D={result['dA_D']:+.4f}, dB_D={result['dB_D']:+.4f}")
                        print(f"Worst min_mass = {result['min_mass']:.2f}")
                        pool.terminate()
                        sys.exit(0)
                        
    print("\nSweep complete. No successful solutions found.")
    sys.exit(1)

if __name__ == "__main__":
    main()
