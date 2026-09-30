#!/usr/bin/env python3
import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer
)
from test_pdm_search import MHRALevel11ProcessingManifold, Level11ManifoldGroup, Level11Sequencer

def run_test(cond_max, load_damping, use_press_sym, linear_load_gate, linear_query_gate, gate_coupling_w0):
    class CustomSequencer(Level11Sequencer):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.is_calibrating = False
            self.is_loading = False
            self.bus_densities = []

        def get_bit_params(self, b: int) -> tuple[float, float]:
            b_local = b % 8
            f_idx = b_local // 2
            omega = self.omegas[f_idx]
            is_cosine = (b_local % 2 == 1)
            phase_offset = 0.5 * math.pi if is_cosine else 0.0
            
            if self.is_calibrating:
                if self.is_loading:
                    phase = 0.0
                else:
                    phase = self.calibrated_phases[b]
            else:
                phase = self.calibrated_phases[b]
                
            return omega, phase + phase_offset

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
                        self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = gate_coupling_w0
                        if linear_load_gate:
                            self.group.get_node(g_target)["psi"] = 1.0
                            self.group.get_node(g_target)["psi_bias"] = 1.0
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
                    
                    if not linear_load_gate:
                        for b in range(16):
                            if (val & (1 << b)):
                                omega, phase_val = self.get_bit_params(b)
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
                                omega, phase_val = self.get_bit_params(b)
                                sum_sin0 += math.sin(omega * t + phase_val)
                        p_amp0 = amp / math.sqrt(num_active0)
                        if use_press_sym:
                            src_rho0 = 16.0 * math.exp(0.5 * p_amp0 * sum_sin0) - 1.0
                        else:
                            src_rho0 += p_amp0 * sum_sin0
                        
                    # Lane 1
                    num_active1 = sum(1 for b in range(8, 16) if (val & (1 << b)))
                    src_rho1 = 15.0
                    if num_active1 > 0:
                        sum_sin1 = 0.0
                        for b in range(8, 16):
                            if (val & (1 << b)):
                                omega, phase_val = self.get_bit_params(b)
                                sum_sin1 += math.sin(omega * t + phase_val)
                        p_amp1 = amp / math.sqrt(num_active1)
                        if use_press_sym:
                            src_rho1 = 16.0 * math.exp(0.5 * p_amp1 * sum_sin1) - 1.0
                        else:
                            src_rho1 += p_amp1 * sum_sin1
                        
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
                
                # Print battery densities at end of LOAD
                print("\nBattery densities at end of LOAD:")
                for b in range(16):
                    bat_id = f"S_R{reg_name}_Bit{b}_B"
                    print(f"  Bit {b:2d}: rho = {self.group.get_node(bat_id)['rho']:.4f}")
                    
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
                                if linear_query_gate:
                                    self.group.get_node(g_active)["psi"] = 1.0
                                    self.group.get_node(g_active)["psi_bias"] = 1.0
                                    self.group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                                    self.group.get_edge(g_active, f"P_Bus{lane}")["w0"] = gate_coupling_w0
                                else:
                                    omega, phase_val = self.get_bit_params(b)
                                    val_psi = 0.3 * math.sin(omega * t + phase_val)
                                    self.group.get_node(g_active)["psi"] = val_psi
                                    self.group.get_node(g_active)["psi_bias"] = val_psi
                                    self.group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                                    self.group.get_edge(g_active, f"P_Bus{lane}")["w0"] = gate_coupling_w0
                            else:
                                self.group.get_node(g_active)["psi_bias"] = -1.0
                                self.group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                                
                    for b in range(16):
                        gate_id = f"Gate_Match{b}"
                        dest_basin_id = f"Basin_Val{b}"
                        
                        self.group.set_edge_connection(gate_id, self.group.semantic.basins[dest_basin_id].bridge_id, True)
                        f_idx = (b % 8) // 2
                        self.group.get_edge(gate_id, self.group.semantic.basins[dest_basin_id].bridge_id)["w0"] = self.match_weights[f_idx]
                        
                        omega, phase_val = self.get_bit_params(b)
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
        group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0, cond_max=cond_max)
        
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
        return deltas, sequencer.bus_densities

    print("Calibrating custom phases...")
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    calibrated_phases = [0.0] * 16
    for b in range(16):
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
        
    # Run Case A word
    val_X = 0b1010110011110001
    expected = [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
    deltas, bus_densities = run_custom_trial(val_X, 0, calibrated_phases, is_calibrating=False)
    
    # Analyze bus densities oscillation
    bus_min = min(bus_densities) if bus_densities else 0
    bus_max = max(bus_densities) if bus_densities else 0
    print(f"Bus P_Bus0 density range during query: min={bus_min:.6f}, max={bus_max:.6f}, amplitude={bus_max-bus_min:.6f}")
    
    print("\nCase A Results:")
    passed_all = True
    for b in range(16):
        exp = expected[b]
        act = "Active" if exp else "Flat"
        status = "PASS" if (exp == 1 and deltas[b] >= 0.2) or (exp == 0 and deltas[b] < 0.1) else "FAIL"
        if status == "FAIL":
            passed_all = False
        print(f"  Bit {b:2d} ({act}): delta = {deltas[b]:+.6f} | Status = {status}")
    print(f"Passed all bits for Case A: {passed_all}")
    return passed_all

if __name__ == "__main__":
    # Test gate_coupling_w0 = 50.0
    run_test(cond_max=1000.0, load_damping=0.0, use_press_sym=True, linear_load_gate=True, linear_query_gate=True, gate_coupling_w0=50.0)
