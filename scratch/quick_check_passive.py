import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from debug_passive_gates import (
    MHRALevel11ProcessingManifoldWeak, Level11ManifoldGroupWeak, Level11SequencerWeak
)
from hybrid_subsystem_framework import UniversalManifold, SemanticManifold, Instruction
from sol_engine import snapshot_state, restore_state

def main():
    baseline = 15.0
    query_steps = 120
    settle_steps = 15
    active_X = True
    active_Y = False
    
    nodes = []
    edges = []
    basins = []
    
    for i in range(16):
        n_val, e_val, b_val = UniversalManifold.build_semantic_basin(f"Basin_Val{i}", num_nodes=10, start_idx=i*10)
        for n in n_val:
            if n["id"] == b_val.hub_id:
                n["semanticMass"] = 1.0
                n["semanticMass0"] = 1.0
        nodes.extend(n_val)
        edges.extend(e_val)
        basins.append(b_val)
        
    n_q, e_q, b_q = UniversalManifold.build_semantic_basin("Basin_Query", num_nodes=10, start_idx=160)
    nodes.extend(n_q)
    edges.extend(e_q)
    basins.append(b_q)
    
    semantic = SemanticManifold(nodes, edges, basins)
    for n in semantic.nodes:
        n["rho"] = baseline * n.get("semanticMass", 1.0)
        
    processing = MHRALevel11ProcessingManifoldWeak(baseline_rho=baseline)
    group = Level11ManifoldGroupWeak(semantic, processing, c_press=2.0, damping=0.0)
    
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 450.0
        else:
            node["rho"] = baseline * node.get("semanticMass", 1.0)
            
    for i in range(16):
        basin = group.semantic.basins[f"Basin_Val{i}"]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline * node.get("semanticMass", 1.0)
            
    # Prime registers: X is active with Bit 1 (Cosine, period 10.0)
    group.prime_register('X', active=True, baseline_rho=baseline)
    group.prime_register('Y', active=False, baseline_rho=baseline)
    
    sequencer = Level11SequencerWeak(group, dt=0.04, baseline_rho=baseline, query_steps=query_steps, settle_steps=settle_steps)
    
    # Exec sequential loads manually to trace
    if active_X:
        print("\n--- Stepping LOAD_16 X 2 ---")
        # Initialize load
        val = 2
        reg_name = 'X'
        other_reg = 'Y'
        for b in range(16):
            host = group.get_node(f"S_R{reg_name}_Bit{b}")
            bat = group.get_node(f"S_R{reg_name}_Bit{b}_B")
            group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
            group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
            if (val & (1 << b)):
                bat["isBattery"] = True
                host["psi_bias"] = 0.0
                bat["psi_bias"] = 0.0
            else:
                bat["isBattery"] = True
                bat["b_state"] = -1
                bat["b_charge"] = 0.0
                bat["psi"] = -1.0
                bat["psi_bias"] = -1.0
                host["psi"] = -1.0
                host["psi_bias"] = -1.0
            group.engine.write_lock(f"S_R{other_reg}_Bit{b}")
            group.engine.write_lock(f"S_R{other_reg}_Bit{b}_B")
            
        for b in range(16):
            group.engine.write_lock(f"Gate_Match{b}")
            lane = b // 8
            group.set_edge_connection(f"P_Bus{lane}", f"Gate_Match{b}", False)
            
        for b in range(16):
            basin = group.semantic.basins[f"Basin_Val{b}"]
            for nid in basin.node_ids:
                group.engine.write_lock(nid)
                
        for nid in group.semantic.basins["Basin_Query"].node_ids:
            group.engine.write_enable(nid)
            
        for b in range(16):
            lane = b // 8
            g_target = f"GATE_{reg_name}_Bit{b}"
            if (val & (1 << b)):
                group.set_edge_connection(g_target, f"P_Bus{lane}", True)
                group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 5.0
            else:
                group.get_node(g_target)["psi_bias"] = -1.0
                group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                
            g_other = f"GATE_{other_reg}_Bit{b}"
            group.get_node(g_other)["psi_bias"] = -1.0
            group.set_edge_connection(g_other, f"P_Bus{lane}", False)
            
        amp = 150.0
        for s in range(80):
            t = s * sequencer.dt
            group.set_edge_connection(group.semantic.basins["Basin_Query"].bridge_id, "P_Bus0", False)
            group.set_edge_connection(group.semantic.basins["Basin_Query"].bridge_id, "P_Bus1", False)
            
            for b in range(16):
                if (val & (1 << b)):
                    omega, phase_val = sequencer.get_reg_gate_params(b)
                    val_psi = 1.0 * math.sin(omega * t + phase_val)
                    g_target = f"GATE_{reg_name}_Bit{b}"
                    group.get_node(g_target)["psi"] = val_psi
                    group.get_node(g_target)["psi_bias"] = val_psi
                    
            num_active0 = sum(1 for b in range(8) if (val & (1 << b)))
            src_rho0 = 15.0
            if num_active0 > 0:
                sum_sin0 = 0.0
                for b in range(8):
                    if (val & (1 << b)):
                        omega, phase_val = sequencer.get_reg_gate_params(b)
                        sum_sin0 += math.sin(omega * t + phase_val)
                src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
                
            num_active1 = sum(1 for b in range(8, 16) if (val & (1 << b)))
            src_rho1 = 15.0
            if num_active1 > 0:
                sum_sin1 = 0.0
                for b in range(8, 16):
                    if (val & (1 << b)):
                        omega, phase_val = sequencer.get_reg_gate_params(b)
                        sum_sin1 += math.sin(omega * t + phase_val)
                src_rho1 += (amp / math.sqrt(num_active1)) * sum_sin1
                
            group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
            group.get_node("P_Bus1")["rho"] = max(1.0, src_rho1)
            
            group.engine.step(dt=sequencer.dt, damping=0.0)
            if s % 10 == 0:
                # Find the resonator edge flux
                flux_val = 0.0
                for e in group.engine.physics.edges:
                    if e["from"] == "S_RX_Bit1" and e["to"] == "S_RX_Bit1_B":
                        flux_val = e["flux"]
                print(f"Step {s:2d}: bus_rho={group.get_node('P_Bus0')['rho']:.2f}, host_rho={group.get_node('S_RX_Bit1')['rho']:.4f}, bat_rho={group.get_node('S_RX_Bit1_B')['rho']:.4f}, flux={flux_val:.4f}")
                
        # Close gates and settle
        for b in range(16):
            lane = b // 8
            g_target = f"GATE_{reg_name}_Bit{b}"
            group.get_node(g_target)["psi_bias"] = -1.0
            group.set_edge_connection(g_target, f"P_Bus{lane}", False)
            
        group.engine.write_enable("P_Bus0")
        group.engine.write_enable("P_Bus1")
        for b in range(16):
            basin = group.semantic.basins[f"Basin_Val{b}"]
            for nid in basin.node_ids:
                group.engine.write_enable(nid)
                
        for s in range(settle_steps):
            group.engine.step(dt=sequencer.dt, damping=0.0)
    
    print("\nResonator S_RX_Bit1 density:", group.get_node("S_RX_Bit1")["rho"])
    print("Resonator S_RX_Bit1 battery density:", group.get_node("S_RX_Bit1_B")["rho"])
    print("Resonator S_RX_Bit1 battery charge:", group.get_node("S_RX_Bit1_B")["b_charge"])
    print("Resonator S_RX_Bit1 battery state:", group.get_node("S_RX_Bit1_B")["b_state"])
    
    # Run a few steps of free oscillation and print state
    print("\n--- Running Free Oscillation ---")
    for s in range(20):
        group.engine.step(dt=0.04, damping=0.0)
        if s % 5 == 0:
            print(f"Step {s:2d}: host_rho={group.get_node('S_RX_Bit1')['rho']:.2f}, bat_rho={group.get_node('S_RX_Bit1_B')['rho']:.2f}")

    print("\n--- Running QUERY_16 Plus ---")
    post_load_snap = snapshot_state(group.engine.physics)
    
    # Let's inspect the derivatives manually at the first query step
    # We prepare the state as QUERY_16 plus does
    group.get_node("P_Bus0")["rho"] = baseline
    group.get_node("P_Bus1")["rho"] = baseline
    for b in range(16):
        group.get_node(f"Gate_Match{b}")["rho"] = baseline
        
    for e in group.engine.physics.edges:
        is_resonator = (
            (e["from"].startswith("S_R") and e["to"].endswith("_B")) or
            (e["to"].startswith("S_R") and e["from"].endswith("_B"))
        )
        if not is_resonator:
            e["flux"] = 0.0
            
    # Enable nodes
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
    for reg in ['X', 'Y']:
        for b in range(16):
            group.engine.write_enable(f"S_R{reg}_Bit{b}")
            group.engine.write_enable(f"S_R{reg}_Bit{b}_B")
            group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = True
            
    for b in range(16):
        gate_id = f"Gate_Match{b}"
        group.engine.write_enable(gate_id)
        lane = b // 8
        group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
        group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = 5.0
        group.get_node(gate_id)["psi_bias"] = 0.0
        
    # Active reg gates passive setup
    for reg in ['X', 'Y']:
        for b in range(16):
            lane = b // 8
            g_active = f"GATE_{reg}_Bit{b}"
            bat = group.get_node(f"S_R{reg}_Bit{b}_B")
            is_bit_active = (bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.5)
            if reg == 'X' and is_bit_active:
                group.get_node(g_active)["psi_bias"] = 0.0
                group.engine.write_enable(g_active)
                group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 5.0
            else:
                group.get_node(g_active)["psi_bias"] = -1.0
                group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                
    # Now compute derivatives
    rho_vals = [n["rho"] for n in group.engine.physics.nodes]
    flux_vals = [e["flux"] for e in group.engine.physics.edges]
    psi_vals = [n["psi"] for n in group.engine.physics.nodes]
    
    d_rho, d_flux, d_psi = group.engine.physics._compute_derivatives(rho_vals, flux_vals, psi_vals, 0.04, 2.0, 0.0)
    
    # Print node indices and their derivatives
    node_map = {n["id"]: idx for idx, n in enumerate(group.engine.physics.nodes)}
    print("S_RX_Bit1 idx:", node_map["S_RX_Bit1"], "rho:", group.get_node("S_RX_Bit1")["rho"], "d_rho:", d_rho[node_map["S_RX_Bit1"]])
    print("GATE_X_Bit1 idx:", node_map["GATE_X_Bit1"], "rho:", group.get_node("GATE_X_Bit1")["rho"], "d_rho:", d_rho[node_map["GATE_X_Bit1"]], "z_gate:", group.engine.physics.nodes[node_map["GATE_X_Bit1"]].get("z_gate"), "z_bias:", group.engine.physics.nodes[node_map["GATE_X_Bit1"]].get("z_bias"))
    print("P_Bus0 idx:", node_map["P_Bus0"], "rho:", group.get_node("P_Bus0")["rho"], "d_rho:", d_rho[node_map["P_Bus0"]], "z_gate:", group.engine.physics.nodes[node_map["P_Bus0"]].get("z_gate"), "z_bias:", group.engine.physics.nodes[node_map["P_Bus0"]].get("z_bias"))
    
    # Print edge conductances and target fluxes
    for idx, e in enumerate(group.engine.physics.edges):
        if e["from"] == "S_RX_Bit1" or e["to"] == "S_RX_Bit1" or e["from"] == "GATE_X_Bit1" or e["to"] == "GATE_X_Bit1":
            print(f"Edge {e['from']} -> {e['to']}: w0={e['w0']}, cond={e['conductance']:.4f}, flux={e['flux']:.4f}, d_flux={d_flux[idx]:.4f}")

    print("\n--- Stepping QUERY_16 Plus ---")
    for s in range(query_steps):
        t = s * sequencer.dt
        # Execute sequencer query steps logic manually so we can print
        for reg in ['X', 'Y']:
            for b in range(16):
                lane = b // 8
                g_active = f"GATE_{reg}_Bit{b}"
                bat = group.get_node(f"S_R{reg}_Bit{b}_B")
                is_bit_active = (bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.5)
                if reg == 'X' and is_bit_active:
                    group.get_node(g_active)["psi_bias"] = 0.0
                    group.engine.write_enable(g_active)
                    group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                    group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 5.0
                else:
                    group.get_node(g_active)["psi_bias"] = -1.0
                    group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                    
        for b in range(16):
            gate_id = f"Gate_Match{b}"
            dest_basin_id = f"Basin_Val{b}"
            group.set_edge_connection(gate_id, group.semantic.basins[dest_basin_id].bridge_id, True)
            f_idx = (b % 8) // 2
            group.get_edge(gate_id, group.semantic.basins[dest_basin_id].bridge_id)["w0"] = sequencer.match_weights[f_idx]
            omega, phase_val = sequencer.get_match_gate_params(b)
            val_psi = 1.0 * math.sin(omega * t + phase_val)
            group.get_node(gate_id)["psi"] = val_psi
            group.get_node(gate_id)["psi_bias"] = val_psi
            
        group.engine.step(dt=sequencer.dt, damping=0.0)
        if s % 20 == 0:
            print(f"Step {s:3d}: GATE_X_Bit1_rho={group.get_node('GATE_X_Bit1')['rho']:.4f}, P_Bus0_rho={group.get_node('P_Bus0')['rho']:.4f}, Gate_Match1_rho={group.get_node('Gate_Match1')['rho']:.4f}, Val1_rho={group.get_node(group.semantic.basins['Basin_Val1'].bridge_id)['rho']:.6f}")
            
    print("\nPost-Query Basin_Val1 bridge node density:", group.get_node(group.semantic.basins["Basin_Val1"].bridge_id)["rho"])
    
    restore_state(group.engine.physics, post_load_snap)
    print("\n--- Running QUERY_16 Minus ---")
    sequencer.execute_instruction(Instruction("QUERY_16", ["minus"]))
    print("Post-Query Basin_Val1 bridge node density:", group.get_node(group.semantic.basins["Basin_Val1"].bridge_id)["rho"])

if __name__ == "__main__":
    main()
