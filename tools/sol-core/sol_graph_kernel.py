# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Graph Kernel Vectorization Scaffold
=======================================
Implements sparse CSR representation, graph state array conversion, and
vectorized placeholder math for SOL WideWord physics models.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union

# Try to import numpy
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

@dataclass
class CSRAdjacency:
    row_ptr: Any  # np.ndarray or List[int]
    col_indices: Any  # np.ndarray or List[int]
    edge_indices: Any  # np.ndarray or List[int]

@dataclass
class GraphKernelArrays:
    node_ids: List[str]
    rho: Any  # np.ndarray or List[float]
    psi: Any  # np.ndarray or List[float]
    pressure: Any  # np.ndarray or List[float]
    semantic_mass: Any  # np.ndarray or List[float]
    edge_from_idx: Any  # np.ndarray or List[int]
    edge_to_idx: Any  # np.ndarray or List[int]
    edge_w0: Any  # np.ndarray or List[float]
    edge_conductance: Any  # np.ndarray or List[float]
    edge_flux: Any  # np.ndarray or List[float]
    csr: CSRAdjacency

@dataclass
class VectorizedStepReport:
    total_flux: float
    active_count: int
    evidence: Dict[str, Any]

def build_csr_from_edges(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> CSRAdjacency:
    """
    Builds a directed CSR representation of the graph adjacency from nodes and edges.
    """
    node_count = len(nodes)
    node_index_by_id = {n["id"]: idx for idx, n in enumerate(nodes)}

    # Count outgoing edges per node index
    row_counts = [0] * node_count
    for e in edges:
        from_idx = node_index_by_id.get(e["from"])
        if from_idx is not None:
            row_counts[from_idx] += 1

    # Compute row_ptr
    row_ptr = [0] * (node_count + 1)
    for i in range(node_count):
        row_ptr[i + 1] = row_ptr[i] + row_counts[i]

    # Fill col_indices and edge_indices
    current_ptrs = list(row_ptr)
    edge_count = len(edges)
    col_indices = [0] * edge_count
    edge_indices = [0] * edge_count

    for edge_idx, e in enumerate(edges):
        from_idx = node_index_by_id.get(e["from"])
        to_idx = node_index_by_id.get(e["to"])
        if from_idx is not None and to_idx is not None:
            ptr = current_ptrs[from_idx]
            col_indices[ptr] = to_idx
            edge_indices[ptr] = edge_idx
            current_ptrs[from_idx] += 1

    if HAS_NUMPY:
        return CSRAdjacency(
            row_ptr=np.array(row_ptr, dtype=np.int32),
            col_indices=np.array(col_indices, dtype=np.int32),
            edge_indices=np.array(edge_indices, dtype=np.int32)
        )
    return CSRAdjacency(
        row_ptr=row_ptr,
        col_indices=col_indices,
        edge_indices=edge_indices
    )

def snapshot_graph_arrays(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> GraphKernelArrays:
    """
    Creates a snapshot of the graph nodes and edges represented as flat arrays.
    """
    node_ids = [n["id"] for n in nodes]
    node_index_by_id = {n["id"]: idx for idx, n in enumerate(nodes)}

    rho = [float(n.get("rho", 0.0)) for n in nodes]
    psi = [float(n.get("psi", 0.0)) for n in nodes]
    pressure = [float(n.get("p", 0.0)) for n in nodes]
    semantic_mass = [float(n.get("semanticMass", 1.0)) for n in nodes]

    edge_from_idx = [node_index_by_id[e["from"]] for e in edges]
    edge_to_idx = [node_index_by_id[e["to"]] for e in edges]
    edge_w0 = [float(e.get("w0", 1.0)) for e in edges]
    edge_conductance = [float(e.get("conductance", 1.0)) for e in edges]
    edge_flux = [float(e.get("flux", 0.0)) for e in edges]

    csr = build_csr_from_edges(nodes, edges)

    if HAS_NUMPY:
        return GraphKernelArrays(
            node_ids=node_ids,
            rho=np.array(rho, dtype=np.float64),
            psi=np.array(psi, dtype=np.float64),
            pressure=np.array(pressure, dtype=np.float64),
            semantic_mass=np.array(semantic_mass, dtype=np.float64),
            edge_from_idx=np.array(edge_from_idx, dtype=np.int32),
            edge_to_idx=np.array(edge_to_idx, dtype=np.int32),
            edge_w0=np.array(edge_w0, dtype=np.float64),
            edge_conductance=np.array(edge_conductance, dtype=np.float64),
            edge_flux=np.array(edge_flux, dtype=np.float64),
            csr=csr
        )

    return GraphKernelArrays(
        node_ids=node_ids,
        rho=rho,
        psi=psi,
        pressure=pressure,
        semantic_mass=semantic_mass,
        edge_from_idx=edge_from_idx,
        edge_to_idx=edge_to_idx,
        edge_w0=edge_w0,
        edge_conductance=edge_conductance,
        edge_flux=edge_flux,
        csr=csr
    )

def restore_graph_arrays(snapshot: GraphKernelArrays, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
    """
    Restores array-backed state from a GraphKernelArrays snapshot in-place into lists of dicts.
    """
    for idx, n in enumerate(nodes):
        n["rho"] = float(snapshot.rho[idx])
        n["psi"] = float(snapshot.psi[idx])
        n["p"] = float(snapshot.pressure[idx])
        n["semanticMass"] = float(snapshot.semantic_mass[idx])

    for idx, e in enumerate(edges):
        e["w0"] = float(snapshot.edge_w0[idx])
        e["conductance"] = float(snapshot.edge_conductance[idx])
        e["flux"] = float(snapshot.edge_flux[idx])

# ---- Vectorized math helpers ----

def compute_pressure_array(rho: Any, semantic_mass: Any, c_press: float) -> Any:
    """
    Vectorized equation of state: P = c_press * log(1 + rho/semantic_mass)
    """
    if HAS_NUMPY and isinstance(rho, np.ndarray):
        return c_press * np.log(1.0 + rho / semantic_mass)
    
    return [c_press * math.log(1.0 + r / m) for r, m in zip(rho, semantic_mass)]

def compute_flux_delta_array(pressure: Any, edge_from: Any, edge_to: Any, conductance: Any) -> Any:
    """
    Vectorized flow flux rate computation: conductance * (pressure[from] - pressure[to])
    """
    if HAS_NUMPY and isinstance(pressure, np.ndarray):
        delta_p = pressure[edge_from] - pressure[edge_to]
        return conductance * delta_p

    return [cond * (pressure[src] - pressure[dst]) for src, dst, cond in zip(edge_from, edge_to, conductance)]

def compute_rho_transport_array(edge_flux: Any, edge_from: Any, edge_to: Any, node_count: int) -> Any:
    """
    Vectorized transport updates for rho based on flux rates.
    """
    if HAS_NUMPY and isinstance(edge_flux, np.ndarray):
        d_rho_transport = np.zeros(node_count, dtype=np.float64)
        flow_rate = edge_flux * 0.5
        np.add.at(d_rho_transport, edge_from, -flow_rate)
        np.add.at(d_rho_transport, edge_to, flow_rate)
        return d_rho_transport

    d_rho_transport = [0.0] * node_count
    for flux, src, dst in zip(edge_flux, edge_from, edge_to):
        flow_rate = flux * 0.5
        d_rho_transport[src] -= flow_rate
        d_rho_transport[dst] += flow_rate
    return d_rho_transport


@dataclass
class VectorizedBackendConfig:
    damping: float
    c_press: float
    dt: float

@dataclass
class VectorizedParityReport:
    lane_id: int
    node_count: int
    edge_count: int
    max_rho_error: float
    max_pressure_error: float
    max_flux_error: float
    tolerance: float
    parity_passed: bool
    backend_mode: str
    evidence: Dict[str, Any]

class VectorizedGraphStepper:
    def __init__(self, snapshot: GraphKernelArrays, node_groups: List[str], initial_t: float = 0.0):
        self.snapshot = snapshot
        self.node_groups = node_groups
        self._t = initial_t

    @classmethod
    def from_engine(cls, engine: Any) -> "VectorizedGraphStepper":
        """
        Builds a VectorizedGraphStepper from an existing SOLEngine instance.
        """
        nodes = engine.physics.nodes
        edges = engine.physics.edges
        snapshot = snapshot_graph_arrays(nodes, edges)
        node_groups = [n.get("group", "bridge") for n in nodes]
        return cls(snapshot, node_groups, initial_t=engine.physics._t)

    def step_arrays(self, dt: float, c_press: float, damping: float) -> VectorizedStepReport:
        """
        Executes a single step purely on the array/list snapshot state.
        """
        self._t += dt
        
        # 1. Phase gating
        omega = 0.15  # Default omega
        phase = math.cos(omega * self._t * 10)
        is_surface_active = phase > -0.2
        is_deep_active = phase < 0.2

        edge_count = len(self.snapshot.edge_from_idx)
        src_awake = [True] * edge_count
        dst_awake = [True] * edge_count

        for i in range(edge_count):
            src_idx = int(self.snapshot.edge_from_idx[i])
            dst_idx = int(self.snapshot.edge_to_idx[i])
            src_g = self.node_groups[src_idx]
            dst_g = self.node_groups[dst_idx]
            
            if src_g == "tech" and not is_surface_active:
                src_awake[i] = False
            if src_g == "spirit" and not is_deep_active:
                src_awake[i] = False
            if dst_g == "tech" and not is_surface_active:
                dst_awake[i] = False
            if dst_g == "spirit" and not is_deep_active:
                dst_awake[i] = False

        # 2. Update conductance based on psi
        # avg_psi = (psi[from] + psi[to]) / 2.0
        # conductance = w0 * exp(0.75 * avg_psi) clamped to [0.1, 3.0]
        if HAS_NUMPY:
            avg_psi = 0.5 * (self.snapshot.psi[self.snapshot.edge_from_idx] + self.snapshot.psi[self.snapshot.edge_to_idx])
            w = self.snapshot.edge_w0 * np.exp(0.75 * avg_psi)
            self.snapshot.edge_conductance = np.clip(w, 0.1, 3.0)
        else:
            for i in range(edge_count):
                src_idx = self.snapshot.edge_from_idx[i]
                dst_idx = self.snapshot.edge_to_idx[i]
                avg_psi = 0.5 * (self.snapshot.psi[src_idx] + self.snapshot.psi[dst_idx])
                w = self.snapshot.edge_w0[i] * math.exp(0.75 * avg_psi)
                self.snapshot.edge_conductance[i] = max(0.1, min(3.0, w))

        # 3. Compute pressure array
        self.snapshot.pressure = compute_pressure_array(self.snapshot.rho, self.snapshot.semantic_mass, c_press)

        # 4. Compute target flux based on pressure deltas and conductance
        target_flux = [0.0] * edge_count
        for i in range(edge_count):
            if not src_awake[i] and not dst_awake[i]:
                target_flux[i] = 0.0
            else:
                src_idx = int(self.snapshot.edge_from_idx[i])
                dst_idx = int(self.snapshot.edge_to_idx[i])
                
                # Check for tension factor based on group
                tension = 1.0
                src_g = self.node_groups[src_idx]
                dst_g = self.node_groups[dst_idx]
                if src_g == "tech" or dst_g == "tech":
                    tension = 1.2  # surfaceTension
                elif src_g == "spirit" or dst_g == "spirit":
                    tension = 0.8  # deepViscosity
                    
                delta_p = self.snapshot.pressure[src_idx] - self.snapshot.pressure[dst_idx]
                target_flux[i] = self.snapshot.edge_conductance[i] * tension * delta_p

        # Convert target_flux to numpy array if using numpy
        if HAS_NUMPY:
            target_flux_arr = np.array(target_flux, dtype=np.float64)
            # Update edge flux: flux += dt * (target_flux - flux)
            self.snapshot.edge_flux += dt * (target_flux_arr - self.snapshot.edge_flux)
        else:
            for i in range(edge_count):
                self.snapshot.edge_flux[i] += dt * (target_flux[i] - self.snapshot.edge_flux[i])

        # 5. Compute rho transport array
        d_rho_transport = [0.0] * len(self.snapshot.node_ids)
        for i in range(edge_count):
            rate = self.snapshot.edge_flux[i] * 0.5
            src_idx = int(self.snapshot.edge_from_idx[i])
            dst_idx = int(self.snapshot.edge_to_idx[i])
            if src_awake[i]:
                d_rho_transport[src_idx] -= rate
            if dst_awake[i]:
                d_rho_transport[dst_idx] += rate

        # Convert d_rho_transport to numpy array if using numpy
        if HAS_NUMPY:
            d_rho_transport_arr = np.array(d_rho_transport, dtype=np.float64)
            decay = -damping * 0.1 * self.snapshot.rho
            self.snapshot.rho = np.maximum(0.0, self.snapshot.rho + dt * (d_rho_transport_arr + decay))
            # Compute total flux and active count
            total_flux = float(np.sum(np.abs(self.snapshot.edge_flux)))
            active_count = int(np.sum(self.snapshot.rho > 0.1))
        else:
            for i in range(len(self.snapshot.rho)):
                decay = -damping * 0.1 * self.snapshot.rho[i]
                self.snapshot.rho[i] = max(0.0, self.snapshot.rho[i] + dt * (d_rho_transport[i] + decay))
            total_flux = sum(abs(f) for f in self.snapshot.edge_flux)
            active_count = sum(1 for r in self.snapshot.rho if r > 0.1)

        evidence = {
            "is_surface_active": is_surface_active,
            "is_deep_active": is_deep_active,
            "total_flux": total_flux,
            "active_count": active_count
        }

        return VectorizedStepReport(total_flux=total_flux, active_count=active_count, evidence=evidence)

    def compare_to_engine(self, engine: Any, tolerance: float = 1e-6) -> VectorizedParityReport:
        """
        Compares the current array snapshot state against the engine's dictionary state.
        """
        nodes = engine.physics.nodes
        edges = engine.physics.edges

        eng_rho = [n["rho"] for n in nodes]
        eng_p = [n["p"] for n in nodes]
        eng_flux = [e["flux"] for e in edges]

        rho_errors = [abs(a - b) for a, b in zip(self.snapshot.rho, eng_rho)]
        p_errors = [abs(a - b) for a, b in zip(self.snapshot.pressure, eng_p)]
        flux_errors = [abs(a - b) for a, b in zip(self.snapshot.edge_flux, eng_flux)]

        max_rho_err = float(max(rho_errors)) if rho_errors else 0.0
        max_p_err = float(max(p_errors)) if p_errors else 0.0
        max_flux_err = float(max(flux_errors)) if flux_errors else 0.0

        max_all = max(max_rho_err, max_p_err, max_flux_err)
        parity_passed = bool(max_all <= tolerance)

        evidence = {
            "rho_errors": rho_errors,
            "pressure_errors": p_errors,
            "flux_errors": flux_errors,
            "tolerance": tolerance
        }

        # Determine backend mode of engine
        backend_mode = getattr(engine, "backend", "dict")

        return VectorizedParityReport(
            lane_id=0,
            node_count=len(nodes),
            edge_count=len(edges),
            max_rho_error=max_rho_err,
            max_pressure_error=max_p_err,
            max_flux_error=max_flux_err,
            tolerance=tolerance,
            parity_passed=parity_passed,
            backend_mode=backend_mode,
            evidence=evidence
        )

def run_shadow_steps(engine: Any, steps: int, dt: float, c_press: float, damping: float) -> VectorizedParityReport:
    """
    Runs shadow execution steps in parallel on the engine (dict) and the vectorized stepper.
    Restores the engine's original state at the end.
    """
    from sol_engine import snapshot_state, restore_state
    
    # 1. Snapshot engine original state
    orig_state = snapshot_state(engine.physics)
    orig_t = engine.physics._t
    orig_step_count = getattr(engine, "_step_count", 0)
    orig_backend = getattr(engine, "backend", "dict")

    # 2. Build vectorized stepper from initial state
    stepper = VectorizedGraphStepper.from_engine(engine)

    # 3. Step the engine
    engine.backend = "dict"
    try:
        for _ in range(steps):
            engine.step(dt, c_press, damping)
    finally:
        engine.backend = orig_backend

    # 4. Step the arrays
    for _ in range(steps):
        stepper.step_arrays(dt, c_press, damping)

    # 5. Compare states
    report = stepper.compare_to_engine(engine)

    # 6. Restore engine state safely
    restore_state(engine.physics, orig_state, engine.cap_law)
    engine.physics._t = orig_t
    if hasattr(engine, "_step_count"):
        engine._step_count = orig_step_count

    return report


@dataclass
class GCSnapshot:
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


def snapshot_for_gc(engine_or_arrays: Any) -> GCSnapshot:
    """
    Creates a snapshot of nodes and edges for GC and compaction analysis.
    Supports either an engine (with physics.nodes and physics.edges) or a GraphKernelArrays.
    """
    # Check if it is an engine
    physics = getattr(engine_or_arrays, "physics", None)
    if physics is not None and hasattr(physics, "nodes") and hasattr(physics, "edges"):
        nodes = [dict(n) for n in physics.nodes]
        edges = [dict(e) for e in physics.edges]
        return GCSnapshot(nodes=nodes, edges=edges)
    
    # Check if it is a GraphKernelArrays
    node_ids = getattr(engine_or_arrays, "node_ids", None)
    if node_ids is not None:
        nodes = []
        for idx, n_id in enumerate(node_ids):
            nodes.append({
                "id": n_id,
                "rho": float(engine_or_arrays.rho[idx]),
                "psi": float(engine_or_arrays.psi[idx]),
                "p": float(engine_or_arrays.pressure[idx]),
                "semanticMass": float(engine_or_arrays.semantic_mass[idx]),
                "group": "bridge"
            })
        
        edges = []
        edge_from_idx = getattr(engine_or_arrays, "edge_from_idx", [])
        edge_to_idx = getattr(engine_or_arrays, "edge_to_idx", [])
        edge_w0 = getattr(engine_or_arrays, "edge_w0", [])
        edge_conductance = getattr(engine_or_arrays, "edge_conductance", [])
        edge_flux = getattr(engine_or_arrays, "edge_flux", [])
        
        for idx in range(len(edge_from_idx)):
            from_id = node_ids[edge_from_idx[idx]]
            to_id = node_ids[edge_to_idx[idx]]
            edges.append({
                "from": from_id,
                "to": to_id,
                "w0": float(edge_w0[idx]),
                "conductance": float(edge_conductance[idx]),
                "flux": float(edge_flux[idx])
            })
        return GCSnapshot(nodes=nodes, edges=edges)
        
    if hasattr(engine_or_arrays, "nodes") and hasattr(engine_or_arrays, "edges"):
        return GCSnapshot(
            nodes=[dict(n) for n in engine_or_arrays.nodes],
            edges=[dict(e) for e in engine_or_arrays.edges]
        )
        
    raise ValueError("Unsupported engine_or_arrays type for GC snapshotting.")


def validate_snapshot_integrity(snapshot: GCSnapshot) -> bool:
    """
    Validates that node IDs are unique, and all edges refer to valid node IDs.
    """
    if not hasattr(snapshot, "nodes") or not hasattr(snapshot, "edges"):
        return False
        
    node_ids = set()
    for n in snapshot.nodes:
        n_id = n.get("id")
        if not n_id or n_id in node_ids:
            return False
        node_ids.add(n_id)
        
    for e in snapshot.edges:
        from_id = e.get("from")
        to_id = e.get("to")
        if from_id not in node_ids or to_id not in node_ids:
            return False
            
    return True


def compare_snapshot_before_after(before: GCSnapshot, after: GCSnapshot) -> Dict[str, Any]:
    """
    Compares two GCSnapshots and returns difference metrics (nodes/edges count change, etc.).
    """
    before_nodes = {n["id"]: n for n in before.nodes}
    after_nodes = {n["id"]: n for n in after.nodes}
    
    added_nodes = [n_id for n_id in after_nodes if n_id not in before_nodes]
    removed_nodes = [n_id for n_id in before_nodes if n_id not in after_nodes]
    
    before_edges = set((e["from"], e["to"]) for e in before.edges)
    after_edges = set((e["from"], e["to"]) for e in after.edges)
    
    added_edges = [pair for pair in after_edges if pair not in before_edges]
    removed_edges = [pair for pair in before_edges if pair not in after_edges]
    
    return {
        "nodes_before_count": len(before.nodes),
        "nodes_after_count": len(after.nodes),
        "edges_before_count": len(before.edges),
        "edges_after_count": len(after.edges),
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "added_edges": added_edges,
        "removed_edges": removed_edges,
        "node_count_delta": len(after.nodes) - len(before.nodes),
        "edge_count_delta": len(after.edges) - len(before.edges)
    }


def graph_arrays_to_wavefront_state(arrays: GraphKernelArrays) -> Any:
    """
    Converts GraphKernelArrays to a WavefrontState.
    """
    from sol_wavefront_propagator import initialize_wavefront_state
    return initialize_wavefront_state(arrays)

def wavefront_state_to_graph_arrays(state: Any) -> GraphKernelArrays:
    """
    Converts a WavefrontState back to a GraphKernelArrays.
    """
    node_ids = state.node_ids
    u = state.u
    v = state.v
    
    import copy
    edge_from_idx = copy.deepcopy(state.metadata["edge_from_idx"])
    edge_to_idx = copy.deepcopy(state.metadata["edge_to_idx"])
    edge_conductance = copy.deepcopy(state.metadata["edge_conductance"])
    semantic_mass = copy.deepcopy(state.metadata["semantic_mass"])
    
    edge_w0 = copy.deepcopy(state.metadata.get("edge_w0", [1.0] * len(edge_from_idx)))
    edge_flux = copy.deepcopy(state.metadata.get("edge_flux", [0.0] * len(edge_from_idx)))
    pressure = copy.deepcopy(state.metadata.get("pressure", [0.0] * len(node_ids)))
    csr = copy.deepcopy(state.metadata.get("csr"))
    
    if HAS_NUMPY:
        return GraphKernelArrays(
            node_ids=node_ids,
            rho=np.array(u, dtype=np.float64),
            psi=np.array(v, dtype=np.float64),
            pressure=np.array(pressure, dtype=np.float64),
            semantic_mass=np.array(semantic_mass, dtype=np.float64),
            edge_from_idx=np.array(edge_from_idx, dtype=np.int32),
            edge_to_idx=np.array(edge_to_idx, dtype=np.int32),
            edge_w0=np.array(edge_w0, dtype=np.float64),
            edge_conductance=np.array(edge_conductance, dtype=np.float64),
            edge_flux=np.array(edge_flux, dtype=np.float64),
            csr=csr
        )
        
    return GraphKernelArrays(
        node_ids=node_ids,
        rho=list(u),
        psi=list(v),
        pressure=pressure,
        semantic_mass=semantic_mass,
        edge_from_idx=edge_from_idx,
        edge_to_idx=edge_to_idx,
        edge_w0=edge_w0,
        edge_conductance=edge_conductance,
        edge_flux=edge_flux,
        csr=csr
    )

def run_shadow_wavefront_steps(arrays: GraphKernelArrays, steps: int, config: Any) -> Any:
    """
    Runs wavefront steps on a copy of GraphKernelArrays without mutating the original.
    """
    import copy
    import hashlib
    # Avoid mutating input arrays
    cloned_arrays = copy.deepcopy(arrays)
    
    from sol_wavefront_propagator import (
        initialize_wavefront_state,
        propagate_wavefront_step,
        compute_wavefront_energy,
        WavefrontPropagationStep,
        WavefrontPropagationReport
    )
    from sol_waveguide_boundary import apply_pml_absorption, measure_boundary_reflection
    
    state = initialize_wavefront_state(cloned_arrays)
    initial_energy = compute_wavefront_energy(state)
    
    step_reports = []
    
    for i in range(steps):
        state = propagate_wavefront_step(state, config)
        
        # Apply PML boundary absorption if pml_state is present in config
        if hasattr(config, "pml_state") and config.pml_state is not None:
            state = apply_pml_absorption(state, config.pml_state)
            
        energy = compute_wavefront_energy(state)
        
        state_str = f"{state.t}_{energy}"
        state_hash = "sha256_" + hashlib.sha256(state_str.encode('utf-8')).hexdigest()[:8]
        
        step_reports.append(WavefrontPropagationStep(
            step_index=i + 1,
            t=state.t,
            energy=energy,
            state_hash=state_hash
        ))
        
    final_energy = compute_wavefront_energy(state)
    stable = final_energy <= 1.1 * initial_energy
    
    # Calculate boundary reflection score if PML is configured
    reflection_score = 0.0
    if hasattr(config, "pml_state") and config.pml_state is not None:
        reflection_score = measure_boundary_reflection(
            initialize_wavefront_state(cloned_arrays),
            state,
            config.pml_state
        )
        
    report_id = f"RPT_WF_SHADOW_{int(state.t * 1000)}"
    
    # Setup gate checking
    errors = []
    checked_gates = {}
    
    arrays_ok = len(cloned_arrays.node_ids) > 0
    checked_gates["graph_arrays_valid"] = arrays_ok
    if not arrays_ok:
        errors.append("Gate failed: graph arrays are invalid or empty.")
        
    state_ok = len(state.u) == len(state.node_ids)
    checked_gates["wavefront_state_valid"] = state_ok
    if not state_ok:
        errors.append("Gate failed: wavefront state is invalid.")
        
    pml_present = getattr(config, "pml_profile", None) is not None
    checked_gates["pml_profile_present"] = pml_present
    if not pml_present:
        errors.append("Gate failed: PML profile is missing.")
        
    pml_cells_ok = False
    if hasattr(config, "pml_state") and config.pml_state is not None:
        pml_cells = config.pml_state.config.pml_cells
        grid_size = config.pml_state.config.grid_size
        pml_cells_ok = 0 < pml_cells <= grid_size // 2
    checked_gates["pml_cells_within_bounds"] = pml_cells_ok
    if not pml_cells_ok:
        errors.append("Gate failed: PML cells out of bounds.")
        
    energy_ok = initial_energy >= 0.0 and final_energy >= 0.0
    checked_gates["energy_non_negative"] = energy_ok
    if not energy_ok:
        errors.append("Gate failed: negative wavefront energy.")
        
    refl_ok = reflection_score is not None and 0.0 <= reflection_score <= 1.0
    checked_gates["boundary_reflection_measured"] = refl_ok
    if not refl_ok:
        errors.append("Gate failed: reflection was not measured.")
        
    stable_ok = stable
    checked_gates["propagation_stable"] = stable_ok
    if not stable_ok:
        errors.append("Gate failed: propagation is unstable.")
        
    dry_run = getattr(config, "dry_run", True)
    checked_gates["shadow_mode_required_by_default"] = dry_run
    if not dry_run:
        errors.append("Gate failed: shadow mode required by default.")
        
    live_stepper_replaced = getattr(config, "live_stepper_replaced", False)
    checked_gates["no_live_stepper_replacement_without_promotion"] = not live_stepper_replaced
    if live_stepper_replaced:
        errors.append("Gate failed: live stepper replacement not permitted.")
        
    passed_gates = len(errors) == 0
    from sol_wideword_instruction import InstructionGateReport
    gate_report = InstructionGateReport(passed=passed_gates, checked_gates=checked_gates, errors=errors)
    
    ev_str = f"{report_id}_{passed_gates}_{stable}"
    repro_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
    
    report = WavefrontPropagationReport(
        report_id=report_id,
        steps=step_reports,
        initial_energy=initial_energy,
        final_energy=final_energy,
        stable=stable,
        passed_gates=passed_gates,
        gate_report=gate_report,
        reproducibility_hash=repro_hash,
        metadata={
            "reflection_score": reflection_score,
            "node_count": len(state.node_ids),
            "edge_count": len(cloned_arrays.edge_from_idx),
            "step_count": steps,
            "pml_cells": config.pml_state.config.pml_cells if (hasattr(config, "pml_state") and config.pml_state is not None) else 0
        }
    )
    return report



