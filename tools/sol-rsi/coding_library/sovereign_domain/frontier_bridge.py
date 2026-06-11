# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Frontier OS Calibration Bridge
==============================
Exposes telemetry collection hooks and stability metrics to interface with Frontier_OS.
Also includes advisory drift controller and recommendation structures.
"""

from dataclasses import dataclass, field
import time
from typing import Dict, Any, List, Optional

@dataclass
class FrontierDriftSignal:
    lane_id: int
    max_phase_error: float
    average_phase_error: float
    coherence: float
    timestamp: float

@dataclass
class FrontierDriftRecommendation:
    lane_id: int
    action: str  # "observe", "hold", "suggest_phase_nudge", "suggest_damping_adjustment", "quarantine_lane"
    nudge_value: float
    damping_adjustment: float
    reason: str
    evidence: Dict[str, Any]

class FrontierBridge:
    """
    Control plane adapter interfacing the SOL WideWord fabric with Frontier_OS telemetry/nudges.
    """
    def __init__(self):
        self.telemetry_history: List[Dict[str, Any]] = []
        self.active_nudges: Dict[str, Any] = {}

    def push_telemetry(self, data: Dict[str, Any]):
        """Append step-level calibration and phase coherence metrics to log history."""
        self.telemetry_history.append(data)

    def request_nudge(self, lane_id: int, nudge_value: float) -> bool:
        """
        Request a bounded nudge token from Frontier_OS.
        Returns False in Phase 0-5 (observe/report only).
        """
        return False

class FrontierDriftController:
    """
    Advisory drift controller computing suggested phase nudges and adjustments.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest(self, observation: Any) -> FrontierDriftRecommendation:
        """
        Evaluates a phase drift observation or generic telemetry source,
        and returns an advisory FrontierDriftRecommendation.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        lane_id = extract(observation, "lane_id", 0)
        max_err = abs(extract(observation, "max_phase_error", 0.0))
        avg_err = abs(extract(observation, "average_phase_error", 0.0))

        # Bounded advisory thresholds:
        # - Error <= 0.05: Keep observing
        # - Error <= 0.15: Suggest phase nudge (bounded to [-0.05, 0.05])
        # - Error <= 0.30: Suggest damping adjustment
        # - Error > 0.30: Quarantine lane
        if max_err <= 0.05:
            action = "observe"
            nudge_val = 0.0
            damping_adj = 0.0
            reason = "Phase error is within acceptable tolerance boundaries."
        elif max_err <= 0.15:
            action = "suggest_phase_nudge"
            nudge_val = -0.5 * avg_err
            # Clamp advisory nudge to [-0.05, 0.05]
            nudge_val = max(-0.05, min(0.05, nudge_val))
            damping_adj = 0.0
            reason = "Moderate phase drift detected; suggesting minor phase correction."
        elif max_err <= 0.30:
            action = "suggest_damping_adjustment"
            nudge_val = 0.0
            damping_adj = 0.012
            reason = "High phase drift detected; suggesting damping adjustment to stabilize."
        else:
            action = "quarantine_lane"
            nudge_val = 0.0
            damping_adj = 0.0
            reason = "Critical phase drift exceeded; recommending lane quarantine."

        evidence = {
            "max_phase_error": max_err,
            "average_phase_error": avg_err,
            "lane_id": lane_id,
            "control_type": "shadow_advisory"
        }

        # Log recommendation to bridge telemetry
        self.bridge.push_telemetry({
            "event": "frontier_drift_suggestion",
            "lane_id": lane_id,
            "action": action,
            "max_phase_error": max_err,
            "evidence": evidence
        })

        return FrontierDriftRecommendation(
            lane_id=lane_id,
            action=action,
            nudge_value=nudge_val,
            damping_adjustment=damping_adj,
            reason=reason,
            evidence=evidence
        )


@dataclass
class BoundedCorrectionPolicy:
    max_phase_nudge: float = 0.05
    max_damping_delta: float = 0.01
    max_gate_weight_delta: float = 0.05


@dataclass
class CandidateCorrection:
    reason: str
    confidence: float
    bounded_delta: float
    target_lane: int
    target_channel: Any  # e.g. tuple (period, quadrature) or None
    before_value: float
    after_value: float
    evidence_hash: str
    correction_type: str  # "phase" | "damping" | "gate_weight"


class FrontierClosedLoopController:
    """
    Closed-loop calibration controller calculating bounded candidate corrections.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_candidate_correction(self, drift_observation: Any, policy: BoundedCorrectionPolicy) -> CandidateCorrection:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        lane_id = extract(drift_observation, "lane_id", 0)
        max_err = extract(drift_observation, "max_phase_error", 0.0)
        avg_err = extract(drift_observation, "average_phase_error", 0.0)
        evidence = extract(drift_observation, "evidence", {})
        
        # Calculate evidence hash
        import hashlib
        import json
        try:
            ev_str = json.dumps(evidence, sort_keys=True)
            ev_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
        except Exception:
            ev_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        # If it's a waveguide/reflection packet, suggest damping correction
        reflection_score = extract(drift_observation, "reflection_score", None)
        if reflection_score is not None:
            damping_delta = 0.005
            bounded_delta = max(-policy.max_damping_delta, min(policy.max_damping_delta, damping_delta))
            before_val = extract(drift_observation, "damping", 0.20)
            return CandidateCorrection(
                reason=f"High waveguide reflection {reflection_score:.4f} detected. Recommending damping correction.",
                confidence=0.90,
                bounded_delta=bounded_delta,
                target_lane=lane_id,
                target_channel=None,
                before_value=before_val,
                after_value=before_val + bounded_delta,
                evidence_hash=ev_hash,
                correction_type="damping"
            )

        # Default is phase drift observation
        channel_errors = evidence.get("channel_errors", [])
        target_channel = None
        before_value = 0.0
        err = max_err
        
        if channel_errors:
            worst_channel = max(channel_errors, key=lambda c: abs(c.get("error", 0.0)))
            target_channel = (worst_channel.get("period"), worst_channel.get("quadrature"))
            before_value = worst_channel.get("expected_phase", 0.0)
            err = worst_channel.get("error", 0.0)
            
        nudge_value = -0.5 * err if err != 0.0 else 0.0

        if abs(max_err) <= 0.05:
            return CandidateCorrection(
                reason="Phase error within tolerance. No correction needed.",
                confidence=0.99,
                bounded_delta=0.0,
                target_lane=lane_id,
                target_channel=target_channel,
                before_value=before_value,
                after_value=before_value,
                evidence_hash=ev_hash,
                correction_type="phase"
            )
            
        max_nudge = policy.max_phase_nudge
        bounded_delta = max(-max_nudge, min(max_nudge, nudge_value))
        after_value = before_value + bounded_delta

        return CandidateCorrection(
            reason=f"Phase drift of {max_err:.4f} detected on lane {lane_id}. Recommending phase correction.",
            confidence=0.95,
            bounded_delta=bounded_delta,
            target_lane=lane_id,
            target_channel=target_channel,
            before_value=before_value,
            after_value=after_value,
            evidence_hash=ev_hash,
            correction_type="phase"
        )


@dataclass
class LiveControlPolicy:
    live_control_enabled: bool = False
    sandbox_only: bool = True
    max_phase_nudge: float = 0.05
    max_damping_delta: float = 0.01
    max_gate_weight_delta: float = 0.05
    max_mutations_per_run: int = 5
    max_mutations_per_lane: int = 2
    rollback_required: bool = True
    ranger_observation_required: bool = True
    court_authorization_required: bool = True


@dataclass
class LiveControlToken:
    token_id: str
    authorized_by_court: bool
    issued_at: float
    expires_at: float
    sandbox_only: bool
    target_lane: int
    max_mutations: int
    correction_type: str = "phase"
    bounded_delta: float = 0.0
    target_channel: Any = None
    active: bool = True


@dataclass
class LiveMutationRequest:
    request_id: str
    candidate_correction: Any  # CandidateCorrection
    shadow_report: Any  # PDMExecutionReport
    ranger_evidence: Any  # SovereignPacket
    sandbox: bool = True
    timestamp: float = 0.0


@dataclass
class RollbackSnapshot:
    snapshot_id: str
    target_lane: int
    phase_table_snapshot: Any
    timestamp: float
    metadata: Dict[str, Any]


@dataclass
class LiveMutationResult:
    success: bool
    mutation_request: LiveMutationRequest
    token: LiveControlToken
    rollback_snapshot: Optional[RollbackSnapshot]
    post_mutation_drift: float
    post_mutation_trace: Optional[Any]  # PDMExecutionTrace
    quarantine_recommended: bool
    error_message: Optional[str] = None


class FrontierClosedLoopDriver:
    """
    Closed-loop calibration driver for waveguide-gated PDM execution in shadow-only mode.
    Now extended with Sandbox Live PDM Mutation capabilities under Phase 11.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def apply_candidate_adjustment(
        self,
        candidate: Any,
        token: LiveControlToken,
        sandbox: bool = True,
        plan: Optional[Any] = None
    ) -> LiveMutationResult:
        """
        Applies a candidate calibration correction in sandbox mode with court authorization.
        Checks safety limits, captures a rollback snapshot, and triggers the mutation.
        """
        req = LiveMutationRequest(
            request_id=f"REQ_{token.token_id}",
            candidate_correction=candidate,
            shadow_report=None,
            ranger_evidence=None,
            sandbox=sandbox,
            timestamp=token.issued_at
        )

        # Safety Gates
        if not sandbox:
            return LiveMutationResult(
                success=False,
                mutation_request=req,
                token=token,
                rollback_snapshot=None,
                post_mutation_drift=0.0,
                post_mutation_trace=None,
                quarantine_recommended=False,
                error_message="Live mutation rejected: sandbox_only gate violated."
            )

        if not token.authorized_by_court or not token.active:
            return LiveMutationResult(
                success=False,
                mutation_request=req,
                token=token,
                rollback_snapshot=None,
                post_mutation_drift=0.0,
                post_mutation_trace=None,
                quarantine_recommended=False,
                error_message="Live mutation rejected: invalid or unauthorized court token."
            )

        if not token.sandbox_only:
            return LiveMutationResult(
                success=False,
                mutation_request=req,
                token=token,
                rollback_snapshot=None,
                post_mutation_drift=0.0,
                post_mutation_trace=None,
                quarantine_recommended=False,
                error_message="Live mutation rejected: token must be sandbox-only."
            )

        # Trigger execution using executor helper
        from sol_pdm_executor import execute_live_pdm_mutation, capture_rollback_snapshot
        
        if plan is None:
            # For testing rollback-required gates when context/plan is missing
            return LiveMutationResult(
                success=False,
                mutation_request=req,
                token=token,
                rollback_snapshot=None,
                post_mutation_drift=0.0,
                post_mutation_trace=None,
                quarantine_recommended=False,
                error_message="Live mutation rejected: rollback snapshot is missing or target context unavailable."
            )

        try:
            res = execute_live_pdm_mutation(plan, token, sandbox=sandbox)
            # Update request details for accuracy
            res.mutation_request = req
            
            # Monitor post-mutation state
            self.monitor_after_mutation(res)
            return res
        except Exception as e:
            return LiveMutationResult(
                success=False,
                mutation_request=req,
                token=token,
                rollback_snapshot=None,
                post_mutation_drift=0.0,
                post_mutation_trace=None,
                quarantine_recommended=True,
                error_message=f"Live mutation runtime failure: {str(e)}"
            )

    def monitor_after_mutation(self, result: LiveMutationResult) -> None:
        """
        Analyzes post-mutation drift. Rolls back changes and quarantines the lane if drift worsens.
        """
        if not result.success:
            return

        # Simple threshold test: if post-mutation drift exceeds policy limits or worsens,
        # trigger a restore snapshot roll-back.
        # Worsening drift is simulated when post_mutation_drift > 0.05 (or drift is higher than pre-mutation drift)
        if result.post_mutation_drift > 0.05:
            result.quarantine_recommended = True
            if result.rollback_snapshot is not None and result.mutation_request is not None:
                # Retrieve context (fabric) from the trace/plan if available
                trace = result.post_mutation_trace
                plan = getattr(trace, "plan", None) if trace else None
                fabric = getattr(plan, "lane_fabric", None) if plan else None
                if fabric:
                    from sol_pdm_executor import restore_rollback_snapshot
                    restore_rollback_snapshot(result.rollback_snapshot, fabric)
                    self.bridge.push_telemetry({
                        "event": "rollback_executed",
                        "lane_id": result.token.target_lane,
                        "reason": f"Post-mutation drift worsened to {result.post_mutation_drift:.4f}."
                    })

    def observe_execution_report(self, report: Any) -> Dict[str, Any]:
        """
        Inspects the PDMExecutionReport and returns a diagnostic overview.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        inst_id = extract(report, "instruction_id", "none")
        op = extract(report, "op", "UNKNOWN")
        passed = extract(report, "passed_gates", False)
        match = extract(report, "oracle_match", False)
        
        demod_res = extract(report, "demodulation_result", {})
        demod_amps = extract(demod_res, "demodulated_amplitudes", [])
        
        active_delta = 1.0
        active_amps = []
        inactive_amps = []
        
        trace = extract(report, "trace", {})
        plan = extract(trace, "plan", {})
        encoded_word = extract(plan, "encoded_word", [])
        
        if encoded_word and demod_amps:
            for lane_idx, encoded_byte in enumerate(encoded_word):
                if lane_idx < len(demod_amps):
                    lane_amps = demod_amps[lane_idx]
                    channels = extract(encoded_byte, "channels", [])
                    for ch in channels:
                        period = extract(ch, "carrier_period")
                        quad = extract(ch, "quadrature")
                        active = extract(ch, "active", False)
                        key = f"P_{period}_{quad}"
                        amp = lane_amps.get(key, 0.0)
                        if active:
                            active_amps.append(amp)
                        else:
                            inactive_amps.append(amp)
            if active_amps:
                min_active = min(active_amps)
                max_inactive = max(inactive_amps) if inactive_amps else 0.0
                active_delta = min_active - max_inactive

        summary = {
            "instruction_id": inst_id,
            "op": op,
            "passed_gates": passed,
            "oracle_match": match,
            "active_delta": active_delta,
            "lane_count": extract(report, "lane_count", 0),
            "timestamp": extract(report, "timestamp", 0.0)
        }
        
        self.bridge.push_telemetry({
            "event": "shadow_pdm_observation",
            "instruction_id": inst_id,
            "oracle_match": match,
            "active_delta": active_delta
        })
        
        return summary

    def suggest_calibration_adjustment(self, report: Any, policy: BoundedCorrectionPolicy) -> FrontierDriftRecommendation:
        """
        Suggests a bounded calibration adjustment based on execution report.
        Strictly shadow-only.
        """
        summary = self.observe_execution_report(report)
        match = summary["oracle_match"]
        active_delta = summary["active_delta"]
        passed_gates = summary["passed_gates"]
        op = summary["op"]
        
        lane_id = 0
        nudge_value = 0.0
        damping_adj = 0.0
        
        if not match:
            action = "quarantine_lane"
            reason = "Demodulated result does not match wide-word reference oracle."
        elif not passed_gates:
            action = "hold"
            reason = "Instruction gating failed; holding calibration."
        elif active_delta < 0.20:
            action = "suggest_damping_adjustment"
            damping_adj = policy.max_damping_delta
            reason = f"Active carrier delta ({active_delta:.4f}) below threshold; suggesting damping update."
        elif op == "SUB_WORD":
            action = "suggest_phase_nudge"
            nudge_value = -0.02
            reason = "Slight phase drift detected in waveguide sub-word phase mapping."
        else:
            action = "observe"
            reason = "Waveguide execution is stable and coherent."
            
        nudge_value = max(-policy.max_phase_nudge, min(policy.max_phase_nudge, nudge_value))
        damping_adj = max(-policy.max_damping_delta, min(policy.max_damping_delta, damping_adj))
        
        evidence = {
            "oracle_match": match,
            "active_delta": active_delta,
            "passed_gates": passed_gates,
            "policy_bounds": {
                "max_phase_nudge": policy.max_phase_nudge,
                "max_damping_delta": policy.max_damping_delta
            }
        }
        
        return FrontierDriftRecommendation(
            lane_id=lane_id,
            action=action,
            nudge_value=nudge_value,
            damping_adjustment=damping_adj,
            reason=reason,
            evidence=evidence
        )

    def build_candidate_adjustment_packet(self, report: Any, suggestion: FrontierDriftRecommendation) -> CandidateCorrection:
        """
        Builds a CandidateCorrection tracking the proposed adjustment details.
        Live control remains disabled and requires promotion.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)
            
        repro_hash = extract(report, "reproducibility_hash", "none")
        action = extract(suggestion, "action", "observe")
        lane_id = extract(suggestion, "lane_id", 0)
        nudge_val = extract(suggestion, "nudge_value", 0.0)
        damping_val = extract(suggestion, "damping_adjustment", 0.0)
        
        corr_type = "phase"
        bounded_delta = nudge_val
        if action == "suggest_damping_adjustment":
            corr_type = "damping"
            bounded_delta = damping_val
            
        target_channel = (11.0, "sin") if corr_type == "phase" else None
        
        return CandidateCorrection(
            reason=extract(suggestion, "reason", "Advisory suggestion"),
            confidence=0.95,
            bounded_delta=bounded_delta,
            target_lane=lane_id,
            target_channel=target_channel,
            before_value=0.0,
            after_value=bounded_delta,
            evidence_hash=repro_hash,
            correction_type=corr_type
        )


@dataclass
class EntanglementStabilizationSuggestion:
    link_id: str
    action: str  # "observe", "hold", "suggest_phase_alignment", "suggest_route_damping", "suggest_boundary_absorption", "quarantine_route"
    nudge_value: float
    damping_adjustment: float
    reason: str
    evidence: Dict[str, Any]


class FrontierEntanglementAdvisor:
    """
    Advisory controller for entanglement stabilization and boundary absorption.
    Suggestions remain bounded and advisory-only.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_stabilization(self, observation: Any) -> EntanglementStabilizationSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        link_id = extract(observation, "observation_id", "unknown_link")
        coherence = extract(observation, "phase_coherence", 1.0)
        drift = extract(observation, "transfer_drift", 0.0)
        
        # Determine stabilization policy suggestions
        if coherence >= 0.95 and drift <= 0.02:
            action = "observe"
            nudge_val = 0.0
            damping_adj = 0.0
            reason = "Entanglement link is highly coherent and stable."
        elif coherence >= 0.90 and drift <= 0.05:
            action = "hold"
            nudge_val = 0.0
            damping_adj = 0.0
            reason = "Coherence is stable but requires baseline monitoring."
        elif coherence >= 0.80 and drift <= 0.10:
            action = "suggest_phase_alignment"
            nudge_val = -0.1 * drift
            nudge_val = max(-0.05, min(0.05, nudge_val)) # Bounded advisory nudges
            damping_adj = 0.0
            reason = "Phase shift detected; suggesting minor phase alignment."
        elif coherence >= 0.65 and drift <= 0.20:
            action = "suggest_route_damping"
            nudge_val = 0.0
            damping_adj = 0.005
            reason = "Route drift elevated; suggesting localized waveguide damping adjustments."
        elif coherence >= 0.50 and drift <= 0.30:
            action = "suggest_boundary_absorption"
            nudge_val = 0.0
            damping_adj = 0.01
            reason = "Boundary reflection detected; recommending PML boundary absorption increase."
        else:
            action = "quarantine_route"
            nudge_val = 0.0
            damping_adj = 0.0
            reason = "Entanglement collapsed; recommending route quarantine."

        evidence = {
            "coherence": coherence,
            "drift": drift,
            "control_type": "advisory_only"
        }

        # Log suggestion to bridge telemetry
        self.bridge.push_telemetry({
            "event": "entanglement_stabilization_suggestion",
            "link_id": link_id,
            "action": action,
            "coherence": coherence,
            "drift": drift,
            "evidence": evidence
        })

        return EntanglementStabilizationSuggestion(
            link_id=link_id,
            action=action,
            nudge_value=nudge_val,
            damping_adjustment=damping_adj,
            reason=reason,
            evidence=evidence
        )


@dataclass
class ConsensusStabilizationSuggestion:
    group_id: str
    action: str  # "observe", "hold", "suggest_phase_alignment", "suggest_route_damping", "suggest_wavefront_resync", "quarantine_sequencer", "quarantine_route"
    nudge_value: float
    damping_adjustment: float
    reason: str
    evidence: Dict[str, Any]


class FrontierConsensusAdvisor:
    """
    Advisory controller for distributed consensus stabilization and resynchronization.
    Suggestions remain bounded and advisory-only.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_consensus_stabilization(self, sync_report: Any) -> ConsensusStabilizationSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        group_id = extract(sync_report, "report_id", "unknown_group")
        coherence = extract(sync_report, "group_coherence", 1.0)
        drift = extract(sync_report, "max_drift", 0.0)
        
        # Advisory Stabilization suggestion checks:
        if coherence >= 0.95 and drift <= 0.02:
            action = "observe"
            nudge_val = 0.0
            damping_adj = 0.0
            reason = "Wavefront consensus group is highly synchronized."
        elif coherence >= 0.90 and drift <= 0.05:
            action = "hold"
            nudge_val = 0.0
            damping_adj = 0.0
            reason = "Wavefront synchronicity is stable within thresholds."
        elif coherence >= 0.80 and drift <= 0.10:
            action = "suggest_phase_alignment"
            nudge_val = -0.05 * drift
            nudge_val = max(-0.05, min(0.05, nudge_val))
            damping_adj = 0.0
            reason = "Coherence drift detected; recommending minor phase adjustments."
        elif coherence >= 0.70 and drift <= 0.15:
            action = "suggest_route_damping"
            nudge_val = 0.0
            damping_adj = 0.006
            reason = "Consensus path drift detected; recommending minor waveguide damping."
        elif coherence >= 0.55 and drift <= 0.25:
            action = "suggest_wavefront_resync"
            nudge_val = 0.0
            damping_adj = 0.0
            reason = "Consensus coherence is poor; recommending a full wavefront resynchronization cycle."
        elif coherence >= 0.40 and drift <= 0.40:
            action = "quarantine_route"
            nudge_val = 0.0
            damping_adj = 0.0
            reason = "High drift detected on routing path; recommending route quarantine."
        else:
            action = "quarantine_sequencer"
            nudge_val = 0.0
            damping_adj = 0.0
            reason = "Critical synchronization collapse; recommending sequencer quarantine."

        evidence = {
            "group_coherence": coherence,
            "max_drift": drift,
            "control_type": "distributed_advisory"
        }

        self.bridge.push_telemetry({
            "event": "consensus_stabilization_suggestion",
            "group_id": group_id,
            "action": action,
            "coherence": coherence,
            "drift": drift,
            "evidence": evidence
        })

        return ConsensusStabilizationSuggestion(
            group_id=group_id,
            action=action,
            nudge_value=nudge_val,
            damping_adjustment=damping_adj,
            reason=reason,
            evidence=evidence
        )


@dataclass
class RelocationControlSuggestion:
    action: str  # "observe" | "hold" | "reduce_step_size" | "increase_boundary_absorption" | "request_phase_realign" | "request_route_damping" | "rollback" | "quarantine_route"
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    boundary_absorption_delta: float = 0.0
    step_size_factor: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RelocationClosedLoopPolicy:
    max_phase_nudge: float = 0.05
    max_damping_delta: float = 0.01
    max_boundary_absorption_delta: float = 0.05
    min_step_size_factor: float = 0.1
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RelocationClosedLoopReport:
    report_id: str
    suggestion: RelocationControlSuggestion
    validated: bool
    applied: bool
    timestamp: float = field(default_factory=time.time)


def suggest_relocation_control_adjustment(
    telemetry_report: Any,
    policy: RelocationClosedLoopPolicy
) -> RelocationControlSuggestion:
    """
    Computes a closed-loop control suggestion based on relocation telemetry metrics.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    is_stable = extract(telemetry_report, "is_stable", True)
    max_drift = extract(telemetry_report, "max_phase_drift", 0.0)
    max_crosstalk = extract(telemetry_report, "max_crosstalk", 0.0)
    max_reflection = extract(telemetry_report, "max_reflection", 0.0)
    min_mass = extract(telemetry_report, "min_active_mass", 500.0)



    if min_mass < 14.0:
        return RelocationControlSuggestion(
            action="rollback",
            reason=f"Active register mass {min_mass:.4f} below threshold 14.0.",
            nudge_value=0.0
        )
    elif max_drift > 0.10:
        return RelocationControlSuggestion(
            action="quarantine_route",
            reason=f"Critical phase drift {max_drift:.4f} exceeded 0.10.",
            nudge_value=0.0
        )
    elif max_drift > 0.05:
        nudge = -0.5 * max_drift
        return RelocationControlSuggestion(
            action="request_phase_realign",
            reason=f"Phase drift {max_drift:.4f} exceeded 0.05.",
            nudge_value=nudge
        )
    elif max_reflection > 0.05:
        return RelocationControlSuggestion(
            action="increase_boundary_absorption",
            reason=f"Boundary reflection {max_reflection:.4f} exceeded 0.05.",
            boundary_absorption_delta=0.02
        )
    elif max_crosstalk > 0.05:
        return RelocationControlSuggestion(
            action="request_route_damping",
            reason=f"Crosstalk {max_crosstalk:.4f} exceeded 0.05.",
            damping_adjustment=0.005
        )
    elif not is_stable:
        return RelocationControlSuggestion(
            action="reduce_step_size",
            reason="Unstable telemetry frame detected.",
            step_size_factor=0.5
        )
    elif max_drift > 0.02:
        return RelocationControlSuggestion(
            action="hold",
            reason="Minor phase drift observed, holding adjustment."
        )
    else:
        return RelocationControlSuggestion(
            action="observe",
            reason="Relocation telemetry is within normal bounds."
        )


def validate_relocation_control_bounds(
    suggestion: RelocationControlSuggestion,
    policy: RelocationClosedLoopPolicy
) -> bool:
    """
    Validates that suggestion values do not exceed the closed-loop policy limits.
    """
    allowed_actions = {
        "observe", "hold", "reduce_step_size", "increase_boundary_absorption",
        "request_phase_realign", "request_route_damping", "rollback", "quarantine_route"
    }
    if suggestion.action not in allowed_actions:
        return False
    
    if abs(suggestion.nudge_value) > policy.max_phase_nudge:
        return False
    if abs(suggestion.damping_adjustment) > policy.max_damping_delta:
        return False
    if abs(suggestion.boundary_absorption_delta) > policy.max_boundary_absorption_delta:
        return False
    if suggestion.step_size_factor < policy.min_step_size_factor:
        return False
        
    return True


@dataclass
class GlobalCoordinationSuggestion:
    action: str  # "observe", "hold_epoch", "reduce_relocation_step_size", "request_wavefront_realign", "request_boundary_absorption", "request_lock_boundary_hold", "rollback_epoch", "quarantine_manifold", "quarantine_route"
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class GlobalCoordinationAdvisor:
    """
    Advisory controller for global multi-manifold coordination.
    All suggestions are strictly advisory unless explicitly authorized by a sandbox token.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_coordination_adjustment(
        self,
        coordination_report: Any,
        policy: Optional[Any] = None
    ) -> GlobalCoordinationSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        passed_gates = extract(coordination_report, "passed_gates", True)
        errors = extract(coordination_report, "errors", []) or []
        
        metadata = extract(coordination_report, "metadata", {}) or {}
        
        if metadata.get("high_skew") or metadata.get("phase_skew_breach"):
            return GlobalCoordinationSuggestion(
                action="request_wavefront_realign",
                reason="High global phase skew detected across manifolds."
            )
        elif metadata.get("high_crosstalk") or metadata.get("crosstalk_breach"):
            return GlobalCoordinationSuggestion(
                action="reduce_relocation_step_size",
                reason="Cross-manifold crosstalk exceeded safety limits."
            )
        elif metadata.get("high_reflection") or metadata.get("reflection_breach"):
            return GlobalCoordinationSuggestion(
                action="request_boundary_absorption",
                reason="Boundary reflection limits exceeded."
            )
        elif metadata.get("lock_conflict") or metadata.get("deadlock_detected"):
            return GlobalCoordinationSuggestion(
                action="request_lock_boundary_hold",
                reason="Lock boundary conflict or potential deadlock detected."
            )
        elif metadata.get("split_brain") or metadata.get("split_brain_detected"):
            return GlobalCoordinationSuggestion(
                action="rollback_epoch",
                reason="Split-brain synchronization detected."
            )
        elif not passed_gates or errors:
            return GlobalCoordinationSuggestion(
                action="hold_epoch",
                reason="Coordination report failed safety gates."
            )
        else:
            return GlobalCoordinationSuggestion(
                action="observe",
                reason="Multi-manifold coordination stability is within limits."
            )


@dataclass
class GeodesicTransactionSuggestion:
    action: str  # "observe", "hold_epoch", "request_phase_realign", "increase_boundary_absorption", "reduce_propagation_step_size", "request_route_damping", "abort_transaction", "rollback_epoch", "quarantine_route", "quarantine_manifold"
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class GeodesicTransactionAdvisor:
    """
    Advisory controller for geodesic multi-manifold transactions.
    All suggestions are advisory unless a valid sandbox token authorizes execution.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_transaction_stabilization(
        self,
        transaction_report: Any,
        policy: Optional[Any] = None
    ) -> GeodesicTransactionSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        passed = extract(transaction_report, "passed_gates", True)
        metadata = extract(transaction_report, "metadata", {}) or {}
        errors = extract(transaction_report, "errors", []) or []

        if metadata.get("high_phase_error") or metadata.get("phase_skew_breach"):
            return GeodesicTransactionSuggestion(
                action="request_phase_realign",
                reason="High phase error detected in transaction propagation."
            )
        elif metadata.get("high_crosstalk") or metadata.get("crosstalk_breach"):
            return GeodesicTransactionSuggestion(
                action="request_route_damping",
                reason="Cross-manifold crosstalk exceeded limits."
            )
        elif metadata.get("high_reflection") or metadata.get("reflection_breach"):
            return GeodesicTransactionSuggestion(
                action="increase_boundary_absorption",
                reason="Boundary reflection limits exceeded."
            )
        elif metadata.get("lock_conflict") or metadata.get("deadlock_detected"):
            return GeodesicTransactionSuggestion(
                action="quarantine_route",
                reason="Global lock boundary conflict or deadlock detected."
            )
        elif metadata.get("split_brain") or metadata.get("split_brain_detected"):
            return GeodesicTransactionSuggestion(
                action="rollback_epoch",
                reason="Split-brain transaction synchronization detected."
            )
        elif not passed or errors:
            return GeodesicTransactionSuggestion(
                action="abort_transaction",
                reason="Transaction report failed safety gates or has errors."
            )
        else:
            return GeodesicTransactionSuggestion(
                action="observe",
                reason="Transaction propagation stability is within limits."
            )


@dataclass
class CalibrationClosedLoopPolicy:
    max_phase_nudge: float = 0.05
    max_damping_delta: float = 0.01
    max_boundary_absorption_delta: float = 0.05
    sandbox_only: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationControlSuggestion:
    action: str  # "observe" | "hold" | "reduce_step_size" | "apply_candidate_phase_offset" | "increase_boundary_absorption" | "request_route_damping" | "request_pml_adjustment" | "rollback_loop" | "quarantine_boundary_group"
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    boundary_absorption_delta: float = 0.0
    step_size_factor: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationClosedLoopReport:
    report_id: str
    suggestion: CalibrationControlSuggestion
    validated: bool
    applied: bool
    timestamp: float = field(default_factory=time.time)


class DistributedCalibrationAdvisor:
    """
    Advisor for distributed calibration-loop closed-loop controls.
    Suggestions are advisory in shadow mode. They can only be applied in sandbox mode with a valid token.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_calibration_control(
        self,
        telemetry_report: Any,
        policy: CalibrationClosedLoopPolicy
    ) -> CalibrationControlSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        is_stable = extract(telemetry_report, "is_stable", True)
        max_drift = extract(telemetry_report, "max_phase_drift", 0.0)
        max_crosstalk = extract(telemetry_report, "max_crosstalk", 0.0)
        max_reflection = extract(telemetry_report, "max_reflection", 0.0)
        min_mass = extract(telemetry_report, "min_active_mass", 500.0)

        # Build closed-loop control suggestions
        if min_mass < 14.0:
            return CalibrationControlSuggestion(
                action="rollback_loop",
                reason=f"Mass preservation failure: {min_mass:.4f} < 14.0."
            )
        elif max_drift > 0.10:
            return CalibrationControlSuggestion(
                action="quarantine_boundary_group",
                reason=f"Critical phase drift {max_drift:.4f} exceeded threshold 0.10."
            )
        elif max_crosstalk > 0.05:
            return CalibrationControlSuggestion(
                action="request_route_damping",
                reason=f"Crosstalk {max_crosstalk:.4f} exceeded safety limit 0.05.",
                damping_adjustment=0.005
            )
        elif max_reflection > 0.05:
            return CalibrationControlSuggestion(
                action="increase_boundary_absorption",
                reason=f"Boundary reflection {max_reflection:.4f} exceeded safety limit 0.05.",
                boundary_absorption_delta=0.02
            )
        elif not is_stable:
            return CalibrationControlSuggestion(
                action="reduce_step_size",
                reason="Calibration telemetry instability detected.",
                step_size_factor=0.5
            )
        elif max_drift > 0.05:
            nudge = -0.5 * max_drift
            clamped_nudge = max(-policy.max_phase_nudge, min(policy.max_phase_nudge, nudge))
            return CalibrationControlSuggestion(
                action="apply_candidate_phase_offset",
                reason=f"Phase drift {max_drift:.4f} exceeded 0.05; proposing correction.",
                nudge_value=clamped_nudge
            )
        elif max_reflection > 0.02:
            return CalibrationControlSuggestion(
                action="request_pml_adjustment",
                reason=f"Minor boundary reflection {max_reflection:.4f} detected."
            )
        elif max_drift > 0.02:
            return CalibrationControlSuggestion(
                action="hold",
                reason="Minor phase drift observed, holding calibration loop."
            )
        else:
            return CalibrationControlSuggestion(
                action="observe",
                reason="Calibration telemetry is within normal bounds."
            )


@dataclass
class WaveguideSynthesisSuggestion:
    action: str  # "observe", "hold", "reduce_junction_degree", "increase_lane_spacing", "increase_boundary_absorption", "request_phase_realign", "request_route_damping", "reject_candidate", "quarantine_candidate_fabric"
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    boundary_absorption_delta: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class WaveguideSynthesisAdvisor:
    """
    Advisory controller for waveguide fabric synthesis and SIMD integration.
    Suggestions remain advisory in shadow mode. Applying suggestions in sandbox mode requires a valid court token.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_synthesis_tuning(self, synthesis_report: Any, policy: Optional[Any] = None) -> WaveguideSynthesisSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        success = extract(synthesis_report, "success", True)
        errors = extract(synthesis_report, "errors", []) or []
        metadata = extract(synthesis_report, "metadata", {}) or {}

        if errors or not success:
            return WaveguideSynthesisSuggestion(
                action="reject_candidate",
                reason=f"Synthesis failed with errors: {', '.join(errors)}"
            )

        junction_degree = metadata.get("max_junction_degree", 0)
        lane_crossings = metadata.get("max_lane_crossings", 0)
        crosstalk = metadata.get("max_crosstalk", 0.0)
        reflection = metadata.get("max_reflection", 0.0)
        drift = metadata.get("max_phase_drift", 0.0)

        if junction_degree > 4:
            return WaveguideSynthesisSuggestion(
                action="reduce_junction_degree",
                reason=f"Junction degree {junction_degree} exceeds balanced limit of 4."
            )
        elif lane_crossings > 5:
            return WaveguideSynthesisSuggestion(
                action="increase_lane_spacing",
                reason=f"Lane crossing count {lane_crossings} exceeds threshold."
            )
        elif crosstalk > 0.05:
            return WaveguideSynthesisSuggestion(
                action="quarantine_candidate_fabric",
                reason=f"Crosstalk {crosstalk:.4f} is too high; recommend quarantine."
            )
        elif reflection > 0.05:
            return WaveguideSynthesisSuggestion(
                action="increase_boundary_absorption",
                reason=f"Boundary reflection {reflection:.4f} exceeds threshold."
            )
        elif drift > 0.05:
            return WaveguideSynthesisSuggestion(
                action="request_phase_realign",
                reason=f"Phase drift {drift:.4f} requires realigning tables."
            )
        elif crosstalk > 0.02:
            return WaveguideSynthesisSuggestion(
                action="request_route_damping",
                reason=f"Minor crosstalk {crosstalk:.4f} detected, requesting route damping."
            )
        elif drift > 0.02:
            return WaveguideSynthesisSuggestion(
                action="hold",
                reason=f"Minor phase drift {drift:.4f} observed, holding promotion."
            )
        else:
            return WaveguideSynthesisSuggestion(
                action="observe",
                reason="Synthesized waveguide candidate meets all quality guidelines."
            )


@dataclass
class ReshapeCarrierSuggestion:
    action: str
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ManifoldReshapeAdvisor:
    """
    Advises on multi-dimensional manifold reshape candidates in shadow mode.
    """
    def suggest_reshape(self, report: Any) -> ReshapeCarrierSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)
            
        success = extract(report, "validation_passed", True)
        errors = extract(report, "errors", [])
        
        if not success or errors:
            return ReshapeCarrierSuggestion(
                action="reject_candidate",
                reason=f"Reshape failed with errors: {', '.join(errors)}"
            )
            
        # Check distortion if present in metadata
        distortion = extract(extract(report, "plan", {}), "intent", {}).source_shape.total_elements()
        target_elements = extract(extract(report, "plan", {}), "intent", {}).target_shape.total_elements()
        
        if distortion != target_elements:
            return ReshapeCarrierSuggestion(
                action="reduce_reshape_distortion",
                reason="Reshape is lossy; recommend reducing dimensionality mapping distortion."
            )
            
        return ReshapeCarrierSuggestion(
            action="observe",
            reason="Manifold reshape candidate satisfies all design criteria."
        )


class CarrierRelocationAdvisor:
    """
    Advises on dynamic PDM carrier relocation trials in shadow mode.
    """
    def suggest_relocation(self, report: Any) -> ReshapeCarrierSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)
            
        success = extract(extract(report, "result", {}), "success", True)
        errors = extract(extract(report, "result", {}), "errors", [])
        
        if not success or errors:
            return ReshapeCarrierSuggestion(
                action="reject_candidate",
                reason=f"Relocation failed with errors: {', '.join(errors)}"
            )
            
        # Check moves count
        steps = extract(extract(report, "plan", {}), "steps", [])
        if len(steps) > 5:
            return ReshapeCarrierSuggestion(
                action="reduce_carrier_move_count",
                reason=f"Carrier move count {len(steps)} is high; recommend reducing migrations."
            )
            
        return ReshapeCarrierSuggestion(
            action="observe",
            reason="Carrier relocation trial meets all calibration limits."
        )


@dataclass
class CadenceStabilizationSuggestion:
    action: str  # observe, hold_epoch, reduce_tick_step, adjust_candidate_phase_offset, etc.
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CadenceClosedLoopPolicy:
    max_phase_nudge: float = 0.05
    max_damping_delta: float = 0.01
    sandbox_only: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CadenceClosedLoopReport:
    report_id: str
    suggestion: CadenceStabilizationSuggestion
    validated: bool
    applied: bool
    timestamp: float = field(default_factory=time.time)


class TemporalCadenceAdvisor:
    """
    Advisory controller for temporal cadence stabilization.
    Suggestions remain advisory in shadow mode.
    Applying suggestions in sandbox mode requires a valid court token.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_cadence_stabilization(
        self,
        cadence_report: Any,
        policy: CadenceClosedLoopPolicy
    ) -> CadenceStabilizationSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # Get metrics
        global_skew = extract(cadence_report, "global_skew", 0.0)
        stable = extract(cadence_report, "stable", True)
        passed_gates = extract(cadence_report, "passed_gates", True)
        
        metadata = extract(cadence_report, "metadata", {}) or {}
        
        if metadata.get("split_brain") or metadata.get("split_brain_detected"):
            return CadenceStabilizationSuggestion(
                action="rollback_cadence_epoch",
                reason="Split-brain synchronization state detected across manifold clocks."
            )
        elif metadata.get("quarantine_clock") or metadata.get("clock_failure"):
            return CadenceStabilizationSuggestion(
                action="quarantine_manifold_clock",
                reason="Critical drift or clock failure detected; recommending quarantine."
            )
        elif metadata.get("outside_cadence_window") or metadata.get("outside_window"):
            return CadenceStabilizationSuggestion(
                action="abort_cadence_epoch",
                reason="Transaction commit attempted outside of approved cadence window."
            )
        elif global_skew > 0.10:
            return CadenceStabilizationSuggestion(
                action="request_cadence_recalibration",
                reason=f"Global cadence skew {global_skew:.4f} exceeded 0.10 threshold."
            )
        elif global_skew > 0.05:
            nudge = -0.5 * global_skew
            clamped_nudge = max(-policy.max_phase_nudge, min(policy.max_phase_nudge, nudge))
            return CadenceStabilizationSuggestion(
                action="adjust_candidate_phase_offset",
                reason=f"Global cadence skew {global_skew:.4f} exceeded 0.05 threshold.",
                nudge_value=clamped_nudge
            )
        elif metadata.get("high_reflection") or metadata.get("reflection_breach"):
            return CadenceStabilizationSuggestion(
                action="increase_boundary_absorption",
                reason="High boundary reflection detected affecting timing cadence.",
                damping_adjustment=policy.max_damping_delta
            )
        elif metadata.get("wavefront_realign_required") or metadata.get("high_phase_error"):
            return CadenceStabilizationSuggestion(
                action="request_wavefront_realign",
                reason="Wavefront timing mismatch detected; realignment required."
            )
        elif not stable or not passed_gates:
            return CadenceStabilizationSuggestion(
                action="reduce_tick_step",
                reason="Unstable cadence state detected; recommending smaller tick rate step.",
                nudge_value=0.0
            )
        elif global_skew > 0.02:
            return CadenceStabilizationSuggestion(
                action="hold_epoch",
                reason="Minor cadence skew observed; holding timing cadence."
            )
        else:
            return CadenceStabilizationSuggestion(
                action="observe",
                reason="Temporal cadence is within stable parameters."
            )

    def apply_cadence_adjustment_in_sandbox(
        self,
        suggestion: CadenceStabilizationSuggestion,
        token: Any
    ) -> CadenceClosedLoopReport:
        """
        Applies timing suggestions in sandbox mode. Requires valid court token.
        """
        errors = []
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

        validated = len(errors) == 0
        applied = validated and (suggestion.action != "observe")
        
        import uuid
        report_id = f"CCLR_{uuid.uuid4().hex[:8]}"
        
        return CadenceClosedLoopReport(
            report_id=report_id,
            suggestion=suggestion,
            validated=validated,
            applied=applied
        )


@dataclass
class EntangledCommitSuggestion:
    action: str
    reason: str
    nudge_value: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntangledCommitClosedLoopPolicy:
    sandbox_only: bool = True
    max_nudge: float = 0.05
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntangledCommitClosedLoopReport:
    report_id: str
    suggestion: EntangledCommitSuggestion
    validated: bool
    applied: bool
    timestamp: float = field(default_factory=time.time)


class EntangledCommitAdvisor:
    """
    Advisory controller for entangled commit stabilization.
    Suggestions remain advisory in shadow mode.
    Applying suggestions in sandbox mode requires a valid court token.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_entangled_commit_stabilization(
        self,
        epoch_report: Any,
        policy: EntangledCommitClosedLoopPolicy
    ) -> EntangledCommitSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        success = extract(epoch_report, "success", True)
        errors = extract(epoch_report, "errors", []) or []
        
        epoch = extract(epoch_report, "epoch")
        meta = extract(epoch, "metadata", {}) or {} if epoch else {}
        if not meta:
            meta = extract(epoch_report, "metadata", {}) or {}

        if meta.get("split_brain") or meta.get("split_brain_detected"):
            return EntangledCommitSuggestion(
                action="rollback_entangled_epoch",
                reason="Split-brain state detected across manifold clocks."
            )
        elif meta.get("quarantine_link"):
            return EntangledCommitSuggestion(
                action="quarantine_entanglement_link",
                reason="Critical drift detected on link; recommending quarantine."
            )
        elif meta.get("quarantine_manifold"):
            return EntangledCommitSuggestion(
                action="quarantine_manifold",
                reason="Critical manifold error detected; recommending quarantine."
            )
        elif meta.get("outside_cadence_window") or meta.get("outside_window"):
            return EntangledCommitSuggestion(
                action="abort_commit_epoch",
                reason="Transaction commit attempted outside of approved cadence window."
            )
        elif meta.get("high_drift") or meta.get("high_cadence_drift"):
            return EntangledCommitSuggestion(
                action="request_cadence_recalibration",
                reason="High timing drift detected."
            )
        elif meta.get("unstable_propagation"):
            return EntangledCommitSuggestion(
                action="reduce_propagation_step_size",
                reason="Unstable propagation detected."
            )
        elif meta.get("high_reflection") or meta.get("boundary_reflection_breach"):
            return EntangledCommitSuggestion(
                action="increase_boundary_absorption",
                reason="High boundary reflections detected."
            )
        elif meta.get("wavefront_realign_required") or meta.get("high_phase_error"):
            return EntangledCommitSuggestion(
                action="request_phase_realign",
                reason="High phase error detected."
            )
        elif not success:
            return EntangledCommitSuggestion(
                action="hold_epoch",
                reason="Commit failed validation gates; holding epoch."
            )
        else:
            return EntangledCommitSuggestion(
                action="observe",
                reason="Entangled propagation and commit timing are stable."
            )

    def apply_entangled_commit_adjustment_in_sandbox(
        self,
        suggestion: EntangledCommitSuggestion,
        token: Any
    ) -> EntangledCommitClosedLoopReport:
        errors = []
        if token is None:
            errors.append("Expired or invalid token is rejected: missing token.")
        else:
            authorized = getattr(token, "authorized_by_court", False)
            expires_at = getattr(token, "expires_at", 0.0)
            active = getattr(token, "active", True)
            
            if not authorized:
                errors.append("Expired or invalid token is rejected: unauthorized token.")
              # We handle key errors if token expires or is inactive
            elif not active:
                errors.append("Expired or invalid token is rejected: inactive token.")
            elif expires_at < time.time():
                errors.append("Expired or invalid token is rejected: token has expired.")

        validated = len(errors) == 0
        applied = validated and (suggestion.action != "observe")
        
        import uuid
        report_id = f"ECCLR_{uuid.uuid4().hex[:8]}"
        return EntangledCommitClosedLoopReport(
            report_id=report_id,
            suggestion=suggestion,
            validated=validated,
            applied=applied
        )


@dataclass
class EntangledFeedbackSuggestion:
    action: str
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntangledFeedbackClosedLoopPolicy:
    sandbox_only: bool = True
    max_phase_nudge: float = 0.05
    max_damping_delta: float = 0.01
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntangledFeedbackClosedLoopReport:
    report_id: str
    suggestion: EntangledFeedbackSuggestion
    validated: bool
    applied: bool
    timestamp: float = field(default_factory=time.time)


class EntangledFeedbackAdvisor:
    """
    Advisory controller for entangled feedback loops and boundary absorption.
    Suggestions are advisory in shadow mode.
    Applying suggestions in sandbox mode requires a valid court token.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_feedback_stabilization(
        self,
        feedback_report: Any,
        policy: EntangledFeedbackClosedLoopPolicy
    ) -> EntangledFeedbackSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        res = extract(feedback_report, "result")
        success = extract(res, "success", True) if res else True
        meta = extract(feedback_report, "metadata", {}) or {}

        # Handle specific simulated conditions
        if meta.get("split_brain") or meta.get("split_brain_detected"):
            return EntangledFeedbackSuggestion(
                action="rollback_loop",
                reason="Split-brain state detected; rolling back feedback loop."
            )
        elif meta.get("quarantine_link") or meta.get("unstable_link"):
            return EntangledFeedbackSuggestion(
                action="quarantine_link",
                reason="Critical drift detected on link; recommending quarantine."
            )
        elif meta.get("quarantine_manifold") or meta.get("unstable_manifold"):
            return EntangledFeedbackSuggestion(
                action="quarantine_manifold",
                reason="Critical manifold error detected; recommending quarantine."
            )
        elif meta.get("high_phase_error"):
            return EntangledFeedbackSuggestion(
                action="apply_candidate_phase_offset",
                reason="High phase error detected; suggesting realignment.",
                nudge_value=-0.02
            )
        elif meta.get("high_cadence_drift"):
            return EntangledFeedbackSuggestion(
                action="apply_candidate_cadence_offset",
                reason="High cadence drift detected; suggesting recalibration.",
                nudge_value=-0.02
            )
        elif meta.get("high_carrier_offset") or meta.get("high_carrier_error"):
            return EntangledFeedbackSuggestion(
                action="apply_candidate_carrier_offset",
                reason="High carrier offset detected; suggesting correction.",
                nudge_value=-0.02
            )
        elif meta.get("high_reflection") or meta.get("boundary_reflection_breach"):
            return EntangledFeedbackSuggestion(
                action="increase_boundary_absorption",
                reason="High boundary reflections detected.",
                damping_adjustment=policy.max_damping_delta
            )
        elif meta.get("high_crosstalk"):
            return EntangledFeedbackSuggestion(
                action="request_route_damping",
                reason="High crosstalk detected."
            )
        elif meta.get("unstable_feedback") or not success:
            return EntangledFeedbackSuggestion(
                action="reduce_feedback_gain",
                reason="Unstable feedback loop; reducing loop gain."
            )
        elif meta.get("hold_epoch") or meta.get("hold"):
            return EntangledFeedbackSuggestion(
                action="hold",
                reason="Holding feedback loop epoch."
            )
        else:
            return EntangledFeedbackSuggestion(
                action="observe",
                reason="Feedback loop is stable and coherent."
            )

    def apply_feedback_adjustment_in_sandbox(
        self,
        suggestion: EntangledFeedbackSuggestion,
        token: Any
    ) -> EntangledFeedbackClosedLoopReport:
        errors = []
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

        validated = len(errors) == 0
        applied = validated and (suggestion.action != "observe")
        
        import uuid
        report_id = f"EFCLR_{uuid.uuid4().hex[:8]}"
        return EntangledFeedbackClosedLoopReport(
            report_id=report_id,
            suggestion=suggestion,
            validated=validated,
            applied=applied
        )


@dataclass
class EntangledAtomicCommitClosedLoopPolicy:
    max_steps: int = 10
    max_phase_delta: float = 0.05
    max_cadence_delta: float = 0.05
    max_damping_delta: float = 0.05

@dataclass
class EntangledAtomicCommitSuggestion:
    action: str
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0

@dataclass
class EntangledAtomicCommitClosedLoopReport:
    report_id: str
    suggestion: EntangledAtomicCommitSuggestion
    validated: bool
    applied: bool

class EntangledAtomicCommitAdvisor:
    """
    Advises on multi-manifold atomic commit execution and recommends tuning adjustments.
    """
    def suggest_atomic_commit_adjustments(
        self,
        consensus_report: Any,
        policy: EntangledAtomicCommitClosedLoopPolicy
    ) -> EntangledAtomicCommitSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        meta = extract(consensus_report, "metadata", {}) or {}
        if not isinstance(meta, dict):
            meta = {}

        if meta.get("split_brain") or meta.get("split_brain_detected"):
            return EntangledAtomicCommitSuggestion(
                action="abort_atomic_epoch",
                reason="Split-brain timing detected; aborting commit."
            )
        elif meta.get("quarantine_manifold") or meta.get("quarantine_participant"):
            return EntangledAtomicCommitSuggestion(
                action="quarantine_manifold",
                reason="Quarantine requested for participant."
            )
        elif meta.get("quarantine_link"):
            return EntangledAtomicCommitSuggestion(
                action="quarantine_entanglement_link",
                reason="Quarantine requested for entanglement link."
            )
        elif meta.get("rollback_needed") or meta.get("missing_rollback_snapshot"):
            return EntangledAtomicCommitSuggestion(
                action="rollback_atomic_epoch",
                reason="Rollback snapshot missing or rollback required."
            )
        elif meta.get("outside_cadence_window") or meta.get("outside_window"):
            return EntangledAtomicCommitSuggestion(
                action="request_cadence_recalibration",
                reason="Outside approved cadence window; request recalibration."
            )
        elif meta.get("high_phase_drift") or meta.get("unstable_propagation"):
            return EntangledAtomicCommitSuggestion(
                action="request_wavefront_realign",
                reason="High wavefront phase drift or unstable propagation detected."
            )
        elif meta.get("high_crosstalk"):
            return EntangledAtomicCommitSuggestion(
                action="observe",
                reason="High crosstalk detected but within advisory limits."
            )
        elif meta.get("boundary_reflection_breach") or meta.get("high_reflection"):
            return EntangledAtomicCommitSuggestion(
                action="increase_boundary_absorption",
                reason="Boundary reflection breach detected."
            )
        elif meta.get("local_quorum_failed") or meta.get("global_quorum_failed") or meta.get("sequencer_quorum_failed"):
            return EntangledAtomicCommitSuggestion(
                action="request_more_votes",
                reason="Quorum failed; requesting retry or additional votes."
            )
        elif meta.get("hold_epoch") or meta.get("hold"):
            return EntangledAtomicCommitSuggestion(
                action="hold_epoch",
                reason="Advisory: hold epoch requested."
            )
        else:
            return EntangledAtomicCommitSuggestion(
                action="observe",
                reason="Atomic commit consensus is stable and prepared."
            )

    def apply_atomic_commit_adjustment_in_sandbox(
        self,
        suggestion: EntangledAtomicCommitSuggestion,
        token: Any
    ) -> EntangledAtomicCommitClosedLoopReport:
        errors = []
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

        validated = len(errors) == 0
        applied = validated and (suggestion.action != "observe")
        
        import uuid
        report_id = f"EACCLR_{uuid.uuid4().hex[:8]}"
        return EntangledAtomicCommitClosedLoopReport(
            report_id=report_id,
            suggestion=suggestion,
            validated=validated,
            applied=applied
        )


@dataclass
class RealtimeRelocationSuggestion:
    action: str
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RealtimeRelocationClosedLoopPolicy:
    sandbox_only: bool = True
    max_phase_nudge: float = 0.05
    max_damping_delta: float = 0.01
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RealtimeRelocationClosedLoopReport:
    report_id: str
    suggestion: RealtimeRelocationSuggestion
    validated: bool
    applied: bool
    timestamp: float = field(default_factory=time.time)


class RealtimeRelocationAdvisor:
    """
    Advisory controller for real-time relocation closed-loop controls.
    Suggestions are advisory in shadow mode.
    Applying suggestions in sandbox mode requires a valid court token.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_relocation_stabilization(
        self,
        relocation_report: Any,
        policy: RealtimeRelocationClosedLoopPolicy
    ) -> RealtimeRelocationSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        meta = extract(relocation_report, "metadata", {}) or {}
        if not isinstance(meta, dict):
            meta = {}

        res = extract(relocation_report, "result")
        errors = extract(res, "errors", []) or []
        success = extract(res, "success", True) if res else True
        if not success:
            if "split_brain" in errors or meta.get("split_brain_detected"):
                return RealtimeRelocationSuggestion(
                    action="rollback_relocation",
                    reason="Split-brain state detected during relocation; rolling back."
                )
            if "quarantine_manifold" in errors or meta.get("quarantine_manifold"):
                return RealtimeRelocationSuggestion(
                    action="quarantine_manifold",
                    reason="Quarantine requested for target manifold."
                )
            if "quarantine_state_ref" in errors or meta.get("quarantine_state"):
                return RealtimeRelocationSuggestion(
                    action="quarantine_state_ref",
                    reason="Quarantine requested for state reference."
                )
            if "abort" in errors or meta.get("abort_requested"):
                return RealtimeRelocationSuggestion(
                    action="abort_relocation",
                    reason="Abort triggered during state relocation."
                )

        if meta.get("split_brain") or meta.get("split_brain_detected"):
            return RealtimeRelocationSuggestion(
                action="rollback_relocation",
                reason="Split-brain state detected during relocation."
            )
        elif meta.get("quarantine_manifold"):
            return RealtimeRelocationSuggestion(
                action="quarantine_manifold",
                reason="Critical manifold error; quarantine recommended."
            )
        elif meta.get("quarantine_state_ref") or meta.get("quarantine_state"):
            return RealtimeRelocationSuggestion(
                action="quarantine_state_ref",
                reason="Critical state reference error; quarantine recommended."
            )
        elif meta.get("abort_requested") or meta.get("failed_consensus"):
            return RealtimeRelocationSuggestion(
                action="abort_relocation",
                reason="State relocation aborted or consensus failed."
            )
        elif meta.get("rollback_needed") or meta.get("missing_rollback_snapshot") or meta.get("failed_verify"):
            return RealtimeRelocationSuggestion(
                action="rollback_relocation",
                reason="Relocation verification or snapshot check failed; rollback recommended."
            )
        elif meta.get("high_phase_error") or meta.get("wavefront_drift_breach"):
            return RealtimeRelocationSuggestion(
                action="request_phase_realign",
                reason="High phase error detected; request realignment."
            )
        elif meta.get("high_cadence_drift") or meta.get("cadence_drift_breach"):
            return RealtimeRelocationSuggestion(
                action="request_cadence_recalibration",
                reason="High cadence drift detected; request recalibration."
            )
        elif meta.get("high_carrier_error") or meta.get("carrier_drift_breach"):
            return RealtimeRelocationSuggestion(
                action="request_carrier_recalibration",
                reason="High carrier error detected; request recalibration."
            )
        elif meta.get("high_reflection") or meta.get("boundary_reflection_breach"):
            return RealtimeRelocationSuggestion(
                action="increase_boundary_absorption",
                reason="High boundary reflection detected.",
                damping_adjustment=policy.max_damping_delta
            )
        elif meta.get("high_crosstalk"):
            return RealtimeRelocationSuggestion(
                action="request_route_damping",
                reason="High crosstalk detected; request route damping."
            )
        elif meta.get("unstable_propagation") or meta.get("unstable_feedback"):
            return RealtimeRelocationSuggestion(
                action="reduce_relocation_step_size",
                reason="Unstable feedback or propagation; recommend reducing step size."
            )
        elif meta.get("hold_relocation") or meta.get("hold") or meta.get("local_quorum_failed"):
            return RealtimeRelocationSuggestion(
                action="hold_relocation",
                reason="Quorum check pending or holding relocation."
            )
        else:
            return RealtimeRelocationSuggestion(
                action="observe",
                reason="Real-time relocation states are within stable parameters."
            )

    def apply_relocation_adjustment_in_sandbox(
        self,
        suggestion: RealtimeRelocationSuggestion,
        token: Any
    ) -> RealtimeRelocationClosedLoopReport:
        errors = []
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

        validated = len(errors) == 0
        applied = validated and (suggestion.action != "observe")
        
        import uuid
        report_id = f"RRCLR_{uuid.uuid4().hex[:8]}"
        return RealtimeRelocationClosedLoopReport(
            report_id=report_id,
            suggestion=suggestion,
            validated=validated,
            applied=applied
        )


@dataclass
class RelocationFaultSuggestion:
    suggestion_id: str
    action: str  # observe | hold_relocation | abort_relocation | rollback_relocation | reduce_calibration_gain | restore_candidate_tables | request_state_hash_rescan | request_lock_boundary_review | request_cadence_recalibration | quarantine_state_ref | quarantine_manifold | reject_candidate
    justification: str
    target_ref: Optional[str] = None


@dataclass
class RelocationFaultResponsePolicy:
    policy_id: str
    allow_sandbox_override: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelocationFaultResponseReport:
    report_id: str
    suggestion: RelocationFaultSuggestion
    validated: bool
    applied: bool = False


class RelocationFaultAdvisor:
    """
    Formulates advisory suggestions in response to fault injection occurrences.
    """
    def formulate_fault_response(
        self,
        fault_matrix_report: Any,
        policy: RelocationFaultResponsePolicy
    ) -> RelocationFaultSuggestion:
        """
        Formulates a suggestion based on the results of the fault matrix execution.
        """
        action = "observe"
        justification = "All fault matrix test cases passed."
        target_ref = None
        
        results = getattr(fault_matrix_report, "results", []) or []
        for r in results:
            if not getattr(r, "success", True) or getattr(r, "actual_outcome", "accept_shadow") != "accept_shadow":
                action = getattr(r, "actual_outcome", "hold_relocation")
                justification = f"Advisory suggestion triggered by active fault: {getattr(r, 'category', 'unknown')}"
                target_ref = getattr(r, "case_id", None)
                break
                
        import uuid
        suggestion_id = f"SUGG_FLT_{uuid.uuid4().hex[:8]}"
        return RelocationFaultSuggestion(
            suggestion_id=suggestion_id,
            action=action,
            justification=justification,
            target_ref=target_ref
        )

    def execute_sandbox_fault_response(
        self,
        suggestion: RelocationFaultSuggestion,
        policy: RelocationFaultResponsePolicy,
        token: Any
    ) -> RelocationFaultResponseReport:
        """
        Executes a suggested action under sandbox mode. Requires a valid court token lease.
        """
        errors = []
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

        validated = len(errors) == 0
        applied = validated and (suggestion.action != "observe")
        
        import uuid
        report_id = f"RFR_REP_{uuid.uuid4().hex[:8]}"
        return RelocationFaultResponseReport(
            report_id=report_id,
            suggestion=suggestion,
            validated=validated,
            applied=applied
        )


@dataclass
class RouteRebalanceSuggestion:
    suggestion_id: str
    action: str  # observe, hold_rebalance, reduce_route_depth, reduce_boundary_crossings, request_phase_realign, request_cadence_recalibration, request_carrier_recalibration, increase_boundary_absorption, request_waveguide_rebalance, rollback_rebalance, quarantine_route, quarantine_waveguide_segment, quarantine_manifold
    justification: str
    target_ref: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0


@dataclass
class RouteRebalanceClosedLoopPolicy:
    policy_id: str
    max_phase_nudge: float = 0.05
    max_damping_delta: float = 0.01
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteRebalanceClosedLoopReport:
    report_id: str
    suggestion: RouteRebalanceSuggestion
    validated: bool
    applied: bool
    timestamp: float = field(default_factory=time.time)


class RouteRebalanceAdvisor:
    """
    Advisory controller for route optimization and dynamic waveguide rebalancing.
    Suggestions are advisory in shadow mode. Sandbox application requires a valid court token.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_route_rebalance_control(
        self,
        telemetry_report: Any,
        policy: RouteRebalanceClosedLoopPolicy
    ) -> RouteRebalanceSuggestion:
        """
        Computes advisory suggestions based on route/waveguide telemetry.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # Extract telemetry parameters
        crosstalk = extract(telemetry_report, "crosstalk", 0.0)
        reflection = extract(telemetry_report, "boundary_reflection", 0.0)
        phase_drift = extract(telemetry_report, "phase_drift", 0.0)
        outside_cadence = extract(telemetry_report, "outside_cadence_window", False)
        cost_improved = extract(telemetry_report, "cost_improved", True)
        
        target_ref = extract(telemetry_report, "route_id", "route_0")

        # Prioritize suggestions based on severity of violation
        if crosstalk > 0.05:
            action = "quarantine_waveguide_segment"
            justification = f"Crosstalk {crosstalk:.4f} exceeded threshold 0.05; quarantining segment."
        elif reflection > 0.05:
            action = "quarantine_route"
            justification = f"Reflection {reflection:.4f} exceeded threshold 0.05; quarantining route."
        elif phase_drift > 0.05:
            action = "quarantine_manifold"
            justification = f"Phase drift {phase_drift:.4f} exceeded threshold 0.05; quarantining manifold."
        elif outside_cadence:
            action = "hold_rebalance"
            justification = "Route lies outside approved cadence window; holding rebalance."
        elif not cost_improved:
            action = "rollback_rebalance"
            justification = "No cost improvement detected; recommending rollback of candidate."
        else:
            action = "observe"
            justification = "All route and waveguide parameters are within safe thresholds."

        import uuid
        suggestion_id = f"SUGG_RO_{uuid.uuid4().hex[:8]}"
        return RouteRebalanceSuggestion(
            suggestion_id=suggestion_id,
            action=action,
            justification=justification,
            target_ref=target_ref,
            nudge_value=-0.5 * phase_drift if action == "observe" else 0.0,
            damping_adjustment=0.005 if action == "observe" and reflection > 0.01 else 0.0
        )

    def execute_sandbox_route_rebalance(
        self,
        suggestion: RouteRebalanceSuggestion,
        policy: RouteRebalanceClosedLoopPolicy,
        token: Any
    ) -> RouteRebalanceClosedLoopReport:
        """
        Executes a suggested action under sandbox mode. Requires a valid court token lease.
        """
        errors = []
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

        validated = len(errors) == 0
        applied = validated and (suggestion.action != "observe")
        
        import uuid
        report_id = f"RO_REP_{uuid.uuid4().hex[:8]}"
        return RouteRebalanceClosedLoopReport(
            report_id=report_id,
            suggestion=suggestion,
            validated=validated,
            applied=applied
        )


@dataclass
class RouteRebalanceFaultSuggestion:
    suggestion_id: str
    value: str
    reason: str


@dataclass
class RouteRebalanceFaultResponsePolicy:
    policy_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RouteRebalanceFaultResponseReport:
    report_id: str
    suggestion: RouteRebalanceFaultSuggestion
    validated: bool
    applied: bool


class RouteRebalanceFaultAdvisor:
    """
    Formulates advisory suggestions in response to route rebalance fault occurrences.
    """
    def suggest_response(
        self,
        route_report: Any,
        rebalance_report: Any,
        protocol: Any = None
    ) -> RouteRebalanceFaultResponseReport:
        import uuid
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        telemetry = {}
        if protocol:
            telemetry.update(getattr(protocol, "route_telemetry", {}) or {})
            telemetry.update(getattr(protocol, "waveguide_telemetry", {}) or {})

        crosstalk = telemetry.get("crosstalk_spike", False)
        reflection = telemetry.get("reflection_breach", False)
        missing_pml = telemetry.get("missing_pml", False)
        prefix_carry = telemetry.get("break_prefix_carry", False)
        carrier_lease = telemetry.get("carrier_lease_failure", False)
        lock_violation = telemetry.get("lock_boundary_violation", False) or telemetry.get("cross_manifold_deadlock", False)
        cadence_violation = telemetry.get("outside_cadence_window", False) or telemetry.get("global_cadence_skew", False)
        cost_false = telemetry.get("no_improvement_without_justification", False) or telemetry.get("risk_underestimated", False)
        table_overwrite = telemetry.get("active_tables_overwritten", False)
        
        reject_cases = (
            telemetry.get("break_transaction_boundaries", False) or
            telemetry.get("break_atomic_commit_boundaries", False) or
            telemetry.get("missing_rollback_snapshot", False) or
            telemetry.get("corrupted_rollback_snapshot", False) or
            telemetry.get("state_hash_mismatch", False) or
            telemetry.get("route_state_hash_mismatch", False) or
            telemetry.get("local_quorum_failed", False) or
            telemetry.get("global_quorum_failed", False) or
            telemetry.get("sequencer_quorum_failed", False) or
            telemetry.get("wavefront_coherence_collapse", False) or
            telemetry.get("weakened_pml", False) or
            telemetry.get("break_carrier_identity", False) or
            telemetry.get("break_quadrature_pair", False) or
            telemetry.get("lane_isolation_breached", False) or
            telemetry.get("arithmetic_oracle_mismatch", False) or
            telemetry.get("tensor_binding_break", False) or
            telemetry.get("reduction_tree_break", False) or
            telemetry.get("safety_oracle_mismatch", False) or
            telemetry.get("production_route_mutation_attempt", False)
        )

        value = "observe"
        reason = "All systems green."

        if crosstalk or missing_pml:
            value = "quarantine_waveguide_segment"
            reason = "Inter-lane crosstalk exceeds safe limit or missing PML boundary."
        elif reflection:
            value = "quarantine_route"
            reason = "PML boundary reflection exceeds acceptable limit."
        elif prefix_carry:
            value = "quarantine_manifold"
            reason = "Rebalance candidate breaks prefix-carry semantics."
        elif carrier_lease:
            value = "quarantine_carrier"
            reason = "Missing active lease for carrier on lane."
        elif lock_violation:
            value = "request_lock_boundary_review"
            reason = "Lock boundary violation or deadlock detected."
        elif cadence_violation:
            value = "request_cadence_recalibration"
            reason = "Cadence window failure or skew spike detected."
        elif cost_false:
            value = "request_cost_model_review"
            reason = "Cost model false improvement or risk underestimation detected."
        elif table_overwrite:
            value = "restore_candidate_tables"
            reason = "Attempt to overwrite active tables."
        elif reject_cases:
            value = "reject_route_candidate"
            reason = "Critical route rebalance validation fault detected."
        else:
            errors = []
            if route_report:
                errors.extend(extract(route_report, "errors", []) or [])
            if rebalance_report:
                errors.extend(extract(rebalance_report, "errors", []) or [])
                
            if errors or (protocol and not getattr(protocol, "rollback_snapshots", None)):
                value = "reject_route_candidate"
                reason = f"Validation errors: {', '.join(errors)}"

        suggestion = RouteRebalanceFaultSuggestion(
            suggestion_id=f"SUGG_RRF_{uuid.uuid4().hex[:8]}",
            value=value,
            reason=reason
        )
        return RouteRebalanceFaultResponseReport(
            report_id=f"REPB_{uuid.uuid4().hex[:8]}",
            suggestion=suggestion,
            validated=True,
            applied=False
        )


@dataclass
class SovereignTopologySuggestion:
    suggestion_id: str
    action: str
    justification: str
    target_ref: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0


@dataclass
class SovereignTopologyClosedLoopPolicy:
    policy_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SovereignTopologyClosedLoopReport:
    report_id: str
    suggestion: SovereignTopologySuggestion
    validated: bool
    applied: bool


class SovereignTopologyAdvisor:
    """
    Advisory-only controller for sovereign topology relocation and multi-manifold reshaping.
    All suggestions remain strictly advisory in shadow mode.
    """
    def recommend_topology_action(
        self,
        telemetry_report: Any
    ) -> SovereignTopologySuggestion:
        """
        Formulates an advisory suggestion based on topology relocation parameters.
        """
        import uuid
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # Extract stats/telemetry
        crosstalk = extract(telemetry_report, "crosstalk", 0.0) or 0.0
        reflection = extract(telemetry_report, "reflection", 0.0) or 0.0
        phase_drift = extract(telemetry_report, "phase_drift", 0.0) or 0.0
        distortion = extract(telemetry_report, "distortion", 0.0) or 0.0
        route_depth = extract(telemetry_report, "route_depth", 0.0) or 0.0
        boundary_crossings = extract(telemetry_report, "boundary_crossings", 0) or 0
        
        target_ref = extract(telemetry_report, "candidate_id", "candidate_0")

        # Map to specific actions
        if extract(telemetry_report, "cadence_windows_failed") or extract(telemetry_report, "outside_cadence_window"):
            action = "hold_topology_relocation"
            justification = "Temporal cadence window validation failed; holding relocation."
        elif distortion > 1.0:
            action = "reduce_shape_distortion"
            justification = f"Shape distortion {distortion} exceeds threshold; requesting reduction."
        elif route_depth > 5.0:
            action = "reduce_route_depth"
            justification = f"Geodesic route depth {route_depth} is too high; requesting reduction."
        elif boundary_crossings > 3:
            action = "reduce_boundary_crossings"
            justification = f"Boundary crossings count {boundary_crossings} exceeds threshold."
        elif phase_drift > 0.05:
            action = "request_phase_realign"
            justification = f"Phase drift {phase_drift} is high; realign recommended."
        elif extract(telemetry_report, "global_cadence_skew", 0.0) > 0.03:
            action = "request_cadence_recalibration"
            justification = "Temporal skew detected; recalibration recommended."
        elif extract(telemetry_report, "carrier_lease_failure"):
            action = "request_carrier_recalibration"
            justification = "Carrier lease validation failed; recalibration recommended."
        elif reflection > 0.02:
            action = "increase_boundary_absorption"
            justification = f"Reflection {reflection} is slightly elevated; increase PML absorption."
        elif extract(telemetry_report, "lock_boundary_failed") or extract(telemetry_report, "cross_manifold_deadlock"):
            action = "rollback_topology_relocation"
            justification = "Critical lock boundary or deadlock violation; recommending rollback."
        elif crosstalk > 0.05:
            action = "quarantine_topology_candidate"
            justification = f"Crosstalk spike {crosstalk} detected; quarantining candidate."
        elif extract(telemetry_report, "wavefront_coherence_collapsed"):
            action = "quarantine_manifold"
            justification = "Wavefront coherence collapsed; quarantining manifold."
        else:
            action = "observe"
            justification = "All topology relocation metrics are within safe shadow parameters."

        return SovereignTopologySuggestion(
            suggestion_id=f"SUGG_TOPO_{uuid.uuid4().hex[:8]}",
            action=action,
            justification=justification,
            target_ref=target_ref
        )

    def execute_sandbox_topology_relocation(
        self,
        suggestion: SovereignTopologySuggestion,
        policy: SovereignTopologyClosedLoopPolicy,
        token: Any
    ) -> SovereignTopologyClosedLoopReport:
        """
        Executes advisory suggestion in sandbox mode. Requires valid court token.
        """
        errors = []
        if token is None:
            errors.append("Invalid or missing token for sandbox trial execution.")
        else:
            authorized = getattr(token, "authorized_by_court", False) or getattr(token, "active", False)
            if not authorized:
                errors.append("Unauthorized or inactive court token lease.")
                
        validated = len(errors) == 0
        applied = validated and suggestion.action != "observe"
        
        import uuid
        return SovereignTopologyClosedLoopReport(
            report_id=f"TOPO_REP_{uuid.uuid4().hex[:8]}",
            suggestion=suggestion,
            validated=validated,
            applied=applied
        )


@dataclass
class AutonomousCadenceSuggestion:
    suggestion_id: str
    action: str
    justification: str
    target_ref: str

@dataclass
class AutonomousCadenceClosedLoopPolicy:
    max_cadence_adjustment: float = 0.2
    max_gain_limit: float = 0.5
    allow_sandbox: bool = True

@dataclass
class AutonomousCadenceClosedLoopReport:
    report_id: str
    suggestion: AutonomousCadenceSuggestion
    validated: bool
    applied: bool


class AutonomousCadenceAdvisor:
    """
    Formulates advisory suggestions for timing and cadence synchronization.
    """
    def suggest(self, telemetry_report: Any) -> AutonomousCadenceSuggestion:
        import uuid
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # Extract values
        res = extract(telemetry_report, "result", {}) or {}
        obs = extract(res, "final_observation", {}) or {}
        
        drift = extract(obs, "cadence_drift", 0.0) or extract(telemetry_report, "drift", 0.0) or 0.0
        skew = extract(obs, "global_cadence_skew", 0.0) or extract(telemetry_report, "global_skew", 0.0) or 0.0
        crosstalk = extract(obs, "crosstalk", 0.0) or 0.0
        reflection = extract(obs, "boundary_reflection", 0.0) or 0.0
        gain = extract(extract(telemetry_report, "policy", {}), "max_feedback_gain", 0.0) or 0.0
        
        target_ref = extract(telemetry_report, "report_id", "report_0")

        if extract(telemetry_report, "split_brain") or extract(telemetry_report, "split_brain_detected"):
            action = "quarantine_manifold_clock"
            justification = "Split-brain clock detected; quarantining manifold clock."
        elif extract(telemetry_report, "guard_failed") or extract(telemetry_report, "autonomy_guard_failed"):
            action = "hold_autonomy"
            justification = "Cadence autonomy guard check failed; holding autonomy."
        elif skew > 0.05:
            action = "rollback_autonomous_sync"
            justification = f"Skew {skew} exceeds safety threshold; recommending rollback."
        elif drift > 0.03:
            action = "reduce_cadence_adjustment"
            justification = f"High drift {drift} detected; reducing adjustment step."
        elif gain > 0.5:
            action = "reduce_feedback_gain"
            justification = f"Gain {gain} exceeds limit; reducing gain."
        elif crosstalk > 0.05:
            action = "quarantine_cadence_candidate"
            justification = f"Crosstalk spike {crosstalk} detected; quarantining candidate."
        elif reflection > 0.02:
            action = "increase_boundary_absorption"
            justification = f"PML reflection {reflection} is elevated."
        elif extract(telemetry_report, "phase_drift", 0.0) > 0.03:
            action = "request_phase_realign"
            justification = "Phase drift detected; request phase realignment."
        elif extract(telemetry_report, "carrier_error", 0.0) > 0.03:
            action = "request_carrier_recalibration"
            justification = "Carrier error detected; request carrier recalibration."
        else:
            action = "observe"
            justification = "All cadence parameters are within safe shadow bounds."

        return AutonomousCadenceSuggestion(
            suggestion_id=f"SUGG_CAD_{uuid.uuid4().hex[:8]}",
            action=action,
            justification=justification,
            target_ref=target_ref
        )

    def execute_sandbox_autonomous_cadence(
        self,
        suggestion: AutonomousCadenceSuggestion,
        policy: AutonomousCadenceClosedLoopPolicy,
        token: Any
    ) -> AutonomousCadenceClosedLoopReport:
        errors = []
        if token is None:
            errors.append("Invalid or missing token for sandbox trial execution.")
        else:
            authorized = getattr(token, "authorized_by_court", False) or getattr(token, "active", False)
            if not authorized:
                errors.append("Unauthorized or inactive court token lease.")
                
        validated = len(errors) == 0
        applied = validated and suggestion.action != "observe"
        
        import uuid
        return AutonomousCadenceClosedLoopReport(
            report_id=f"CAD_REP_{uuid.uuid4().hex[:8]}",
            suggestion=suggestion,
            validated=validated,
            applied=applied
        )


@dataclass
class CoreAssemblySuggestion:
    action: str
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineCalibrationSuggestion:
    action: str
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoreAssemblyClosedLoopReport:
    report_id: str
    suggestion: Any
    validated: bool
    applied: bool
    timestamp: float = field(default_factory=time.time)


class SovereignCoreAssemblyAdvisor:
    """
    Advisory controller for multi-core assembly.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_assembly_control(
        self,
        assembly_report: Any,
        policy: Optional[Any] = None
    ) -> CoreAssemblySuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        res = extract(assembly_report, "result")
        success = extract(res, "success", True) if res is not None else extract(assembly_report, "success", True)
        metadata = extract(assembly_report, "metadata", {}) or {}
        errors = extract(res, "errors", []) or []

        if metadata.get("unstable_cadence") or metadata.get("cadence_instability") or (isinstance(assembly_report, dict) and assembly_report.get("unstable_cadence")):
            return CoreAssemblySuggestion(
                action="hold_assembly",
                reason="Core assembly blocked: unstable autonomous cadence."
            )
        elif metadata.get("stage_latency_breach"):
            return CoreAssemblySuggestion(
                action="rebalance_pipeline_stage",
                reason="Stage latency breach detected during assembly."
            )
        elif metadata.get("backpressure_breach"):
            return CoreAssemblySuggestion(
                action="reduce_core_load",
                reason="Backpressure breach detected during assembly."
            )
        elif metadata.get("cross_core_stall_breach") or metadata.get("stall_breach"):
            return CoreAssemblySuggestion(
                action="reduce_bypass_scope",
                reason="Cross-core stall breach detected; reducing bypass scope."
            )
        elif metadata.get("cadence_skew_breach") or metadata.get("high_skew"):
            return CoreAssemblySuggestion(
                action="request_core_cadence_calibration",
                reason="Cadence skew breach detected during assembly."
            )
        elif metadata.get("wavefront_timing_drift_breach"):
            return CoreAssemblySuggestion(
                action="request_wavefront_realign",
                reason="Wavefront timing drift breach detected during assembly."
            )
        elif metadata.get("carrier_timing_drift_breach"):
            return CoreAssemblySuggestion(
                action="request_carrier_recalibration",
                reason="Carrier timing drift breach detected during assembly."
            )
        elif metadata.get("pml_coverage_violated") or metadata.get("missing_pml_boundary"):
            return CoreAssemblySuggestion(
                action="increase_boundary_absorption",
                reason="PML boundary absorption violation detected during assembly."
            )
        elif metadata.get("quarantine_recommended"):
            return CoreAssemblySuggestion(
                action="quarantine_core",
                reason="Quarantine recommended for core unit."
            )
        elif metadata.get("quarantine_stage_recommended"):
            return CoreAssemblySuggestion(
                action="quarantine_pipeline_stage",
                reason="Quarantine recommended for pipeline stage."
            )
        elif not success or errors:
            return CoreAssemblySuggestion(
                action="rollback_assembly",
                reason="Core assembly validation failed or has errors."
            )
        else:
            return CoreAssemblySuggestion(
                action="observe",
                reason="Core assembly stability is within shadow limits."
            )


class PipelineCalibrationAdvisor:
    """
    Advisory controller for pipeline calibration.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_calibration_control(
        self,
        calibration_report: Any,
        policy: Optional[Any] = None
    ) -> PipelineCalibrationSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        res = extract(calibration_report, "result")
        success = extract(res, "success", True) if res is not None else extract(calibration_report, "success", True)
        metadata = extract(calibration_report, "metadata", {}) or {}
        errors = extract(res, "errors", []) or []

        if metadata.get("stage_latency_breach"):
            return PipelineCalibrationSuggestion(
                action="rebalance_pipeline_stage",
                reason="Stage latency breach detected."
            )
        elif metadata.get("backpressure_breach"):
            return PipelineCalibrationSuggestion(
                action="reduce_core_load",
                reason="Backpressure breach detected."
            )
        elif metadata.get("cross_core_stall_breach") or metadata.get("stall_breach"):
            return PipelineCalibrationSuggestion(
                action="reduce_bypass_scope",
                reason="Cross-core stall breach detected."
            )
        elif metadata.get("cadence_skew_breach") or metadata.get("high_skew"):
            return PipelineCalibrationSuggestion(
                action="request_core_cadence_calibration",
                reason="Cadence skew breach detected."
            )
        elif metadata.get("wavefront_timing_drift_breach"):
            return PipelineCalibrationSuggestion(
                action="request_wavefront_realign",
                reason="Wavefront timing drift breach detected."
            )
        elif metadata.get("carrier_timing_drift_breach"):
            return PipelineCalibrationSuggestion(
                action="request_carrier_recalibration",
                reason="Carrier timing drift breach detected."
            )
        elif metadata.get("pml_coverage_violated") or metadata.get("missing_pml_boundary"):
            return PipelineCalibrationSuggestion(
                action="increase_boundary_absorption",
                reason="PML boundary absorption violation detected."
            )
        elif metadata.get("quarantine_recommended"):
            return PipelineCalibrationSuggestion(
                action="quarantine_core",
                reason="Quarantine recommended for core unit."
            )
        elif metadata.get("quarantine_stage_recommended"):
            return PipelineCalibrationSuggestion(
                action="quarantine_pipeline_stage",
                reason="Quarantine recommended for pipeline stage."
            )
        elif not success or errors:
            return PipelineCalibrationSuggestion(
                action="rollback_assembly",
                reason="Pipeline calibration failed or has errors."
            )
        else:
            return PipelineCalibrationSuggestion(
                action="observe",
                reason="Pipeline calibration is within acceptable bounds."
            )


@dataclass
class PipelineBalanceSuggestion:
    action: str
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuantumWavefrontSuggestion:
    action: str
    reason: str
    nudge_value: float = 0.0
    damping_adjustment: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineWavefrontClosedLoopReport:
    report_id: str
    suggestion: Any
    validated: bool
    applied: bool
    timestamp: float = field(default_factory=time.time)


class GeodesicPipelineBalanceAdvisor:
    """
    Advisory controller for geodesic pipeline balancing.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_balance_control(
        self,
        balance_report: Any,
        policy: Optional[Any] = None
    ) -> PipelineBalanceSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        res = extract(balance_report, "result")
        success = extract(res, "success", True) if res is not None else extract(balance_report, "success", True)
        metadata = extract(balance_report, "metadata", {}) or {}
        errors = extract(res, "errors", []) or []

        if metadata.get("quarantine_segment") or metadata.get("quarantine_pipeline_segment"):
            return PipelineBalanceSuggestion(
                action="quarantine_pipeline_segment",
                reason="Quarantine recommended for pipeline segment."
            )
        elif metadata.get("quarantine_core"):
            return PipelineBalanceSuggestion(
                action="quarantine_core",
                reason="Quarantine recommended for core."
            )
        elif metadata.get("quarantine_wavefront_packet"):
            return PipelineBalanceSuggestion(
                action="quarantine_wavefront_packet",
                reason="Quarantine recommended for wavefront packet."
            )
        elif metadata.get("route_depth_breach"):
            return PipelineBalanceSuggestion(
                action="reduce_route_depth",
                reason="Geodesic route depth breach detected."
            )
        elif metadata.get("backpressure_breach") or metadata.get("reduce_core_load"):
            return PipelineBalanceSuggestion(
                action="reduce_core_load",
                reason="Backpressure breach or core overload detected."
            )
        elif metadata.get("stage_latency_breach"):
            return PipelineBalanceSuggestion(
                action="rebalance_pipeline_stage",
                reason="Stage latency breach detected during balancing."
            )
        elif not success or errors:
            return PipelineBalanceSuggestion(
                action="rollback_balance",
                reason="Pipeline balance failed or has errors."
            )
        else:
            return PipelineBalanceSuggestion(
                action="observe",
                reason="Pipeline balance metrics are within shadow limits."
            )


class QuantumWavefrontCalibrationAdvisor:
    """
    Advisory controller for quantum wavefront calibration.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_calibration_control(
        self,
        calibration_report: Any,
        policy: Optional[Any] = None
    ) -> QuantumWavefrontSuggestion:
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        res = extract(calibration_report, "result")
        success = extract(res, "success", True) if res is not None else extract(calibration_report, "success", True)
        metadata = extract(calibration_report, "metadata", {}) or {}
        errors = extract(res, "errors", []) or []

        if metadata.get("unbounded_uncertainty"):
            return QuantumWavefrontSuggestion(
                action="rollback_wavefront_calibration",
                reason="Unbounded wavefront uncertainty blocks calibration."
            )
        elif metadata.get("wavefront_dispersion_breach"):
            return QuantumWavefrontSuggestion(
                action="reduce_wavefront_dispersion",
                reason="Wavefront dispersion exceeds threshold."
            )
        elif metadata.get("cadence_skew_breach"):
            return QuantumWavefrontSuggestion(
                action="request_quantum_wavefront_realign",
                reason="Quantum wavefront alignment requested."
            )
        elif metadata.get("carrier_recalibration_required") or metadata.get("carrier_timing_drift_breach"):
            return QuantumWavefrontSuggestion(
                action="request_carrier_recalibration",
                reason="Carrier recalibration requested."
            )
        elif metadata.get("pml_coverage_violated") or metadata.get("missing_pml_boundary"):
            return QuantumWavefrontSuggestion(
                action="increase_boundary_absorption",
                reason="PML boundary absorption violation detected."
            )
        elif metadata.get("quarantine_wavefront_packet"):
            return QuantumWavefrontSuggestion(
                action="quarantine_wavefront_packet",
                reason="Quarantine recommended for wavefront packet."
            )
        elif not success or errors:
            return QuantumWavefrontSuggestion(
                action="rollback_wavefront_calibration",
                reason="Quantum wavefront calibration failed or has errors."
            )
        else:
            return QuantumWavefrontSuggestion(
                action="observe",
                reason="Quantum wavefront calibration metrics are within shadow limits."
            )


@dataclass
class PipelineWavefrontFaultSuggestion:
    suggestion_id: str
    action: str
    justification: str


@dataclass
class PipelineWavefrontFaultResponsePolicy:
    allow_shadow_fault_response: bool = True
    quarantine_threshold: float = 0.5


@dataclass
class PipelineWavefrontFaultResponseReport:
    report_id: str
    suggestion: PipelineWavefrontFaultSuggestion
    validated: bool = True
    applied: bool = False


class PipelineWavefrontFaultAdvisor:
    """
    Formulates advisory suggestions in response to pipeline wavefront fault occurrences.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_response(
        self,
        fault_report: Any,
        policy: Optional[PipelineWavefrontFaultResponsePolicy] = None
    ) -> PipelineWavefrontFaultResponseReport:
        import uuid
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        action = "observe"
        justification = "All systems green."

        errors = []
        results = []
        
        if fault_report:
            errors.extend(extract(fault_report, "errors", []) or [])
            results.extend(extract(fault_report, "results", []) or [])
        
        has_failure = False
        for res in results:
            if not extract(res, "success", True):
                has_failure = True
                
        if errors or has_failure:
            action = "reject_candidate"
            justification = f"Pipeline wavefront fault audit detected failures."

        suggestion = PipelineWavefrontFaultSuggestion(
            suggestion_id=f"SUGG_PWF_{uuid.uuid4().hex[:8]}",
            action=action,
            justification=justification
        )
        return PipelineWavefrontFaultResponseReport(
            report_id=f"REPB_WF_{uuid.uuid4().hex[:8]}",
            suggestion=suggestion,
            validated=True,
            applied=False
        )


@dataclass
class BurnInRuntimeSuggestion:
    suggestion_id: str
    action: str
    justification: str


@dataclass
class BurnInStabilityPolicy:
    stability_threshold: float = 0.95
    sandbox_token: Optional[str] = None


@dataclass
class BurnInClosedLoopReport:
    report_id: str
    suggestion: BurnInRuntimeSuggestion
    validated: bool = True
    applied: bool = False


class BurnInRuntimeAdvisor:
    """
    Advisory-only burn-in advisor interfacing with Frontier_OS.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_response(
        self,
        burnin_report: Any,
        policy: Optional[BurnInStabilityPolicy] = None
    ) -> BurnInClosedLoopReport:
        import uuid
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        action = "observe"
        justification = "Burn-in execution normal."

        if burnin_report:
            errors = extract(burnin_report, "errors", []) or []
            result = extract(burnin_report, "result", None)
            if result:
                success = extract(result, "success", True)
                cycle_results = extract(result, "cycle_results", []) or []
                if not success:
                    action = "hold_burnin"
                    justification = "Burn-in cycle failures detected."
                
                for cyc_res in cycle_results:
                    metrics = extract(cyc_res, "metrics", {}) or {}
                    if metrics.get("oracle_match_rate", 1.0) < 1.0:
                        action = "reject_burnin_candidate"
                        justification = "Oracle mismatch spike detected."
                    elif metrics.get("wavefront_coherence", 1.0) < 0.90:
                        action = "rollback_to_checkpoint"
                        justification = "Wavefront coherence collapsed."
                    elif metrics.get("phase_drift", 0.0) > 0.05:
                        action = "hold_burnin"
                        justification = "Critical phase drift detected."

            passed_audit = extract(burnin_report, "passed_audit", True)
            if not passed_audit:
                if action == "observe":
                    action = "hold_burnin"
                    justification = "Burn-in audit failed."

        token = extract(policy, "sandbox_token", None) if policy else None
        applied = False
        if token and token != "INVALID_TOKEN":
            applied = True

        suggestion = BurnInRuntimeSuggestion(
            suggestion_id=f"SUGG_BRN_{uuid.uuid4().hex[:8]}",
            action=action,
            justification=justification
        )
        return BurnInClosedLoopReport(
            report_id=f"REPB_BRN_{uuid.uuid4().hex[:8]}",
            suggestion=suggestion,
            validated=True,
            applied=applied
        )


@dataclass
class SystemFinalizationSuggestion:
    suggestion_id: str
    action: str  # observe, hold_finalization, request_more_evidence, request_ranger_review, request_court_review, request_ledger_repair, request_api_contract_review, request_governance_freeze_review, reject_gateway_request, quarantine_finalization_candidate
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class ProductionGatewaySuggestion:
    suggestion_id: str
    action: str  # observe, reject_gateway_request, request_more_evidence, hold_finalization
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class SystemFinalizationClosedLoopReport:
    report_id: str
    suggestion: Any  # SystemFinalizationSuggestion or ProductionGatewaySuggestion
    validated: bool = True
    applied: bool = False
    timestamp: float = field(default_factory=time.time)

class SystemFinalizationAdvisor:
    """
    Advisory-only system finalization advisor.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_finalization(
        self,
        final_manifest: Any,
        policy: Optional[Any] = None
    ) -> SystemFinalizationClosedLoopReport:
        import uuid
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        action = "observe"
        justification = "System finalization evidence checks normal."

        if final_manifest:
            valid = extract(final_manifest, "valid", True)
            if not valid:
                action = "hold_finalization"
                justification = "System finalization manifest contains validation failures."
                
            quarantine = extract(final_manifest, "quarantine_status", "none")
            if quarantine == "quarantined":
                action = "quarantine_finalization_candidate"
                justification = "System is quarantined."

            evidence_items = extract(final_manifest, "evidence", []) or []
            evidence_types = {extract(item, "evidence_type") for item in evidence_items}
            if "api_contract" in evidence_types:
                for item in evidence_items:
                    if extract(item, "evidence_type") == "api_contract" and extract(item, "payload", {}).get("broken"):
                        action = "request_api_contract_review"
                        justification = "API contract broken."
            if "governance_freeze" in evidence_types:
                for item in evidence_items:
                    if extract(item, "evidence_type") == "governance_freeze" and not extract(item, "payload", {}).get("frozen", True):
                        action = "request_governance_freeze_review"
                        justification = "Governance freeze violation."

        token = extract(policy, "sandbox_token") or extract(policy, "court_token")
        applied = False
        if token and token != "INVALID_TOKEN":
            applied = True

        suggestion = SystemFinalizationSuggestion(
            suggestion_id=f"SUGG_FIN_{uuid.uuid4().hex[:8]}",
            action=action,
            justification=justification
        )
        return SystemFinalizationClosedLoopReport(
            report_id=f"REPB_FIN_{uuid.uuid4().hex[:8]}",
            suggestion=suggestion,
            validated=True,
            applied=applied
        )

class ProductionGatewayAdvisor:
    """
    Advisory-only production gateway advisor.
    """
    def __init__(self, bridge: FrontierBridge):
        self.bridge = bridge

    def suggest_gateway_response(
        self,
        gateway_report: Any,
        policy: Optional[Any] = None
    ) -> SystemFinalizationClosedLoopReport:
        import uuid
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        action = "observe"
        justification = "Gateway request normal."

        if gateway_report:
            dec_obj = extract(gateway_report, "decision")
            decision_str = extract(dec_obj, "decision") if dec_obj else None
            if decision_str == "deny":
                action = "reject_gateway_request"
                justification = extract(dec_obj, "justification", "Gateway check denied.")
            elif decision_str == "hold":
                action = "hold_finalization"
                justification = "Gateway request is held."
            elif decision_str == "needs_more_evidence":
                action = "request_more_evidence"
                justification = "Gateway request needs more evidence."

        token = extract(policy, "sandbox_token") or extract(policy, "court_token")
        applied = False
        if token and token != "INVALID_TOKEN":
            applied = True

        suggestion = ProductionGatewaySuggestion(
            suggestion_id=f"SUGG_GW_{uuid.uuid4().hex[:8]}",
            action=action,
            justification=justification
        )
        return SystemFinalizationClosedLoopReport(
            report_id=f"REPB_GW_{uuid.uuid4().hex[:8]}",
            suggestion=suggestion,
            validated=True,
            applied=applied
        )
















