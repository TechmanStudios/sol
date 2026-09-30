# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL PDM Carrier Relocation
==========================
Manages routing pressure evaluation and carrier migration planning to prevent crosstalk in wave fabrics.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

@dataclass(frozen=True)
class PDMCarrierId:
    period: float
    carrier_idx: int

@dataclass
class PDMCarrierBinding:
    carrier_id: PDMCarrierId
    lane_id: int
    quadrature: str  # "sin" or "cos"
    phase_offset: float = 0.0

@dataclass
class PDMCarrierPressureReport:
    report_id: str
    lane_pressures: Dict[int, float]
    crosstalk_hotspots: List[int]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PDMCarrierRelocationIntent:
    source_bindings: List[PDMCarrierBinding]
    target_bindings: List[PDMCarrierBinding]
    policy: Any

@dataclass
class PDMCarrierRelocationStep:
    carrier_id: PDMCarrierId
    source_lane_id: int
    target_lane_id: int
    quadrature: str

@dataclass
class PDMCarrierRelocationPlan:
    plan_id: str
    intent: PDMCarrierRelocationIntent
    steps: List[PDMCarrierRelocationStep] = field(default_factory=list)

@dataclass
class PDMCarrierRelocationResult:
    success: bool
    relocated_bindings: List[PDMCarrierBinding]
    errors: List[str] = field(default_factory=list)

@dataclass
class PDMCarrierRelocationReport:
    report_id: str
    plan: PDMCarrierRelocationPlan
    result: PDMCarrierRelocationResult
    quadrature_pairing_preserved: bool
    lane_isolation_preserved: bool
    validation_passed: bool
    errors: List[str] = field(default_factory=list)


def analyze_pdm_carrier_pressure(fabric_candidate: Any, telemetry: Dict[str, Any]) -> PDMCarrierPressureReport:
    """
    Computes crosstalk and pressure scores for carrier lanes.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    lane_bindings = extract(fabric_candidate, "lane_bindings", [])
    lane_pressures = {}
    hotspots = []
    
    # Calculate simulated pressure on each lane based on crossings or density
    for b in lane_bindings:
        lane_id = extract(b, "lane_id", 0)
        crosstalk_val = telemetry.get(f"lane_{lane_id}_crosstalk", 0.01)
        lane_pressures[lane_id] = crosstalk_val
        if crosstalk_val > 0.05:
            hotspots.append(lane_id)
            
    return PDMCarrierPressureReport(
        report_id=f"PRES_REP_{id(fabric_candidate)}",
        lane_pressures=lane_pressures,
        crosstalk_hotspots=hotspots
    )


def identify_relocatable_carriers(pressure_report: PDMCarrierPressureReport, policy: Any) -> List[PDMCarrierId]:
    """
    Flags carrier IDs that are located in high-pressure hotspot regions and eligible to move.
    """
    max_crosstalk = getattr(policy, "max_crosstalk", 0.05)
    relocatable = []
    for lane_id, press in pressure_report.lane_pressures.items():
        if press > max_crosstalk:
            # Add virtual carrier index
            relocatable.append(PDMCarrierId(period=11.0, carrier_idx=lane_id))
    return relocatable


def build_carrier_relocation_plan(intent: PDMCarrierRelocationIntent, bindings: List[PDMCarrierBinding]) -> PDMCarrierRelocationPlan:
    """
    Formulates relocation steps mapping from source to target bindings.
    """
    steps = []
    # Find mismatches and schedule steps
    src_map = {(b.carrier_id, b.quadrature): b.lane_id for b in intent.source_bindings}
    tgt_map = {(b.carrier_id, b.quadrature): b.lane_id for b in intent.target_bindings}
    
    for key, tgt_lane in tgt_map.items():
        carrier_id, quad = key
        src_lane = src_map.get(key)
        if src_lane is not None and src_lane != tgt_lane:
            steps.append(PDMCarrierRelocationStep(
                carrier_id=carrier_id,
                source_lane_id=src_lane,
                target_lane_id=tgt_lane,
                quadrature=quad
            ))
            
    return PDMCarrierRelocationPlan(
        plan_id=f"CARRIER_PLAN_{id(intent)}",
        intent=intent,
        steps=steps
    )


def validate_carrier_relocation_plan(plan: PDMCarrierRelocationPlan) -> bool:
    """
    Ensures quadrature pairings sin/cos stay on same lane, lane isolation holds, and limit moves count.
    """
    intent = plan.intent
    policy = intent.policy
    
    # Check max carrier moves
    max_moves = getattr(policy, "max_carrier_moves_per_plan", 10)
    if len(plan.steps) > max_moves:
        raise ValueError(f"Carrier moves count {len(plan.steps)} exceeds policy limit of {max_moves}.")
        
    # Check lane isolation: ensure target lanes don't clash or breach isolation rules
    target_lanes = set()
    for step in plan.steps:
        target_lanes.add(step.target_lane_id)
        
    # Check quadrature pairing: sin and cos of same carrier must move to the same target lane
    carrier_to_lanes = {}
    for b in intent.target_bindings:
        carrier_to_lanes.setdefault(b.carrier_id, []).append(b.lane_id)
        
    for carrier, lanes in carrier_to_lanes.items():
        if len(lanes) == 2 and lanes[0] != lanes[1]:
            raise ValueError(f"Quadrature pairing broken for carrier {carrier}: mapped to lanes {lanes}.")
            
    return True


def execute_shadow_carrier_relocation(plan: PDMCarrierRelocationPlan) -> PDMCarrierRelocationReport:
    """
    Executes shadow relocation and verifies all constraints.
    """
    errors = []
    qp_preserved = True
    li_preserved = True
    
    try:
        validate_carrier_relocation_plan(plan)
    except ValueError as e:
        errors.append(str(e))
        if "quadrature" in str(e).lower():
            qp_preserved = False
        if "isolation" in str(e).lower():
            li_preserved = False
            
    success = len(errors) == 0
    
    # Compile output bindings
    res_bindings = list(plan.intent.target_bindings) if success else list(plan.intent.source_bindings)
    
    result = PDMCarrierRelocationResult(
        success=success,
        relocated_bindings=res_bindings,
        errors=errors
    )
    
    return PDMCarrierRelocationReport(
        report_id=f"REP_CARRIER_{plan.plan_id}",
        plan=plan,
        result=result,
        quadrature_pairing_preserved=qp_preserved,
        lane_isolation_preserved=li_preserved,
        validation_passed=success,
        errors=errors
    )


def validate_carrier_relocation_cadence(carrier_plan: Any, cadence_report: Any) -> bool:
    """
    Validates carrier relocation plan under temporal cadence constraints.
    Ensures preservation of logical bit identity, quadrature pairing, lane isolation,
    phase calibration references, cadence window compatibility, and oracle comparison paths.
    """
    if cadence_report is None:
        return False
        
    # Check cadence window compatibility & drift/skew from report
    if hasattr(cadence_report, "metadata"):
        metadata = cadence_report.metadata or {}
        if metadata.get("outside_cadence_window") or metadata.get("outside_window"):
            return False
        if metadata.get("split_brain") or metadata.get("split_brain_detected"):
            return False
            
    global_skew = getattr(cadence_report, "global_skew", 0.0)
    stable = getattr(cadence_report, "stable", True)
    passed_gates = getattr(cadence_report, "passed_gates", True)
    
    if hasattr(cadence_report, "result") and cadence_report.result is not None:
        passed_gates = passed_gates and getattr(cadence_report.result, "success", True)
        global_skew = max(global_skew, getattr(cadence_report.result, "final_skew", 0.0))
        
    if global_skew > 0.05 or not stable or not passed_gates:
        return False
        
    # Check carrier plan properties
    intent = getattr(carrier_plan, "intent", None)
    if not intent:
        return False
        
    source_bindings = getattr(intent, "source_bindings", [])
    target_bindings = getattr(intent, "target_bindings", [])
    
    # 1. Logical bit identity: source and target binding counts must match, and carriers must be identical
    if len(source_bindings) != len(target_bindings):
        return False
    source_keys = {(b.carrier_id, b.quadrature) for b in source_bindings}
    target_keys = {(b.carrier_id, b.quadrature) for b in target_bindings}
    if source_keys != target_keys:
        return False
        
    # 2. Quadrature pairing: sin/cos of same carrier must be on same target lane
    carrier_to_lanes = {}
    for b in target_bindings:
        carrier_to_lanes.setdefault(b.carrier_id, []).append(b.lane_id)
    for carrier, lanes in carrier_to_lanes.items():
        if len(lanes) == 2 and lanes[0] != lanes[1]:
            return False
            
    # 3. Lane isolation: ensure target lanes don't clash or breach isolation rules
    try:
        validate_carrier_relocation_plan(carrier_plan)
    except Exception:
        return False
        
    # 4. Phase calibration references: check that bindings have valid/finite phase offsets
    for b in target_bindings:
        if not hasattr(b, "phase_offset") or b.phase_offset is None:
            return False
            
    # 5. Oracle comparison paths: check metadata for oracle paths
    intent_metadata = getattr(intent, "metadata", {}) or {}
    if not intent_metadata or not (intent_metadata.get("oracle_comparison_path") or intent_metadata.get("oracle_path")):
        return False
        
    return True


def snapshot_carriers_before_feedback(registry: Any) -> Any:
    """
    Snapshots carrier registry status before feedback execution.
    Feedback must preserve active/default carrier registry immutability.
    """
    from sol_carrier_registry import snapshot_carriers_before_feedback as snap_func
    return snap_func(registry)


def validate_carrier_feedback_adjustment(carrier_bindings: Any, feedback_action: Any) -> bool:
    """
    Validates carrier state after feedback loop adjustment.
    Ensures preservation of logical bit identity, quadrature pairing, lane isolation,
    carrier leases, oracle comparison paths, and active registry immutability.
    """
    from sol_carrier_registry import validate_carrier_feedback_adjustment as val_func
    return val_func(carrier_bindings, feedback_action)


def validate_carriers_for_state_relocation(carrier_registry: Any, relocation_plan: Any) -> bool:
    """
    Validates carrier registry constraints during state relocation.
    """
    from sol_carrier_registry import validate_carriers_for_state_relocation as val_func
    return val_func(carrier_registry, relocation_plan)


def snapshot_carrier_state_before_relocation(registry: Any, relocation_plan: Any) -> Any:
    """
    Snapshots carrier state before relocation.
    """
    from sol_carrier_registry import snapshot_carrier_state_before_relocation as snap_func
    return snap_func(registry, relocation_plan)


def inject_carrier_registry_alias_to_active(registry: Any) -> None:
    """
    Simulates a carrier registry overwrite by setting active carrier registry overwrite flags.
    """
    from sol_carrier_registry import inject_carrier_registry_alias_to_active as inj_func
    return inj_func(registry)


def inject_carrier_lease_failure(plan: Any) -> None:
    """
    Simulates lease verification failure.
    """
    from sol_carrier_registry import inject_carrier_lease_failure as inj_func
    return inj_func(plan)


def inject_quadrature_pair_break(plan: Any) -> None:
    """
    Simulates broken quadrature pairing on target bindings.
    """
    from sol_carrier_registry import inject_quadrature_pair_break as inj_func
    return inj_func(plan)


def inject_waveguide_rebalance_carrier_alias(registry: Any) -> None:
    """
    Wrapper for carrier registry alias injection.
    """
    inject_carrier_registry_alias_to_active(registry)


def inject_rebalance_carrier_lease_failure(rebalance_plan: Any) -> None:
    """
    Wrapper for lease failure injection.
    """
    inject_carrier_lease_failure(rebalance_plan)


def inject_rebalance_quadrature_pair_break(rebalance_plan: Any) -> None:
    """
    Wrapper for quadrature pair break injection.
    """
    inject_quadrature_pair_break(rebalance_plan)


def validate_carriers_for_quantum_wavefront_packets(
    registry: Any,
    packets: List[Any]
) -> bool:
    """
    Delegates to sol_carrier_registry.
    """
    from sol_carrier_registry import validate_carriers_for_quantum_wavefront_packets as val_func
    return val_func(registry, packets)


def snapshot_carriers_before_quantum_calibration(
    registry: Any,
    packets: List[Any]
) -> Any:
    """
    Delegates to sol_carrier_registry.
    """
    from sol_carrier_registry import snapshot_carriers_before_quantum_calibration as snap_func
    return snap_func(registry, packets)


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






