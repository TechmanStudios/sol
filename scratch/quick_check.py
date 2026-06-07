import sys
import os
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm import Level11ManifoldGroup, Level11Sequencer, MHRALevel11ProcessingManifold, SemanticManifold, UniversalManifold, Instruction

def evaluate_config(periods, settle_steps, query_steps, baseline_rho=15.0):
    class PatchedSequencer(Level11Sequencer):
        def __init__(self, group, dt=0.08, baseline_rho=15.0):
            super().__init__(group, dt, baseline_rho)
            self.periods = periods
            self.omegas = [2 * math.pi / (p * self.dt) for p in self.periods]
            
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
                for s in range(settle_steps):
                    self.group.engine.step(dt=self.dt, damping=0.0)
                    self.record_telemetry()
            elif op == "QUERY_16":
                for reg in ['X', 'Y']:
                    for lane in [0, 1]:
                        self.group.get_node(f"S_R{reg}{lane}_B")["isBattery"] = False
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
                for s in range(query_steps):
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

    def run_patched_trial(val_X, val_Y, phases):
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
        sequencer = PatchedSequencer(group, dt=0.08, baseline_rho=baseline_rho)
        sequencer.calibrated_phases = phases
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
        return deltas

    # Phase Calibration
    calibrated = [0.0] * 16
    steps = 12
    phases = [2 * math.pi * j / steps for j in range(steps)]
    
    for f_idx in range(4):
        bit_sine = 2 * f_idx
        bit_cosine = 2 * f_idx + 1
        best_phase_sine = 0.0
        best_phase_cosine = 0.0
        max_delta_sine = -float('inf')
        max_delta_cosine = -float('inf')
        
        # Sine channel
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[bit_sine] = ph
            deltas = run_patched_trial(1 << bit_sine, 0, temp_phases)
            if deltas[bit_sine] > max_delta_sine:
                max_delta_sine = deltas[bit_sine]
                best_phase_sine = ph
                
        # Cosine channel
        for ph in phases:
            temp_phases = [0.0] * 16
            temp_phases[bit_cosine] = ph
            deltas = run_patched_trial(1 << bit_cosine, 0, temp_phases)
            if deltas[bit_cosine] > max_delta_cosine:
                max_delta_cosine = deltas[bit_cosine]
                best_phase_cosine = ph
                
        calibrated[bit_sine] = best_phase_sine
        calibrated[bit_cosine] = best_phase_cosine
        calibrated[bit_sine + 8] = best_phase_sine
        calibrated[bit_cosine + 8] = best_phase_cosine
        print(f"    Frequency index {f_idx} calibrated: Sine phase={best_phase_sine/math.pi:.2f}*pi, Cosine phase={best_phase_cosine/math.pi:.2f}*pi", flush=True)

    # Verify Case A
    val_X = 0b1010110011110001
    expected_X = [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
    deltas = run_patched_trial(val_X, 0, calibrated)
    
    passed_count = 0
    for i in range(16):
        exp_val = expected_X[i]
        d = deltas[i]
        if exp_val == 1:
            if d >= 0.2:
                passed_count += 1
        else:
            if d < 0.1:
                passed_count += 1
                
    sep_list = []
    for f in range(4):
        diff = abs(calibrated[2*f+1] - calibrated[2*f])
        diff = min(diff, 2*math.pi - diff)
        sep_list.append(diff / math.pi)
        
    return passed_count, sep_list, deltas, calibrated

def main():
    configs = [
        ([6.0, 8.0, 10.0, 12.0], 5, 30),
        ([6.0, 8.0, 10.0, 12.0], 5, 45),
        ([7.0, 9.0, 11.0, 13.0], 5, 30),
        ([7.0, 9.0, 11.0, 13.0], 5, 45),
    ]
    for periods, settle, query in configs:
        print(f"\nTesting periods={periods}, settle={settle}, query={query}...", flush=True)
        passed, seps, deltas, phases = evaluate_config(periods, settle, query)
        seps_str = ", ".join([f"{s:.2f}*pi" for s in seps])
        print(f"Passed Bits: {passed}/16 | Seps: [{seps_str}]", flush=True)
        print(f"Deltas: {[round(d, 4) for d in deltas]}", flush=True)
        print(f"Phases: {[round(p/math.pi, 4) for p in phases]}", flush=True)
        print("-" * 50, flush=True)

if __name__ == "__main__":
    main()
