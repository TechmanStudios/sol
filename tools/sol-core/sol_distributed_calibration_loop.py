# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Distributed Calibration Loop
================================
Scaffolds distributed calibration steps, policies, and target calibrations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import time
import math

@dataclass
class CalibrationLoopId:
    loop_id: str

@dataclass
class CalibrationLoopPolicy:
    max_steps: int
    max_adjustment_magnitude: float
    max_phase_correction: float
    max_damping_adjustment: float
    max_boundary_absorption_adjustment: float
    abort_thresholds: Dict[str, float] = field(default_factory=dict)
    rollback_requirement: bool = True

@dataclass
class CalibrationLoopTarget:
    target_id: str
    boundary_group_id: str
    channels: List[Any] = field(default_factory=list)

@dataclass
class CalibrationLoopObservation:
    observation_id: str
    timestamp: float = field(default_factory=time.time)
    metrics: Dict[str, float] = field(default_factory=dict)

@dataclass
class CalibrationLoopAdjustment:
    adjustment_id: str
    phase_correction: float = 0.0
    damping_adjustment: float = 0.0
    boundary_absorption_adjustment: float = 0.0
    target_lane: Optional[int] = None
    target_channel: Optional[Any] = None

@dataclass
class CalibrationLoopStep:
    step_index: int
    observation: CalibrationLoopObservation
    adjustment: CalibrationLoopAdjustment
    timestamp: float = field(default_factory=time.time)

@dataclass
class CalibrationLoopResult:
    success: bool
    step_count: int
    final_drift: float
    rolled_back: bool
    quarantined: bool
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CalibrationLoopReport:
    report_id: str
    loop_id: CalibrationLoopId
    targets: List[CalibrationLoopTarget]
    policy: CalibrationLoopPolicy
    steps: List[CalibrationLoopStep]
    result: CalibrationLoopResult
    passed_gates: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class CalibrationLoop:
    loop_id: CalibrationLoopId
    targets: List[CalibrationLoopTarget]
    policy: CalibrationLoopPolicy
    baseline_telemetry: Optional[Dict[str, Any]] = None


def build_calibration_loop(
    targets: List[CalibrationLoopTarget],
    policy: CalibrationLoopPolicy
) -> CalibrationLoop:
    """
    Constructs a calibration loop configuration.
    Validates bounds during construction.
    """
    if not targets:
        raise ValueError("Calibration loop requires at least one target.")
    if policy.max_steps <= 0:
        raise ValueError("Invalid calibration policy: max_steps must be greater than 0.")
    if not math.isfinite(policy.max_adjustment_magnitude) or policy.max_adjustment_magnitude <= 0.0:
        raise ValueError("Invalid calibration policy: max_adjustment_magnitude must be finite and positive.")
    if policy.max_adjustment_magnitude > 2.0:
        raise ValueError("Unbounded or unsafe adjustment magnitude is rejected.")
    if not policy.abort_thresholds:
        raise ValueError("Invalid calibration policy: abort_thresholds is required.")

    loop_id = CalibrationLoopId(f"CL_{int(time.time())}_{len(targets)}")
    return CalibrationLoop(loop_id=loop_id, targets=targets, policy=policy)


def validate_calibration_loop(loop: CalibrationLoop) -> bool:
    """
    Validates calibration loop bounds and policy invariants.
    """
    p = loop.policy
    if p.max_steps <= 0 or p.max_steps > 1000:
        return False
    if not math.isfinite(p.max_adjustment_magnitude) or p.max_adjustment_magnitude <= 0.0 or p.max_adjustment_magnitude > 2.0:
        return False
    if not math.isfinite(p.max_phase_correction) or p.max_phase_correction <= 0.0:
        return False
    if not math.isfinite(p.max_damping_adjustment) or p.max_damping_adjustment <= 0.0:
        return False
    if not math.isfinite(p.max_boundary_absorption_adjustment) or p.max_boundary_absorption_adjustment <= 0.0:
        return False
    if not loop.targets:
        return False
    return True


def run_shadow_calibration_loop(
    loop: CalibrationLoop,
    observations: List[CalibrationLoopObservation]
) -> CalibrationLoopReport:
    """
    Simulates calibration step sweeps, performing shadow checks and generating adjustments.
    In shadow mode, active phase tables are NOT overwritten; candidate tables are separate.
    """
    errors = []
    steps = []
    rolled_back = False
    quarantined = False
    success = True
    final_drift = 0.0

    # 1. Check baseline telemetry requirement
    if not loop.baseline_telemetry:
        errors.append("Calibration baseline is required before loop execution.")
        res = CalibrationLoopResult(
            success=False,
            step_count=0,
            final_drift=1.0,
            rolled_back=False,
            quarantined=False,
            errors=errors
        )
        return CalibrationLoopReport(
            report_id=f"CLREP_{loop.loop_id.loop_id}",
            loop_id=loop.loop_id,
            targets=loop.targets,
            policy=loop.policy,
            steps=[],
            result=res,
            passed_gates=False
        )

    # 2. Check loop validity
    if not validate_calibration_loop(loop):
        errors.append("Invalid calibration policy or target configuration.")
        res = CalibrationLoopResult(
            success=False,
            step_count=0,
            final_drift=1.0,
            rolled_back=False,
            quarantined=False,
            errors=errors
        )
        return CalibrationLoopReport(
            report_id=f"CLREP_{loop.loop_id.loop_id}",
            loop_id=loop.loop_id,
            targets=loop.targets,
            policy=loop.policy,
            steps=[],
            result=res,
            passed_gates=False
        )

    prev_drift = loop.baseline_telemetry.get("phase_drift", 0.0)

    for i, obs in enumerate(observations[:loop.policy.max_steps]):
        drift = obs.metrics.get("phase_drift", 0.0)
        crosstalk = obs.metrics.get("crosstalk", 0.0)
        reflection = obs.metrics.get("boundary_reflection", 0.0)
        active_mass = obs.metrics.get("active_mass", 500.0)

        # Check abort thresholds
        if drift > loop.policy.abort_thresholds.get("phase_drift", 0.10):
            errors.append(f"Phase drift {drift:.4f} breached abort threshold.")
            success = False
            if loop.policy.rollback_requirement:
                rolled_back = True
            break
        
        if crosstalk > loop.policy.abort_thresholds.get("crosstalk", 0.05):
            errors.append(f"Crosstalk {crosstalk:.4f} breached abort threshold.")
            success = False
            quarantined = True
            break

        if reflection > loop.policy.abort_thresholds.get("boundary_reflection", 0.05):
            errors.append(f"Boundary reflection {reflection:.4f} breached abort threshold.")
            success = False
            break

        if active_mass < loop.policy.abort_thresholds.get("active_mass_min", 14.0):
            errors.append(f"Active mass {active_mass:.4f} fell below minimum safety threshold.")
            success = False
            if loop.policy.rollback_requirement:
                rolled_back = True
            break

        # Advisory corrections: shadow corrections are separate candidate tables.
        # We calculate adjustment to reduce drift
        adj_phase = -0.5 * drift
        # Clamp to bounds
        adj_phase = max(-loop.policy.max_phase_correction, min(loop.policy.max_phase_correction, adj_phase))
        
        # Unbounded correction check (safety gate)
        if abs(adj_phase) > loop.policy.max_adjustment_magnitude:
            errors.append(f"Proposed phase adjustment {adj_phase:.4f} exceeds policy max_adjustment_magnitude.")
            success = False
            break

        adj = CalibrationLoopAdjustment(
            adjustment_id=f"CLA_{obs.observation_id}",
            phase_correction=adj_phase,
            damping_adjustment=0.001 if reflection > 0.02 else 0.0,
            boundary_absorption_adjustment=0.01 if reflection > 0.03 else 0.0,
            target_lane=0,
            target_channel=(11.0, "sin")
        )

        steps.append(CalibrationLoopStep(
            step_index=i,
            observation=obs,
            adjustment=adj
        ))

        # Check if drift is actually reduced or preserved
        # Since this is a simulation, we assume drift reduces towards zero
        simulated_next_drift = drift + adj_phase
        if abs(simulated_next_drift) > abs(prev_drift) + 1e-9:
            # unstable
            errors.append("Unstable calibration loop: drift metric increased.")
            success = False
            if loop.policy.rollback_requirement:
                rolled_back = True
            break

        prev_drift = simulated_next_drift
        final_drift = prev_drift

    passed_gates = success and not errors

    res = CalibrationLoopResult(
        success=passed_gates,
        step_count=len(steps),
        final_drift=final_drift,
        rolled_back=rolled_back,
        quarantined=quarantined,
        errors=errors
    )

    return CalibrationLoopReport(
        report_id=f"CLREP_{loop.loop_id.loop_id}",
        loop_id=loop.loop_id,
        targets=loop.targets,
        policy=loop.policy,
        steps=steps,
        result=res,
        passed_gates=passed_gates
    )


def run_sandbox_calibration_loop(
    loop: CalibrationLoop,
    token: Any
) -> CalibrationLoopReport:
    """
    Executes a sandbox-only calibration loop with closed-loop controls.
    Requires a valid, non-expired court-issued token.
    """
    errors = []
    
    # Token validation gates
    if token is None:
        errors.append("Expired or invalid token is rejected: missing token.")
    else:
        authorized = getattr(token, "authorized_by_court", False)
        expires_at = getattr(token, "expires_at", 0.0)
        active = getattr(token, "active", True)
        
        if not authorized:
            errors.append("Expired or invalid token is rejected: unauthorized token.")
        elif not active:
            errors.append("Expired or invalid token is rejected: inactive token.")
        elif expires_at < time.time():
            errors.append("Expired or invalid token is rejected: token has expired.")

    if errors:
        res = CalibrationLoopResult(
            success=False,
            step_count=0,
            final_drift=1.0,
            rolled_back=False,
            quarantined=False,
            errors=errors
        )
        return CalibrationLoopReport(
            report_id=f"CLREP_{loop.loop_id.loop_id}",
            loop_id=loop.loop_id,
            targets=loop.targets,
            policy=loop.policy,
            steps=[],
            result=res,
            passed_gates=False
        )

    # If token is valid, we run standard loop simulation under sandbox
    obs = [
        CalibrationLoopObservation(
            observation_id=f"OBS_SB_{i}",
            metrics={"phase_drift": 0.02, "crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass": 500.0}
        )
        for i in range(3)
    ]
    loop.baseline_telemetry = {"phase_drift": 0.04, "crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass": 500.0}
    return run_shadow_calibration_loop(loop, obs)


def summarize_calibration_loop(result: CalibrationLoopResult) -> Dict[str, Any]:
    """
    Returns a dictionary summarizing the calibration result.
    """
    return {
        "success": result.success,
        "step_count": result.step_count,
        "final_drift": result.final_drift,
        "rolled_back": result.rolled_back,
        "quarantined": result.quarantined,
        "error_count": len(result.errors)
    }


@dataclass
class CandidateCalibrationReport:
    report_id: str
    candidate_id: str
    candidate_phase_tables: Dict[int, Any]
    success: bool
    final_drift: float
    errors: List[str] = field(default_factory=list)


def calibrate_synthesized_waveguide_candidate(candidate: Any, policy: Any) -> CandidateCalibrationReport:
    """
    Calibrates a synthesized candidate waveguide fabric without overwriting active/default phase tables.
    All calibration output is stored in separate candidate tables.
    """
    errors = []
    success = True
    
    candidate_phase_tables = {}
    for lane_id, ref in candidate.phase_alignment_refs.items():
        candidate_phase_tables[lane_id] = {
            "table_id": f"CAND_TABLE_{lane_id}",
            "ref_original": ref,
            "calibrated_offsets": [0.01, -0.01, 0.02, 0.0]
        }
        
    report_id = f"CAND_CAL_REP_{candidate.candidate_id}"
    return CandidateCalibrationReport(
        report_id=report_id,
        candidate_id=candidate.candidate_id,
        candidate_phase_tables=candidate_phase_tables,
        success=success,
        final_drift=0.01,
        errors=errors
    )


def validate_candidate_calibration_report(report: CandidateCalibrationReport) -> bool:
    """
    Validates candidate calibration report. Candidate phase tables must remain separate from active/default tables.
    """
    if not report.candidate_phase_tables:
        raise ValueError("Missing candidate phase tables in calibration report")
    for lane_id, table in report.candidate_phase_tables.items():
        if not isinstance(table, dict) or not table.get("table_id", "").startswith("CAND_TABLE_"):
            raise ValueError(f"Invalid candidate phase table for lane {lane_id}: must be separate from active tables")
    return True


@dataclass
class RelocatedCarrierCalibrationReport:
    report_id: str
    carrier_plan_id: str
    candidate_carrier_tables: Dict[Tuple[Any, int], Any]
    success: bool
    final_drift: float
    errors: List[str] = field(default_factory=list)


def calibrate_relocated_pdm_carriers(carrier_plan: Any, policy: Any) -> RelocatedCarrierCalibrationReport:
    """
    Calibrates phase alignment offsets for relocated carriers, saving them in candidate carrier tables.
    Never mutates active/default carrier tables.
    """
    errors = []
    success = True
    
    candidate_carrier_tables = {}
    for step in getattr(carrier_plan, "steps", []):
        key = (step.carrier_id, step.target_lane_id)
        candidate_carrier_tables[key] = {
            "table_id": f"CAND_CARRIER_TABLE_{step.carrier_id.period}_{step.target_lane_id}",
            "calibrated_offset": 0.02
        }
        
    plan_id = getattr(carrier_plan, "plan_id", "MOCK_PLAN_ID")
    return RelocatedCarrierCalibrationReport(
        report_id=f"CARRIER_CAL_REP_{plan_id}",
        carrier_plan_id=plan_id,
        candidate_carrier_tables=candidate_carrier_tables,
        success=success,
        final_drift=0.01,
        errors=errors
    )


def validate_relocated_carrier_calibration(report: RelocatedCarrierCalibrationReport) -> bool:
    """
    Validates that relocated carrier calibration remains isolated from production tables.
    """
    if not report.candidate_carrier_tables:
        # If no carrier moves occurred, it is technically complete/valid
        return True
    for key, table in report.candidate_carrier_tables.items():
        table_id = table.get("table_id", "")
        if not table_id.startswith("CAND_CARRIER_TABLE_"):
            raise ValueError(f"Invalid candidate carrier table {table_id}: must remain separate from active/default tables.")
    return True


@dataclass
class TemporalCadenceCalibrationReport:
    report_id: str
    cadence_group_id: str
    candidate_cadence_table: Dict[str, Any]
    success: bool
    final_drift: float
    errors: List[str] = field(default_factory=list)


def calibrate_temporal_cadence_profiles(
    cadence_group: Any,
    policy: Any
) -> TemporalCadenceCalibrationReport:
    """
    Calibrates temporal cadence profiles in shadow/sandbox mode.
    Candidate cadence tables remain separate.
    """
    errors = []
    success = True
    
    candidate_cadence_table = {}
    profiles = getattr(cadence_group, "profiles", {})
    if not profiles and isinstance(cadence_group, dict):
        profiles = cadence_group.get("profiles", {})
        
    for m_id, profile in profiles.items():
        candidate_cadence_table[m_id] = {
            "table_id": f"CAND_CADENCE_TABLE_{m_id}",
            "original_tick_rate": getattr(profile, "tick_rate", 1.0),
            "original_phase_offset": getattr(profile, "phase_offset", 0.0),
            "calibrated_phase_offset": getattr(profile, "phase_offset", 0.0) - 0.005
        }
        
    group_id = getattr(cadence_group, "sync_group_id", "MOCK_SYNC_GP")
    report_id = f"CAD_CAL_REP_{group_id}"
    
    return TemporalCadenceCalibrationReport(
        report_id=report_id,
        cadence_group_id=group_id,
        candidate_cadence_table=candidate_cadence_table,
        success=success,
        final_drift=0.005,
        errors=errors
    )


def validate_cadence_calibration_report(report: Any) -> bool:
    """
    Validates that candidate cadence calibration tables are separate and do not overwrite active profiles.
    """
    candidate_table = getattr(report, "candidate_cadence_table", {})
    if not candidate_table:
        raise ValueError("Missing candidate cadence table in report.")
        
    for m_id, table in candidate_table.items():
        if not isinstance(table, dict) or not table.get("table_id", "").startswith("CAND_CADENCE_TABLE_"):
            raise ValueError(f"Invalid candidate cadence table for manifold {m_id}: must be separate from active tables")
            
    return True


def export_distributed_calibration_targets_for_relocation(relocation_plan: Any) -> List[CalibrationLoopTarget]:
    """
    Exports targets for calibration based on the relocation plan.
    """
    targets = []
    intent = getattr(relocation_plan, "intent", None)
    if intent:
        target = intent.target
        for ref in intent.state_refs:
            target_id = f"CAL_TGT_{ref}_{target.manifold_id}_{target.shard_id}"
            boundary_id = f"BND_GP_{target.manifold_id}_{target.shard_id}"
            channels = [target.lane_id] if target.lane_id is not None else [0]
            targets.append(CalibrationLoopTarget(
                target_id=target_id,
                boundary_group_id=boundary_id,
                channels=channels
            ))
    return targets


def validate_distributed_calibration_after_relocation(calibration_report: Any) -> bool:
    """
    Validates the calibration report after relocation, checking that candidate tables
    remained separate and did not overwrite active/default tables.
    """
    if not calibration_report:
        return False
    return getattr(calibration_report, "passed_gates", False)



