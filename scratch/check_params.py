import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm_final import MHRALevel11ProcessingManifold, SemanticManifold, Level11ManifoldGroup, Level11Sequencer, UniversalManifold

# Build minimal dummy group to instantiate sequencer
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
processing = MHRALevel11ProcessingManifold(baseline_rho=15.0)
group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)

seq = Level11Sequencer(group, dt=0.04, baseline_rho=15.0)

print("Bit | reg_gate_params (omega, phase) | match_gate_params (omega, phase)")
print("-" * 70)
for b in range(16):
    omega_r, phase_r = seq.get_reg_gate_params(b)
    omega_m, phase_m = seq.get_match_gate_params(b)
    print(f"{b:2d}  | ({omega_r:.6f}, {phase_r/math.pi:.4f} * pi)        | ({omega_m:.6f}, {phase_m/math.pi:.4f} * pi)")
