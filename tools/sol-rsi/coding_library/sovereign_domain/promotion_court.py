# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Sovereign Promotion Court
=========================
Validates design and simulation evidence packets to vote on promoting new SOL layers.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from coding_library.sovereign_domain.evidence_packet import SovereignPacket

@dataclass
class PromotionGateResult:
    decision: str  # "observe" | "needs_more_evidence" | "authorize_candidate_phase_correction" | "authorize_candidate_damping_correction" | "quarantine_lane" | "reject"
    gate_name: str
    passed: bool
    evidence_hash: str
    details: Dict[str, Any]

@dataclass
class CalibrationCorrectionDecision:
    authorized: bool
    decision: str
    target_lane: int
    correction_type: str  # "phase" | "damping" | "none"
    reproducibility_hash: str
    reason: str

class PromotionCourt:
    """
    Judicial branch that reviews evidence packets and decides on component promotions.
    """
    def __init__(self):
        self.submitted_packets: List[SovereignPacket] = []

    def submit_packet(self, packet: SovereignPacket):
        """Submit a new evidence packet to the court."""
        self.submitted_packets.append(packet)

    def evaluate_promotion(self, mission_id: str) -> bool:
        """
        Check all submitted packets for the given mission.
        Promotes if there are valid packets and no 'reject' or 'quarantine' recommendations.
        """
        packets = [p for p in self.submitted_packets if p.mission_id == mission_id]
        if not packets:
            return False
            
        for p in packets:
            if p.recommendation in ["reject", "quarantine"]:
                return False
                
        return True

    def review_drift_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a drift packet's evidence and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        evidence = extract(packet, "evidence", {})
        max_err = abs(extract(evidence, "max_phase_error", 0.0))
        tolerance = extract(evidence, "tolerance", 0.05)
        lane_id = extract(evidence, "lane_id", 0)
        repro_hash = extract(packet, "reproducibility_hash", "none")

        if max_err <= tolerance:
            decision = "observe"
            passed = True
        elif max_err <= 0.15:
            decision = "authorize_candidate_phase_correction"
            passed = True
        elif max_err <= 0.30:
            decision = "needs_more_evidence"
            passed = False
        elif max_err <= 0.50:
            decision = "quarantine_lane"
            passed = False
        else:
            decision = "reject"
            passed = False

        return PromotionGateResult(
            decision=decision,
            gate_name=f"drift_gate_lane_{lane_id}",
            passed=passed,
            evidence_hash=repro_hash,
            details={"max_phase_error": max_err, "tolerance": tolerance, "lane_id": lane_id}
        )

    def review_waveguide_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews waveguide reflection/damping packet evidence and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        evidence = extract(packet, "evidence", {})
        reflection_score = extract(evidence, "reflection_score", 0.0)
        lane_id = extract(evidence, "lane_id", 0)
        repro_hash = extract(packet, "reproducibility_hash", "none")

        if reflection_score <= 0.05:
            decision = "observe"
            passed = True
        elif reflection_score <= 0.15:
            decision = "authorize_candidate_damping_correction"
            passed = True
        elif reflection_score <= 0.25:
            decision = "needs_more_evidence"
            passed = False
        elif reflection_score <= 0.40:
            decision = "quarantine_lane"
            passed = False
        else:
            decision = "reject"
            passed = False

        return PromotionGateResult(
            decision=decision,
            gate_name=f"waveguide_gate_lane_{lane_id}",
            passed=passed,
            evidence_hash=repro_hash,
            details={"reflection_score": reflection_score, "lane_id": lane_id}
        )

    def authorize_candidate_correction(self, packet: Any, policy: Any) -> CalibrationCorrectionDecision:
        """
        Evaluates a decision packet and authorizes a candidate correction within policy bounds.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        decision = extract(packet, "decision")
        details = extract(packet, "details", {})
        lane_id = extract(details, "lane_id", 0)
        repro_hash = extract(packet, "evidence_hash", "none")
        if repro_hash == "none":
            repro_hash = extract(packet, "reproducibility_hash", "none")

        # Check policy bounds
        max_phase_nudge = extract(policy, "max_phase_nudge", 0.05)
        max_damping_delta = extract(policy, "max_damping_delta", 0.01)

        nudge_value = extract(details, "nudge_value", 0.0)
        if nudge_value == 0.0:
            max_err = extract(details, "max_phase_error", 0.0)
            nudge_value = -0.5 * max_err
            
        damping_delta = extract(details, "damping_adjustment", 0.0)
        if damping_delta == 0.0 and decision == "authorize_candidate_damping_correction":
            damping_delta = 0.005

        if decision == "authorize_candidate_phase_correction":
            clamped_nudge = max(-max_phase_nudge, min(max_phase_nudge, nudge_value))
            return CalibrationCorrectionDecision(
                authorized=True,
                decision=decision,
                target_lane=lane_id,
                correction_type="phase",
                reproducibility_hash=repro_hash,
                reason=f"Authorized phase correction clamped to {clamped_nudge:.4f} radians"
            )
        elif decision == "authorize_candidate_damping_correction":
            clamped_damping = max(-max_damping_delta, min(max_damping_delta, damping_delta))
            return CalibrationCorrectionDecision(
                authorized=True,
                decision=decision,
                target_lane=lane_id,
                correction_type="damping",
                reproducibility_hash=repro_hash,
                reason=f"Authorized damping adjustment clamped to {clamped_damping:.4f}"
            )
        elif decision == "quarantine_lane":
            return CalibrationCorrectionDecision(
                authorized=False,
                decision=decision,
                target_lane=lane_id,
                correction_type="none",
                reproducibility_hash=repro_hash,
                reason="Lane quarantined due to critical threshold breach."
            )
        elif decision == "reject":
            return CalibrationCorrectionDecision(
                authorized=False,
                decision=decision,
                target_lane=lane_id,
                correction_type="none",
                reproducibility_hash=repro_hash,
                reason="Rejected due to critical failure."
            )
        else:
            return CalibrationCorrectionDecision(
                authorized=False,
                decision=decision or "observe",
                target_lane=lane_id,
                correction_type="none",
                reproducibility_hash=repro_hash,
                reason="No correction authorized (observation only or deferred)."
            )

    def review_word_commit_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a word commit packet's evidence and gates, returning a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        gate_report = extract(packet, "gate_report", {})
        passed = extract(gate_report, "passed", False)
        errors = extract(gate_report, "errors", [])
        checked_gates = extract(gate_report, "checked_gates", {})
        
        op = extract(packet, "op", "UNKNOWN")
        width = extract(packet, "width", 0)
        repro_hash = extract(packet, "reproducibility_hash", "none")
        inst_id = extract(packet, "instruction_id", "none")

        if not passed:
            if not checked_gates.get("width_supported", True) or not checked_gates.get("lane_count_matches_width", True):
                decision = "reject_commit"
            elif not checked_gates.get("carry_trace_present_for_add_sub", True):
                decision = "needs_more_evidence"
            elif not checked_gates.get("result_masked_to_width", True):
                decision = "reject_commit"
            elif not checked_gates.get("dry_run_required_by_default", True) or not checked_gates.get("promotion_packet_required_for_live_commit", True):
                decision = "quarantine_instruction"
            else:
                decision = "reject_commit"
        else:
            if op == "COMMIT_WORD":
                decision = "authorize_scaffold_commit"
            else:
                decision = "accept_dry_run_commit"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"word_gate_{inst_id}",
            passed=passed,
            evidence_hash=repro_hash,
            details={
                "op": op,
                "width": width,
                "errors": errors,
                "checked_gates": checked_gates
            }
        )

    def review_pdm_execution_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a PDM execution report's evidence and gates, returning a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        passed = extract(report, "passed_gates", False)
        match = extract(report, "oracle_match", False)
        repro_hash = extract(report, "reproducibility_hash", "none")
        inst_id = extract(report, "instruction_id", "none")
        
        active_delta = 1.0
        demod_res = extract(report, "demodulation_result", {})
        demod_amps = extract(demod_res, "demodulated_amplitudes", [])
        trace = extract(report, "trace", {})
        plan = extract(trace, "plan", {})
        encoded_word = extract(plan, "encoded_word", [])
        
        if encoded_word and demod_amps:
            active_amps = []
            inactive_amps = []
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

        if not passed:
            decision = "reject_execution"
        elif not match:
            decision = "quarantine_lane"
        elif active_delta < 0.20:
            decision = "needs_more_evidence"
        else:
            decision = "accept_shadow_execution"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"pdm_execution_gate_{inst_id}",
            passed=(decision == "accept_shadow_execution"),
            evidence_hash=repro_hash,
            details={
                "instruction_id": inst_id,
                "passed_gates": passed,
                "oracle_match": match,
                "active_delta": active_delta
            }
        )

    def review_frontier_adjustment_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a Frontier closed-loop driver's candidate adjustment correction, returning a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        confidence = extract(packet, "confidence", 0.0)
        bounded_delta = extract(packet, "bounded_delta", 0.0)
        corr_type = extract(packet, "correction_type", "phase")
        repro_hash = extract(packet, "evidence_hash", "none")
        lane_id = extract(packet, "target_lane", 0)

        limit = 0.05 if corr_type == "phase" else 0.01
        
        if confidence < 0.90:
            decision = "needs_more_evidence"
            passed = False
        elif abs(bounded_delta) > limit:
            decision = "reject_execution"
            passed = False
        else:
            decision = "authorize_candidate_adjustment"
            passed = True

        return PromotionGateResult(
            decision=decision,
            gate_name=f"frontier_adjustment_gate_lane_{lane_id}",
            passed=passed,
            evidence_hash=repro_hash,
            details={
                "confidence": confidence,
                "bounded_delta": bounded_delta,
                "correction_type": corr_type,
                "target_lane": lane_id
            }
        )

    def review_live_mutation_request(self, request: Any) -> PromotionGateResult:
        """
        Reviews a live mutation request using safety gates.
        Returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        sandbox = extract(request, "sandbox", True)
        cand = extract(request, "candidate_correction", None)
        report = extract(request, "shadow_report", None)
        ranger_ev = extract(request, "ranger_evidence", None)
        req_id = extract(request, "request_id", "none")

        if not sandbox:
            return PromotionGateResult(
                decision="reject_live_mutation",
                gate_name=f"live_mutation_gate_{req_id}",
                passed=False,
                evidence_hash="none",
                details={"error": "Rejected: sandbox_only gate violated."}
            )

        if cand is None or report is None or ranger_ev is None:
            return PromotionGateResult(
                decision="needs_more_evidence",
                gate_name=f"live_mutation_gate_{req_id}",
                passed=False,
                evidence_hash="none",
                details={"error": "Missing candidate, shadow report, or ranger evidence."}
            )

        passed_gates = extract(report, "passed_gates", False)
        match = extract(report, "oracle_match", False)
        repro_hash = extract(report, "reproducibility_hash", "none")

        if not passed_gates or not match:
            return PromotionGateResult(
                decision="reject_live_mutation",
                gate_name=f"live_mutation_gate_{req_id}",
                passed=False,
                evidence_hash=repro_hash,
                details={"error": "Previous shadow/dry-run execution did not pass all gates."}
            )

        ranger_rec = extract(ranger_ev, "recommendation", "")
        if ranger_rec not in ["promote", "observe"]:
            return PromotionGateResult(
                decision="reject_live_mutation",
                gate_name=f"live_mutation_gate_{req_id}",
                passed=False,
                evidence_hash=repro_hash,
                details={"error": f"Ranger recommendation is not advisory (got: {ranger_rec})."}
            )

        corr_type = extract(cand, "correction_type", "phase")
        bounded_delta = extract(cand, "bounded_delta", 0.0)
        limit = 0.05 if corr_type == "phase" else 0.01

        if abs(bounded_delta) > limit:
            return PromotionGateResult(
                decision="reject_live_mutation",
                gate_name=f"live_mutation_gate_{req_id}",
                passed=False,
                evidence_hash=repro_hash,
                details={"error": f"Delta {bounded_delta:.4f} exceeds safety policy limit."}
            )

        return PromotionGateResult(
            decision="authorize_sandbox_live_mutation",
            gate_name=f"live_mutation_gate_{req_id}",
            passed=True,
            evidence_hash=repro_hash,
            details={
                "target_lane": extract(cand, "target_lane", 0),
                "correction_type": corr_type,
                "bounded_delta": bounded_delta
            }
        )

    def authorize_live_control_token(self, request: Any, policy: Any) -> Any:
        """
        Reviews request against policy constraints and issues a LiveControlToken.
        """
        from coding_library.sovereign_domain.frontier_bridge import LiveControlToken
        import time

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        gate_res = self.review_live_mutation_request(request)
        if not gate_res.passed:
            return LiveControlToken(
                token_id="UNAUTHORIZED_TOKEN",
                authorized_by_court=False,
                issued_at=time.time(),
                expires_at=time.time(),
                sandbox_only=True,
                target_lane=0,
                max_mutations=0,
                active=False
            )

        cand = extract(request, "candidate_correction")
        lane_id = extract(cand, "target_lane", 0)
        corr_type = extract(cand, "correction_type", "phase")
        bounded_delta = extract(cand, "bounded_delta", 0.0)
        target_channel = extract(cand, "target_channel", None)
        req_id = extract(request, "request_id", "none")

        return LiveControlToken(
            token_id=f"TOKEN_AUTH_{req_id}_{int(time.time())}",
            authorized_by_court=True,
            issued_at=time.time(),
            expires_at=time.time() + 300.0,
            sandbox_only=True,
            target_lane=lane_id,
            max_mutations=policy.max_mutations_per_lane,
            correction_type=corr_type,
            bounded_delta=bounded_delta,
            target_channel=target_channel,
            active=True
        )

    def revoke_live_control_token(self, token: Any) -> None:
        """
        Immediately revokes an active LiveControlToken.
        """
        if hasattr(token, "active"):
            token.active = False

    def review_wideword_fabric_report(self, report: Any) -> PromotionGateResult:
        """
        Evaluates WideWordFabricReport gates and decides on promotion / quarantine / sandbox trial.
        """
        passed = report.passed_gates
        oracle_match = report.oracle_match
        crosstalk_ok = all(v <= 0.05 for v in report.crosstalk_levels.values())
        
        pdm_report = report.pdm_report
        checked_gates = pdm_report.gate_report.checked_gates
        
        has_pml = checked_gates.get("all_lanes_have_pml_profile", True)
        has_phase = checked_gates.get("all_lanes_have_phase_table", True)
        carry_complete = checked_gates.get("prefix_carry_trace_complete", True)
        
        errors = pdm_report.gate_report.errors
        
        if not passed or not oracle_match:
            if not oracle_match:
                decision = "reject_fabric"
            elif not has_pml or not has_phase:
                decision = "needs_more_evidence"
            else:
                decision = "quarantine_lane"
            passed_court = False
        elif not crosstalk_ok:
            decision = "quarantine_lane"
            passed_court = False
        elif not carry_complete:
            decision = "needs_more_evidence"
            passed_court = False
        else:
            if report.metadata.get("sandbox_trial", False):
                decision = "authorize_sandbox_fabric_trial"
            else:
                decision = "promote_fabric_candidate"
            passed_court = True
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"fabric_court_gate_{report.instruction_id}",
            passed=passed_court,
            evidence_hash=report.reproducibility_hash,
            details={
                "decision": decision,
                "errors": errors,
                "crosstalk_ok": crosstalk_ok,
                "pml_ok": has_pml,
                "phase_ok": has_phase
            }
        )

    def review_hcam_recall_report(self, report: Any) -> PromotionGateResult:
        """
        Evaluates HCAMRecallReport gates and decides on promotion / quarantine / sandbox trial.
        """
        passed = report.passed_gates
        oracle_match = report.oracle_match
        
        checked_gates = report.gate_report.checked_gates
        
        width_supported = checked_gates.get("width_supported", True)
        bank_count_matches = checked_gates.get("bank_count_matches_width", True)
        all_lanes_have_banks = checked_gates.get("all_lanes_have_banks", True)
        all_banks_have_boundaries = checked_gates.get("all_banks_have_boundaries", True)
        query_routes_complete = checked_gates.get("query_routes_complete", True)
        response_routes_complete = checked_gates.get("response_routes_complete", True)
        reduction_tree_complete = checked_gates.get("reduction_tree_complete", True)
        
        errors = report.gate_report.errors
        
        if not passed or not oracle_match:
            if not oracle_match:
                decision = "reject_recall"
            elif not all_lanes_have_banks or not all_banks_have_boundaries:
                decision = "needs_more_evidence"
            else:
                decision = "quarantine_bank"
            passed_court = False
        elif not query_routes_complete or not response_routes_complete or not reduction_tree_complete:
            decision = "needs_more_evidence"
            passed_court = False
        else:
            if report.metadata.get("sandbox_trial", False):
                decision = "authorize_sandbox_recall_trial"
            else:
                decision = "promote_hcam_candidate"
            passed_court = True
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"hcam_court_gate_{report.instruction_id}",
            passed=passed_court,
            evidence_hash=report.reproducibility_hash,
            details={
                "decision": decision,
                "errors": errors,
                "width_supported": width_supported,
                "bank_count_matches": bank_count_matches,
                "all_lanes_have_banks": all_lanes_have_banks,
                "all_banks_have_boundaries": all_banks_have_boundaries,
                "query_routes_complete": query_routes_complete,
                "response_routes_complete": response_routes_complete,
                "reduction_tree_complete": reduction_tree_complete
            }
        )

    def review_simd_execution_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a SIMD execution report and decides on promotion/quarantine.
        """
        passed = report.passed_gates
        oracle_match = report.oracle_match
        
        checked_gates = report.gate_report.checked_gates
        
        mode_supported = checked_gates.get("mode_supported", True)
        lane_group_mapping_complete = checked_gates.get("lane_group_mapping_complete", True)
        operand_count_valid = checked_gates.get("operand_count_valid", True)
        result_masked_to_lane_width = checked_gates.get("result_masked_to_lane_width", True)
        
        errors = report.gate_report.errors
        
        if not passed or not oracle_match:
            if not oracle_match:
                decision = "reject_simd"
            elif not mode_supported:
                decision = "needs_more_evidence"
            else:
                decision = "quarantine_mode"
            passed_court = False
        elif not lane_group_mapping_complete or not operand_count_valid or not result_masked_to_lane_width:
            decision = "needs_more_evidence"
            passed_court = False
        else:
            if report.metadata.get("sandbox_trial", False):
                decision = "authorize_sandbox_simd_trial"
            else:
                decision = "promote_level14_candidate"
            passed_court = True
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"simd_court_gate_{report.instruction_id}",
            passed=passed_court,
            evidence_hash=report.reproducibility_hash,
            details={
                "decision": decision,
                "errors": errors,
                "mode_supported": mode_supported,
                "lane_group_mapping_complete": lane_group_mapping_complete,
                "operand_count_valid": operand_count_valid,
                "result_masked_to_lane_width": result_masked_to_lane_width
            }
        )

    def review_geodesic_reduction_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a geodesic reduction tree execution report and decides on promotion.
        """
        passed = report.passed_gates
        oracle_match = report.oracle_match
        
        checked_gates = report.gate_report.checked_gates
        reduction_tree_complete = checked_gates.get("reduction_tree_complete_if_required", True)
        no_unbounded_reduction_path = checked_gates.get("no_unbounded_reduction_path", True)
        
        errors = report.gate_report.errors
        
        if not passed or not oracle_match:
            decision = "reject_simd"
            passed_court = False
        elif not reduction_tree_complete:
            decision = "needs_more_evidence"
            passed_court = False
        elif not no_unbounded_reduction_path:
            decision = "quarantine_mode"
            passed_court = False
        else:
            if report.metadata.get("sandbox_trial", False):
                decision = "authorize_sandbox_simd_trial"
            else:
                decision = "promote_level14_candidate"
            passed_court = True
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"reduction_court_gate_{report.instruction_id}",
            passed=passed_court,
            evidence_hash=report.reproducibility_hash,
            details={
                "decision": decision,
                "errors": errors,
                "reduction_tree_complete": reduction_tree_complete,
                "no_unbounded_reduction_path": no_unbounded_reduction_path
            }
        )

    def review_cross_manifold_routing_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a cross-manifold routing report and decides on promotion/quarantine.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        passed = extract(report, "passed_gates", False)
        oracle_match = extract(report, "oracle_match", False)
        depth = extract(report, "route_depth", 0)
        repro_hash = extract(report, "reproducibility_hash", "none")
        inst_id = extract(report, "request_id", "none")
        
        gate_rep = extract(report, "gate_report", {})
        errors = extract(gate_rep, "errors", [])
        
        if not passed or not oracle_match:
            if not oracle_match:
                decision = "reject_route"
            elif depth > 4:
                decision = "quarantine_route"
            else:
                decision = "needs_more_evidence"
            passed_court = False
        else:
            meta = extract(report, "metadata", {})
            if meta.get("sandbox_trial", False):
                decision = "authorize_sandbox_route_trial"
            elif meta.get("stability_decision") == "stable":
                decision = "promote_cross_manifold_candidate"
            else:
                decision = "accept_shadow_route"
            passed_court = True
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"cross_manifold_court_gate_{inst_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "errors": errors,
                "oracle_match": oracle_match,
                "route_depth": depth
            }
        )

    def review_entanglement_stability_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an entanglement stability report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        stable = extract(report, "stable", False)
        decision = extract(report, "decision", "stable")
        coherence = extract(report, "phase_coherence", 1.0)
        drift = extract(report, "transfer_drift", 0.0)
        repro_hash = extract(report, "reproducibility_hash", "none")
        obs_id = extract(report, "observation_id", "none")

        if stable:
            court_decision = "promote_cross_manifold_candidate"
        elif decision == "quarantine_route":
            court_decision = "quarantine_route"
        elif decision in ("reject_transfer", "rollback_recommended"):
            court_decision = "reject_route"
        else:
            court_decision = "needs_more_evidence"

        return PromotionGateResult(
            decision=court_decision,
            gate_name=f"entanglement_stability_court_gate_{obs_id}",
            passed=stable,
            evidence_hash=repro_hash,
            details={
                "decision": court_decision,
                "phase_coherence": coherence,
                "transfer_drift": drift,
                "internal_decision": decision
            }
        )

    def review_wavefront_consensus_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a wavefront consensus report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        passed_gates = extract(report, "passed_gates", False)
        proposal = extract(report, "proposal")
        proposal_id = extract(proposal, "proposal_id", "unknown")
        repro_hash = extract(report, "reproducibility_hash", "none")
        
        gate_report = extract(report, "gate_report")
        checked_gates = extract(gate_report, "checked_gates", {}) if gate_report is not None else {}
        errors = extract(gate_report, "errors", []) if gate_report is not None else []
        
        quorum_reached = checked_gates.get("quorum_reached", False)
        state_hashes_valid = checked_gates.get("state_hashes_valid", True)
        group_coherence_within_tolerance = checked_gates.get("group_coherence_within_tolerance", True)
        entanglement_stability_passed = checked_gates.get("entanglement_stability_passed", True)
        sequencer_group_valid = checked_gates.get("sequencer_group_valid", True)
        sequencer_count_minimum_met = checked_gates.get("sequencer_count_minimum_met", True)
        route_valid_if_transfer = checked_gates.get("route_valid_if_transfer", True)
        oracle_match = checked_gates.get("oracle_match_if_available", True)
        no_live_mutation = checked_gates.get("no_live_distributed_mutation_without_token", True)
        
        passed_court = False
        if not sequencer_group_valid or not sequencer_count_minimum_met:
            decision = "reject_consensus"
        elif not quorum_reached:
            decision = "reject_consensus"
        elif not state_hashes_valid:
            decision = "reject_consensus"
        elif not group_coherence_within_tolerance:
            decision = "quarantine_sequencer"
        elif not entanglement_stability_passed:
            decision = "quarantine_route"
        elif not route_valid_if_transfer:
            decision = "quarantine_route"
        elif not oracle_match:
            decision = "needs_more_evidence"
        elif not no_live_mutation:
            decision = "needs_more_evidence"
        else:
            metadata = extract(report, "metadata", {})
            if metadata and metadata.get("sandbox_trial", False):
                decision = "authorize_sandbox_consensus_trial"
            elif metadata and metadata.get("shadow_only", True):
                decision = "accept_shadow_consensus"
            else:
                decision = "promote_level16_candidate"
            passed_court = True
                
        return PromotionGateResult(
            decision=decision,
            gate_name=f"wavefront_consensus_court_gate_{proposal_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "errors": errors,
                "quorum_reached": quorum_reached,
                "state_hashes_valid": state_hashes_valid,
                "group_coherence_within_tolerance": group_coherence_within_tolerance,
                "entanglement_stability_passed": entanglement_stability_passed,
                "sequencer_group_valid": sequencer_group_valid,
                "sequencer_count_minimum_met": sequencer_count_minimum_met,
                "route_valid_if_transfer": route_valid_if_transfer,
                "oracle_match": oracle_match,
                "no_live_mutation": no_live_mutation
            }
        )

    def review_sequencer_sync_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a sequencer synchronization report and decides on promotion/quarantine/evidence requirements.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        coherence = extract(report, "group_coherence", 0.0)
        max_drift = extract(report, "max_drift", 1.0)
        synchronized = extract(report, "synchronized", False)
        repro_hash = extract(report, "reproducibility_hash", "none")

        passed_court = synchronized
        if not synchronized:
            if coherence < 0.60:
                decision = "quarantine_sequencer"
            else:
                decision = "needs_more_evidence"
        else:
            if max_drift > 0.05:
                decision = "needs_more_evidence"
                passed_court = False
            elif max_drift <= 0.01 and coherence >= 0.99:
                decision = "promote_level16_candidate"
            else:
                decision = "accept_shadow_consensus"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"sequencer_sync_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "group_coherence": coherence,
                "max_drift": max_drift,
                "synchronized": synchronized
            }
        )

    def review_atomic_commit_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an atomic commit report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        gate_report = extract(report, "gate_report")
        checked_gates = extract(gate_report, "checked_gates", {}) if gate_report is not None else {}
        errors = extract(gate_report, "errors", []) if gate_report is not None else []
        repro_hash = extract(report, "reproducibility_hash", "none")
        transaction = extract(report, "transaction")
        tx_id = extract(transaction, "transaction_id", "unknown_tx")
        
        parts_ok = checked_gates.get("participants_valid", True)
        snap_ok = checked_gates.get("rollback_snapshots_present", False)
        q_ok = checked_gates.get("consensus_quorum_reached", False)
        prep_ok = checked_gates.get("all_participants_prepared", False)
        route_ok = checked_gates.get("boundary_routes_valid", True)
        stab_ok = checked_gates.get("entanglement_stability_passed_if_required", True)
        val_ok = checked_gates.get("oracle_match_if_available", True)
        no_prod = checked_gates.get("no_production_commit", True)
        partial_ok = checked_gates.get("no_partial_commit_without_rollback", True)

        passed_court = False
        if not parts_ok or not no_prod or not partial_ok:
            decision = "reject_atomic_commit"
        elif not prep_ok:
            decision = "quarantine_participant"
        elif not q_ok:
            decision = "reject_atomic_commit"
        elif not route_ok or not stab_ok:
            decision = "quarantine_route"
        elif not snap_ok:
            decision = "needs_more_evidence"
        elif not val_ok:
            decision = "needs_more_evidence"
        else:
            passed_court = True
            metadata = extract(report, "metadata", {})
            if metadata is None:
                metadata = {}
            if metadata.get("sandbox_trial", False):
                decision = "authorize_sandbox_atomic_trial"
            elif metadata.get("shadow_only", True):
                decision = "accept_shadow_atomic_commit"
            else:
                decision = "promote_level17_candidate"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"atomic_commit_court_gate_{tx_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "errors": errors,
                "participants_valid": parts_ok,
                "rollback_snapshots_present": snap_ok,
                "consensus_quorum_reached": q_ok,
                "all_participants_prepared": prep_ok,
                "boundary_routes_valid": route_ok,
                "entanglement_stability_passed": stab_ok,
                "oracle_match": val_ok,
                "no_production_commit": no_prod,
                "no_partial_commit_without_rollback": partial_ok
            }
        )

    def review_atomic_rollback_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an atomic rollback report/result and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        tx_id = extract(report, "transaction_id", "unknown_tx")
        rolled_back = extract(report, "rolled_back", False)
        reason = extract(report, "reason", "none")
        repro_hash = extract(report, "reproducibility_hash", "none")
        
        rollback_result = extract(report, "rollback_result")
        if rollback_result is not None:
            rolled_back = extract(rollback_result, "rolled_back", False)
            reason = extract(rollback_result, "reason", "none")
            tx_id = extract(rollback_result, "transaction_id", "unknown_tx")
            
        passed_court = rolled_back
        if rolled_back:
            decision = "reject_atomic_commit"
        else:
            decision = "quarantine_participant"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"atomic_rollback_court_gate_{tx_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "rolled_back": rolled_back,
                "reason": reason
            }
        )

    def review_shard_topology_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a shard topology validation report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        topo = extract(report, "topology")
        passed = extract(report, "passed", False)
        repro_hash = extract(report, "reproducibility_hash", "none")
        
        shard_count = len(extract(topo, "shards", {}))
        rep_factor = extract(topo, "replication_factor", 1)
        
        passed_court = passed and (shard_count in [2, 4, 8]) and (rep_factor >= 1)
        
        if passed_court:
            decision = "accept_shadow_shard_plan"
        else:
            decision = "reject_shard_plan"
            
        return PromotionGateResult(
            decision=decision,
            gate_name="shard_topology_court_gate",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "shard_count": shard_count,
                "replication_factor": rep_factor
            }
        )

    def review_cross_shard_query_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a cross-shard query execution report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        gate_rep = extract(report, "gate_report")
        checked_gates = extract(gate_rep, "checked_gates", {}) if gate_rep is not None else {}
        repro_hash = extract(report, "reproducibility_hash", "none")
        query_plan = extract(report, "query_plan")
        query = extract(query_plan, "query")
        query_id = extract(query, "query_id", "unknown_query")
        
        passed_gates = extract(report, "passed_gates", False)
        
        # Gates verification
        topo_ok = checked_gates.get("shard_topology_valid", True)
        shard_count_ok = checked_gates.get("shard_count_supported", True)
        lane_ok = checked_gates.get("lane_to_shard_mapping_complete", True)
        plan_ok = checked_gates.get("query_plan_complete", True)
        bounded_ok = checked_gates.get("query_tree_bounded", True)
        crossings_ok = checked_gates.get("boundary_crossings_declared", True)
        local_q_ok = checked_gates.get("local_quorum_reached_if_required", True)
        global_q_ok = checked_gates.get("global_quorum_reached_if_required", True)
        prod_ok = checked_gates.get("no_production_shard_mutation", True)
        live_ok = checked_gates.get("no_live_cross_shard_execution_without_token", True)
        
        passed_court = False
        if not topo_ok or not shard_count_ok or not lane_ok or not plan_ok or not bounded_ok:
            decision = "reject_shard_plan"
        elif not prod_ok or not live_ok:
            decision = "reject_shard_plan"
        elif not local_q_ok or not global_q_ok:
            decision = "quarantine_shard"
        elif not crossings_ok:
            decision = "quarantine_route"
        elif passed_gates:
            passed_court = True
            metadata = extract(report, "metadata", {})
            if metadata is None:
                metadata = {}
            if metadata.get("sandbox_trial", False):
                decision = "authorize_sandbox_shard_trial"
            elif metadata.get("shadow_only", True):
                decision = "accept_shadow_shard_plan"
            else:
                decision = "promote_level18_candidate"
        else:
            decision = "needs_more_evidence"
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"cross_shard_query_court_gate_{query_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "passed_gates": passed_gates,
                "checked_gates": checked_gates
            }
        )

    def review_hierarchical_consensus_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews hierarchical consensus report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        passed_gates = extract(report, "passed_gates", False)
        repro_hash = extract(report, "reproducibility_hash", "none")
        proposal = extract(report, "proposal")
        prop_id = extract(proposal, "proposal_id", "unknown_proposal")
        
        global_dec = extract(report, "global_decision")
        global_q_ok = extract(global_dec, "quorum_reached", False)
        
        local_decs = extract(report, "local_decisions", {})
        local_q_ok = all(extract(dec, "quorum_reached", False) for dec in local_decs.values()) if local_decs else False
        
        passed_court = passed_gates and global_q_ok and local_q_ok
        
        if not local_q_ok:
            decision = "quarantine_shard"
        elif not global_q_ok:
            decision = "reject_shard_plan"
        elif passed_court:
            decision = "promote_level18_candidate"
        else:
            decision = "needs_more_evidence"
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"hierarchical_consensus_court_gate_{prop_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "local_quorum_passed": local_q_ok,
                "global_quorum_passed": global_q_ok
            }
        )

    def review_transaction_coordinator_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews transaction coordinator report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        tx_id = extract(report, "transaction_id", "unknown_tx")
        status = extract(report, "status", "unknown_status")
        passed_gates = extract(report, "passed_gates", False)
        repro_hash = extract(report, "reproducibility_hash", "none")
        
        prep_report = extract(report, "prepare_report")
        passed_prep = extract(prep_report, "passed", False) if prep_report else False
        
        gate_rep = extract(report, "gate_report")
        checked_gates = extract(gate_rep, "checked_gates", {}) if gate_rep else {}
        
        all_locks_granted = checked_gates.get("all_locks_granted", False)
        lock_order_ok = checked_gates.get("lock_order_valid", False)
        no_deadlock = checked_gates.get("no_deadlock_detected", False)
        snapshots_ok = checked_gates.get("rollback_snapshots_present", False)
        quorum_ok = checked_gates.get("consensus_quorum_reached_if_required", False)
        no_prod = checked_gates.get("no_production_transaction", False)
        
        passed_court = (
            passed_gates and 
            passed_prep and 
            all_locks_granted and 
            lock_order_ok and 
            no_deadlock and 
            snapshots_ok and 
            quorum_ok and 
            no_prod
        )
        
        if not no_prod:
            decision = "reject_transaction"
        elif not no_deadlock:
            decision = "abort_transaction"
        elif not all_locks_granted:
            decision = "quarantine_shard"
        elif not snapshots_ok:
            decision = "quarantine_transaction"
        elif passed_court:
            decision = "promote_level19_candidate"
        elif passed_gates:
            decision = "accept_shadow_transaction"
        else:
            decision = "needs_more_evidence"
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"transaction_coordinator_court_gate_{tx_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "passed_gates": passed_gates,
                "passed_prep": passed_prep,
                "all_locks_granted": all_locks_granted,
                "lock_order_ok": lock_order_ok,
                "no_deadlock": no_deadlock,
                "snapshots_ok": snapshots_ok,
                "quorum_ok": quorum_ok
            }
        )

    def review_shard_lock_scheduler_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews shard lock scheduler report.
        """
        import time
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "scheduler_report_id", "unknown_report")
        active_locks = extract(report, "active_locks", [])
        deadlock_rep = extract(report, "deadlock_report")
        
        deadlock_detected = extract(deadlock_rep, "deadlock_detected", False) if deadlock_rep else False
        
        lock_order_ok = True
        lock_lease_ok = True
        
        for lock in active_locks:
            expires_at = extract(lock, "expires_at", 0.0)
            if expires_at < time.time() - 3600.0:
                lock_lease_ok = False
                
        passed_court = not deadlock_detected and lock_order_ok and lock_lease_ok
        
        if deadlock_detected:
            decision = "abort_transaction"
        elif not lock_lease_ok:
            decision = "quarantine_transaction"
        elif passed_court:
            decision = "authorize_sandbox_transaction_trial"
        else:
            decision = "needs_more_evidence"
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"shard_lock_scheduler_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash="sha256_lock_sched",
            details={
                "decision": decision,
                "active_lock_count": len(active_locks),
                "deadlock_detected": deadlock_detected,
                "lock_lease_ok": lock_lease_ok
            }
        )

    def review_deadlock_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews deadlock report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        deadlock_detected = extract(report, "deadlock_detected", False)
        cycle = extract(report, "cycle", [])
        
        passed_court = not deadlock_detected
        
        if deadlock_detected:
            decision = "abort_transaction"
        elif len(cycle) > 0:
            decision = "quarantine_transaction"
        elif passed_court:
            decision = "accept_shadow_transaction"
        else:
            decision = "needs_more_evidence"
            
        return PromotionGateResult(
            decision=decision,
            gate_name="deadlock_court_gate",
            passed=passed_court,
            evidence_hash="sha256_deadlock",
            details={
                "decision": decision,
                "deadlock_detected": deadlock_detected,
                "cycle": cycle
            }
        )

    def review_graph_compaction_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews graph compaction report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed_gates = extract(report, "passed_gates", False)
        repro_hash = extract(report, "reproducibility_hash", "none")
        
        gate_rep = extract(report, "gate_report")
        checked_gates = extract(gate_rep, "checked_gates", {}) if gate_rep else {}
        
        snap_ok = checked_gates.get("graph_snapshot_valid", False)
        roots_ok = checked_gates.get("reachability_roots_declared", False)
        remap_ok = checked_gates.get("remap_table_complete", False)
        no_prod = checked_gates.get("no_live_gc_without_token", True)
        
        passed_court = passed_gates and snap_ok and roots_ok and remap_ok and no_prod
        
        if not snap_ok:
            decision = "reject_gc"
        elif not remap_ok:
            decision = "quarantine_gc_candidate"
        elif passed_court:
            decision = "promote_level20_candidate"
        elif passed_gates:
            decision = "accept_shadow_gc"
        else:
            decision = "needs_more_evidence"
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"graph_compaction_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "passed_gates": passed_gates,
                "snapshot_valid": snap_ok,
                "remap_complete": remap_ok
            }
        )

    def review_gc_collection_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews GC collection report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed_gates = extract(report, "passed_gates", False)
        
        plan = extract(report, "plan")
        tombstones = extract(plan, "tombstones", [])
        tombstones_present = len(tombstones) > 0
        
        from sol_manifold_gc import no_active_transaction_references
        no_refs = True
        if plan:
            for n_id in extract(plan, "nodes_to_collect", []):
                if not no_active_transaction_references(n_id):
                    no_refs = False
                    
        passed_court = passed_gates and tombstones_present and no_refs
        
        if not no_refs:
            decision = "reject_gc"
        elif not tombstones_present:
            decision = "quarantine_gc_candidate"
        elif passed_court:
            decision = "promote_level20_candidate"
        elif passed_gates:
            decision = "authorize_sandbox_gc_trial"
        else:
            decision = "needs_more_evidence"
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"gc_collection_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash="sha256_gc_collection",
            details={
                "decision": decision,
                "tombstones_created": len(extract(report, "tombstones_created", [])),
                "no_active_references": no_refs
            }
        )

    def review_sequence_lifecycle_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews sequence lifecycle compaction report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed_gates = extract(report, "passed_gates", False)
        repro_hash = extract(report, "reproducibility_hash", "none")
        
        passed_court = passed_gates
        
        if passed_court:
            decision = "accept_shadow_gc"
        else:
            decision = "needs_more_evidence"
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"sequence_lifecycle_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "compacted_sequence_count": len(extract(report, "compacted_sequence_ids", []))
            }
        )

    def review_wavefront_propagation_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a wavefront propagation report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed_gates = extract(report, "passed_gates", False)
        stable = extract(report, "stable", False)
        repro_hash = extract(report, "reproducibility_hash", "none")
        
        gate_rep = extract(report, "gate_report")
        checked_gates = extract(gate_rep, "checked_gates", {}) if gate_rep else {}
        
        graph_ok = checked_gates.get("graph_arrays_valid", False)
        state_ok = checked_gates.get("wavefront_state_valid", False)
        energy_ok = checked_gates.get("energy_non_negative", False)
        stable_ok = checked_gates.get("propagation_stable", False)
        shadow_ok = checked_gates.get("shadow_mode_required_by_default", True)
        live_blocked = checked_gates.get("no_live_stepper_replacement_without_promotion", True)
        
        passed_court = passed_gates and stable and graph_ok and state_ok and energy_ok and stable_ok and shadow_ok and live_blocked
        
        if not graph_ok or not state_ok:
            decision = "reject_wavefront"
        elif not energy_ok:
            decision = "reject_wavefront"
        elif not live_blocked:
            decision = "quarantine_boundary"
        elif not stable_ok or not stable:
            decision = "needs_more_evidence"
        elif passed_court:
            metadata = extract(report, "metadata", {})
            if metadata.get("sandbox_trial", False):
                decision = "authorize_sandbox_wavefront_trial"
            elif metadata.get("shadow_only", True):
                decision = "accept_shadow_wavefront"
            else:
                decision = "promote_level21_candidate"
        else:
            decision = "needs_more_evidence"
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"wavefront_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "passed_gates": passed_gates,
                "stable": stable,
                "graph_ok": graph_ok,
                "state_ok": state_ok,
                "energy_ok": energy_ok,
                "stable_ok": stable_ok
            }
        )

    def review_pml_absorption_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a PML absorption report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed_gates = extract(report, "passed_gates", False)
        repro_hash = "sha256_pml_review"
        
        reflection_score = extract(report, "reflection_score", 1.0)
        pml_cells = extract(report, "pml_cells", 0)
        
        passed_court = passed_gates and reflection_score <= 0.15 and pml_cells > 0
        
        if reflection_score > 0.40:
            decision = "reject_wavefront"
        elif reflection_score > 0.25:
            decision = "quarantine_boundary"
        elif reflection_score > 0.15:
            decision = "needs_more_evidence"
        elif passed_court:
            decision = "promote_level21_candidate"
        else:
            decision = "needs_more_evidence"
            
        return PromotionGateResult(
            decision=decision,
            gate_name=f"pml_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "passed_gates": passed_gates,
                "reflection_score": reflection_score,
                "pml_cells": pml_cells
            }
        )

    def review_multisequencer_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a multi-sequencer parallel execution report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed_gates = extract(report, "passed_gates", False)
        repro_hash = extract(report, "reproducibility_hash", "none")
        if not repro_hash or repro_hash == "none":
            meta = extract(report, "metadata", {})
            repro_hash = extract(meta, "reproducibility_hash", "none")

        # Extract gate report details
        gate_rep = extract(report, "metadata", {}).get("gate_report")
        checked_gates = extract(gate_rep, "checked_gates", {}) if gate_rep else {}

        cg_valid = checked_gates.get("core_group_valid", False)
        cc_supported = checked_gates.get("core_count_supported", False)
        fabric_assigned = checked_gates.get("lane_fabric_assigned_per_core", False)
        consensus_ok = checked_gates.get("consensus_quorum_reached_if_required", False)

        passed_court = passed_gates and cg_valid and cc_supported and fabric_assigned and consensus_ok

        if not cg_valid:
            decision = "reject_tensor_flow"
        elif not fabric_assigned:
            decision = "quarantine_core"
        elif not cc_supported:
            decision = "reject_tensor_flow"
        elif not consensus_ok:
            decision = "needs_more_evidence"
        elif passed_court:
            decision = "promote_level22_candidate"
        else:
            decision = "needs_more_evidence"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"multisequencer_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "passed_gates": passed_gates,
                "core_group_valid": cg_valid,
                "core_count_supported": cc_supported,
                "lane_fabric_assigned": fabric_assigned,
                "consensus_quorum": consensus_ok
            }
        )

    def review_tensor_flow_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a tensor flow execution report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed_gates = extract(report, "passed_gates", False)
        repro_hash = extract(report, "reproducibility_hash", "none")
        if not repro_hash or repro_hash == "none":
            meta = extract(report, "metadata", {})
            repro_hash = extract(meta, "reproducibility_hash", "none")

        meta = extract(report, "metadata", {})
        oracle_match = extract(meta, "oracle_match", False)

        gate_rep = meta.get("gate_report")
        checked_gates = extract(gate_rep, "checked_gates", {}) if gate_rep else {}

        cg_valid = checked_gates.get("core_group_valid", False)
        cc_supported = checked_gates.get("core_count_supported", False)
        fabric_assigned = checked_gates.get("lane_fabric_assigned_per_core", False)
        shape_valid = checked_gates.get("tensor_shape_valid", False)
        shards_complete = checked_gates.get("tensor_shards_complete", False)
        mapping_complete = checked_gates.get("shard_to_core_mapping_complete", False)
        tree_ok = checked_gates.get("reduction_tree_complete_if_required", True)
        consensus_ok = checked_gates.get("consensus_quorum_reached_if_required", False)

        passed_court = (
            passed_gates and cg_valid and cc_supported and fabric_assigned and
            shape_valid and shards_complete and mapping_complete and tree_ok and consensus_ok and oracle_match
        )

        if not cg_valid or not cc_supported:
            decision = "reject_tensor_flow"
        elif not fabric_assigned:
            decision = "quarantine_core"
        elif not shards_complete or not mapping_complete:
            decision = "quarantine_tensor_shard"
        elif not tree_ok:
            decision = "quarantine_tensor_shard"
        elif not oracle_match:
            decision = "reject_tensor_flow"
        elif passed_court:
            is_sandbox_trial = meta.get("sandbox_trial", False)
            if is_sandbox_trial:
                decision = "authorize_sandbox_tensor_trial"
            elif meta.get("shadow_only", True):
                decision = "accept_shadow_tensor_flow"
            else:
                decision = "promote_level22_candidate"
        else:
            decision = "needs_more_evidence"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"tensor_flow_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "passed_gates": passed_gates,
                "oracle_match": oracle_match,
                "core_group_valid": cg_valid,
                "tensor_shards_complete": shards_complete,
                "reduction_tree_valid": tree_ok,
                "consensus_quorum": consensus_ok
            }
        )

    def review_pipeline_execution_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a pipeline execution report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed_gates = extract(report, "passed_gates", False)
        repro_hash = extract(report, "reproducibility_hash", "none")
        if not repro_hash or repro_hash == "none":
            meta = extract(report, "metadata", {})
            repro_hash = extract(meta, "reproducibility_hash", "none")

        meta = extract(report, "metadata", {})
        oracle_match = extract(meta, "oracle_match", True)

        gate_rep = extract(report, "gate_report")
        checked_gates = extract(gate_rep, "checked_gates", {}) if gate_rep else {}

        cg_valid = checked_gates.get("core_group_valid", False)
        dag_valid = checked_gates.get("pipeline_dag_valid", False)
        no_unresolved = checked_gates.get("no_unresolved_dependencies", False)
        assignment_complete = checked_gates.get("task_assignment_complete", False)
        reductions_ok = checked_gates.get("reductions_have_join_points", True)
        oracle_match_gate = checked_gates.get("oracle_match_if_available", True)

        passed_court = (
            passed_gates and cg_valid and dag_valid and no_unresolved and
            assignment_complete and reductions_ok and oracle_match_gate and oracle_match
        )

        if not dag_valid:
            decision = "reject_pipeline"
        elif not cg_valid:
            decision = "quarantine_core"
        elif not assignment_complete:
            decision = "quarantine_task"
        elif not no_unresolved:
            decision = "needs_more_evidence"
        elif passed_court:
            is_sandbox_trial = meta.get("sandbox_trial", False)
            if is_sandbox_trial:
                decision = "authorize_sandbox_pipeline_trial"
            elif meta.get("shadow_only", True):
                decision = "accept_shadow_pipeline"
            else:
                decision = "promote_level23_candidate"
        else:
            decision = "needs_more_evidence"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"pipeline_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "passed_gates": passed_gates,
                "oracle_match": oracle_match,
                "core_group_valid": cg_valid,
                "pipeline_dag_valid": dag_valid,
                "task_assignment_complete": assignment_complete,
                "no_unresolved_dependencies": no_unresolved
            }
        )

    def review_pipeline_stall_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a pipeline stall report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        stalled_tasks = extract(report, "stalled_tasks", [])
        stall_duration = extract(report, "stall_duration", 0.0)
        hazard_waiting_metrics = extract(report, "hazard_waiting_metrics", {})
        meta = extract(report, "metadata", {})
        
        repro_hash = extract(meta, "reproducibility_hash", "none")
        if repro_hash == "none":
            repro_hash = f"stall_hash_{len(stalled_tasks)}"

        raw_waits = hazard_waiting_metrics.get("read_after_write", 0)
        reduction_waits = hazard_waiting_metrics.get("cross_core_reduction_wait", 0)
        consensus_waits = hazard_waiting_metrics.get("consensus_wait", 0)
        lock_waits = hazard_waiting_metrics.get("shard_lock_wait", 0)

        if consensus_waits > 0 or lock_waits > 10:
            decision = "quarantine_core"
            passed = False
        elif raw_waits > 0 or reduction_waits > 0:
            decision = "quarantine_task"
            passed = False
        elif len(stalled_tasks) > 0:
            decision = "needs_more_evidence"
            passed = False
        else:
            decision = "accept_shadow_pipeline"
            passed = True

        return PromotionGateResult(
            decision=decision,
            gate_name=f"pipeline_stall_court_gate_{len(stalled_tasks)}",
            passed=passed,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "stalled_tasks_count": len(stalled_tasks),
                "stall_duration": stall_duration,
                "hazard_waiting_metrics": hazard_waiting_metrics
            }
        )

    def review_pipeline_optimization_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a pipeline optimization report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "optimization_report_id", "unknown_report")
        passed_gates = extract(report, "passed_gates", False)
        
        comparison = extract(report, "performance_comparison", {})
        improvement = comparison.get("speedup", 0.0) if isinstance(comparison, dict) else 0.0
        
        result = extract(report, "result")
        success = extract(result, "success", False) if result else False
        
        repro_hash = "none"
        oracle_match = True
        is_sandbox_trial = False
        shadow_only = True
        
        if result:
            opt_rep = extract(result, "optimized_report")
            if opt_rep:
                repro_hash = extract(opt_rep, "reproducibility_hash", "none")
                meta = extract(opt_rep, "metadata", {})
                oracle_match = meta.get("oracle_match", True)
                is_sandbox_trial = meta.get("sandbox_trial", False)
                shadow_only = meta.get("shadow_only", True)

        passed_court = passed_gates and success and oracle_match
        
        if not passed_gates:
            decision = "reject_optimization"
        elif not oracle_match:
            decision = "needs_more_evidence"
        elif passed_court:
            if is_sandbox_trial:
                decision = "authorize_sandbox_optimization_trial"
            elif shadow_only:
                decision = "accept_shadow_optimization"
            else:
                decision = "promote_level24_candidate"
        else:
            decision = "needs_more_evidence"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"pipeline_optimization_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "passed_gates": passed_gates,
                "success": success,
                "oracle_match": oracle_match,
                "improvement": improvement
            }
        )

    def review_bypass_execution_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a lock-free bypass execution report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed_gates = extract(report, "passed_gates", False)
        
        applied_routes = extract(report, "bypass_routes_applied", [])
        
        safe_bypass = True
        for r in applied_routes:
            reason = extract(r, "reason", "").lower()
            if "consensus" in reason or "write" in reason:
                safe_bypass = False
                
        repro_hash = f"bypass_hash_{len(applied_routes)}"
        
        passed_court = passed_gates and safe_bypass
        
        if not passed_gates:
            decision = "reject_optimization"
        elif not safe_bypass:
            decision = "quarantine_bypass_route"
        elif passed_court:
            decision = "accept_shadow_optimization"
        else:
            decision = "needs_more_evidence"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"bypass_court_gate_{report_id}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "passed_gates": passed_gates,
                "safe_bypass": safe_bypass,
                "applied_routes_count": len(applied_routes)
            }
        )

    def review_lock_boundary_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a cross-core lock boundary reduction report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        boundaries = extract(report, "boundaries", [])
        opts = extract(report, "optimizations", [])
        is_safe = extract(report, "is_safe", True)
        
        no_weakened_locks = True
        for opt in opts:
            if extract(opt, "reducible"):
                target_id = extract(opt, "target_boundary_id")
                boundary = None
                for b in boundaries:
                    if extract(b, "boundary_id") == target_id:
                        boundary = b
                        break
                if boundary and extract(boundary, "lock_mode") == "exclusive":
                    no_weakened_locks = False

        passed_court = is_safe and no_weakened_locks
        repro_hash = f"lock_boundary_hash_{len(boundaries)}"
        
        if not no_weakened_locks:
            decision = "quarantine_core_boundary"
        elif not is_safe:
            decision = "reject_optimization"
        elif passed_court:
            decision = "accept_shadow_optimization"
        else:
            decision = "needs_more_evidence"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"lock_boundary_court_gate_{len(boundaries)}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "boundaries_count": len(boundaries),
                "optimizations_count": len(opts),
                "no_weakened_locks": no_weakened_locks
            }
        )

    def review_rebalance_plan(self, plan: Any) -> PromotionGateResult:
        """
        Reviews a rebalance plan's candidates and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        candidates = extract(plan, "candidates", []) or []
        policy = extract(plan, "policy")
        
        # Check constraints
        passed = True
        decision = "accept_shadow_rebalance"
        repro_hash = extract(plan, "plan_id", "none")
        errors = []

        max_moves = 3
        if policy is not None:
            max_moves = extract(policy, "max_moves_per_plan", 3)

        if len(candidates) > max_moves:
            passed = False
            decision = "reject_rebalance"
            errors.append(f"Move count {len(candidates)} exceeds policy limit of {max_moves}.")

        for cand in candidates:
            meta = extract(cand, "metadata", {}) or {}
            if meta.get("transaction_active") or meta.get("exclusive_lock_held"):
                passed = False
                decision = "quarantine_move"
                errors.append(f"Candidate {extract(cand, 'candidate_id')} violates locks or transactions.")
                
            if meta.get("quarantined"):
                passed = False
                decision = "quarantine_shard"
                errors.append(f"Candidate contains quarantined shard {extract(cand, 'item_id')}.")

        if not passed and decision == "accept_shadow_rebalance":
            decision = "reject_rebalance"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"rebalance_plan_court_gate_{repro_hash}",
            passed=passed,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "candidates_count": len(candidates),
                "errors": errors
            }
        )

    def review_rebalance_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a rebalance report and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        result = extract(report, "result")
        passed_gates = extract(report, "passed_gates", False)
        before_cost = extract(report, "before_cost", 0.0)
        after_cost = extract(report, "after_cost", 0.0)
        repro_hash = extract(report, "report_id", "none")
        errors = []

        if result is None:
            return PromotionGateResult(
                decision="needs_more_evidence",
                gate_name=f"rebalance_report_court_gate_{repro_hash}",
                passed=False,
                evidence_hash=repro_hash,
                details={"errors": ["Missing rebalance result"]}
            )

        # Verification rules:
        # 1. Valid before/after topology
        original_topo = extract(result, "original_topology")
        rebalanced_topo = extract(result, "rebalanced_topology")
        topo_ok = original_topo is not None and rebalanced_topo is not None

        # 2. Metrics-backed move justification (cost improvement or no moves needed)
        improvement = before_cost - after_cost
        policy = extract(result, "policy")
        min_improvement = 0.05
        if policy:
            min_improvement = extract(policy, "min_improvement_threshold", 0.05)
            
        justified = True
        moves_applied = extract(result, "moves_applied", [])
        if len(moves_applied) > 0 and improvement < min_improvement:
            justified = False
            errors.append(f"Improvement {improvement:.4f} is below policy threshold {min_improvement:.4f}.")

        # 3. Preservation checks
        meta = extract(report, "metadata", {}) or {}
        res_meta = extract(result, "metadata", {}) or {}
        meta.update(res_meta)
        
        lock_ok = meta.get("locks_preserved", passed_gates)
        tx_ok = meta.get("transactions_preserved", passed_gates)
        rollback_ok = meta.get("rollback_preserved", passed_gates)
        consensus_ok = meta.get("consensus_preserved", passed_gates)

        # Look for submitted ranger evidence packet if available
        ranger_ok = True
        has_ranger_evidence = False
        for p in self.submitted_packets:
            if p.domain == "sol_sovereign" and p.level == 25 and p.actor_type == "ranger":
                has_ranger_evidence = True
                if p.recommendation == "reject":
                    ranger_ok = False
                
        # If we have a ranger packet submitted, require it to be positive
        if has_ranger_evidence and not ranger_ok:
            passed_gates = False
            errors.append("Ranger evidence packet indicates violation or recommendation is reject.")

        passed_court = topo_ok and lock_ok and tx_ok and rollback_ok and consensus_ok and justified and passed_gates
        
        if passed_court:
            # If everything is solid and sandbox rebalance trial is requested or allowed
            if meta.get("sandbox_trial", False) or meta.get("sandbox_token_present", False):
                decision = "authorize_sandbox_rebalance_trial"
            else:
                decision = "promote_level25_candidate"
        else:
            if not topo_ok:
                decision = "needs_more_evidence"
                errors.append("Before/after topology references are missing.")
            elif not lock_ok:
                decision = "quarantine_move"
                errors.append("Exclusive lock held or lock ordering violated.")
            elif not tx_ok:
                decision = "reject_rebalance"
                errors.append("Moved participant in active prepare/commit.")
            elif not justified:
                decision = "needs_more_evidence"
            else:
                decision = "reject_rebalance"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"rebalance_report_court_gate_{repro_hash}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "topo_ok": topo_ok,
                "lock_ok": lock_ok,
                "tx_ok": tx_ok,
                "rollback_ok": rollback_ok,
                "consensus_ok": consensus_ok,
                "justified": justified,
                "errors": errors
            }
        )

    def review_placement_map(self, placement_map: Any) -> PromotionGateResult:
        """
        Reviews a placement map's integrity.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        repro_hash = extract(placement_map, "placement_id", "none")
        manifold_to_core = extract(placement_map, "manifold_to_core", {}) or {}
        shard_to_core = extract(placement_map, "shard_to_core", {}) or {}
        
        complete = len(manifold_to_core) > 0 or len(shard_to_core) > 0
        passed = complete
        decision = "accept_shadow_rebalance" if complete else "needs_more_evidence"
        
        return PromotionGateResult(
            decision=decision,
            gate_name=f"placement_map_court_gate_{repro_hash}",
            passed=passed,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "manifold_placements_count": len(manifold_to_core),
                "shard_placements_count": len(shard_to_core),
                "complete": complete
            }
        )

    def review_sandbox_relocation_plan(self, plan: Any) -> PromotionGateResult:
        """
        Reviews a sandbox relocation plan.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        repro_hash = extract(plan, "plan_id", "none")
        req = extract(plan, "request")
        steps = extract(plan, "steps", [])
        
        passed = req is not None and len(steps) > 0
        decision = "accept_sandbox_relocation_plan" if passed else "needs_more_evidence"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"sandbox_relocation_plan_court_gate_{repro_hash}",
            passed=passed,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "steps_count": len(steps),
                "request_present": req is not None
            }
        )

    def review_sandbox_relocation_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a sandbox relocation report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        repro_hash = extract(report, "report_id", "none")
        result = extract(report, "result")
        passed_gates = extract(report, "passed_gates", False)

        errors = []
        if result is None:
            return PromotionGateResult(
                decision="needs_more_evidence",
                gate_name=f"sandbox_relocation_report_court_gate_{repro_hash}",
                passed=False,
                evidence_hash=repro_hash,
                details={"errors": ["Missing relocation result"]}
            )

        success = extract(result, "success", False)
        rolled_back = extract(result, "rolled_back", False)

        passed = success and passed_gates and not rolled_back
        if rolled_back:
            decision = "rollback_relocation"
            errors.append(extract(result, "rollback_reason", "Rolled back"))
        elif not success:
            decision = "reject_relocation_trial"
            errors.append("Relocation failed safety gates or step execution.")
        else:
            decision = "accept_sandbox_relocation_trial"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"sandbox_relocation_report_court_gate_{repro_hash}",
            passed=passed,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "success": success,
                "rolled_back": rolled_back,
                "errors": errors
            }
        )

    def review_pdm_relocation_stability_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a PDM relocation stability report.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        is_stable = extract(report, "is_stable", False)
        breaches = extract(report, "breaches", [])
        repro_hash = f"RPT_STABILITY_{id(report)}"

        passed = is_stable and len(breaches) == 0
        if not passed:
            decision = "rollback_relocation"
        else:
            decision = "accept_sandbox_relocation_trial"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"pdm_relocation_stability_court_gate",
            passed=passed,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "is_stable": is_stable,
                "breaches_count": len(breaches),
                "breaches": breaches
            }
        )

    def review_relocation_trial_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a relocation trial report to check for Level 26 promotion.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        repro_hash = extract(report, "report_id", "none")
        trial_state = extract(report, "trial_state")
        decision_obj = extract(report, "decision")
        passed_gates = extract(report, "passed_gates", False)
        
        errors = []
        if trial_state is None or decision_obj is None:
            return PromotionGateResult(
                decision="needs_more_evidence",
                gate_name=f"relocation_trial_court_gate_{repro_hash}",
                passed=False,
                evidence_hash=repro_hash,
                details={"errors": ["Missing trial state or decision"]}
            )

        trial_decision = extract(decision_obj, "decision", "none")
        trial_status = extract(trial_state, "status", "pending")

        # Extract tokens and validations
        plan = extract(trial_state, "plan")
        req = extract(plan, "request") if plan is not None else None
        token = extract(req, "token") if req is not None else None
        snapshot = extract(trial_state, "snapshot")
        baseline = extract(trial_state, "baseline")
        telemetry_loop = extract(trial_state, "telemetry_loop")
        
        # Check token and other promotion requirements
        # 1. Valid sandbox token
        from sol_live_relocation import validate_live_relocation_token
        token_valid = token is not None and validate_live_relocation_token(token)
        if not token_valid:
            errors.append("Invalid or missing live relocation token.")

        # 2. Successful rollback snapshot capture
        snapshot_captured = snapshot is not None
        if not snapshot_captured:
            errors.append("Rollback snapshot was not successfully captured.")

        # 3. Successful PDM baseline capture
        baseline_captured = baseline is not None
        if not baseline_captured:
            errors.append("PDM baseline was not successfully captured.")

        # 4. Stable telemetry loop
        stable_loop = True
        if telemetry_loop is not None:
            frames = extract(telemetry_loop, "frames", [])
            for frame in frames:
                drift = extract(frame, "phase_drift", 0.0)
                crosstalk = extract(frame, "crosstalk", 0.0)
                reflection = extract(frame, "boundary_reflection", 0.0)
                mass = extract(frame, "active_mass", 500.0)
                if drift > 0.05 or crosstalk > 0.05 or reflection > 0.05 or mass < 14.0:
                    stable_loop = False
                    errors.append(f"Unstable telemetry frame: drift={drift}, crosstalk={crosstalk}, reflection={reflection}, mass={mass}")

        # 5. No production/default mutation
        no_production_mutation = token_valid and extract(token, "sandbox_scope", False)
        if not no_production_mutation:
            errors.append("Production scope is strictly prohibited for relocation trials.")

        # 6. All relocation gates passed
        all_gates_passed = passed_gates and trial_decision == "accept"
        if not all_gates_passed:
            errors.append(f"Relocation gates or trial decision failed: {trial_decision}")

        # 7. Valid ranger evidence packet presence
        ranger_ok = True
        has_ranger_evidence = False
        for p in self.submitted_packets:
            if p.domain == "sol_sovereign" and p.level == 26 and p.actor_type == "ranger":
                has_ranger_evidence = True
                if p.recommendation == "reject" or not p.evidence.get("token_validity", False):
                    ranger_ok = False
                    errors.append("Ranger evidence packet indicates invalid token or rejected recommendation.")

        # 8. Rollback proven or not needed
        rollback_proven = snapshot_captured

        passed_court = (
            token_valid and
            snapshot_captured and
            baseline_captured and
            stable_loop and
            no_production_mutation and
            all_gates_passed and
            ranger_ok and
            rollback_proven
        )

        if passed_court:
            decision = "promote_level26_candidate"
        else:
            if trial_decision == "rollback":
                decision = "rollback_relocation"
            elif trial_decision == "quarantine":
                decision = "quarantine_relocation_route"
            elif not token_valid or not no_production_mutation:
                decision = "reject_relocation_trial"
            elif not stable_loop:
                decision = "quarantine_manifold"
            else:
                decision = "needs_more_evidence"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"relocation_trial_court_gate_{repro_hash}",
            passed=passed_court,
            evidence_hash=repro_hash,
            details={
                "decision": decision,
                "token_valid": token_valid,
                "snapshot_captured": snapshot_captured,
                "baseline_captured": baseline_captured,
                "stable_loop": stable_loop,
                "no_production_mutation": no_production_mutation,
                "all_gates_passed": all_gates_passed,
                "ranger_ok": ranger_ok,
                "rollback_proven": rollback_proven,
                "errors": errors
            }
        )

    def review_multimanifold_coordination_plan(self, plan: Any) -> PromotionGateResult:
        """
        Reviews a MultiManifoldCoordinationPlan and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        plan_id = extract(plan, "plan_id", "unknown_plan")
        metadata = extract(plan, "metadata", {}) or {}
        
        passed = True
        decision = "accept_shadow_multimanifold_coordination"
        errors = []

        if metadata.get("group_invalid", False):
            passed = False
            decision = "reject_coordination_plan"
            errors.append("Invalid coordination group configuration.")
        elif metadata.get("missing_manifold_registration", False):
            passed = False
            decision = "needs_more_evidence"
            errors.append("Missing manifold registration.")

        return PromotionGateResult(
            decision=decision,
            gate_name=f"multimanifold_coordination_plan_gate_{plan_id}",
            passed=passed,
            evidence_hash=extract(plan, "plan_id", "hash"),
            details={"errors": errors}
        )

    def review_global_lock_boundary_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a GlobalLockBoundaryReport and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        valid = extract(report, "valid", True)
        conflict = extract(report, "conflict_detected", False)
        deadlock = extract(report, "deadlock_detected", False)

        passed = valid and not conflict and not deadlock
        errors = extract(report, "errors", []) or []

        if deadlock:
            decision = "quarantine_route"
        elif conflict:
            decision = "hold_coordination_epoch"
        elif not valid:
            decision = "reject_coordination_plan"
        else:
            decision = "accept_shadow_lock_boundaries"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"global_lock_boundary_gate_{report_id}",
            passed=passed,
            evidence_hash=report_id,
            details={"deadlock": deadlock, "conflict": conflict, "valid": valid, "errors": errors}
        )

    def review_wavefront_alignment_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a WavefrontAlignmentReport and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        stable = extract(report, "stable", True)
        skew = extract(report, "global_phase_skew", 0.0)
        crosstalk = extract(report, "global_crosstalk", 0.0)
        reflection = extract(report, "global_boundary_reflection", 0.0)

        passed = stable
        errors = []

        if skew > 0.10:
            decision = "quarantine_manifold"
            errors.append("Critical global phase skew threshold exceeded.")
        elif crosstalk > 0.10:
            decision = "quarantine_route"
            errors.append("Critical global crosstalk threshold exceeded.")
        elif reflection > 0.05:
            decision = "hold_coordination_epoch"
            errors.append("Boundary reflection threshold exceeded.")
        elif not stable:
            decision = "needs_more_evidence"
            errors.append("Wavefront alignment is unstable.")
        else:
            decision = "accept_wavefront_alignment"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"wavefront_alignment_gate_{report_id}",
            passed=passed,
            evidence_hash=report_id,
            details={"stable": stable, "global_phase_skew": skew, "global_crosstalk": crosstalk, "global_boundary_reflection": reflection, "errors": errors}
        )

    def review_epoch_synchronization_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an EpochSynchronizationReport and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        status = extract(report, "status", "active")
        barrier_satisfied = extract(report, "barrier_satisfied", False)
        consensus = extract(report, "consensus_decision")

        passed = barrier_satisfied and status == "committed"
        if consensus:
            passed = passed and (extract(consensus, "quorum_reached", False) or extract(consensus, "passed", False))

        errors = []
        if status == "aborted":
            decision = "rollback_coordination_epoch"
            errors.append("Epoch aborted.")
        elif not barrier_satisfied:
            decision = "hold_coordination_epoch"
            errors.append("Epoch barrier not satisfied.")
        elif consensus and not (extract(consensus, "quorum_reached", False) or extract(consensus, "passed", False)):
            decision = "needs_more_evidence"
            errors.append("Consensus quorum not reached.")
        else:
            decision = "accept_epoch_synchronization"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"epoch_synchronization_gate_{report_id}",
            passed=passed,
            evidence_hash=report_id,
            details={"status": status, "barrier_satisfied": barrier_satisfied, "consensus": consensus, "errors": errors}
        )

    def review_multimanifold_coordination_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a MultiManifoldCoordinationReport and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        result = extract(report, "result")
        passed_gates = extract(report, "passed_gates", True)
        checked_gates = extract(report, "checked_gates", {}) or {}
        
        errors = []
        
        # 1. Valid coordination group
        group_ok = checked_gates.get("coordination_group_valid", True)
        if not group_ok:
            errors.append("Coordination group is invalid.")
            
        # 2. Satisfied epoch barrier
        epoch_ok = checked_gates.get("epoch_barrier_satisfied", True)
        if not epoch_ok:
            errors.append("Epoch barrier is not satisfied.")
            
        # 3. Global lock boundaries valid
        lock_ok = checked_gates.get("global_lock_boundaries_valid", True)
        if not lock_ok:
            errors.append("Global lock boundaries are invalid.")
            
        # 4. No cross-manifold deadlock
        no_deadlock = checked_gates.get("no_cross_manifold_deadlock", True)
        if not no_deadlock:
            errors.append("Cross-manifold deadlock detected.")
            
        # 5. Wavefront alignment measured and stable
        wavefront_ok = checked_gates.get("wavefront_alignment_measured", True) and not checked_gates.get("high_skew_detected", False)
        if not wavefront_ok:
            errors.append("Wavefront alignment is unstable or unmeasured.")
            
        # 6. Multi-manifold quorum reached
        quorum_ok = checked_gates.get("multimanifold_quorum_reached", True)
        if not quorum_ok:
            errors.append("Consensus quorum not reached.")
            
        # 7. Rollback snapshots for all participants
        rollback_ok = checked_gates.get("rollback_snapshots_present_for_all_manifolds", True)
        if not rollback_ok:
            errors.append("Rollback snapshots are missing for some manifolds.")
            
        # 8. No uncontrolled live mutation
        no_production = not checked_gates.get("production_coordination_mutation", False)
        if not no_production:
            errors.append("Production live coordination mutation detected.")

        # 9. Valid ranger evidence packet
        has_ranger_evidence = False
        ranger_ok = True
        for p in self.submitted_packets:
            if p.domain == "sol_sovereign" and p.level == 27 and p.actor_type == "ranger":
                has_ranger_evidence = True
                p_ev = extract(p, "evidence", {}) or {}
                if extract(p, "recommendation") == "reject" or not p_ev.get("token_validity", False):
                    ranger_ok = False
                    errors.append("Ranger evidence indicates invalid token or rejected sync.")

        meta = extract(report, "metadata", {}) or {}
        if not has_ranger_evidence and not meta.get("skip_ranger_check"):
            ranger_ok = False
            errors.append("Missing required Level 27 ranger evidence packet.")

        passed_court = (
            passed_gates and
            group_ok and
            epoch_ok and
            lock_ok and
            no_deadlock and
            wavefront_ok and
            quorum_ok and
            rollback_ok and
            no_production and
            ranger_ok
        )

        if passed_court:
            decision = "promote_level27_candidate"
        else:
            if not no_production:
                decision = "reject_coordination_plan"
            elif not no_deadlock:
                decision = "quarantine_route"
            elif not wavefront_ok:
                decision = "quarantine_manifold"
            elif not epoch_ok:
                decision = "hold_coordination_epoch"
            else:
                decision = "needs_more_evidence"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"multimanifold_coordination_report_gate_{report_id}",
            passed=passed_court,
            evidence_hash=report_id,
            details={
                "decision": decision,
                "passed_court": passed_court,
                "errors": errors,
                "group_ok": group_ok,
                "epoch_ok": epoch_ok,
                "lock_ok": lock_ok,
                "no_deadlock": no_deadlock,
                "wavefront_ok": wavefront_ok,
                "quorum_ok": quorum_ok,
                "rollback_ok": rollback_ok,
                "no_production": no_production,
                "ranger_ok": ranger_ok
            }
        )

    def review_transaction_consensus_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a TransactionConsensusReport and decides on transaction propagation consensus validity.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed = extract(report, "passed_gates", True)
        decision = extract(report, "decision")
        agreed = extract(decision, "agreed", True)
        status = extract(decision, "status", "committed")

        if status == "aborted":
            court_decision = "abort_transaction_epoch"
        elif not agreed:
            court_decision = "needs_more_evidence"
        elif not passed:
            court_decision = "reject_transaction_propagation"
        else:
            court_decision = "accept_shadow_transaction_propagation"

        return PromotionGateResult(
            decision=court_decision,
            gate_name=f"transaction_consensus_gate_{report_id}",
            passed=passed and agreed,
            evidence_hash=report_id,
            details={"status": status, "agreed": agreed}
        )

    def review_geodesic_propagation_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a GeodesicPropagationReport and decides on geodesic update propagation validity.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed = extract(report, "passed_gates", True)
        result = extract(report, "result")
        success = extract(result, "success", True)
        max_drift = extract(result, "max_phase_drift", 0.0)

        if not success:
            court_decision = "reject_transaction_propagation"
        elif max_drift > 0.10:
            court_decision = "quarantine_manifold"
        elif max_drift > 0.05:
            court_decision = "hold_transaction_epoch"
        else:
            court_decision = "accept_shadow_transaction_propagation"

        return PromotionGateResult(
            decision=court_decision,
            gate_name=f"geodesic_propagation_gate_{report_id}",
            passed=passed and success,
            evidence_hash=report_id,
            details={"success": success, "max_phase_drift": max_drift}
        )

    def review_wavefront_transaction_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a WavefrontTransactionReport and decides on commit barrier fulfillment.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed = extract(report, "passed_gates", True)
        result = extract(report, "result")
        success = extract(result, "success", True)
        rolled_back = extract(result, "rolled_back", False)

        if rolled_back:
            court_decision = "rollback_transaction_epoch"
        elif not success:
            court_decision = "abort_transaction_epoch"
        else:
            court_decision = "accept_shadow_transaction_propagation"

        return PromotionGateResult(
            decision=court_decision,
            gate_name=f"wavefront_transaction_gate_{report_id}",
            passed=passed and success,
            evidence_hash=report_id,
            details={"success": success, "rolled_back": rolled_back}
        )

    def review_transaction_propagation_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a TransactionPropagationRanger SovereignPacket for promotion voting.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        packet_id = extract(packet, "packet_id", "unknown_packet")
        evidence = extract(packet, "evidence", {}) or {}
        passed = extract(packet, "recommendation") == "promote"
        errors = []

        local_q = evidence.get("local_quorum_status") == "passed"
        global_q = evidence.get("global_quorum_status") == "passed"
        geo_valid = evidence.get("geodesic_path_status") == "valid"
        lock_valid = evidence.get("lock_boundary_status") == "valid"
        rollback_ok = evidence.get("rollback_ready", False)

        # check ranger pack
        has_ranger_evidence = False
        ranger_ok = True
        for p in self.submitted_packets:
            if p.domain == "sol_sovereign" and p.level == 28 and p.actor_type == "ranger":
                has_ranger_evidence = True
                p_ev = extract(p, "evidence", {}) or {}
                if extract(p, "recommendation") == "reject" or not p_ev.get("token_validity", False):
                    ranger_ok = False
                    errors.append("Ranger evidence indicates invalid token or rejected propagation.")

        meta = extract(packet, "metadata", {}) or {}
        if not has_ranger_evidence and not meta.get("skip_ranger_check"):
            ranger_ok = False
            errors.append("Missing required Level 28 ranger evidence packet.")

        passed_court = passed and local_q and global_q and geo_valid and lock_valid and rollback_ok and ranger_ok

        if passed_court:
            decision = "promote_level28_candidate"
        else:
            if not lock_valid:
                decision = "reject_transaction_propagation"
            elif not geo_valid:
                decision = "quarantine_route"
            elif not local_q or not global_q:
                decision = "hold_transaction_epoch"
            else:
                decision = "needs_more_evidence"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"transaction_propagation_packet_gate_{packet_id}",
            passed=passed_court,
            evidence_hash=packet_id,
            details={
                "decision": decision,
                "passed_court": passed_court,
                "errors": errors,
                "local_q": local_q,
                "global_q": global_q,
                "geo_valid": geo_valid,
                "lock_valid": lock_valid,
                "rollback_ok": rollback_ok,
                "ranger_ok": ranger_ok
            }
        )

    def review_transaction_orchestration_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a TransactionOrchestrationReport and returns a PromotionGateResult.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        report_id = extract(report, "report_id", "unknown_report")
        passed = extract(report, "passed_gates", True)
        result = extract(report, "result")
        success = extract(result, "success", True) if result else False
        decision = extract(result, "decision", "reject_promotion") if result else "reject_promotion"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"transaction_orchestration_gate_{report_id}",
            passed=passed and success,
            evidence_hash=report_id,
            details={"success": success, "decision": decision}
        )

    def review_promotion_docket(self, docket: Any) -> PromotionGateResult:
        """
        Reviews a PromotionDocket's completeness and evidence.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        docket_id = extract(docket, "docket_id", "unknown_docket")
        candidate_id = extract(docket, "candidate_id", "unknown_candidate")
        level = extract(docket, "level", 0)
        
        from sol_promotion_docket import validate_promotion_docket
        valid = validate_promotion_docket(docket)

        if not valid:
            decision = "needs_more_evidence"
        elif extract(docket, "quarantine_status", False):
            decision = "quarantine_candidate"
        else:
            decision = "accept_shadow_candidate"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"promotion_docket_gate_{docket_id}",
            passed=valid and decision == "accept_shadow_candidate",
            evidence_hash=docket_id,
            details={
                "candidate_id": candidate_id,
                "level": level,
                "valid": valid,
                "quarantine_status": extract(docket, "quarantine_status", False)
            }
        )

    def review_promotion_manifest(self, manifest: Any) -> PromotionGateResult:
        """
        Reviews a final PromotionManifest.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        manifest_id = extract(manifest, "manifest_id", "unknown_manifest")
        docket_id = extract(manifest, "docket_id", "unknown_docket")
        level = extract(manifest, "level", 0)
        verdict = extract(manifest, "verdict", None)
        verdict_decision = extract(verdict, "decision", "unknown") if verdict else "unknown"

        passed = verdict_decision in ["promote_level28_candidate", "promote_level29_candidate"]
        decision = "promote_level29_candidate" if passed else "reject_promotion"

        return PromotionGateResult(
            decision=decision,
            gate_name=f"promotion_manifest_gate_{manifest_id}",
            passed=passed,
            evidence_hash=manifest_id,
            details={
                "docket_id": docket_id,
                "level": level,
                "verdict_decision": verdict_decision
            }
        )

    def issue_court_supervised_promotion_verdict(self, docket: Any) -> Any:
        """
        Issues a PromotionVerdict after evaluating all evidence inside the docket.
        """
        import time
        from sol_promotion_docket import validate_promotion_docket, PromotionVerdict
        from sol_court_supervised_promotion import CourtPromotionPolicy, review_promotion_docket
        
        policy = CourtPromotionPolicy()
        review = review_promotion_docket(docket, policy)
        
        if not review.policy_satisfied:
            justification = "; ".join(review.errors)
            if not review.checked_invariants["evidence_complete"] or not review.checked_invariants["local_quorum"]:
                decision = "hold_promotion"
            elif not review.checked_invariants["quarantine_clean"]:
                decision = "quarantine_candidate"
            else:
                decision = "reject_promotion"
        else:
            if getattr(docket, "level", 0) == 36:
                decision = "promote_level36_candidate"
            elif getattr(docket, "level", 0) == 35:
                decision = "promote_level35_candidate"
            elif getattr(docket, "level", 0) == 34:
                decision = "promote_level34_candidate"
            elif getattr(docket, "level", 0) == 33:
                decision = "promote_level33_candidate"
            elif getattr(docket, "level", 0) == 32:
                decision = "promote_level32_candidate"
            elif getattr(docket, "level", 0) == 31:
                decision = "promote_level31_candidate"
            elif getattr(docket, "level", 0) == 30:
                decision = "promote_level30_candidate"
            else:
                decision = "promote_level29_candidate"
            justification = "All multi-manifold transaction and propagation invariants verified successfully."

        verdict_id = f"VERDICT_{docket.docket_id}_{int(time.time())}"
        return PromotionVerdict(
            verdict_id=verdict_id,
            decision=decision,
            justification=justification,
            judge_signatures=["Court_Justice_1", "Court_Justice_2"]
        )

    def review_calibration_loop_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a CalibrationLoopReport.
        """
        from sol_court_supervised_promotion import review_calibration_loop_report
        dec = review_calibration_loop_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"calibration_loop_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level30_candidate", "accept_shadow_calibration"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_boundary_calibration_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a ShardBoundaryCalibrationReport.
        """
        from sol_court_supervised_promotion import review_boundary_calibration_report
        dec = review_boundary_calibration_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"boundary_calibration_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level30_candidate", "accept_shadow_calibration"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_wavefront_stabilization_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a WavefrontAlignmentStabilizationReport.
        """
        from sol_court_supervised_promotion import review_wavefront_stabilization_report
        dec = review_wavefront_stabilization_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"wavefront_stabilization_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level30_candidate", "accept_shadow_calibration"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_calibration_control_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a CalibrationClosedLoopReport.
        """
        from sol_court_supervised_promotion import review_calibration_control_report
        dec = review_calibration_control_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"calibration_control_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level30_candidate", "accept_shadow_calibration", "authorize_sandbox_calibration_trial"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_waveguide_synthesis_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a WaveguideSynthesisReport.
        """
        from sol_court_supervised_promotion import review_waveguide_synthesis_report
        dec = review_waveguide_synthesis_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"waveguide_synthesis_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level31_candidate", "accept_shadow_fabric_candidate"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_simd_core_integration_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a SIMDCoreIntegrationReport.
        """
        from sol_court_supervised_promotion import review_simd_core_integration_report
        dec = review_simd_core_integration_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"simd_core_integration_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level31_candidate", "accept_shadow_fabric_candidate"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_waveguide_layout_optimization_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a WaveguideLayoutOptimizationReport.
        """
        from sol_court_supervised_promotion import review_waveguide_layout_optimization_report
        dec = review_waveguide_layout_optimization_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"waveguide_layout_optimization_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level31_candidate", "accept_shadow_fabric_candidate"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_fabric_synthesis_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a fabric synthesis SovereignPacket.
        """
        from sol_court_supervised_promotion import review_fabric_synthesis_packet
        dec = review_fabric_synthesis_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"fabric_synthesis_packet_gate",
            passed=(dec.decision in ["promote_level31_candidate", "accept_shadow_fabric_candidate", "authorize_sandbox_fabric_trial"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )

    def review_manifold_reshape_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a ManifoldReshapeReport.
        """
        from sol_court_supervised_promotion import review_manifold_reshape_report
        dec = review_manifold_reshape_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"manifold_reshape_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level32_candidate", "accept_shadow_reshape_candidate"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_pdm_carrier_relocation_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a PDMCarrierRelocationReport.
        """
        from sol_court_supervised_promotion import review_pdm_carrier_relocation_report
        dec = review_pdm_carrier_relocation_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"pdm_carrier_relocation_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level32_candidate", "accept_shadow_reshape_candidate"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_carrier_registry_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a CarrierRegistryReport.
        """
        from sol_court_supervised_promotion import review_carrier_registry_report
        dec = review_carrier_registry_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"carrier_registry_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level32_candidate", "accept_shadow_reshape_candidate"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_reshape_ranger_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a reshape ranger SovereignPacket.
        """
        from sol_court_supervised_promotion import review_reshape_ranger_packet
        dec = review_reshape_ranger_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"reshape_ranger_packet_gate",
            passed=(dec.decision in ["promote_level32_candidate", "accept_shadow_reshape_candidate", "authorize_sandbox_reshape_trial"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )

    def review_cadence_stability_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a CadenceStabilityReport.
        """
        from sol_court_supervised_promotion import review_cadence_stability_report
        dec = review_cadence_stability_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"cadence_stability_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level33_candidate", "accept_shadow_cadence_candidate"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_cadence_sync_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a CadenceSyncReport.
        """
        from sol_court_supervised_promotion import review_cadence_sync_report
        dec = review_cadence_sync_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"cadence_sync_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level33_candidate", "accept_shadow_cadence_candidate"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_transaction_cadence_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a TransactionCadenceReport.
        """
        from sol_court_supervised_promotion import review_transaction_cadence_report
        dec = review_transaction_cadence_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"transaction_cadence_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level33_candidate", "accept_shadow_cadence_candidate"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_cadence_ranger_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a cadence ranger SovereignPacket.
        """
        from sol_court_supervised_promotion import review_cadence_ranger_packet
        dec = review_cadence_ranger_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"cadence_ranger_packet_gate",
            passed=(dec.decision in ["promote_level33_candidate", "accept_shadow_cadence_candidate", "authorize_sandbox_cadence_trial"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )

    def review_entangled_propagation_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an EntangledPropagationReport.
        """
        from sol_court_supervised_promotion import review_entangled_propagation_report
        dec = review_entangled_propagation_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"entangled_propagation_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level34_candidate", "accept_shadow_entangled_commit"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_synchronized_commit_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a SynchronizedCommitReport.
        """
        from sol_court_supervised_promotion import review_synchronized_commit_report
        dec = review_synchronized_commit_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"synchronized_commit_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level34_candidate", "accept_shadow_entangled_commit"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_entangled_commit_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an EntangledCommitReport.
        """
        from sol_court_supervised_promotion import review_entangled_commit_report
        dec = review_entangled_commit_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"entangled_commit_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level34_candidate", "accept_shadow_entangled_commit"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_entangled_commit_ranger_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews an entangled commit ranger SovereignPacket.
        """
        from sol_court_supervised_promotion import review_entangled_commit_ranger_packet
        dec = review_entangled_commit_ranger_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"entangled_commit_ranger_packet_gate",
            passed=(dec.decision in ["promote_level34_candidate", "accept_shadow_entangled_commit", "authorize_sandbox_entangled_commit_trial"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )

    def review_entangled_calibration_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an EntangledCalibrationReport.
        """
        from sol_court_supervised_promotion import review_entangled_calibration_report
        dec = review_entangled_calibration_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"entangled_calibration_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level35_candidate", "accept_shadow_entangled_feedback"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_entangled_feedback_loop_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an EntangledFeedbackLoopReport.
        """
        from sol_court_supervised_promotion import review_entangled_feedback_loop_report
        dec = review_entangled_feedback_loop_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"entangled_feedback_loop_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level35_candidate", "accept_shadow_entangled_feedback"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_entangled_stability_control_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an EntangledStabilityControlReport.
        """
        from sol_court_supervised_promotion import review_entangled_stability_control_report
        dec = review_entangled_stability_control_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"entangled_stability_control_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level35_candidate", "accept_shadow_entangled_feedback"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_entangled_feedback_ranger_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews an entangled feedback ranger SovereignPacket.
        """
        from sol_court_supervised_promotion import review_entangled_feedback_ranger_packet
        dec = review_entangled_feedback_ranger_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"entangled_feedback_ranger_packet_gate",
            passed=(dec.decision in ["promote_level35_candidate", "accept_shadow_entangled_feedback", "authorize_sandbox_entangled_feedback_trial"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )

    def review_sovereign_runtime_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a SovereignRuntimeReport.
        """
        from sol_court_supervised_promotion import review_sovereign_runtime_report
        dec = review_sovereign_runtime_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"sovereign_runtime_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level36_candidate", "accept_shadow_runtime"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_levelup_sequence_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a LevelUpSequenceReport.
        """
        from sol_court_supervised_promotion import review_levelup_sequence_report
        dec = review_levelup_sequence_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"levelup_sequence_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level36_candidate", "accept_shadow_runtime"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_runtime_governance_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a RuntimeGovernanceReport.
        """
        from sol_court_supervised_promotion import review_runtime_governance_report
        dec = review_runtime_governance_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"runtime_governance_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level36_candidate", "accept_shadow_runtime"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_sovereign_runtime_ranger_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a sovereign runtime ranger SovereignPacket.
        """
        from sol_court_supervised_promotion import review_sovereign_runtime_ranger_packet
        dec = review_sovereign_runtime_ranger_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"sovereign_runtime_ranger_packet_gate",
            passed=(dec.decision in ["promote_level36_candidate", "accept_shadow_runtime", "authorize_sandbox_runtime_step"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )


    def review_hierarchical_waveguide_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a HierarchicalWaveguideReport.
        """
        from sol_court_supervised_promotion import review_hierarchical_waveguide_report
        dec = review_hierarchical_waveguide_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"hierarchical_waveguide_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level37_candidate", "accept_shadow_waveguide_arithmetic"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_interlane_prefix_carry_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an InterLaneCarryReport.
        """
        from sol_court_supervised_promotion import review_interlane_prefix_carry_report
        dec = review_interlane_prefix_carry_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"interlane_prefix_carry_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level37_candidate", "accept_shadow_waveguide_arithmetic"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_waveguide_arithmetic_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a WaveguideArithmeticReport.
        """
        from sol_court_supervised_promotion import review_waveguide_arithmetic_report
        dec = review_waveguide_arithmetic_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"waveguide_arithmetic_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level37_candidate", "accept_shadow_waveguide_arithmetic"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_waveguide_arithmetic_ranger_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a waveguide arithmetic ranger SovereignPacket.
        """
        from sol_court_supervised_promotion import review_waveguide_arithmetic_ranger_packet
        dec = review_waveguide_arithmetic_ranger_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"waveguide_arithmetic_ranger_packet_gate",
            passed=(dec.decision in ["promote_level37_candidate", "accept_shadow_waveguide_arithmetic", "authorize_sandbox_waveguide_arithmetic_trial"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )

    def review_entangled_wavefront_consensus_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an EntangledWavefrontConsensusReport.
        """
        from sol_court_supervised_promotion import review_entangled_wavefront_consensus_report
        dec = review_entangled_wavefront_consensus_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"entangled_wavefront_consensus_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level38_candidate", "accept_shadow_atomic_consensus"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_multimanifold_atomic_commit_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a MultiManifoldAtomicCommitReport.
        """
        from sol_court_supervised_promotion import review_multimanifold_atomic_commit_report
        dec = review_multimanifold_atomic_commit_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"multimanifold_atomic_commit_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level38_candidate", "accept_shadow_atomic_consensus"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_entangled_atomic_epoch_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews an EntangledAtomicEpochReport.
        """
        from sol_court_supervised_promotion import review_entangled_atomic_epoch_report
        dec = review_entangled_atomic_epoch_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"entangled_atomic_epoch_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level38_candidate", "accept_shadow_atomic_consensus"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_atomic_consensus_ranger_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews an atomic consensus ranger SovereignPacket.
        """
        from sol_court_supervised_promotion import review_atomic_consensus_ranger_packet
        dec = review_atomic_consensus_ranger_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"atomic_consensus_ranger_packet_gate",
            passed=(dec.decision in ["promote_level38_candidate", "accept_shadow_atomic_consensus", "authorize_sandbox_atomic_commit_trial"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )

    def review_state_relocation_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a StateRelocationReport.
        """
        from sol_court_supervised_promotion import review_state_relocation_report
        dec = review_state_relocation_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"state_relocation_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level39_candidate", "accept_shadow_state_relocation"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_realtime_calibration_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a RealtimeCalibrationReport.
        """
        from sol_court_supervised_promotion import review_realtime_calibration_report
        dec = review_realtime_calibration_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"realtime_calibration_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level39_candidate", "accept_shadow_state_relocation"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_relocation_protocol_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a RelocationProtocolReport.
        """
        from sol_court_supervised_promotion import review_relocation_protocol_report
        dec = review_relocation_protocol_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"relocation_protocol_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level39_candidate", "accept_shadow_state_relocation"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_state_relocation_ranger_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a state relocation ranger SovereignPacket.
        """
        from sol_court_supervised_promotion import review_state_relocation_ranger_packet
        dec = review_state_relocation_ranger_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"state_relocation_ranger_packet_gate",
            passed=(dec.decision in ["promote_level39_candidate", "accept_shadow_state_relocation", "authorize_sandbox_state_relocation_trial"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )

    def review_relocation_fault_matrix_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a RelocationFaultMatrixReport.
        """
        from sol_court_supervised_promotion import review_relocation_fault_matrix_report
        dec = review_relocation_fault_matrix_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"relocation_fault_matrix_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level40_candidate", "accept_shadow_fault_matrix"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_calibration_fault_matrix_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a CalibrationFaultMatrixReport.
        """
        from sol_court_supervised_promotion import review_calibration_fault_matrix_report
        dec = review_calibration_fault_matrix_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"calibration_fault_matrix_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level40_candidate", "accept_shadow_fault_matrix"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_rollback_proof_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a RollbackProofReport.
        """
        from sol_court_supervised_promotion import review_rollback_proof_report
        dec = review_rollback_proof_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"rollback_proof_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level40_candidate", "accept_shadow_fault_matrix"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_safety_oracle_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a RelocationSafetyOracleReport.
        """
        from sol_court_supervised_promotion import review_safety_oracle_report
        dec = review_safety_oracle_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"safety_oracle_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level40_candidate", "accept_shadow_fault_matrix"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_fault_matrix_ranger_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a fault matrix ranger SovereignPacket.
        """
        from sol_court_supervised_promotion import review_fault_matrix_ranger_packet
        dec = review_fault_matrix_ranger_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"fault_matrix_ranger_packet_gate",
            passed=(dec.decision in ["promote_level40_candidate", "accept_shadow_fault_matrix", "authorize_sandbox_fault_audit"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )

    def review_transactional_route_optimization_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a TransactionalRouteOptimizationReport.
        """
        from sol_court_supervised_promotion import review_transactional_route_optimization_report
        dec = review_transactional_route_optimization_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"route_optimization_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level41_candidate", "accept_shadow_route_rebalance"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_waveguide_rebalance_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a WaveguideRebalanceReport.
        """
        from sol_court_supervised_promotion import review_waveguide_rebalance_report
        dec = review_waveguide_rebalance_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"waveguide_rebalance_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level41_candidate", "accept_shadow_route_rebalance"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_route_rebalance_protocol_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a RouteRebalanceProtocolReport.
        """
        from sol_court_supervised_promotion import review_route_rebalance_protocol_report
        dec = review_route_rebalance_protocol_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"route_rebalance_protocol_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level41_candidate", "accept_shadow_route_rebalance"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_waveguide_rebalance_oracle_report(self, report: Any) -> PromotionGateResult:
        """
        Reviews a WaveguideRebalanceOracleReport.
        """
        from sol_court_supervised_promotion import review_waveguide_rebalance_oracle_report
        dec = review_waveguide_rebalance_oracle_report(report)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"waveguide_rebalance_oracle_gate_{extract_id(report)}",
            passed=(dec.decision in ["promote_level41_candidate", "accept_shadow_route_rebalance", "accept_shadow"]),
            evidence_hash=extract_id(report),
            details={"justification": dec.justification}
        )

    def review_route_rebalance_ranger_packet(self, packet: Any) -> PromotionGateResult:
        """
        Reviews a route/rebalance ranger SovereignPacket.
        """
        from sol_court_supervised_promotion import review_route_rebalance_ranger_packet
        dec = review_route_rebalance_ranger_packet(packet)
        return PromotionGateResult(
            decision=dec.decision,
            gate_name=f"route_rebalance_ranger_packet_gate",
            passed=(dec.decision in ["promote_level41_candidate", "accept_shadow_route_rebalance", "authorize_sandbox_route_rebalance_trial"]),
            evidence_hash="packet_evidence",
            details={"justification": dec.justification}
        )



def extract_id(obj: Any) -> str:
    if isinstance(obj, dict):
        return obj.get("report_id") or obj.get("docket_id") or "unknown"
    return getattr(obj, "report_id", None) or getattr(obj, "docket_id", "unknown")











