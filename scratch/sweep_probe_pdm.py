#!/usr/bin/env python3
import sys
import math
import time
from pathlib import Path
from multiprocessing import Pool

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_passive import (
    Level11ManifoldGroup, MHRALevel11ProcessingManifold, Level11Sequencer,
    Instruction, UniversalManifold, SemanticManifold
)

class SweepSequencer(Level11Sequencer):
    def __init__(self, group, dt=0.08, baseline_rho=15.0, query_steps=150, settle_steps=0, load_damping=0.65, amp=8.0, match_w=10.0):
        super().__init__(group, dt, baseline_rho, query_steps, settle_steps)
        self.load_damping = load_damping
        self.amp = amp
        self.match_weights = [match_w] * 4

    def execute_instruction(self, inst):
        op = inst.op.upper()
        if op == "LOAD_16":
            reg_name = inst.args[0]
            val = int(inst.args[1])
            
            for lane in [0, 1]:
                self.group.engine.write_enable(f"S_R{reg_name}{lane}")
                self.group.engine.write_enable(f"S_R{reg_name}{lane}_B")
                self.group.get_node(f"S_R{reg_name}{lane}_B")["isBattery"] = False
                
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
                
            for s in range(60):
                t = len(self.history) * self.dt
                self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus0", False)
                self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus1", False)
                
                num_active0 = sum(1 for b in range(8) if (val & (1 << b)))
                src_rho0 = self.baseline_rho
                if num_active0 > 0:
                    sum_sin0 = 0.0
                    for b in range(8):
                        if (val & (1 << b)):
                            f_idx = b // 2
                            is_cosine = (b % 2 == 1)
                            phase_offset = 0.5 * math.pi if is_cosine else 0.0
                            sum_sin0 += math.sin(self.omegas[f_idx] * t + phase_offset)
                    src_rho0 += (self.amp / math.sqrt(num_active0)) * sum_sin0
                    
                num_active1 = sum(1 for b in range(8, 16) if (val & (1 << b)))
                src_rho1 = self.baseline_rho
                if num_active1 > 0:
                    sum_sin1 = 0.0
                    for b in range(8, 16):
                        if (val & (1 << b)):
                            f_idx = (b - 8) // 2
                            is_cosine = (b % 2 == 1)
                            phase_offset = 0.5 * math.pi if is_cosine else 0.0
                            sum_sin1 += math.sin(self.omegas[f_idx] * t + phase_offset)
                    src_rho1 += (self.amp / math.sqrt(num_active1)) * sum_sin1
                    
                self.group.get_node("P_Bus0")["rho"] = src_rho0
                self.group.get_node("P_Bus1")["rho"] = src_rho1
                
                self.group.engine.step(dt=self.dt, damping=self.load_damping)
                self.record_telemetry()
                
            for lane in [0, 1]:
                self.group.get_node(f"GATE_{reg_name}{lane}")["psi_bias"] = -1.0
                self.group.set_edge_connection(f"GATE_{reg_name}{lane}", f"P_Bus{lane}", False)
                
            self.group.engine.write_enable("P_Bus0")
            self.group.engine.write_enable("P_Bus1")
            
            for s in range(self.settle_steps):
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
        else:
            super().execute_instruction(inst)

def run_sweep_trial(val_X, val_Y, calibrated_phases, baseline_rho, query_steps, settle_steps, load_damping, amp, match_w, c_max):
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
    
    original_init = Level11ManifoldGroup.__init__
    def patched_init(self_group, sem, proc, c_press=2.0, damping=0.0):
        original_init(self_group, sem, proc, c_press, damping)
        self_group.engine.physics.conductance_max = c_max
    Level11ManifoldGroup.__init__ = patched_init
    
    try:
        group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    finally:
        Level11ManifoldGroup.__init__ = original_init
        
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
        group.prime_register_lane('X', lane, active=active_X, baseline_rho=baseline_rho)
        group.prime_register_lane('Y', lane, active=active_Y, baseline_rho=baseline_rho)
        
    sequencer = SweepSequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps, load_damping=load_damping, amp=amp, match_w=match_w)
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
            bat["isBattery"] = False
            bat["b_state"] = -1
            bat["b_charge"] = 0.0
            bat["psi"] = -1.0
            bat["psi_bias"] = -1.0
            host["psi"] = -1.0
            host["psi_bias"] = -1.0
            host["rho"] = 5.0
            bat["rho"] = 0.0
            
    return deltas, sequencer.history

def calibrate_phases(baseline_rho, query_steps, settle_steps, load_damping, amp, match_w, c_max):
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
            deltas, _ = run_sweep_trial(1 << bit_sine, 0, temp_phases, baseline_rho, query_steps, settle_steps, load_damping, amp, match_w, c_max)
            if deltas[bit_sine] > max_delta_sine:
                max_delta_sine = deltas[bit_sine]
                best_phase_sine = ph
                
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[bit_cosine] = ph
            deltas, _ = run_sweep_trial(1 << bit_cosine, 0, temp_phases, baseline_rho, query_steps, settle_steps, load_damping, amp, match_w, c_max)
            if deltas[bit_cosine] > max_delta_cosine:
                max_delta_cosine = deltas[bit_cosine]
                best_phase_cosine = ph
                
        calibrated[bit_sine] = best_phase_sine
        calibrated[bit_cosine] = best_phase_cosine
        calibrated[bit_sine + 8] = best_phase_sine
        calibrated[bit_cosine + 8] = best_phase_cosine
        
    return calibrated

def evaluate_combo(args):
    c_max, load_damping, amp, match_w, calibrated = args
    baseline = 15.0
    query_steps = 150
    settle_steps = 0
    
    try:
        # Verify Case A
        val_X = 0b1010110011110001
        expected = [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        deltas, history = run_sweep_trial(val_X, 0, calibrated, baseline, query_steps, settle_steps, load_damping, amp, match_w, c_max)
        
        passed = True
        for i in range(16):
            exp_val = expected[i]
            d = deltas[i]
            if exp_val == 1:
                if d < 0.2:
                    passed = False
                    break
            else:
                if d >= 0.1:
                    passed = False
                    break
                    
        min_mass = history[-1]["min_active_register_mass"] if history else 0.0
        if min_mass < 14.0:
            passed = False
            
        return (passed, deltas, min_mass)
    except Exception as e:
        return (False, str(e), 0.0)

def main():
    c_max = 1000.0
    load_damping = 0.65
    baseline = 15.0
    query_steps = 150
    settle_steps = 0
    
    amp_values = [2.0, 4.0, 6.0, 8.0]
    match_w_values = [1.0, 2.0, 3.0, 5.0, 10.0]
    
    calibrations = {}
    for amp in amp_values:
        print(f"Calibrating for amp={amp}...", flush=True)
        t0 = time.time()
        calibrations[amp] = calibrate_phases(baseline, query_steps, settle_steps, load_damping, amp, 10.0, c_max)
        print(f"  Calibrated phases for amp={amp} in {time.time() - t0:.2f}s", flush=True)
        print(f"  Phases: {[round(p/math.pi, 4) for p in calibrations[amp]]} * pi", flush=True)
        
    tasks = []
    for amp in amp_values:
        for match_w in match_w_values:
            tasks.append((c_max, load_damping, amp, match_w, calibrations[amp]))
            
    print(f"Running {len(tasks)} sweeps on 3 parallel workers...", flush=True)
    t0 = time.time()
    with Pool(processes=3) as pool:
        results = pool.map(evaluate_combo, tasks)
    print(f"Sweep completed in {time.time() - t0:.2f} seconds", flush=True)
    
    found_any = False
    for (c_max, load_damping, amp, match_w, _), (passed, res_data, min_mass) in zip(tasks, results):
        if passed:
            print(f"amp = {amp:3.1f} | match_w = {match_w:4.1f} -> Passed = {passed} | min_mass = {min_mass:.1f}", flush=True)
            print(f"*** FOUND WORKING COMBO: amp={amp}, match_w={match_w} ***", flush=True)
            print(f"Deltas: {[round(d, 4) for d in res_data]}")
            found_any = True
            
    if not found_any:
        print("No combinations passed Case A completely. Let's dump some results to understand what's close:", flush=True)
        for (c_max, load_damping, amp, match_w, _), (passed, res_data, min_mass) in zip(tasks, results):
            print(f"amp = {amp:3.1f} | match_w = {match_w:4.1f} -> min_mass = {min_mass:.1f}", flush=True)
            if isinstance(res_data, list):
                print(f"  Deltas: {[round(d, 4) for d in res_data]}")
            else:
                print(f"  Error: {res_data}")

if __name__ == "__main__":
    main()
