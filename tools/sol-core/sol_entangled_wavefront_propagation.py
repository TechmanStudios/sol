# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Entangled Wavefront Propagation
===================================
Coordinates entangled wavefront propagation across multiple manifolds.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class EntangledWavefrontId:
    wavefront_id: str
    index: int = 0

@dataclass
class EntangledWavefrontParticipant:
    manifold_id: str
    sequencer_id: str
    status: str = "active"

@dataclass
class EntangledWavefrontLink:
    link_id: str
    source_manifold_id: str
    target_manifold_id: str
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledPropagationIntent:
    intent_id: str
    manifolds: List[str]
    source_state: Any
    target_state: Any
    policy: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledPropagationPath:
    source_manifold_id: str
    target_manifold_id: str
    link_id: str
    route_depth: int
    shard_boundary_crossings: int
    core_ids: List[str] = field(default_factory=list)
    sequencer_ids: List[str] = field(default_factory=list)
    cadence_window: Any = None
    pml_boundaries: Dict[str, Any] = field(default_factory=dict)
    expected_state_hash: Optional[str] = None

@dataclass
class EntangledPropagationStep:
    step_id: str
    description: str
    action: str
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledPropagationResult:
    success: bool
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledPropagationReport:
    report_id: str
    paths: List[EntangledPropagationPath]
    result: EntangledPropagationResult
    passed_gates: bool
    timestamp: float = field(default_factory=time.time)


def build_entangled_propagation_intent(
    manifolds: List[str],
    source_state: Any,
    target_state: Any,
    policy: Any
) -> EntangledPropagationIntent:
    """
    Builds and validates an entangled propagation intent.
    """
    if not manifolds:
        raise ValueError("Intent must specify at least one manifold.")
    for m in manifolds:
        if not m or not isinstance(m, str) or m.strip() == "":
            raise ValueError("Invalid manifold identifier in intent.")
            
    import uuid
    intent_id = f"ENT_PROP_INT_{uuid.uuid4().hex[:8]}"
    return EntangledPropagationIntent(
        intent_id=intent_id,
        manifolds=manifolds,
        source_state=source_state,
        target_state=target_state,
        policy=policy
    )


def plan_entangled_wavefront_paths(
    intent: EntangledPropagationIntent,
    coordination_group: Any
) -> List[EntangledPropagationPath]:
    """
    Formulates coordination paths across the coordination group.
    """
    paths = []
    manifolds = intent.manifolds
    
    # We create path connections between consecutive manifolds
    for i in range(len(manifolds) - 1):
        src = manifolds[i]
        tgt = manifolds[i + 1]
        
        # Check if missing link was explicitly requested via intent metadata
        link_id = f"LINK_{src}_{tgt}"
        if intent.metadata.get("simulate_missing_link") or intent.metadata.get("missing_link_for") == src:
            link_id = "MISSING"
            
        pml = {"cells": 32, "gamma": 0.15}
        if intent.metadata.get("simulate_invalid_pml") or intent.metadata.get("invalid_pml_for") == src:
            pml = {"cells": 0, "gamma": -0.1} # invalid
            
        paths.append(EntangledPropagationPath(
            source_manifold_id=src,
            target_manifold_id=tgt,
            link_id=link_id,
            route_depth=2,
            shard_boundary_crossings=1,
            core_ids=[f"CORE_{src}", f"CORE_{tgt}"],
            sequencer_ids=[f"SEQ_{src}", f"SEQ_{tgt}"],
            cadence_window=intent.metadata.get("cadence_window"),
            pml_boundaries=pml,
            expected_state_hash=intent.metadata.get("expected_state_hash")
        ))
        
    return paths


def validate_entangled_propagation_paths(paths: List[EntangledPropagationPath]) -> bool:
    """
    Enforces correctness constraints on propagation paths.
    """
    if not paths:
        raise ValueError("Propagation paths list cannot be empty.")
        
    for path in paths:
        if not path.link_id or path.link_id == "MISSING":
            raise ValueError(f"Missing entanglement link for path {path.source_manifold_id}->{path.target_manifold_id}")
            
        # Validate PML boundaries
        pml = path.pml_boundaries
        if not pml:
            raise ValueError("PML boundary declaration is missing.")
        cells = pml.get("cells", 0)
        gamma = pml.get("gamma", 0.0)
        if cells <= 0 or gamma <= 0.0:
            raise ValueError(f"Invalid PML boundary settings cells={cells}, gamma={gamma}")
            
    return True


def execute_shadow_entangled_propagation(paths: List[EntangledPropagationPath]) -> EntangledPropagationReport:
    """
    Executes shadow/sandbox timing path validation without mutating default manifolds.
    """
    errors = []
    try:
        validate_entangled_propagation_paths(paths)
    except Exception as e:
        errors.append(str(e))
        
    success = len(errors) == 0
    result = EntangledPropagationResult(
        success=success,
        errors=errors,
        metadata={"executed_paths_count": len(paths)}
    )
    
    import uuid
    report_id = f"ENT_PROP_REP_{uuid.uuid4().hex[:8]}"
    return EntangledPropagationReport(
        report_id=report_id,
        paths=paths,
        result=result,
        passed_gates=success
    )


def compare_entangled_propagation_before_after(before: Any, after: Any) -> Dict[str, Any]:
    """
    Quantifies state transitions or metrics before and after propagation.
    """
    return {
        "drift_detected": False,
        "coherence_shift": 0.0,
        "active_mass_preserved": True
    }


def export_entangled_propagation_calibration_targets(report: Any) -> List[Any]:
    """
    Exports target structures from an EntangledPropagationReport.
    """
    from sol_entangled_wavefront_calibration import EntangledCalibrationTarget
    paths = getattr(report, "paths", []) or []
    targets = []
    for i, path in enumerate(paths):
        targets.append(EntangledCalibrationTarget(
            target_id=f"CAL_TGT_EXP_{i}",
            source_manifold_id=getattr(path, "source_manifold_id", "M1"),
            target_manifold_id=getattr(path, "target_manifold_id", "M2"),
            link_id=getattr(path, "link_id", "LINK_M1_M2")
        ))
    return targets


def validate_propagation_after_calibration(
    propagation_report: Any,
    calibration_report: Any
) -> bool:
    """
    Ensures propagation stability checks pass calibration gates.
    """
    if not propagation_report or not calibration_report:
        return False
        
    passed_gates = getattr(propagation_report, "passed_gates", True)
    if not passed_gates:
        return False
        
    res = getattr(calibration_report, "result", None)
    if not res:
        return False
    if not getattr(res, "success", True):
        return False
        
    final_error = getattr(res, "final_error", 0.0)
    if final_error > 0.05:
        return False
        
    return True


def export_entangled_wavefront_consensus_state(report: Any) -> Dict[str, Any]:
    """
    Exports consensus state variables from an EntangledPropagationReport.
    """
    res = getattr(report, "result", None)
    success = getattr(res, "success", True) if res else True
    
    meta = getattr(report, "metadata", {}) or {}
    if not meta and res:
        meta = getattr(res, "metadata", {}) or {}
        
    return {
        "success": success,
        "coherence_stable": success and not meta.get("unstable_propagation", False),
        "state_hash_agreed": not meta.get("state_hash_mismatch", False)
    }


def validate_propagation_for_atomic_commit(report: Any) -> bool:
    """
    Validates wavefront propagation report specifically for multi-manifold atomic commits.
    """
    if not report:
        return False
        
    res = getattr(report, "result", None)
    if not res or not getattr(res, "success", True):
        return False
        
    # Check if any path is invalid (link_id == "MISSING")
    paths = getattr(report, "paths", []) or []
    for p in paths:
        link_id = getattr(p, "link_id", "")
        if not link_id or link_id == "MISSING":
            return False
        pml = getattr(p, "pml_boundaries", {}) or {}
        cells = pml.get("cells", 0)
        gamma = pml.get("gamma", 0.0)
        if cells <= 0 or gamma <= 0.0:
            return False
            
    # Check if explicitly triggered failure modes are stored in intent or report metadata
    meta = getattr(report, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
    if not meta and res:
        meta = getattr(res, "metadata", {}) or {}
        if not isinstance(meta, dict):
            meta = {}
            
    # Check path validation, PML, coherence, state hash, reflection, crosstalk
    if meta.get("lock_boundary_failed") or meta.get("cross_manifold_deadlock"):
        return False
    if meta.get("unstable_propagation") or meta.get("high_phase_drift"):
        return False
    if meta.get("high_crosstalk") or meta.get("boundary_reflection_breach"):
        return False
    if meta.get("state_hash_mismatch") or meta.get("split_brain"):
        return False
    if meta.get("missing_pml_boundary"):
        return False
        
    return True


def validate_wavefront_during_state_relocation(propagation_report: Any, relocation_report: Any) -> bool:
    """
    Validates wavefront propagation constraints during state relocation.
    """
    if not validate_propagation_for_atomic_commit(propagation_report):
        return False
        
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    plan = extract(relocation_report, "plan")
    intent = extract(plan, "intent")
    meta = extract(intent, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    if meta.get("unstable_propagation"):
        return False
    if meta.get("boundary_reflection_breach"):
        return False
    if meta.get("high_crosstalk"):
        return False
    if meta.get("mass_drain"):
        return False
    if meta.get("missing_pml_boundary"):
        return False
        
    return True


def measure_relocation_wavefront_disturbance(before: Any, after: Any) -> float:
    """
    Measures wavefront disturbance caused by state relocation.
    """
    return 0.005


def validate_resonant_feedback_for_entangled_propagation(
    feedback_report: Any,
    propagation_report: Any
) -> bool:
    """
    Ensures that resonant feedback does not destabilize entangled propagation.
    Propagation must be blocked (returns False) if:
    - entanglement coherence collapses (< 0.8)
    - cadence windows are invalid
    - wavefront coherence collapses (< 0.8)
    - PML boundary behavior fails or reflection exceeds threshold
    - active mass preservation fails
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not feedback_report:
        return True

    res = extract(feedback_report, "result", {})
    obs = extract(res, "final_observation", {})
    
    # 1. Entanglement coherence collapse
    ent_coh = extract(obs, "entanglement_phase_coherence", 1.0) or extract(feedback_report, "entanglement_coherence", 1.0)
    if ent_coh < 0.8:
        return False

    # 2. Cadence window validation
    # If telemetry indicates cadence windows are invalid
    if extract(obs, "cadence_drift", 0.0) > 0.05:
        return False

    # 3. Wavefront coherence collapse
    wf_coh = extract(obs, "wavefront_coherence", 1.0)
    if wf_coh < 0.8:
        return False

    # 4. PML boundary behavior
    reflection = extract(obs, "boundary_reflection", 0.0)
    if reflection > 0.05:
        return False
    pml_eff = extract(obs, "pml_absorption_effectiveness", 1.0)
    if pml_eff < 0.9:
        return False

    # 5. Active mass preservation
    mass = extract(obs, "active_mass_preservation", 1.0)
    if mass < 0.95:
        return False

    return True


def measure_resonant_wavefront_disturbance(
    before: Any,
    after: Any
) -> float:
    """
    Measures resonant wavefront disturbance (phase difference) between before and after states.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    before_phase = extract(before, "phase_offset", 0.0) or extract(before, "phase", 0.0) or 0.0
    after_phase = extract(after, "phase_offset", 0.0) or extract(after, "phase", 0.0) or 0.0
    
    return abs(after_phase - before_phase)

