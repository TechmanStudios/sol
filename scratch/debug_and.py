import sys
import os
from pathlib import Path

# Add project root and scratch paths
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_programmable_hybrid_processor import build_group
from hybrid_subsystem_framework import Instruction, MicroInstructionSequencer

group = build_group()
group.prime_basin("Basin_A", active=True)
group.prime_basin("Basin_B", active=False)
group.prime_basin("Basin_C", active=False)
group.prime_register('A', active=False)
group.prime_register('B', active=False)
group.prime_register('C', active=False)

# Custom record function to get beliefs and conductances
beliefs_history = []
original_record = MicroInstructionSequencer.record_telemetry

def custom_record(self):
    original_record(self)
    node_a = self.group.get_node("S_RA")
    node_b = self.group.get_node("S_RB")
    node_c = self.group.get_node("S_RC")
    node_c_b = self.group.get_node("S_RC_B")
    node_sum = self.group.get_node("P_Sum")
    
    edge_c = self.group.get_edge("S_RC", "S_RC_B")
    edge_sum_c = self.group.get_edge("P_Sum", "GATE_C")
    
    beliefs_history.append({
        "A_psi": node_a["psi"],
        "B_psi": node_b["psi"],
        "C_psi": node_c["psi"],
        "C_charge": node_c_b["b_charge"],
        "Sum_psi": node_sum["psi"],
        "cond_c": edge_c.get("conductance", 1.0),
        "cond_sum_c": edge_sum_c.get("conductance", 1.0),
    })

MicroInstructionSequencer.record_telemetry = custom_record

sequencer = MicroInstructionSequencer(group)
program = [
    Instruction("LOAD", ['A', "Basin_A"]),
    Instruction("LOAD", ['B', "Basin_B"]),
    Instruction("RESET_CORE", []),
    Instruction("AND", []),
    Instruction("STORE", ['C', "Basin_C"])
]

history = sequencer.run_program(program)

print("Step | Sum_psi | C_psi | C_charge | cond_c | cond_sum_c | C_mass | A_mass | B_mass")
# RESET_CORE ends at step 130. AND runs 130 to 182.
for step in range(130, 182):
    h = history[step]
    b = beliefs_history[step]
    print(f"{step:4d} | {b['Sum_psi']:7.3f} | {b['C_psi']:5.2f} | {b['C_charge']:8.4f} | {b['cond_c']:7.2f} | {b['cond_sum_c']:10.2f} | {h['rho_reg_c']:6.1f} | {h['rho_reg_a']:6.1f} | {h['rho_reg_b']:6.1f}")
