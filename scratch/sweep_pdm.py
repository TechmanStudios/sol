import sys
import os
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm import run_level11_trial, Level11ManifoldGroup, Level11Sequencer, MHRALevel11ProcessingManifold, SemanticManifold, UniversalManifold, Instruction

def try_params(reg_gate_w0, gate_bus_w0, write_enable_gates=False, register_rho_load=200.0):
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
        
    # Custom manifold construction to apply custom edge weights
    processing = MHRALevel11ProcessingManifold(baseline_rho=baseline)
    
    # Modify weights in processing manifold before group construction
    for e in processing.edges:
        # Connect registers to gate
        if e["from"].startswith("S_R") and e["to"].startswith("GATE_"):
            e["w0"] = reg_gate_w0
        # Connect gate to bus
        if e["from"].startswith("GATE_") and e["to"].startswith("P_Bus"):
            e["w0"] = gate_bus_w0
            
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    # Prime basins
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 300.0
        else:
            node["rho"] = baseline
            
    for i in range(16):
        basin = group.semantic.basins[f"Basin_Val{i}"]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline
            
    val_X = 0b1010110011110001
    group.prime_register_lane('X', 0, active=True)
    group.prime_register_lane('X', 1, active=True)
    group.prime_register_lane('Y', 0, active=False)
    group.prime_register_lane('Y', 1, active=False)
    
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline)
    
    # Run calibration with the same parameter group
    # To calibrate, we need to temporarily inject the parameter group
    # We will just manually calibrate phases for this trial to be accurate
    calibrated_phases = [0.0] * 16
    
    # Sweep phases for the active bits of val_X
    # (For speed, we'll calibrate just the active bits: 0, 4, 5, 6, 7, 10, 11, 13, 15)
    active_bits = [0, 4, 5, 6, 7, 10, 11, 13, 15]
    steps = 12
    phases = [2 * math.pi * j / steps for j in range(steps)]
    
    for b in active_bits:
        best_ph = 0.0
        max_d = -999.0
        for ph in phases:
            # Run a mini trial
            temp_phases = list(calibrated_phases)
            temp_phases[b] = ph
            
            # Simple trial runner
            d = run_custom_trial(group, sequencer, val_X, temp_phases, write_enable_gates, register_rho_load, baseline)[b]
            if d > max_d:
                max_d = d
                best_ph = ph
        calibrated_phases[b] = best_ph
        
    # Run final trial with calibrated phases
    deltas = run_custom_trial(group, sequencer, val_X, calibrated_phases, write_enable_gates, register_rho_load, baseline)
    return deltas, calibrated_phases

def run_custom_trial(group, sequencer, val_X, phases, write_enable_gates, register_rho_load, baseline):
    # Reset group state
    for n in group.semantic.nodes:
        n["rho"] = baseline
        n["psi"] = 0.0
        n["psi_bias"] = 0.0
        
    for n in group.processing.nodes:
        if n["id"].startswith("S_R"):
            n["rho"] = register_rho_load
            n["psi"] = 1.0
            n["psi_bias"] = 1.0
        else:
            n["rho"] = baseline
            n["psi"] = 0.0
            n["psi_bias"] = 0.0
            
    for lane in [0, 1]:
        group.prime_register_lane('X', lane, active=True)
        group.prime_register_lane('Y', lane, active=False)
        
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 300.0
        else:
            node["rho"] = baseline
            
    sequencer.calibrated_phases = phases
    
    # 1. LOAD_16
    # Write-enable
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
    for lane in [0, 1]:
        group.engine.write_enable(f"S_RX{lane}")
        group.engine.write_enable(f"S_RX{lane}_B")
        if write_enable_gates:
            group.engine.write_enable(f"GATE_X{lane}")
            
    for i in range(16):
        group.engine.write_enable(f"Gate_Match{i}")
        
    for nid in group.semantic.basins["Basin_Query"].node_ids:
        group.engine.write_enable(nid)
        
    for i in range(16):
        bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
        group.set_edge_connection(bus_lane, f"Gate_Match{i}", False)
        
    for r in ['X', 'Y']:
        for lane in [0, 1]:
            group.get_node(f"GATE_{r}{lane}")["psi_bias"] = -1.0
            group.set_edge_connection(f"GATE_{r}{lane}", f"P_Bus{lane}", False)
            
    # Load steps
    for s in range(60):
        t = s * sequencer.dt
        amp = 8.0
        src_rho0 = register_rho_load
        for b in range(8):
            if (val_X & (1 << b)):
                f_idx = b // 2
                is_cosine = (b % 2 == 1)
                phase_offset = 0.5 * math.pi if is_cosine else 0.0
                src_rho0 += amp * math.sin(sequencer.omegas[f_idx] * t + phase_offset)
                
        src_rho1 = register_rho_load
        for b in range(8, 16):
            if (val_X & (1 << b)):
                f_idx = (b - 8) // 2
                is_cosine = (b % 2 == 1)
                phase_offset = 0.5 * math.pi if is_cosine else 0.0
                src_rho1 += amp * math.sin(sequencer.omegas[f_idx] * t + phase_offset)
                
        group.get_node("S_RX0")["rho"] = src_rho0
        group.get_node("S_RX1")["rho"] = src_rho1
        group.get_node("P_Bus0")["rho"] = baseline
        group.get_node("P_Bus1")["rho"] = baseline
        
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
    for s in range(15):
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
    # 2. QUERY_16
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
    for reg in ['X', 'Y']:
        for lane in [0, 1]:
            group.engine.write_enable(f"S_R{reg}{lane}")
            group.engine.write_enable(f"S_R{reg}{lane}_B")
            if write_enable_gates:
                group.engine.write_enable(f"GATE_{reg}{lane}")
                
    for i in range(16):
        group.engine.write_enable(f"Gate_Match{i}")
        bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
        group.set_edge_connection(bus_lane, f"Gate_Match{i}", True)
        f_idx = (i % 8) // 2
        group.get_edge(bus_lane, f"Gate_Match{i}")["w0"] = sequencer.match_weights[f_idx]
        
    for n in group.processing.nodes:
        n["psi_bias"] = 0.0
        
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
                    # We keep edge weight w0 = gate_bus_w0 as defined in custom manifold
                else:
                    group.get_node(gate_id)["psi_bias"] = -1.0
                    group.set_edge_connection(gate_id, f"P_Bus{lane}", False)
                    
        for i in range(16):
            gate_id = f"Gate_Match{i}"
            basin_id = f"Basin_Val{i}"
            group.set_edge_connection(gate_id, group.semantic.basins[basin_id].bridge_id, True)
            f_idx = (i % 8) // 2
            
            # Drive matching gate reference phase
            group.get_node(gate_id)["psi"] = math.sin(sequencer.omegas[f_idx] * t + phases[i])
            
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
    for s in range(20):
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                group.get_node(f"GATE_{reg}{lane}")["psi_bias"] = -1.0
                group.set_edge_connection(f"GATE_{reg}{lane}", f"P_Bus{lane}", False)
        for i in range(16):
            group.set_edge_connection(f"Gate_Match{i}", group.semantic.basins[f"Basin_Val{i}"].bridge_id, False)
        group.engine.step(dt=sequencer.dt, damping=0.0)
        
    deltas = []
    for i in range(16):
        dest_id = group.semantic.basins[f"Basin_Val{i}"].bridge_id
        delta = group.get_node(dest_id)["rho"] - baseline
        deltas.append(delta)
        
    return deltas

def main():
    # Sweep parameter configurations
    configs = [
        # (reg_gate_w0, gate_bus_w0, write_enable_gates, register_rho_load)
        (5.0, 5.0, False, 200.0), # Baseline (gates frozen)
        (10.0, 10.0, False, 200.0), # Stronger register-to-bus coupling
        (20.0, 20.0, False, 200.0), # Very strong coupling
        (20.0, 20.0, False, 300.0), # Strong coupling + high load density
        (10.0, 10.0, True, 200.0), # Gates write-enabled (just to check difference)
    ]
    
    for cfg in configs:
        reg_gate_w0, gate_bus_w0, we_gates, rho_load = cfg
        print(f"\nTesting: reg_gate_w0={reg_gate_w0}, gate_bus_w0={gate_bus_w0}, we_gates={we_gates}, rho_load={rho_load}...")
        try:
            deltas, phases = try_params(reg_gate_w0, gate_bus_w0, we_gates, rho_load)
            print("  Active bits deltas:")
            active_bits = [0, 4, 5, 6, 7, 10, 11, 13, 15]
            for b in active_bits:
                print(f"    Bit {b:2d}: delta = {deltas[b]:+.4f} | phase = {phases[b]/math.pi:.4f} * pi")
            inactive_bits = [1, 2, 3, 8, 9, 12, 14]
            print("  Inactive bits deltas:")
            for b in inactive_bits:
                print(f"    Bit {b:2d}: delta = {deltas[b]:+.4f}")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    main()
