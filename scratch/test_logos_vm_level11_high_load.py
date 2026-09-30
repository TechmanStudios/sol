#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL LogosVM Level 11 PDM Verification (High Load Baseline & Active Battery)
================================================================================
"""
import sys
import os
import json
import math
import time
from pathlib import Path
from typing import Any, Optional

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_battery_pdm import Level11ManifoldGroup, MHRALevel11ProcessingManifold, SemanticManifold, UniversalManifold, Instruction, Level11Sequencer

class HighLoadSequencer(Level11Sequencer):
    def execute_instruction(self, inst: Instruction):
        op = inst.op.upper()
        if op == "LOAD_16":
            reg_name = inst.args[0]
            val = int(inst.args[1])
            
            for lane in [0, 1]:
                self.group.engine.write_enable(f"S_R{reg_name}{lane}")
                self.group.engine.write_enable(f"S_R{reg_name}{lane}_B")
                self.group.get_node(f"S_R{reg_name}{lane}_B")["isBattery"] = True
                
            for i in range(16):
                self.group.engine.write_enable(f"Gate_Match{i}")
                
            for nid in self.group.semantic.basins["Basin_Query"].node_ids:
                self.group.engine.write_enable(nid)
                
            for i in range(16):
                bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
                self.group.set_edge_connection(bus_lane, f"Gate_Match{i}", False)
                
            other_reg = "Y" if reg_name == "X" else "X"
            for lane in [0, 1]:
                self.group.get_node(f"GATE_{reg_name}{lane}")["psi_bias"] = 1.0
                self.group.set_edge_connection(f"GATE_{reg_name}{lane}", f"P_Bus{lane}", True)
                self.group.get_edge(f"GATE_{reg_name}{lane}", f"P_Bus{lane}")["w0"] = 10.0
                
                self.group.get_node(f"GATE_{other_reg}{lane}")["psi_bias"] = -1.0
                self.group.set_edge_connection(f"GATE_{other_reg}{lane}", f"P_Bus{lane}", False)
                
            amp = 8.0
            load_baseline = 200.0
            
            for s in range(60):
                t = len(self.history) * self.dt
                self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus0", False)
                self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus1", False)
                
                num_active0 = sum(1 for b in range(8) if (val & (1 << b)))
                src_rho0 = load_baseline
                if num_active0 > 0:
                    sum_sin0 = 0.0
                    for b in range(8):
                        if (val & (1 << b)):
                            f_idx = b // 2
                            is_cosine = (b % 2 == 1)
                            phase_offset = 0.5 * math.pi if is_cosine else 0.0
                            sum_sin0 += math.sin(self.omegas[f_idx] * t + phase_offset)
                    src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
                    
                num_active1 = sum(1 for b in range(8, 16) if (val & (1 << b)))
                src_rho1 = load_baseline
                if num_active1 > 0:
                    sum_sin1 = 0.0
                    for b in range(8, 16):
                        if (val & (1 << b)):
                            f_idx = (b - 8) // 2
                            is_cosine = (b % 2 == 1)
                            phase_offset = 0.5 * math.pi if is_cosine else 0.0
                            sum_sin1 += math.sin(self.omegas[f_idx] * t + phase_offset)
                    src_rho1 += (amp / math.sqrt(num_active1)) * sum_sin1
                    
                self.group.get_node("P_Bus0")["rho"] = src_rho0
                self.group.get_node("P_Bus1")["rho"] = src_rho1
                
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            for lane in [0, 1]:
                self.group.get_node(f"GATE_{reg_name}{lane}")["psi_bias"] = -1.0
                self.group.set_edge_connection(f"GATE_{reg_name}{lane}", f"P_Bus{lane}", False)
                
            self.group.engine.write_enable("P_Bus0")
            self.group.engine.write_enable("P_Bus1")
            
            for s in range(self.settle_steps):
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
        elif op == "QUERY_16":
            # KEEP isBattery = True by NOT setting it to False!
            
            self.group.engine.write_enable("P_Bus0")
            self.group.engine.write_enable("P_Bus1")
            for reg in ['X', 'Y']:
                for lane in [0, 1]:
                    self.group.engine.write_enable(f"S_R{reg}{lane}")
                    self.group.engine.write_enable(f"S_R{reg}{lane}_B")
                    
            for i in range(16):
                self.group.engine.write_enable(f"Gate_Match{i}")
                bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
                self.group.set_edge_connection(bus_lane, f"Gate_Match{i}", True)
                f_idx = (i % 8) // 2
                self.group.get_edge(bus_lane, f"Gate_Match{i}")["w0"] = self.match_weights[f_idx]
                
            for n in self.group.processing.nodes:
                self.group.get_node(n["id"])["psi_bias"] = 0.0
                
            for i in range(16):
                basin = self.group.semantic.basins[f"Basin_Val{i}"]
                for nid in basin.node_ids:
                    self.group.engine.write_enable(nid)
                    self.group.get_node(nid)["psi_bias"] = 0.0
                    
            active_regs = []
            for reg in ['X', 'Y']:
                active_lanes = 0
                for lane in [0, 1]:
                    bat = self.group.get_node(f"S_R{reg}{lane}_B")
                    if bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.1:
                        active_lanes += 1
                if active_lanes > 0:
                    active_regs.append(reg)
                    
            for s in range(self.query_steps):
                t = len(self.history) * self.dt
                for reg in ['X', 'Y']:
                    for lane in [0, 1]:
                        gate_id = f"GATE_{reg}{lane}"
                        if reg in active_regs:
                            self.group.get_node(gate_id)["psi_bias"] = 1.0
                            self.group.set_edge_connection(gate_id, f"P_Bus{lane}", True)
                            self.group.get_edge(gate_id, f"P_Bus{lane}")["w0"] = 10.0
                        else:
                            self.group.get_node(gate_id)["psi_bias"] = -1.0
                            self.group.set_edge_connection(gate_id, f"P_Bus{lane}", False)
                            
                for i in range(16):
                    gate_id = f"Gate_Match{i}"
                    basin_id = f"Basin_Val{i}"
                    self.group.set_edge_connection(gate_id, self.group.semantic.basins[basin_id].bridge_id, True)
                    f_idx = (i % 8) // 2
                    self.group.get_edge(gate_id, self.group.semantic.basins[basin_id].bridge_id)["w0"] = self.match_weights[f_idx]
                    
                    self.group.get_node(gate_id)["psi"] = math.sin(self.omegas[f_idx] * t + self.calibrated_phases[i])
                    
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            for s in range(15):
                for reg in ['X', 'Y']:
                    for lane in [0, 1]:
                        self.group.get_node(f"GATE_{reg}{lane}")["psi_bias"] = -1.0
                        self.group.set_edge_connection(f"GATE_{reg}{lane}", f"P_Bus{lane}", False)
                for i in range(16):
                    self.group.set_edge_connection(f"Gate_Match{i}", self.group.semantic.basins[f"Basin_Val{i}"].bridge_id, False)
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()

def run_level11_trial(val_X: int, val_Y: int, calibrated_phases: list[float], baseline_rho=15.0, query_steps=45, settle_steps=5) -> tuple[list[float], list[dict]]:
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
        n["rho"] = baseline_rho
        
    processing = MHRALevel11ProcessingManifold(baseline_rho=baseline_rho)
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 300.0
        else:
            node["rho"] = baseline_rho
            
    for i in range(16):
        basin = group.semantic.basins[f"Basin_Val{i}"]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline_rho
            
    active_X = (val_X != 0)
    active_Y = (val_Y != 0)
    
    for lane in [0, 1]:
        group.prime_register_lane('X', lane, active=active_X)
        group.prime_register_lane('Y', lane, active=active_Y)
        
    sequencer = HighLoadSequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps)
    sequencer.calibrated_phases = calibrated_phases
    
    if active_X:
        sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    if active_Y:
        sequencer.execute_instruction(Instruction("LOAD_16", ["Y", val_Y]))
        
    sequencer.execute_instruction(Instruction("QUERY_16", []))
    
    deltas = []
    for i in range(16):
        dest_id = group.semantic.basins[f"Basin_Val{i}"].bridge_id
        delta = group.get_node(dest_id)["rho"] - baseline_rho
        deltas.append(delta)
        
    for reg in ['X', 'Y']:
        for lane in [0, 1]:
            bat = group.get_node(f"S_R{reg}{lane}_B")
            host = group.get_node(f"S_R{reg}{lane}")
            bat["isBattery"] = True
            bat["b_state"] = -1
            bat["b_charge"] = 0.0
            bat["psi"] = -1.0
            bat["psi_bias"] = -1.0
            host["psi"] = -1.0
            host["psi_bias"] = -1.0
            host["rho"] = 5.0
            bat["rho"] = 0.0
            
    return deltas, sequencer.history

def calibrate_pdm_phases(baseline_rho=15.0, query_steps=45, settle_steps=5) -> list[float]:
    print("Starting automatic phase calibration for Level 11 PDM (High Load & Active Battery)...", flush=True)
    calibrated = [0.0] * 16
    
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    for f_idx in range(4):
        p = [6.0, 8.0, 10.0, 12.0][f_idx]
        print(f"  Calibrating frequency channel period {p}...", flush=True)
        
        bit_sine = 2 * f_idx
        bit_cosine = 2 * f_idx + 1
        
        best_phase_sine = 0.0
        best_phase_cosine = 0.0
        max_delta_sine = -float('inf')
        max_delta_cosine = -float('inf')
        
        for idx, ph in enumerate(phases):
            temp_phases = [0.0] * 16
            temp_phases[bit_sine] = ph
            val_X = (1 << bit_sine)
            deltas, _ = run_level11_trial(val_X, 0, temp_phases, baseline_rho, query_steps, settle_steps)
            if deltas[bit_sine] > max_delta_sine:
                max_delta_sine = deltas[bit_sine]
                best_phase_sine = ph
                
        for idx, ph in enumerate(phases):
            temp_phases = [0.0] * 16
            temp_phases[bit_cosine] = ph
            val_X = (1 << bit_cosine)
            deltas, _ = run_level11_trial(val_X, 0, temp_phases, baseline_rho, query_steps, settle_steps)
            if deltas[bit_cosine] > max_delta_cosine:
                max_delta_cosine = deltas[bit_cosine]
                best_phase_cosine = ph
                
        print(f"    Sine Match (Bit {bit_sine}):   phase = {best_phase_sine:.6f} ({best_phase_sine/math.pi:.4f} * pi), max_delta = {max_delta_sine:+.4f}", flush=True)
        print(f"    Cosine Match (Bit {bit_cosine}): phase = {best_phase_cosine:.6f} ({best_phase_cosine/math.pi:.4f} * pi), max_delta = {max_delta_cosine:+.4f}", flush=True)
        
        calibrated[bit_sine] = best_phase_sine
        calibrated[bit_cosine] = best_phase_cosine
        calibrated[bit_sine + 8] = best_phase_sine
        calibrated[bit_cosine + 8] = best_phase_cosine
        
    print("PDM Phase Calibration Complete.", flush=True)
    return calibrated

def main():
    print("==========================================================================", flush=True)
    print("  SOL LOGOSVM LEVEL 11 PDM VERIFICATION (HIGH LOAD + ACTIVE BATTERY)")
    print("==========================================================================", flush=True)
    
    baseline = 15.0
    query_steps = 30
    settle_steps = 5
    
    calibrated_phases = calibrate_pdm_phases(baseline, query_steps, settle_steps)
    
    print("\nStarting Verification Cases...", flush=True)
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
    
    results = []
    suite_ok = True
    worst_min_mass = float('inf')
    
    for idx, c in enumerate(cases):
        print(f"\nTrial {idx+1}/{len(cases)}: {c['name']}...", flush=True)
        
        if idx == 3: # Case D
            phases = list(calibrated_phases)
            phases[0] = (phases[0] + math.pi) % (2 * math.pi)
            deltas, history = run_level11_trial(c["val_X"], c["val_Y"], phases, baseline, query_steps, settle_steps)
        else:
            deltas, history = run_level11_trial(c["val_X"], c["val_Y"], calibrated_phases, baseline, query_steps, settle_steps)
            
        passed = True
        
        if idx == 1: # Case B
            expected = [c["expected_X"][i] | c["expected_Y"][i] for i in range(16)]
        else:
            expected = c["expected_X"]
            
        if idx == 3: # Case D
            expected[0] = 0
            
        print("  Bit verification:", flush=True)
        for i in range(16):
            exp_val = expected[i]
            d = deltas[i]
            if exp_val == 1:
                if d < 0.2:
                    passed = False
                    print(f"    [FAIL] Bit {i:2d} (Active): delta = {d:+.4f} (expected >= 0.2)", flush=True)
                else:
                    print(f"    [PASS] Bit {i:2d} (Active): delta = {d:+.4f}", flush=True)
            else:
                if d >= 0.1:
                    passed = False
                    print(f"    [FAIL] Bit {i:2d} (Flat):   delta = {d:+.4f} (expected < 0.1)", flush=True)
                else:
                    print(f"    [PASS] Bit {i:2d} (Flat):   delta = {d:+.4f}", flush=True)
                    
        min_mass = history[-1]["min_active_register_mass"]
        if min_mass < worst_min_mass:
            worst_min_mass = min_mass
            
        print(f"  Result: Passed={passed} | min_mass={min_mass:.2f}", flush=True)
        results.append({
            "name": c["name"], "passed": passed, "min_mass": min_mass, "deltas": deltas
        })
        if not passed:
            suite_ok = False
            
    mass_ok = worst_min_mass >= 14.0
    if not mass_ok:
        print(f"  [WARNING] Worst-case active register mass: {worst_min_mass:.2f} (expected >= 14.0)", flush=True)
        
    assert suite_ok and mass_ok, "Level 11 Verification Suite Failed"
    print("\nSUITE PASSED SUCCESSFULLY!", flush=True)

if __name__ == "__main__":
    main()
