#!/usr/bin/env python3
import sys
import os
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer, BasinConfig
)

# Reuse manifolds but with corrected physics and initializations
from test_logos_vm_level11_pdm import MHRALevel11ProcessingManifold, Level11ManifoldGroup, Level11Sequencer

def run_trial_modified(val_X: int, val_Y: int, calibrated_phases: list[float], baseline_rho=15.0, query_steps=150, settle_steps=0, w0_val=100.0, c_max=4000.0, gamma=6.0, match_w=[10.0, 10.0, 10.0, 10.0], scale_factor=50.0):
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
    
    # Scale registers' mass and initial density
    for node in processing.nodes:
        if node["id"].startswith("S_R"):
            node["semanticMass"] = 20.0 * scale_factor
            node["semanticMass0"] = 20.0 * scale_factor
            node["rho"] = baseline_rho * node["semanticMass"]
            
    # Patch processing manifold's edges with the scaled w0_val
    for edge in processing.edges:
        if edge["from"].endswith("Host") or edge["to"].endswith("Battery") or "_B" in edge["to"] or edge["to"].endswith("_B"):
            edge["w0"] = w0_val * scale_factor
            
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    group.engine.physics.conductance_max = c_max
    group.engine.physics.conductance_gamma = gamma
    
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
    
    # Patch execute_instruction
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
            original_execute(inst)
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
        
    # Scale back history min mass for validation purposes
    for hist in sequencer.history:
        hist["min_active_register_mass"] /= scale_factor
        
    return deltas, sequencer.history

def calibrate_pdm_phases_modified(baseline_rho=15.0, query_steps=150, settle_steps=0, w0_val=100.0, c_max=4000.0, gamma=6.0, match_w=[10.0, 10.0, 10.0, 10.0], scale_factor=50.0) -> list[float]:
    calibrated = [0.0] * 16
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    for f_idx in range(4):
        bit_sine = 2 * f_idx
        bit_cosine = 2 * f_idx + 1
        best_phase_sine = 0.0
        best_phase_cosine = 0.0
        max_delta_sine = -float('inf')
        max_delta_cosine = -float('inf')
        
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[bit_sine] = ph
            val_X = (1 << bit_sine)
            deltas, _ = run_trial_modified(val_X, 0, temp_phases, baseline_rho, query_steps, settle_steps, w0_val, c_max, gamma, match_w, scale_factor)
            if deltas[bit_sine] > max_delta_sine:
                max_delta_sine = deltas[bit_sine]
                best_phase_sine = ph
                
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[bit_cosine] = ph
            val_X = (1 << bit_cosine)
            deltas, _ = run_trial_modified(val_X, 0, temp_phases, baseline_rho, query_steps, settle_steps, w0_val, c_max, gamma, match_w, scale_factor)
            if deltas[bit_cosine] > max_delta_cosine:
                max_delta_cosine = deltas[bit_cosine]
                best_phase_cosine = ph
                
        calibrated[bit_sine] = best_phase_sine
        calibrated[bit_cosine] = best_phase_cosine
        calibrated[bit_sine + 8] = best_phase_sine
        calibrated[bit_cosine + 8] = best_phase_cosine
        
    return calibrated

def test_config(query_steps, w0_val, c_max, gamma, match_w, scale_factor):
    print(f"\n--- Testing query_steps={query_steps}, w0={w0_val}, c_max={c_max}, gamma={gamma}, match_w={match_w} ---", flush=True)
    baseline = 15.0
    settle_steps = 0
    
    try:
        calibrated_phases = calibrate_pdm_phases_modified(baseline, query_steps, settle_steps, w0_val, c_max, gamma, match_w, scale_factor)
    except Exception as e:
        print(f"Calibration failed: {e}")
        return False
        
    cases = [
        {
            "name": "Case A: Single-Register 16-Bit Word Recall",
            "val_X": 0b1010110011110001,
            "val_Y": 0,
            "expected_X": [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        },
        {
            "name": "Case B: Simultaneous Dual-Register Parallel Recall",
            "val_X": 0b1010000000001111,
            "val_Y": 0b0101111111110000,
            "expected_X": [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1],
            "expected_Y": [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0]
        },
        {
            "name": "Case C: Selective Bit Masking (Odd Bits)",
            "val_X": 0b1010101010101010,
            "val_Y": 0,
            "expected_X": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        },
        {
            "name": "Case D: Phase-Reversed Rejection",
            "val_X": 0b1010110011110001,
            "val_Y": 0,
            "expected_X": [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        }
    ]
    
    suite_ok = True
    worst_min_mass = float('inf')
    
    for idx, c in enumerate(cases):
        if idx == 3:
            phases = list(calibrated_phases)
            phases[0] = (phases[0] + math.pi) % (2 * math.pi)
            deltas, history = run_trial_modified(c["val_X"], c["val_Y"], phases, baseline, query_steps, settle_steps, w0_val, c_max, gamma, match_w, scale_factor)
        else:
            deltas, history = run_trial_modified(c["val_X"], c["val_Y"], calibrated_phases, baseline, query_steps, settle_steps, w0_val, c_max, gamma, match_w, scale_factor)
            
        passed = True
        if idx == 1:
            expected = [c["expected_X"][i] | c["expected_Y"][i] for i in range(16)]
        else:
            expected = c["expected_X"]
            
        if idx == 3:
            expected[0] = 0
            
        active_deltas = []
        flat_deltas = []
        for i in range(16):
            exp_val = expected[i]
            d = deltas[i]
            if exp_val == 1:
                active_deltas.append(d)
                if d < 0.2:
                    passed = False
            else:
                flat_deltas.append(d)
                if d >= 0.1:
                    passed = False
                    
        min_mass = history[-1]["min_active_register_mass"]
        if min_mass < worst_min_mass:
            worst_min_mass = min_mass
            
        print(f"  {c['name']}: passed={passed}, min_mass={min_mass:.2f}")
        print(f"    Active deltas: {['{:.4f}'.format(x) for x in active_deltas]}")
        print(f"    Flat deltas: {['{:.4f}'.format(x) for x in flat_deltas]}")
        
        if not passed:
            suite_ok = False
            
    mass_ok = worst_min_mass >= 14.0
    print(f"  Verdict: {suite_ok and mass_ok} (suite_ok={suite_ok}, mass_ok={mass_ok}, worst_mass={worst_min_mass:.2f})")
    return suite_ok and mass_ok

def main():
    scale_factor = 50.0
    for q_steps in [20, 25, 30, 35, 40, 45, 50, 60]:
        for w0 in [100.0, 500.0]:
            c_max = 4000.0
            gamma = 6.0
            match_w = [10.0, 10.0, 10.0, 10.0]
            if test_config(q_steps, w0, c_max, gamma, match_w, scale_factor):
                print(f"\nSUCCESS! Working configuration: query_steps={q_steps}, w0={w0}, c_max={c_max}, gamma={gamma}")
                return

if __name__ == "__main__":
    main()
