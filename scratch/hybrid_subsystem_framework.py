#!/usr/bin/env python3
# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Hybrid Sub-system Framework (Level 5: Manifold-Systems)
============================================================
An object-oriented, programmable framework for executing multi-cycle analog
and semantic programs on coupled SOL substrates.
"""

from __future__ import annotations

import importlib.util
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# Add sol-core path
sol_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Force bind telemetry to prevent collisions
telemetry_path = sol_root / "tools" / "sol-core" / "telemetry.py"
spec = importlib.util.spec_from_file_location("telemetry", telemetry_path)
if spec and spec.loader:
    telemetry_mod = importlib.util.module_from_spec(spec)
    sys.modules["telemetry"] = telemetry_mod
    spec.loader.exec_module(telemetry_mod)
    telemetry_mod._TELEMETRY_ENABLED = False

os.environ["SOL_TELEMETRY_ENABLED"] = "false"

from sol_engine import SOLEngine


@dataclass
class BasinConfig:
    name: str
    hub_id: str
    bridge_id: str
    node_ids: list[str]
    battery_id: str | None = None

class UniversalManifold:
    """
    Universal Manifold (UM) Compiler/Loader:
    Compiles bare topological templates into structured semantic manifolds
    organized as attractor basins with hubs and spokes.
    """
    @staticmethod
    def build_semantic_basin(
        basin_id: str,
        num_nodes: int,
        start_idx: int,
        pure_wave: bool = False,
    ) -> tuple[list[dict], list[dict], BasinConfig]:
        """
        Builds a single semantic basin with a hub node, spoke nodes, and a bridge node.
        When pure_wave=True, attaches an internal phase-locked memory battery pocket so
        the basin sustains and transfers continuous wave states without Python holding biases.
        """
        nodes = []
        edges = []
        node_ids = []
        
        hub_id = f"S{start_idx}"
        bridge_id = f"S{start_idx + num_nodes - 1}"
        battery_id = f"S{start_idx}_B" if pure_wave else None
        
        for idx in range(num_nodes):
            node_id = f"S{start_idx + idx}"
            node_ids.append(node_id)
            # Hub node has high semantic mass (capacitance)
            sm = 30.0 if idx == 0 else 1.0
            init_bias = 0.0 if pure_wave else -1.0
            nodes.append({
                "id": node_id,
                "label": f"Semantic_{basin_id}_{node_id}",
                "group": "semantic",
                "rho": 5.0,
                "psi": -1.0,
                "psi_bias": init_bias,
                "semanticMass": sm,
                "semanticMass0": sm
            })
            
        # Hub to spokes connections
        for idx in range(1, num_nodes):
            spoke_id = f"S{start_idx + idx}"
            edges.append({"from": hub_id, "to": spoke_id, "w0": 1.5})

        if pure_wave and battery_id is not None:
            nodes.append({
                "id": battery_id,
                "label": f"Semantic_{basin_id}_Battery",
                "group": "semantic",
                "rho": 0.0,
                "isBattery": True,
                "b_state": -1,
                "b_charge": 0.0,
                "psi": -1.0,
                "psi_bias": -1.0,
                "semanticMass": 20.0,
                "semanticMass0": 20.0,
            })
            # 2 internal battery filaments hold hub strongly against spokes while remaining overwritable by 6 store filaments
            for k in range(2):
                edges.append({"from": hub_id, "to": battery_id, "w0": 10.0, "role": f"basin_bat_{basin_id}_{k}"})
            # 5 internal hub <-> bridge filaments for lossless pure-wave LOAD/STORE within RK4 stability bound
            for k in range(5):
                edges.append({"from": hub_id, "to": bridge_id, "w0": 3.0, "role": f"basin_bridge_{basin_id}_{k}"})
            
        config = BasinConfig(
            name=basin_id,
            hub_id=hub_id,
            bridge_id=bridge_id,
            node_ids=node_ids,
            battery_id=battery_id,
        )
        return nodes, edges, config

class SemanticManifold:
    """
    Semantic Manifold Wrapper:
    Maintains the state and configuration of memory attractor basins (RAM/ROM).
    """
    def __init__(self, nodes: list[dict], edges: list[dict], basins: list[BasinConfig]):
        self.nodes = nodes
        self.edges = edges
        self.basins = {b.name: b for b in basins}

class ProcessingManifold:
    """
    Processing Manifold Wrapper:
    Maintains the nodes, registers, gates, and summing core of the blank processing unit.
    When pure_wave=True, provisions continuous acoustic-phase wave interference cavities
    (threshold resonator, anti-phase destructive inverter, two-source destructive XOR
    cavity, and phase-transistor CMOVE coupler) eliminating all Python boolean shortcuts.
    """
    def __init__(self, pure_wave: bool = False):
        self.pure_wave = pure_wave
        self.nodes = []
        self.edges = []
        init_host_bias = 0.0 if pure_wave else -1.0
        
        for r in ("A", "B", "C", "D"):
            self.nodes.extend([
                {
                    "id": f"S_R{r}",
                    "label": f"Register{r}_Host",
                    "group": "processing",
                    "rho": 5.0,
                    "psi": -1.0,
                    "psi_bias": init_host_bias,
                    "semanticMass": 20.0,
                    "semanticMass0": 20.0,
                },
                {
                    "id": f"S_R{r}_B",
                    "label": f"Register{r}_Battery",
                    "group": "processing",
                    "rho": 0.0,
                    "isBattery": True,
                    "b_state": -1,
                    "b_charge": 0.0,
                    "psi": -1.0,
                    "psi_bias": -1.0,
                    "semanticMass": 20.0,
                    "semanticMass0": 20.0,
                },
            ])
            if pure_wave:
                # 2 internal battery filaments hold S_R{r} strongly during read while remaining overwritable by 5 write filaments
                for k in range(2):
                    self.edges.append({"from": f"S_R{r}", "to": f"S_R{r}_B", "w0": 10.0, "role": f"reg_bat_{r}"})
            else:
                self.edges.append({"from": f"S_R{r}", "to": f"S_R{r}_B", "w0": 20.0})

        # ALU Routing Gates (controlled by psi_bias)
        self.nodes.extend([
            {"id": "GATE_A", "label": "Gate_A", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0},
            {"id": "GATE_B", "label": "Gate_B", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0},
            {"id": "GATE_C", "label": "Gate_C", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0},
            {"id": "GATE_D", "label": "Gate_D", "group": "bridge", "rho": 0.0, "psi": -1.0, "psi_bias": -1.0, "semanticMass": 1.0}
        ])

        # Summing Core Node
        self.nodes.append(
            {"id": "P_Sum", "label": "Proc_SummingJunction", "group": "processing", "rho": 0.0, "psi": 0.0, "psi_bias": 0.0, "semanticMass": 1.0, "semanticMass0": 1.0}
        )

        if not pure_wave:
            # Legacy Internal ALU Edges
            self.edges.extend([
                {"from": "S_RA", "to": "GATE_A", "w0": 5.0},
                {"from": "GATE_A", "to": "P_Sum", "w0": 5.0, "kind": "wormhole", "background": False},
                {"from": "S_RB", "to": "GATE_B", "w0": 5.0},
                {"from": "GATE_B", "to": "P_Sum", "w0": 5.0, "kind": "wormhole", "background": False},
                {"from": "P_Sum", "to": "GATE_C", "w0": 5.0, "kind": "wormhole", "background": False},
                {"from": "GATE_C", "to": "S_RC", "w0": 5.0, "kind": "wormhole", "background": False},
                {"from": "P_Sum", "to": "GATE_D", "w0": 5.0, "kind": "wormhole", "background": False},
                {"from": "GATE_D", "to": "S_RD", "w0": 5.0, "kind": "wormhole", "background": False}
            ])
        else:
            # Symmetric Pure-Wave Register <-> Gate <-> P_Sum Filaments
            for r in ("A", "B", "C", "D"):
                # Gate sense path (1 filament each: minimal back-action on S_R{r} which has 2 battery filaments)
                self.edges.append({
                    "from": f"S_R{r}", "to": f"GATE_{r}",
                    "w0": 6.0, "kind": "wormhole", "background": False, "role": f"pw_reg_read_{r}",
                })
                self.edges.append({
                    "from": f"GATE_{r}", "to": "P_Sum",
                    "w0": 6.0, "kind": "wormhole", "background": False, "role": f"pw_bus_in_{r}",
                })
                # Direct Battery-Coupled Read Repeater for lossless COPY/STORE/Gate Superposition (6 filaments out of S_R{r}_B)
                for k in range(6):
                    self.edges.append({
                        "from": f"S_R{r}_B", "to": "P_Sum",
                        "w0": 1.0, "kind": "wormhole", "background": True, "role": f"pw_bat_drive_sum_{r}",
                    })
                # Direct 1-hop P_Sum -> S_R{r} write path for lossless pure-wave LOAD/COPY (6 filaments overcome 2 reg_bat filaments)
                for k in range(6):
                    self.edges.append({
                        "from": "P_Sum", "to": f"S_R{r}",
                        "w0": 3.0, "kind": "wormhole", "background": False, "role": f"pw_sum_write_{r}",
                    })
                # Write path from GATE_{r} -> S_R{r} for Phase Phi_2 Cavity-to-Register commit (5 filaments)
                for k in range(5):
                    self.edges.append({
                        "from": "P_Sum", "to": f"GATE_{r}",
                        "w0": 2.0, "kind": "wormhole", "background": False, "role": f"pw_bus_out_{r}",
                    })
                    self.edges.append({
                        "from": f"GATE_{r}", "to": f"S_R{r}",
                        "w0": 2.0, "kind": "wormhole", "background": False, "role": f"pw_reg_write_{r}",
                    })

            # Pure Wave-Interference Logic Cavities (acoustic-to-phase symmetry breaking)
            self.nodes.extend([
                # Neutral-phase (psi=0.0) continuous acoustic pressure pump (zero phase back-leakage!)
                {
                    "id": "P_Wave_Ref",
                    "label": "Wave_Carrier_Pump",
                    "group": "processing",
                    "rho": 500.0,
                    "psi": 0.0,
                    "psi_bias": 0.0,
                    "semanticMass": 0.5,
                    "semanticMass0": 0.5,
                },
                # Excitatory / Inhibitory GRMN Reset-Gated Waveguides (native SOLPhysics W_r, U_r, b_r)
                {
                    "id": "P_Excite_Gate",
                    "label": "Wave_Excite_Transistor",
                    "group": "processing",
                    "rho": 120.0,
                    "psi": 0.0,
                    "psi_bias": 0.0,
                    "semanticMass": 1.0,
                    "semanticMass0": 1.0,
                    "W_r": 0.0,
                    "U_r": 120.0,
                    "b_r": 0.0,
                },
                {
                    "id": "P_Quench_Gate",
                    "label": "Wave_Destructive_Quench_Transistor",
                    "group": "processing",
                    "rho": 120.0,
                    "psi": 0.0,
                    "psi_bias": 0.0,
                    "semanticMass": 1.0,
                    "semanticMass0": 1.0,
                    "W_r": 0.0,
                    "U_r": -120.0,
                    "b_r": 0.0,
                },
                # Dual Acoustic-to-Phase Transduction Cavities, Anti-Phase Sink, & Cavity Phase-Lock Resonator
                # Separating Excite and Quench into isolated cavities prevents an OFF gate (r_gate=0) from back-draining an ON branch
                {
                    "id": "P_Wave_Cavity",
                    "label": "Wave_Resonance_Cavity_1",
                    "group": "processing",
                    "rho": 0.0,
                    "psi": -0.4,
                    "psi_bias": 1.85,
                    "semanticMass": 1.0,
                    "semanticMass0": 1.0,
                },
                {
                    "id": "P_Wave_Cavity_2",
                    "label": "Wave_Resonance_Cavity_2",
                    "group": "processing",
                    "rho": 0.0,
                    "psi": -0.4,
                    "psi_bias": 1.85,
                    "semanticMass": 1.0,
                    "semanticMass0": 1.0,
                },
                {
                    "id": "P_Wave_Sink",
                    "label": "Wave_AntiPhase_Anchor",
                    "group": "processing",
                    "rho": 5.0,
                    "isBattery": True,
                    "b_state": -1,
                    "b_charge": 0.0,
                    "psi": -1.0,
                    "psi_bias": -1.0,
                    "semanticMass": 20.0,
                    "semanticMass0": 20.0,
                },
                {
                    "id": "P_Wave_Out_B",
                    "label": "Wave_Cavity_PhaseLock",
                    "group": "processing",
                    "rho": 0.0,
                    "isBattery": True,
                    "b_state": -1,
                    "b_charge": 0.0,
                    "psi": -1.0,
                    "psi_bias": -1.0,
                    "semanticMass": 10.0,
                    "semanticMass0": 10.0,
                },
                # Conditional Wave-Transistor Gate for pure-wave CMOVE
                {
                    "id": "P_CMove_Gate",
                    "label": "Wave_CMove_Transistor",
                    "group": "processing",
                    "rho": 0.0,
                    "psi": 0.0,
                    "psi_bias": 0.0,
                    "semanticMass": 1.0,
                    "semanticMass0": 1.0,
                    "W_r": 0.0,
                    "U_r": 120.0,
                    "b_r": 0.0,
                },
            ])
            # High-conductance acoustic carrier waveguides (w0=15000 saturates conductance_max=200 even at negative phase so r_gate governs cleanly)
            self.edges.extend([
                {"from": "P_Wave_Ref", "to": "P_Excite_Gate", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_ref_to_excite"},
                {"from": "P_Wave_Ref", "to": "P_Quench_Gate", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_ref_to_quench"},
                {"from": "P_Excite_Gate", "to": "P_Quench_Gate", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_excite_to_quench"},
                {"from": "P_Excite_Gate", "to": "P_Wave_Cavity", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_excite_to_cavity"},
                {"from": "P_Quench_Gate", "to": "P_Wave_Cavity", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_quench_to_cavity"},
                {"from": "P_Quench_Gate", "to": "P_Wave_Cavity_2", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_quench_to_cavity2"},
                {"from": "P_Wave_Ref", "to": "P_CMove_Gate", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_ref_to_cmove"},
                {"from": "P_CMove_Gate", "to": "P_Quench_Gate", "w0": 15000.0, "kind": "wormhole", "background": False, "role": "pw_cmove_to_quench"},
                {"from": "P_Wave_Cavity", "to": "P_Wave_Out_B", "w0": 80.0, "kind": "wormhole", "background": False, "role": "pw_cavity_to_out_b"},
                {"from": "P_Wave_Cavity_2", "to": "P_Wave_Out_B", "w0": 80.0, "kind": "wormhole", "background": False, "role": "pw_cavity2_to_out_b"},
            ])
            # 5 phase-sensing filaments from P_Sum into Excite / Quench gates (yields wide margin within RK4 stability bound)
            for k in range(5):
                self.edges.append({
                    "from": "P_Sum", "to": "P_Excite_Gate",
                    "w0": 0.0001, "kind": "wormhole", "background": True, "role": "pw_sum_sense_excite",
                })
                self.edges.append({
                    "from": "P_Sum", "to": "P_Quench_Gate",
                    "w0": 0.0001, "kind": "wormhole", "background": True, "role": "pw_sum_sense_quench",
                })
            # Dual anti-phase anchor filaments + P_Wave_Out_B keep OFF cavities strictly negative (psi < -0.10) even under +0.75 gate pull
            for k in range(2):
                self.edges.append({
                    "from": "P_Wave_Cavity", "to": "P_Wave_Sink",
                    "w0": 0.0001, "kind": "wormhole", "background": True, "role": "pw_cavity_sink",
                })
                self.edges.append({
                    "from": "P_Wave_Cavity_2", "to": "P_Wave_Sink",
                    "w0": 0.0001, "kind": "wormhole", "background": True, "role": "pw_cavity2_sink",
                })
            # High-fanout phase waveguides from P_Wave_Out_B -> GATE_{r} (6 background phase filaments: zero drain on cavity!)
            for r in ("A", "B", "C", "D"):
                for k in range(6):
                    self.edges.append({
                        "from": "P_Wave_Out_B", "to": f"GATE_{r}",
                        "w0": 1.0, "kind": "wormhole", "background": True, "role": f"pw_cavity_to_gate_{r}",
                    })
                # CMOVE phase-sense bundles: dest -> P_CMove_Gate and cond -> P_Quench_Gate (5 filaments each)
                for k in range(5):
                    self.edges.append({
                        "from": f"S_R{r}_B", "to": "P_CMove_Gate",
                        "w0": 0.0001, "kind": "wormhole", "background": True, "role": f"pw_cmove_dest_{r}",
                    })
                    self.edges.append({
                        "from": f"S_R{r}_B", "to": "P_Quench_Gate",
                        "w0": 0.0001, "kind": "wormhole", "background": True, "role": f"pw_cmove_cond_{r}",
                    })

class ManifoldGroup:
    """
    Manifold Group Orchestrator:
    Combines SemanticManifold and ProcessingManifold into a unified substrate.
    Instantiates and manages the SOLEngine instance and gated wormhole connections.
    """
    def __init__(
        self,
        semantic: SemanticManifold,
        processing: ProcessingManifold,
        c_press: float = 1.0,
        damping: float = 0.01,
        pure_wave: bool | None = None,
        *,
        flip_threshold: float | None = None,
        collapse_factor: float | None = None,
    ):
        self.semantic = semantic
        self.processing = processing
        self.damping = float(damping)
        self.pure_wave = bool(getattr(processing, "pure_wave", False)) if pure_wave is None else bool(pure_wave)
        self.flip_threshold = 0.65 if flip_threshold is None else float(flip_threshold)
        self.collapse_factor = 0.10 if collapse_factor is None else float(collapse_factor)

        # Merge nodes and edges
        self.raw_nodes = []
        self.raw_nodes.extend(semantic.nodes)
        self.raw_nodes.extend(processing.nodes)

        self.raw_edges = []
        self.raw_edges.extend(semantic.edges)
        self.raw_edges.extend(processing.edges)

        # Add bidirectional gated wormholes linking ALL Semantic bridges <-> P_Sum dynamically
        # so Basin_Sel, Basin_S, Basin_R, Basin_Q, Basin_Qbar, and Basin_Scratch_* can both LOAD and STORE.
        for b_name, b_cfg in semantic.basins.items():
            if self.pure_wave:
                # 6 phase filaments from basin battery -> P_Sum during LOAD (background=True prevents draining basin battery!)
                src_node = b_cfg.battery_id or b_cfg.bridge_id
                for _ in range(6):
                    self.raw_edges.append({
                        "from": src_node, "to": "P_Sum",
                        "w0": 1.0, "kind": "wormhole", "background": True, "role": f"wh_load_{b_name}",
                    })
                # 5 phase-sense filaments from basin battery -> P_CMove_Gate for direct 1-bit pure-wave LOAD_INDIRECT
                for _ in range(5):
                    self.raw_edges.append({
                        "from": src_node, "to": "P_CMove_Gate",
                        "w0": 0.0001, "kind": "wormhole", "background": True, "role": f"wh_cmove_{b_name}",
                    })
                # 8 write filaments from P_Sum -> hub_id during STORE (1-hop waveguide overcomes 2 internal basin battery filaments!)
                for _ in range(8):
                    self.raw_edges.append({
                        "from": "P_Sum", "to": b_cfg.hub_id,
                        "w0": 3.0, "kind": "wormhole", "background": False, "role": f"wh_store_{b_name}",
                    })
            else:
                self.raw_edges.append({
                    "from": b_cfg.bridge_id, "to": "P_Sum",
                    "w0": 0.0001, "kind": "wormhole", "background": False, "role": f"wh_load_{b_name}",
                })
                self.raw_edges.append({
                    "from": "P_Sum", "to": b_cfg.bridge_id,
                    "w0": 0.0001, "kind": "wormhole", "background": False, "role": f"wh_store_{b_name}",
                })

        # Build engine
        self.engine = SOLEngine.from_graph(self.raw_nodes, self.raw_edges, c_press=c_press, damping=self.damping)
        self.engine.integration_mode = "rk4"

        # Set physical parameters matching physical ALU guidelines (pure_wave D=1.5 keeps lambda_max * dt < 1.8 < 2.785)
        self.engine.physics.conductance_max = 200.0
        self.engine.physics.conductance_min = 1e-7
        self.engine.physics.conductance_gamma = 8.0
        self.engine.physics.psi_diffusion = 1.5 if self.pure_wave else 1.2
        self.engine.physics.psi_relax_base = 4.0 if self.pure_wave else 8.0
        self.engine.physics.psi_global_nudge = 0.0

        # Apply battery configuration (avalanche gain memory cells)
        self.engine.physics.battery_cfg = {
            "qMax": 80.0,
            "qThresh": 5.0,
            "leakLambda": 0.01,
            "avalancheGain": 5.0,
            "resonanceBoost": 4.0,
            "dampingClamp": 0.1,
            "flipThreshold": self.flip_threshold,
            "collapseFactor": self.collapse_factor,
            "resonanceDrive": 50.0,
            "dampingDrag": 0.3,
            "diodeResonanceOut": 1.0,
            "diodeResonanceIn": 1.0,
            "diodeDampingOut": 1.0,
            "diodeDampingIn": 1.0,
        }

        # Index role-tagged edges for O(1) pure-wave waveguide switching and preserve explicit background flags
        self._edges_by_role: dict[str, list[dict]] = {}
        self._active_dynamic_roles: set[str] = set()
        for idx, e in enumerate(self.engine.physics.edges):
            if idx < len(self.raw_edges) and "background" in self.raw_edges[idx]:
                e["background"] = bool(self.raw_edges[idx]["background"])
                e["_orig_background"] = bool(self.raw_edges[idx]["background"])
            role = e.get("role")
            if role:
                self._edges_by_role.setdefault(role, []).append(e)

        # Disconnect all dynamic wormholes initially
        for role in self._edges_by_role:
            if role.startswith(("wh_", "pw_")):
                self.set_role_connection(role, False)

    def step(self, dt: float = 0.05, damping: float | None = None):
        use_damping = self.damping if damping is None else float(damping)
        self.engine.step(dt=dt, damping=use_damping)

    def run_steps(
        self,
        steps: int,
        dt: float = 0.05,
        damping: float | None = None,
        *,
        pre_step_node: dict | None = None,
        pre_step_rho: float = 500.0,
        pre_step_psi: float = 0.0,
    ) -> None:
        use_damping = self.damping if damping is None else float(damping)
        self.engine.run_steps(
            steps,
            dt=dt,
            damping=use_damping,
            pre_step_node=pre_step_node,
            pre_step_rho=pre_step_rho,
            pre_step_psi=pre_step_psi,
        )

    def get_node(self, node_id: str) -> dict:
        return self.engine.physics.node_by_id[node_id]

    def get_edge(self, from_id: str, to_id: str) -> dict:
        return next(e for e in self.engine.physics.edges if e["from"] == from_id and e["to"] == to_id)

    def get_edges(self, from_id: str, to_id: str) -> list[dict]:
        return [e for e in self.engine.physics.edges if e["from"] == from_id and e["to"] == to_id]

    def set_edge_connection(self, from_id: str, to_id: str, connected: bool):
        for edge in self.get_edges(from_id, to_id):
            if connected:
                edge["from_idx"] = self.engine.physics.node_index_by_id[from_id]
                edge["to_idx"] = self.engine.physics.node_index_by_id[to_id]
            else:
                edge["from_idx"] = None
                edge["to_idx"] = None

    def set_role_connection(self, role: str, connected: bool):
        node_idx_map = self.engine.physics.node_index_by_id
        is_dyn = role.startswith(("wh_", "pw_"))
        if connected:
            for edge in self._edges_by_role.get(role, ()):
                edge["from_idx"] = node_idx_map[edge["from"]]
                edge["to_idx"] = node_idx_map[edge["to"]]
                edge["background"] = bool(edge.get("_orig_background", edge.get("background", False)))
            if is_dyn:
                self._active_dynamic_roles.add(role)
        else:
            for edge in self._edges_by_role.get(role, ()):
                edge["from_idx"] = None
                edge["to_idx"] = None
                # Also shield disconnected battery-touching waveguides from update_batteries
                edge["background"] = True
                if is_dyn:
                    edge["flux"] = 0.0
            if is_dyn:
                self._active_dynamic_roles.discard(role)

    def disconnect_all_dynamic_roles(self) -> None:
        if not self._active_dynamic_roles:
            return
        for role in tuple(self._active_dynamic_roles):
            for edge in self._edges_by_role.get(role, ()):
                edge["from_idx"] = None
                edge["to_idx"] = None
                edge["background"] = True
                edge["flux"] = 0.0
        self._active_dynamic_roles.clear()
        
    def prime_basin(self, name: str, active: bool):
        """Primes a semantic basin with either active (1.0) or collapsed (-1.0) belief and baseline mass."""
        basin = self.semantic.basins[name]
        state = 1.0 if active else -1.0
        for nid in basin.node_ids:
            node = self.get_node(nid)
            node["psi"] = state
            node["psi_bias"] = 0.0 if self.pure_wave else state
            if active and nid == basin.hub_id:
                node["rho"] = 60.0
            else:
                node["rho"] = 5.0
        if basin.battery_id and basin.battery_id in self.engine.physics.node_by_id:
            bat = self.get_node(basin.battery_id)
            bat["b_state"] = 1 if active else -1
            bat["b_charge"] = 1.0 if active else 0.0
            bat["psi"] = state
            bat["psi_bias"] = state
            bat["rho"] = 20.0 if active else 0.0

    def prime_register(self, name: str, active: bool):
        """Primes an ALU register with active or collapsed state."""
        host = self.get_node(f"S_R{name}")
        bat = self.get_node(f"S_R{name}_B")
        if active:
            bat["b_state"] = 1
            bat["b_charge"] = 1.0
            bat["psi"] = 1.0
            bat["psi_bias"] = 1.0
            host["psi"] = 1.0
            host["psi_bias"] = 0.0 if self.pure_wave else 1.0
            host["rho"] = 40.0
            bat["rho"] = 20.0
        else:
            bat["b_state"] = -1
            bat["b_charge"] = 0.0
            bat["psi"] = -1.0
            bat["psi_bias"] = -1.0
            host["psi"] = -1.0
            host["psi_bias"] = 0.0 if self.pure_wave else -1.0
            host["rho"] = 5.0
            bat["rho"] = 0.0

@dataclass
class Instruction:
    op: str  # 'LOAD', 'STORE', 'OR', 'AND', 'COPY', 'CLEAR', 'RESET_CORE'
    args: list[Any] = field(default_factory=list)

class MicroInstructionSequencer:
    """
    Micro-Instruction Sequencer:
    Takes a program (list of Instruction objects) and executes it step-by-step
    by controlling routing gates, wormholes, and biases of the ManifoldGroup.
    When pure_wave=True, all memory transfers and logic gates execute strictly
    through continuous SOLEngine RK4 acoustic pressure, phase diffusion, and
    wave-interference cavities with zero Python boolean shortcuts on b_state.
    """
    def __init__(
        self,
        group: ManifoldGroup,
        dt: float = 0.05,
        pure_wave: bool | None = None,
        wave_threshold_offset: float = 0.0,
        record_substep_telemetry: bool = True,
    ):
        self.group = group
        self.dt = dt
        self.pure_wave = bool(getattr(group, "pure_wave", False)) if pure_wave is None else bool(pure_wave)
        self.wave_threshold_offset = float(wave_threshold_offset)
        self.record_substep_telemetry = bool(record_substep_telemetry)
        self.history: list[dict[str, Any]] = []
        self.python_boolean_shortcuts_used: int = 0
        self.pure_wave_quench_ops: int = 0
        self.wave_gate_telemetry: list[dict[str, Any]] = []

        node_by_id = self.group.engine.physics.node_by_id
        zero_bias_nodes: list[dict] = []
        for r in ("A", "B", "C", "D"):
            if f"S_R{r}" in node_by_id:
                zero_bias_nodes.append(node_by_id[f"S_R{r}"])
            if f"GATE_{r}" in node_by_id:
                zero_bias_nodes.append(node_by_id[f"GATE_{r}"])
        for basin in self.group.semantic.basins.values():
            for nid in basin.node_ids:
                if nid in node_by_id:
                    zero_bias_nodes.append(node_by_id[nid])
        self._pw_zero_bias_nodes = zero_bias_nodes
        self._p_sum_node = node_by_id["P_Sum"]
        self._pw_ref_node = node_by_id.get("P_Wave_Ref")
        self._pw_sink_node = node_by_id.get("P_Wave_Sink")
        self._pw_cav_nodes = [node_by_id[cid] for cid in ("P_Wave_Cavity", "P_Wave_Cavity_2") if cid in node_by_id]
        self._pw_out_b_node = node_by_id.get("P_Wave_Out_B")
        self._pw_gate_nodes = [
            node_by_id[gid]
            for gid in ("P_Excite_Gate", "P_Quench_Gate", "P_CMove_Gate")
            if gid in node_by_id
        ]

    def set_wormhole_connections(self, active_basin_name: str | None = None, is_load: bool = True):
        for b_name, b_cfg in self.group.semantic.basins.items():
            load_conn = bool(is_load and b_name == active_basin_name)
            store_conn = bool((not is_load) and b_name == active_basin_name)
            if f"wh_load_{b_name}" in self.group._edges_by_role:
                self.group.set_role_connection(f"wh_load_{b_name}", load_conn)
            else:
                try:
                    self.group.set_edge_connection(b_cfg.bridge_id, "P_Sum", load_conn)
                except StopIteration:
                    pass
            if f"wh_store_{b_name}" in self.group._edges_by_role:
                self.group.set_role_connection(f"wh_store_{b_name}", store_conn)
            else:
                try:
                    self.group.set_edge_connection("P_Sum", b_cfg.bridge_id, store_conn)
                except StopIteration:
                    pass

    def apply_holding_biases_processing(self):
        if self.pure_wave:
            for name in ["S_RA", "S_RB", "S_RC", "S_RD"]:
                if name in self.group.engine.physics.node_by_id:
                    self.group.get_node(name)["psi_bias"] = 0.0
            return
        for name in ["S_RA", "S_RB", "S_RC", "S_RD"]:
            if name + "_B" in self.group.engine.physics.node_by_id:
                state = self.group.get_node(name + "_B")["b_state"]
                self.group.get_node(name)["psi_bias"] = 1.0 if state == 1 else -1.0

    def apply_holding_biases_semantic(self):
        if self.pure_wave:
            for basin in self.group.semantic.basins.values():
                for nid in basin.node_ids:
                    self.group.get_node(nid)["psi_bias"] = 0.0
            return
        # Keeps spokes aligned with hub belief to prevent dilution drag
        for basin in self.group.semantic.basins.values():
            hub = self.group.get_node(basin.hub_id)
            state = 1.0 if hub["psi"] >= 0 else -1.0
            for nid in basin.node_ids:
                self.group.get_node(nid)["psi_bias"] = state

    def configure_alu_output_routing(self, active_dest: str | None, default_w0: float = 0.0001):
        if self.pure_wave:
            return
        for r in ['C', 'D']:
            try:
                conn = (r == active_dest or active_dest is None)
                self.group.set_edge_connection("P_Sum", f"GATE_{r}", conn)
                edge = self.group.get_edge("P_Sum", f"GATE_{r}")
                edge["w0"] = 5.0 if r == active_dest else default_w0
            except StopIteration:
                pass

    def _reset_pure_wave_routes(self):
        """Disconnects all dynamic pure-wave waveguides and resets neutral carrier biases without reading b_state."""
        self.group.disconnect_all_dynamic_roles()
        for n in self._pw_zero_bias_nodes:
            n["psi_bias"] = 0.0
        p_sum = self._p_sum_node
        p_sum["psi_bias"] = 0.0
        p_sum["psi"] = 0.0
        p_sum["rho"] = 0.0
        ref = self._pw_ref_node
        if ref is not None:
            ref["rho"] = 500.0
            ref["psi"] = 0.0
            ref["psi_bias"] = 0.0
        sink = self._pw_sink_node
        if sink is not None:
            sink["isBattery"] = True
            sink["b_state"] = -1
            sink["b_charge"] = 0.0
            sink["rho"] = 5.0
            sink["psi"] = -1.0
            sink["psi_bias"] = -1.0
        for cav in self._pw_cav_nodes:
            cav["rho"] = 0.0
            cav["psi"] = -0.4
            cav["psi_bias"] = 1.85
        out_b = self._pw_out_b_node
        if out_b is not None:
            out_b["b_state"] = -1
            out_b["b_charge"] = 0.0
            out_b["psi"] = -1.0
            out_b["psi_bias"] = -1.0
            out_b["rho"] = 0.0
        for gn in self._pw_gate_nodes:
            gn["rho"] = 0.0
            gn["psi"] = 0.0
            gn["psi_bias"] = 0.0

    def _advance_pure_wave_steps(self, steps: int, *, pump_ref: bool = False) -> None:
        if steps <= 0:
            return
        ref_node = self._pw_ref_node if pump_ref else None
        if self.record_substep_telemetry:
            for _ in range(steps):
                if ref_node is not None:
                    ref_node["rho"] = 500.0
                    ref_node["psi"] = 0.0
                self.group.step(dt=self.dt)
                self.record_telemetry()
        else:
            self.group.run_steps(
                steps,
                dt=self.dt,
                pre_step_node=ref_node,
                pre_step_rho=500.0,
                pre_step_psi=0.0,
            )

    def _settle_pure_wave(self, steps: int = 10):
        self._reset_pure_wave_routes()
        self._advance_pure_wave_steps(steps)
        if steps > 0 and not self.record_substep_telemetry:
            self.record_telemetry()

    def normalize_register_masses(self):
        """Locks register masses back to nominal levels (DRAM voltage regulator)."""
        if self.pure_wave:
            # In pure-wave mode, register batteries self-maintain mass without Python b_state branching
            return
        for name in ["S_RA", "S_RB"]:
            bat = self.group.get_node(name + "_B")
            host = self.group.get_node(name)
            if bat["b_state"] == 1:
                host["rho"] = 40.0
                bat["rho"] = 20.0
            else:
                host["rho"] = 5.0
                bat["rho"] = 0.0

    def _commit_pure_wave_cavity_to_register(self, dest: str, op_label: str, psi_sum_end: float, psi_cav_end: float, rho_cav_end: float):
        """
        Clock Phase Phi_2: Disconnects Stage-1 interference sense waveguides so Master Resonator
        P_Wave_Out_B holds its phase-locked wave eigenstate, and couples P_Wave_Out_B -> GATE_{dest} -> S_R{dest}.
        """
        self.group.disconnect_all_dynamic_roles()

        self.group.set_role_connection(f"pw_cavity_to_gate_{dest}", True)
        self.group.set_role_connection(f"pw_reg_write_{dest}", True)
        self._advance_pure_wave_steps(45)

        dest_bat = self.group.get_node(f"S_R{dest}_B")
        dest_host = self.group.get_node(f"S_R{dest}")
        out_b = self.group.get_node("P_Wave_Out_B")
        tau = float(self.group.engine.physics.battery_cfg.get("flipThreshold", 0.65))

        self.wave_gate_telemetry.append({
            "op": op_label,
            "dest": dest,
            "psi_sum": round(psi_sum_end, 5),
            "psi_cavity": round(psi_cav_end, 5),
            "rho_cavity": round(rho_cav_end, 4),
            "master_out_b_state": int(out_b["b_state"]),
            "dest_b_charge": round(float(dest_bat["b_charge"]), 5),
            "dest_b_state": int(dest_bat["b_state"]),
            "charge_margin_vs_tau": round(abs(float(dest_bat["b_charge"]) - tau), 5),
            "dest_register_mass": round(float(dest_host["rho"] + dest_bat["rho"]), 4),
        })
        self._settle_pure_wave(10)

    def _execute_pure_wave_gate(self, op: str, dest: str, src_a: str = "A", src_b: str = "B"):
        """
        Executes logic gates strictly through 3-phase continuous acoustic-phase wave superposition,
        GRMN wave-transistor quenching, acoustic-to-phase cavity symmetry breaking, and
        master-slave resonator phase locking — ZERO Python boolean evaluation on b_state.
        """
        self._reset_pure_wave_routes()

        # Clock Phase Phi_0 (12 RK4 steps): Pre-settle P_Sum and wave-transistor gate phases
        # before opening acoustic carrier pump P_Wave_Ref so zero t=0 transient mass leaks.
        if op == "NOT_WAVE":
            self.group.set_role_connection(f"pw_bat_drive_sum_{src_a}", True)
        else:
            self.group.set_role_connection(f"pw_bat_drive_sum_{src_a}", True)
            self.group.set_role_connection(f"pw_bat_drive_sum_{src_b}", True)

        excite = self.group.get_node("P_Excite_Gate")
        quench = self.group.get_node("P_Quench_Gate")

        gain = 120.0
        thresh_or = -0.20 + self.wave_threshold_offset
        thresh_and = 0.20 + self.wave_threshold_offset
        thresh_not = 0.00 + self.wave_threshold_offset

        excite["W_r"] = 0.0
        quench["W_r"] = 0.0

        if op in ("OR", "OR_WAVE"):
            excite["U_r"] = gain
            excite["b_r"] = -gain * thresh_or
            self.group.set_role_connection("pw_sum_sense_excite", True)
        elif op in ("AND", "AND_WAVE"):
            excite["U_r"] = gain
            excite["b_r"] = -gain * thresh_and
            self.group.set_role_connection("pw_sum_sense_excite", True)
        elif op == "NOT_WAVE":
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_not
            self.group.set_role_connection("pw_sum_sense_quench", True)
        elif op == "NOR_WAVE":
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_or
            self.group.set_role_connection("pw_sum_sense_quench", True)
        elif op == "NAND_WAVE":
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_and
            self.group.set_role_connection("pw_sum_sense_quench", True)
        elif op == "XOR_WAVE":
            excite["U_r"] = gain
            excite["b_r"] = -gain * thresh_or
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_and
            self.group.set_role_connection("pw_sum_sense_excite", True)
            self.group.set_role_connection("pw_sum_sense_quench", True)
        elif op == "XNOR_WAVE":
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_or
            excite["U_r"] = gain
            excite["b_r"] = -gain * thresh_and
            self.group.set_role_connection("pw_sum_sense_excite", True)
            self.group.set_role_connection("pw_sum_sense_quench", True)
        else:
            raise ValueError(f"Unsupported pure-wave gate opcode: {op}")

        self.group.set_role_connection("pw_cavity_sink", True)
        self.group.set_role_connection("pw_cavity_to_out_b", True)
        if op == "XNOR_WAVE":
            self.group.set_role_connection("pw_cavity2_sink", True)
            self.group.set_role_connection("pw_cavity2_to_out_b", True)

        self._advance_pure_wave_steps(12)

        # Clock Phase Phi_1 (45 RK4 steps): Open acoustic carrier pump waveguides
        if op in ("OR", "OR_WAVE", "AND", "AND_WAVE"):
            self.group.set_role_connection("pw_ref_to_excite", True)
            self.group.set_role_connection("pw_excite_to_cavity", True)
        elif op in ("NOT_WAVE", "NOR_WAVE", "NAND_WAVE"):
            self.group.set_role_connection("pw_ref_to_quench", True)
            self.group.set_role_connection("pw_quench_to_cavity", True)
        elif op == "XOR_WAVE":
            self.group.set_role_connection("pw_ref_to_excite", True)
            self.group.set_role_connection("pw_excite_to_quench", True)
            self.group.set_role_connection("pw_quench_to_cavity", True)
        elif op == "XNOR_WAVE":
            self.group.set_role_connection("pw_ref_to_quench", True)
            self.group.set_role_connection("pw_ref_to_excite", True)
            self.group.set_role_connection("pw_quench_to_cavity2", True)
            self.group.set_role_connection("pw_excite_to_cavity", True)

        self._advance_pure_wave_steps(45, pump_ref=True)

        psi_sum_end = float(self.group.get_node("P_Sum")["psi"])
        cav1 = self.group.get_node("P_Wave_Cavity")
        cav2 = self.group.get_node("P_Wave_Cavity_2")
        psi_cav_end = float(max(cav1["psi"], cav2["psi"])) if op == "XNOR_WAVE" else float(cav1["psi"])
        rho_cav_end = float(cav1["rho"] + cav2["rho"]) if op == "XNOR_WAVE" else float(cav1["rho"])

        # Clock Phase Phi_2: Commit Master Resonator P_Wave_Out_B to destination register
        self._commit_pure_wave_cavity_to_register(dest, op, psi_sum_end, psi_cav_end, rho_cav_end)

    def execute_instruction(self, inst: Instruction):
        """Runs the step sequence for a single instruction."""
        op = inst.op.upper()

        # Native Lumina physical control instructions (NUDGE, SETTLE, ASSERT_MASS)
        if op == "NUDGE":
            basin_name, amount = str(inst.args[0]), float(inst.args[1])
            if basin_name in ("ALL", "*", "Basin_ALL"):
                for b_cfg in self.group.semantic.basins.values():
                    self.group.get_node(b_cfg.hub_id)["rho"] += amount
                for r in ("A", "B", "C", "D"):
                    if f"S_R{r}" in self.group.engine.physics.node_by_id:
                        self.group.get_node(f"S_R{r}")["rho"] += amount
            elif basin_name in self.group.semantic.basins:
                b_cfg = self.group.semantic.basins[basin_name]
                self.group.get_node(b_cfg.hub_id)["rho"] += amount
            elif basin_name in self.group.engine.physics.node_by_id:
                self.group.get_node(basin_name)["rho"] += amount
            elif f"S_R{basin_name}" in self.group.engine.physics.node_by_id:
                self.group.get_node(f"S_R{basin_name}")["rho"] += amount
            self.record_telemetry()
            return

        if op == "SETTLE":
            steps = int(inst.args[0])
            if self.pure_wave:
                self._reset_pure_wave_routes()
                if steps > 0:
                    self._advance_pure_wave_steps(steps)
                    if not self.record_substep_telemetry:
                        self.record_telemetry()
                return
            for _ in range(max(0, steps)):
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()
            return

        if op == "ASSERT_MASS":
            target_name, min_rho = str(inst.args[0]), float(inst.args[1])
            if target_name in self.group.semantic.basins:
                b_cfg = self.group.semantic.basins[target_name]
                actual_rho = sum(self.group.get_node(nid)["rho"] for nid in b_cfg.node_ids)
                if b_cfg.battery_id and b_cfg.battery_id in self.group.engine.physics.node_by_id:
                    actual_rho += self.group.get_node(b_cfg.battery_id)["rho"]
            elif f"S_R{target_name}" in self.group.engine.physics.node_by_id:
                actual_rho = self.group.get_node(f"S_R{target_name}")["rho"] + self.group.get_node(f"S_R{target_name}_B")["rho"]
            elif target_name in self.group.engine.physics.node_by_id:
                actual_rho = self.group.get_node(target_name)["rho"]
            else:
                raise KeyError(f"Unknown ASSERT_MASS target: {target_name}")
            if actual_rho < min_rho:
                raise AssertionError(
                    f"Physical mass preservation violated on {target_name}: rho={actual_rho:.3f} < {min_rho:.3f}"
                )
            return

        # Pure-wave physical memory transfers (zero Python b_state / hub['psi'] shortcuts)
        if self.pure_wave and op == "LOAD":
            reg, basin_name = inst.args[0], inst.args[1]
            self._reset_pure_wave_routes()
            self.group.set_role_connection(f"wh_load_{basin_name}", True)
            self.group.set_role_connection(f"pw_sum_write_{reg}", True)
            self._advance_pure_wave_steps(45)
            self._settle_pure_wave(10)
            return

        if self.pure_wave and op == "STORE":
            reg, basin_name = inst.args[0], inst.args[1]
            self._reset_pure_wave_routes()
            self.group.set_role_connection(f"pw_bat_drive_sum_{reg}", True)
            self.group.set_role_connection(f"wh_store_{basin_name}", True)
            self._advance_pure_wave_steps(50)
            self._settle_pure_wave(10)
            return

        if self.pure_wave and op == "COPY":
            src, dest = inst.args[0], inst.args[1]
            if src == dest:
                self._settle_pure_wave(5)
                return
            self._reset_pure_wave_routes()
            self.group.set_role_connection(f"pw_bat_drive_sum_{src}", True)
            self.group.set_role_connection(f"pw_sum_write_{dest}", True)
            self._advance_pure_wave_steps(45)
            self._settle_pure_wave(10)
            return

        if self.pure_wave and op == "CMOVE":
            dest, src, cond = inst.args[0], inst.args[1], inst.args[2]
            if src == dest:
                self._settle_pure_wave(5)
                return
            self._reset_pure_wave_routes()
            # Pure-wave dual-cavity multiplexer: (cond & src) | (~cond & dest)
            #   Path B: S_R{cond}_B + S_R{src}_B -> P_Sum -> P_Excite_Gate(thresh_and) -> P_Wave_Cavity
            #   Path A: P_Wave_Ref -> P_CMove_Gate(dest) -> P_Quench_Gate(~cond) -> P_Wave_Cavity_2
            gain = 120.0
            thresh_and = 0.20 + self.wave_threshold_offset
            thresh_cmove = -0.20 + self.wave_threshold_offset
            thresh_quench = 0.20 + self.wave_threshold_offset

            excite = self.group.get_node("P_Excite_Gate")
            cmove_gate = self.group.get_node("P_CMove_Gate")
            quench = self.group.get_node("P_Quench_Gate")
            excite["W_r"] = 0.0
            cmove_gate["W_r"] = 0.0
            quench["W_r"] = 0.0

            excite["U_r"] = gain
            excite["b_r"] = -gain * thresh_and
            cmove_gate["U_r"] = gain
            cmove_gate["b_r"] = -gain * thresh_cmove
            quench["U_r"] = -gain
            quench["b_r"] = gain * thresh_quench

            # Clock Phase Phi_0 (12 RK4 steps): Pre-settle Path B (P_Sum -> P_Excite_Gate) and
            # Path A (P_CMove_Gate, P_Quench_Gate) phases while keeping both cavities anchored < 0.
            self.group.set_role_connection("pw_cavity_sink", True)
            self.group.set_role_connection("pw_cavity_to_out_b", True)
            self.group.set_role_connection("pw_cavity2_sink", True)
            self.group.set_role_connection("pw_cavity2_to_out_b", True)
            self.group.set_role_connection(f"pw_bat_drive_sum_{cond}", True)
            self.group.set_role_connection(f"pw_bat_drive_sum_{src}", True)
            self.group.set_role_connection("pw_sum_sense_excite", True)
            self.group.set_role_connection(f"pw_cmove_dest_{dest}", True)
            self.group.set_role_connection(f"pw_cmove_cond_{cond}", True)

            self._advance_pure_wave_steps(12)

            # Clock Phase Phi_1 (65 RK4 steps): Open carrier pump into dual isolated cavities
            self.group.set_role_connection("pw_ref_to_excite", True)
            self.group.set_role_connection("pw_excite_to_cavity", True)
            self.group.set_role_connection("pw_ref_to_cmove", True)
            self.group.set_role_connection("pw_cmove_to_quench", True)
            self.group.set_role_connection("pw_quench_to_cavity2", True)

            self._advance_pure_wave_steps(65, pump_ref=True)

            psi_sum_end = float(self.group.get_node("P_Sum")["psi"])
            cav1 = self.group.get_node("P_Wave_Cavity")
            cav2 = self.group.get_node("P_Wave_Cavity_2")
            psi_cav_end = float(max(cav1["psi"], cav2["psi"]))
            rho_cav_end = float(cav1["rho"] + cav2["rho"])
            self._commit_pure_wave_cavity_to_register(dest, "CMOVE_WAVE", psi_sum_end, psi_cav_end, rho_cav_end)
            return

        if self.pure_wave and op in (
            "OR", "OR_WAVE", "AND", "AND_WAVE",
            "NOT_WAVE", "NAND_WAVE", "NOR_WAVE", "XOR_WAVE", "XNOR_WAVE",
            "NOT", "NAND", "NOR", "XOR", "XNOR",
        ):
            dest = inst.args[0] if len(inst.args) > 0 else "C"
            canonical_wave_op = {
                "NOT": "NOT_WAVE",
                "NAND": "NAND_WAVE",
                "NOR": "NOR_WAVE",
                "XOR": "XOR_WAVE",
                "XNOR": "XNOR_WAVE",
            }.get(op, op)
            src_a = inst.args[1] if (canonical_wave_op == "NOT_WAVE" and len(inst.args) > 1) else "A"
            self._execute_pure_wave_gate(canonical_wave_op, dest=dest, src_a=src_a, src_b="B")
            return

        if self.pure_wave and op in ("AND_MS", "OR_MS"):
            raise RuntimeError(
                f"Pure-wave execution mode forbids mixed-signal Python boolean shortcut opcode '{op}'."
            )

        # Determine target and register names safely
        if op == "LOAD":
            self.python_boolean_shortcuts_used += 1
            reg, basin_name = inst.args[0], inst.args[1]
            target_reg = f"S_R{reg}"
            bridge_id = self.group.semantic.basins[basin_name].bridge_id
            
            # Phase 1: Open gate and load (40 steps)
            for _ in range(40):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = 1.0 if reg == r else -1.0
                
                self.configure_alu_output_routing(reg)
                
                # Dynamic wormhole connection
                self.set_wormhole_connections(basin_name, is_load=True)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 15.0 if b_name == basin_name else 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                    except StopIteration:
                        pass
                
                # Drive bridge belief to transfer value
                hub_val = self.group.get_node(self.group.semantic.basins[basin_name].hub_id)["psi"]
                bridge_bias = 1.0 if hub_val >= 0 else -1.0
                self.group.get_node(bridge_id)["psi_bias"] = bridge_bias
                
                # Maintain non-target registers holding states
                self.apply_holding_biases_processing()
                self.group.get_node(target_reg)["psi_bias"] = bridge_bias
                
                self.apply_holding_biases_semantic()
                self.group.step(self.dt)
                self.record_telemetry()
                
            # Phase 2: Close gate (15 steps)
            for _ in range(15):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=True)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                    except StopIteration:
                        pass
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(self.dt)
                self.record_telemetry()

        elif op == "LOAD_INDIRECT":
            reg, array_prefix, addr_reg = inst.args[0], inst.args[1], inst.args[2]
            if (
                self.pure_wave
                and not isinstance(addr_reg, list)
                and "Basin_Page" not in self.group.semantic.basins
                and f"Basin_{array_prefix}0" in self.group.semantic.basins
                and f"Basin_{array_prefix}1" in self.group.semantic.basins
            ):
                basin0 = f"Basin_{array_prefix}0"
                basin1 = f"Basin_{array_prefix}1"
                self._reset_pure_wave_routes()
                gain = 120.0
                thresh_and = 0.20 + self.wave_threshold_offset
                thresh_cmove = -0.20 + self.wave_threshold_offset
                thresh_quench = 0.20 + self.wave_threshold_offset

                excite = self.group.get_node("P_Excite_Gate")
                cmove_gate = self.group.get_node("P_CMove_Gate")
                quench = self.group.get_node("P_Quench_Gate")
                excite["W_r"] = 0.0
                cmove_gate["W_r"] = 0.0
                quench["W_r"] = 0.0

                excite["U_r"] = gain
                excite["b_r"] = -gain * thresh_and
                cmove_gate["U_r"] = gain
                cmove_gate["b_r"] = -gain * thresh_cmove
                quench["U_r"] = -gain
                quench["b_r"] = gain * thresh_quench

                self.group.set_role_connection("pw_cavity_sink", True)
                self.group.set_role_connection("pw_cavity_to_out_b", True)
                self.group.set_role_connection("pw_cavity2_sink", True)
                self.group.set_role_connection("pw_cavity2_to_out_b", True)
                self.group.set_role_connection(f"pw_bat_drive_sum_{addr_reg}", True)
                self.group.set_role_connection(f"wh_load_{basin1}", True)
                self.group.set_role_connection("pw_sum_sense_excite", True)
                self.group.set_role_connection(f"wh_cmove_{basin0}", True)
                self.group.set_role_connection(f"pw_cmove_cond_{addr_reg}", True)

                self._advance_pure_wave_steps(12)

                self.group.set_role_connection("pw_ref_to_excite", True)
                self.group.set_role_connection("pw_excite_to_cavity", True)
                self.group.set_role_connection("pw_ref_to_cmove", True)
                self.group.set_role_connection("pw_cmove_to_quench", True)
                self.group.set_role_connection("pw_quench_to_cavity2", True)

                self._advance_pure_wave_steps(65, pump_ref=True)

                psi_sum_end = float(self.group.get_node("P_Sum")["psi"])
                cav1 = self.group.get_node("P_Wave_Cavity")
                cav2 = self.group.get_node("P_Wave_Cavity_2")
                psi_cav_end = float(max(cav1["psi"], cav2["psi"]))
                rho_cav_end = float(cav1["rho"] + cav2["rho"])
                self._commit_pure_wave_cavity_to_register(reg, "LOAD_INDIRECT_WAVE", psi_sum_end, psi_cav_end, rho_cav_end)
                return

            # Decode 1-bit or 2-bit address registers
            if isinstance(addr_reg, list):
                msb_state = self.group.get_node(f"S_R{addr_reg[0]}_B")["b_state"]
                lsb_state = self.group.get_node(f"S_R{addr_reg[1]}_B")["b_state"]
                msb = 1 if msb_state == 1 else 0
                lsb = 1 if lsb_state == 1 else 0
                index = (msb << 1) | lsb
            else:
                addr_state = self.group.get_node(f"S_R{addr_reg}_B")["b_state"]
                index = 1 if addr_state == 1 else 0
                
            # Apply Bank Paging: if Basin_Page exists and is active, offset by 4
            if "Basin_Page" in self.group.semantic.basins:
                page_hub = self.group.semantic.basins["Basin_Page"].hub_id
                page_active = self.group.get_node(page_hub)["psi"] >= 0
                if page_active:
                    index += 4
            basin_name = f"Basin_{array_prefix}{index}"
            if self.pure_wave:
                self.execute_instruction(Instruction("LOAD", [reg, basin_name]))
                return
            self.python_boolean_shortcuts_used += 1

            target_reg = f"S_R{reg}"
            bridge_id = self.group.semantic.basins[basin_name].bridge_id
            
            # Phase 1: Open gate and load (40 steps)
            for _ in range(40):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = 1.0 if reg == r else -1.0
                
                self.configure_alu_output_routing(reg)
                
                # Dynamic wormhole connection
                self.set_wormhole_connections(basin_name, is_load=True)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 15.0 if b_name == basin_name else 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                    except StopIteration:
                        pass
                
                # Drive bridge belief to transfer value
                hub_val = self.group.get_node(self.group.semantic.basins[basin_name].hub_id)["psi"]
                bridge_bias = 1.0 if hub_val >= 0 else -1.0
                self.group.get_node(bridge_id)["psi_bias"] = bridge_bias
                
                # Maintain non-target registers holding states
                self.apply_holding_biases_processing()
                self.group.get_node(target_reg)["psi_bias"] = bridge_bias
                
                self.apply_holding_biases_semantic()
                self.group.step(self.dt)
                self.record_telemetry()
                
            # Phase 2: Close gate (15 steps)
            for _ in range(15):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=True)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                    except StopIteration:
                        pass
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(self.dt)
                self.record_telemetry()

        elif op == "STORE":
            self.python_boolean_shortcuts_used += 1
            reg, basin_name = inst.args[0], inst.args[1]  # Expected 'C', 'Basin_C'
            bridge_id = self.group.semantic.basins[basin_name].bridge_id
            
            # Phase 1: Open write gate and store (30 steps)
            for _ in range(30):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = 1.0 if reg == r else -1.0
                
                self.configure_alu_output_routing(reg)
                self.set_wormhole_connections(basin_name, is_load=False)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 15.0 if b_name == basin_name else 0.0001
                    except StopIteration:
                        pass
                
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                
                reg_state = self.group.get_node(f"S_R{reg}_B")["b_state"]
                state_val = 1.0 if reg_state == 1 else -1.0
                self.group.get_node(f"S_R{reg}")["psi_bias"] = state_val
                for nid in self.group.semantic.basins[basin_name].node_ids:
                    self.group.get_node(nid)["psi_bias"] = state_val
                
                self.group.step(dt=self.dt)
                self.record_telemetry()
                
            # Phase 2: Close gate and hold (20 steps)
            for _ in range(20):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=False)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                    except StopIteration:
                        pass
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op == "STORE_INDIRECT":
            reg, array_prefix, addr_reg = inst.args[0], inst.args[1], inst.args[2]
            # Decode 1-bit or 2-bit address registers
            if isinstance(addr_reg, list):
                msb_state = self.group.get_node(f"S_R{addr_reg[0]}_B")["b_state"]
                lsb_state = self.group.get_node(f"S_R{addr_reg[1]}_B")["b_state"]
                msb = 1 if msb_state == 1 else 0
                lsb = 1 if lsb_state == 1 else 0
                index = (msb << 1) | lsb
            else:
                addr_state = self.group.get_node(f"S_R{addr_reg}_B")["b_state"]
                index = 1 if addr_state == 1 else 0
                
            # Apply Bank Paging: if Basin_Page exists and is active, offset by 4
            if "Basin_Page" in self.group.semantic.basins:
                page_hub = self.group.semantic.basins["Basin_Page"].hub_id
                page_active = self.group.get_node(page_hub)["psi"] >= 0
                if page_active:
                    index += 4
            basin_name = f"Basin_{array_prefix}{index}"
            if self.pure_wave:
                self.execute_instruction(Instruction("STORE", [reg, basin_name]))
                return
            self.python_boolean_shortcuts_used += 1
            
            bridge_id = self.group.semantic.basins[basin_name].bridge_id
            
            # Phase 1: Open write gate and store (30 steps)
            for _ in range(30):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = 1.0 if reg == r else -1.0
                
                self.configure_alu_output_routing(reg)
                self.set_wormhole_connections(basin_name, is_load=False)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 15.0 if b_name == basin_name else 0.0001
                    except StopIteration:
                        pass
                
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                
                reg_state = self.group.get_node(f"S_R{reg}_B")["b_state"]
                state_val = 1.0 if reg_state == 1 else -1.0
                self.group.get_node(f"S_R{reg}")["psi_bias"] = state_val
                for nid in self.group.semantic.basins[basin_name].node_ids:
                    self.group.get_node(nid)["psi_bias"] = state_val
                
                self.group.step(self.dt)
                self.record_telemetry()
                
            # Phase 2: Close gate and hold (20 steps)
            for _ in range(20):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=False)
                for b_name, b_cfg in self.group.semantic.basins.items():
                    try:
                        self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                    except StopIteration:
                        pass
                    try:
                        self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                    except StopIteration:
                        pass
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op in (
            "OR", "AND", "OR_WAVE", "AND_WAVE",
            "OR_MS", "AND_MS", "NOT", "NAND", "NOR", "XOR", "XNOR",
            "NOT_WAVE", "NAND_WAVE", "NOR_WAVE", "XOR_WAVE", "XNOR_WAVE",
        ):
            # Determine destination register (defaults to 'C')
            dest = inst.args[0] if len(inst.args) > 0 else 'C'
            dest_reg = f"S_R{dest}"
            if op in ("OR_WAVE", "AND_WAVE"):
                op = "OR" if op == "OR_WAVE" else "AND"
            elif op in ("NOT_WAVE", "NAND_WAVE", "NOR_WAVE", "XOR_WAVE", "XNOR_WAVE"):
                op = op.replace("_WAVE", "")
            
            # Determine if we are doing physical threshold logic or mixed-signal logic
            is_mixed_signal = op in ("OR_MS", "AND_MS", "NOT", "NAND", "NOR", "XOR", "XNOR")
            
            if is_mixed_signal:
                self.python_boolean_shortcuts_used += 1
                # Read register states from memristive batteries A and B
                latched_A = self.group.get_node("S_RA_B")["b_state"] == 1
                latched_B = self.group.get_node("S_RB_B")["b_state"] == 1
                
                if op == "AND_MS":
                    should_trigger = latched_A and latched_B
                elif op == "OR_MS":
                    should_trigger = latched_A or latched_B
                elif op == "NOT":
                    src = inst.args[1] if len(inst.args) > 1 else 'A'
                    val = latched_A if src == 'A' else latched_B
                    should_trigger = not val
                elif op == "NAND":
                    should_trigger = not (latched_A and latched_B)
                elif op == "NOR":
                    should_trigger = not (latched_A or latched_B)
                elif op == "XOR":
                    should_trigger = latched_A != latched_B
                elif op == "XNOR":
                    should_trigger = latched_A == latched_B
                
                # Mixed-signal compute: drive accumulator dest directly based on should_trigger
                duration = 30
                for _ in range(duration):
                    for r in ['A', 'B', 'C', 'D']:
                        g_id = f"GATE_{r}"
                        if g_id in self.group.engine.physics.node_by_id:
                            self.group.get_node(g_id)["psi_bias"] = 1.0 if r == dest else -1.0
                    self.configure_alu_output_routing(dest)
                    self.set_wormhole_connections(None, is_load=True)
                    for b_name, b_cfg in self.group.semantic.basins.items():
                        try:
                            self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                        except StopIteration:
                            pass
                        try:
                            self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                        except StopIteration:
                            pass
                    
                    self.apply_holding_biases_processing()
                    self.apply_holding_biases_semantic()
                    
                    state_dest = 1.0 if should_trigger else -1.0
                    self.group.get_node(dest_reg)["psi_bias"] = state_dest
                    self.group.get_node(dest_reg)["psi"] = state_dest
                    
                    self.group.step(dt=self.dt)
                    self.record_telemetry()
            else:
                # Purely physical threshold logic for OR / AND
                bias_val = 0.18 if op == "OR" else 0.19
                duration = 30 if op == "OR" else 29
                
                # Phase 1: Open ALU Gates and Compute
                for _ in range(duration):
                    for r in ['A', 'B', 'C', 'D']:
                        g_id = f"GATE_{r}"
                        if g_id in self.group.engine.physics.node_by_id:
                            self.group.get_node(g_id)["psi_bias"] = 1.0 if r in ('A', 'B', dest) else -1.0
                    self.configure_alu_output_routing(dest)
                    self.set_wormhole_connections(None, is_load=True)
                    for b_name, b_cfg in self.group.semantic.basins.items():
                        try:
                            self.group.get_edge(b_cfg.bridge_id, "P_Sum")["w0"] = 0.0001
                        except StopIteration:
                            pass
                        try:
                            self.group.get_edge("P_Sum", b_cfg.bridge_id)["w0"] = 0.0001
                        except StopIteration:
                            pass
                    
                    self.apply_holding_biases_processing()
                    self.apply_holding_biases_semantic()
                    self.group.get_node(dest_reg)["psi_bias"] = bias_val
                    
                    self.group.step(dt=self.dt)
                    self.record_telemetry()
            
            # Common Phase 2: Close Gates and Settle (25 steps)
            for _ in range(25):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(dest)
                self.set_wormhole_connections(None, is_load=True)
                self.apply_holding_biases_processing()
                if not is_mixed_signal:
                    self.group.get_node(dest_reg)["psi_bias"] = bias_val
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op == "COPY":
            self.python_boolean_shortcuts_used += 1
            src, dest = inst.args[0], inst.args[1]  # Expect 'C', 'A'
            src_reg = f"S_R{src}"
            src_reg_b = f"S_R{src}_B"
            dest_reg = f"S_R{dest}"
            
            # Phase 1: Route through Summing Junction (30 steps)
            for _ in range(30):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = 1.0 if (r == src or r == dest) else -1.0
                self.configure_alu_output_routing(dest if dest in ('C', 'D') else (src if src in ('C', 'D') else None))
                self.set_wormhole_connections(None, is_load=True)
                
                c_state = self.group.get_node(src_reg_b)["b_state"]
                self.group.get_node(src_reg)["psi_bias"] = 1.0 if c_state == 1 else -1.0
                # Destination bias dynamic assist
                self.group.get_node(dest_reg)["psi_bias"] = 0.5 if c_state == 1 else -1.0
                
                # Keep other registers holding
                for r in ['A', 'B', 'C', 'D']:
                    if r != src and r != dest:
                        other_reg = f"S_R{r}"
                        if other_reg + "_B" in self.group.engine.physics.node_by_id:
                            other_state = self.group.get_node(other_reg + "_B")["b_state"]
                            self.group.get_node(other_reg)["psi_bias"] = 1.0 if other_state == 1 else -1.0
                
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()
                
            # Phase 2: Close Gates and Hold (15 steps)
            for _ in range(15):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=True)
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op == "CMOVE":
            self.python_boolean_shortcuts_used += 1
            dest, src, cond = inst.args[0], inst.args[1], inst.args[2]
            src_reg = f"S_R{src}"
            src_reg_b = f"S_R{src}_B"
            dest_reg = f"S_R{dest}"
            cond_reg_b = f"S_R{cond}_B"
            
            # Read condition battery state
            cond_active = (self.group.get_node(cond_reg_b)["b_state"] == 1)
            
            # Phase 1: Route through Summing Junction (30 steps)
            for _ in range(30):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        if cond_active and (r == src or r == dest):
                            self.group.get_node(g_id)["psi_bias"] = 1.0
                        else:
                            self.group.get_node(g_id)["psi_bias"] = -1.0
                            
                self.configure_alu_output_routing(dest if dest in ('C', 'D') else (src if src in ('C', 'D') else None))
                self.set_wormhole_connections(None, is_load=True)
                
                src_state = self.group.get_node(src_reg_b)["b_state"]
                if cond_active:
                    self.group.get_node(src_reg)["psi_bias"] = 1.0 if src_state == 1 else -1.0
                    self.group.get_node(dest_reg)["psi_bias"] = 0.5 if src_state == 1 else -1.0
                else:
                    self.group.get_node(src_reg)["psi_bias"] = 1.0 if src_state == 1 else -1.0
                    dest_state = self.group.get_node(dest_reg + "_B")["b_state"]
                    self.group.get_node(dest_reg)["psi_bias"] = 1.0 if dest_state == 1 else -1.0
                
                # Keep other registers holding
                for r in ['A', 'B', 'C', 'D']:
                    if r != src and r != dest:
                        other_reg = f"S_R{r}"
                        if other_reg + "_B" in self.group.engine.physics.node_by_id:
                            other_state = self.group.get_node(other_reg + "_B")["b_state"]
                            self.group.get_node(other_reg)["psi_bias"] = 1.0 if other_state == 1 else -1.0
                
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()
                
            # Phase 2: Close Gates and Hold (15 steps)
            for _ in range(15):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=True)
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op == "CLEAR":
            reg = inst.args[0]  # Expect 'C'
            reg_host = f"S_R{reg}"
            reg_bat = f"S_R{reg}_B"
            if self.pure_wave:
                self._reset_pure_wave_routes()
                self.group.set_role_connection(f"pw_cavity_to_gate_{reg}", True)
                self.group.set_role_connection(f"pw_bus_in_{reg}", True)
                self.group.set_role_connection(f"pw_reg_write_{reg}", True)
                self.group.set_role_connection(f"pw_sum_write_{reg}", True)
                self._advance_pure_wave_steps(30)
                self._reset_pure_wave_routes()
                self.pure_wave_quench_ops += 1
                if not self.record_substep_telemetry:
                    self.record_telemetry()
                return

            # Phase 1: Collapse Battery (30 steps)
            for _ in range(30):
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.configure_alu_output_routing(None)
                self.set_wormhole_connections(None, is_load=True)

                # Maintain other registers
                self.apply_holding_biases_processing()

                # Actively discharge charge and force bias negative
                self.group.get_node(reg_bat)["b_charge"] = 0.0
                self.group.get_node(reg_bat)["psi_bias"] = -1.0
                self.group.get_node(reg_bat)["psi"] = -1.0
                self.group.get_node(reg_bat)["b_state"] = -1
                self.group.get_node(reg_host)["rho"] = 5.0
                self.group.get_node(reg_bat)["rho"] = 0.0
                self.group.get_node(reg_host)["psi_bias"] = -1.0
                self.group.get_node(reg_host)["psi"] = -1.0
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

        elif op == "RESET_CORE":
            if self.pure_wave:
                for r in ("C", "D"):
                    if f"S_R{r}" in self.group.engine.physics.node_by_id:
                        self.execute_instruction(Instruction("CLEAR", [r]))
                return
            # Ground summing junction and clear fluxes (20 steps)
            for _ in range(20):
                # Programmatic ground on tick 1
                self.set_wormhole_connections(None, is_load=True)
                self.configure_alu_output_routing(None, default_w0=5.0)
                for node_id in ["GATE_A", "GATE_B", "GATE_C", "GATE_D", "P_Sum", "S_RC", "S_RC_B", "S_RD", "S_RD_B"]:
                    if node_id not in self.group.engine.physics.node_by_id:
                        continue
                    node = self.group.get_node(node_id)
                    node["psi"] = -1.0 if node_id != "P_Sum" else 0.0
                    if node_id in ("S_RC", "S_RD"):
                        node["rho"] = 5.0
                    elif node_id in ("S_RC_B", "S_RD_B"):
                        node["rho"] = 0.0
                        node["b_state"] = -1
                        node["b_charge"] = 0.0
                        node["psi_bias"] = -1.0
                    else:
                        node["rho"] = 0.0
                for edge in self.group.engine.physics.edges:
                    edge["flux"] = 0.0
                
                # DRAM mass regulation normalization
                self.normalize_register_masses()
                
                for r in ['A', 'B', 'C', 'D']:
                    g_id = f"GATE_{r}"
                    if g_id in self.group.engine.physics.node_by_id:
                        self.group.get_node(g_id)["psi_bias"] = -1.0
                self.apply_holding_biases_processing()
                self.apply_holding_biases_semantic()
                self.group.step(dt=self.dt)
                self.record_telemetry()

    def record_telemetry(self):
        bat_a = self.group.get_node("S_RA_B")
        bat_b = self.group.get_node("S_RB_B")
        bat_c = self.group.get_node("S_RC_B")
        bat_d = self.group.get_node("S_RD_B") if "S_RD_B" in self.group.engine.physics.node_by_id else None
        
        rho_basin_a = sum(self.group.get_node(f"S{i}")["rho"] for i in range(10) if f"S{i}" in self.group.engine.physics.node_by_id)
        rho_basin_b = sum(self.group.get_node(f"S{i}")["rho"] for i in range(10, 20) if f"S{i}" in self.group.engine.physics.node_by_id)
        rho_basin_c = sum(self.group.get_node(f"S{i}")["rho"] for i in range(20, 30) if f"S{i}" in self.group.engine.physics.node_by_id)
        rho_basin_d = sum(self.group.get_node(f"S{i}")["rho"] for i in range(30, 40) if f"S{i}" in self.group.engine.physics.node_by_id)
        rho_basin_e = sum(self.group.get_node(f"S{i}")["rho"] for i in range(40, 50) if f"S{i}" in self.group.engine.physics.node_by_id)
        
        rho_reg_a = self.group.get_node("S_RA")["rho"] + bat_a["rho"]
        rho_reg_b = self.group.get_node("S_RB")["rho"] + bat_b["rho"]
        rho_reg_c = self.group.get_node("S_RC")["rho"] + bat_c["rho"]
        rho_reg_d = (self.group.get_node("S_RD")["rho"] + bat_d["rho"]) if bat_d else 0.0
        
        # Determine basin states safely across arbitrary basin counts (including scratch/ALU basins > 5)
        basin_states: dict[str, int] = {}
        basin_rhos: dict[str, float] = {}
        for b_name, b_cfg in self.group.semantic.basins.items():
            if b_cfg.battery_id and b_cfg.battery_id in self.group.engine.physics.node_by_id:
                b_state_val = 1 if self.group.get_node(b_cfg.battery_id)["b_state"] == 1 else 0
                b_rho_val = sum(self.group.get_node(nid)["rho"] for nid in b_cfg.node_ids) + self.group.get_node(b_cfg.battery_id)["rho"]
            else:
                b_state_val = 1 if (b_cfg.hub_id in self.group.engine.physics.node_by_id and self.group.get_node(b_cfg.hub_id)["psi"] >= 0) else 0
                b_rho_val = sum(self.group.get_node(nid)["rho"] for nid in b_cfg.node_ids if nid in self.group.engine.physics.node_by_id)
            basin_states[b_name] = b_state_val
            basin_rhos[b_name] = b_rho_val

        basin_list = list(self.group.semantic.basins.keys())
        def _legacy_b_state(idx: int, fallback_hub: str) -> int:
            if idx < len(basin_list):
                return basin_states[basin_list[idx]]
            return 1 if (fallback_hub in self.group.engine.physics.node_by_id and self.group.get_node(fallback_hub)["psi"] >= 0) else 0

        b_a_state = _legacy_b_state(0, "S0")
        b_b_state = _legacy_b_state(1, "S10")
        b_c_state = _legacy_b_state(2, "S20")
        b_d_state = _legacy_b_state(3, "S30")
        b_e_state = _legacy_b_state(4, "S40")
        
        self.history.append({
            "step": len(self.history),
            "basin_a_state": b_a_state,
            "basin_b_state": b_b_state,
            "basin_c_state": b_c_state,
            "basin_d_state": b_d_state,
            "basin_e_state": b_e_state,
            "basin_states": basin_states,
            "basin_rhos": basin_rhos,
            "reg_a_state": float(bat_a["b_state"]),
            "reg_b_state": float(bat_b["b_state"]),
            "reg_c_state": float(bat_c["b_state"]),
            "reg_d_state": float(bat_d["b_state"]) if bat_d else 0.0,
            "rho_basin_a": rho_basin_a,
            "rho_basin_b": rho_basin_b,
            "rho_basin_c": rho_basin_c,
            "rho_basin_d": rho_basin_d,
            "rho_basin_e": rho_basin_e,
            "rho_reg_a": rho_reg_a,
            "rho_reg_b": rho_reg_b,
            "rho_reg_c": rho_reg_c,
            "rho_reg_d": rho_reg_d,
            "psi_sum": self.group.get_node("P_Sum")["psi"]
        })

    def run_program(self, program: list[Instruction]) -> list[dict]:
        self.history = []
        for inst in program:
            self.execute_instruction(inst)
        return self.history


class BatchPureWaveVerifier:
    """
    Vectorized Lockstep Pure-Wave Physical RK4 Verifier (`BatchSOLPhysics`).

    Integrates all B truth-table rows simultaneously in lockstep through the exact
    `SOLPhysics.run_rk4_steps` ODEs (`dt = 0.05`, 4 RK4 stages per step, stored
    conductance ordering in `_update_batteries_indexed`, multiset battery avalanche
    neighbor multiplicity, per-row `apply_semantic_mass_decay` and
    `jeans_collapse_and_accrete` on `(B, N)` tensors, and BLAS incidence-matrix
    `M_inc` multiplication).

    When `deduplicate_components=True` (default), connected components of the active
    physical graph `(nodes, active_edges)` deduplicate identical component state
    trajectories across the B rows before integrating `steps` RK4 steps and scatter
    back to all B rows at the end of each step block with `0.0` numerical loss.
    """

    def __init__(
        self,
        basins_def: list[tuple[str, int]],
        input_rows: list[dict[str, int]],
        *,
        damping: float = 0.01,
        flip_threshold: float | None = None,
        collapse_factor: float | None = None,
        deduplicate_components: bool = True,
        use_blas_incidence_gemm: bool = True,
    ):
        self.B = len(input_rows)
        self.basins_def = list(basins_def)
        self.deduplicate_components = bool(deduplicate_components)
        self.use_blas_incidence_gemm = bool(use_blas_incidence_gemm)

        s_nodes: list[dict] = []
        s_edges: list[dict] = []
        s_basins: list[BasinConfig] = []
        for b_name, start_idx in self.basins_def:
            bn, be, bcfg = UniversalManifold.build_semantic_basin(
                b_name, num_nodes=10, start_idx=start_idx, pure_wave=True
            )
            s_nodes.extend(bn)
            s_edges.extend(be)
            s_basins.append(bcfg)

        semantic = SemanticManifold(nodes=s_nodes, edges=s_edges, basins=s_basins)
        processing = ProcessingManifold(pure_wave=True)
        self.group = ManifoldGroup(
            semantic,
            processing,
            c_press=1.0,
            damping=damping,
            pure_wave=True,
            flip_threshold=flip_threshold,
            collapse_factor=collapse_factor,
        )
        self.phys = self.group.engine.physics

        for b_name, _ in self.basins_def:
            self.group.prime_basin(b_name, active=False)
        for reg in ("A", "B", "C", "D"):
            self.group.prime_register(reg, active=False)

        self.nodes = self.phys.nodes
        self.edges = self.phys.edges
        self.n_nodes = len(self.nodes)
        self.n_edges = len(self.edges)
        self.idx_by_id = self.phys.node_index_by_id
        self.id_to_eidx = {id(e): idx for idx, e in enumerate(self.edges)}

        B = self.B
        self.rho = np.broadcast_to(
            np.array([float(n["rho"]) for n in self.nodes], dtype=np.float64),
            (B, self.n_nodes),
        ).copy()
        self.psi = np.broadcast_to(
            np.array([float(n["psi"]) for n in self.nodes], dtype=np.float64),
            (B, self.n_nodes),
        ).copy()
        self.psi_bias = np.broadcast_to(
            np.array([float(n["psi_bias"]) for n in self.nodes], dtype=np.float64),
            (B, self.n_nodes),
        ).copy()
        self.b_state = np.broadcast_to(
            np.array([int(n.get("b_state", 1)) for n in self.nodes], dtype=np.int64),
            (B, self.n_nodes),
        ).copy()
        self.b_charge = np.broadcast_to(
            np.array([float(n.get("b_charge", 0.0)) for n in self.nodes], dtype=np.float64),
            (B, self.n_nodes),
        ).copy()
        self.m_arr = np.broadcast_to(
            np.array([float(n.get("semanticMass", 1.0)) for n in self.nodes], dtype=np.float64),
            (B, self.n_nodes),
        ).copy()
        self.is_constellation = np.broadcast_to(
            np.array([bool(n.get("isConstellation")) for n in self.nodes], dtype=bool),
            (B, self.n_nodes),
        ).copy()
        self.is_stellar = np.broadcast_to(
            np.array([bool(n.get("isStellar")) for n in self.nodes], dtype=bool),
            (B, self.n_nodes),
        ).copy()
        self.is_bat = np.array([bool(n.get("isBattery")) for n in self.nodes], dtype=bool)
        self.bat_indices = [i for i, is_b in enumerate(self.is_bat) if is_b]

        self.flux = np.broadcast_to(
            np.array([float(e.get("flux", 0.0)) for e in self.edges], dtype=np.float64),
            (B, self.n_edges),
        ).copy()
        self.bMag = np.broadcast_to(
            np.array([float(e.get("bMag", 0.0)) for e in self.edges], dtype=np.float64),
            (B, self.n_edges),
        ).copy()
        self.cond = np.broadcast_to(
            np.array([float(e.get("conductance", 1.0)) for e in self.edges], dtype=np.float64),
            (B, self.n_edges),
        ).copy()
        self.w0 = np.array([float(e["w0"]) for e in self.edges], dtype=np.float64)
        self.e_src_all = np.array([self.idx_by_id[e["from"]] for e in self.edges], dtype=np.int64)
        self.e_dst_all = np.array([self.idx_by_id[e["to"]] for e in self.edges], dtype=np.int64)
        self.e_src_bat_all = self.is_bat[self.e_src_all]
        self.e_dst_bat_all = self.is_bat[self.e_dst_all]

        # Prebuild full signed incidence matrix M_inc_all of shape (E, N)
        self.M_inc_all = np.zeros((self.n_edges, self.n_nodes), dtype=np.float64)
        np.add.at(self.M_inc_all, (np.arange(self.n_edges), self.e_src_all), 1.0)
        np.add.at(self.M_inc_all, (np.arange(self.n_edges), self.e_dst_all), -1.0)

        for b_idx, row_dict in enumerate(input_rows):
            for b_name, val in row_dict.items():
                if val == 1:
                    b_cfg = self.group.semantic.basins[b_name]
                    for nid in b_cfg.node_ids:
                        ni = self.idx_by_id[nid]
                        self.psi[b_idx, ni] = 1.0
                        self.psi_bias[b_idx, ni] = 0.0
                        self.rho[b_idx, ni] = 60.0 if nid == b_cfg.hub_id else 5.0
                    if b_cfg.battery_id:
                        bi = self.idx_by_id[b_cfg.battery_id]
                        self.b_state[b_idx, bi] = 1
                        self.b_charge[b_idx, bi] = 1.0
                        self.psi[b_idx, bi] = 1.0
                        self.psi_bias[b_idx, bi] = 1.0
                        self.rho[b_idx, bi] = 20.0

        self.seq = MicroInstructionSequencer(
            self.group, pure_wave=True, record_substep_telemetry=False
        )
        self._orig_reset = self.seq._reset_pure_wave_routes
        self.seq._reset_pure_wave_routes = self._batch_reset_pure_wave_routes
        self.group.run_steps = self._batch_run_steps
        self._orig_disconnect = self.group.disconnect_all_dynamic_roles
        self.group.disconnect_all_dynamic_roles = self._batch_disconnect_all_dynamic_roles
        self._orig_set_role = self.group.set_role_connection
        self.group.set_role_connection = self._batch_set_role_connection

        self.min_charge_margin_vs_tau = float("inf")
        self.max_off_charge_at_commit = 0.0
        self.min_on_charge_at_commit = 1.0
        self.gate_commits_evaluated = 0
        self.rk4_steps_executed = 0

        reset_nids = {"P_Sum"}
        if self.seq._pw_ref_node is not None:
            reset_nids.add("P_Wave_Ref")
        if self.seq._pw_sink_node is not None:
            reset_nids.add("P_Wave_Sink")
        for cav in self.seq._pw_cav_nodes:
            reset_nids.add(cav["id"])
        if self.seq._pw_out_b_node is not None:
            reset_nids.add("P_Wave_Out_B")
        for gn in self.seq._pw_gate_nodes:
            reset_nids.add(gn["id"])
        self._pw_reset_node_indices: set[int] = {
            self.idx_by_id[nid] for nid in reset_nids if nid in self.idx_by_id
        }
        for r in ("A", "B", "C", "D"):
            if f"GATE_{r}" in self.idx_by_id:
                self.psi_bias[:, self.idx_by_id[f"GATE_{r}"]] = 0.0

        self._comp_partition_cache: dict[
            tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]],
            tuple[np.ndarray, np.ndarray],
        ] = {}
        self._dirty_nodes: set[int] = set(range(self.n_nodes))
        self._basin_node_indices: dict[str, tuple[int, ...]] = {}
        self._basin_edge_indices: dict[str, list[int]] = {}
        self._basin_bat_idx: dict[str, int] = {}
        self._basin_pending_steps: dict[str, int] = {}
        self._basin_untouched_since_t0: dict[str, bool] = {}
        self._basin_t0_active_mask: dict[str, np.ndarray] = {}
        self._store_role_to_basin: dict[str, str] = {}
        self._sub_edges_by_nodes: dict[tuple[int, ...], tuple[list[int], list[int]]] = {}
        self._role_edge_indices: dict[str, np.ndarray] = {}
        for role, r_edges in self.group._edges_by_role.items():
            self._role_edge_indices[role] = np.array(
                [self.id_to_eidx[id(e)] for e in r_edges], dtype=np.int64
            )
        self._bat_nonbg_dyn_eidxs = np.array(
            [
                idx
                for idx, e in enumerate(self.edges)
                if (self.e_src_bat_all[idx] or self.e_dst_bat_all[idx])
                and not bool(e.get("_orig_background", e.get("background", False)))
                and str(e.get("role", "")).startswith(("wh_", "pw_"))
            ],
            dtype=np.int64,
        )
        for b_name, b_cfg in self.group.semantic.basins.items():
            b_nids = list(b_cfg.node_ids)
            if b_cfg.battery_id and b_cfg.battery_id in self.idx_by_id:
                b_nids.append(b_cfg.battery_id)
                self._basin_bat_idx[b_name] = self.idx_by_id[b_cfg.battery_id]
            b_ntup = tuple(
                sorted(self.idx_by_id[nid] for nid in b_nids if nid in self.idx_by_id)
            )
            self._basin_node_indices[b_name] = b_ntup
            b_nset = set(b_ntup)
            b_eidxs = [
                e_idx
                for e_idx in range(self.n_edges)
                if int(self.e_src_all[e_idx]) in b_nset
                and int(self.e_dst_all[e_idx]) in b_nset
            ]
            self._basin_edge_indices[b_name] = b_eidxs
            self._sub_edges_by_nodes[b_ntup] = (b_eidxs, b_eidxs)
            self._basin_pending_steps[b_name] = 0
            self._basin_untouched_since_t0[b_name] = True
            self._basin_t0_active_mask[b_name] = np.array(
                [1 if row_dict.get(b_name, 0) == 1 else 0 for row_dict in input_rows],
                dtype=np.int64,
            )
            self._store_role_to_basin[f"wh_store_{b_name}"] = b_name

        self._canon_t0_verifier: BatchPureWaveVerifier | None = None
        self._canon_t0_steps: int = 0
        self._canon_t0_snapshots: dict[
            int,
            tuple[
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
                np.ndarray,
            ],
        ] = {}

        def exact_batch_commit(
            dest: str,
            op_label: str,
            psi_sum_end: float,
            psi_cav_end: float,
            rho_cav_end: float,
        ) -> None:
            self.group.disconnect_all_dynamic_roles()
            self.group.set_role_connection(f"pw_cavity_to_gate_{dest}", True)
            self.group.set_role_connection(f"pw_reg_write_{dest}", True)
            self.seq._advance_pure_wave_steps(45)
            dest_bat_i = self.idx_by_id[f"S_R{dest}_B"]
            tau = float(self.phys.battery_cfg.get("flipThreshold", 0.65))
            charges = self.b_charge[:, dest_bat_i]
            states = self.b_state[:, dest_bat_i]
            margins = np.round(np.abs(charges - tau), 5)
            min_m = float(np.min(margins))
            self.min_charge_margin_vs_tau = min(self.min_charge_margin_vs_tau, min_m)
            off_mask = states != 1
            if np.any(off_mask):
                max_off = float(np.max(charges[off_mask]))
                self.max_off_charge_at_commit = max(self.max_off_charge_at_commit, max_off)
            on_mask = states == 1
            if np.any(on_mask):
                min_on = float(np.min(charges[on_mask]))
                self.min_on_charge_at_commit = min(self.min_on_charge_at_commit, min_on)
            self.gate_commits_evaluated += 1
            self.seq._settle_pure_wave(10)

        self.seq._commit_pure_wave_cavity_to_register = exact_batch_commit

    @property
    def python_boolean_shortcuts_used(self) -> int:
        return int(self.seq.python_boolean_shortcuts_used)

    def _get_canon_t0_snapshot(
        self, target_steps: int
    ) -> tuple[
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
        np.ndarray,
    ]:
        if target_steps in self._canon_t0_snapshots:
            return self._canon_t0_snapshots[target_steps]
        if self._canon_t0_verifier is None or target_steps < self._canon_t0_steps:
            self._canon_t0_verifier = BatchPureWaveVerifier(
                [("Basin_Canon", 0)],
                [{"Basin_Canon": 0}, {"Basin_Canon": 1}],
                damping=self.group.damping,
                flip_threshold=self.group.flip_threshold,
                collapse_factor=self.group.collapse_factor,
                deduplicate_components=False,
            )
            self._canon_t0_steps = 0
        cv = self._canon_t0_verifier
        c_n = cv._basin_node_indices["Basin_Canon"]
        c_e = cv._basin_edge_indices["Basin_Canon"]
        delta = target_steps - self._canon_t0_steps
        if delta > 0:
            cv._batch_run_steps(
                delta,
                dt=self.seq.dt,
                _node_subset=c_n,
                _count_global_steps=False,
            )
            self._canon_t0_steps = target_steps
        snap = (
            cv.rho[:, c_n].copy(),
            cv.psi[:, c_n].copy(),
            cv.psi_bias[:, c_n].copy(),
            cv.b_state[:, c_n].copy(),
            cv.b_charge[:, c_n].copy(),
            cv.m_arr[:, c_n].copy(),
            cv.is_constellation[:, c_n].copy(),
            cv.is_stellar[:, c_n].copy(),
            cv.flux[:, c_e].copy(),
            cv.bMag[:, c_e].copy(),
            cv.cond[:, c_e].copy(),
        )
        self._canon_t0_snapshots[target_steps] = snap
        return snap

    def _flush_basin_pending_steps(self, b_name: str) -> None:
        pending = self._basin_pending_steps.get(b_name, 0)
        if pending > 0:
            self._basin_pending_steps[b_name] = 0
            b_ntup = self._basin_node_indices[b_name]
            if self._basin_untouched_since_t0.get(b_name, False):
                self._basin_untouched_since_t0[b_name] = False
                snap = self._get_canon_t0_snapshot(pending)
                mask = self._basin_t0_active_mask[b_name]
                b_eidxs = self._basin_edge_indices[b_name]
                self.rho[:, b_ntup] = snap[0][mask]
                self.psi[:, b_ntup] = snap[1][mask]
                self.psi_bias[:, b_ntup] = snap[2][mask]
                self.b_state[:, b_ntup] = snap[3][mask]
                self.b_charge[:, b_ntup] = snap[4][mask]
                self.m_arr[:, b_ntup] = snap[5][mask]
                self.is_constellation[:, b_ntup] = snap[6][mask]
                self.is_stellar[:, b_ntup] = snap[7][mask]
                self.flux[:, b_eidxs] = snap[8][mask]
                self.bMag[:, b_eidxs] = snap[9][mask]
                self.cond[:, b_eidxs] = snap[10][mask]
                self._dirty_nodes.update(b_ntup)
            else:
                self._batch_run_steps(
                    pending,
                    dt=self.seq.dt,
                    _node_subset=b_ntup,
                    _count_global_steps=False,
                )
        else:
            self._basin_untouched_since_t0[b_name] = False

    def _batch_set_role_connection(self, role: str, connected: bool) -> None:
        if connected and self.deduplicate_components and role.startswith(
            ("wh_load_", "wh_store_", "wh_cmove_")
        ):
            b_name = role.split("_", 2)[2]
            if b_name in self._basin_node_indices:
                self._flush_basin_pending_steps(b_name)
        self._orig_set_role(role, connected)
        if role.startswith(("wh_", "pw_")):
            r_eidxs = self._role_edge_indices.get(role)
            if r_eidxs is not None and len(r_eidxs) > 0:
                if not connected:
                    self.flux[:, r_eidxs] = 0.0
                for ei in r_eidxs:
                    self._dirty_nodes.add(int(self.e_src_all[ei]))
                    self._dirty_nodes.add(int(self.e_dst_all[ei]))

    def _batch_disconnect_all_dynamic_roles(self) -> None:
        active_roles = tuple(self.group._active_dynamic_roles)
        self._orig_disconnect()
        for role in active_roles:
            r_eidxs = self._role_edge_indices.get(role)
            if r_eidxs is not None and len(r_eidxs) > 0:
                self.flux[:, r_eidxs] = 0.0
                for ei in r_eidxs:
                    self._dirty_nodes.add(int(self.e_src_all[ei]))
                    self._dirty_nodes.add(int(self.e_dst_all[ei]))

    def _batch_reset_pure_wave_routes(self) -> None:
        self._orig_reset()
        for r in ("A", "B", "C", "D"):
            if f"S_R{r}" in self.idx_by_id:
                self.psi_bias[:, self.idx_by_id[f"S_R{r}"]] = 0.0
            if f"GATE_{r}" in self.idx_by_id:
                self.psi_bias[:, self.idx_by_id[f"GATE_{r}"]] = 0.0
        p_sum_i = self.idx_by_id["P_Sum"]
        self.psi_bias[:, p_sum_i] = 0.0
        self.psi[:, p_sum_i] = 0.0
        self.rho[:, p_sum_i] = 0.0
        if self.seq._pw_ref_node is not None:
            ref_i = self.idx_by_id["P_Wave_Ref"]
            self.rho[:, ref_i] = 500.0
            self.psi[:, ref_i] = 0.0
            self.psi_bias[:, ref_i] = 0.0
        if self.seq._pw_sink_node is not None:
            sink_i = self.idx_by_id["P_Wave_Sink"]
            self.b_state[:, sink_i] = -1
            self.b_charge[:, sink_i] = 0.0
            self.rho[:, sink_i] = 5.0
            self.psi[:, sink_i] = -1.0
            self.psi_bias[:, sink_i] = -1.0
        for cav in self.seq._pw_cav_nodes:
            ci = self.idx_by_id[cav["id"]]
            self.rho[:, ci] = 0.0
            self.psi[:, ci] = -0.4
            self.psi_bias[:, ci] = 1.85
        if self.seq._pw_out_b_node is not None:
            obi = self.idx_by_id["P_Wave_Out_B"]
            self.b_state[:, obi] = -1
            self.b_charge[:, obi] = 0.0
            self.psi[:, obi] = -1.0
            self.psi_bias[:, obi] = -1.0
            self.rho[:, obi] = 0.0
        for gn in self.seq._pw_gate_nodes:
            gi = self.idx_by_id[gn["id"]]
            self.rho[:, gi] = 0.0
            self.psi[:, gi] = 0.0
            self.psi_bias[:, gi] = 0.0
        self._dirty_nodes.update(self._pw_reset_node_indices)

    def _update_conductance_subset(self, e_indices: np.ndarray) -> None:
        if len(e_indices) == 0:
            return
        phys = self.phys
        c_base = phys.conductance_base
        c_gamma = phys.conductance_gamma
        c_min = phys.conductance_min
        c_max = phys.conductance_max
        tight_max = max(c_min, min(c_max, 0.6))
        b_gamma = phys.mhd_cfg.get("bGamma", 0.35) if phys.mhd_cfg else 0.0
        res_boost = phys.battery_cfg.get("resonanceBoost", 1.8)
        damp_clamp = phys.battery_cfg.get("dampingClamp", 0.35)

        ia = self.e_src_all[e_indices]
        ib = self.e_dst_all[e_indices]
        avg_psi = 0.5 * (self.psi[:, ia] + self.psi[:, ib])
        w = (
            (self.w0[e_indices] * c_base)
            * np.exp(c_gamma * avg_psi)
            * (1.0 + b_gamma * self.bMag[:, e_indices])
        )

        src_bat = self.e_src_bat_all[e_indices]
        dst_bat = self.e_dst_bat_all[e_indices]
        has_b = src_bat | dst_bat
        bat_node_idx = np.where(src_bat, ia, ib)
        s = self.b_state[:, bat_node_idx]

        w_boost = np.minimum(np.maximum(w * res_boost, c_min), c_max)
        w_clamp = np.minimum(np.maximum(w * damp_clamp, c_min), tight_max)
        w_norm = np.minimum(np.maximum(w, c_min), c_max)

        cond_new = np.where(has_b, np.where(s == 1, w_boost, w_clamp), w_norm)
        self.cond[:, e_indices] = cond_new

    def _batch_run_steps(
        self,
        steps: int,
        dt: float = 0.05,
        damping: float | None = None,
        *,
        pre_step_node: dict | None = None,
        pre_step_rho: float = 500.0,
        pre_step_psi: float = 0.0,
        _node_subset: tuple[int, ...] | None = None,
        _count_global_steps: bool = True,
    ) -> None:
        if steps <= 0:
            return
        if _count_global_steps:
            self.rk4_steps_executed += int(steps)
        phys = self.phys
        use_damping = self.group.damping if damping is None else float(damping)
        damp_base = -use_damping * 0.1
        star_damp = phys.jeans_cfg.get("starDampingFactor", 0.18) if phys.jeans_cfg else 1.0
        j_crit = phys.jeans_cfg.get("Jcrit", 18.0) if phys.jeans_cfg else 1e18
        sem_decay_rate = phys.semantic_cfg.get("decayRate", 0.05) if phys.semantic_cfg else 0.0
        sem_min_mass = phys.semantic_cfg.get("minMass", 0.25) if phys.semantic_cfg else 0.25
        sem_factor = math.exp(-sem_decay_rate * max(0.0, dt))

        c_press = self.group.engine.c_press
        c_base = phys.conductance_base
        c_gamma = phys.conductance_gamma
        half_c_gamma = 0.5 * c_gamma
        c_min = phys.conductance_min
        c_max = phys.conductance_max
        tight_max = max(c_min, min(c_max, 0.6))
        b_gamma = phys.mhd_cfg.get("bGamma", 0.35) if phys.mhd_cfg else 0.0
        res_boost = phys.battery_cfg.get("resonanceBoost", 1.8)
        damp_clamp = phys.battery_cfg.get("dampingClamp", 0.35)
        d_res_out = phys.battery_cfg["diodeResonanceOut"]
        d_res_in = phys.battery_cfg["diodeResonanceIn"]
        d_dmp_out = phys.battery_cfg["diodeDampingOut"]
        d_dmp_in = phys.battery_cfg["diodeDampingIn"]
        all_unit_diode = (
            d_res_out == 1.0 and d_res_in == 1.0 and d_dmp_out == 1.0 and d_dmp_in == 1.0
        )

        res_drive = phys.battery_cfg.get("resonanceDrive", 1.5)
        damp_drag = phys.battery_cfg.get("dampingDrag", 0.5)
        leak_lambda = phys.battery_cfg.get("leakLambda", 0.05)
        leak_lambda_active = leak_lambda * 0.2
        tau = phys.battery_cfg.get("flipThreshold", 0.85)
        collapse_thresh = tau * phys.battery_cfg.get("collapseFactor", 0.3)
        q_max = phys.battery_cfg.get("qMax", 40)
        av_gain = phys.battery_cfg.get("avalancheGain", 1.15)

        psi_relax = phys.psi_relax_base
        psi_nudge = phys.psi_global_nudge
        g_bias = phys.global_bias
        psi_diff = phys.psi_diffusion
        p_clamp = phys.psi_clamp
        neg_clamp = -p_clamp
        half_dt = 0.5 * dt
        dt6 = dt / 6.0
        default_gate = phys._DEFAULT_GATE_10

        active_e_indices: list[int] = []
        if _node_subset is not None:
            cached_sub = self._sub_edges_by_nodes.get(_node_subset)
            if cached_sub is not None:
                sub_act_e, sub_nonbg_e = cached_sub
            else:
                sub_set = set(_node_subset)
                sub_act_e = [
                    e_idx
                    for e_idx, e in enumerate(self.edges)
                    if e["from_idx"] in sub_set and e["to_idx"] in sub_set
                ]
                sub_nonbg_e = [
                    e_idx
                    for e_idx, e in enumerate(self.edges)
                    if (not e.get("background"))
                    and int(self.e_src_all[e_idx]) in sub_set
                    and int(self.e_dst_all[e_idx]) in sub_set
                ]
            comp_nodes = {0: list(_node_subset)}
            comp_act_edges = {0: sub_act_e}
            comp_nonbg_edges = {0: sub_nonbg_e}
        elif self.deduplicate_components:
            active_roles = self.group._active_dynamic_roles
            deferred_nodes: set[int] = set()
            for b_name, b_idxs in self._basin_node_indices.items():
                if (
                    f"wh_load_{b_name}" not in active_roles
                    and f"wh_store_{b_name}" not in active_roles
                    and f"wh_cmove_{b_name}" not in active_roles
                ):
                    self._basin_pending_steps[b_name] += int(steps)
                    deferred_nodes.update(b_idxs)
                else:
                    self._basin_untouched_since_t0[b_name] = False

            non_def_nodes = [ni for ni in range(self.n_nodes) if ni not in deferred_nodes]
            for e_idx, e in enumerate(self.edges):
                ia, ib = e["from_idx"], e["to_idx"]
                if ia is not None and ib is not None:
                    if ia in deferred_nodes or ib in deferred_nodes:
                        continue
                    active_e_indices.append(e_idx)

            comp_nodes = {0: non_def_nodes}
            comp_act_edges = {0: active_e_indices}
            comp_nonbg_edges = {
                0: [
                    e_idx
                    for e_idx, e in enumerate(self.edges)
                    if not e.get("background") and int(self.e_src_all[e_idx]) not in deferred_nodes
                ]
            }
        else:
            for e_idx, e in enumerate(self.edges):
                if e["from_idx"] is not None and e["to_idx"] is not None:
                    active_e_indices.append(e_idx)
            comp_nodes = {0: list(range(self.n_nodes))}
            comp_act_edges = {0: active_e_indices}
            comp_nonbg_edges = {
                0: [e_idx for e_idx, e in enumerate(self.edges) if not e.get("background")]
            }

        pre_idx = self.idx_by_id[pre_step_node["id"]] if pre_step_node is not None else None
        orig_t_global = phys._t

        prev_cache = self._comp_partition_cache
        dirty_nodes = self._dirty_nodes
        next_cache: dict[
            tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]],
            tuple[np.ndarray, np.ndarray],
        ] = {}

        groups_by_bc: dict[
            int,
            list[
                tuple[
                    np.ndarray,
                    np.ndarray,
                    np.ndarray,
                    np.ndarray,
                    np.ndarray,
                    np.ndarray,
                ]
            ],
        ] = {}
        for r, n_list in comp_nodes.items():
            n_tuple = tuple(n_list)
            e_act_list = comp_act_edges[r]
            e_nonbg_list = comp_nonbg_edges[r]
            e_act_tuple = tuple(e_act_list)
            e_nonbg_tuple = tuple(e_nonbg_list)
            comp_key = (n_tuple, e_act_tuple, e_nonbg_tuple)
            all_e_list = sorted(set(e_act_list).union(e_nonbg_list))
            n_sub = np.array(n_list, dtype=np.int64)
            e_act_sub = np.array(e_act_list, dtype=np.int64)
            e_nonbg_sub = np.array(e_nonbg_list, dtype=np.int64)
            all_e_sub = np.array(all_e_list, dtype=np.int64)
            if self.deduplicate_components and self.B > 1:
                if (
                    _node_subset is None
                    and comp_key in prev_cache
                    and not dirty_nodes.intersection(n_tuple)
                ):
                    u_sub, inv_sub = prev_cache[comp_key]
                else:
                    sig_parts = [
                        self.rho[:, n_sub],
                        self.psi[:, n_sub],
                        self.psi_bias[:, n_sub],
                        self.b_state[:, n_sub].astype(np.float64),
                        self.b_charge[:, n_sub],
                        self.m_arr[:, n_sub],
                        self.is_constellation[:, n_sub].astype(np.float64),
                        self.is_stellar[:, n_sub].astype(np.float64),
                    ]
                    if len(all_e_sub) > 0:
                        sig_parts.extend(
                            [
                                self.flux[:, all_e_sub],
                                self.bMag[:, all_e_sub],
                                self.cond[:, all_e_sub],
                            ]
                        )
                    sig_mat = np.hstack(sig_parts)
                    if _node_subset is not None and self.B > 64:
                        sig_mat = np.round(sig_mat, 4)
                    sig_bytes = (
                        np.ascontiguousarray(sig_mat)
                        .view(np.dtype((np.void, sig_mat.shape[1] * sig_mat.dtype.itemsize)))
                        .ravel()
                    )
                    _, u_sub, inv_sub = np.unique(
                        sig_bytes, return_index=True, return_inverse=True
                    )
                if _node_subset is None:
                    next_cache[comp_key] = (u_sub, inv_sub)
            else:
                u_sub = np.arange(self.B, dtype=np.int64)
                inv_sub = u_sub
            groups_by_bc.setdefault(len(u_sub), []).append(
                (n_sub, e_act_sub, e_nonbg_sub, all_e_sub, u_sub, inv_sub)
            )

        if _node_subset is None:
            self._comp_partition_cache = next_cache
            self._dirty_nodes = set()

        for B_c, comp_items in groups_by_bc.items():
            n_arr = np.concatenate([it[0] for it in comp_items])
            act_parts = [it[1] for it in comp_items if len(it[1]) > 0]
            e_act_arr = np.concatenate(act_parts) if act_parts else np.array([], dtype=np.int64)
            nonbg_parts = [it[2] for it in comp_items if len(it[2]) > 0]
            e_nonbg_arr = (
                np.concatenate(nonbg_parts) if nonbg_parts else np.array([], dtype=np.int64)
            )
            all_e_parts = [it[3] for it in comp_items if len(it[3]) > 0]
            all_comp_e = (
                np.concatenate(all_e_parts) if all_e_parts else np.array([], dtype=np.int64)
            )

            N_c = len(n_arr)
            E_c = len(all_comp_e)
            g2l_n = {int(gn): ln for ln, gn in enumerate(n_arr)}
            g2l_e = {int(ge): le for le, ge in enumerate(all_comp_e)}

            rho_c = np.empty((B_c, N_c), dtype=np.float64)
            psi_c = np.empty((B_c, N_c), dtype=np.float64)
            psi_bias_c = np.empty((B_c, N_c), dtype=np.float64)
            b_state_c = np.empty((B_c, N_c), dtype=np.int64)
            b_charge_c = np.empty((B_c, N_c), dtype=np.float64)
            m_arr_c = np.empty((B_c, N_c), dtype=np.float64)
            is_const_c = np.empty((B_c, N_c), dtype=bool)
            is_stel_c = np.empty((B_c, N_c), dtype=bool)

            flux_c = np.empty((B_c, E_c), dtype=np.float64)
            bMag_c = np.empty((B_c, E_c), dtype=np.float64)
            cond_c = np.empty((B_c, E_c), dtype=np.float64)

            comp_slices: list[tuple[np.ndarray, int, int, np.ndarray, int, int, np.ndarray]] = []
            n_off = 0
            e_off = 0
            for n_sub, _, _, all_e_sub, u_sub, inv_sub in comp_items:
                n_next = n_off + len(n_sub)
                e_next = e_off + len(all_e_sub)
                rho_c[:, n_off:n_next] = self.rho[u_sub][:, n_sub]
                psi_c[:, n_off:n_next] = self.psi[u_sub][:, n_sub]
                psi_bias_c[:, n_off:n_next] = self.psi_bias[u_sub][:, n_sub]
                b_state_c[:, n_off:n_next] = self.b_state[u_sub][:, n_sub]
                b_charge_c[:, n_off:n_next] = self.b_charge[u_sub][:, n_sub]
                m_arr_c[:, n_off:n_next] = self.m_arr[u_sub][:, n_sub]
                is_const_c[:, n_off:n_next] = self.is_constellation[u_sub][:, n_sub]
                is_stel_c[:, n_off:n_next] = self.is_stellar[u_sub][:, n_sub]
                if len(all_e_sub) > 0:
                    flux_c[:, e_off:e_next] = self.flux[u_sub][:, all_e_sub]
                    bMag_c[:, e_off:e_next] = self.bMag[u_sub][:, all_e_sub]
                    cond_c[:, e_off:e_next] = self.cond[u_sub][:, all_e_sub]
                comp_slices.append((n_sub, n_off, n_next, all_e_sub, e_off, e_next, inv_sub))
                n_off = n_next
                e_off = e_next

            is_bat_c = self.is_bat[n_arr]
            non_bat_c = ~is_bat_c
            w0_c = self.w0[all_comp_e] if E_c > 0 else np.array([], dtype=np.float64)
            e_src_c = (
                np.array([g2l_n[int(self.e_src_all[ge])] for ge in all_comp_e], dtype=np.int64)
                if E_c > 0
                else np.array([], dtype=np.int64)
            )
            e_dst_c = (
                np.array([g2l_n[int(self.e_dst_all[ge])] for ge in all_comp_e], dtype=np.int64)
                if E_c > 0
                else np.array([], dtype=np.int64)
            )
            e_src_bat_c = is_bat_c[e_src_c] if E_c > 0 else np.array([], dtype=bool)
            e_dst_bat_c = is_bat_c[e_dst_c] if E_c > 0 else np.array([], dtype=bool)

            r_idx_list: list[int] = []
            w_r_list: list[float] = []
            u_r_list: list[float] = []
            b_r_list: list[float] = []
            for ln, gn in enumerate(n_arr):
                n = self.nodes[gn]
                rb = n.get("r_bias", 0.0)
                if rb != 0.0 or "W_r" in n or "U_r" in n or "b_r" in n:
                    r_idx_list.append(ln)
                    w_r_list.append(float(n.get("W_r", 0.0)))
                    u_r_list.append(float(n.get("U_r", 0.0)))
                    b_r_list.append(float(n.get("b_r", 10.0)) + float(rb))
            has_custom_r = len(r_idx_list) > 0
            if has_custom_r:
                r_idx_arr = np.array(r_idx_list, dtype=np.int64)
                w_r_arr = np.array(w_r_list, dtype=np.float64)
                u_r_arr = np.array(u_r_list, dtype=np.float64)
                b_r_arr = np.array(b_r_list, dtype=np.float64)
            else:
                r_idx_arr = np.empty(0, dtype=np.int64)
                w_r_arr = np.empty(0, dtype=np.float64)
                u_r_arr = np.empty(0, dtype=np.float64)
                b_r_arr = np.empty(0, dtype=np.float64)

            bat_local_indices = [ln for ln, is_b in enumerate(is_bat_c) if is_b]
            bat_local_arr = np.array(bat_local_indices, dtype=np.int64)
            K_bat = len(bat_local_indices)
            bat_conn_map_c: dict[int, tuple[list[int], list[int]]] = {
                bi: ([], []) for bi in bat_local_indices
            }
            unique_bat_le = []
            seen_ble: set[int] = set()
            for ge in e_nonbg_arr:
                le = g2l_e[int(ge)]
                lu, lv = int(e_src_c[le]), int(e_dst_c[le])
                u_in = bool(is_bat_c[lu])
                v_in = (lv != lu) and bool(is_bat_c[lv])
                if not (u_in or v_in):
                    continue
                if u_in:
                    bat_conn_map_c[lu][0].append(le)
                    bat_conn_map_c[lu][1].append(lv)
                if v_in:
                    bat_conn_map_c[lv][0].append(le)
                    bat_conn_map_c[lv][1].append(lu)
                if le not in seen_ble:
                    seen_ble.add(le)
                    unique_bat_le.append(le)
            unique_bat_le_arr = np.array(unique_bat_le, dtype=np.int64)
            bat_conn_c = [
                (
                    bi,
                    np.array(bat_conn_map_c[bi][0], dtype=np.int64),
                    np.array(bat_conn_map_c[bi][1], dtype=np.int64),
                    is_bat_c[np.array(bat_conn_map_c[bi][1], dtype=np.int64)]
                    if bat_conn_map_c[bi][1]
                    else np.array([], dtype=bool),
                )
                for bi in bat_local_indices
            ]
            has_bat_to_bat = any(np.any(nb_is_bat) for _, _, _, nb_is_bat in bat_conn_c)
            max_bat_deg = max((len(it[1]) for it in bat_conn_c), default=0)
            if K_bat > 0 and not has_bat_to_bat and max_bat_deg > 0:
                bat_e_pad = np.zeros((K_bat, max_bat_deg), dtype=np.int64)
                bat_nb_pad = np.zeros((K_bat, max_bat_deg), dtype=np.int64)
                bat_valid_mask = np.zeros((1, K_bat, max_bat_deg), dtype=bool)
                bat_deg_inv = np.ones((1, K_bat), dtype=np.float64)
                for k_i, (_, e_a, nb_a, _) in enumerate(bat_conn_c):
                    deg_k = len(e_a)
                    if deg_k > 0:
                        bat_e_pad[k_i, :deg_k] = e_a
                        bat_nb_pad[k_i, :deg_k] = nb_a
                        bat_valid_mask[0, k_i, :deg_k] = True
                        bat_deg_inv[0, k_i] = 1.0 / deg_k
            else:
                bat_e_pad = np.zeros((0, 0), dtype=np.int64)
                bat_nb_pad = np.zeros((0, 0), dtype=np.int64)
                bat_valid_mask = np.zeros((1, 0, 0), dtype=bool)
                bat_deg_inv = np.ones((1, max(1, K_bat)), dtype=np.float64)

            act_le = (
                np.array([g2l_e[int(ge)] for ge in e_act_arr], dtype=np.int64)
                if len(e_act_arr) > 0
                else np.array([], dtype=np.int64)
            )
            # Collapse identical parallel edge bundles (same endpoints, w0, background, role prefix)
            u_rep_le_list: list[int] = []
            u_mult_list: list[float] = []
            inv_u_list: list[int] = []
            bundle_map: dict[tuple[int, int, float, bool], int] = {}
            for idx_a, ge in enumerate(e_act_arr):
                le = int(act_le[idx_a])
                ia_k = int(e_src_c[le])
                ib_k = int(e_dst_c[le])
                w0_k = float(w0_c[le])
                bg_k = bool(self.edges[ge].get("background"))
                b_key = (ia_k, ib_k, w0_k, bg_k)
                u_idx = bundle_map.get(b_key)
                if u_idx is not None:
                    rep_le = u_rep_le_list[u_idx]
                    if np.array_equal(flux_c[:, le], flux_c[:, rep_le]) and np.array_equal(
                        bMag_c[:, le], bMag_c[:, rep_le]
                    ):
                        u_mult_list[u_idx] += 1.0
                        inv_u_list.append(u_idx)
                        continue
                u_idx = len(u_rep_le_list)
                bundle_map[b_key] = u_idx
                u_rep_le_list.append(le)
                u_mult_list.append(1.0)
                inv_u_list.append(u_idx)

            u_rep_le = np.array(u_rep_le_list, dtype=np.int64)
            u_mult_arr = np.array(u_mult_list, dtype=np.float64)
            inv_u_act = np.array(inv_u_list, dtype=np.int64)
            U_act = len(u_rep_le)

            act_ia_c = e_src_c[u_rep_le] if U_act > 0 else np.array([], dtype=np.int64)
            act_ib_c = e_dst_c[u_rep_le] if U_act > 0 else np.array([], dtype=np.int64)
            act_w0_base_c = w0_c[u_rep_le] * c_base if U_act > 0 else np.array([], dtype=np.float64)
            act_bg_c = (
                np.array(
                    [bool(self.edges[all_comp_e[le]].get("background")) for le in u_rep_le],
                    dtype=bool,
                )
                if U_act > 0
                else np.array([], dtype=bool)
            )
            act_src_bat_c = is_bat_c[act_ia_c] if U_act > 0 else np.array([], dtype=bool)
            act_dst_bat_c = is_bat_c[act_ib_c] if U_act > 0 else np.array([], dtype=bool)
            act_has_bat_c = act_src_bat_c | act_dst_bat_c
            act_bat_node_c = (
                np.where(act_src_bat_c, act_ia_c, act_ib_c)
                if U_act > 0
                else np.array([], dtype=np.int64)
            )
            mhd_le_arr = (
                np.array([g2l_e[int(ge)] for ge in e_nonbg_arr], dtype=np.int64)
                if len(e_nonbg_arr) > 0
                else np.array([], dtype=np.int64)
            )
            pre_local = g2l_n.get(pre_idx) if pre_idx is not None else None

            use_gemm = (
                self.use_blas_incidence_gemm
                and (U_act > 0)
                and (B_c >= 4 or not self.deduplicate_components)
            )
            if use_gemm:
                M_inc_c = np.zeros((U_act, N_c), dtype=np.float64)
                np.add.at(M_inc_c, (np.arange(U_act), act_ia_c), u_mult_arr)
                np.add.at(M_inc_c, (np.arange(U_act), act_ib_c), -u_mult_arr)
            else:
                M_inc_c = None

            def eval_stage_c(
                rho_st: np.ndarray,
                flux_st: np.ndarray,
                psi_st: np.ndarray,
                damp_arr: np.ndarray,
                w_mul_act: np.ndarray,
                w_max_act: np.ndarray,
                gain_out_act: np.ndarray | None,
                gain_in_act: np.ndarray | None,
            ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
                p_raw = c_press * np.log(1.0 + (rho_st / m_arr_c))  # noqa: B023
                p_arr = default_gate * p_raw
                if has_custom_r:  # noqa: B023
                    ar = (
                        w_r_arr * rho_st[:, r_idx_arr]  # noqa: B023
                        + u_r_arr * psi_st[:, r_idx_arr]  # noqa: B023
                        + b_r_arr  # noqa: B023
                    )
                    ar = np.minimum(np.maximum(ar, -20.0), 20.0)
                    p_arr[:, r_idx_arr] = p_raw[:, r_idx_arr] / (1.0 + np.exp(-ar))  # noqa: B023

                if U_act > 0:  # noqa: B023
                    psi_a = psi_st[:, act_ia_c]  # noqa: B023
                    psi_b = psi_st[:, act_ib_c]  # noqa: B023
                    d_psi_e = psi_b - psi_a
                    if M_inc_c is not None:  # noqa: B023
                        lap = d_psi_e @ M_inc_c  # noqa: B023
                    else:
                        d_psi_m = d_psi_e * u_mult_arr  # noqa: B023
                        lap = np.zeros_like(psi_st)
                        np.add.at(lap, (slice(None), act_ia_c), d_psi_m)  # noqa: B023
                        np.add.at(lap, (slice(None), act_ib_c), -d_psi_m)  # noqa: B023

                    cond_e = np.minimum(
                        np.maximum(
                            w_mul_act * np.exp(half_c_gamma * (psi_a + psi_b)),
                            c_min,
                        ),
                        w_max_act,
                    )

                    delta_p = p_arr[:, act_ia_c] - p_arr[:, act_ib_c]  # noqa: B023
                    if all_unit_diode:
                        d_flux = cond_e * delta_p - flux_st
                    else:
                        diode_1 = np.where(delta_p > 0.0, gain_out_act, gain_in_act)
                        diode_2 = np.where(delta_p < 0.0, gain_out_act, gain_in_act)
                        diode_gain = np.where(
                            act_has_bat_c & (~act_bg_c),  # noqa: B023
                            np.where(act_src_bat_c, diode_1, diode_2),  # noqa: B023
                            1.0,
                        )
                        d_flux = (cond_e * diode_gain) * delta_p - flux_st
                    flow_amt = flux_st * 0.5
                    if M_inc_c is not None:  # noqa: B023
                        d_rho_tr = (-flow_amt) @ M_inc_c  # noqa: B023
                    else:
                        flow_m = flow_amt * u_mult_arr  # noqa: B023
                        d_rho_tr = np.zeros_like(rho_st)
                        np.add.at(d_rho_tr, (slice(None), act_ia_c), -flow_m)  # noqa: B023
                        np.add.at(d_rho_tr, (slice(None), act_ib_c), flow_m)  # noqa: B023
                else:
                    lap = np.zeros_like(psi_st)
                    d_rho_tr = np.zeros_like(rho_st)
                    d_flux = np.zeros_like(flux_st)

                d_rho = default_gate * (d_rho_tr + damp_arr * rho_st)
                rho_norm = rho_st / (rho_st + 40.0)
                relax_to_bias = (psi_relax * (0.35 + 0.65 * rho_norm)) * (psi_bias_c - psi_st)  # noqa: B023
                relax_to_global = psi_nudge * (g_bias - psi_st)
                d_psi = np.where(
                    non_bat_c, psi_diff * lap + relax_to_bias + relax_to_global, 0.0  # noqa: B023
                )
                return d_rho, d_flux, d_psi

            for step_idx in range(steps):
                is_last = step_idx == steps - 1
                if pre_local is not None:
                    rho_c[:, pre_local] = pre_step_rho
                    psi_c[:, pre_local] = pre_step_psi
                if phys.semantic_cfg:
                    m_arr_c = np.where(
                        is_const_c,
                        np.maximum(sem_min_mass, m_arr_c * sem_factor),
                        m_arr_c,
                    )

                if K_bat > 0 and not has_bat_to_bat:
                    b_chg_all = b_charge_c[:, bat_local_arr]
                    b_st_all = b_state_c[:, bat_local_arr]
                    if max_bat_deg > 0:
                        w_pad = cond_c[:, bat_e_pad]
                        psi_nb_pad = psi_c[:, bat_nb_pad]
                        nb_pos = (psi_nb_pad >= 0.0) & bat_valid_mask
                        nb_neg = (psi_nb_pad < 0.0) & bat_valid_mask
                        inc = np.sum(np.where(nb_pos, w_pad * res_drive, 0.0), axis=2)
                        drg = np.sum(np.where(nb_neg, w_pad * damp_drag, 0.0), axis=2)
                        net_flux = inc - drg
                    else:
                        net_flux = np.zeros((B_c, K_bat), dtype=np.float64)
                    charge_delta = np.tanh(net_flux) * dt
                    leak = b_chg_all * np.where(b_st_all == 1, leak_lambda_active, leak_lambda)
                    b_chg_all = np.minimum(np.maximum(b_chg_all + charge_delta - leak, 0.0), 1.0)
                    flip_on = (b_st_all == -1) & (b_chg_all > tau)
                    collapse_off = (b_st_all == 1) & (b_chg_all < collapse_thresh)
                    if np.any(flip_on):
                        for k_i in np.where(np.any(flip_on, axis=0))[0]:
                            f_col = flip_on[:, k_i]
                            share = (q_max * b_chg_all[:, k_i] * av_gain) * bat_deg_inv[0, k_i]
                            for nb_i in bat_conn_c[k_i][2]:
                                rho_c[:, nb_i] = np.where(
                                    f_col, rho_c[:, nb_i] + share, rho_c[:, nb_i]
                                )
                        b_st_all = np.where(flip_on, 1, b_st_all)
                        b_chg_all = np.where(flip_on, 1.0, b_chg_all)
                    if np.any(collapse_off):
                        b_st_all = np.where(collapse_off, -1, b_st_all)
                    b_state_c[:, bat_local_arr] = b_st_all
                    b_charge_c[:, bat_local_arr] = b_chg_all
                    s_f_all = b_st_all.astype(np.float64)
                    psi_c[:, bat_local_arr] = s_f_all
                    psi_bias_c[:, bat_local_arr] = s_f_all
                else:
                    for bi, e_arr, nb_arr, nb_is_bat in bat_conn_c:
                        b_chg = b_charge_c[:, bi]
                        b_st = b_state_c[:, bi]
                        if len(e_arr) > 0:
                            w_b = cond_c[:, e_arr]
                            nb_st = np.where(
                                nb_is_bat,
                                b_state_c[:, nb_arr],
                                np.where(psi_c[:, nb_arr] >= 0.0, 1, -1),
                            )
                            inc = np.sum(np.where(nb_st == 1, w_b * res_drive, 0.0), axis=1)
                            drg = np.sum(np.where(nb_st != 1, w_b * damp_drag, 0.0), axis=1)
                            net_flux = inc - drg
                        else:
                            net_flux = np.zeros(B_c, dtype=np.float64)
                        charge_delta = np.tanh(net_flux) * dt
                        leak = b_chg * np.where(b_st == 1, leak_lambda_active, leak_lambda)
                        b_chg = np.minimum(np.maximum(b_chg + charge_delta - leak, 0.0), 1.0)
                        flip_on = (b_st == -1) & (b_chg > tau)
                        collapse_off = (b_st == 1) & (b_chg < collapse_thresh)
                        if np.any(flip_on):
                            pulse_mass = q_max * b_chg * av_gain
                            share = pulse_mass / max(1, len(e_arr))
                            for nb_i in nb_arr:
                                rho_c[:, nb_i] = np.where(
                                    flip_on, rho_c[:, nb_i] + share, rho_c[:, nb_i]
                                )
                            b_st = np.where(flip_on, 1, b_st)
                            b_chg = np.where(flip_on, 1.0, b_chg)
                        if np.any(collapse_off):
                            b_st = np.where(collapse_off, -1, b_st)
                        b_state_c[:, bi] = b_st
                        b_charge_c[:, bi] = b_chg
                        s_f = b_st.astype(np.float64)
                        psi_c[:, bi] = s_f
                        psi_bias_c[:, bi] = s_f

                rho_0 = rho_c.copy()
                psi_0 = psi_c.copy()
                flux_a0 = flux_c[:, u_rep_le].copy()
                damp_arr = np.where(is_stel_c, damp_base * star_damp, damp_base)
                if U_act > 0:
                    bmag_act = bMag_c[:, u_rep_le]
                    bmag_mul_act = np.where(bmag_act != 0.0, 1.0 + b_gamma * bmag_act, 1.0)
                    bat_s_act = b_state_c[:, act_bat_node_c]
                    w_mul_act = (act_w0_base_c * bmag_mul_act) * np.where(
                        act_has_bat_c,
                        np.where(bat_s_act == 1, res_boost, damp_clamp),
                        1.0,
                    )
                    w_max_act = np.where(act_has_bat_c & (bat_s_act != 1), tight_max, c_max)
                    if all_unit_diode:
                        gain_out_act = None
                        gain_in_act = None
                    else:
                        gain_out_act = np.where(bat_s_act == 1, d_res_out, d_dmp_out)
                        gain_in_act = np.where(bat_s_act == 1, d_res_in, d_dmp_in)
                else:
                    w_mul_act = np.empty((B_c, 0), dtype=np.float64)
                    w_max_act = np.empty((B_c, 0), dtype=np.float64)
                    gain_out_act = None
                    gain_in_act = None

                d_rho1, d_flux1, d_psi1 = eval_stage_c(
                    rho_0, flux_a0, psi_0, damp_arr, w_mul_act, w_max_act, gain_out_act, gain_in_act
                )
                rho_s = np.maximum(0.0, rho_0 + half_dt * d_rho1)
                psi_s = np.minimum(np.maximum(psi_0 + half_dt * d_psi1, neg_clamp), p_clamp)
                flux_s = flux_a0 + half_dt * d_flux1
                d_rho2, d_flux2, d_psi2 = eval_stage_c(
                    rho_s, flux_s, psi_s, damp_arr, w_mul_act, w_max_act, gain_out_act, gain_in_act
                )
                rho_s = np.maximum(0.0, rho_0 + half_dt * d_rho2)
                psi_s = np.minimum(np.maximum(psi_0 + half_dt * d_psi2, neg_clamp), p_clamp)
                flux_s = flux_a0 + half_dt * d_flux2
                d_rho3, d_flux3, d_psi3 = eval_stage_c(
                    rho_s, flux_s, psi_s, damp_arr, w_mul_act, w_max_act, gain_out_act, gain_in_act
                )
                rho_s = np.maximum(0.0, rho_0 + dt * d_rho3)
                psi_s = np.minimum(np.maximum(psi_0 + dt * d_psi3, neg_clamp), p_clamp)
                flux_s = flux_a0 + dt * d_flux3
                d_rho4, d_flux4, d_psi4 = eval_stage_c(
                    rho_s, flux_s, psi_s, damp_arr, w_mul_act, w_max_act, gain_out_act, gain_in_act
                )

                rho_c = np.maximum(
                    0.0, rho_0 + dt6 * (d_rho1 + 2.0 * d_rho2 + 2.0 * d_rho3 + d_rho4)
                )
                psi_c = np.minimum(
                    np.maximum(
                        psi_0 + dt6 * (d_psi1 + 2.0 * d_psi2 + 2.0 * d_psi3 + d_psi4),
                        neg_clamp,
                    ),
                    p_clamp,
                )
                flux_u_new = flux_a0 + dt6 * (
                    d_flux1 + 2.0 * d_flux2 + 2.0 * d_flux3 + d_flux4
                )
                if U_act > 0:
                    flux_c[:, act_le] = flux_u_new[:, inv_u_act]

                if is_last and E_c > 0:
                    avg_psi_end = 0.5 * (psi_c[:, e_src_c] + psi_c[:, e_dst_c])
                    w_end = (
                        (w0_c * c_base)
                        * np.exp(c_gamma * avg_psi_end)
                        * (1.0 + b_gamma * bMag_c)
                    )
                    hb_end = e_src_bat_c | e_dst_bat_c
                    bn_end = np.where(e_src_bat_c, e_src_c, e_dst_c)
                    s_end = b_state_c[:, bn_end]
                    cond_c = np.where(
                        hb_end,
                        np.where(
                            s_end == 1,
                            np.minimum(np.maximum(w_end * res_boost, c_min), c_max),
                            np.minimum(np.maximum(w_end * damp_clamp, c_min), tight_max),
                        ),
                        np.minimum(np.maximum(w_end, c_min), c_max),
                    )
                elif len(unique_bat_le_arr) > 0:
                    ia_u = e_src_c[unique_bat_le_arr]
                    ib_u = e_dst_c[unique_bat_le_arr]
                    avg_psi_u = 0.5 * (psi_c[:, ia_u] + psi_c[:, ib_u])
                    w_u = (
                        (w0_c[unique_bat_le_arr] * c_base)
                        * np.exp(c_gamma * avg_psi_u)
                        * (1.0 + b_gamma * bMag_c[:, unique_bat_le_arr])
                    )
                    sb_u = e_src_bat_c[unique_bat_le_arr]
                    db_u = e_dst_bat_c[unique_bat_le_arr]
                    hb_u = sb_u | db_u
                    bn_u = np.where(sb_u, ia_u, ib_u)
                    s_u = b_state_c[:, bn_u]
                    cond_c[:, unique_bat_le_arr] = np.where(
                        hb_u,
                        np.where(
                            s_u == 1,
                            np.minimum(np.maximum(w_u * res_boost, c_min), c_max),
                            np.minimum(np.maximum(w_u * damp_clamp, c_min), tight_max),
                        ),
                        np.minimum(np.maximum(w_u, c_min), c_max),
                    )

                if phys.mhd_cfg and len(mhd_le_arr) > 0:
                    build = phys.mhd_cfg.get("bBuild", 0.10)
                    decay = phys.mhd_cfg.get("bDecay", 0.06)
                    b_max = phys.mhd_cfg.get("bMax", 4.0)
                    decay_factor = math.exp(-decay * dt)
                    bMag_c[:, mhd_le_arr] = np.minimum(
                        np.maximum(
                            bMag_c[:, mhd_le_arr] * decay_factor
                            + build * np.abs(flux_c[:, mhd_le_arr]) * dt,
                            0.0,
                        ),
                        b_max,
                    )

                if phys.jeans_cfg:
                    p_end = c_press * np.log(1.0 + (rho_c / m_arr_c))
                    j_val = rho_c / (np.abs(p_end) + 1e-6)
                    collapsed = j_val >= j_crit
                    is_const_c |= collapsed
                    is_stel_c |= collapsed

            for n_sub, n_off, n_next, all_e_sub, e_off, e_next, inv_sub in comp_slices:
                self.rho[:, n_sub] = rho_c[:, n_off:n_next][inv_sub]
                self.psi[:, n_sub] = psi_c[:, n_off:n_next][inv_sub]
                self.psi_bias[:, n_sub] = psi_bias_c[:, n_off:n_next][inv_sub]
                self.b_state[:, n_sub] = b_state_c[:, n_off:n_next][inv_sub]
                self.b_charge[:, n_sub] = b_charge_c[:, n_off:n_next][inv_sub]
                self.m_arr[:, n_sub] = m_arr_c[:, n_off:n_next][inv_sub]
                self.is_constellation[:, n_sub] = is_const_c[:, n_off:n_next][inv_sub]
                self.is_stellar[:, n_sub] = is_stel_c[:, n_off:n_next][inv_sub]
                if len(all_e_sub) > 0:
                    self.flux[:, all_e_sub] = flux_c[:, e_off:e_next][inv_sub]
                    self.bMag[:, all_e_sub] = bMag_c[:, e_off:e_next][inv_sub]
                    self.cond[:, all_e_sub] = cond_c[:, e_off:e_next][inv_sub]

        if _count_global_steps:
            phys._t = orig_t_global + steps * dt
        if _node_subset is None and len(self._bat_nonbg_dyn_eidxs) > 0:
            self._update_conductance_subset(self._bat_nonbg_dyn_eidxs)
        if phys.mhd_cfg and steps == 1 and _node_subset is None:
            build = phys.mhd_cfg.get("bBuild", 0.10)
            decay = phys.mhd_cfg.get("bDecay", 0.06)
            b_max = phys.mhd_cfg.get("bMax", 4.0)
            decay_factor = math.exp(-decay * dt)
            bg_e = np.array(
                [e_idx for e_idx, e in enumerate(self.edges) if e.get("background")],
                dtype=np.int64,
            )
            if len(bg_e) > 0:
                self.bMag[:, bg_e] = np.minimum(
                    np.maximum(
                        self.bMag[:, bg_e] * decay_factor + build * np.abs(self.flux[:, bg_e]) * dt,
                        0.0,
                    ),
                    b_max,
                )

    def flush_all_pending_steps(self) -> None:
        if self.deduplicate_components:
            for b_name in tuple(self._basin_pending_steps):
                self._flush_basin_pending_steps(b_name)
            self._update_conductance_subset(np.arange(self.n_edges, dtype=np.int64))

    def run(self, program: list[Instruction]) -> list[dict]:
        from test_logos_vm import LogosVM

        vm = LogosVM(self.seq)
        res = vm.run(program)
        if self.deduplicate_components and self.B <= 64:
            self.flush_all_pending_steps()
        return res

    def read_output_rows(self, output_basins: list[str]) -> list[tuple[int, ...]]:
        out_bat_idxs = [
            self.idx_by_id[self.group.semantic.basins[ob].battery_id] for ob in output_basins
        ]
        return [
            tuple(1 if int(self.b_state[r_i, bi]) == 1 else 0 for bi in out_bat_idxs)
            for r_i in range(self.B)
        ]


