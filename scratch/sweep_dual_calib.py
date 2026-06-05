import sys
import os
from pathlib import Path

# Add project root and scratch paths
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_programmable_hybrid_processor import build_group
from hybrid_subsystem_framework import Instruction, MicroInstructionSequencer

def test_configs(bias, duration):
    # Override execute_instruction dynamically to use the specified bias and duration
    def custom_execute(self, inst):
        op = inst.op.upper()
        if op == "AND":
            dest = 'C'
            dest_reg = "S_RC"
            # Phase 1: Open ALU Gates and Compute
            for _ in range(duration):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = 1.0 if r in ('A', 'B', dest) else -1.0
                self.configure_alu_output_routing(dest)
                self.set_wormhole_connections(None, is_load=True)
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.get_node(dest_reg)["psi_bias"] = bias
                self.group.step(dt=self.dt)
                self.record_telemetry()
            # Phase 2: Close Gates and Settle (25 steps)
            for _ in range(25):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(dest)
                self.set_wormhole_connections(None, is_load=True)
                self.apply_holding_biases_processing()
                self.group.get_node(dest_reg)["psi_bias"] = bias
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()
        else:
            original_execute(self, inst)

    original_execute = MicroInstructionSequencer.execute_instruction
    MicroInstructionSequencer.execute_instruction = custom_execute

    # 1. Evaluate Program 2 (AND only)
    p2_ok = True
    p2_res = {}
    for A, B in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        group = build_group()
        group.prime_basin("Basin_A", active=(A == 1))
        group.prime_basin("Basin_B", active=(B == 1))
        group.prime_basin("Basin_C", active=False)
        group.prime_register('A', active=False)
        group.prime_register('B', active=False)
        group.prime_register('C', active=False)
        
        seq = MicroInstructionSequencer(group)
        program = [
            Instruction("LOAD", ['A', "Basin_A"]),
            Instruction("LOAD", ['B', "Basin_B"]),
            Instruction("RESET_CORE", []),
            Instruction("AND", []),
            Instruction("STORE", ['C', "Basin_C"])
        ]
        history = seq.run_program(program)
        expected = (A and B)
        # Store check
        stored = history[-1]["basin_c_state"] == expected
        # Compute check (at shifted index 181)
        computed = (history[181]["reg_c_state"] == 1.0) == (expected == 1)
        p2_res[(A, B)] = stored and computed
        if not (stored and computed):
            p2_ok = False

    # 2. Evaluate Program 3 (Sequential)
    p3_ok = True
    p3_res = {}
    for A, B in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        group = build_group()
        group.prime_basin("Basin_A", active=(A == 1))
        group.prime_basin("Basin_B", active=(B == 1))
        group.prime_basin("Basin_C", active=False)
        group.prime_register('A', active=False)
        group.prime_register('B', active=False)
        group.prime_register('C', active=False)
        
        seq = MicroInstructionSequencer(group)
        program = [
            Instruction("LOAD", ['A', "Basin_A"]),
            Instruction("LOAD", ['B', "Basin_B"]),
            Instruction("OR", []),
            Instruction("COPY", ['C', 'A']),
            Instruction("CLEAR", ['C']),
            Instruction("RESET_CORE", []),
            Instruction("AND", []),
            Instruction("STORE", ['C', "Basin_C"])
        ]
        history = seq.run_program(program)
        expected_C1 = (A or B)
        expected_C2 = (expected_C1 and B)
        stored = history[-1]["basin_c_state"] == expected_C2
        # Compute check (index 311 for 30 duration, wait! If duration changes, index is 260 + duration + 25 - 1)
        check_idx = 260 + duration + 25 - 1
        computed = (history[check_idx]["reg_c_state"] == 1.0) == (expected_C2 == 1)
        p3_res[(A, B)] = stored and computed
        if not (stored and computed):
            p3_ok = False

    # Restore execute_instruction
    MicroInstructionSequencer.execute_instruction = original_execute
    return p2_ok, p2_res, p3_ok, p3_res

# Sweep bias and duration
biases = [0.18, 0.185, 0.19, 0.195, 0.20]
durations = [27, 28, 29, 30, 31, 32]
for bias in biases:
    for dur in durations:
        p2_ok, p2_res, p3_ok, p3_res = test_configs(bias, dur)
        if p2_ok or p3_ok:
            print(f"bias={bias:.3f} dur={dur} -> P2_ok={p2_ok} (res={p2_res}) | P3_ok={p3_ok} (res={p3_res})")
