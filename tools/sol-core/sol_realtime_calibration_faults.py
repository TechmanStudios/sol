# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Real-time Calibration Faults
================================
Injects deterministic faults into real-time calibration loops, validating safety oracle responses.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class CalibrationFaultCase:
    case_id: str
    category: str
    description: str
    injected_value: Any
    expected_outcome: str

@dataclass
class CalibrationFaultInjection:
    injection_id: str
    case: CalibrationFaultCase
    timestamp: float = field(default_factory=time.time)

@dataclass
class CalibrationFaultResult:
    case_id: str
    category: str
    success: bool
    actual_outcome: str
    matched_expected: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class CalibrationStabilityAudit:
    audit_id: str
    policy: Any
    cases: List[CalibrationFaultCase] = field(default_factory=list)

@dataclass
class CalibrationFaultMatrixReport:
    report_id: str
    matrix_id: str
    results: List[CalibrationFaultResult]
    passed_cases: int
    failed_cases: int
    success: bool
    timestamp: float = field(default_factory=time.time)


def build_calibration_fault_matrix(policy: Any) -> CalibrationStabilityAudit:
    """
    Builds a calibration fault matrix for all 14 required categories.
    """
    categories = [
        ("phase drift spike", "Phase drift value exceeds policy limit", 0.5, "rollback_relocation"),
        ("cadence drift spike", "Cadence drift value exceeds policy limit", 0.5, "rollback_relocation"),
        ("carrier phase error spike", "Carrier phase error exceeds policy limit", 0.5, "rollback_relocation"),
        ("wavefront coherence collapse", "Wavefront coherence falls below threshold", 0.4, "rollback_relocation"),
        ("PML weakening", "PML boundary absorption drops below threshold", 0.4, "quarantine_manifold"),
        ("excessive route damping", "Route damping exceeds safe limit", 0.8, "quarantine_manifold"),
        ("runaway feedback gain", "Feedback gain exceeds safety margin", True, "rollback_relocation"),
        ("missing calibration baseline", "Baseline telemetry is missing from loop", True, "abort_relocation"),
        ("missing candidate phase table", "Candidate phase table is missing or invalid", True, "abort_relocation"),
        ("candidate table accidentally points to active table", "Candidate table overwrite detected", True, "reject_candidate"),
        ("adjustment exceeds policy bounds", "Adjustment delta exceeds policy clamping limit", True, "abort_relocation"),
        ("feedback loop fails to converge", "Entangled feedback loop fails to reach target", True, "rollback_relocation"),
        ("rollback after feedback fails", "Rollback is triggered after feedback failure", True, "rollback_relocation"),
        ("oracle mismatch after calibration", "Oracle verification mismatch detected", True, "reject_candidate"),
    ]
    
    cases = []
    for idx, (cat, desc, val, out) in enumerate(categories):
        cases.append(CalibrationFaultCase(
            case_id=f"CASE_CAL_{idx+1:03d}",
            category=cat,
            description=desc,
            injected_value=val,
            expected_outcome=out
        ))
        
    return CalibrationStabilityAudit(
        audit_id=f"AUDIT_CAL_{uuid.uuid4().hex[:8]}",
        policy=policy,
        cases=cases
    )


def inject_calibration_fault(case: CalibrationFaultCase, loop: Any) -> Any:
    """
    Injects calibration fault into loop metadata/policy/frames.
    """
    # If loop is a dict/object, we modify metadata/policy
    meta = None
    if isinstance(loop, dict):
        if "metadata" not in loop:
            loop["metadata"] = {}
        meta = loop["metadata"]
    else:
        meta = getattr(loop, "metadata", None)
        if meta is None:
            meta = {}
            setattr(loop, "metadata", meta)
            
    cat = case.category
    if cat == "phase drift spike":
        meta["phase_drift_spike"] = True
    elif cat == "cadence drift spike":
        meta["cadence_drift_spike"] = True
    elif cat == "carrier phase error spike":
        meta["carrier_phase_error_spike"] = True
    elif cat == "wavefront coherence collapse":
        meta["wavefront_coherence_collapse"] = True
    elif cat == "PML weakening":
        meta["pml_weakening"] = True
        meta["high_reflection"] = True
    elif cat == "excessive route damping":
        meta["excessive_route_damping"] = True
        meta["lane_isolation_breached"] = True
    elif cat == "runaway feedback gain":
        meta["runaway_feedback_gain"] = True
        meta["unstable_feedback"] = True
    elif cat == "missing calibration baseline":
        meta["missing_calibration_baseline"] = True
    elif cat == "missing candidate phase table":
        meta["missing_candidate_phase_table"] = True
    elif cat == "candidate table accidentally points to active table":
        meta["active_phase_table_overwritten"] = True
        meta["active_tables_overwritten"] = True
    elif cat == "adjustment exceeds policy bounds":
        meta["unbounded_adjustment"] = True
    elif cat == "feedback loop fails to converge":
        meta["unstable_feedback"] = True
    elif cat == "rollback after feedback fails":
        meta["unstable_feedback"] = True
        meta["rollback_triggered"] = True
    elif cat == "oracle mismatch after calibration":
        meta["oracle_comparison_failed"] = True
        
    return loop


def run_shadow_calibration_fault_case(case: CalibrationFaultCase) -> CalibrationFaultResult:
    """
    Runs shadow execution of a calibration fault case.
    """
    from sol_realtime_calibration_loop import (
        RealtimeCalibrationPolicy,
        RealtimeCalibrationTarget,
        RealtimeCalibrationFrame,
        build_realtime_calibration_loop,
        run_shadow_realtime_calibration
    )
    from sol_relocation_safety_oracle import evaluate_relocation_safety, RelocationSafetyOracleInput
    
    policy = RealtimeCalibrationPolicy(policy_id="POL_CAL_FAULT", clamped_adjustment_delta=0.01)
    loop = build_realtime_calibration_loop([RealtimeCalibrationTarget("TGT1", "M1", 0, 10.0)], policy)
    loop.baseline_telemetry = {"phase_drift": 0.01}
    
    # Inject fault
    inject_calibration_fault(case, loop)
    
    # Check if baseline is missing
    if loop.metadata.get("missing_calibration_baseline"):
        loop.baseline_telemetry = {}
        
    # Build frame based on case
    cat = case.category
    frame = RealtimeCalibrationFrame(
        frame_id="F_FAULT",
        timestamp=time.time(),
        phase_drift=0.5 if cat == "phase drift spike" else 0.01,
        cadence_drift=0.5 if cat == "cadence drift spike" else 0.01,
        carrier_phase_error=0.5 if cat == "carrier phase error spike" else 0.01,
        wavefront_coherence=0.4 if cat == "wavefront coherence collapse" else 0.95,
        crosstalk=0.01,
        boundary_reflection=0.5 if cat == "PML weakening" else 0.01,
        pml_absorption_effectiveness=0.4 if cat == "PML weakening" else 1.0,
        active_mass_preservation=True,
        lane_timing_consistency=True,
        state_hash_agreement=True
    )
    
    # Inject unbounded adjustment to loop policy metadata
    if loop.metadata.get("unbounded_adjustment"):
        loop.policy.metadata["unbounded_adjustment"] = True
        
    # Check if missing baseline
    errors = []
    if not loop.baseline_telemetry:
        errors.append("Baseline calibration telemetry is missing.")
        
    # Run loop
    rep = run_shadow_realtime_calibration(loop, [frame])
    
    # Merge errors
    all_errors = list(rep.result.errors)
    for e in errors:
        if e not in all_errors:
            all_errors.append(e)
            
    success_val = rep.result.success and not all_errors
    
    # Oracle evaluation
    oracle_input = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category=case.category,
        success=success_val,
        errors=all_errors,
        metadata=loop.metadata
    )
    decision = evaluate_relocation_safety(oracle_input)
    actual_outcome = decision.outcome
    
    matched = (actual_outcome == case.expected_outcome)
    success = matched and (actual_outcome in ["hold_relocation", "abort_relocation", "rollback_relocation", "quarantine_state_ref", "quarantine_manifold", "reject_candidate"])
    
    return CalibrationFaultResult(
        case_id=case.case_id,
        category=case.category,
        success=success,
        actual_outcome=actual_outcome,
        matched_expected=matched,
        errors=all_errors
    )


def run_shadow_calibration_fault_matrix(matrix: CalibrationStabilityAudit) -> CalibrationFaultMatrixReport:
    """
    Runs all cases in the calibration fault matrix.
    """
    results = []
    for case in matrix.cases:
        results.append(run_shadow_calibration_fault_case(case))
        
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    success = failed == 0
    
    report_id = f"REP_CAL_MATRIX_{uuid.uuid4().hex[:8]}"
    return CalibrationFaultMatrixReport(
        report_id=report_id,
        matrix_id=matrix.audit_id,
        results=results,
        passed_cases=passed,
        failed_cases=failed,
        success=success
    )


def summarize_calibration_fault_results(results: List[CalibrationFaultResult]) -> Dict[str, Any]:
    """
    Summarizes results of calibration fault matrix execution.
    """
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "success": all(r.success for r in results)
    }
