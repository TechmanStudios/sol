import sys
import math
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from test_logos_vm_level11_pdm_final import MHRALevel11ProcessingManifold, SemanticManifold, Level11ManifoldGroup, Level11Sequencer, UniversalManifold, Instruction

# Build 16 value basins + 1 query basin
nodes = []
edges = []
basins = []

for i in range(16):
    n_val, e_val, b_val = UniversalManifold.build_semantic_basin(f"Basin_Val{i}", num_nodes=10, start_idx=i*10)
    for n in n_val:
        if n["id"] == b_val.hub_id:
            n["semanticMass"] = 1.0
            n["semanticMass0"] = 1.0
    nodes.extend(n_val)
    edges.extend(e_val)
    basins.append(b_val)
    
n_q, e_q, b_q = UniversalManifold.build_semantic_basin("Basin_Query", num_nodes=10, start_idx=160)
nodes.extend(n_q)
edges.extend(e_q)
basins.append(b_q)

semantic = SemanticManifold(nodes, edges, basins)
for n in semantic.nodes:
    n["rho"] = 15.0 * n.get("semanticMass", 1.0)
    
processing = MHRALevel11ProcessingManifold(baseline_rho=15.0)
group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)

# Prime basins
group.prime_basin("Basin_Query", active=True)
q_basin = group.semantic.basins["Basin_Query"]
for nid in q_basin.node_ids:
    node = group.get_node(nid)
    if nid == q_basin.hub_id:
        node["rho"] = 450.0
    else:
        node["rho"] = 15.0 * node.get("semanticMass", 1.0)
        
for i in range(16):
    basin = group.semantic.basins[f"Basin_Val{i}"]
    for nid in basin.node_ids:
        node = group.get_node(nid)
        node["rho"] = 15.0 * node.get("semanticMass", 1.0)

# Prime register X for both Bit 0 and Bit 1
group.prime_register('X', active=True, baseline_rho=15.0)

# We set up the sequencer
sequencer = Level11Sequencer(group, dt=0.04, baseline_rho=15.0)
# Use a dummy calibrated phase of 0.0 for all bits
sequencer.calibrated_phases = [0.0] * 16

# We will manually step through LOAD and QUERY and print out the state of:
# S_RX_Bit0, S_RX_Bit1, GATE_X_Bit0, GATE_X_Bit1, P_Bus0

print("Step | T | S_RX_Bit0 rho | S_RX_Bit1 rho | GATE_X_Bit0 psi | GATE_X_Bit1 psi | P_Bus0 rho | S_RX_Bit0_B charge | S_RX_Bit1_B charge")
print("-" * 120)

# LOAD_16
val_X = 3 # Both Bit 0 and Bit 1
inst = Instruction("LOAD_16", ["X", val_X])
reg_name = inst.args[0]
val = int(inst.args[1])
other_reg = "Y" if reg_name == "X" else "X"

# Write-enable the active registers, lock inactive register
for b in range(16):
    host = group.get_node(f"S_R{reg_name}_Bit{b}")
    bat = group.get_node(f"S_R{reg_name}_Bit{b}_B")
    group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
    group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
    
    if (val & (1 << b)):
        bat["isBattery"] = True
        host["psi_bias"] = 0.0
        bat["psi_bias"] = 0.0
    else:
        bat["isBattery"] = True
        bat["b_state"] = -1
        bat["b_charge"] = 0.0
        bat["psi"] = -1.0
        bat["psi_bias"] = -1.0
        host["psi"] = -1.0
        host["psi_bias"] = -1.0
    
    group.engine.write_lock(f"S_R{other_reg}_Bit{b}")
    group.engine.write_lock(f"S_R{other_reg}_Bit{b}_B")
    
# Write-lock match gates and isolate them from the bus during load
for b in range(16):
    group.engine.write_lock(f"Gate_Match{b}")
    lane = b // 8
    group.set_edge_connection(f"P_Bus{lane}", f"Gate_Match{b}", False)
    
# Write-lock value basins during load to prevent damping decay
for b in range(16):
    basin = group.semantic.basins[f"Basin_Val{b}"]
    for nid in basin.node_ids:
        group.engine.write_lock(nid)
        
# Write-enable query basin nodes
for nid in group.semantic.basins["Basin_Query"].node_ids:
    group.engine.write_enable(nid)
    
# Configure register gates connection and state
for b in range(16):
    lane = b // 8
    g_target = f"GATE_{reg_name}_Bit{b}"
    if (val & (1 << b)):
        group.set_edge_connection(g_target, f"P_Bus{lane}", True)
        group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 5.0
    else:
        group.get_node(g_target)["psi_bias"] = -1.0
        group.set_edge_connection(g_target, f"P_Bus{lane}", False)
        
    g_other = f"GATE_{other_reg}_Bit{b}"
    group.get_node(g_other)["psi_bias"] = -1.0
    group.set_edge_connection(g_other, f"P_Bus{lane}", False)
    
amp = 150.0

# Run LOAD steps
print("Step | T | S_RX_Bit0 rho | S_RX_Bit1 rho | GATE_X_Bit0 psi | GATE_X_Bit1 psi | P_Bus0 rho | R0_Flux | R1_Flux")
print("-" * 120)
for s in range(80):
    t = s * sequencer.dt
    group.set_edge_connection(group.semantic.basins["Basin_Query"].bridge_id, "P_Bus0", False)
    group.set_edge_connection(group.semantic.basins["Basin_Query"].bridge_id, "P_Bus1", False)
    
    # Drive active target register gates
    for b in range(16):
        if (val & (1 << b)):
            omega, phase_val = sequencer.get_reg_gate_params(b)
            val_psi = 1.0 * math.sin(omega * t + phase_val)
            g_target = f"GATE_{reg_name}_Bit{b}"
            group.get_node(g_target)["psi"] = val_psi
            group.get_node(g_target)["psi_bias"] = val_psi
            
    # Modulate superposition of active bits directly onto P_Bus nodes
    num_active0 = sum(1 for b in range(8) if (val & (1 << b)))
    src_rho0 = 15.0
    if num_active0 > 0:
        sum_sin0 = 0.0
        for b in range(8):
            if (val & (1 << b)):
                omega, phase_val = sequencer.get_reg_gate_params(b)
                sum_sin0 += math.sin(omega * t + phase_val)
        src_rho0 += (amp / math.sqrt(num_active0)) * sum_sin0
        
    group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
    group.engine.step(dt=sequencer.dt, damping=0.0)
    
    edge0 = group.get_edge('S_RX_Bit0', 'S_RX_Bit0_B')
    edge1 = group.get_edge('S_RX_Bit1', 'S_RX_Bit1_B')
    print(f"L{s:02d} | {t:.2f} | {group.get_node('S_RX_Bit0')['rho']:14.2f} | {group.get_node('S_RX_Bit1')['rho']:14.2f} | {group.get_node('GATE_X_Bit0')['psi']:14.4f} | {group.get_node('GATE_X_Bit1')['psi']:14.4f} | {group.get_node('P_Bus0')['rho']:10.2f} | {edge0['flux']:7.4f} | {edge1['flux']:7.4f}")

# Close active gates and settle
for b in range(16):
    lane = b // 8
    g_target = f"GATE_{reg_name}_Bit{b}"
    group.get_node(g_target)["psi_bias"] = -1.0
    group.set_edge_connection(g_target, f"P_Bus{lane}", False)
    
group.engine.write_enable("P_Bus0")
group.engine.write_enable("P_Bus1")
for b in range(16):
    basin = group.semantic.basins[f"Basin_Val{b}"]
    for nid in basin.node_ids:
        group.engine.write_enable(nid)

print("\n--- SETTLE STARTED ---")
for s in range(30):
    group.engine.step(dt=sequencer.dt, damping=0.0)
    t = (80 + s) * sequencer.dt
    edge0 = group.get_edge('S_RX_Bit0', 'S_RX_Bit0_B')
    edge1 = group.get_edge('S_RX_Bit1', 'S_RX_Bit1_B')
    print(f"S{s:02d} | {t:.2f} | {group.get_node('S_RX_Bit0')['rho']:14.2f} | {group.get_node('S_RX_Bit1')['rho']:14.2f} | {group.get_node('GATE_X_Bit0')['psi']:14.4f} | {group.get_node('GATE_X_Bit1')['psi']:14.4f} | {group.get_node('P_Bus0')['rho']:10.2f} | {edge0['flux']:7.4f} | {edge1['flux']:7.4f}")

# Print final states of resonators at the end of settle
edge0 = group.get_edge('S_RX_Bit0', 'S_RX_Bit0_B')
edge1 = group.get_edge('S_RX_Bit1', 'S_RX_Bit1_B')
print("\n--- RESONATOR STATE AT END OF SETTLE ---")
print(f"R0_Host: {group.get_node('S_RX_Bit0')['rho']:.4f} | R0_Bat: {group.get_node('S_RX_Bit0_B')['rho']:.4f} | R0_Flux: {edge0['flux']:.6f}")
print(f"R1_Host: {group.get_node('S_RX_Bit1')['rho']:.4f} | R1_Bat: {group.get_node('S_RX_Bit1_B')['rho']:.4f} | R1_Flux: {edge1['flux']:.6f}")


# QUERY_16
print("\n--- QUERY STARTED ---")
# Reset bus and matching gate densities to 15.0 at query start to clear transients
group.get_node("P_Bus0")["rho"] = 15.0
group.get_node("P_Bus1")["rho"] = 15.0
for b in range(16):
    group.get_node(f"Gate_Match{b}")["rho"] = 15.0
    
# Reset all edge fluxes to 0.0 to clear frozen flux transients, except for resonators!
for e in group.engine.physics.edges:
    is_resonator = (
        (e["from"].startswith("S_R") and e["to"].endswith("_B")) or
        (e["to"].startswith("S_R") and e["from"].endswith("_B"))
    )
    if not is_resonator:
        e["flux"] = 0.0

active_regs = ['X']

# Write-enable all processing nodes, batteries isBattery=True
group.engine.write_enable("P_Bus0")
group.engine.write_enable("P_Bus1")
for reg in ['X', 'Y']:
    for b in range(16):
        group.engine.write_enable(f"S_R{reg}_Bit{b}")
        group.engine.write_enable(f"S_R{reg}_Bit{b}_B")
        group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = True
        
# Match gates connect weakly to P_Bus0/1 (w0 = 0.2) to prevent phase pulling
for b in range(16):
    gate_id = f"Gate_Match{b}"
    group.engine.write_enable(gate_id)
    lane = b // 8
    group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
    group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = 5.0
    group.get_node(gate_id)["psi_bias"] = 0.0
    
# Neutralize belief gradients for host/battery/buses
for reg in ['X', 'Y']:
    for b in range(16):
        group.get_node(f"S_R{reg}_Bit{b}")["psi_bias"] = 0.0
        group.get_node(f"S_R{reg}_Bit{b}_B")["psi_bias"] = 0.0
group.get_node("P_Bus0")["psi_bias"] = 0.0
group.get_node("P_Bus1")["psi_bias"] = 0.0

# Enable value basins
for b in range(16):
    basin = group.semantic.basins[f"Basin_Val{b}"]
    for nid in basin.node_ids:
        group.engine.write_enable(nid)
        group.get_node(nid)["psi_bias"] = 0.0

for s in range(120):
    t = s * sequencer.dt
    # Set register access gates based on active registers
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
                
    # Set match gate outputs
    for b in range(16):
        gate_id = f"Gate_Match{b}"
        dest_basin_id = f"Basin_Val{b}"
        group.set_edge_connection(gate_id, group.semantic.basins[dest_basin_id].bridge_id, True)
        f_idx = (b % 8) // 2
        group.get_edge(gate_id, group.semantic.basins[dest_basin_id].bridge_id)["w0"] = sequencer.match_weights[f_idx]
        omega, phase_val = sequencer.get_match_gate_params(b)
        val_psi = 1.0 * math.sin(omega * t + phase_val)
        group.get_node(gate_id)["psi"] = val_psi
        group.get_node(gate_id)["psi_bias"] = val_psi
        
    group.engine.step(dt=sequencer.dt, damping=0.0)
    
    if s < 20:
        print(f"Q{s:02d} | {t:.2f} | R0:{group.get_node('S_RX_Bit0')['rho']:.2f} | R1:{group.get_node('S_RX_Bit1')['rho']:.2f} | G0_psi:{group.get_node('GATE_X_Bit0')['psi']:.4f} | G1_psi:{group.get_node('GATE_X_Bit1')['psi']:.4f} | B0:{group.get_node('P_Bus0')['rho']:.2f}")
