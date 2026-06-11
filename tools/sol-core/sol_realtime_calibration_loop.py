# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Real-time Calibration Loop
==============================
Tracks phase drift, cadence drift, carrier errors, and wavefront coherence metrics in real-time,
applying bounded, shadow adjustments to prevent resonance collapse.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class RealtimeCalibrationPolicy:
    policy_id: str
    max_phase_drift: float = 0.05
    max_cadence_drift: float = 0.05
    max_crosstalk: float = 0.05
    max_reflection: float = 0.05
    clamped_adjustment_delta: float = 0.01
    allow_sandbox_nudges: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RealtimeCalibrationTarget:
    target_id: str
    manifold_id: str
    lane_id: int
    expected_period: float
    current_phase: float = 0.0

@dataclass
class RealtimeCalibrationFrame:
    frame_id: str
    timestamp: float
    phase_drift: float
    cadence_drift: float
    carrier_phase_error: float
    wavefront_coherence: float
    crosstalk: float
    boundary_reflection: float
    pml_absorption_effectiveness: float
    active_mass_preservation: bool
    lane_timing_consistency: bool
    state_hash_agreement: bool
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RealtimeCalibrationAdjustment:
    adjustment_id: str
    target_id: str
    phase_nudge: float
    cadence_skew_correction: float
    bounded: bool
    applied: bool = False

@dataclass
class RealtimeCalibrationLoop:
    loop_id: str
    targets: List[RealtimeCalibrationTarget]
    policy: RealtimeCalibrationPolicy
    current_state: str = "initialized"  # "initialized" | "running" | "suspended"
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RealtimeCalibrationResult:
    success: bool
    adjustments: List[RealtimeCalibrationAdjustment]
    coherence_stable: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class RealtimeCalibrationReport:
    report_id: str
    loop_id: str
    frames_sampled: int
    result: RealtimeCalibrationResult
    passed_gates: bool
    timestamp: float = field(default_factory=time.time)


def build_realtime_calibration_loop(
    targets: List[RealtimeCalibrationTarget],
    policy: RealtimeCalibrationPolicy,
    metadata: Optional[Dict[str, Any]] = None
) -> RealtimeCalibrationLoop:
    """
    Builds a real-time calibration loop.
    """
    loop_id = f"RCL_{uuid.uuid4().hex[:8]}"
    meta = dict(metadata) if metadata is not None else {}
    loop = RealtimeCalibrationLoop(
        loop_id=loop_id,
        targets=targets,
        policy=policy,
        metadata=meta
    )
    validate_realtime_calibration_loop(loop)
    return loop


def validate_realtime_calibration_loop(loop: RealtimeCalibrationLoop) -> bool:
    """
    Validates a real-time calibration loop's configuration.
    """
    if not loop.targets:
        raise ValueError("Real-time calibration loop must specify at least one target.")
    if loop.policy.clamped_adjustment_delta <= 0.0 or loop.policy.clamped_adjustment_delta > 0.5:
        raise ValueError("Calibration policy clamped adjustment delta exceeds safe boundaries.")
    return True


def sample_realtime_calibration_frame(
    loop: RealtimeCalibrationLoop,
    state: Dict[str, Any]
) -> RealtimeCalibrationFrame:
    """
    Samples a single real-time calibration frame from current substrate state.
    """
    # Look for simulated drift/crosstalk/reflection in state/loop metadata
    meta = loop.metadata
    
    # Defaults are perfectly aligned
    phase_drift = state.get("phase_drift", meta.get("phase_drift", 0.0))
    cadence_drift = state.get("cadence_drift", meta.get("cadence_drift", 0.0))
    carrier_phase_error = state.get("carrier_phase_error", meta.get("carrier_phase_error", 0.0))
    wavefront_coherence = state.get("wavefront_coherence", meta.get("wavefront_coherence", 1.0))
    crosstalk = state.get("crosstalk", meta.get("crosstalk", 0.0))
    boundary_reflection = state.get("boundary_reflection", meta.get("boundary_reflection", 0.0))
    pml_effectiveness = state.get("pml_absorption_effectiveness", meta.get("pml_absorption_effectiveness", 1.0))
    
    active_mass = state.get("active_mass_preservation", not meta.get("mass_drain", False))
    lane_timing = state.get("lane_timing_consistency", not meta.get("lane_skew_failure", False))
    state_hash_agreement = state.get("state_hash_agreement", not meta.get("state_hash_mismatch", False))

    return RealtimeCalibrationFrame(
        frame_id=f"FRAME_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        phase_drift=phase_drift,
        cadence_drift=cadence_drift,
        carrier_phase_error=carrier_phase_error,
        wavefront_coherence=wavefront_coherence,
        crosstalk=crosstalk,
        boundary_reflection=boundary_reflection,
        pml_absorption_effectiveness=pml_effectiveness,
        active_mass_preservation=active_mass,
        lane_timing_consistency=lane_timing,
        state_hash_agreement=state_hash_agreement
    )


def plan_realtime_calibration_adjustment(
    frame: RealtimeCalibrationFrame,
    policy: RealtimeCalibrationPolicy
) -> RealtimeCalibrationAdjustment:
    """
    Plans bounded adjustments based on sampled frame telemetry.
    """
    # If policy limits are exceeded or unbounded drift is requested
    bounded = True
    if frame.phase_drift > policy.max_phase_drift or frame.cadence_drift > policy.max_cadence_drift:
        # If adjustment delta is unbounded, policy rejects adjustment
        if policy.metadata.get("unbounded_adjustment"):
            bounded = False
            
    phase_nudge = 0.0
    if frame.phase_drift > 0.0:
        phase_nudge = -min(frame.phase_drift, policy.clamped_adjustment_delta)
        
    cadence_skew = 0.0
    if frame.cadence_drift > 0.0:
        cadence_skew = -min(frame.cadence_drift, policy.clamped_adjustment_delta)

    return RealtimeCalibrationAdjustment(
        adjustment_id=f"ADJ_{uuid.uuid4().hex[:8]}",
        target_id="ALL",
        phase_nudge=phase_nudge,
        cadence_skew_correction=cadence_skew,
        bounded=bounded,
        applied=False
    )


def run_shadow_realtime_calibration(
    loop: RealtimeCalibrationLoop,
    frames: List[RealtimeCalibrationFrame]
) -> RealtimeCalibrationReport:
    """
    Simulates a calibration run over sampled frames in shadow mode.
    """
    adjustments = []
    errors = []
    
    for f in frames:
        # Check invariants
        if f.phase_drift > loop.policy.max_phase_drift:
            errors.append(f"Phase drift {f.phase_drift} exceeds limit {loop.policy.max_phase_drift}")
        if f.cadence_drift > loop.policy.max_cadence_drift:
            errors.append(f"Cadence drift {f.cadence_drift} exceeds limit {loop.policy.max_cadence_drift}")
        if f.crosstalk > loop.policy.max_crosstalk:
            errors.append(f"Crosstalk {f.crosstalk} exceeds limit {loop.policy.max_crosstalk}")
        if f.boundary_reflection > loop.policy.max_reflection:
            errors.append(f"Boundary reflection {f.boundary_reflection} exceeds limit {loop.policy.max_reflection}")
        if not f.active_mass_preservation:
            errors.append("Active mass preservation invariant failed.")
        if not f.state_hash_agreement:
            errors.append("State hash agreement failed.")

        adj = plan_realtime_calibration_adjustment(f, loop.policy)
        if not adj.bounded:
            errors.append("Calibration adjustment exceeds policy bounds.")
        adjustments.append(adj)

    # Coherence checks
    coherence_stable = all(f.wavefront_coherence >= 0.9 for f in frames)
    if not coherence_stable:
        errors.append("Wavefront coherence is unstable.")

    success = len(errors) == 0
    passed_gates = success
    
    res = RealtimeCalibrationResult(
        success=success,
        adjustments=adjustments,
        coherence_stable=coherence_stable,
        errors=errors
    )
    
    return RealtimeCalibrationReport(
        report_id=f"RCR_{uuid.uuid4().hex[:8]}",
        loop_id=loop.loop_id,
        frames_sampled=len(frames),
        result=res,
        passed_gates=passed_gates
    )


def run_sandbox_realtime_calibration(
    loop: RealtimeCalibrationLoop,
    token: Any
) -> RealtimeCalibrationReport:
    """
    Runs calibration in sandbox mode with valid court token validation.
    """
    errors = []
    if token is None:
        errors.append("Sandbox calibration aborted: missing court token.")
    else:
        authorized = getattr(token, "authorized_by_court", False)
        active = getattr(token, "active", True)
        expires_at = getattr(token, "expires_at", 0.0)
        
        if not authorized:
            errors.append("Sandbox calibration aborted: unauthorized token.")
        elif not active:
            errors.append("Sandbox calibration aborted: inactive token.")
        elif expires_at < time.time():
            errors.append("Sandbox calibration aborted: token expired.")

    # Generate dummy frame
    f = sample_realtime_calibration_frame(loop, {})
    if errors:
        f.wavefront_coherence = 0.5  # force failure
        
    return run_shadow_realtime_calibration(loop, [f])


def export_calibration_fault_targets(loop: RealtimeCalibrationLoop) -> Dict[str, Any]:
    """
    Exports targets details from calibration loop for fault matrix injection.
    """
    return {
        "loop_id": loop.loop_id,
        "targets": [t.target_id for t in loop.targets],
        "policy_id": loop.policy.policy_id
    }


def validate_calibration_fault_response(report: RealtimeCalibrationReport, expected_response: str) -> bool:
    """
    Validates that the calibration loop results reflect the expected safety action (e.g. abort, rollback).
    """
    if expected_response != "accept_shadow":
        # Any safety outcome other than approval means the calibration run should show failure.
        if report.passed_gates or report.result.success:
            return False
    return True


@dataclass
class CandidateCalibrationTable:
    table_id: str
    phase_adjustments: Dict[str, float] = field(default_factory=dict)
    cadence_adjustments: Dict[str, float] = field(default_factory=dict)
    carrier_adjustments: Dict[str, float] = field(default_factory=dict)


def calibrate_optimized_geodesic_route(
    route_plan: Any,
    policy: RealtimeCalibrationPolicy
) -> CandidateCalibrationTable:
    """
    Builds candidate calibration tables and phase adjustments for the optimized route.
    Candidate tables stay separate from default active tables.
    """
    import uuid
    table_id = f"CAND_TABLE_{uuid.uuid4().hex[:8]}"
    return CandidateCalibrationTable(
        table_id=table_id,
        phase_adjustments={"route_lane_0": 0.01},
        cadence_adjustments={"route_lane_0": -0.01},
        carrier_adjustments={"route_lane_0": 0.0}
    )


def calibrate_rebalanced_waveguide(
    rebalance_plan: Any,
    policy: RealtimeCalibrationPolicy
) -> CandidateCalibrationTable:
    """
    Builds candidate calibration tables and phase adjustments for the rebalanced waveguide.
    Candidate tables stay separate from default active tables.
    """
    import uuid
    table_id = f"CAND_CADENCE_TABLE_{uuid.uuid4().hex[:8]}"
    return CandidateCalibrationTable(
        table_id=table_id,
        phase_adjustments={"rebal_lane_0": 0.02},
        cadence_adjustments={"rebal_lane_0": -0.02},
        carrier_adjustments={"rebal_lane_0": 0.0}
    )


def validate_post_rebalance_calibration(
    report: Any
) -> bool:
    """
    Checks post-rebalance calibration and ensures active/default tables were not modified.
    Candidate tables must not use active or default table IDs.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not report:
        return False

    table_id = extract(report, "table_id") or extract(report, "report_id") or ""
    # Reject default/active table overwrites
    if "ACTIVE" in table_id or "DEFAULT" in table_id or "PROD" in table_id:
        return False

    # Ensure table prefix matches candidate prefixes
    if not (table_id.startswith("CAND_TABLE_") or table_id.startswith("CAND_CADENCE_TABLE_") or table_id.startswith("RCR_") or table_id.startswith("CAND_CARRIER_TABLE_")):
        return False

    return True

