import sys
import os
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer, BasinConfig
)
from test_logos_vm_level11_pdm_prime import (
    MHRALevel11ProcessingManifold, Level11ManifoldGroup, Level11Sequencer
)

def run_diagnose():
    baseline_rho = 15.0
    val_X = 0b0000000000000001  # Only bit 0 is active, bit 1 is flat
    calibrated_phases = [0.0] * 16

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
    group.engine.physics.semantic_cfg["decayRate"] = 0.0
    group.engine.physics.jeans_cfg = None
    
    # Prime basins
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 300.0
        else:
            node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    for i in range(16):
        basin = group.semantic.basins[f"Basin_Val{i}"]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    group.prime_register('X', active=True, baseline_rho=baseline_rho)
    group.prime_register('Y', active=False, baseline_rho=baseline_rho)
        
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=120, settle_steps=15)
    sequencer.calibrated_phases = calibrated_phases
    
    # Run LOAD_16
    print("--- Running LOAD_16 ---")
    sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    
    # Check states after load
    print("\n--- After LOAD_16 & Settle ---")
    for b in [0, 1]:
        dest_id = group.semantic.basins[f"Basin_Val{b}"].bridge_id
        hub_id = group.semantic.basins[f"Basin_Val{b}"].hub_id
        dest_node = group.get_node(dest_id)
        hub_node = group.get_node(hub_id)
        gate_node = group.get_node(f"Gate_Match{b}")
        print(f"Bit {b}:")
        print(f"  Basin Hub:    rho = {hub_node['rho']:.4f}, p = {hub_node['p']:.4f}")
        print(f"  Basin Bridge: rho = {dest_node['rho']:.4f}, p = {dest_node['p']:.4f}")
        print(f"  Match Gate:   rho = {gate_node['rho']:.4f}, p = {gate_node['p']:.4f}")
        
    print("\n--- Starting QUERY_16 ---")
    # Reset bus and match gates
    group.get_node("P_Bus0")["rho"] = baseline_rho
    group.get_node("P_Bus1")["rho"] = baseline_rho
    for b in range(16):
        group.get_node(f"Gate_Match{b}")["rho"] = baseline_rho
        
    # Enable value basins
    for b in range(16):
        basin = group.semantic.basins[f"Basin_Val{b}"]
        for nid in basin.node_ids:
            group.engine.write_enable(nid)
            group.get_node(nid)["psi_bias"] = 0.0
            
    # Match gates connect to P_Bus0/1
    for b in range(16):
        gate_id = f"Gate_Match{b}"
        group.engine.write_enable(gate_id)
        lane = b // 8
        group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
        f_idx = (b % 8) // 2
        group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = sequencer.match_weights[f_idx]
        group.get_node(gate_id)["psi_bias"] = 0.0
        
    # Write-enable all processing nodes, batteries isBattery=False
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
    for reg in ['X', 'Y']:
        for b in range(16):
            group.engine.write_enable(f"S_R{reg}_Bit{b}")
            group.engine.write_enable(f"S_R{reg}_Bit{b}_B")
            group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = False
            group.get_node(f"S_R{reg}_Bit{b}")["psi_bias"] = 0.0
            group.get_node(f"S_R{reg}_Bit{b}_B")["psi_bias"] = 0.0
    group.get_node("P_Bus0")["psi_bias"] = 0.0
    group.get_node("P_Bus1")["psi_bias"] = 0.0
    
    # We step query manually and print
    print("\n--- QUERY_16 Step-by-Step ---")
    for s in range(40):
        t = len(sequencer.history) * sequencer.dt
        # Set register access gates
        for b in range(16):
            lane = b // 8
            g_active = f"GATE_X_Bit{b}"
            omega, phase_val = sequencer.get_reg_gate_params(b)
            val_psi = 0.3 * math.sin(omega * t + phase_val)
            group.get_node(g_active)["psi"] = val_psi
            group.get_node(g_active)["psi_bias"] = val_psi
            group.set_edge_connection(g_active, f"P_Bus{lane}", True)
            group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 1.0
            
            g_inactive = f"GATE_Y_Bit{b}"
            group.get_node(g_inactive)["psi_bias"] = -1.0
            group.set_edge_connection(g_inactive, f"P_Bus{lane}", False)
            
        # Match gate
        for b in range(16):
            gate_id = f"Gate_Match{b}"
            dest_basin_id = f"Basin_Val{b}"
            group.set_edge_connection(gate_id, group.semantic.basins[dest_basin_id].bridge_id, True)
            f_idx = (b % 8) // 2
            group.get_edge(gate_id, group.semantic.basins[dest_basin_id].bridge_id)["w0"] = sequencer.match_weights[f_idx]
            omega, phase_val = sequencer.get_match_gate_params(b)
            val_psi = 0.3 * math.sin(omega * t + phase_val)
            group.get_node(gate_id)["psi"] = val_psi
            group.get_node(gate_id)["psi_bias"] = val_psi
            
        group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
        bus_node = group.get_node("P_Bus0")
        print(f"Step {s:2d}: Bus rho = {bus_node['rho']:.4f}, Gate 0 psi = {group.get_node('Gate_Match0')['psi']:.4f}")

if __name__ == "__main__":
    run_diagnose()

if __name__ == "__main__":
    run_diagnose()
