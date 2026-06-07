#!/usr/bin/env python3
import sys
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer, BasinConfig
)

from test_logos_vm_level11_pdm import MHRALevel11ProcessingManifold, Level11ManifoldGroup, Level11Sequencer
from sweep_pdm_scaled import run_trial_modified, calibrate_pdm_phases_modified

def run_trial_telemetry(val_X: int, val_Y: int, calibrated_phases: list[float], baseline_rho=15.0, query_steps=150, settle_steps=0, w0_val=100.0, c_max=4000.0, gamma=6.0, match_w=[10.0, 10.0, 10.0, 10.0], scale_factor=50.0):
    # Copy implementation of run_trial_modified but print telemetries at step 59 (end of LOAD) and during QUERY
    # Build 16 value basins + 1 query basin
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
    
    # Scale registers
    for node in processing.nodes:
        if node["id"].startswith("S_R"):
            node["semanticMass"] = 20.0 * scale_factor
            node["semanticMass0"] = 20.0 * scale_factor
            node["rho"] = baseline_rho * node["semanticMass"]
            
    for edge in processing.edges:
        if edge["from"].endswith("Host") or edge["to"].endswith("Battery") or "_B" in edge["to"] or edge["to"].endswith("_B"):
            edge["w0"] = w0_val * scale_factor
            
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    group.engine.physics.conductance_max = c_max
    group.engine.physics.conductance_gamma = gamma
    
    print("\n--- Initial Lane 1 Edge Diagnostics ---", flush=True)
    lane1_nodes = ["S_RX1", "S_RX1_B", "GATE_X1", "P_Bus1"] + [f"Gate_Match{i}" for i in range(8, 16)]
    for e in group.engine.physics.edges:
        if e["from"] in lane1_nodes or e["to"] in lane1_nodes:
            print(f"  Edge: {e['from']} -> {e['to']} | w0={e.get('w0')} | from_idx={e.get('from_idx')} | to_idx={e.get('to_idx')}", flush=True)
    print("---------------------------------------\n", flush=True)
    
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
            
    # Prime registers
    active_X = (val_X != 0)
    active_Y = (val_Y != 0)
    
    for lane in [0, 1]:
        for reg, act in [('X', active_X), ('Y', active_Y)]:
            host = group.get_node(f"S_R{reg}{lane}")
            bat = group.get_node(f"S_R{reg}{lane}_B")
            if act:
                bat["b_state"] = 1
                bat["b_charge"] = 1.0
                bat["psi"] = 1.0
                bat["psi_bias"] = 1.0
                host["psi"] = 1.0
                host["psi_bias"] = 1.0
                host["rho"] = 300.0 * scale_factor
                bat["rho"] = 300.0 * scale_factor
            else:
                bat["b_state"] = -1
                bat["b_charge"] = 0.0
                bat["psi"] = -1.0
                bat["psi_bias"] = -1.0
                host["psi"] = -1.0
                host["psi_bias"] = -1.0
                host["rho"] = baseline_rho * host["semanticMass"]
                bat["rho"] = baseline_rho * bat["semanticMass"]
                
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps)
    sequencer.calibrated_phases = calibrated_phases
    sequencer.match_weights = match_w
    
    # Patch execute_instruction to trace densities
    original_execute = sequencer.execute_instruction
    def patched_execute(inst):
        op = inst.op.upper()
        if op == "LOAD_16":
            reg_name = inst.args[0]
            val = int(inst.args[1])
            for lane in [0, 1]:
                sequencer.group.engine.write_enable(f"S_R{reg_name}{lane}")
                sequencer.group.engine.write_enable(f"S_R{reg_name}{lane}_B")
                sequencer.group.get_node(f"S_R{reg_name}{lane}_B")["isBattery"] = False
            for i in range(16):
                sequencer.group.engine.write_enable(f"Gate_Match{i}")
            for nid in sequencer.group.semantic.basins["Basin_Query"].node_ids:
                sequencer.group.engine.write_enable(nid)
            for i in range(16):
                bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
                sequencer.group.set_edge_connection(bus_lane, f"Gate_Match{i}", False)
            other_reg = "Y" if reg_name == "X" else "X"
            for lane in [0, 1]:
                sequencer.group.get_node(f"GATE_{reg_name}{lane}")["psi_bias"] = 1.0
                sequencer.group.set_edge_connection(f"GATE_{reg_name}{lane}", f"P_Bus{lane}", True)
                sequencer.group.get_edge(f"GATE_{reg_name}{lane}", f"P_Bus{lane}")["w0"] = 10.0
                sequencer.group.get_node(f"GATE_{other_reg}{lane}")["psi_bias"] = -1.0
                sequencer.group.set_edge_connection(f"GATE_{other_reg}{lane}", f"P_Bus{lane}", False)
            
            amp = 10.0
            for s in range(60):
                t = len(sequencer.history) * sequencer.dt
                sequencer.group.set_edge_connection(sequencer.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus0", False)
                sequencer.group.set_edge_connection(sequencer.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus1", False)
                
                # Lane 0
                num_active0 = sum(1 for b in range(8) if (val & (1 << b)))
                src_rho0 = sequencer.baseline_rho
                if num_active0 > 0:
                    sum_sin0 = 0.0
                    for b in range(8):
                        if (val & (1 << b)):
                            f_idx = b // 2
                            is_cosine = (b % 2 == 1)
                            phase_offset = 0.5 * math.pi if is_cosine else 0.0
                            sum_sin0 += math.sin(sequencer.omegas[f_idx] * t + phase_offset)
                    src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
                    
                # Lane 1
                num_active1 = sum(1 for b in range(8, 16) if (val & (1 << b)))
                src_rho1 = sequencer.baseline_rho
                if num_active1 > 0:
                    sum_sin1 = 0.0
                    for b in range(8, 16):
                        if (val & (1 << b)):
                            f_idx = (b - 8) // 2
                            is_cosine = (b % 2 == 1)
                            phase_offset = 0.5 * math.pi if is_cosine else 0.0
                            sum_sin1 += math.sin(sequencer.omegas[f_idx] * t + phase_offset)
                    src_rho1 += (amp / math.sqrt(num_active1)) * sum_sin1
                    
                sequencer.group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
                sequencer.group.get_node("P_Bus1")["rho"] = max(1.0, src_rho1)
                
                sequencer.group.engine.step(dt=sequencer.dt, damping=0.0)
                sequencer.record_telemetry()
                
            print(f"End of LOAD: S_RX0_rho={sequencer.group.get_node('S_RX0')['rho']:.2f}, S_RX0_B_rho={sequencer.group.get_node('S_RX0_B')['rho']:.2f}", flush=True)
            print(f"End of LOAD: S_RX1_rho={sequencer.group.get_node('S_RX1')['rho']:.2f}, S_RX1_B_rho={sequencer.group.get_node('S_RX1_B')['rho']:.2f}", flush=True)
            
            # Close active gates and settle (NO manual density addition)
            for lane in [0, 1]:
                sequencer.group.get_node(f"GATE_{reg_name}{lane}")["psi_bias"] = -1.0
                sequencer.group.set_edge_connection(f"GATE_{reg_name}{lane}", f"P_Bus{lane}", False)
                
                # Apply DC Bias Correction
                host = sequencer.group.get_node(f"S_R{reg_name}{lane}")
                bat = sequencer.group.get_node(f"S_R{reg_name}{lane}_B")
                current_avg = (host["rho"] + bat["rho"]) / 2.0
                diff = current_avg - (300.0 * scale_factor)
                host["rho"] -= diff
                bat["rho"] -= diff
                
            sequencer.group.engine.write_enable("P_Bus0")
            sequencer.group.engine.write_enable("P_Bus1")
            for s in range(sequencer.settle_steps):
                sequencer.group.engine.step(dt=sequencer.dt, damping=0.0)
                sequencer.record_telemetry()
        elif op == "QUERY_16":
            # Apply DC Bias Correction before starting query
            for reg in ['X', 'Y']:
                active_lanes = 0
                for lane in [0, 1]:
                    bat = sequencer.group.get_node(f"S_R{reg}{lane}_B")
                    if bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.1:
                        active_lanes += 1
                if active_lanes > 0:
                    for lane in [0, 1]:
                        host = sequencer.group.get_node(f"S_R{reg}{lane}")
                        bat = sequencer.group.get_node(f"S_R{reg}{lane}_B")
                        current_avg = (host["rho"] + bat["rho"]) / 2.0
                        diff = current_avg - (300.0 * scale_factor)
                        host["rho"] -= diff
                        bat["rho"] -= diff
            
            # Custom QUERY_16 execution with print tracing
            for reg in ['X', 'Y']:
                for lane in [0, 1]:
                    sequencer.group.get_node(f"S_R{reg}{lane}_B")["isBattery"] = False
            
            sequencer.group.engine.write_enable("P_Bus0")
            sequencer.group.engine.write_enable("P_Bus1")
            for reg in ['X', 'Y']:
                for lane in [0, 1]:
                    sequencer.group.engine.write_enable(f"S_R{reg}{lane}")
                    sequencer.group.engine.write_enable(f"S_R{reg}{lane}_B")
                    
            for i in range(16):
                sequencer.group.engine.write_enable(f"Gate_Match{i}")
                bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
                sequencer.group.set_edge_connection(bus_lane, f"Gate_Match{i}", True)
                f_idx = (i % 8) // 2
                sequencer.group.get_edge(bus_lane, f"Gate_Match{i}")["w0"] = sequencer.match_weights[f_idx]
                
            for reg in ['X', 'Y']:
                for lane in [0, 1]:
                    sequencer.group.get_node(f"S_R{reg}{lane}")["psi_bias"] = 0.0
                    sequencer.group.get_node(f"S_R{reg}{lane}_B")["psi_bias"] = 0.0
                    
            sequencer.group.get_node("P_Bus0")["psi_bias"] = 0.0
            sequencer.group.get_node("P_Bus1")["psi_bias"] = 0.0
            for i in range(16):
                sequencer.group.get_node(f"Gate_Match{i}")["psi_bias"] = 0.0
                
            for i in range(16):
                basin = sequencer.group.semantic.basins[f"Basin_Val{i}"]
                for nid in basin.node_ids:
                    sequencer.group.engine.write_enable(nid)
                    sequencer.group.get_node(nid)["psi"] = 0.0
                    sequencer.group.get_node(nid)["psi_bias"] = 0.0
                    
            active_regs = ["X"]
            
            print("\n--- QUERY step-by-step tracing (first 10 steps) ---", flush=True)
            for s in range(sequencer.query_steps):
                t = len(sequencer.history) * sequencer.dt
                for reg in ['X', 'Y']:
                    for lane in [0, 1]:
                        gate_id = f"GATE_{reg}{lane}"
                        host_id = f"S_R{reg}{lane}"
                        bat_id = f"S_R{reg}{lane}_B"
                        if reg in active_regs:
                            sequencer.group.get_node(gate_id)["psi_bias"] = 1.0
                            sequencer.group.set_edge_connection(gate_id, f"P_Bus{lane}", True)
                            sequencer.group.get_edge(gate_id, f"P_Bus{lane}")["w0"] = 10.0
                        else:
                            sequencer.group.get_node(gate_id)["psi_bias"] = -1.0
                            sequencer.group.set_edge_connection(gate_id, f"P_Bus{lane}", False)
                            sequencer.group.get_node(host_id)["psi"] = -1.0
                            sequencer.group.get_node(host_id)["psi_bias"] = -1.0
                            sequencer.group.get_node(bat_id)["psi"] = -1.0
                            sequencer.group.get_node(bat_id)["psi_bias"] = -1.0
                            
                for i in range(16):
                    gate_id = f"Gate_Match{i}"
                    basin_id = f"Basin_Val{i}"
                    sequencer.group.set_edge_connection(gate_id, sequencer.group.semantic.basins[basin_id].bridge_id, True)
                    f_idx = (i % 8) // 2
                    sequencer.group.get_edge(gate_id, sequencer.group.semantic.basins[basin_id].bridge_id)["w0"] = sequencer.match_weights[f_idx]
                    
                    val_psi = 0.3 * math.sin(sequencer.omegas[f_idx] * t + sequencer.calibrated_phases[i])
                    sequencer.group.get_node(gate_id)["psi"] = val_psi
                    sequencer.group.get_node(gate_id)["psi_bias"] = val_psi
                    
                sequencer.group.engine.step(dt=sequencer.dt, damping=0.0)
                sequencer.record_telemetry()
                
                if s < 10:
                    rx0_rho = sequencer.group.get_node("S_RX0")["rho"]
                    rx1_rho = sequencer.group.get_node("S_RX1")["rho"]
                    pb0_rho = sequencer.group.get_node("P_Bus0")["rho"]
                    pb1_rho = sequencer.group.get_node("P_Bus1")["rho"]
                    gm0_rho = sequencer.group.get_node("Gate_Match0")["rho"]
                    gm8_rho = sequencer.group.get_node("Gate_Match8")["rho"]
                    v0_rho = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_Val0"].bridge_id)["rho"]
                    v8_rho = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_Val8"].bridge_id)["rho"]
                    print(f"Step {s:2d}: S_RX0={rx0_rho:.2f}, S_RX1={rx1_rho:.2f} | P_Bus0={pb0_rho:.2f}, P_Bus1={pb1_rho:.2f} | Gate_Match0={gm0_rho:.2f}, Gate_Match8={gm8_rho:.2f} | Val0={v0_rho:.2f}, Val8={v8_rho:.2f}", flush=True)
                    
            for s in range(20):
                for reg in ['X', 'Y']:
                    for lane in [0, 1]:
                        sequencer.group.get_node(f"GATE_{reg}{lane}")["psi_bias"] = -1.0
                        sequencer.group.set_edge_connection(f"GATE_{reg}{lane}", f"P_Bus{lane}", False)
                for i in range(16):
                    sequencer.group.set_edge_connection(f"Gate_Match{i}", sequencer.group.semantic.basins[f"Basin_Val{i}"].bridge_id, False)
                sequencer.group.engine.step(dt=sequencer.dt, damping=0.0)
                sequencer.record_telemetry()
        else:
            original_execute(inst)
            
    sequencer.execute_instruction = patched_execute
    
    # Exec sequential loads
    if active_X:
        sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    if active_Y:
        sequencer.execute_instruction(Instruction("LOAD_16", ["Y", val_Y]))
        
    # Exec simultaneous recall
    sequencer.execute_instruction(Instruction("QUERY_16", []))
    
    deltas = []
    for i in range(16):
        dest_id = group.semantic.basins[f"Basin_Val{i}"].bridge_id
        delta = group.get_node(dest_id)["rho"] - baseline_rho
        deltas.append(delta)
        
    return deltas

def calibrate_16_phases(baseline, query_steps, settle_steps, w0_val, c_max, gamma, match_w, scale_factor):
    print("Calibrating all 16 bits independently...", flush=True)
    calibrated = [0.0] * 16
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    for i in range(16):
        print(f"  Calibrating bit {i}...", flush=True)
        best_ph = 0.0
        max_d = -999.0
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[i] = ph
            val_X = (1 << i)
            # Run trial and read delta
            deltas = run_trial_telemetry(val_X, 0, temp_phases, baseline, query_steps, settle_steps, w0_val, c_max, gamma, match_w, scale_factor)
            d = deltas[i]
            if d > max_d:
                max_d = d
                best_ph = ph
        calibrated[i] = best_ph
        print(f"    Bit {i:2d}: phase = {best_ph:.6f} ({best_ph/math.pi:.4f} * pi) | max_delta = {max_d:+.4f}", flush=True)
    return calibrated

def main():
    baseline = 15.0
    query_steps = 20
    settle_steps = 0
    w0_val = 100.0
    c_max = 4000.0
    gamma = 6.0
    match_w = [10.0, 10.0, 10.0, 10.0]
    scale_factor = 50.0
    
    calibrated_phases = calibrate_16_phases(baseline, query_steps, settle_steps, w0_val, c_max, gamma, match_w, scale_factor)
    
    print("\nRunning Case A with independent phases...", flush=True)
    val_X = 0b1010110011110001
    deltas = run_trial_telemetry(val_X, 0, calibrated_phases, baseline, query_steps, settle_steps, w0_val, c_max, gamma, match_w, scale_factor)
    print("\n--- Final Deltas ---", flush=True)
    for i, d in enumerate(deltas):
        print(f"  Bit {i:2d}: delta = {d:+.4f}", flush=True)

if __name__ == "__main__":
    main()
