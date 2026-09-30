import sys
import os
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm import Level11ManifoldGroup, Level11Sequencer, MHRALevel11ProcessingManifold, SemanticManifold, UniversalManifold, Instruction

def trace_bit(bit: int):
    baseline = 15.0
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
        n["rho"] = baseline
        
    processing = MHRALevel11ProcessingManifold(baseline_rho=baseline)
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    # Prime X active
    group.prime_register_lane('X', 0, active=True)
    group.prime_register_lane('X', 1, active=True)
    group.prime_register_lane('Y', 0, active=False)
    group.prime_register_lane('Y', 1, active=False)
    
    for lane in [0, 1]:
        group.get_node(f"S_RX{lane}")["rho"] = baseline
        group.get_node(f"S_RX{lane}_B")["rho"] = 0.0
        
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline)
    
    # LOAD_16
    for lane in [0, 1]:
        group.engine.write_enable(f"S_RX{lane}")
        group.engine.write_enable(f"S_RX{lane}_B")
        
    for lane in [0, 1]:
        group.get_node(f"GATE_X{lane}")["psi_bias"] = 1.0
        group.set_edge_connection(f"GATE_X{lane}", f"P_Bus{lane}", True)
        group.get_edge(f"GATE_X{lane}", f"P_Bus{lane}")["w0"] = 10.0
        
    for lane in [0, 1]:
        group.get_node(f"GATE_Y{lane}")["psi_bias"] = -1.0
        group.set_edge_connection(f"GATE_Y{lane}", f"P_Bus{lane}", False)
        
    amp = 8.0
    val_X = (1 << bit)
    
    print(f"\n--- TRACING LOAD_16 FOR BIT {bit} ---")
    print(f"Step | Bus0_rho | RX0_rho | RX0_B_rho | RX0_psi | RX0_B_psi")
    
    for s in range(60):
        t = s * sequencer.dt
        num_active0 = sum(1 for b in range(8) if (val_X & (1 << b)))
        src_rho0 = baseline
        if num_active0 > 0:
            sum_sin0 = 0.0
            for b in range(8):
                if (val_X & (1 << b)):
                    f_idx = b // 2
                    is_cosine = (b % 2 == 1)
                    phase_offset = 0.5 * math.pi if is_cosine else 0.0
                    sum_sin0 += math.sin(sequencer.omegas[f_idx] * t + phase_offset)
            src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
            
        group.get_node("P_Bus0")["rho"] = src_rho0
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
        if s % 5 == 0 or s >= 55:
            bus = group.get_node("P_Bus0")
            rx = group.get_node("S_RX0")
            rxb = group.get_node("S_RX0_B")
            print(f"{s:4d} | {bus['rho']:8.4f} | {rx['rho']:7.4f} | {rxb['rho']:9.4f} | {rx['psi']:7.4f} | {rxb['psi']:9.4f}")
            
    # Settle
    for lane in [0, 1]:
        group.get_node(f"GATE_X{lane}")["psi_bias"] = -1.0
        group.set_edge_connection(f"GATE_X{lane}", f"P_Bus{lane}", False)
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
    
    for s in range(15):
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
    # QUERY_16
    for reg in ['X', 'Y']:
        for lane in [0, 1]:
            group.get_node(f"S_R{reg}{lane}_B")["isBattery"] = False
            
    group.engine.write_enable("P_Bus0")
    for reg in ['X', 'Y']:
        for lane in [0, 1]:
            group.engine.write_enable(f"S_R{reg}{lane}")
            group.engine.write_enable(f"S_R{reg}{lane}_B")
            
    for i in range(16):
        group.engine.write_enable(f"Gate_Match{i}")
        bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
        group.set_edge_connection(bus_lane, f"Gate_Match{i}", True)
        f_idx = (i % 8) // 2
        group.get_edge(bus_lane, f"Gate_Match{i}")["w0"] = sequencer.match_weights[f_idx]
        
    for n in group.processing.nodes:
        group.get_node(n["id"])["psi_bias"] = 0.0
        
    for i in range(16):
        basin = group.semantic.basins[f"Basin_Val{i}"]
        for nid in basin.node_ids:
            group.engine.write_enable(nid)
            group.get_node(nid)["psi_bias"] = 0.0
            
    for i in range(16):
        gate_id = f"Gate_Match{i}"
        basin_id = f"Basin_Val{i}"
        group.set_edge_connection(gate_id, group.semantic.basins[basin_id].bridge_id, True)
        f_idx = (i % 8) // 2
        group.get_edge(gate_id, group.semantic.basins[basin_id].bridge_id)["w0"] = sequencer.match_weights[f_idx]
        
    print(f"\n--- TRACING QUERY_16 FOR BIT {bit} ---")
    print(f"Step | Bus0_rho | RX0_rho | RX0_B_rho | RX0_psi | RX0_B_psi")
    
    # We will trace the query steps. Let's record the last 40 steps at high resolution to see oscillation phases
    for s in range(120):
        t = (75 + s) * sequencer.dt
        
        # open gates
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                gate_id = f"GATE_{reg}{lane}"
                if reg == "X":
                    group.get_node(gate_id)["psi_bias"] = 1.0
                    group.set_edge_connection(gate_id, f"P_Bus{lane}", True)
                    group.get_edge(gate_id, f"P_Bus{lane}")["w0"] = 10.0
                else:
                    group.get_node(gate_id)["psi_bias"] = -1.0
                    group.set_edge_connection(gate_id, f"P_Bus{lane}", False)
                    
        for i in range(16):
            gate_id = f"Gate_Match{i}"
            f_idx = (i % 8) // 2
            # Drive matching gate phase with ph=0.0
            group.get_node(gate_id)["psi"] = math.sin(sequencer.omegas[f_idx] * t)
            
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
        if s >= 80:
            bus = group.get_node("P_Bus0")
            rx = group.get_node("S_RX0")
            rxb = group.get_node("S_RX0_B")
            print(f"{s:4d} | {bus['rho']:8.4f} | {rx['rho']:7.4f} | {rxb['rho']:9.4f} | {rx['psi']:7.4f} | {rxb['psi']:9.4f}")

def main():
    trace_bit(0)
    trace_bit(1)

if __name__ == "__main__":
    main()
