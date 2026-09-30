# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL PDM Waveguide Gated Execution Plan and Demodulation
======================================================
Compiles WideWordInstructionResults into PDM wave traces, executes demodulation,
and compiles execution reports with parity metrics.
"""

import math
import time
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from sol_wideword_instruction import WideWordInstructionResult, InstructionGateReport
from sol_pdm_byte_slice import PDMEncodedByte
from sol_lane_fabric import LaneFabric

@dataclass
class PDMExecutionPlan:
    instruction_result: WideWordInstructionResult
    encoded_word: List[PDMEncodedByte]
    lane_fabric: LaneFabric
    width: int
    lane_count: int
    channel_count: int = 0
    carrier_map: List[Dict[str, Any]] = field(default_factory=list)
    phase_table_reference: Optional[Any] = None
    pml_profile_reference: Optional[Any] = None
    expected_oracle_result: int = 0

@dataclass
class PDMExecutionTrace:
    plan: PDMExecutionPlan
    t_values: List[float]
    lane_signals: List[List[float]]

@dataclass
class PDMDemodulationResult:
    demodulated_value: int
    lane_values: List[int]
    matches_oracle: bool
    demodulated_amplitudes: List[Dict[str, float]]

@dataclass
class PDMExecutionReport:
    instruction_id: str
    op: str
    width: int
    lane_count: int
    passed_gates: bool
    oracle_match: bool
    demodulation_result: PDMDemodulationResult
    gate_report: InstructionGateReport
    trace: PDMExecutionTrace
    timestamp: float
    reproducibility_hash: str

def build_execution_plan(instruction_result: WideWordInstructionResult, lane_fabric: LaneFabric) -> PDMExecutionPlan:
    """
    Encodes the reference WideWord instruction result into a PDM multi-lane word format.
    """
    from dataclasses import field
    res_val = instruction_result.result
    encoded_word = lane_fabric.encode_word(res_val)
    
    channel_count = len(encoded_word) * 8
    
    carrier_map = []
    for lane in lane_fabric.lanes:
        carrier_map.extend(lane.channel_map())
        
    phase_table_reference = [lane.phase_table for lane in lane_fabric.lanes]
    
    from sol_waveguide_boundary import WaveguideBoundary
    boundary = WaveguideBoundary()
    pml_profile_reference = [
        boundary.build_pml_profile(lane_id=lane.lane_id)
        for lane in lane_fabric.lanes
    ]
    
    return PDMExecutionPlan(
        instruction_result=instruction_result,
        encoded_word=encoded_word,
        lane_fabric=lane_fabric,
        width=instruction_result.instruction.width,
        lane_count=instruction_result.instruction.lane_count,
        channel_count=channel_count,
        carrier_map=carrier_map,
        phase_table_reference=phase_table_reference,
        pml_profile_reference=pml_profile_reference,
        expected_oracle_result=res_val
    )

def modulate_plan(
    plan: PDMExecutionPlan,
    t_values: List[float],
    envelope_func: Optional[Callable[[float], float]] = None
) -> PDMExecutionTrace:
    """
    Samples the multi-lane PDM encoded wave packet signals over discrete time steps.
    """
    fabric = plan.lane_fabric
    lane_signals = fabric.sample_word_wave_packet(plan.encoded_word, t_values, envelope_func)
    return PDMExecutionTrace(
        plan=plan,
        t_values=t_values,
        lane_signals=lane_signals
    )

def demodulate_trace(trace: PDMExecutionTrace) -> PDMDemodulationResult:
    """
    Demodulates the wave trace signals back into logical bit values using orthogonal reference carrier projection.
    """
    plan = trace.plan
    fabric = plan.lane_fabric
    t_values = trace.t_values
    lane_signals = trace.lane_signals

    demodulated_amplitudes = []
    lane_values = []

    for lane_idx in range(fabric.num_lanes):
        lane = fabric.lanes[lane_idx]
        signal = lane_signals[lane_idx]

        # Use encode_byte with dummy values to extract channels and reference settings
        encoded_byte = lane.encode_byte(0xFF)
        lane_amps = {}
        lane_val = 0
        N = len(t_values)

        for ch in encoded_byte.channels:
            proj_sum = 0.0
            for t, s_val in zip(t_values, signal):
                angle = ch.angular_frequency * t + ch.phase
                ref = math.sin(angle) if ch.quadrature == "sin" else math.cos(angle)
                proj_sum += s_val * ref

            est_amp = (2.0 / N) * proj_sum if N > 0 else 0.0
            key = f"P_{ch.carrier_period}_{ch.quadrature}"
            lane_amps[key] = est_amp

            # Set the bit as active if amplitude is above threshold
            if est_amp > 0.5:
                bit_pos = ch.bit_index - lane.bit_offset
                lane_val |= (1 << bit_pos)

        demodulated_amplitudes.append(lane_amps)
        lane_values.append(lane_val)

    # Reconstruct final wide-word value
    demodulated_value = 0
    for i, lv in enumerate(lane_values):
        demodulated_value |= (lv << (i * 8))

    oracle_value = plan.instruction_result.result
    matches_oracle = demodulated_value == oracle_value

    return PDMDemodulationResult(
        demodulated_value=demodulated_value,
        lane_values=lane_values,
        matches_oracle=matches_oracle,
        demodulated_amplitudes=demodulated_amplitudes
    )

def compare_demodulated_to_oracle(result: PDMDemodulationResult, oracle_value: int) -> bool:
    """
    Verifies that the demodulated wide-word matches the reference integer oracle.
    """
    return result.demodulated_value == oracle_value

def capture_rollback_snapshot(target_context: Any) -> Any:
    """
    Captures a rollback snapshot of the target_context's phase tables/calibrated phase alignments.
    """
    import copy
    import time
    from coding_library.sovereign_domain.frontier_bridge import RollbackSnapshot

    snapshot_data = {}
    if hasattr(target_context, "lanes"):
        for lane in target_context.lanes:
            lane_snap = {
                "phase_table": copy.deepcopy(lane.phase_table),
                "calibrated_phases": copy.deepcopy(lane.calibrated_phases),
                "damping": getattr(lane, "damping", 0.20)
            }
            snapshot_data[lane.lane_id] = lane_snap
        target_lane = -1
    elif hasattr(target_context, "phase_table"):
        snapshot_data = {
            "phase_table": copy.deepcopy(target_context.phase_table),
            "calibrated_phases": copy.deepcopy(target_context.calibrated_phases),
            "damping": getattr(target_context, "damping", 0.20)
        }
        target_lane = getattr(target_context, "lane_id", 0)
    else:
        snapshot_data = copy.deepcopy(target_context)
        target_lane = getattr(target_context, "lane_id", 0) if hasattr(target_context, "lane_id") else 0

    return RollbackSnapshot(
        snapshot_id=f"SNAP_{int(time.time())}",
        target_lane=target_lane,
        phase_table_snapshot=snapshot_data,
        timestamp=time.time(),
        metadata={"type": type(target_context).__name__}
    )

def restore_rollback_snapshot(snapshot: Any, target_context: Any = None) -> None:
    """
    Restores target_context phase tables/damping state using the snapshot data.
    """
    import copy
    if target_context is None:
        return

    snapshot_data = snapshot.phase_table_snapshot

    if hasattr(target_context, "lanes") and isinstance(snapshot_data, dict):
        for lane in target_context.lanes:
            if lane.lane_id in snapshot_data:
                lane_snap = snapshot_data[lane.lane_id]
                lane.phase_table = copy.deepcopy(lane_snap["phase_table"])
                lane.calibrated_phases = copy.deepcopy(lane_snap["calibrated_phases"])
                if hasattr(lane, "damping") and "damping" in lane_snap:
                    lane.damping = lane_snap["damping"]
    elif hasattr(target_context, "phase_table") and isinstance(snapshot_data, dict) and "phase_table" in snapshot_data:
        target_context.phase_table = copy.deepcopy(snapshot_data["phase_table"])
        target_context.calibrated_phases = copy.deepcopy(snapshot_data["calibrated_phases"])
        if hasattr(target_context, "damping") and "damping" in snapshot_data:
            target_context.damping = snapshot_data["damping"]

def execute_live_pdm_mutation(plan: Any, token: Any, sandbox: bool = True) -> Any:
    """
    Executes a bounded live PDM mutation on the plan's lane fabric.
    Checks token validity, sandbox mode, mutation count limits, and channel/lane bounds.
    Captures a rollback snapshot before mutation, performs the mutation, and returns a LiveMutationResult.
    """
    from coding_library.sovereign_domain.frontier_bridge import (
        LiveMutationRequest,
        LiveMutationResult
    )

    req = LiveMutationRequest(
        request_id=f"REQ_{token.token_id if token else 'unknown'}",
        candidate_correction=None,
        shadow_report=None,
        ranger_evidence=None,
        sandbox=sandbox,
        timestamp=time.time()
    )

    # 1. Gate check: sandbox_only / no_default_live_control
    if not sandbox:
        return LiveMutationResult(
            success=False,
            mutation_request=req,
            token=token,
            rollback_snapshot=None,
            post_mutation_drift=0.0,
            post_mutation_trace=None,
            quarantine_recommended=False,
            error_message="Live mutation rejected: sandbox_only gate failed. Unrestricted production mutation is blocked."
        )

    # 2. Gate check: valid_live_control_token
    if token is None or not token.active or token.token_id == "UNAUTHORIZED_TOKEN":
        return LiveMutationResult(
            success=False,
            mutation_request=req,
            token=token,
            rollback_snapshot=None,
            post_mutation_drift=0.0,
            post_mutation_trace=None,
            quarantine_recommended=False,
            error_message="Live mutation rejected: valid_live_control_token gate failed."
        )

    # 3. Gate check: court_authorized
    if not token.authorized_by_court:
        return LiveMutationResult(
            success=False,
            mutation_request=req,
            token=token,
            rollback_snapshot=None,
            post_mutation_drift=0.0,
            post_mutation_trace=None,
            quarantine_recommended=False,
            error_message="Live mutation rejected: court_authorized gate failed."
        )

    # 4. Gate check: token sandbox match
    if not token.sandbox_only:
        return LiveMutationResult(
            success=False,
            mutation_request=req,
            token=token,
            rollback_snapshot=None,
            post_mutation_drift=0.0,
            post_mutation_trace=None,
            quarantine_recommended=False,
            error_message="Live mutation rejected: token sandbox flag mismatch."
        )

    # 5. Extract target lane
    fabric = plan.lane_fabric
    target_lane_id = token.target_lane

    # Validate target lane bounds
    if target_lane_id < 0 or target_lane_id >= len(fabric.lanes):
        return LiveMutationResult(
            success=False,
            mutation_request=req,
            token=token,
            rollback_snapshot=None,
            post_mutation_drift=0.0,
            post_mutation_trace=None,
            quarantine_recommended=True,
            error_message=f"Live mutation rejected: target lane {target_lane_id} out of bounds."
        )

    target_lane = fabric.lanes[target_lane_id]

    # 6. Gate check: mutation count limits
    mutation_count = getattr(target_lane, "_mutation_count", 0)
    if mutation_count >= token.max_mutations:
        return LiveMutationResult(
            success=False,
            mutation_request=req,
            token=token,
            rollback_snapshot=None,
            post_mutation_drift=0.0,
            post_mutation_trace=None,
            quarantine_recommended=True,
            error_message="Live mutation rejected: mutation_count_within_bounds gate failed."
        )

    # 7. Gate check: delta bounds
    if token.correction_type == "phase":
        if abs(token.bounded_delta) > 0.05:
            return LiveMutationResult(
                success=False,
                mutation_request=req,
                token=token,
                rollback_snapshot=None,
                post_mutation_drift=0.0,
                post_mutation_trace=None,
                quarantine_recommended=False,
                error_message="Live mutation rejected: phase_delta_within_bounds gate failed."
            )
    elif token.correction_type == "damping":
        if abs(token.bounded_delta) > 0.01:
            return LiveMutationResult(
                success=False,
                mutation_request=req,
                token=token,
                rollback_snapshot=None,
                post_mutation_drift=0.0,
                post_mutation_trace=None,
                quarantine_recommended=False,
                error_message="Live mutation rejected: damping_delta_within_bounds gate failed."
            )

    # 8. Capture rollback snapshot before mutation
    snapshot = capture_rollback_snapshot(fabric)

    # 9. Gate check: rollback snapshot present
    if snapshot is None:
        return LiveMutationResult(
            success=False,
            mutation_request=req,
            token=token,
            rollback_snapshot=None,
            post_mutation_drift=0.0,
            post_mutation_trace=None,
            quarantine_recommended=False,
            error_message="Live mutation rejected: rollback_snapshot_present gate failed."
        )

    # 10. Perform mutation
    from sol_phase_alignment import apply_candidate_phase_correction, build_default_phase_table
    if target_lane.phase_table is None:
        target_lane.phase_table = build_default_phase_table(target_lane.lane_id, target_lane.periods)

    if token.correction_type == "phase":
        target_lane.phase_table = apply_candidate_phase_correction(target_lane.phase_table, token)
    elif token.correction_type == "damping":
        current_damping = getattr(target_lane, "damping", 0.20)
        target_lane.damping = current_damping + token.bounded_delta

    # Increment mutation count
    target_lane._mutation_count = mutation_count + 1

    # Re-modulate and compute post-mutation drift
    t_values = [i * 0.1 for i in range(10000)]
    try:
        new_plan = PDMExecutionPlan(
            instruction_result=plan.instruction_result,
            encoded_word=fabric.encode_word(plan.instruction_result.result),
            lane_fabric=fabric,
            width=plan.width,
            lane_count=plan.lane_count
        )
        post_trace = modulate_plan(new_plan, t_values)
        post_demod = demodulate_trace(post_trace)

        # Calculate post-mutation drift
        expected_table = build_default_phase_table(target_lane_id, target_lane.periods)
        from sol_phase_alignment import observe_phase_drift
        drift_obs = observe_phase_drift(expected_table, target_lane.phase_table)
        post_drift = drift_obs.max_phase_error

        success = post_demod.matches_oracle
        quarantine = not success or post_drift > 0.05

        return LiveMutationResult(
            success=success,
            mutation_request=req,
            token=token,
            rollback_snapshot=snapshot,
            post_mutation_drift=post_drift,
            post_mutation_trace=post_trace,
            quarantine_recommended=quarantine,
            error_message=None if success else "Post-mutation demodulation failed to match oracle."
        )
    except Exception as e:
        return LiveMutationResult(
            success=False,
            mutation_request=req,
            token=token,
            rollback_snapshot=snapshot,
            post_mutation_drift=1.0,
            post_mutation_trace=None,
            quarantine_recommended=True,
            error_message=f"Post-mutation evaluation failure: {str(e)}"
        )
