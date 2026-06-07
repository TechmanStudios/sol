import sys
import os
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm import Level11ManifoldGroup, Level11Sequencer, MHRALevel11ProcessingManifold, SemanticManifold, UniversalManifold, Instruction

def run_trial_for_bit(bit: int, phase: float, toggle_nobat: bool) -> float:
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
    
    # Prime registers
    group.prime_register_lane('X', 0, active=True)
    group.prime_register_lane('X', 1, active=True)
    group.prime_register_lane('Y', 0, active=False)
    group.prime_register_lane('Y', 1, active=False)
    
    # Set registers to baseline density so they can absorb the wave
    for lane in [0, 1]:
        group.get_node(f"S_RX{lane}")["rho"] = baseline
        group.get_node(f"S_RX{lane}_B")["rho"] = 0.0
        
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline)
    
    # LOAD_16 via bus driving
    for lane in [0, 1]:
        group.engine.write_enable(f"S_RX{lane}")
        group.engine.write_enable(f"S_RX{lane}_B")
        
    # Open active register X gates
    for lane in [0, 1]:
        group.get_node(f"GATE_X{lane}")["psi_bias"] = 1.0
        group.set_edge_connection(f"GATE_X{lane}", f"P_Bus{lane}", True)
        group.get_edge(f"GATE_X{lane}", f"P_Bus{lane}")["w0"] = 10.0
        
    # Close register Y gates
    for lane in [0, 1]:
        group.get_node(f"GATE_Y{lane}")["psi_bias"] = -1.0
        group.set_edge_connection(f"GATE_Y{lane}", f"P_Bus{lane}", False)
        
    amp = 8.0
    val_X = (1 << bit)
    
    for s in range(60):
        t = s * sequencer.dt
        
        # Drive P_Bus0
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
            
        # Drive P_Bus1
        num_active1 = sum(1 for b in range(8, 16) if (val_X & (1 << b)))
        src_rho1 = baseline
        if num_active1 > 0:
            sum_sin1 = 0.0
            for b in range(8, 16):
                if (val_X & (1 << b)):
                    f_idx = (b - 8) // 2
                    is_cosine = (b % 2 == 1)
                    phase_offset = 0.5 * math.pi if is_cosine else 0.0
                    sum_sin1 += math.sin(sequencer.omegas[f_idx] * t + phase_offset)
            src_rho1 += (amp / math.sqrt(num_active1)) * sum_sin1
            
        group.get_node("P_Bus0")["rho"] = src_rho0
        group.get_node("P_Bus1")["rho"] = src_rho1
        
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
    # Close gates and settle
    for lane in [0, 1]:
        group.get_node(f"GATE_X{lane}")["psi_bias"] = -1.0
        group.set_edge_connection(f"GATE_X{lane}", f"P_Bus{lane}", False)
        
    # Write-enable bus lanes so they relax naturally
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
    
    for s in range(15):
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
    # QUERY_16
    if toggle_nobat:
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                group.get_node(f"S_R{reg}{lane}_B")["isBattery"] = False
                
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
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
            
    active_regs = ["X"]
    
    for s in range(120):
        t = (75 + s) * sequencer.dt
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                gate_id = f"GATE_{reg}{lane}"
                if reg in active_regs:
                    group.get_node(gate_id)["psi_bias"] = 1.0
                    group.set_edge_connection(gate_id, f"P_Bus{lane}", True)
                    group.get_edge(gate_id, f"P_Bus{lane}")["w0"] = 10.0
                else:
                    group.get_node(gate_id)["psi_bias"] = -1.0
                    group.set_edge_connection(gate_id, f"P_Bus{lane}", False)
                    
        for i in range(16):
            gate_id = f"Gate_Match{i}"
            basin_id = f"Basin_Val{i}"
            group.set_edge_connection(gate_id, group.semantic.basins[basin_id].bridge_id, True)
            f_idx = (i % 8) // 2
            group.get_edge(gate_id, group.semantic.basins[basin_id].bridge_id)["w0"] = sequencer.match_weights[f_idx]
            
            # Drive matching gate reference phase
            if i == bit:
                group.get_node(gate_id)["psi"] = math.sin(sequencer.omegas[f_idx] * t + phase)
            else:
                group.get_node(gate_id)["psi"] = math.sin(sequencer.omegas[f_idx] * t)
                
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
    dest_id = group.semantic.basins[f"Basin_Val{bit}"].bridge_id
    delta = group.get_node(dest_id)["rho"] - baseline
    return delta

def main():
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    # Test Bit 0 (Sine) and Bit 1 (Cosine) with toggle_nobat = False (keep battery active)
    print(f"\n========================================================")
    print(f"  DIAGNOSTIC SWEEP WITH toggle_nobat = False (Battery Active)")
    print(f"========================================================")
    
    for bit in [0, 1]:
        name = "Cosine (Bit 1)" if bit == 1 else "Sine (Bit 0)"
        print(f"\nSweeping matching phase for {name} Period 10.0...")
        for idx, ph in enumerate(phases):
            delta = run_trial_for_bit(bit, ph, toggle_nobat=False)
            print(f"  Phase {idx:2d}: {ph/math.pi:4.2f} * pi | delta = {delta:+.4f}", flush=True)

if __name__ == "__main__":
    main()
