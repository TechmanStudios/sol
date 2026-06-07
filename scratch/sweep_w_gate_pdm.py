#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Sweep script to optimize reg_query_w0 and query_psi_amp for Level 11 PDM (Tuned Resonance).
import sys
import math
import time
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer, BasinConfig
)

class MHRALevel11ProcessingManifold:
    def __init__(self, baseline_rho=15.0):
        self.nodes = []
        self.edges = []
        
        # Registers X and Y, each running on 2 lanes (Lane 0 and Lane 1)
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                host_id = f"S_R{reg}{lane}"
                bat_id = f"S_R{reg}{lane}_B"
                self.nodes.extend([
                    {"id": host_id, "label": f"Register{reg}_Lane{lane}_Host", "group": "processing", "rho": baseline_rho * 20.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0},
                    {"id": bat_id, "label": f"Register{reg}_Lane{lane}_Battery", "group": "processing", "rho": baseline_rho * 20.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0}
                ])
                # w0 = 100.0 to tune natural frequency to omega_0 ~ 5.18 rad/s
                self.edges.append({"from": host_id, "to": bat_id, "w0": 100.0})
                
        # Register access gates connecting to P_Bus0 and P_Bus1
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                gate_id = f"GATE_{reg}{lane}"
                self.nodes.append(
                    {"id": gate_id, "label": f"Gate_{reg}{lane}", "group": "bridge", "rho": baseline_rho, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0}
                )
                
        # Dual Shared Waveguide Bus Nodes
        self.nodes.extend([
            {"id": "P_Bus0", "label": "Shared_Bus_Lane0", "group": "processing", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0},
            {"id": "P_Bus1", "label": "Shared_Bus_Lane1", "group": "processing", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0}
        ])
        
        # Connect registers to respective bus lanes
        for reg in ['X', 'Y']:
            # Lane 0 connects to P_Bus0
            self.edges.extend([
                {"from": f"S_R{reg}0", "to": f"GATE_{reg}0", "w0": 5.0},
                {"from": f"GATE_{reg}0", "to": "P_Bus0", "w0": 5.0, "kind": "wormhole", "background": False}
            ])
            # Lane 1 connects to P_Bus1
            self.edges.extend([
                {"from": f"S_R{reg}1", "to": f"GATE_{reg}1", "w0": 5.0},
                {"from": f"GATE_{reg}1", "to": "P_Bus1", "w0": 5.0, "kind": "wormhole", "background": False}
            ])
            
        # 16 matching gates (0-7 connect to P_Bus0, 8-15 connect to P_Bus1)
        for i in range(16):
            gate_id = f"Gate_Match{i}"
            self.nodes.append(
                {"id": gate_id, "label": gate_id, "group": "bridge", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0}
            )
            bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
            self.edges.append(
                {"from": bus_lane, "to": gate_id, "w0": 5.0, "kind": "wormhole", "background": False}
            )

class Level11ManifoldGroup(ManifoldGroup):
    def __init__(self, semantic: SemanticManifold, processing: MHRALevel11ProcessingManifold, c_press: float = 2.0, damping: float = 0.0):
        self.semantic = semantic
        self.processing = processing
        self.raw_nodes = []
        self.raw_nodes.extend(semantic.nodes)
        self.raw_nodes.extend(processing.nodes)
        self.raw_edges = []
        self.raw_edges.extend(semantic.edges)
        self.raw_edges.extend(processing.edges)
        
        # Connect query input basin to BOTH bus lanes (very weak background weight)
        self.raw_edges.extend([
            {"from": semantic.basins["Basin_Query"].bridge_id, "to": "P_Bus0", "w0": 0.0001, "kind": "wormhole", "background": False},
            {"from": semantic.basins["Basin_Query"].bridge_id, "to": "P_Bus1", "w0": 0.0001, "kind": "wormhole", "background": False}
        ])
        
        # Connect matching gates to target value destination basins
        for i in range(16):
            gate_id = f"Gate_Match{i}"
            basin_id = f"Basin_Val{i}"
            self.raw_edges.append(
                {"from": gate_id, "to": semantic.basins[basin_id].bridge_id, "w0": 0.0001, "kind": "wormhole", "background": False}
            )
            
        from sol_engine import SOLEngine
        self.engine = SOLEngine.from_graph(self.raw_nodes, self.raw_edges, c_press=c_press, damping=damping)
        self.engine.integration_mode = "rk4"
        self.engine.physics.conductance_max = 4000.0 # High max conductance to enable high w0
        self.engine.physics.conductance_min = 1e-7
        self.engine.physics.conductance_gamma = 6.0
        self.engine.physics.psi_diffusion = 0.0
        self.engine.physics.psi_relax_base = 8.0
        self.engine.physics.psi_global_nudge = 0.0
        self.engine.physics.jeans_cfg = None
        self.engine.physics.semantic_cfg = None
        self.engine.physics.battery_cfg = {
            "qMax": 80.0, "qThresh": 5.0, "leakLambda": 0.01, "avalancheGain": 5.0,
            "resonanceBoost": 4.0, "dampingClamp": 0.1, "flipThreshold": 0.65,
            "collapseFactor": 0.10, "resonanceDrive": 50.0, "dampingDrag": 0.3,
            "diodeResonanceOut": 1.0, "diodeResonanceIn": 1.0, "diodeDampingOut": 1.0, "diodeDampingIn": 1.0
        }

    def prime_register_lane(self, reg_name: str, lane: int, active: bool, baseline_rho=15.0):
        host = self.get_node(f"S_R{reg_name}{lane}")
        bat = self.get_node(f"S_R{reg_name}{lane}_B")
        if active:
            bat["b_state"] = 1
            bat["b_charge"] = 1.0
            bat["psi"] = 1.0
            bat["psi_bias"] = 1.0
            host["psi"] = 1.0
            host["psi_bias"] = 1.0
            host["rho"] = 300.0  # High mass register
            bat["rho"] = 300.0  # High mass register
        else:
            bat["b_state"] = -1
            bat["b_charge"] = 0.0
            bat["psi"] = -1.0
            bat["psi_bias"] = -1.0
            host["psi"] = -1.0
            host["psi_bias"] = -1.0
            host["rho"] = baseline_rho
            bat["rho"] = 0.0

class DynamicSweepSequencer(MicroInstructionSequencer):
    def __init__(self, group: Level11ManifoldGroup, dt: float = 0.08, baseline_rho=15.0, query_steps=150, settle_steps=0):
        super().__init__(group, dt)
        self.min_active_register_mass = float('inf')
        self.history = []
        self.baseline_rho = baseline_rho
        self.query_steps = query_steps
        self.settle_steps = settle_steps
        
        # Configurable parameters for sweep
        self.reg_query_w0 = 10.0
        self.query_psi_amp = 1.0
        
        # Frequencies / Periods configuration
        self.periods = [10.0, 14.0, 18.0, 22.0]
        self.omegas = [2 * math.pi / (p * self.dt) for p in self.periods]
        self.calibrated_phases = [0.0] * 16
        self.match_weights = [10.0, 10.0, 10.0, 10.0]

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
                    src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
                    
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
                
            for reg in ['X', 'Y']:
                for lane in [0, 1]:
                    self.group.get_node(f"S_R{reg}{lane}")["psi_bias"] = 0.0
                    self.group.get_node(f"S_R{reg}{lane}_B")["psi_bias"] = 0.0
            self.group.get_node("P_Bus0")["psi_bias"] = 0.0
            self.group.get_node("P_Bus1")["psi_bias"] = 0.0
            for i in range(16):
                self.group.get_node(f"Gate_Match{i}")["psi_bias"] = 0.0
                
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
                            self.group.get_edge(gate_id, f"P_Bus{lane}")["w0"] = self.reg_query_w0
                        else:
                            self.group.get_node(gate_id)["psi_bias"] = -1.0
                            self.group.set_edge_connection(gate_id, f"P_Bus{lane}", False)
                            
                for i in range(16):
                    gate_id = f"Gate_Match{i}"
                    basin_id = f"Basin_Val{i}"
                    self.group.set_edge_connection(gate_id, self.group.semantic.basins[basin_id].bridge_id, True)
                    f_idx = (i % 8) // 2
                    self.group.get_edge(gate_id, self.group.semantic.basins[basin_id].bridge_id)["w0"] = self.match_weights[f_idx]
                    
                    # Drive matching gate reference phase
                    self.group.get_node(gate_id)["psi"] = self.query_psi_amp * math.sin(self.omegas[f_idx] * t + self.calibrated_phases[i])
                    
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            for s in range(20):
                for reg in ['X', 'Y']:
                    for lane in [0, 1]:
                        self.group.get_node(f"GATE_{reg}{lane}")["psi_bias"] = -1.0
                        self.group.set_edge_connection(f"GATE_{reg}{lane}", f"P_Bus{lane}", False)
                for i in range(16):
                    self.group.set_edge_connection(f"Gate_Match{i}", self.group.semantic.basins[f"Basin_Val{i}"].bridge_id, False)
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()

    def record_telemetry(self):
        active_masses = []
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                bat = self.group.get_node(f"S_R{reg}{lane}_B")
                host = self.group.get_node(f"S_R{reg}{lane}")
                if bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.1:
                    active_masses.append(bat["rho"] + host["rho"])
                    
        if active_masses:
            min_act = min(active_masses)
            if min_act < self.min_active_register_mass:
                self.min_active_register_mass = min_act
                
        self.history.append({
            "step": len(self.history),
            "min_active_register_mass": self.min_active_register_mass if self.min_active_register_mass != float('inf') else 0.0
        })

def run_level11_trial_custom(val_X: int, val_Y: int, calibrated_phases: list[float], reg_query_w0: float, query_psi_amp: float, baseline_rho=15.0, query_steps=150, settle_steps=0) -> tuple[list[float], list[dict]]:
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
        group.prime_register_lane('X', lane, active=active_X, baseline_rho=baseline_rho)
        group.prime_register_lane('Y', lane, active=active_Y, baseline_rho=baseline_rho)
        
    sequencer = DynamicSweepSequencer(group, dt=0.08, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps)
    sequencer.reg_query_w0 = reg_query_w0
    sequencer.query_psi_amp = query_psi_amp
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
        
    # Clean register collapse
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

def calibrate_pdm_phases_custom(reg_query_w0: float, query_psi_amp: float, baseline_rho=15.0, query_steps=150, settle_steps=0) -> list[float]:
    calibrated = [0.0] * 16
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    for f_idx in range(4):
        p = [10.0, 14.0, 18.0, 22.0][f_idx]
        bit_sine = 2 * f_idx
        bit_cosine = 2 * f_idx + 1
        
        best_phase_sine = 0.0
        best_phase_cosine = 0.0
        max_delta_sine = -float('inf')
        max_delta_cosine = -float('inf')
        
        # Sweep matching phase for Sine channel
        for idx, ph in enumerate(phases):
            temp_phases = [0.0] * 16
            temp_phases[bit_sine] = ph
            val_X = (1 << bit_sine)
            deltas, _ = run_level11_trial_custom(val_X, 0, temp_phases, reg_query_w0, query_psi_amp, baseline_rho, query_steps, settle_steps)
            if deltas[bit_sine] > max_delta_sine:
                max_delta_sine = deltas[bit_sine]
                best_phase_sine = ph
                
        # Sweep matching phase for Cosine channel
        for idx, ph in enumerate(phases):
            temp_phases = [0.0] * 16
            temp_phases[bit_cosine] = ph
            val_X = (1 << bit_cosine)
            deltas, _ = run_level11_trial_custom(val_X, 0, temp_phases, reg_query_w0, query_psi_amp, baseline_rho, query_steps, settle_steps)
            if deltas[bit_cosine] > max_delta_cosine:
                max_delta_cosine = deltas[bit_cosine]
                best_phase_cosine = ph
                
        print(f"    Channel Period {p:4.1f} | Sine (Bit {bit_sine}): max_delta = {max_delta_sine:+.4f} | Cosine (Bit {bit_cosine}): max_delta = {max_delta_cosine:+.4f}", flush=True)
        
        calibrated[bit_sine] = best_phase_sine
        calibrated[bit_cosine] = best_phase_cosine
        calibrated[bit_sine + 8] = best_phase_sine
        calibrated[bit_cosine + 8] = best_phase_cosine
        
    return calibrated

def main():
    print("==========================================================================", flush=True)
    print("  SOL LOGOSVM LEVEL 11 PARAMETER SWEEP (TUNED RESONATORS + BATTERY-BACKED)")
    print("==========================================================================", flush=True)
    
    baseline = 15.0
    query_steps = 150
    settle_steps = 0
    
    # Sweep over target parameters to find optimal combination
    w0_sweep = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]
    amp_sweep = [0.12, 0.15, 0.18, 0.20, 0.25, 0.30, 0.50, 1.0]
    
    cases = [
        {
            "name": "Case A: Single-Register 16-Bit Word Recall",
            "val_X": 0b1010110011110001,
            "val_Y": 0,
            "expected_X": [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        },
        {
            "name": "Case C: Selective Bit Masking (Odd Bits)",
            "val_X": 0b1010101010101010,
            "val_Y": 0,
            "expected_X": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        }
    ]
    
    best_config = None
    
    for w0 in w0_sweep:
        for amp in amp_sweep:
            print(f"\nEvaluating combination: reg_query_w0={w0:.1f} | query_psi_amp={amp:.2f}...", flush=True)
            
            t_cal_start = time.time()
            cal_phases = calibrate_pdm_phases_custom(w0, amp, baseline, query_steps, settle_steps)
            
            cal_ok = True
            for b in range(8):
                val = (1 << b)
                deltas, _ = run_level11_trial_custom(val, 0, cal_phases, w0, amp, baseline, query_steps, settle_steps)
                if deltas[b] < 0.2:
                    cal_ok = False
                    break
                    
            if not cal_ok:
                print("  -> Calibration validation failed (at least one channel active delta < 0.2). Skipping.", flush=True)
                continue
                
            print(f"  -> Calibration validation passed in {time.time() - t_cal_start:.1f}s. Running verification cases...", flush=True)
            
            suite_passed = True
            worst_min_mass = float('inf')
            
            for c in cases:
                deltas, history = run_level11_trial_custom(c["val_X"], c["val_Y"], cal_phases, w0, amp, baseline, query_steps, settle_steps)
                expected = c["expected_X"]
                
                case_passed = True
                for i in range(16):
                    exp_val = expected[i]
                    d = deltas[i]
                    if exp_val == 1:
                        if d < 0.2:
                            case_passed = False
                            suite_passed = False
                    else:
                        if d >= 0.1:
                            case_passed = False
                            suite_passed = False
                            
                min_mass = history[-1]["min_active_register_mass"]
                if min_mass < worst_min_mass:
                    worst_min_mass = min_mass
                    
                print(f"    {c['name']}: Passed={case_passed} | min_mass={min_mass:.2f}", flush=True)
                if not case_passed:
                    print(f"      Deltas: {[f'{d:+.4f}' for d in deltas]}", flush=True)
                
            if suite_passed and worst_min_mass >= 14.0:
                print(f"*** FOUND WORKING CONFIGURATION: w0={w0}, amp={amp}, min_mass={worst_min_mass:.2f} ***", flush=True)
                best_config = {
                    "w0": w0,
                    "amp": amp,
                    "phases": cal_phases
                }
                break
        if best_config:
            break
            
    if best_config:
        print("\nSweep Complete. Optimal config found:", best_config, flush=True)
    else:
        print("\nSweep Complete. No working configuration found.", flush=True)

if __name__ == "__main__":
    main()
