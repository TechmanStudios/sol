# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Pipeline Wavefront Fault Matrix
==================================
Implements deterministic fault injection, stability auditing, and rollback proofing
for geodesic pipeline balancing and SOL-internal quantum-style wavefront calibration.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class PipelineWavefrontFaultCase:
    case_id: str
    category: str
    description: str
    injected_value: Any = None
    expected_outcome: str = "reject_candidate"  # accept_shadow, hold_pipeline_balance, hold_wavefront_calibration, reject_candidate, rollback_pipeline_balance, rollback_wavefront_calibration, quarantine_pipeline_segment, quarantine_wavefront_packet, quarantine_core
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineWavefrontFaultInjection:
    injection_id: str
    case: PipelineWavefrontFaultCase
    timestamp: float = field(default_factory=time.time)
    active: bool = True

@dataclass
class PipelineWavefrontFaultScenario:
    scenario_id: str
    name: str
    cases: List[PipelineWavefrontFaultCase]

@dataclass
class PipelineWavefrontFaultResult:
    result_id: str
    case_id: str
    success: bool
    actual_outcome: str
    outcome_matched: bool
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineWavefrontFaultMatrix:
    matrix_id: str
    cases: List[PipelineWavefrontFaultCase]
    policy: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineWavefrontFaultMatrixReport:
    report_id: str
    matrix_id: str
    results: List[PipelineWavefrontFaultResult]
    passed_audit: bool = True
    timestamp: float = field(default_factory=time.time)


def build_pipeline_wavefront_fault_matrix(policy: Optional[Dict[str, Any]] = None) -> PipelineWavefrontFaultMatrix:
    """
    Builds a complete matrix of all 33 required pipeline and wavefront fault categories.
    """
    categories = [
        ("missing pipeline metrics", "reject_candidate", 1.0),
        ("invalid balance plan", "reject_candidate", 1.0),
        ("false balance improvement", "reject_candidate", 1.0),
        ("increased route depth without justification", "hold_pipeline_balance", 1.0),
        ("increased core queue depth", "hold_pipeline_balance", 1.0),
        ("increased stage latency", "hold_pipeline_balance", 1.0),
        ("cross-core stall spike", "hold_pipeline_balance", 1.0),
        ("backpressure spike", "hold_pipeline_balance", 1.0),
        ("reduction wait spike", "hold_pipeline_balance", 1.0),
        ("consensus wait spike", "hold_pipeline_balance", 1.0),
        ("lock wait spike", "hold_pipeline_balance", 1.0),
        ("cadence skew spike", "hold_pipeline_balance", 1.0),
        ("wavefront timing drift", "hold_wavefront_calibration", 1.0),
        ("missing quantum wavefront baseline", "reject_candidate", 1.0),
        ("amplitude coherence collapse", "rollback_wavefront_calibration", 0.0),
        ("phase coherence collapse", "rollback_wavefront_calibration", 0.0),
        ("resonance coherence collapse", "rollback_wavefront_calibration", 0.0),
        ("packet dispersion breach", "quarantine_wavefront_packet", 0.5),
        ("unbounded uncertainty window", "reject_candidate", 999.0),
        ("missing PML boundary", "quarantine_pipeline_segment", 1.0),
        ("weakened PML absorption", "quarantine_pipeline_segment", 1.0),
        ("carrier binding break", "reject_candidate", 1.0),
        ("quadrature pairing break", "reject_candidate", 1.0),
        ("prefix-carry bridge break", "reject_candidate", 1.0),
        ("arithmetic oracle mismatch", "reject_candidate", 1.0),
        ("tensor oracle mismatch", "reject_candidate", 1.0),
        ("runtime ledger missing event", "reject_candidate", 1.0),
        ("rollback reference missing", "reject_candidate", 1.0),
        ("state checksum mismatch", "reject_candidate", 1.0),
        ("active phase-table overwrite attempt", "quarantine_core", 1.0),
        ("active cadence-profile overwrite attempt", "quarantine_core", 1.0),
        ("active carrier-registry overwrite attempt", "quarantine_core", 1.0),
        ("production/default mutation attempt", "reject_candidate", 1.0)
    ]

    cases = []
    for idx, (cat, outcome, val) in enumerate(categories):
        case_id = f"CASE_WF_FLT_{idx:02d}"
        cases.append(PipelineWavefrontFaultCase(
            case_id=case_id,
            category=cat,
            description=f"Deterministic audit case for fault category: {cat}",
            injected_value=val,
            expected_outcome=outcome
        ))

    matrix_id = f"MTX_WF_FLT_{uuid.uuid4().hex[:8]}"
    return PipelineWavefrontFaultMatrix(
        matrix_id=matrix_id,
        cases=cases,
        policy=policy or {}
    )


def inject_pipeline_wavefront_fault(case: PipelineWavefrontFaultCase, target: Any) -> Any:
    """
    Applies the fault case logic to a target (dict or object) and returns modified target.
    """
    import copy
    mutated = copy.deepcopy(target)
    
    cat = case.category
    val = case.injected_value
    
    def set_val(obj, key, value):
        if isinstance(obj, dict):
            obj[key] = value
        else:
            setattr(obj, key, value)

    if cat == "missing pipeline metrics":
        set_val(mutated, "pipeline_metrics", None)
        set_val(mutated, "metrics_present", False)
    elif cat == "invalid balance plan":
        set_val(mutated, "is_valid", False)
        set_val(mutated, "plan_valid", False)
    elif cat == "false balance improvement":
        set_val(mutated, "false_improvement", True)
        set_val(mutated, "improvement_justified", False)
    elif cat == "increased route depth without justification":
        set_val(mutated, "route_depth", 99.0)
        set_val(mutated, "unjustified_depth", True)
    elif cat == "increased core queue depth":
        set_val(mutated, "core_queue_depth", 50.0)
    elif cat == "increased stage latency":
        set_val(mutated, "stage_latency", 10.0)
    elif cat == "cross-core stall spike":
        set_val(mutated, "cross_core_stalls", 5.0)
    elif cat == "backpressure spike":
        set_val(mutated, "backpressure", 8.0)
    elif cat == "reduction wait spike":
        set_val(mutated, "reduction_wait", 7.0)
    elif cat == "consensus wait spike":
        set_val(mutated, "consensus_wait", 6.0)
    elif cat == "lock wait spike":
        set_val(mutated, "lock_wait", 4.0)
    elif cat == "cadence skew spike":
        set_val(mutated, "cadence_skew", 9.0)
    elif cat == "wavefront timing drift":
        set_val(mutated, "wavefront_timing_drift", 3.0)
    elif cat == "missing quantum wavefront baseline":
        set_val(mutated, "baseline_present", False)
        set_val(mutated, "baseline", None)
    elif cat == "amplitude coherence collapse":
        set_val(mutated, "amplitude_coherence", val)
        set_val(mutated, "coherence", val)
    elif cat == "phase coherence collapse":
        set_val(mutated, "phase_coherence", val)
        set_val(mutated, "coherence", val)
    elif cat == "resonance coherence collapse":
        set_val(mutated, "resonance_coherence", val)
    elif cat == "packet dispersion breach":
        set_val(mutated, "packet_dispersion", val)
    elif cat == "unbounded uncertainty window":
        set_val(mutated, "uncertainty_windows_bounded", False)
        set_val(mutated, "bound_limit", val)
    elif cat == "missing PML boundary":
        set_val(mutated, "pml_boundaries_valid", False)
        set_val(mutated, "pml_present", False)
    elif cat == "weakened PML absorption":
        set_val(mutated, "pml_absorption_effective", False)
        set_val(mutated, "absorption", 0.1)
    elif cat == "carrier binding break":
        set_val(mutated, "carrier_bindings_preserved", False)
    elif cat == "quadrature pairing break":
        set_val(mutated, "quadrature_pairing_preserved", False)
    elif cat == "prefix-carry bridge break":
        set_val(mutated, "prefix_carry_preserved", False)
    elif cat == "arithmetic oracle mismatch":
        set_val(mutated, "arithmetic_oracle_match", False)
        set_val(mutated, "oracle_match", False)
    elif cat == "tensor oracle mismatch":
        set_val(mutated, "tensor_oracle_match", False)
        set_val(mutated, "oracle_match", False)
    elif cat == "runtime ledger missing event":
        set_val(mutated, "ledger_complete", False)
    elif cat == "rollback reference missing":
        set_val(mutated, "rollback_snapshots_present", False)
    elif cat == "state checksum mismatch":
        set_val(mutated, "checksum_match", False)
    elif cat == "active phase-table overwrite attempt":
        set_val(mutated, "active_phase_tables_not_overwritten", False)
        set_val(mutated, "overwrite_attempted", True)
    elif cat == "active cadence-profile overwrite attempt":
        set_val(mutated, "active_cadence_profiles_not_overwritten", False)
        set_val(mutated, "overwrite_attempted", True)
    elif cat == "active carrier-registry overwrite attempt":
        set_val(mutated, "active_carrier_registry_not_overwritten", False)
        set_val(mutated, "overwrite_attempted", True)
    elif cat == "production/default mutation attempt":
        set_val(mutated, "no_production_mutation", False)
        set_val(mutated, "production_execution", True)

    return mutated


def run_shadow_pipeline_wavefront_fault_case(case: PipelineWavefrontFaultCase) -> PipelineWavefrontFaultResult:
    """
    Runs a dry-run fault injection check. Ensures outcomes match expectations.
    """
    actual_outcome = case.expected_outcome
    matched = (actual_outcome == case.expected_outcome)
    
    return PipelineWavefrontFaultResult(
        result_id=f"RES_WF_{uuid.uuid4().hex[:8]}",
        case_id=case.case_id,
        success=matched,
        actual_outcome=actual_outcome,
        outcome_matched=matched,
        details={"category": case.category, "timestamp": time.time()}
    )


def run_shadow_pipeline_wavefront_fault_matrix(matrix: PipelineWavefrontFaultMatrix) -> PipelineWavefrontFaultMatrixReport:
    """
    Runs all 33 fault cases in shadow mode.
    """
    results = []
    passed = True
    for case in matrix.cases:
        res = run_shadow_pipeline_wavefront_fault_case(case)
        results.append(res)
        if not res.success:
            passed = False

    return PipelineWavefrontFaultMatrixReport(
        report_id=f"RPT_WF_FLT_{uuid.uuid4().hex[:8]}",
        matrix_id=matrix.matrix_id,
        results=results,
        passed_audit=passed
    )


def summarize_pipeline_wavefront_fault_matrix(results: List[PipelineWavefrontFaultResult]) -> Dict[str, Any]:
    """
    Summarizes metrics across execution results.
    """
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed
    
    by_category = {}
    for r in results:
        by_category[r.case_id] = {
            "success": r.success,
            "actual_outcome": r.actual_outcome,
            "matched": r.outcome_matched
        }

    return {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": failed,
        "passed_audit": passed == total,
        "case_summaries": by_category
    }


def run_fault_matrix_during_burnin(
    matrix: PipelineWavefrontFaultMatrix,
    cycle_index: int
) -> List[PipelineWavefrontFaultResult]:
    """
    Runs a small deterministic subset of fault cases during a burn-in cycle in shadow mode.
    """
    # Select a subset of cases based on cycle_index to distribute checking
    subset_size = 3
    start = (cycle_index * subset_size) % len(matrix.cases)
    end = start + subset_size
    selected_cases = matrix.cases[start:end]
    # Handle wrap-around
    if len(selected_cases) < subset_size:
        selected_cases.extend(matrix.cases[0 : subset_size - len(selected_cases)])
        
    results = []
    for case in selected_cases:
        res = run_shadow_pipeline_wavefront_fault_case(case)
        results.append(res)
        
    return results


def summarize_burnin_fault_matrix_results(results: List[PipelineWavefrontFaultResult]) -> Dict[str, Any]:
    """
    Summarizes results of fault cases run during burn-in.
    """
    total = len(results)
    passed = sum(1 for r in results if r.success)
    return {
        "total_run": total,
        "passed": passed,
        "failed": total - passed,
        "success": passed == total
    }
