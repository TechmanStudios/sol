import sys
from pathlib import Path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_hybrid_alu_expanded import build_group
from hybrid_subsystem_framework import MicroInstructionSequencer

group = build_group()
seq = MicroInstructionSequencer(group)

print("Initial w0 (P_Sum -> GATE_C):", group.get_edge("P_Sum", "GATE_C")["w0"])

seq.configure_alu_output_routing("C")
print("After configure('C') w0 (P_Sum -> GATE_C):", group.get_edge("P_Sum", "GATE_C")["w0"])
if "GATE_D" in group.engine.physics.node_by_id:
    print("After configure('C') w0 (P_Sum -> GATE_D):", group.get_edge("P_Sum", "GATE_D")["w0"])

seq.configure_alu_output_routing(None)
print("After configure(None) w0 (P_Sum -> GATE_C):", group.get_edge("P_Sum", "GATE_C")["w0"])
