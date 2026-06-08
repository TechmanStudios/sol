#!/usr/bin/env python3
import sys
from pathlib import Path
import math

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

def main():
    print("Running a single PDM trial with tracking (balanced parameters)...")
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
    
    # Prime basins
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    for i in range(16):
        basin = group.semantic.basins[f"Basin_Val{i}"]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    group.prime_register_lane('X', 0, active=True, baseline_rho=baseline_rho)
    group.prime_register_lane('X', 1, active=False, baseline_rho=baseline_rho)
    group.prime_register_lane('Y', 0, active=False, baseline_rho=baseline_rho)
    group.prime_register_lane('Y', 1, active=False, baseline_rho=baseline_rho)
    
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=120, settle_steps=15)
    sequencer.calibrated_phases = phases
    
    # Now let's execute LOAD_16 step-by-step
    reg_name = "X"
    val = val_X
    
    print("--- STARTING LOAD ---")
    for page in [0]: # Just track Page 0 loading
        # Enable active register page nodes and its gates, freeze the other page and other register
        other_reg = "Y" if reg_name == "X" else "X"
        for lane in [0, 1]:
            group.engine.write_enable(f"S_R{reg_name}{lane}_P{page}")
            group.engine.write_enable(f"S_R{reg_name}{lane}_P{page}_B")
            group.get_node(f"S_R{reg_name}{lane}_P{page}_B")["isBattery"] = False
            
            group.engine.write_lock(f"S_R{reg_name}{lane}_P{1-page}")
            group.engine.write_lock(f"S_R{reg_name}{lane}_P{1-page}_B")
            
            for p in [0, 1]:
                group.engine.write_lock(f"S_R{other_reg}{lane}_P{p}")
                group.engine.write_lock(f"S_R{other_reg}{lane}_P{p}_B")
            
        for i in range(8):
            group.engine.write_enable(f"Gate_Match{i}")
            bus_lane = "P_Bus0" if i < 4 else "P_Bus1"
            group.set_edge_connection(bus_lane, f"Gate_Match{i}", False)
            
        for nid in group.semantic.basins["Basin_Query"].node_ids:
            group.engine.write_enable(nid)
            
        # Open active gates, close others
        for lane in [0, 1]:
            g_active = f"GATE_{reg_name}{lane}_P{page}"
            group.get_node(g_active)["psi_bias"] = 1.0
            group.set_edge_connection(g_active, f"P_Bus{lane}", True)
            group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 10.0
            
            g_inact_p = f"GATE_{reg_name}{lane}_P{1-page}"
            group.get_node(g_inact_p)["psi_bias"] = -1.0
            group.set_edge_connection(g_inact_p, f"P_Bus{lane}", False)
            
        amp = 8.0
        
        # Settle/modulate for 150 steps
        for s in range(150):
            t = s * sequencer.dt
            num_active0 = sum(1 for b in range(4) if (val & (1 << (page * 8 + b))))
            src_rho0 = baseline_rho
            if num_active0 > 0:
                sum_sin0 = 0.0
                for b in range(4):
                    if (val & (1 << (page * 8 + b))):
                        f_idx = b // 2
                        is_cosine = (b % 2 == 1)
                        phase_offset = 0.5 * math.pi if is_cosine else 0.0
                        sum_sin0 += math.sin(sequencer.omegas[f_idx] * t + phase_offset)
                src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
                
            group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
            group.engine.step(dt=sequencer.dt, damping=0.5)
            
            if s % 15 == 0:
                print(f"Load Step {s:3d}: P_Bus0 rho = {group.get_node('P_Bus0')['rho']:.3f}, Register S_RX0_P0 rho = {group.get_node('S_RX0_P0')['rho']:.3f}")

        # Close active gates and settle
        for lane in [0, 1]:
            g_active = f"GATE_{reg_name}{lane}_P{page}"
            group.get_node(g_active)["psi_bias"] = -1.0
            group.set_edge_connection(g_active, f"P_Bus{lane}", False)
            
        group.engine.write_enable("P_Bus0")
        group.engine.write_enable("P_Bus1")
        
        print("--- STARTING SETTLE ---")
        for s in range(15):
            group.engine.step(dt=sequencer.dt, damping=0.0)
            print(f"Settle Step {s:2d}: Register S_RX0_P0 rho = {group.get_node('S_RX0_P0')['rho']:.3f}")

    print("--- STARTING QUERY ---")
    page = 0
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
    for reg in ['X', 'Y']:
        for lane in [0, 1]:
            group.engine.write_enable(f"S_R{reg}{lane}_P{page}")
            group.engine.write_enable(f"S_R{reg}{lane}_P{page}_B")
            group.get_node(f"S_R{reg}{lane}_P{page}_B")["isBattery"] = False
            
            group.engine.write_lock(f"S_R{reg}{lane}_P{1-page}")
            group.engine.write_lock(f"S_R{reg}{lane}_P{1-page}_B")
            
    for i in range(8):
        gate_id = f"Gate_Match{i}"
        group.engine.write_enable(gate_id)
        bus_lane = "P_Bus0" if i < 4 else "P_Bus1"
        group.set_edge_connection(bus_lane, gate_id, True)
        f_idx = (i % 4) // 2
        group.get_edge(bus_lane, gate_id)["w0"] = sequencer.match_weights[f_idx]
        group.get_node(gate_id)["psi_bias"] = 0.0
        
    for i in range(8):
        basin_idx = page * 8 + i
        basin = group.semantic.basins[f"Basin_Val{basin_idx}"]
        for nid in basin.node_ids:
            group.engine.write_enable(nid)
            group.get_node(nid)["psi_bias"] = 0.0

    # Set register access gate
    g_active = f"GATE_X0_P0"
    group.get_node(g_active)["psi_bias"] = 1.0
    group.set_edge_connection(g_active, "P_Bus0", True)
    group.get_edge(g_active, "P_Bus0")["w0"] = 1.0

    for s in range(40):
        t = s * sequencer.dt
        val_psi = 0.3 * math.sin(sequencer.omegas[0] * t + 0.0)
        group.get_node("Gate_Match0")["psi"] = val_psi
        group.get_node("Gate_Match0")["psi_bias"] = val_psi
        
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
        if s % 2 == 0:
            print(f"Query Step {s:2d}: Register S_RX0_P0 rho = {group.get_node('S_RX0_P0')['rho']:.3f}, P_Bus0 rho = {group.get_node('P_Bus0')['rho']:.3f}, Basin_Val0 bridge rho = {group.get_node(group.semantic.basins['Basin_Val0'].bridge_id)['rho']:.3f}")

if __name__ == "__main__":
    main()
