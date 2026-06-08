import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm_final import MHRALevel11ProcessingManifold, SemanticManifold, Level11ManifoldGroup, Level11Sequencer, UniversalManifold, Instruction

def trace_bus_for_val(val_X):
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
        n["rho"] = 15.0
    processing = MHRALevel11ProcessingManifold(baseline_rho=15.0)
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 450.0
            
    group.prime_register('X', active=True, baseline_rho=15.0)
    sequencer = Level11Sequencer(group, dt=0.04, baseline_rho=15.0)
    sequencer.calibrated_phases = [0.0] * 16
    
    # Load
    sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    
    # Settle bus
    group.get_node("P_Bus0")["rho"] = 15.0
    group.get_node("P_Bus1")["rho"] = 15.0
    for b in range(16):
        group.get_node(f"Gate_Match{b}")["rho"] = 15.0
        
    for e in group.engine.physics.edges:
        is_resonator = (
            (e["from"].startswith("S_R") and e["to"].endswith("_B")) or
            (e["to"].startswith("S_R") and e["from"].endswith("_B"))
        )
        if not is_resonator:
            e["flux"] = 0.0
            
    # Query steps
    bus_rhos = []
    active_regs = ['X']
    
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
    for reg in ['X', 'Y']:
        for b in range(16):
            group.engine.write_enable(f"S_R{reg}_Bit{b}")
            group.engine.write_enable(f"S_R{reg}_Bit{b}_B")
            group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = True
            
    for b in range(16):
        gate_id = f"Gate_Match{b}"
        group.engine.write_enable(gate_id)
        lane = b // 8
        group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
        group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = 5.0
        group.get_node(gate_id)["psi_bias"] = 0.0
        
    for s in range(20):
        t = s * sequencer.dt
        for reg in ['X', 'Y']:
            for b in range(16):
                lane = b // 8
                g_active = f"GATE_{reg}_Bit{b}"
                bat = group.get_node(f"S_R{reg}_Bit{b}_B")
                is_bit_active = (bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.5)
                if reg in active_regs and is_bit_active:
                    omega, phase_val = sequencer.get_reg_gate_params(b)
                    val_psi = 1.0 * math.sin(omega * t + phase_val)
                    group.get_node(g_active)["psi"] = val_psi
                    group.get_node(g_active)["psi_bias"] = val_psi
                    group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                    group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 5.0
                else:
                    group.get_node(g_active)["psi_bias"] = -1.0
                    group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                    
        group.engine.step(dt=sequencer.dt, damping=0.0)
        bus_rhos.append(group.get_node("P_Bus0")["rho"])
        
    return bus_rhos

sine_bus = trace_bus_for_val(1)
cosine_bus = trace_bus_for_val(2)

print("Step | T | P_Bus0 rho (Sine only) | P_Bus0 rho (Cosine only) | Difference")
print("-" * 75)
for s in range(20):
    t = s * 0.04
    diff = sine_bus[s] - cosine_bus[s]
    print(f"{s:02d}   | {t:.2f} | {sine_bus[s]:21.6f} | {cosine_bus[s]:23.6f} | {diff:+.6f}")
