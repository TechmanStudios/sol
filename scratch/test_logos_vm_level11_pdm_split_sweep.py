#!/usr/bin/env python3
import sys
import os
import json
import math
import time
from pathlib import Path

sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root))
sys.path.insert(0, str(sol_root / "scratch"))

from hybrid_subsystem_framework import (
    UniversalManifold, SemanticManifold, ProcessingManifold,
    ManifoldGroup, Instruction, MicroInstructionSequencer, BasinConfig
)
from sol_engine import snapshot_state, restore_state

class MHRALevel11ProcessingManifold:
    def __init__(self, baseline_rho=15.0):
        self.nodes = []
        self.edges = []
        
        # Registers X and Y, each running with 16 independent resonators
        for reg in ['X', 'Y']:
            for b in range(16):
                host_id = f"S_R{reg}_Bit{b}"
                bat_id = f"S_R{reg}_Bit{b}_B"
                self.nodes.extend([
                    {"id": host_id, "label": f"Register{reg}_Bit{b}_Host", "group": "processing", "rho": baseline_rho * 20.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0},
                    {"id": bat_id, "label": f"Register{reg}_Bit{b}_Battery", "group": "processing", "rho": baseline_rho * 20.0, "isBattery": True, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 20.0, "semanticMass0": 20.0}
                ])
                # Prime coprime periods matching the verified prime configuration
                b_local = b % 8
                f_idx = b_local // 2
                p = [10.0, 12.0, 15.0, 20.0][f_idx]
                dt = 0.04
                omega = (2 * math.pi) / (p * dt)
                w0_tuned = 10.0 * (omega ** 2)
                self.edges.append({"from": host_id, "to": bat_id, "w0": w0_tuned})
                
        # Register access gates (16 gates per register)
        for reg in ['X', 'Y']:
            for b in range(16):
                gate_id = f"GATE_{reg}_Bit{b}"
                self.nodes.append(
                    {"id": gate_id, "label": f"Gate_{reg}_Bit{b}", "group": "bridge", "rho": baseline_rho, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0}
                )
                
        # Dual Shared Waveguide Bus Nodes
        self.nodes.extend([
            {"id": "P_Bus0", "label": "Shared_Bus_Lane0", "group": "processing", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0},
            {"id": "P_Bus1", "label": "Shared_Bus_Lane1", "group": "processing", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0}
        ])
        
        # Connect registers to respective bus lanes (bits 0-7 to Bus 0, bits 8-15 to Bus 1)
        for reg in ['X', 'Y']:
            for b in range(16):
                gate_id = f"GATE_{reg}_Bit{b}"
                lane = b // 8
                self.edges.extend([
                    {"from": f"S_R{reg}_Bit{b}", "to": gate_id, "w0": 5.0},
                    {"from": gate_id, "to": f"P_Bus{lane}", "w0": 5.0, "kind": "wormhole", "background": False}
                ])
            
        # 16 matching gates (0-7 connect to P_Bus0, 8-15 connect to P_Bus1)
        for b in range(16):
            gate_id = f"Gate_Match{b}"
            self.nodes.append(
                {"id": gate_id, "label": gate_id, "group": "bridge", "rho": baseline_rho, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0}
            )
            lane = b // 8
            self.edges.append(
                {"from": f"P_Bus{lane}", "to": gate_id, "w0": 5.0, "kind": "wormhole", "background": False}
            )

class Level11ManifoldGroup(ManifoldGroup):
    def __init__(self, semantic: SemanticManifold, processing: MHRALevel11ProcessingManifold, c_press: float = 2.0, damping: float = 0.0):
        self.semantic = semantic
        self.processing = processing
        self.raw_nodes = []
        self.raw_nodes.extend(semantic.nodes)
        self.raw_nodes.extend(processing.nodes)
        self.raw_edges = []
        self.raw_edges.extend(semantic.edges)
        self.raw_edges.extend(processing.edges)
        
        # Connect query input basin to BOTH bus lanes (very weak background weight)
        self.raw_edges.extend([
            {"from": semantic.basins["Basin_Query"].bridge_id, "to": "P_Bus0", "w0": 0.0001, "kind": "wormhole", "background": False},
            {"from": semantic.basins["Basin_Query"].bridge_id, "to": "P_Bus1", "w0": 0.0001, "kind": "wormhole", "background": False}
        ])
        
        # Connect matching gates to target value destination basins
        for b in range(16):
            gate_id = f"Gate_Match{b}"
            self.raw_edges.append(
                {"from": gate_id, "to": semantic.basins[f"Basin_Val{b}"].bridge_id, "w0": 0.0001, "kind": "wormhole", "background": False}
            )
            
        from sol_engine import SOLEngine
        self.engine = SOLEngine.from_graph(self.raw_nodes, self.raw_edges, c_press=c_press, damping=damping)
        self.engine.integration_mode = "rk4"
        self.engine.physics.semantic_cfg["decayRate"] = 0.0
        self.engine.physics.jeans_cfg = None
        self.engine.physics.conductance_max = 50000.0
        self.engine.physics.conductance_min = 1e-7
        self.engine.physics.conductance_gamma = 6.0
        self.engine.physics.psi_diffusion = 0.0
        self.engine.physics.psi_relax_base = 8.0
        self.engine.physics.psi_global_nudge = 0.0
        self.engine.physics.battery_cfg = {
            "qMax": 80.0, "qThresh": 5.0, "leakLambda": 0.01, "avalancheGain": 5.0,
            "resonanceBoost": 4.0, "dampingClamp": 0.1, "flipThreshold": 0.65,
            "collapseFactor": 0.10, "resonanceDrive": 50.0, "dampingDrag": 0.3,
            "diodeResonanceOut": 1.0, "diodeResonanceIn": 1.0, "diodeDampingOut": 1.0, "diodeDampingIn": 1.0
        }

    def prime_register(self, reg_name: str, active: bool, baseline_rho=15.0):
        # We prime all 16 register bit nodes
        for b in range(16):
            host = self.get_node(f"S_R{reg_name}_Bit{b}")
            bat = self.get_node(f"S_R{reg_name}_Bit{b}_B")
            if active:
                bat["b_state"] = 1
                bat["b_charge"] = 1.0
                bat["psi"] = 1.0
                bat["psi_bias"] = 1.0
                host["psi"] = 1.0
                host["psi_bias"] = 1.0
                host["rho"] = baseline_rho * 20.0
                bat["rho"] = baseline_rho * 20.0
            else:
                bat["b_state"] = -1
                bat["b_charge"] = 0.0
                bat["psi"] = -1.0
                bat["psi_bias"] = -1.0
                host["psi"] = -1.0
                host["psi_bias"] = -1.0
                host["rho"] = baseline_rho * 20.0
                bat["rho"] = baseline_rho * 20.0

class Level11Sequencer(MicroInstructionSequencer):
    def __init__(self, group: Level11ManifoldGroup, dt: float = 0.04, baseline_rho=15.0, query_steps=120, settle_steps=15):
        super().__init__(group, dt)
        self.min_active_register_mass = float('inf')
        self.history = []
        self.baseline_rho = baseline_rho
        self.query_steps = query_steps
        self.settle_steps = settle_steps
        
        # Prime coprime periods
        self.periods = [10.0, 12.0, 15.0, 20.0]
        self.omegas = [2 * math.pi / (p * self.dt) for p in self.periods]
        
        # Default calibrated phases
        self.calibrated_phases = [0.0] * 16
        
        # Match weights from match gates to value basins (scaled up to match high sensitivity)
        self.match_weights = [120.0, 80.0, 60.0, 40.0]

    def get_reg_gate_params(self, b: int) -> tuple[float, float]:
        b_local = b % 8
        f_idx = b_local // 2
        omega = self.omegas[f_idx]
        is_cosine = (b_local % 2 == 1)
        phase_offset = 0.5 * math.pi if is_cosine else 0.0
        return omega, phase_offset

    def get_match_gate_params(self, b: int) -> tuple[float, float]:
        b_local = b % 8
        f_idx = b_local // 2
        omega = self.omegas[f_idx]
        return omega, self.calibrated_phases[b]

    def execute_instruction(self, inst: Instruction):
        op = inst.op.upper()
        if op == "LOAD_16":
            reg_name = inst.args[0]
            val = int(inst.args[1])
            other_reg = "Y" if reg_name == "X" else "X"
            
            # 1. Initialize resonators and gates as write-locked by default
            for b in range(16):
                host = self.group.get_node(f"S_R{reg_name}_Bit{b}")
                bat = self.group.get_node(f"S_R{reg_name}_Bit{b}_B")
                self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}")
                self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}_B")
                
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
                
                self.group.engine.write_lock(f"S_R{other_reg}_Bit{b}")
                self.group.engine.write_lock(f"S_R{other_reg}_Bit{b}_B")
                
            for b in range(16):
                self.group.engine.write_lock(f"Gate_Match{b}")
                lane = b // 8
                self.group.set_edge_connection(f"P_Bus{lane}", f"Gate_Match{b}", False)
                
            for b in range(16):
                basin = self.group.semantic.basins[f"Basin_Val{b}"]
                for nid in basin.node_ids:
                    self.group.engine.write_lock(nid)
                    
            for nid in self.group.semantic.basins["Basin_Query"].node_ids:
                self.group.engine.write_enable(nid)
                
            amp = 150.0
            
            # --- PHASE 1: Load SINE bits (even bits) ---
            # Write-enable ONLY the active Sine resonators
            for b in range(16):
                is_sine = (b % 2 == 0)
                if is_sine and (val & (1 << b)):
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
            
            # Connect only active Sine gates
            for b in range(16):
                lane = b // 8
                g_target = f"GATE_{reg_name}_Bit{b}"
                is_sine = (b % 2 == 0)
                if is_sine and (val & (1 << b)):
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", True)
                    self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 5.0
                else:
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                    
            for s in range(40):
                t = s * self.dt
                # Drive active Sine gates
                for b in range(16):
                    is_sine = (b % 2 == 0)
                    if is_sine and (val & (1 << b)):
                        omega, phase_val = self.get_reg_gate_params(b)
                        val_psi = 1.0 * math.sin(omega * t + phase_val)
                        g_target = f"GATE_{reg_name}_Bit{b}"
                        self.group.get_node(g_target)["psi"] = val_psi
                        self.group.get_node(g_target)["psi_bias"] = val_psi
                        
                # Modulate bus with active Sine waves
                # Lane 0
                num_sine0 = sum(1 for b in range(8) if (b % 2 == 0) and (val & (1 << b)))
                src_rho0 = 15.0
                if num_sine0 > 0:
                    sum_sin0 = 0.0
                    for b in range(8):
                        if (b % 2 == 0) and (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin0 += math.sin(omega * t + phase_val)
                    src_rho0 += (amp / math.sqrt(num_sine0)) * sum_sin0
                # Lane 1
                num_sine1 = sum(1 for b in range(8, 16) if (b % 2 == 0) and (val & (1 << b)))
                src_rho1 = 15.0
                if num_sine1 > 0:
                    sum_sin1 = 0.0
                    for b in range(8, 16):
                        if (b % 2 == 0) and (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin1 += math.sin(omega * t + phase_val)
                    src_rho1 += (amp / math.sqrt(num_sine1)) * sum_sin1
                    
                self.group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
                self.group.get_node("P_Bus1")["rho"] = max(1.0, src_rho1)
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            # Disconnect all Sine gates and WRITE-LOCK all Sine resonators
            for b in range(16):
                is_sine = (b % 2 == 0)
                if is_sine:
                    lane = b // 8
                    g_target = f"GATE_{reg_name}_Bit{b}"
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                    self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}_B")
                    
            # --- PHASE 2: Load COSINE bits (odd bits) ---
            # Write-enable ONLY the active Cosine resonators
            for b in range(16):
                is_cos = (b % 2 == 1)
                if is_cos and (val & (1 << b)):
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
            
            # Connect only active Cosine gates
            for b in range(16):
                lane = b // 8
                g_target = f"GATE_{reg_name}_Bit{b}"
                is_cos = (b % 2 == 1)
                if is_cos and (val & (1 << b)):
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", True)
                    self.group.get_edge(g_target, f"P_Bus{lane}")["w0"] = 5.0
                else:
                    self.group.get_node(g_target)["psi_bias"] = -1.0
                    self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                    
            for s in range(40):
                t = s * self.dt
                # Drive active Cosine gates
                for b in range(16):
                    is_cos = (b % 2 == 1)
                    if is_cos and (val & (1 << b)):
                        omega, phase_val = self.get_reg_gate_params(b)
                        val_psi = 1.0 * math.sin(omega * t + phase_val)
                        g_target = f"GATE_{reg_name}_Bit{b}"
                        self.group.get_node(g_target)["psi"] = val_psi
                        self.group.get_node(g_target)["psi_bias"] = val_psi
                        
                # Modulate bus with active Cosine waves
                # Lane 0
                num_cos0 = sum(1 for b in range(8) if (b % 2 == 1) and (val & (1 << b)))
                src_rho0 = 15.0
                if num_cos0 > 0:
                    sum_sin0 = 0.0
                    for b in range(8):
                        if (b % 2 == 1) and (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin0 += math.sin(omega * t + phase_val)
                    src_rho0 += (amp / math.sqrt(num_cos0)) * sum_sin0
                # Lane 1
                num_cos1 = sum(1 for b in range(8, 16) if (b % 2 == 1) and (val & (1 << b)))
                src_rho1 = 15.0
                if num_cos1 > 0:
                    sum_sin1 = 0.0
                    for b in range(8, 16):
                        if (b % 2 == 1) and (val & (1 << b)):
                            omega, phase_val = self.get_reg_gate_params(b)
                            sum_sin1 += math.sin(omega * t + phase_val)
                    src_rho1 += (amp / math.sqrt(num_cos1)) * sum_sin1
                    
                self.group.get_node("P_Bus0")["rho"] = max(1.0, src_rho0)
                self.group.get_node("P_Bus1")["rho"] = max(1.0, src_rho1)
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            # Disconnect all Cosine gates and WRITE-LOCK all Cosine resonators
            for b in range(16):
                lane = b // 8
                g_target = f"GATE_{reg_name}_Bit{b}"
                self.group.get_node(g_target)["psi_bias"] = -1.0
                self.group.set_edge_connection(g_target, f"P_Bus{lane}", False)
                is_cos = (b % 2 == 1)
                if is_cos:
                    self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}")
                    self.group.engine.write_lock(f"S_R{reg_name}_Bit{b}_B")
                
            # WRITE-ENABLE ALL resonators so they settle correctly
            for b in range(16):
                self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}")
                self.group.engine.write_enable(f"S_R{reg_name}_Bit{b}_B")
                
            self.group.engine.write_enable("P_Bus0")
            self.group.engine.write_enable("P_Bus1")
            for b in range(16):
                basin = self.group.semantic.basins[f"Basin_Val{b}"]
                for nid in basin.node_ids:
                    self.group.engine.write_enable(nid)
            
            for s in range(self.settle_steps):
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
        elif op == "QUERY_16":
            phase_invert = (len(inst.args) > 0 and inst.args[0] == "minus")
            
            # Reset bus and matching gate densities to 15.0 at query start to clear transients
            self.group.get_node("P_Bus0")["rho"] = self.baseline_rho
            self.group.get_node("P_Bus1")["rho"] = self.baseline_rho
            for b in range(16):
                self.group.get_node(f"Gate_Match{b}")["rho"] = self.baseline_rho
                
            # Reset all edge fluxes to 0.0 to clear frozen flux transients, except for resonators!
            for e in self.group.engine.physics.edges:
                is_resonator = (
                    (e["from"].startswith("S_R") and e["to"].endswith("_B")) or
                    (e["to"].startswith("S_R") and e["from"].endswith("_B"))
                )
                if not is_resonator:
                    e["flux"] = 0.0
                
            # Determine which registers are active
            active_regs = []
            for reg in ['X', 'Y']:
                is_active = False
                for b in range(16):
                    bat = self.group.get_node(f"S_R{reg}_Bit{b}_B")
                    if bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.1:
                        is_active = True
                        break
                if is_active:
                    active_regs.append(reg)
                    
            # Write-enable all processing nodes, batteries isBattery=True
            self.group.engine.write_enable("P_Bus0")
            self.group.engine.write_enable("P_Bus1")
            for reg in ['X', 'Y']:
                for b in range(16):
                    self.group.engine.write_enable(f"S_R{reg}_Bit{b}")
                    self.group.engine.write_enable(f"S_R{reg}_Bit{b}_B")
                    self.group.get_node(f"S_R{reg}_Bit{b}_B")["isBattery"] = True
                    
            # Match gates connect weakly to P_Bus0/1 (w0 = 5.0) to prevent phase pulling
            for b in range(16):
                gate_id = f"Gate_Match{b}"
                self.group.engine.write_enable(gate_id)
                lane = b // 8
                self.group.set_edge_connection(f"P_Bus{lane}", gate_id, True)
                self.group.get_edge(f"P_Bus{lane}", gate_id)["w0"] = 5.0
                self.group.get_node(gate_id)["psi_bias"] = 0.0
                
            # Neutralize belief gradients for host/battery/buses
            for reg in ['X', 'Y']:
                for b in range(16):
                    self.group.get_node(f"S_R{reg}_Bit{b}")["psi_bias"] = 0.0
                    self.group.get_node(f"S_R{reg}_Bit{b}_B")["psi_bias"] = 0.0
            self.group.get_node("P_Bus0")["psi_bias"] = 0.0
            self.group.get_node("P_Bus1")["psi_bias"] = 0.0
            
            # Enable value basins
            for b in range(16):
                basin = self.group.semantic.basins[f"Basin_Val{b}"]
                for nid in basin.node_ids:
                    self.group.engine.write_enable(nid)
                    self.group.get_node(nid)["psi_bias"] = 0.0
                    
            for s in range(self.query_steps):
                t = s * self.dt
                # Set register access gates based on active registers (amplitude 1.0, weak coupling 5.0)
                for reg in ['X', 'Y']:
                    for b in range(16):
                        lane = b // 8
                        g_active = f"GATE_{reg}_Bit{b}"
                        
                        bat = self.group.get_node(f"S_R{reg}_Bit{b}_B")
                        is_bit_active = (bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.5)
                        if reg in active_regs and is_bit_active:
                            omega, phase_val = self.get_reg_gate_params(b)
                            val_psi = 1.0 * math.sin(omega * t + phase_val)
                            self.group.get_node(g_active)["psi"] = val_psi
                            self.group.get_node(g_active)["psi_bias"] = val_psi
                            self.group.set_edge_connection(g_active, f"P_Bus{lane}", True)
                            self.group.get_edge(g_active, f"P_Bus{lane}")["w0"] = 5.0
                        else:
                            self.group.get_node(g_active)["psi_bias"] = -1.0
                            self.group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                            
                # Set match gate outputs and connect to value basins (strong match weights)
                for b in range(16):
                    gate_id = f"Gate_Match{b}"
                    dest_basin_id = f"Basin_Val{b}"
                    bridge_node = self.group.semantic.basins[dest_basin_id].bridge_id
                    
                    self.group.set_edge_connection(gate_id, bridge_node, True)
                    f_idx = (b % 8) // 2
                    self.group.get_edge(gate_id, bridge_node)["w0"] = self.match_weights[f_idx]
                    
                    # Receiver-driven: drive the value basin bridge node's psi (amplitude 1.0)
                    omega, phase_val = self.get_match_gate_params(b)
                    if phase_invert:
                        phase_val += math.pi
                    val_psi = 1.0 * math.sin(omega * t + phase_val)
                    self.group.get_node(bridge_node)["psi"] = val_psi
                    self.group.get_node(bridge_node)["psi_bias"] = val_psi
                    
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()
                
            # Settle and close connections
            for s in range(40):
                for reg in ['X', 'Y']:
                    for b in range(16):
                        lane = b // 8
                        g_active = f"GATE_{reg}_Bit{b}"
                        self.group.get_node(g_active)["psi_bias"] = -1.0
                        self.group.set_edge_connection(g_active, f"P_Bus{lane}", False)
                        
                for b in range(16):
                    gate_id = f"Gate_Match{b}"
                    self.group.set_edge_connection(gate_id, self.group.semantic.basins[f"Basin_Val{b}"].bridge_id, False)
                    
                self.group.engine.step(dt=self.dt, damping=0.0)
                self.record_telemetry()

    def record_telemetry(self):
        active_masses = []
        for reg in ['X', 'Y']:
            for b in range(16):
                bat = self.group.get_node(f"S_R{reg}_Bit{b}_B")
                host = self.group.get_node(f"S_R{reg}_Bit{b}")
                if bat.get("b_state", -1) == 1 or bat.get("b_charge", 0.0) > 0.1:
                    active_masses.append(bat["rho"] + host["rho"])
                        
        if active_masses:
            min_act = min(active_masses)
            if min_act < self.min_active_register_mass:
                self.min_active_register_mass = min_act
                
        self.history.append({
            "step": len(self.history),
            "min_active_register_mass": self.min_active_register_mass if self.min_active_register_mass != float('inf') else 0.0
        })

def run_level11_trial(val_X: int, val_Y: int, calibrated_phases: list[float], baseline_rho=15.0, query_steps=120, settle_steps=15) -> tuple[list[float], list[dict]]:
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
        n["rho"] = baseline_rho * n.get("semanticMass", 1.0)
        
    processing = MHRALevel11ProcessingManifold(baseline_rho=baseline_rho)
    group = Level11ManifoldGroup(semantic, processing, c_press=2.0, damping=0.0)
    
    group.prime_basin("Basin_Query", active=True)
    q_basin = group.semantic.basins["Basin_Query"]
    for nid in q_basin.node_ids:
        node = group.get_node(nid)
        if nid == q_basin.hub_id:
            node["rho"] = 450.0
        else:
            node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    for i in range(16):
        basin = group.semantic.basins[f"Basin_Val{i}"]
        for nid in basin.node_ids:
            node = group.get_node(nid)
            node["rho"] = baseline_rho * node.get("semanticMass", 1.0)
            
    active_X = (val_X != 0)
    active_Y = (val_Y != 0)
    
    group.prime_register('X', active=active_X, baseline_rho=baseline_rho)
    group.prime_register('Y', active=active_Y, baseline_rho=baseline_rho)
        
    sequencer = Level11Sequencer(group, dt=0.04, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps)
    sequencer.calibrated_phases = calibrated_phases
        
    if active_X:
        sequencer.execute_instruction(Instruction("LOAD_16", ["X", val_X]))
    if active_Y:
        sequencer.execute_instruction(Instruction("LOAD_16", ["Y", val_Y]))
        
    post_load_snap = snapshot_state(group.engine.physics)
    
    sequencer.execute_instruction(Instruction("QUERY_16", ["plus"]))
    rhos_plus = [group.get_node(group.semantic.basins[f"Basin_Val{i}"].bridge_id)["rho"] for i in range(16)]
    
    restore_state(group.engine.physics, post_load_snap)
    
    sequencer.execute_instruction(Instruction("QUERY_16", ["minus"]))
    rhos_minus = [group.get_node(group.semantic.basins[f"Basin_Val{i}"].bridge_id)["rho"] for i in range(16)]
    
    deltas = [(rhos_plus[i] - rhos_minus[i]) / 2.0 for i in range(16)]
    return deltas, sequencer.history

def calibrate_pdm_phases_split(baseline_rho=15.0, query_steps=120, settle_steps=15) -> list[float]:
    print("Starting Split-Simultaneous phase calibration...", flush=True)
    calibrated = [0.0] * 16
    
    steps = 12
    phases = [2 * math.pi * i / steps for i in range(steps)]
    
    # 1. Sweep SINE bits (even bits: val_X = 0b0101010101010101)
    print("  Sweeping SINE (even) bits...", flush=True)
    val_sine = 0b0101010101010101
    sine_deltas = []
    for idx, ph in enumerate(phases):
        temp_phases = [0.0] * 16
        for b in range(16):
            if b % 2 == 0:
                temp_phases[b] = ph
        deltas, _ = run_level11_trial(val_sine, 0, temp_phases, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps)
        sine_deltas.append(deltas)
        
    # 2. Sweep COSINE bits (odd bits: val_X = 0b1010101010101010)
    print("  Sweeping COSINE (odd) bits...", flush=True)
    val_cos = 0b1010101010101010
    cos_deltas = []
    for idx, ph in enumerate(phases):
        temp_phases = [0.0] * 16
        for b in range(16):
            if b % 2 == 1:
                temp_phases[b] = ph
        deltas, _ = run_level11_trial(val_cos, 0, temp_phases, baseline_rho=baseline_rho, query_steps=query_steps, settle_steps=settle_steps)
        cos_deltas.append(deltas)
        
    # Reconstruct calibrated phases
    for b in range(16):
        best_phase = 0.0
        max_delta = -float('inf')
        is_sine = (b % 2 == 0)
        deltas_list = sine_deltas if is_sine else cos_deltas
        for idx, ph in enumerate(phases):
            d = deltas_list[idx][b]
            if d > max_delta:
                max_delta = d
                best_phase = ph
        b_local = b % 8
        f_idx = b_local // 2
        p = [10.0, 12.0, 15.0, 20.0][f_idx]
        wave_type = "Sine" if is_sine else "Cosine"
        print(f"    Bit {b:2d} (p={p:.1f}, {wave_type}): phase = {best_phase:.6f} ({best_phase/math.pi:.4f} * pi), max_delta = {max_delta:+.4f}", flush=True)
        calibrated[b] = best_phase
        
    print("PDM Phase Calibration Complete.", flush=True)
    return calibrated

def main():
    baseline = 15.0
    query_steps = 120
    settle_steps = 30
    
    calibrated_phases = calibrate_pdm_phases_split(baseline, query_steps, settle_steps)
    
    print("\nStarting Verification Cases...", flush=True)
    cases = [
        {
            "name": "Case A: Single-Register 16-Bit Word Recall",
            "val_X": 0b1010110011110001,
            "val_Y": 0,
            "expected_X": [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        },
        {
            "name": "Case B: Simultaneous Dual-Register Parallel Recall",
            "val_X": 0b1010000000001111,
            "val_Y": 0b0101111111110000,
            "expected_X": [1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1],
            "expected_Y": [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0]
        },
        {
            "name": "Case C: Selective Bit Masking (Odd Bits)",
            "val_X": 0b1010101010101010,
            "val_Y": 0,
            "expected_X": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        },
        {
            "name": "Case D: Phase-Reversed Rejection",
            "val_X": 0b1010110011110001,
            "val_Y": 0,
            "expected_X": [1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        }
    ]
    
    suite_ok = True
    worst_min_mass = float('inf')
    
    for idx, c in enumerate(cases):
        print(f"\nTrial {idx+1}/{len(cases)}: {c['name']}...", flush=True)
        if idx == 3: # Case D
            phases = list(calibrated_phases)
            phases[0] = (phases[0] + math.pi) % (2 * math.pi)
            deltas, history = run_level11_trial(c["val_X"], c["val_Y"], phases, baseline, query_steps, settle_steps)
        else:
            deltas, history = run_level11_trial(c["val_X"], c["val_Y"], calibrated_phases, baseline, query_steps, settle_steps)
            
        passed = True
        if idx == 1: # Case B
            expected = [c["expected_X"][i] | c["expected_Y"][i] for i in range(16)]
        else:
            expected = c["expected_X"]
            
        if idx == 3: # Case D
            expected[0] = 0
            
        print("  Bit verification:", flush=True)
        for i in range(16):
            exp_val = expected[i]
            d = deltas[i]
            if exp_val == 1:
                if d < 0.2:
                    passed = False
                    print(f"    [FAIL] Bit {i:2d} (Active): delta = {d:+.4f} (expected >= 0.2)", flush=True)
                else:
                    print(f"    [PASS] Bit {i:2d} (Active): delta = {d:+.4f}", flush=True)
            else:
                if d >= 0.1:
                    passed = False
                    print(f"    [FAIL] Bit {i:2d} (Flat):   delta = {d:+.4f} (expected < 0.1)", flush=True)
                else:
                    print(f"    [PASS] Bit {i:2d} (Flat):   delta = {d:+.4f}", flush=True)
                    
        min_mass = history[-1]["min_active_register_mass"]
        if min_mass < worst_min_mass:
            worst_min_mass = min_mass
        print(f"  Result: Passed={passed} | min_mass={min_mass:.2f}", flush=True)
        if not passed:
            suite_ok = False
            
    print(f"\nVerification Suite Result: {'PASSED' if (suite_ok and worst_min_mass >= 14.0) else 'FAILED'}")
    print(f"Worst active register mass: {worst_min_mass:.2f} (threshold >= 14.0)")

if __name__ == "__main__":
    main()
