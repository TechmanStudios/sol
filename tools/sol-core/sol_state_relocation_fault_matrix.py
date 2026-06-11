# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL State Relocation Fault Matrix
=================================
Injects deterministic faults into state relocation intents and plans, auditing safety oracle outcomes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class RelocationFaultCase:
    case_id: str
    category: str
    description: str
    injected_value: Any
    expected_outcome: str

@dataclass
class RelocationFaultInjection:
    injection_id: str
    case: RelocationFaultCase
    timestamp: float = field(default_factory=time.time)

@dataclass
class RelocationFaultScenario:
    scenario_id: str
    name: str
    cases: List[RelocationFaultCase]

@dataclass
class RelocationFaultResult:
    case_id: str
    category: str
    success: bool
    actual_outcome: str
    matched_expected: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class RelocationFaultMatrix:
    matrix_id: str
    policy: Any
    scenarios: List[RelocationFaultScenario] = field(default_factory=list)

@dataclass
class RelocationFaultMatrixReport:
    report_id: str
    matrix_id: str
    results: List[RelocationFaultResult]
    passed_cases: int
    failed_cases: int
    success: bool
    timestamp: float = field(default_factory=time.time)


def build_relocation_fault_matrix(policy: Any) -> RelocationFaultMatrix:
    """
    Builds a relocation fault matrix containing cases for all 21 required categories.
    """
    categories = [
        ("missing source state", "Source state reference is missing or invalid", True, "abort_relocation"),
        ("missing target state", "Target state reference is missing or invalid", True, "abort_relocation"),
        ("state hash mismatch", "Before and after state hashes do not match", True, "rollback_relocation"),
        ("missing rollback snapshot", "Rollback snapshot reference is absent before transfer", True, "abort_relocation"),
        ("corrupted rollback snapshot", "Rollback snapshot is corrupted during verification", True, "reject_candidate"),
        ("local quorum failure", "Local quorum voting consensus is rejected", True, "abort_relocation"),
        ("global quorum failure", "Global coordinator transaction consensus fails", True, "abort_relocation"),
        ("sequencer quorum failure", "Sequencer group consensus is rejected", True, "abort_relocation"),
        ("cadence window failure", "State relocation requested outside safe cadence window", True, "abort_relocation"),
        ("lock boundary failure", "Resource lock acquisition fails", True, "abort_relocation"),
        ("cross-manifold deadlock", "Deadlock detected during multi-manifold lock acquisition", True, "abort_relocation"),
        ("unstable wavefront coherence", "Wavefront coherence falls below threshold", True, "rollback_relocation"),
        ("crosstalk spike", "Inter-lane crosstalk exceeds safe limit", True, "quarantine_manifold"),
        ("boundary reflection breach", "PML boundary reflection exceeds threshold", True, "quarantine_manifold"),
        ("invalid PML boundary", "PML cells boundary is missing or invalid", True, "quarantine_manifold"),
        ("unstable feedback loop", "Drift feedback adjustments fail to converge", True, "rollback_relocation"),
        ("unbounded real-time calibration adjustment", "Calibration adjustment delta exceeds clamped threshold", True, "abort_relocation"),
        ("partial relocation risk", "Risk of partial/incomplete state relocation is detected", True, "hold_relocation"),
        ("active phase-table overwrite attempt", "Attempt to overwrite default/active phase table", True, "reject_candidate"),
        ("active cadence-table overwrite attempt", "Attempt to overwrite default/active cadence table", True, "reject_candidate"),
        ("active carrier-registry overwrite attempt", "Attempt to overwrite default/active carrier registry", True, "reject_candidate"),
    ]
    
    cases = []
    for idx, (cat, desc, val, out) in enumerate(categories):
        cases.append(RelocationFaultCase(
            case_id=f"CASE_SR_{idx+1:03d}",
            category=cat,
            description=desc,
            injected_value=val,
            expected_outcome=out
        ))
        
    scenario = RelocationFaultScenario(
        scenario_id="SCEN_SR_ALL",
        name="All Relocation Faults Scenario",
        cases=cases
    )
    
    matrix_id = f"MATRIX_SR_{uuid.uuid4().hex[:8]}"
    return RelocationFaultMatrix(
        matrix_id=matrix_id,
        policy=policy,
        scenarios=[scenario]
    )


def inject_relocation_fault(case: RelocationFaultCase, baseline: Any) -> Any:
    """
    Injects the specified fault case into a plan or metadata dictionary.
    """
    meta = None
    if isinstance(baseline, dict):
        meta = baseline
    elif hasattr(baseline, "intent") and hasattr(baseline.intent, "metadata"):
        meta = baseline.intent.metadata
    elif hasattr(baseline, "metadata"):
        meta = baseline.metadata
        
    if meta is None:
        raise ValueError("Cannot inject fault: baseline does not have metadata.")
        
    cat = case.category
    if cat == "missing source state":
        meta["missing_source"] = True
        meta["missing_source_state"] = True
    elif cat == "missing target state":
        meta["missing_target"] = True
        meta["missing_target_state"] = True
    elif cat == "state hash mismatch":
        meta["state_hash_mismatch"] = True
    elif cat == "missing rollback snapshot":
        meta["missing_rollback_snapshot"] = True
    elif cat == "corrupted rollback snapshot":
        meta["corrupted_rollback_snapshot"] = True
    elif cat == "local quorum failure":
        meta["local_quorum_failed"] = True
        meta["failed_consensus"] = True
    elif cat == "global quorum failure":
        meta["global_quorum_failed"] = True
        meta["failed_consensus"] = True
    elif cat == "sequencer quorum failure":
        meta["sequencer_quorum_failed"] = True
    elif cat == "cadence window failure":
        meta["outside_cadence_window"] = True
    elif cat == "lock boundary failure":
        meta["lock_boundary_failed"] = True
        meta["failed_prepare"] = True
    elif cat == "cross-manifold deadlock":
        meta["cross_manifold_deadlock"] = True
    elif cat == "unstable wavefront coherence":
        meta["unstable_wavefront"] = True
    elif cat == "crosstalk spike":
        meta["high_crosstalk"] = True
    elif cat == "boundary reflection breach":
        meta["high_reflection"] = True
    elif cat == "invalid PML boundary":
        meta["pml_boundaries_invalid"] = True
    elif cat == "unstable feedback loop":
        meta["unstable_feedback"] = True
    elif cat == "unbounded real-time calibration adjustment":
        meta["unbounded_adjustment"] = True
    elif cat == "partial relocation risk":
        meta["partial_relocation_risk"] = True
    elif cat == "active phase-table overwrite attempt":
        meta["active_phase_table_overwritten"] = True
        meta["active_tables_overwritten"] = True
    elif cat == "active cadence-table overwrite attempt":
        meta["active_cadence_table_overwritten"] = True
        meta["active_tables_overwritten"] = True
    elif cat == "active carrier-registry overwrite attempt":
        meta["active_carrier_registry_overwritten"] = True
        meta["active_tables_overwritten"] = True
        
    return baseline


def run_shadow_relocation_fault_case(case: RelocationFaultCase) -> RelocationFaultResult:
    """
    Runs shadow execution of a relocation fault case.
    """
    from sol_distributed_state_relocation import (
        StateRelocationSource,
        StateRelocationTarget,
        build_state_relocation_intent,
        build_state_relocation_plan,
        execute_shadow_state_relocation
    )
    from sol_relocation_safety_oracle import evaluate_relocation_safety, RelocationSafetyOracleInput
    
    src = StateRelocationSource("M1", "S1", 0, "SEQ1")
    tgt = StateRelocationTarget("M2", "S2", 0, "SEQ2")
    intent = build_state_relocation_intent(src, tgt, ["ref1"], "strict_shadow")
    plan = build_state_relocation_plan(intent, ["M1", "M2"])
    
    # Inject fault
    inject_relocation_fault(case, plan)
    
    # Run
    res = execute_shadow_state_relocation(plan)
    
    # Use Safety Oracle to evaluate actual outcome
    oracle_input = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category=case.category,
        success=res.success,
        errors=res.errors,
        metadata=plan.intent.metadata
    )
    decision = evaluate_relocation_safety(oracle_input)
    actual_outcome = decision.outcome
    
    matched = (actual_outcome == case.expected_outcome)
    success = matched and (actual_outcome in ["hold_relocation", "abort_relocation", "rollback_relocation", "quarantine_state_ref", "quarantine_manifold", "reject_candidate"])
    
    return RelocationFaultResult(
        case_id=case.case_id,
        category=case.category,
        success=success,
        actual_outcome=actual_outcome,
        matched_expected=matched,
        errors=res.errors
    )


def run_shadow_relocation_fault_matrix(matrix: RelocationFaultMatrix) -> RelocationFaultMatrixReport:
    """
    Runs all cases in the relocation fault matrix.
    """
    results = []
    for scen in matrix.scenarios:
        for case in scen.cases:
            results.append(run_shadow_relocation_fault_case(case))
            
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    success = failed == 0
    
    report_id = f"REP_SR_MATRIX_{uuid.uuid4().hex[:8]}"
    return RelocationFaultMatrixReport(
        report_id=report_id,
        matrix_id=matrix.matrix_id,
        results=results,
        passed_cases=passed,
        failed_cases=failed,
        success=success
    )


def summarize_relocation_fault_matrix(results: List[RelocationFaultResult]) -> Dict[str, Any]:
    """
    Summarizes results of relocation fault execution.
    """
    return {
        "total": len(results),
        "passed": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "success": all(r.success for r in results)
    }
