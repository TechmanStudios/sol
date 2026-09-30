# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Pipeline Calibration
========================
Calibrates stage latency and scheduling parameters in shadow/sandbox mode.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class PipelineCalibrationPolicy:
    max_steps: int
    max_adjustment_limit: float = 0.2
    max_phase_offset_adjustment: float = 0.1
    max_gain_limit: float = 0.5
    abort_thresholds: Dict[str, float] = field(default_factory=dict)
    rollback_requirement: bool = True
    court_token_required_for_sandbox: bool = True

@dataclass
class PipelineCalibrationTarget:
    target_id: str
    core_id: str
    stage_name: str
    expected_latency: float

@dataclass
class PipelineCalibrationBaseline:
    baseline_id: str
    targets: List[PipelineCalibrationTarget]
    captured_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PipelineCalibrationObservation:
    observation_id: str
    stage_latency: float
    core_queue_depth: int
    cross_core_stall_time: float
    backpressure: float
    reduction_wait: float
    consensus_wait: float
    shard_lock_wait: float
    cadence_drift: float
    wavefront_timing_drift: float
    carrier_timing_drift: float
    oracle_match: bool = True
    timestamp: float = field(default_factory=time.time)

@dataclass
class PipelineCalibrationAdjustment:
    adjustment_id: str
    target_id: str
    latency_offset: float
    gain: float

@dataclass
class PipelineCalibrationResult:
    success: bool
    errors: List[str] = field(default_factory=list)
    final_error_vector: Dict[str, float] = field(default_factory=dict)
    rolled_back: bool = False

@dataclass
class PipelineCalibrationReport:
    report_id: str
    baseline: PipelineCalibrationBaseline
    result: PipelineCalibrationResult
    history: List[Any] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


def build_pipeline_calibration_targets(
    pipeline_schedule: Any,
    core_assembly: Any
) -> List[PipelineCalibrationTarget]:
    """
    Formulates calibration targets for all cores and pipeline stages.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    targets = []
    
    # Extract tasks/cores
    tasks = extract(pipeline_schedule, "tasks", {})
    if isinstance(tasks, dict):
        task_list = list(tasks.values())
    elif isinstance(tasks, list):
        task_list = tasks
    else:
        task_list = []
        
    for task in task_list:
        core_id = extract(task, "core_id", "core_0")
        stage_name = extract(task, "stage_name", "execute")
        targets.append(PipelineCalibrationTarget(
            target_id=f"TGT_CAL_{uuid.uuid4().hex[:4]}",
            core_id=core_id,
            stage_name=stage_name,
            expected_latency=extract(task, "duration", 0.0) or 0.005
        ))
        
    if not targets:
        # Fallback default targets
        targets.append(PipelineCalibrationTarget(
            target_id="TGT_DEFAULT",
            core_id="core_0",
            stage_name="execute",
            expected_latency=0.005
        ))
        
    return targets


def capture_pipeline_calibration_baseline(
    targets: List[PipelineCalibrationTarget]
) -> PipelineCalibrationBaseline:
    """
    Captures a baseline configuration of target latency profiles.
    """
    return PipelineCalibrationBaseline(
        baseline_id=f"BASE_{uuid.uuid4().hex[:8]}",
        targets=targets,
        captured_at=time.time()
    )


def measure_pipeline_calibration_error(
    baseline: PipelineCalibrationBaseline,
    current: PipelineCalibrationObservation
) -> Dict[str, float]:
    """
    Measures error vector between current observation metrics and the expected baseline.
    """
    if not baseline:
        raise ValueError("Pipeline calibration baseline is required before calibration.")
        
    # Baseline expected latency average
    exp_lat = sum(t.expected_latency for t in baseline.targets) / len(baseline.targets) if baseline.targets else 0.005
    err_lat = current.stage_latency - exp_lat
    
    return {
        "stage_latency_error": err_lat,
        "cadence_drift": current.cadence_drift,
        "cross_core_stall_error": current.cross_core_stall_time,
        "backpressure_error": current.backpressure
    }


def plan_pipeline_calibration_adjustment(
    error_report: Dict[str, float],
    policy: PipelineCalibrationPolicy
) -> List[PipelineCalibrationAdjustment]:
    """
    Computes a set of bounded offset adjustments based on the error vector.
    """
    if not policy or policy.max_steps <= 0:
        raise ValueError("Pipeline calibration policy is invalid: max_steps must be > 0.")
        
    adjustments = []
    
    # Proportional latency offset calculation
    lat_err = error_report.get("stage_latency_error", 0.0)
    # Clamp to adjustment limits
    adj_val = -0.5 * lat_err
    adj_val = max(-policy.max_adjustment_limit, min(policy.max_adjustment_limit, adj_val))
    
    adjustments.append(PipelineCalibrationAdjustment(
        adjustment_id=f"ADJ_CAL_{uuid.uuid4().hex[:4]}",
        target_id="TGT_0",
        latency_offset=adj_val,
        gain=policy.max_gain_limit
    ))
    return adjustments


def execute_shadow_pipeline_calibration(
    adjustments: List[PipelineCalibrationAdjustment]
) -> PipelineCalibrationResult:
    """
    Applies pipeline calibration adjustments in shadow mode.
    """
    errors = []
    for adj in adjustments:
        # Check safety bounds
        if abs(adj.latency_offset) > 0.5: # Hard safety limit
            errors.append("Latency offset exceeds safety bounds.")
            
    success = len(errors) == 0
    return PipelineCalibrationResult(
        success=success,
        errors=errors,
        final_error_vector={},
        rolled_back=not success
    )


def summarize_pipeline_calibration(result: PipelineCalibrationResult) -> Dict[str, Any]:
    """
    Returns summary metrics.
    """
    return {
        "success": result.success,
        "errors": list(result.errors),
        "rolled_back": result.rolled_back
    }


def calibrate_pipeline_after_geodesic_balance(
    balance_report: Any,
    calibration_policy: PipelineCalibrationPolicy
) -> PipelineCalibrationReport:
    """
    Runs calibration based on geodesic balancing report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    targets = [PipelineCalibrationTarget("target_balanced", "core_0", "execute", 0.005)]
    baseline = capture_pipeline_calibration_baseline(targets)
    
    errors = []
    res_obj = extract(balance_report, "result", {})
    success = extract(res_obj, "success", True)
    if not success:
        errors.append("Calibration blocked: geodesic balancing failed.")

    result = PipelineCalibrationResult(
        success=len(errors) == 0,
        errors=errors,
        final_error_vector={},
        rolled_back=not success
    )
    
    return PipelineCalibrationReport(
        report_id=f"CAL_REP_BAL_{uuid.uuid4().hex[:8]}",
        baseline=baseline,
        result=result,
        timestamp=time.time()
    )


def validate_pipeline_calibration_after_balance(
    calibration_report: PipelineCalibrationReport,
    balance_report: Any
) -> bool:
    """
    Validates pipeline calibration after balance.
    """
    if not calibration_report or not calibration_report.result.success:
        return False
    return True

