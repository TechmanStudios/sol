#!/usr/bin/env python3
import sys
import math
import time
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer
)
from test_pdm_search import MHRALevel11ProcessingManifold, Level11ManifoldGroup, Level11Sequencer

def run_suite():
    class CustomSequencer(Level11Sequencer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.is_calibrating = False
            self.is_loading = False
            self.bus_densities = []

        def get_reg_gate_params(self, b: int) -> tuple[float, float]:
            b_local = b % 8
            f_idx = b_local // 2
            omega = self.omegas[f_idx]
            is_cosine = (b_local % 2 == 1)
            phase_offset = 0.5 * math.pi if is_cosine else 0.0
            
            if self.is_calibrating:
                phase = 0.0
            else:
                phase = phase_offset
            return omega, phase

        def get_match_gate_params(self, b: int) -> tuple[float, float]:
            b_local = b % 8
            f_idx = b_local // 2
            omega = self.omegas[f_idx]
            is_cosine = (b_local % 2 == 1)
            phase_offset = 0.5 * math.pi if is_cosine else 0.0
            
            if self.is_calibrating:
                phase = self.calibrated_phases[b]
            else:
                phase = self.calibrated_phases[b] + phase_offset
            return omega, phase

        def execute_instruction(self, inst: Instruction):
            op = inst.op.upper()
            if op == "LOAD_16":
                self.is_loading = True
                reg_name = inst.args[0]
                val = int(inst.args[1])
                other_reg = "Y" if reg_name == "X" else "X"
                
                for b in range(16):
                    host = self.group.get_node(f"S_R{reg_name}_Bit{b}")
                    bat = self.group.get_node(f"S_R{reg_name}_Bit{b}_B")
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
                    bat["isBattery"] = False
                    host["psi_bias"] = 0.0
                    bat["psi_bias"] = 0.0
                    self.group.engine.write_lock(f"S_R{other_reg}_Bit{b}")
                    self.group.engine.write_lock(f"S_R{other_reg}_Bit{b}_B")
                    
                for b in range(16):
                    self.group.engine.write_enable(f"Gate_Match{b}")
                    lane = b // 8
                    self.group.set_edge_connection(f"P_Bus{lane}", f"Gate_Match{b}", False)
                    
                for nid in self.group.semantic.basins["Basin_Query"].node_ids:
                    self.group.engine.write_enable(nid)
                    
                for b in range(16):
                    lane = b // 8
                    g_target = f"GATE_{reg_name}_Bit{b}"
                    if (val & (1 << b)):
                        self.group.set_edge_connection(g_target, f"P_Bus{lane}", True)
                        self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 50.0
                        self.group.engine.write_enable(g_target)
                    else:
                        self.group.get_node(g_target)["psi_bias"] = -1.0
                        self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                        
                    g_other = f"GATE_{other_reg}_Bit{b}"
                    self.group.get_node(g_other)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_other, f"P_Bus{lane}", False)
                    
                amp = 8.0
                
                for s in range(150):
                    t = len(self.history) * self.dt
                    self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus0", False)
                    self.group.set_edge_connection(self.group.semantic.basins["Basin_Query"].bridge_id, "P_Bus1", False)
                    
                    for b in range(16):
                        if (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            val_psi = 0.3 * math.sin(omega * t + phase_val)
                            g_target = f"GATE_{reg_name}_Bit{b}"
                            self.group.get_node(g_target)["psi"] = val_psi
                            self.group.get_node(g_target)["psi_bias"] = val_psi
                                
                    # Lane 0
                    num_active0 = sum(1 for b in range(8) if (val & (1 << b)))
                    src_rho0 = 15.0
                    if num_active0 > 0:
                        sum_sin0 = 0.0
                        for b in range(8):
                            if (val & (1 << b)):
                                omega, phase_val = self.get_reg_gate_params(b)
                                sum_sin0 += math.sin(omega * t + phase_val)
                        p_amp0 = amp / math.sqrt(num_active0)
                        src_rho0 = 16.0 * math.exp(0.5 * p_amp0 * sum_sin0) - 1.0
                        
                    # Lane 1
                    num_active1 = sum(1 for b in range(8, 16) if (val & (1 << b)))
                    src_rho1 = 15.0
                    if num_active1 > 0:
                        sum_sin1 = 0.0
                        for b in range(8, 16):
                            if (val & (1 << b)):
                                omega, phase_val = self.get_reg_gate_params(b)
                                sum_sin1 += math.sin(omega * t + phase_val)
                        p_amp1 = amp / math.sqrt(num_active1)
                        src_rho1 = 16.0 * math.exp(0.5 * p_amp1 * sum_sin1) - 1.0
                        
                    self.group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
                    self.group.get_node("P_Bus1")["rho"] = max(1.0, src_rho1)
                    
                    self.group.engine.step(dt=self.dt, damping=self.load_damping)
                    self.record_telemetry()
                    
                for b in range(16):
                    lane = b // 8
                    g_target = f"GATE_{reg_name}_Bit{b}"
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                    
                self.group.engine.write_enable("P_Bus0")
                self.group.engine.write_enable("P_Bus1")
                
                for s in range(self.settle_steps):
                    self.group.engine.step(dt=self.dt, damping=0.0)
                    self.record_telemetry()
                self.is_loading = False
                
            elif op == "QUERY_16":
                self.group.get_node("P_Bus0")["rho"] = self.baseline_rho
                self.group.get_node("P_Bus1")["rho"] = self.baseline_rho
                for b in range(16):
                    self.group.get_node(f"Gate_Match{b}")["rho"] = self.baseline_rho
                    
                active_regs = []
                for reg in ['X', 'Y']:
                    is_active = False
                    for b in range(16):
                        bat = self.group.get_node(f"S_R{reg}_Bit{b}_B")
                        if bat["rho"] > 2.0 * self.baseline_rho:
                            is_active = True
                            break
                    if is_active:
                        active_regs.append(reg)
                        
                self.group.engine.write_enable("P_Bus0")
                self.group.engine.write_enable("P_Bus1")
                for reg in ['X', 'Y']:
                    for b in range(16):
                        self.group.engine.write_enable(f"S_R{reg}_Bit{b}")
                        self.group.engine.write_enable(f"S_R{reg}_Bit{b}_B")
                        self.group.engine.write_enable(f"GATE_{reg}_Bit{b}")
                        self.group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = False
                        
                for b in range(16):
                    gate_id = f"Gate_Match{b}"
                    self.group.engine.write_enable(gate_id)
                    lane = b // 8
                    self.group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
                    f_idx = (b % 8) // 2
                    self.group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = self.match_weights[f_idx]
                    self.group.get_node(gate_id)["psi_bias"] = 0.0
                    
                for reg in ['X', 'Y']:
                    for b in range(16):
                        self.group.get_node(f"S_R{reg}_Bit{b}")["psi_bias"] = 0.0
                        self.group.get_node(f"S_R{reg}_Bit{b}_B")["psi_bias"] = 0.0
                self.group.get_node("P_Bus0")["psi_bias"] = 0.0
                self.group.get_node("P_Bus1")["psi_bias"] = 0.0
                
                for b in range(16):
                    basin = self.group.semantic.basins[f"Basin_Val{b}"]
                    for nid in basin.node_ids:
                        self.group.engine.write_enable(nid)
                        self.group.get_node(nid)["psi_bias"] = 0.0
                        
                for s in range(self.query_steps):
                    t = len(self.history) * self.dt
                    for reg in ['X', 'Y']:
                        for b in range(16):
                            lane = b // 8
                            g_active = f"GATE_{reg}_Bit{b}"
                            
                            if reg in active_regs:
                                omega, phase_val = self.get_reg_gate_params(b)
                                val_psi = 0.3 * math.sin(omega * t + phase_val)
                                self.group.get_node(g_active)["psi"] = val_psi
                                self.group.get_node(g_active)["psi_bias"] = val_psi
                                self.group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                                self.group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 50.0
                            else:
                                self.group.get_node(g_active)["psi_bias"] = -1.0
                                self.group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                                
                    for b in range(16):
                        gate_id = f"Gate_Match{b}"
                        dest_basin_id = f"Basin_Val{b}"
                        
                        self.group.set_edge_connection(gate_id, self.group.semantic.basins[dest_basin_id].bridge_id, True)
                        f_idx = (b % 8) // 2
                        self.group.get_edge(gate_id, self.group.semantic.basins[dest_basin_id].bridge_id)["w0"] = self.match_weights[f_idx]
                        
                        omega, phase_val = self.get_match_gate_params(b)
                        val_psi = 0.3 * math.sin(omega * t + phase_val)
                        self.group.get_node(gate_id)["psi"] = val_psi
                        self.group.get_node(gate_id)["psi_bias"] = val_psi
                        
                    self.group.engine.step(dt=self.dt, damping=0.0)
                    self.record_telemetry()
                    self.bus_densities.append(self.group.get_node("P_Bus0")["rho"])
                    
                for s in range(20):
                    for reg in ['X', 'Y']:
                        for b in range(16):
                            lane = b // 8
                            g_active = f"GATE_{reg}_Bit{b}"
                            self.group.get_node(g_active)["psi_bias"] = -1.0
                            self.group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                            
                    for b in range(16):
                        gate_id = f"Gate_Match{b}"
                        self.group.set_edge_connection(gate_id, self.group.semantic.basins[f"Basin_Val{b}"].bridge_id, False)
                        
                    self.group.engine.step(dt=self.dt, damping=0.0)
                    self.record_telemetry()

    def run_custom_trial(val_X, val_Y, phases, is_calibrating=False, baseline_rho=15.0):
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
        group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0, cond_max=1000.0)
        
        def custom_prime_register(reg_name: str, active: bool, baseline_rho=15.0):
            for b in range(16):
                host = group.get_node(f"S_R{reg_name}_Bit{b}")
                bat = group.get_node(f"S_R{reg_name}_Bit{b}_B")
                host["rho"] = baseline_rho
                bat["rho"] = baseline_rho
                if active:
                    bat["b_state"] = 1
                    bat["b_charge"] = 1.0
                    bat["psi"] = 1.0
                    bat["psi_bias"] = 1.0
                    host["psi"] = 1.0
                    host["psi_bias"] = 1.0
                else:
                    bat["b_state"] = -1
                    bat["b_charge"] = 0.0
                    bat["psi"] = -1.0
                    bat["psi_bias"] = -1.0
                    host["psi"] = -1.0
                    host["psi_bias"] = -1.0
        group.prime_register = custom_prime_register
        
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
                
        active_X = (val_X != 0)
        active_Y = (val_Y != 0)
        
        group.prime_register('X', active=active_X, baseline_rho=baseline_rho)
        group.prime_register('Y', active=active_Y, baseline_rho=baseline_rho)
            
        sequencer = CustomSequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=120, settle_steps=15)
        sequencer.calibrated_phases = phases
        sequencer.is_calibrating = is_calibrating
        
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
        return deltas, sequencer.history

    print("Calibrating custom phases using symmetry...", flush=True)
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    calibrated_phases = [0.0] * 16
    
    # Calibrate only unique frequencies
    for b in [0, 2, 4, 6]:
        best_phase = 0.0
        max_delta = -float('inf')
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[b] = ph
            val_X = (1 << b)
            deltas, _ = run_custom_trial(val_X, 0, temp_phases, is_calibrating=True)
            if deltas[b] > max_delta:
                max_delta = deltas[b]
                best_phase = ph
        calibrated_phases[b] = best_phase
        
    # Extrapolate to sines/cosines
    calibrated_phases[1] = calibrated_phases[0]
    calibrated_phases[3] = calibrated_phases[2]
    calibrated_phases[5] = calibrated_phases[4]
    calibrated_phases[7] = calibrated_phases[6]
    
    # Extrapolate to Lane 1 using symmetry
    for b in range(8):
        calibrated_phases[b + 8] = calibrated_phases[b]
        
    print(f"Calibration Complete. Calibrated phases: {calibrated_phases}\n", flush=True)
    
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
        print(f"Running {c['name']}...", flush=True)
        if idx == 3:
            phases_trial = list(calibrated_phases)
            # Flip phase on bit 0 to verify rejection
            phases_trial[0] = (phases_trial[0] + math.pi) % (2 * math.pi)
            deltas, history = run_custom_trial(c["val_X"], c["val_Y"], phases_trial, is_calibrating=False)
        else:
            deltas, history = run_custom_trial(c["val_X"], c["val_Y"], calibrated_phases, is_calibrating=False)
            
        passed = True
        if idx == 1:
            expected = [c["expected_X"][i] | c["expected_Y"][i] for i in range(16)]
        else:
            expected = c["expected_X"]
            
        if idx == 3:
            expected[0] = 0
            
        for b in range(16):
            exp = expected[b]
            act = "Active" if exp else "Flat"
            status = "PASS" if (exp == 1 and deltas[b] >= 0.2) or (exp == 0 and deltas[b] < 0.1) else "FAIL"
            if status == "FAIL":
                passed = False
            print(f"  Bit {b:2d} ({act}): delta = {deltas[b]:+.6f} | Status = {status}", flush=True)
            
        min_mass = history[-1]["min_active_register_mass"]
        if min_mass < worst_min_mass:
            worst_min_mass = min_mass
            
        print(f"Result for {c['name']}: {'PASS' if passed else 'FAIL'} | Min register mass = {min_mass:.4f}\n", flush=True)
        if not passed:
            suite_ok = False
            
    print("=======================================", flush=True)
    print(f"Suite Status: {'PASS' if suite_ok else 'FAIL'}", flush=True)
    print(f"Worst Register Mass: {worst_min_mass:.4f} (Threshold >= 14.0)", flush=True)
    print("=======================================", flush=True)

if __name__ == "__main__":
    run_suite()
