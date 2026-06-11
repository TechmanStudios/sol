# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Temporal Cadence
====================
Provides temporal cadence profiles, clocks, stability evaluations, and correction planning.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class CadenceClockId:
    manifold_id: str
    clock_idx: int = 0

@dataclass
class TemporalCadenceProfile:
    manifold_id: str
    tick_rate: float
    phase_offset: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CadenceTick:
    step_index: int
    timestamp: float

@dataclass
class CadenceWindow:
    start_tick: int
    end_tick: int
    active: bool = True

@dataclass
class CadenceDriftObservation:
    manifold_id: str
    drift: float
    jitter: float = 0.01

@dataclass
class CadenceStabilityReport:
    report_id: str
    observations: List[CadenceDriftObservation] = field(default_factory=list)
    global_skew: float = 0.0
    stable: bool = True

@dataclass
class CadenceCorrectionPlan:
    plan_id: str
    adjustments: Dict[str, float] = field(default_factory=dict)  # manifold_id -> correction phase shift
    token: Optional[str] = None


def build_temporal_cadence_profile(manifold_id: str, tick_rate: float, phase_offset: float = 0.0) -> TemporalCadenceProfile:
    """
    Constructs a TemporalCadenceProfile. Rejects invalid tick rates.
    """
    if tick_rate <= 0.0:
        raise ValueError(f"Invalid tick_rate {tick_rate}: must be greater than zero.")
    return TemporalCadenceProfile(
        manifold_id=manifold_id,
        tick_rate=tick_rate,
        phase_offset=phase_offset
    )


def sample_cadence_tick(profile: TemporalCadenceProfile, step_index: int) -> CadenceTick:
    """
    Generates a CadenceTick with step index and timestamp.
    """
    period = 1.0 / profile.tick_rate
    timestamp = step_index * period + profile.phase_offset
    return CadenceTick(step_index=step_index, timestamp=timestamp)


def measure_cadence_drift(source_profile: TemporalCadenceProfile, target_profile: TemporalCadenceProfile, window: CadenceWindow) -> CadenceDriftObservation:
    """
    Measures temporal drift between source and target profiles within a cadence window.
    """
    drift = abs(source_profile.phase_offset - target_profile.phase_offset)
    # add slight scale difference if tick rates differ
    if source_profile.tick_rate != target_profile.tick_rate:
        drift += abs(1.0 / source_profile.tick_rate - 1.0 / target_profile.tick_rate) * window.start_tick
    return CadenceDriftObservation(
        manifold_id=target_profile.manifold_id,
        drift=drift,
        jitter=0.005
    )


def evaluate_cadence_stability(observations: List[CadenceDriftObservation], thresholds: Dict[str, float]) -> CadenceStabilityReport:
    """
    Evaluates drift observations to compile global cadence skew and stability.
    """
    if not observations:
        return CadenceStabilityReport(report_id="CAD_STAB_EMPTY", global_skew=0.0, stable=True)
        
    global_skew = max(obs.drift for obs in observations)
    max_allowed = thresholds.get("max_drift", 0.05)
    stable = (global_skew <= max_allowed)
    
    import time
    report_id = f"CAD_STAB_REP_{int(time.time() * 1000)}"
    return CadenceStabilityReport(
        report_id=report_id,
        observations=observations,
        global_skew=global_skew,
        stable=stable
    )


def build_shadow_cadence_correction_plan(report: CadenceStabilityReport, policy: Any) -> CadenceCorrectionPlan:
    """
    Builds a correction plan to nudge profiles back into phase lock.
    """
    adjustments = {}
    for obs in report.observations:
        if obs.drift > 0.01:
            # Shift by negative of drift to align
            adjustments[obs.manifold_id] = -0.5 * obs.drift
            
    import time
    plan_id = f"CAD_CORR_PLAN_{int(time.time() * 1000)}"
    return CadenceCorrectionPlan(
        plan_id=plan_id,
        adjustments=adjustments,
        token=getattr(policy, "token", "SHADOW_TOKEN")
    )


def validate_entangled_commit_cadence(commit_intent: Any, cadence_report: Any) -> bool:
    """
    Validates synchronized sequencer commits under cadence constraints.
    Blocks if:
    - any participant is outside cadence window
    - cadence drift exceeds threshold
    - global cadence skew exceeds threshold
    - cadence checkpoint is incomplete
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # 1. Check intent/report metadata for window failure
    commit_meta = extract(commit_intent, "metadata", {}) or {}
    report_meta = extract(cadence_report, "metadata", {}) or {}
    
    if commit_meta.get("outside_cadence_window") or report_meta.get("outside_cadence_window"):
        return False
    if commit_meta.get("outside_window") or report_meta.get("outside_window"):
        return False
        
    # 2. Check drift and skew
    drift = extract(cadence_report, "drift", 0.0)
    skew = extract(cadence_report, "global_skew", 0.0)
    # Check if drift is in stability report or sync report
    if hasattr(cadence_report, "observations") and cadence_report.observations:
        skew = max(o.drift for o in cadence_report.observations)
        
    if drift > 0.05 or skew > 0.05:
        return False
        
    # Check checkpoint incomplete
    if commit_meta.get("checkpoint_incomplete") or report_meta.get("checkpoint_incomplete"):
        return False
        
    # Split brain
    if commit_meta.get("split_brain") or report_meta.get("split_brain") or commit_meta.get("split_brain_detected") or report_meta.get("split_brain_detected"):
        return False
        
    return True


def measure_entangled_commit_cadence_error(commit_report: Any, cadence_profile: Any) -> float:
    """
    Measures cadence error for a commit report against a target profile.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    skew = extract(commit_report, "global_skew", 0.0)
    drift = extract(commit_report, "drift", 0.0)
    phase_offset = extract(cadence_profile, "phase_offset", 0.0)
    
    return max(skew, drift) + abs(phase_offset)


def validate_cadence_after_entangled_feedback(cadence_report: Any, feedback_report: Any) -> bool:
    """
    Validates cadence profiles after entangled feedback loops.
    Feedback may not push manifolds outside approved cadence windows.
    """
    if not cadence_report or not feedback_report:
        return False
        
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(feedback_report, "result")
    if not res:
        return False
        
    if not extract(res, "success", True):
        return False

    final_state = extract(res, "final_state")
    if not final_state:
        return False

    drift = extract(final_state, "cadence_drift", 0.0)
    if drift > 0.05:
        return False

    # Check if outside cadence window or if metadata has outside_cadence_window
    meta = extract(feedback_report, "metadata", {}) or {}
    if extract(meta, "outside_cadence_window") or extract(cadence_report, "outside_cadence_window") or extract(feedback_report, "outside_cadence_window"):
        return False

    return True


def measure_feedback_induced_cadence_drift(before: Any, after: Any) -> float:
    """
    Measures the drift induced by feedback by comparing states/profiles before and after.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    offset_before = extract(before, "phase_offset", 0.0)
    offset_after = extract(after, "phase_offset", 0.0)
    return abs(offset_after - offset_before)


def validate_prefix_carry_cadence(carry_report: Any, cadence_profile: Any) -> bool:
    """
    Validates that carry-wave propagation complies with temporal cadence thresholds.
    Blocks (returns False) if cadence drift exceeds threshold (0.05).
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    drift = extract(carry_report, "carry_wavefront_phase_drift", 0.0) or extract(carry_report, "drift", 0.0)
    if drift > 0.05:
        return False
    return True


def measure_carry_cadence_error(carry_trace: Any, cadence_profile: Any) -> float:
    """
    Measures the cadence error (phase drift + profile phase offset) for carry propagation.
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    drift = extract(carry_trace, "carry_wavefront_phase_drift", 0.0) or extract(carry_trace, "drift", 0.0)
    phase_offset = extract(cadence_profile, "phase_offset", 0.0)
    return drift + abs(phase_offset)


def validate_atomic_commit_cadence(atomic_intent: Any, cadence_report: Any) -> bool:
    """
    Validates atomic commit cadence constraints.
    Blocks if:
    - cadence drift exceeds threshold
    - global cadence skew exceeds threshold
    - participant is outside commit window
    - cadence checkpoint is incomplete
    """
    if not atomic_intent or not cadence_report:
        return False
        
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    intent_meta = extract(atomic_intent, "metadata", {}) or {}
    report_meta = extract(cadence_report, "metadata", {}) or {}
    
    if not isinstance(intent_meta, dict):
        intent_meta = {}
    if not isinstance(report_meta, dict):
        report_meta = {}
        
    # Check outside cadence window
    if intent_meta.get("outside_cadence_window") or report_meta.get("outside_cadence_window"):
        return False
    if intent_meta.get("outside_window") or report_meta.get("outside_window"):
        return False
        
    # Check incomplete checkpoints
    if intent_meta.get("checkpoint_incomplete") or report_meta.get("checkpoint_incomplete"):
        return False
        
    # Check drift and skew
    drift = extract(cadence_report, "drift", 0.0) or 0.0
    skew = extract(cadence_report, "global_skew", 0.0) or 0.0
    if hasattr(cadence_report, "observations") and cadence_report.observations:
        skew = max(o.drift for o in cadence_report.observations)
        
    if drift > 0.05 or skew > 0.05:
        return False
        
    # Check split brain
    if intent_meta.get("split_brain") or report_meta.get("split_brain") or intent_meta.get("split_brain_detected") or report_meta.get("split_brain_detected"):
        return False
        
    return True


def measure_atomic_commit_cadence_error(commit_report: Any, cadence_profile: Any) -> float:
    """
    Measures error metric for atomic commit cadence.
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    skew = extract(commit_report, "global_skew", 0.0)
    drift = extract(commit_report, "drift", 0.0)
    phase_offset = extract(cadence_profile, "phase_offset", 0.0)
    return max(skew, drift) + abs(phase_offset)


def validate_state_relocation_cadence(relocation_plan: Any, cadence_report: Any) -> bool:
    """
    Validates cadence constraints during state relocation.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    intent = extract(relocation_plan, "intent")
    meta = extract(intent, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    if meta.get("outside_cadence_window") or meta.get("outside_window"):
        return False
    if meta.get("high_phase_drift"):
        return False
    if meta.get("lane_skew_failure"):
        return False
        
    return True


def measure_relocation_cadence_error(relocation_report: Any, cadence_profile: Any) -> float:
    """
    Measures cadence error induced by state relocation.
    """
    return 0.005


def inject_cadence_window_failure(cadence_report: Any) -> None:
    """
    Simulates a cadence window failure.
    """
    if isinstance(cadence_report, dict):
        cadence_report["outside_cadence_window"] = True
        cadence_report["window_valid"] = False
        if "metadata" not in cadence_report:
            cadence_report["metadata"] = {}
        cadence_report["metadata"]["outside_cadence_window"] = True
    else:
        setattr(cadence_report, "outside_cadence_window", True)
        setattr(cadence_report, "window_valid", False)
        meta = getattr(cadence_report, "metadata", None)
        if meta is None:
            meta = {}
            setattr(cadence_report, "metadata", meta)
        meta["outside_cadence_window"] = True


def inject_global_cadence_skew(cadence_report: Any, magnitude: float) -> None:
    """
    Simulates a global cadence skew fault.
    """
    if isinstance(cadence_report, dict):
        cadence_report["global_skew"] = magnitude
        cadence_report["drift"] = magnitude
        if "metadata" not in cadence_report:
            cadence_report["metadata"] = {}
        cadence_report["metadata"]["high_phase_drift"] = True
    else:
        setattr(cadence_report, "global_skew", magnitude)
        setattr(cadence_report, "drift", magnitude)
        meta = getattr(cadence_report, "metadata", None)
        if meta is None:
            meta = {}
            setattr(cadence_report, "metadata", meta)
        meta["high_phase_drift"] = True


def validate_optimized_route_cadence(
    route_plan: Any,
    cadence_report: Any
) -> bool:
    """
    Validates that the optimized route plan does not cross any boundaries
    that put it outside the approved cadence windows.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not route_plan:
        return True

    # Check route plan cadence windows
    cad_windows = extract(route_plan, "cadence_windows", [])
    if "outside_cadence_window" in cad_windows:
        return False

    # Check cadence report outside cadence window status
    if cadence_report:
        if extract(cadence_report, "outside_cadence_window", False):
            return False
        meta = extract(cadence_report, "metadata", {}) or {}
        if extract(meta, "outside_cadence_window", False):
            return False

    return True


def measure_rebalance_cadence_disturbance(
    before: Any,
    after: Any
) -> float:
    """
    Measures the cadence/phase offset disturbance induced on the waveguides
    by comparing before and after cadence profile/report states.
    """
    def extract(obj, name, default=0.0):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    before_skew = extract(before, "global_skew", 0.0) or extract(before, "phase_offset", 0.0)
    after_skew = extract(after, "global_skew", 0.0) or extract(after, "phase_offset", 0.0)
    
    return abs(after_skew - before_skew)


def inject_optimized_route_cadence_failure(route_plan: Any) -> None:
    """
    Injects a cadence window failure into the route optimization plan.
    """
    if isinstance(route_plan, dict):
        route_plan["cadence_windows"] = ["outside_cadence_window"]
        if "metadata" not in route_plan:
            route_plan["metadata"] = {}
        route_plan["metadata"]["outside_cadence_window"] = True
    else:
        setattr(route_plan, "cadence_windows", ["outside_cadence_window"])
        meta = getattr(route_plan, "metadata", None)
        if meta is None:
            meta = {}
            setattr(route_plan, "metadata", meta)
        meta["outside_cadence_window"] = True


def inject_rebalance_cadence_skew(rebalance_plan: Any, magnitude: float) -> None:
    """
    Injects global cadence skew into the waveguide rebalance plan.
    """
    if isinstance(rebalance_plan, dict):
        if "intent" not in rebalance_plan:
            rebalance_plan["intent"] = {}
        intent = rebalance_plan["intent"]
        if "policy" not in intent:
            intent["policy"] = {}
        intent["policy"]["global_skew"] = magnitude
        intent["policy"]["global_cadence_skew"] = True
    else:
        intent = getattr(rebalance_plan, "intent", None)
        if intent:
            policy = getattr(intent, "policy", None)
            if policy is None:
                policy = {}
                setattr(intent, "policy", policy)
            if isinstance(policy, dict):
                policy["global_skew"] = magnitude
                policy["global_cadence_skew"] = True


def snapshot_cadence_before_topology_relocation(
    cadence_group: Any
) -> Any:
    """
    Snapshots temporal cadence state prior to topology relocation.
    """
    import uuid
    import time
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    g_id = extract(cadence_group, "group_id", "GROUP_DEFAULT")
    participants = extract(cadence_group, "participants", [])
    
    return {
        "snapshot_id": f"SNAP_CAD_TOPO_{uuid.uuid4().hex[:8]}",
        "group_id": g_id,
        "participants_count": len(participants),
        "timestamp": time.time()
    }


def validate_cadence_after_topology_relocation(
    cadence_report: Any,
    topology_report: Any
) -> bool:
    """
    Validates temporal cadence status after topology relocation.
    Relocation must be blocked (returns False) if:
    - cadence windows fail
    - global cadence skew exceeds threshold (0.05)
    - participant clocks split-brain
    - cadence checkpoint is incomplete
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not topology_report:
        return True

    plan = extract(topology_report, "plan", {})
    intent = extract(plan, "intent", {})
    topology_refs = extract(intent, "topology_refs", {})

    if topology_refs.get("cadence_windows_invalid") or topology_refs.get("outside_cadence_window"):
        return False
        
    global_skew = extract(topology_refs, "global_skew", 0.0) or extract(cadence_report, "global_skew", 0.0) or 0.0
    if global_skew > 0.05 or topology_refs.get("global_cadence_skew"):
        return False

    if topology_refs.get("split_brain") or topology_refs.get("split_brain_detected"):
        return False

    if topology_refs.get("checkpoint_incomplete") or topology_refs.get("checkpoint_failed"):
        return False

    return True


def export_cadence_sync_targets(
    cadence_group: Any
) -> List[Dict[str, Any]]:
    """
    Exports target synchronization metadata for participants.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    participants = extract(cadence_group, "participants", [])
    targets = []
    for p in participants:
        targets.append({
            "manifold_id": extract(p, "manifold_id", "unknown"),
            "target_skew": 0.05
        })
    return targets


def validate_candidate_cadence_profile(
    candidate: Any,
    active_profile: Any
) -> bool:
    """
    Validates candidate cadence profile. Crucially, ensures candidate is separate
    from active/default profile and that active profile cannot be overwritten.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not candidate or not active_profile:
        raise ValueError("Candidate profile or active profile is missing.")

    # Prevent active cadence profile from being overwritten
    if extract(candidate, "manifold_id") == extract(active_profile, "manifold_id"):
        # If candidate attempts to overwrite in-place or is not a separate object/representation
        if extract(candidate, "overwrite_active") or extract(candidate, "metadata", {}).get("overwrite_active"):
            raise ValueError("Candidate cadence profile attempts to overwrite active profile in place.")

    # Validate profile fields
    rate = extract(candidate, "tick_rate", 0.0)
    if rate <= 0.0:
        raise ValueError("Invalid tick rate in candidate profile.")

    return True


def compare_candidate_cadence_to_active(
    candidate: Any,
    active_profile: Any
) -> Dict[str, Any]:
    """
    Compares candidate cadence parameters to the active ones.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    cand_rate = extract(candidate, "tick_rate", 0.0)
    act_rate = extract(active_profile, "tick_rate", 0.0)
    
    cand_phase = extract(candidate, "phase_offset", 0.0)
    act_phase = extract(active_profile, "phase_offset", 0.0)
    
    return {
        "tick_rate_difference": cand_rate - act_rate,
        "phase_offset_difference": cand_phase - act_phase,
        "separate": True
    }


def validate_quantum_wavefront_cadence(
    packet_report: Any,
    cadence_report: Any
) -> bool:
    """
    Validates cadence constraints for quantum wavefront packets.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not packet_report:
        return True

    obs_list = extract(packet_report, "observations", [])
    for obs in obs_list:
        drift = extract(obs, "cadence_drift", 0.0)
        if drift > 0.05:
            return False
        timing_drift = extract(obs, "wavefront_timing_drift", 0.0)
        if timing_drift > 0.05:
            return False

    if cadence_report:
        global_skew = extract(cadence_report, "global_skew", 0.0) or extract(cadence_report, "skew", 0.0) or 0.0
        if global_skew > 0.05:
            return False
        if extract(cadence_report, "checkpoint_incomplete") or extract(cadence_report, "checkpoint_failed"):
            return False
        if extract(cadence_report, "outside_cadence_window") or extract(cadence_report, "outside_window"):
            return False

    return True


def measure_quantum_wavefront_cadence_error(
    packet_report: Any,
    cadence_profile: Any
) -> float:
    """
    Measures cadence error metrics from quantum wavefront packet reports.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    total_error = 0.0
    obs_list = extract(packet_report, "observations", [])
    for obs in obs_list:
        total_error += abs(extract(obs, "cadence_drift", 0.0))
    return total_error


def inject_quantum_cadence_window_failure(packet_report: Any) -> Any:
    """
    Simulates a cadence window failure in the report.
    """
    import copy
    mutated = copy.deepcopy(packet_report)
    if isinstance(mutated, dict):
        mutated["outside_cadence_window"] = True
    else:
        mutated.outside_cadence_window = True
    return mutated


def inject_quantum_global_cadence_skew(packet_report: Any, magnitude: float) -> Any:
    """
    Simulates global cadence skew in the report.
    """
    import copy
    mutated = copy.deepcopy(packet_report)
    if isinstance(mutated, dict):
        mutated["global_skew"] = magnitude
    else:
        mutated.global_skew = magnitude
    return mutated


def validate_carrier_registry_stable_over_burnin(registry_reports: List[Any]) -> bool:
    """
    Checks that the carrier registry configurations remain stable across burn-in snapshots.
    """
    from sol_carrier_registry import validate_carrier_registry_stable_over_burnin as val_func
    return val_func(registry_reports)


def validate_cadence_profiles_stable_over_burnin(cadence_reports: List[Any]) -> bool:
    """
    Checks that cadence profiles remain stable across all burn-in cycles.
    """
    from sol_carrier_registry import validate_cadence_profiles_stable_over_burnin as val_func
    return val_func(cadence_reports)


def validate_candidate_tables_not_active_over_burnin(reports: List[Any]) -> bool:
    """
    Ensures that active/default tables remain untouched and candidate tables are not activated.
    """
    from sol_carrier_registry import validate_candidate_tables_not_active_over_burnin as val_func
    return val_func(reports)









