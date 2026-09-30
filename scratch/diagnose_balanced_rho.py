import sys
import os
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_balanced import Level11ManifoldGroup, BalancedSequencer, MHRALevel11ProcessingManifold, SemanticManifold, UniversalManifold, Instruction, run_level11_trial

def run_diagnostic():
    out_path = Path("scratch/diagnose_output.txt")
    with open(out_path, "w") as f:
        baseline = 15.0
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
            n["rho"] = baseline * n.get("semanticMass", 1.0)
            
        processing = MHRALevel11ProcessingManifold(baseline_rho=baseline)
        group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
        
        group.prime_basin("Basin_Query", active=True)
        q_basin = group.semantic.basins["Basin_Query"]
        for nid in q_basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline * node.get("semanticMass", 1.0)
                
        for i in range(16):
            basin = group.semantic.basins[f"Basin_Val{i}"]
            for nid in basin.node_ids:
                node = group.get_node(nid)
                node["rho"] = baseline * node.get("semanticMass", 1.0)
                
        # Prime Register X as active
        group.prime_register_lane('X', 0, active=True)
        group.prime_register_lane('X', 1, active=True)
        group.prime_register_lane('Y', 0, active=False)
        group.prime_register_lane('Y', 1, active=False)
        
        sequencer = BalancedSequencer(group, dt=0.08, baseline_rho=baseline, query_steps=30, settle_steps=5)
        
        # Run LOAD_16 step-by-step to inspect oscillation
        f.write("\nStepping LOAD_16...\n")
        reg_name = "X"
        val = 1
        for lane in [0, 1]:
            group.engine.write_enable(f"S_R{reg_name}{lane}")
            group.engine.write_enable(f"S_R{reg_name}{lane}_B")
            group.get_node(f"S_R{reg_name}{lane}_B")["isBattery"] = True
        for i in range(16):
            group.engine.write_enable(f"Gate_Match{i}")
            bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
            group.set_edge_connection(bus_lane, f"Gate_Match{i}", False)
            
        other_reg = "Y"
        for lane in [0, 1]:
            group.get_node(f"GATE_{reg_name}{lane}")["psi_bias"] = 1.0
            group.set_edge_connection(f"GATE_{reg_name}{lane}", f"P_Bus{lane}", True)
            group.get_edge(f"GATE_{reg_name}{lane}", f"P_Bus{lane}")["w0"] = 10.0
            group.get_node(f"GATE_{other_reg}{lane}")["psi_bias"] = -1.0
            group.set_edge_connection(f"GATE_{other_reg}{lane}", f"P_Bus{lane}", False)
            
        amp = 8.0
        for s in range(60):
            t = len(sequencer.history) * sequencer.dt
            group.set_edge_connection(group.semantic.basins["Basin_Query"].bridge_id, "P_Bus0", False)
            group.set_edge_connection(group.semantic.basins["Basin_Query"].bridge_id, "P_Bus1", False)
            
            # Lane 0
            src_rho0 = baseline + amp * math.sin(sequencer.omegas[0] * t)
            group.get_node("P_Bus0")["rho"] = src_rho0
            group.get_node("P_Bus1")["rho"] = baseline
            
            group.engine.step(dt=sequencer.dt, damping=0.0)
            sequencer.record_telemetry()
            
            if s >= 40:
                rx = group.get_node("S_RX0")
                bus = group.get_node("P_Bus0")
                f.write(f"  LOAD Step {s:2d} | S_RX0 rho: {rx['rho']:.4f} | P_Bus0 rho: {bus['rho']:.4f}\n")
                
        f.write("Settle Phase...\n")
        group.engine.write_enable("P_Bus0")
        group.engine.write_enable("P_Bus1")
        for lane in [0, 1]:
            group.get_node(f"GATE_{reg_name}{lane}")["psi_bias"] = -1.0
            group.set_edge_connection(f"GATE_{reg_name}{lane}", f"P_Bus{lane}", False)
            
        for s in range(5):
            group.engine.step(dt=sequencer.dt, damping=0.0)
            sequencer.record_telemetry()
            rx = group.get_node("S_RX0")
            bus = group.get_node("P_Bus0")
            f.write(f"  Settle Step {s:2d} | S_RX0 rho: {rx['rho']:.4f} | P_Bus0 rho: {bus['rho']:.4f}\n")
            
        f.write("\nStarting QUERY tracking...\n")
        # Manual setup for QUERY_16
        group.get_node("P_Bus0")["rho"] = baseline
        group.get_node("P_Bus1")["rho"] = baseline
        for i in range(16):
            group.get_node(f"Gate_Match{i}")["rho"] = baseline
        group.engine.write_enable("P_Bus0")
        group.engine.write_enable("P_Bus1")
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                group.engine.write_enable(f"S_R{reg}{lane}")
                group.engine.write_enable(f"S_R{reg}{lane}_B")
                
        for i in range(16):
            group.engine.write_enable(f"Gate_Match{i}")
            bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
            group.set_edge_connection(bus_lane, f"Gate_Match{i}", True)
            f_idx = (i % 8) // 2
            group.get_edge(bus_lane, f"Gate_Match{i}")["w0"] = sequencer.match_weights[f_idx]
            
        active_regs = ['X']
        for n in group.processing.nodes:
            nid = n["id"]
            if nid.startswith("S_R"):
                reg = nid[3]
                if reg in active_regs:
                    group.get_node(nid)["psi_bias"] = 1.0
                else:
                    group.get_node(nid)["psi_bias"] = -1.0
            elif nid.startswith("GATE_"):
                reg = nid[5]
                if reg in active_regs:
                    group.get_node(nid)["psi_bias"] = 1.0
                else:
                    group.get_node(nid)["psi_bias"] = -1.0
            else:
                group.get_node(nid)["psi_bias"] = 0.0
                
        for i in range(16):
            basin = group.semantic.basins[f"Basin_Val{i}"]
            for nid in basin.node_ids:
                group.engine.write_enable(nid)
                group.get_node(nid)["psi_bias"] = 0.0

        f.write("Step | S_RX0 rho / p | P_Bus0 rho / p | Val0 Bridge (S9) | Val0 Hub (S0) | Val0 Spoke (S1)\n")
        f.write("-----------------------------------------------------------------------------------------\n")
        
        for s in range(120):
            t = len(sequencer.history) * sequencer.dt
            for reg in ['X', 'Y']:
                for lane in [0, 1]:
                    gate_id = f"GATE_{reg}{lane}"
                    if reg in active_regs:
                        group.get_node(gate_id)["psi_bias"] = 1.0
                        group.set_edge_connection(gate_id, f"P_Bus{lane}", True)
                        group.get_edge(gate_id, f"P_Bus{lane}")["w0"] = 10.0
                    else:
                        group.get_node(gate_id)["psi_bias"] = -1.0
                        group.set_edge_connection(gate_id, f"P_Bus{lane}", False)
                        
            for i in range(16):
                gate_id = f"Gate_Match{i}"
                basin_id = f"Basin_Val{i}"
                group.set_edge_connection(gate_id, group.semantic.basins[basin_id].bridge_id, True)
                f_idx = (i % 8) // 2
                group.get_edge(gate_id, group.semantic.basins[basin_id].bridge_id)["w0"] = sequencer.match_weights[f_idx]
                
                group.get_node(gate_id)["psi"] = math.sin(sequencer.omegas[f_idx] * t + 4.712389)
                
            group.engine.step(dt=sequencer.dt, damping=0.0)
            sequencer.record_telemetry()
            
            rx = group.get_node("S_RX0")
            bus = group.get_node("P_Bus0")
            b0_bridge = group.get_node("S9")
            b0_hub = group.get_node("S0")
            b0_spoke = group.get_node("S1")
            
            f.write(f"{s:4d} | {rx['rho']:5.1f}/{rx['p']:4.2f}  | {bus['rho']:5.1f}/{bus['p']:4.2f}  | {b0_bridge['rho']:7.3f}/{b0_bridge['p']:4.2f} (sm={b0_bridge.get('semanticMass')}) | {b0_hub['rho']:6.1f}/{b0_hub['p']:4.2f} (sm={b0_hub.get('semanticMass')}) | {b0_spoke['rho']:6.1f}/{b0_spoke['p']:4.2f} (sm={b0_spoke.get('semanticMass')})\n")

if __name__ == "__main__":
    out_path = Path("scratch/diagnose_output.txt")
    run_diagnostic()
    phases = [0.0] * 16
    phases[0] = 4.712389
    deltas, history = run_level11_trial(1, 0, phases, 15.0, 120, 5)
    print("Deltas returned by run_level11_trial:")
    for i in range(16):
        print(f"  Bit {i:2d}: {deltas[i]:+.4f}")
