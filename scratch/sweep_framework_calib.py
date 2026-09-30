import sys
import os
from pathlib import Path

# Add project root and scratch paths
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_programmable_hybrid_processor import build_group
from hybrid_subsystem_framework import Instruction, MicroInstructionSequencer

def test_config(bias, duration):
    # Override logic parameters in sequencer
    def custom_execute(self, inst):
        op = inst.op.upper()
        if op == "AND":
            # Purely physical threshold logic
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
            # Fallback to original
            original_execute(self, inst)

    # Backup original execute
    original_execute = MicroInstructionSequencer.execute_instruction
    MicroInstructionSequencer.execute_instruction = custom_execute

    results = {}
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
        results[(A, B)] = history[-1]["basin_c_state"] == 1
        
    return results

# Sweep parameters
for bias in [0.17, 0.18, 0.19, 0.20, 0.21]:
    for dur in [25, 27, 30, 33, 35]:
        res = test_config(bias, dur)
        # Check if matches AND truth table
        is_and = (res[(0,0)] == False and res[(1,0)] == False and res[(0,1)] == False and res[(1,1)] == True)
        print(f"bias={bias:.2f} duration={dur} -> res={res} | MATCH AND={is_and}")
