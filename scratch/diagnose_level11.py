import sys
import os
import math
from pathlib import Path

sol_root = Path("g:/docs/TechmanStudios/sol")
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm import run_level11_trial, calibrate_pdm_phases, Level11ManifoldGroup, Level11Sequencer, MHRALevel11ProcessingManifold, SemanticManifold, UniversalManifold, Instruction

def run_diagnose():
    print("Running diagnostic trial for Level 11 PDM...")
    baseline = 15.0
    
    # 1. Build semantic manifold with 16 val basins + 1 query basin
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
            
    # Prime registers: let's load Case A value: val_X = 0b1010110011110001
    val_X = 0b1010110011110001
    group.prime_register_lane('X', 0, active=True)
    group.prime_register_lane('X', 1, active=True)
    group.prime_register_lane('Y', 0, active=False)
    group.prime_register_lane('Y', 1, active=False)
    
    sequencer = Level11Sequencer(group, dt=0.08, baseline_rho=baseline)
    # We will use zeros for calibrated phases to keep it simple or sweep
    calibrated_phases = [0.0] * 16
    sequencer.calibrated_phases = calibrated_phases
    
    # Execute LOAD_16
    # Write-enable the query input, bus lanes, and registers (no gate write-enable!)
    group.engine.write_enable("P_Bus0")
    group.engine.write_enable("P_Bus1")
    for lane in [0, 1]:
        group.engine.write_enable(f"S_R{'X'}{lane}")
        group.engine.write_enable(f"S_R{'X'}{lane}_B")
        
    for i in range(16):
        group.engine.write_enable(f"Gate_Match{i}")
        
    for nid in group.semantic.basins["Basin_Query"].node_ids:
        group.engine.write_enable(nid)
        
    # Isolate matching gates during load
    for i in range(16):
        bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
        group.set_edge_connection(bus_lane, f"Gate_Match{i}", False)
        
    # Close all register gates to isolate the loading process
    for r in ['X', 'Y']:
        for lane in [0, 1]:
            group.get_node(f"GATE_{r}{lane}")["psi_bias"] = -1.0
            group.set_edge_connection(f"GATE_{r}{lane}", f"P_Bus{lane}", False)
            
    for s in range(60):
        t = len(sequencer.history) * sequencer.dt
        amp = 80.0
        
        num_active0 = sum(1 for b in range(8) if (val_X & (1 << b)))
        src_rho0 = 200.0
        if num_active0 > 0:
            sum_sin0 = 0.0
            for b in range(8):
                if (val_X & (1 << b)):
                    f_idx = b // 2
                    is_cosine = (b % 2 == 1)
                    phase_offset = 0.5 * math.pi if is_cosine else 0.0
                    sum_sin0 += math.sin(sequencer.omegas[f_idx] * t + phase_offset)
            src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
                
        num_active1 = sum(1 for b in range(8, 16) if (val_X & (1 << b)))
        src_rho1 = 200.0
        if num_active1 > 0:
            sum_sin1 = 0.0
            for b in range(8, 16):
                if (val_X & (1 << b)):
                    f_idx = (b - 8) // 2
                    is_cosine = (b % 2 == 1)
                    phase_offset = 0.5 * math.pi if is_cosine else 0.0
                    sum_sin1 += math.sin(sequencer.omegas[f_idx] * t + phase_offset)
            src_rho1 += (amp / math.sqrt(num_active1)) * sum_sin1
            
        group.get_node("S_RX0")["rho"] = src_rho0
        group.get_node("S_RX1")["rho"] = src_rho1
        group.get_node("P_Bus0")["rho"] = baseline
        group.get_node("P_Bus1")["rho"] = baseline
        
        group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
    for s in range(15):
        group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
    # Now execute QUERY_16 manually so we can print status
    inst = Instruction("QUERY_16", [])
    
    # Manual execute (no gate write-enable!):
    sequencer.group.engine.write_enable("P_Bus0")
    sequencer.group.engine.write_enable("P_Bus1")
    for reg in ['X', 'Y']:
        for lane in [0, 1]:
            sequencer.group.engine.write_enable(f"S_R{reg}{lane}")
            sequencer.group.engine.write_enable(f"S_R{reg}{lane}_B")
            
    for i in range(16):
        sequencer.group.engine.write_enable(f"Gate_Match{i}")
        bus_lane = "P_Bus0" if i < 8 else "P_Bus1"
        sequencer.group.set_edge_connection(bus_lane, f"Gate_Match{i}", True)
        f_idx = (i % 8) // 2
        sequencer.group.get_edge(bus_lane, f"Gate_Match{i}")["w0"] = sequencer.match_weights[f_idx]
        
    for n in sequencer.group.processing.nodes:
        sequencer.group.get_node(n["id"])["psi_bias"] = 0.0
        
    for i in range(16):
        basin = sequencer.group.semantic.basins[f"Basin_Val{i}"]
        for nid in basin.node_ids:
            sequencer.group.engine.write_enable(nid)
            sequencer.group.get_node(nid)["psi_bias"] = 0.0
            
    active_regs = ["X"]
    
    print("\nTracing step-by-step query phase...")
    print(f"{'Step':5s} | {'S_RX0 Host + Battery':35s} | {'P_Bus0 rho':10s} | {'Val0Bridge':10s} | {'Val0Hub':10s} | {'Gate0 psi':10s}")
    
    for s in range(120):
        t = len(sequencer.history) * sequencer.dt
        for reg in ['X', 'Y']:
            for lane in [0, 1]:
                gate_id = f"GATE_{reg}{lane}"
                if reg in active_regs:
                    sequencer.group.get_node(gate_id)["psi_bias"] = 1.0
                    sequencer.group.set_edge_connection(gate_id, f"P_Bus{lane}", True)
                    sequencer.group.get_edge(gate_id, f"P_Bus{lane}")["w0"] = 10.0
                else:
                    sequencer.group.get_node(gate_id)["psi_bias"] = -1.0
                    sequencer.group.set_edge_connection(gate_id, f"P_Bus{lane}", False)
                    
        for i in range(16):
            gate_id = f"Gate_Match{i}"
            basin_id = f"Basin_Val{i}"
            sequencer.group.set_edge_connection(gate_id, sequencer.group.semantic.basins[basin_id].bridge_id, True)
            f_idx = (i % 8) // 2
            sequencer.group.get_edge(gate_id, sequencer.group.semantic.basins[basin_id].bridge_id)["w0"] = sequencer.match_weights[f_idx]
            
            # Drive matching gate reference phase
            sequencer.group.get_node(gate_id)["psi"] = math.sin(sequencer.omegas[f_idx] * t + sequencer.calibrated_phases[i])
            
        sequencer.group.engine.step(dt=sequencer.dt, damping=0.0)
        sequencer.record_telemetry()
        
        if s % 10 == 0 or s < 10:
            rx0 = sequencer.group.get_node("S_RX0")["rho"]
            rx0_bat_rho = sequencer.group.get_node("S_RX0_B")["rho"]
            rx0_psi = sequencer.group.get_node("S_RX0")["psi"]
            rx0_bat_psi = sequencer.group.get_node("S_RX0_B")["psi"]
            rx0_bat_state = sequencer.group.get_node("S_RX0_B").get("b_state", 0)
            rx0_bat_charge = sequencer.group.get_node("S_RX0_B").get("b_charge", 0.0)
            pbus0 = sequencer.group.get_node("P_Bus0")["rho"]
            val0_br = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_Val0"].bridge_id)["rho"]
            val0_hb = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_Val0"].hub_id)["rho"]
            val1_br = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_Val1"].bridge_id)["rho"]
            val1_hb = sequencer.group.get_node(sequencer.group.semantic.basins["Basin_Val1"].hub_id)["rho"]
            
            gate0_psi = sequencer.group.get_node("Gate_Match0")["psi"]
            gate1_psi = sequencer.group.get_node("Gate_Match1")["psi"]
            
            print(f"{s:5d} | {rx0:7.1f}+{rx0_bat_rho:7.1f} (psi={rx0_psi:+.4f}, bat_psi={rx0_bat_psi:+.4f}) | {pbus0:10.2f} | {val0_br:10.2f} | {val0_hb:10.2f} | {gate0_psi:10.4f}")

if __name__ == "__main__":
    run_diagnose()
