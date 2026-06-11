# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Court-Supervised Promotion
==============================
Enforces gate requirements, evaluates readiness, and issues authorization or rejection reviews.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class CourtPromotionPolicy:
    require_all_gates_pass: bool = True
    require_no_missing_evidence: bool = True
    require_no_missing_snapshots: bool = True
    require_no_unresolved_quarantine: bool = True
    require_local_quorum: bool = True
    require_global_quorum: bool = True
    require_lock_boundaries_valid: bool = True
    require_transaction_boundaries_valid: bool = True
    require_geodesic_propagation_stable: bool = True
    require_wavefront_alignment_stable: bool = True
    require_tests_passed: bool = True
    allow_production_mutation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CourtPromotionReview:
    review_id: str
    docket_id: str
    policy_satisfied: bool
    checked_invariants: Dict[str, bool]
    errors: List[str] = field(default_factory=list)

@dataclass
class CourtPromotionDecision:
    decision_id: str
    decision: str  # "accept_shadow_candidate" | "needs_more_evidence" | "hold_promotion" | "reject_promotion" | "authorize_sandbox_promotion_trial" | "rollback_candidate" | "quarantine_candidate" | "promote_level29_candidate"
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class CourtPromotionReport:
    report_id: str
    review: CourtPromotionReview
    decision: CourtPromotionDecision
    passed_gates: bool


def review_promotion_docket(docket: Any, policy: CourtPromotionPolicy) -> CourtPromotionReview:
    """
    Validates all docket contents against the CourtPromotionPolicy.
    """
    from sol_promotion_docket import validate_promotion_docket
    errors = []
    checked = {
        "gates_passed": True,
        "evidence_complete": True,
        "snapshots_complete": True,
        "quarantine_clean": True,
        "local_quorum": True,
        "global_quorum": True,
        "locks_valid": True,
        "boundaries_valid": True,
        "propagation_stable": True,
        "alignment_stable": True,
        "tests_passed": True,
        "sandbox_only": True
    }

    # Helper function to access dict or object attributes
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    # 1. Complete docket validation
    if policy.require_no_missing_evidence:
        if not validate_promotion_docket(docket):
            checked["evidence_complete"] = False
            errors.append("Promotion docket fails basic completeness checks (missing evidence types)")

    # Extract payloads for specific validation checks
    def extract_evidence_payload(e_type):
        for item in docket.evidence:
            if getattr(item, "evidence_type", None) == e_type or (isinstance(item, dict) and item.get("evidence_type") == e_type):
                return getattr(item, "payload", None) or (item.get("payload") if isinstance(item, dict) else item)
        return None

    ranger_packet = extract_evidence_payload("ranger_packet")
    consensus_report = extract_evidence_payload("consensus_report")
    transaction_report = extract_evidence_payload("transaction_report")
    geodesic_report = extract_evidence_payload("geodesic_propagation_report")
    telemetry_report = extract_evidence_payload("telemetry_report")
    rollback_snapshot = extract_evidence_payload("rollback_snapshot")

    # 2. Quarantine checks
    if policy.require_no_unresolved_quarantine:
        if extract(docket, "quarantine_status", False):
            checked["quarantine_clean"] = False
            errors.append("Unresolved quarantine flag present on the docket")

    # 3. Rollback snapshots checks
    if policy.require_no_missing_snapshots:
        if not rollback_snapshot:
            checked["snapshots_complete"] = False
            errors.append("Missing rollback snapshots references")

    # 4. Quorum validation checks
    if consensus_report:
        decision = extract(consensus_report, "decision", None)
        agreed = extract(decision, "agreed", False) if decision else False
        votes = extract(consensus_report, "votes", [])
        
        if policy.require_global_quorum:
            if not agreed:
                checked["global_quorum"] = False
                errors.append("Global quorum check failed")
                
        if policy.require_local_quorum:
            # if any vote decision is reject, local quorum failed
            for v in votes:
                dec = extract(v, "decision", "")
                if dec == "reject":
                    checked["local_quorum"] = False
                    errors.append(f"Local quorum check failed for participant {extract(v, 'node_id', 'unknown')}")

    # 5. Lock boundary validation checks & Level 30 calibration checks
    if ranger_packet:
        ev = extract(ranger_packet, "evidence", {}) or {}
        if getattr(docket, "level", 0) == 30:
            # Level 30 Distributed Calibration and Wavefront Alignment Stabilization checks
            cal_loop_rep = extract_evidence_payload("calibration_loop_report")
            bnd_cal_rep = extract_evidence_payload("boundary_calibration_report")
            wave_stab_rep = extract_evidence_payload("wavefront_stabilization_report")
            cal_ctrl_rep = extract_evidence_payload("calibration_control_report")
            
            # Calibration loop report checks
            if cal_loop_rep:
                # Bounded control policy check
                policy_obj = extract(cal_loop_rep, "policy", None)
                if not policy_obj or extract(policy_obj, "max_steps", 0) <= 0:
                    errors.append("Level 30 promotion requires a valid bounded control policy")
                
                # Baseline telemetry check
                if not telemetry_report:
                    errors.append("Level 30 promotion requires baseline telemetry")
                
                # Stable loop result
                res = extract(cal_loop_rep, "result")
                success = extract(res, "success", False) if res else False
                if not success:
                    errors.append("Level 30 promotion requires stable loop result")
            else:
                errors.append("Level 30 promotion requires calibration loop report")
                
            # Boundary drift/crosstalk/reflection checks from evidence
            phase_drift = extract(ev, "phase_drift_after", 0.0)
            if phase_drift > 0.10:
                checked["alignment_stable"] = False
                errors.append(f"Phase drift {phase_drift} exceeds threshold 0.10")
                
            crosstalk = extract(ev, "crosstalk_after", 0.0)
            if crosstalk > 0.05:
                errors.append(f"Crosstalk {crosstalk} exceeds threshold 0.05")
                
            boundary_reflection = extract(ev, "boundary_reflection_after", 0.0)
            if boundary_reflection > 0.05:
                errors.append(f"Boundary reflection {boundary_reflection} exceeds threshold 0.05")
                
            # Wavefront stabilization breaches check
            if wave_stab_rep:
                wave_result = extract(wave_stab_rep, "result")
                stable = extract(wave_result, "stable", False) if wave_result else False
                breaches = extract(wave_result, "breaches", []) if wave_result else []
                if breaches:
                    errors.append(f"Wavefront alignment reflection breach blocks promotion: {', '.join(breaches)}")
            else:
                errors.append("Level 30 promotion requires wavefront stabilization report")
        elif getattr(docket, "level", 0) == 31:
            # Level 31 Advanced Waveguide Fabric Synthesis and SIMD Core Integration checks
            wf_syn_rep = extract_evidence_payload("waveguide_synthesis_report")
            simd_int_rep = extract_evidence_payload("simd_core_integration_report")
            wf_opt_rep = extract_evidence_payload("waveguide_layout_optimization_report")
            
            if wf_syn_rep:
                success = extract(wf_syn_rep, "success", False)
                if not success:
                    errors.append("Level 31 promotion requires successful waveguide synthesis report")
            else:
                errors.append("Level 31 promotion requires waveguide synthesis report")
                
            if simd_int_rep:
                oracle_match = extract(simd_int_rep, "oracle_match", True)
                if not oracle_match:
                    errors.append("Oracle mismatch blocks promotion")
            else:
                errors.append("Level 31 promotion requires SIMD core integration report")
        elif getattr(docket, "level", 0) == 32:
            # Level 32 Multi-Dimensional Manifold Reshape and Dynamic PDM Carrier Relocation checks
            reshape_rep = extract_evidence_payload("manifold_reshape_report")
            carrier_reloc_rep = extract_evidence_payload("pdm_carrier_relocation_report")
            carrier_reg_rep = extract_evidence_payload("carrier_registry_report")
            
            if reshape_rep:
                res = extract(reshape_rep, "result")
                success = extract(res, "success", False) if res else False
                if not success:
                    errors.append("Level 32 promotion requires successful manifold reshape report")
            else:
                errors.append("Level 32 promotion requires manifold reshape report")
                
            if carrier_reloc_rep:
                res = extract(carrier_reloc_rep, "result")
                success = extract(res, "success", False) if res else False
                if not success:
                    errors.append("Level 32 promotion requires successful carrier relocation report")
            else:
                errors.append("Level 32 promotion requires pdm carrier relocation report")
                
            if carrier_reg_rep:
                leases_valid = extract(carrier_reg_rep, "leases_valid", True)
                snap_present = extract(carrier_reg_rep, "snapshot_present", True)
                if not leases_valid or not snap_present:
                    errors.append("Level 32 promotion requires valid carrier leases and snapshot present")
            else:
                errors.append("Level 32 promotion requires carrier registry report")
        elif getattr(docket, "level", 0) == 36:
            # Level 36 Sovereign Execution Runtime and Scheduled Level-Up Sequence checks
            run_rep = extract_evidence_payload("sovereign_runtime_report")
            seq_rep = extract_evidence_payload("levelup_sequence_report")
            gov_rep = extract_evidence_payload("runtime_governance_report")
            
            if ranger_packet:
                ev = extract(ranger_packet, "evidence", {}) or {}
                if extract(ev, "ledger_completeness") != "complete":
                    errors.append("Missing runtime ledger logging history for Level 36")
                if extract(ev, "runtime_mode") == "quarantine":
                    checked["quarantine_clean"] = False
                    errors.append("Unresolved quarantine present on Level 36 runtime")
                if extract(ev, "runtime_mode") == "production":
                    errors.append("Production execution attempt blocked for Level 36")
                if not extract(ev, "promotion_readiness", False):
                    errors.append("Level 36 promotion readiness is false according to ranger packet")
            else:
                errors.append("Level 36 promotion requires sovereign runtime ranger packet")
                
            if not run_rep:
                errors.append("Level 36 promotion requires sovereign runtime report")
            if not seq_rep:
                errors.append("Level 36 promotion requires level-up sequence report")
        elif getattr(docket, "level", 0) == 35:
            # Level 35 Multi-Manifold Entangled Wavefront Calibration and Feedback Loops checks
            cal_rep = extract_evidence_payload("entangled_calibration_report")
            fb_rep = extract_evidence_payload("entangled_feedback_loop_report")
            stab_rep = extract_evidence_payload("entangled_stability_control_report")
            
            if ranger_packet:
                ev = extract(ranger_packet, "evidence", {}) or {}
                if extract(ev, "calibration_baseline_status") != "present":
                    errors.append("Missing calibration baseline telemetry for Level 35")
                
                # Check thresholds
                phase_drift = extract(ev, "phase_drift_after", 0.0)
                cadence_drift = extract(ev, "cadence_drift_after", 0.0)
                carrier_error = extract(ev, "carrier_phase_error_after", 0.0)
                crosstalk = extract(ev, "crosstalk_after", 0.0)
                reflection = extract(ev, "boundary_reflection_after", 0.0)
                
                if phase_drift > 0.05:
                    errors.append(f"Phase drift {phase_drift} exceeds threshold 0.05")
                if cadence_drift > 0.05:
                    errors.append(f"Cadence drift {cadence_drift} exceeds threshold 0.05")
                if carrier_error > 0.05:
                    errors.append(f"Carrier phase error {carrier_error} exceeds threshold 0.05")
                if crosstalk > 0.05:
                    errors.append(f"Crosstalk {crosstalk} exceeds threshold 0.05")
                if reflection > 0.05:
                    errors.append(f"Boundary reflection {reflection} exceeds threshold 0.05")
                    
                if not extract(ev, "active_mass_preservation", True):
                    errors.append("Active mass preservation violated")
                if extract(ev, "synchronized_commit_readiness") != "stable":
                    errors.append("Synchronized commits not blocked during unstable feedback")
                if extract(ev, "rollback_status") == "missing":
                    checked["snapshots_complete"] = False
                    errors.append("Missing rollback snapshots references for Level 35")
                if not extract(ev, "promotion_readiness", False):
                    errors.append("Level 35 promotion readiness is false according to ranger packet")
            else:
                errors.append("Level 35 promotion requires entangled feedback ranger packet")
                
            if not cal_rep:
                errors.append("Level 35 promotion requires calibration report")
            else:
                targets = extract(cal_rep, "targets", [])
                if not targets:
                    errors.append("Level 35 promotion requires valid calibration targets")
                    
            if not fb_rep:
                errors.append("Level 35 promotion requires feedback loop report")
            else:
                policy_obj = extract(fb_rep, "policy", None)
                if policy_obj is not None:
                    if extract(policy_obj, "max_steps", 0) <= 0:
                        errors.append("Level 35 promotion requires a valid bounded control policy")
                
                res = extract(fb_rep, "result")
                success = extract(res, "success", False) if res else False
                if not success:
                    errors.append("Level 35 promotion requires stable feedback loop result")
        elif getattr(docket, "level", 0) == 34:
            # Level 34 Multi-Manifold Entangled Wavefront Propagation and Synchronized Sequencer Commits checks
            ent_prop_rep = extract_evidence_payload("entangled_propagation_report")
            sync_comm_rep = extract_evidence_payload("synchronized_commit_report")
            ent_comm_rep = extract_evidence_payload("entangled_commit_report")
            
            if ranger_packet:
                ev = extract(ranger_packet, "evidence", {}) or {}
                if extract(ev, "rollback_readiness") != "present":
                    checked["snapshots_complete"] = False
                    errors.append("Missing rollback snapshots references for Level 34")
                if extract(ev, "local_quorum_status") != "passed":
                    checked["local_quorum"] = False
                    errors.append("Local quorum check failed for Level 34")
                if extract(ev, "global_quorum_status") != "passed":
                    checked["global_quorum"] = False
                    errors.append("Global quorum check failed for Level 34")
                if extract(ev, "synchronized_commit_barrier_status") != "satisfied":
                    errors.append("Synchronized commit barrier unsatisfied for Level 34")
                if extract(ev, "propagation_path_status") != "valid":
                    errors.append("Invalid geodesic propagation path for Level 34")
                if extract(ev, "lock_boundary_status") == "deadlock_detected":
                    errors.append("Cross-manifold deadlock detected for Level 34")
                if extract(ev, "cadence_status") == "split_brain":
                    errors.append("Split-brain clock synchronization detected for Level 34")
            else:
                errors.append("Level 34 promotion requires entangled commit ranger packet")
                
            if not ent_prop_rep:
                errors.append("Level 34 promotion requires entangled propagation report")
            if not sync_comm_rep:
                errors.append("Level 34 promotion requires synchronized commit report")
            if not ent_comm_rep:
                errors.append("Level 34 promotion requires entangled commit report")
        elif getattr(docket, "level", 0) == 33:
            # Level 33 Multi-Manifold Transaction Consensus and Temporal Cadence Stabilization checks
            cad_stab_rep = extract_evidence_payload("cadence_stability_report")
            cad_sync_rep = extract_evidence_payload("cadence_sync_report")
            tx_cad_rep = extract_evidence_payload("transaction_cadence_report")
            
            if ranger_packet:
                ev = extract(ranger_packet, "evidence", {}) or {}
                if extract(ev, "rollback_readiness") != "present":
                    checked["snapshots_complete"] = False
                    errors.append("Missing rollback snapshots references for Level 33")
                if extract(ev, "local_quorum_status") != "passed":
                    checked["local_quorum"] = False
                    errors.append("Local quorum check failed for Level 33")
                if extract(ev, "global_quorum_status") != "passed":
                    checked["global_quorum"] = False
                    errors.append("Global quorum check failed for Level 33")
                if extract(ev, "cadence_window_status") == "split_brain":
                    errors.append("Split-brain clock synchronization detected for Level 33")
            else:
                errors.append("Level 33 promotion requires cadence ranger packet")
                
            if not cad_stab_rep:
                errors.append("Level 33 promotion requires cadence stability report")
            if not cad_sync_rep:
                errors.append("Level 33 promotion requires cadence sync report")
            if not tx_cad_rep:
                errors.append("Level 33 promotion requires transaction cadence report")
        else:
            # Level 28/29 lock and transaction boundaries checks:
            if policy.require_lock_boundaries_valid:
                if extract(ev, "lock_boundary_status") != "valid":
                    checked["locks_valid"] = False
                    errors.append("Global lock boundaries validation failed")
                    
            if policy.require_transaction_boundaries_valid:
                if extract(ev, "transaction_boundary_status") != "valid":
                    checked["boundaries_valid"] = False
                    errors.append("Transaction boundaries validation failed")
                    
            # Split-brain check
            if extract(ev, "split_brain_detected") or extract(ev, "consensus_quorum_status") == "failed":
                checked["global_quorum"] = False
                errors.append("Split-brain transaction state detected")

    # 6. Propagation & alignment checks
    if geodesic_report:
        res = extract(geodesic_report, "result", None)
        if policy.require_geodesic_propagation_stable:
            success = extract(res, "success", False) if res else False
            if not res or not success:
                checked["propagation_stable"] = False
                errors.append("Geodesic propagation update failed or was unstable")

    if telemetry_report:
        if policy.require_wavefront_alignment_stable:
            drift = extract(telemetry_report, "drift", 0.0) or extract(telemetry_report, "max_drift", 0.0)
            res = extract(telemetry_report, "result", None)
            if res:
                drift = extract(res, "max_drift", drift)
            if drift > 0.10:
                checked["alignment_stable"] = False
                errors.append("Wavefront phase error exceeds stability threshold")

    # 7. Production promotion check
    if not policy.allow_production_mutation:
        if extract(docket, "metadata", {}).get("allow_production_promotion", False):
            checked["sandbox_only"] = False
            errors.append("Automatic production promotion is prohibited")

    # 8. Test checks
    if policy.require_tests_passed:
        test_summary = extract_evidence_payload("test_summary")
        if test_summary:
            status = extract(test_summary, "status", "unknown")
            if status not in ["passed", "all_passed"]:
                checked["tests_passed"] = False
                errors.append(f"Critical test failures present on docket: {status}")

    policy_satisfied = len(errors) == 0
    review_id = f"REV_{docket.docket_id}_{int(time.time())}"
    return CourtPromotionReview(
        review_id=review_id,
        docket_id=docket.docket_id,
        policy_satisfied=policy_satisfied,
        checked_invariants=checked,
        errors=errors
    )


def evaluate_promotion_readiness(docket: Any, policy: CourtPromotionPolicy) -> bool:
    """
    Checks if a candidate is ready for level promotion by running the policy review.
    """
    review = review_promotion_docket(docket, policy)
    return review.policy_satisfied


def authorize_sandbox_promotion_trial(docket: Any, token_request: Any) -> CourtPromotionDecision:
    """
    Grants sandbox trial status if constraints allow.
    """
    policy = CourtPromotionPolicy()
    review = review_promotion_docket(docket, policy)
    
    # Sandbox trial requires rollback snapshots and no quarantine
    if not review.checked_invariants["snapshots_complete"]:
        return CourtPromotionDecision(
            decision_id=f"DEC_SBOX_{int(time.time())}",
            decision="hold_promotion",
            justification="Sandbox trial rejected: Missing rollback snapshots"
        )
    if not review.checked_invariants["quarantine_clean"]:
        return CourtPromotionDecision(
            decision_id=f"DEC_SBOX_{int(time.time())}",
            decision="reject_promotion",
            justification="Sandbox trial rejected: Unresolved quarantine boundaries"
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_SBOX_{int(time.time())}",
        decision="authorize_sandbox_promotion_trial",
        justification="Authorized sandbox-only promotion trial"
    )


def reject_or_hold_promotion(docket: Any, reason: str) -> CourtPromotionDecision:
    """
    Registers a reject or hold decision.
    """
    decision_type = "hold_promotion"
    if "quarantine" in reason.lower() or "deadlock" in reason.lower() or "critical" in reason.lower():
        decision_type = "reject_promotion"
        
    return CourtPromotionDecision(
        decision_id=f"DEC_REJ_{int(time.time())}",
        decision=decision_type,
        justification=reason
    )


def review_calibration_loop_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a CalibrationLoopReport and issues a decision.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed = extract(report, "passed_gates", False)
    result = extract(report, "result")
    success = extract(result, "success", False) if result else False
    errors = extract(result, "errors", []) if result else []
    rolled_back = extract(result, "rolled_back", False) if result else False
    quarantined = extract(result, "quarantined", False) if result else False

    if errors:
        reason = "; ".join(errors)
        if quarantined:
            return CourtPromotionDecision(f"DEC_CAL_{int(time.time())}", "quarantine_boundary_group", f"Quarantining group: {reason}")
        if rolled_back:
            return CourtPromotionDecision(f"DEC_CAL_{int(time.time())}", "rollback_calibration_loop", f"Rolling back loop: {reason}")
        return CourtPromotionDecision(f"DEC_CAL_{int(time.time())}", "reject_calibration_loop", f"Rejection: {reason}")
        
    if not passed or not success:
        return CourtPromotionDecision(f"DEC_CAL_{int(time.time())}", "hold_calibration_loop", "Calibration loop is unstable or gates failed.")
        
    return CourtPromotionDecision(f"DEC_CAL_{int(time.time())}", "accept_shadow_calibration", "Calibration loop is stable and coherent.")


def review_boundary_calibration_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a ShardBoundaryCalibrationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    errors = extract(report, "errors", []) or []
    
    if not success or errors:
        reason = "; ".join(errors) if errors else "Validation failed"
        if "crosstalk" in reason.lower():
            return CourtPromotionDecision(f"DEC_BND_{int(time.time())}", "quarantine_boundary_group", f"High crosstalk: {reason}")
        return CourtPromotionDecision(f"DEC_BND_{int(time.time())}", "reject_calibration_loop", f"Boundary error: {reason}")
        
    return CourtPromotionDecision(f"DEC_BND_{int(time.time())}", "accept_shadow_calibration", "Shard boundary calibration verified successfully.")


def review_wavefront_stabilization_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a WavefrontAlignmentStabilizationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    result = extract(report, "result")
    stable = extract(result, "stable", False) if result else False
    breaches = extract(result, "breaches", []) if result else []
    
    if not stable or breaches:
        reason = "; ".join(breaches) if breaches else "Alignment unstable"
        if "reflection" in reason.lower():
            return CourtPromotionDecision(f"DEC_WAVE_{int(time.time())}", "reject_calibration_loop", f"Boundary reflection breach blocks promotion: {reason}")
        return CourtPromotionDecision(f"DEC_WAVE_{int(time.time())}", "hold_calibration_loop", f"Alignment unstable: {reason}")
        
    return CourtPromotionDecision(f"DEC_WAVE_{int(time.time())}", "promote_level30_candidate", "Wavefront alignment stabilization trial approved.")


def review_calibration_control_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a CalibrationClosedLoopReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    applied = extract(report, "applied", False)
    validated = extract(report, "validated", False)
    
    if not validated:
        return CourtPromotionDecision(f"DEC_CTRL_{int(time.time())}", "reject_calibration_loop", "Closed-loop control validation failed.")
        
    if applied:
        return CourtPromotionDecision(f"DEC_CTRL_{int(time.time())}", "promote_level30_candidate", "Closed-loop control applied successfully.")
    else:
        return CourtPromotionDecision(f"DEC_CTRL_{int(time.time())}", "authorize_sandbox_calibration_trial", "Closed-loop control suggestions validated in shadow mode.")


def review_waveguide_synthesis_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a WaveguideSynthesisReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    errors = extract(report, "errors", []) or []
    
    if errors or not success:
        reason = "; ".join(errors) if errors else "Synthesis gates failed"
        if "crosstalk" in reason.lower():
            return CourtPromotionDecision(f"DEC_WF_{int(time.time())}", "quarantine_candidate_fabric", f"Synthesis rejected due to crosstalk/quarantine: {reason}")
        return CourtPromotionDecision(f"DEC_WF_{int(time.time())}", "reject_fabric_candidate", f"Synthesis rejected: {reason}")
        
    return CourtPromotionDecision(f"DEC_WF_{int(time.time())}", "accept_shadow_fabric_candidate", "Waveguide fabric candidate is accepted in shadow mode.")


def review_simd_core_integration_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a SIMDCoreIntegrationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    errors = extract(report, "errors", []) or []
    oracle_match = extract(report, "oracle_match", True)
    
    if errors or not success:
        return CourtPromotionDecision(f"DEC_SIMD_{int(time.time())}", "reject_fabric_candidate", f"SIMD core integration failed: {'; '.join(errors)}")
        
    if not oracle_match:
        return CourtPromotionDecision(f"DEC_SIMD_{int(time.time())}", "reject_fabric_candidate", "Oracle mismatch blocks promotion.")
        
    return CourtPromotionDecision(f"DEC_SIMD_{int(time.time())}", "accept_shadow_fabric_candidate", "SIMD core integration is accepted in shadow mode.")


def review_waveguide_layout_optimization_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a WaveguideLayoutOptimizationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", True)
    errors = extract(report, "errors", []) or []
    
    if errors or not success:
         return CourtPromotionDecision(f"DEC_OPT_{int(time.time())}", "reject_fabric_candidate", f"Layout optimization failed: {'; '.join(errors)}")
         
    return CourtPromotionDecision(f"DEC_OPT_{int(time.time())}", "accept_shadow_fabric_candidate", "Waveguide layout optimization is accepted in shadow mode.")


def review_fabric_synthesis_packet(packet: Any) -> CourtPromotionDecision:
    """
    Evaluates a SovereignPacket containing all Level 31 synthesis evidence.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    payload = extract(packet, "payload", {}) or {}
    evidence = extract(packet, "evidence", {}) or {}
    gates = extract(payload, "gates_status", {}) or extract(evidence, "gates_status", {})
    
    errors = []
    
    if not gates.get("synthesis_spec_valid", False):
        errors.append("Invalid synthesis spec")
    if not gates.get("candidate_fabric_valid", False):
        errors.append("Invalid candidate fabric")
    if not gates.get("simd_core_bindings_complete", False):
        errors.append("Incomplete SIMD core bindings")
    if not gates.get("pml_boundaries_valid", False):
        errors.append("Invalid PML boundaries")
    if not gates.get("candidate_phase_table_separate", False):
        errors.append("Candidate phase tables not separated from active tables")
    if gates.get("oracle_match_if_available") is False or gates.get("oracle_match") is False:
        errors.append("Oracle mismatch blocks promotion")
    if gates.get("no_default_stepper_replacement") is False:
        errors.append("Prohibited default stepper replacement")
    if gates.get("no_production_fabric_mutation") is False:
        errors.append("Prohibited production fabric mutation")
        
    drift = extract(evidence, "phase_drift", 0.0)
    crosstalk = extract(evidence, "crosstalk", 0.0)
    reflection = extract(evidence, "boundary_reflection", 0.0)
    
    if drift > 0.05:
        errors.append(f"Phase drift {drift:.4f} exceeds 0.05")
    if crosstalk > 0.05:
        errors.append(f"Crosstalk {crosstalk:.4f} exceeds 0.05")
    if reflection > 0.05:
        errors.append(f"Boundary reflection {reflection:.4f} exceeds 0.05")
        
    if errors:
        reason = "; ".join(errors)
        if "crosstalk" in reason.lower() or "quarantine" in reason.lower():
            return CourtPromotionDecision(f"DEC_PROM_{int(time.time())}", "quarantine_candidate_fabric", f"Court quarantine: {reason}")
        if "oracle" in reason.lower() or "mutation" in reason.lower():
            return CourtPromotionDecision(f"DEC_PROM_{int(time.time())}", "reject_fabric_candidate", f"Court rejection: {reason}")
        return CourtPromotionDecision(f"DEC_PROM_{int(time.time())}", "needs_more_evidence", f"Court hold: {reason}")
        
    if extract(packet, "sandbox_trial", False) or extract(payload, "sandbox_trial", False) or extract(evidence, "sandbox_trial", False):
        return CourtPromotionDecision(f"DEC_PROM_{int(time.time())}", "authorize_sandbox_fabric_trial", "Authorized sandbox-only waveguide fabric trial.")
        
    return CourtPromotionDecision(f"DEC_PROM_{int(time.time())}", "promote_level31_candidate", "Waveguide fabric synthesis promoted to Level 31.")


def review_manifold_reshape_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a ManifoldReshapeReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed = extract(report, "validation_passed", True)
    errors = extract(report, "errors", []) or []
    
    # Also extract success from result
    result = extract(report, "result")
    if result:
        passed = passed and extract(result, "success", True)
        res_errors = extract(result, "errors", [])
        if res_errors:
            errors.extend(res_errors)

    if errors or not passed:
        reason = "; ".join(errors)
        if "distortion" in reason.lower():
            return CourtPromotionDecision(f"DEC_RESHAPE_{int(time.time())}", "quarantine_reshape_candidate", f"Court quarantine: {reason}")
        return CourtPromotionDecision(f"DEC_RESHAPE_{int(time.time())}", "reject_reshape_candidate", f"Reshape mapping failed: {reason}")
        
    return CourtPromotionDecision(f"DEC_RESHAPE_{int(time.time())}", "accept_shadow_reshape_candidate", "Manifold reshape is accepted in shadow mode.")


def review_pdm_carrier_relocation_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a PDMCarrierRelocationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed = extract(report, "validation_passed", True)
    qp_preserved = extract(report, "quadrature_pairing_preserved", True)
    li_preserved = extract(report, "lane_isolation_preserved", True)
    errors = extract(report, "errors", []) or []
    
    result = extract(report, "result")
    if result:
        passed = passed and extract(result, "success", True)
        res_errors = extract(result, "errors", [])
        if res_errors:
            errors.extend(res_errors)

    if errors or not passed:
        reason = "; ".join(errors)
        if not qp_preserved:
            return CourtPromotionDecision(f"DEC_CARRIER_{int(time.time())}", "quarantine_carrier", f"Carrier quarantine (quadrature broken): {reason}")
        if not li_preserved:
            return CourtPromotionDecision(f"DEC_CARRIER_{int(time.time())}", "reject_carrier_relocation", f"Carrier relocation rejected (lane isolation breach): {reason}")
        return CourtPromotionDecision(f"DEC_CARRIER_{int(time.time())}", "reject_carrier_relocation", f"Carrier relocation failed: {reason}")
        
    return CourtPromotionDecision(f"DEC_CARRIER_{int(time.time())}", "accept_shadow_reshape_candidate", "Carrier relocation is accepted in shadow mode.")


def review_carrier_registry_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a CarrierRegistryReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    leases_valid = extract(report, "leases_valid", True)
    snap_present = extract(report, "snapshot_present", True)
    errors = extract(report, "errors", []) or []

    if errors or not leases_valid or not snap_present:
        reason = "; ".join(errors) or "leases invalid or snapshot missing"
        return CourtPromotionDecision(f"DEC_REG_{int(time.time())}", "reject_carrier_relocation", f"Carrier registry audit failed: {reason}")
        
    return CourtPromotionDecision(f"DEC_REG_{int(time.time())}", "accept_shadow_reshape_candidate", "Carrier registry audit is accepted in shadow mode.")


def review_reshape_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Evaluates a SovereignPacket containing Level 32 reshape/relocation evidence.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    payload = extract(packet, "payload", {}) or {}
    evidence = extract(packet, "evidence", {}) or {}
    gates = extract(payload, "gates_status", {}) or extract(evidence, "gates_status", {})
    
    errors = []
    
    # Verify critical gates
    if not gates.get("source_shape_valid", False):
        errors.append("Invalid source shape")
    if not gates.get("target_shape_valid", False):
        errors.append("Invalid target shape")
    if not gates.get("coordinate_remap_complete", False):
        errors.append("Incomplete coordinate remap")
    if not gates.get("coordinate_remap_reversible_if_lossless", False):
        errors.append("Coordinate remap is not reversible")
    if not gates.get("reshape_plan_valid", False):
        errors.append("Invalid reshape plan")
    if not gates.get("carrier_registry_snapshot_present", False):
        errors.append("Missing carrier registry snapshot")
    if not gates.get("carrier_remap_table_complete", False):
        errors.append("Incomplete carrier remap table")
    if not gates.get("carrier_leases_valid", False):
        errors.append("Invalid carrier leases")
    if not gates.get("quadrature_pairing_preserved", False):
        errors.append("Broken quadrature pairing")
    if not gates.get("lane_bindings_preserved", False):
        errors.append("Broken lane bindings preservation")
    if not gates.get("simd_bindings_preserved", False):
        errors.append("Broken SIMD bindings preservation")
    if not gates.get("pml_boundaries_valid_after_reshape", False):
        errors.append("Invalid PML boundaries after reshape")
    if not gates.get("candidate_phase_table_separate", False):
        errors.append("Candidate phase tables not separate")
    if not gates.get("active_carrier_registry_not_overwritten", False):
        errors.append("Active carrier registry was overwritten")
    if gates.get("oracle_match_if_available") is False or gates.get("oracle_match") is False:
        errors.append("Oracle mismatch blocks promotion")
    if gates.get("no_production_reshape_or_carrier_mutation") is False:
        errors.append("Prohibited production reshape or carrier mutation")

    drift = extract(evidence, "phase_error", 0.0)
    crosstalk = extract(evidence, "crosstalk", 0.0)
    reflection = extract(evidence, "boundary_reflection", 0.0)
    
    if drift > 0.05:
        errors.append(f"Phase drift {drift:.4f} exceeds 0.05")
    if crosstalk > 0.05:
        errors.append(f"Crosstalk {crosstalk:.4f} exceeds 0.05")
    if reflection > 0.05:
        errors.append(f"Boundary reflection {reflection:.4f} exceeds 0.05")

    if errors:
        reason = "; ".join(errors)
        if "crosstalk" in reason.lower() or "quarantine" in reason.lower():
            if "carrier" in reason.lower():
                return CourtPromotionDecision(f"DEC_PROM_L32_{int(time.time())}", "quarantine_carrier", f"Court quarantine: {reason}")
            return CourtPromotionDecision(f"DEC_PROM_L32_{int(time.time())}", "quarantine_reshape_candidate", f"Court quarantine: {reason}")
        if "oracle" in reason.lower() or "mutation" in reason.lower():
            return CourtPromotionDecision(f"DEC_PROM_L32_{int(time.time())}", "reject_reshape_candidate", f"Court rejection: {reason}")
        return CourtPromotionDecision(f"DEC_PROM_L32_{int(time.time())}", "needs_more_evidence", f"Court hold: {reason}")

    if extract(packet, "sandbox_trial", False) or extract(payload, "sandbox_trial", False) or extract(evidence, "sandbox_trial", False):
        return CourtPromotionDecision(f"DEC_PROM_L32_{int(time.time())}", "authorize_sandbox_reshape_trial", "Authorized sandbox-only manifold reshape and carrier relocation trial.")

    return CourtPromotionDecision(f"DEC_PROM_L32_{int(time.time())}", "promote_level32_candidate", "Manifold reshape and carrier relocation promoted to Level 32.")


def review_cadence_stability_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a CadenceStabilityReport and issues a decision.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    stable = extract(report, "stable", True)
    global_skew = extract(report, "global_skew", 0.0)
    
    if global_skew > 0.10:
        return CourtPromotionDecision(
            decision_id=f"DEC_CAD_STAB_{int(time.time() * 1000)}",
            decision="quarantine_manifold_clock",
            justification=f"Critical timing instability: Global skew {global_skew:.4f} exceeded 0.10 threshold."
        )
    elif not stable or global_skew > 0.05:
        return CourtPromotionDecision(
            decision_id=f"DEC_CAD_STAB_{int(time.time() * 1000)}",
            decision="hold_cadence_epoch",
            justification=f"Timing drift observed: Global skew {global_skew:.4f} exceeded 0.05 threshold."
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_CAD_STAB_{int(time.time() * 1000)}",
        decision="accept_shadow_cadence_candidate",
        justification="Cadence stability is verified within normal tolerance bounds."
    )


def review_cadence_sync_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a CadenceSyncReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed_gates = extract(report, "passed_gates", True)
    global_skew = extract(report, "global_skew", 0.0)
    result = extract(report, "result")
    success = extract(result, "success", True) if result else True
    errors = extract(result, "errors", []) if result else []
    
    metadata = extract(report, "metadata", {}) or {}
    split_brain = metadata.get("split_brain") or metadata.get("split_brain_detected")
    
    if split_brain:
        return CourtPromotionDecision(
            decision_id=f"DEC_CAD_SYNC_{int(time.time() * 1000)}",
            decision="rollback_cadence_epoch",
            justification="Split-brain clock synchronization detected across manifolds; rolling back epoch."
        )
        
    if errors or not passed_gates or not success:
        reason = "; ".join(errors) if errors else "Synchronization gates failed"
        if "drift" in reason.lower() or global_skew > 0.10:
            return CourtPromotionDecision(
                decision_id=f"DEC_CAD_SYNC_{int(time.time() * 1000)}",
                decision="quarantine_manifold_clock",
                justification=f"Clock synchronization failure: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_CAD_SYNC_{int(time.time() * 1000)}",
            decision="hold_cadence_epoch",
            justification=f"Coherence timing hold: {reason}"
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_CAD_SYNC_{int(time.time() * 1000)}",
        decision="accept_shadow_cadence_candidate",
        justification="Cadence synchronization is verified stable."
    )


def review_transaction_cadence_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a TransactionCadenceReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    errors = extract(report, "errors", []) or []
    epoch = extract(report, "epoch")
    metadata = extract(epoch, "metadata", {}) if epoch else {}
    
    if metadata.get("split_brain") or metadata.get("split_brain_detected"):
         return CourtPromotionDecision(
            decision_id=f"DEC_TX_CAD_{int(time.time() * 1000)}",
            decision="rollback_cadence_epoch",
            justification="Split-brain state detected during epoch execution; triggering rollback."
         )
         
    if errors or not success:
        reason = "; ".join(errors)
        if "outside_cadence_window" in reason.lower() or "outside of approved cadence window" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_TX_CAD_{int(time.time() * 1000)}",
                decision="abort_cadence_epoch",
                justification=f"Transaction attempted outside approved cadence window: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_TX_CAD_{int(time.time() * 1000)}",
            decision="hold_cadence_epoch",
            justification=f"Epoch timing gates hold: {reason}"
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_TX_CAD_{int(time.time() * 1000)}",
        decision="accept_shadow_cadence_candidate",
        justification="Transaction cadence epoch verified successfully."
    )


def review_cadence_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Evaluates a SovereignPacket containing Level 33 timing cadence evidence.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    payload = extract(packet, "payload", {}) or {}
    evidence = extract(packet, "evidence", {}) or {}
    gates = extract(payload, "gates_status", {}) or extract(evidence, "gates_status", {})
    
    actor = extract(packet, "actor", "")
    if "Cadence" not in actor:
        return CourtPromotionDecision(
            decision_id=f"DEC_CAD_PROM_{int(time.time() * 1000)}",
            decision="needs_more_evidence",
            justification="Invalid ranger: Packet actor is not the Cadence Ranger."
        )

    errors = []
    
    if gates.get("cadence_profiles_valid") is False:
        errors.append("Invalid cadence profiles")
    if gates.get("cadence_sync_group_valid") is False:
        errors.append("Invalid sync group")
        
    drift = extract(evidence, "cadence_drift", 0.0)
    global_skew = extract(evidence, "global_skew", 0.0)
    
    if drift > 0.05 or global_skew > 0.05:
        errors.append(f"Cadence drift or global skew {max(drift, global_skew):.4f} exceeds 0.05 limit")
        
    if extract(evidence, "local_quorum_status") != "passed":
        errors.append("Local quorum check failed")
    if extract(evidence, "global_quorum_status") != "passed":
        errors.append("Global quorum check failed")
    if extract(evidence, "commit_barrier_status") != "satisfied":
        errors.append("Commit barrier unsatisfied")
        
    if extract(evidence, "propagation_timing_status") != "valid":
        errors.append("Invalid geodesic propagation timing")
        
    if extract(evidence, "wavefront_temporal_alignment_status") != "stable":
        errors.append("Unstable wavefront temporal alignment")
        
    if extract(evidence, "rollback_readiness") != "present":
        errors.append("Missing rollback snapshots references")
        
    if extract(evidence, "cadence_window_status") == "split_brain":
        errors.append("Split-brain clock synchronization detected")
        
    if gates.get("no_production_cadence_mutation") is False:
        errors.append("Prohibited production timing mutation")
        
    if errors:
        reason = "; ".join(errors)
        if "split_brain" in reason.lower() or "rollback" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_CAD_PROM_{int(time.time() * 1000)}",
                decision="rollback_cadence_epoch",
                justification=f"Court rollback due to timing errors: {reason}"
            )
        if "skew" in reason.lower() or "quarantine" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_CAD_PROM_{int(time.time() * 1000)}",
                decision="quarantine_manifold_clock",
                justification=f"Court clock quarantine: {reason}"
            )
        if "mutation" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_CAD_PROM_{int(time.time() * 1000)}",
                decision="reject_cadence_candidate",
                justification=f"Court rejection due to illegal mutation: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_CAD_PROM_{int(time.time() * 1000)}",
            decision="hold_cadence_epoch",
            justification=f"Court hold: {reason}"
        )
        
    if extract(packet, "sandbox_trial", False) or extract(payload, "sandbox_trial", False) or extract(evidence, "sandbox_trial", False):
        return CourtPromotionDecision(
            decision_id=f"DEC_CAD_PROM_{int(time.time() * 1000)}",
            decision="authorize_sandbox_cadence_trial",
            justification="Authorized sandbox-only timing cadence trial."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_CAD_PROM_{int(time.time() * 1000)}",
        decision="promote_level33_candidate",
        justification="Timing cadence and multi-manifold transaction consensus promoted to Level 33."
    )


def review_entangled_propagation_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates an EntangledPropagationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed_gates = extract(report, "passed_gates", True)
    result = extract(report, "result")
    success = extract(result, "success", True) if result else True
    errors = extract(result, "errors", []) if result else []
    
    if errors or not passed_gates or not success:
        reason = "; ".join(errors) if errors else "Propagation validation gates failed"
        if "pml" in reason.lower() or "boundary" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_PROP_{int(time.time() * 1000)}",
                decision="quarantine_manifold",
                justification=f"Boundary absorption failure: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_PROP_{int(time.time() * 1000)}",
            decision="hold_entangled_epoch",
            justification=f"Propagation timing hold: {reason}"
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_ENT_PROP_{int(time.time() * 1000)}",
        decision="accept_shadow_entangled_commit",
        justification="Entangled propagation is verified stable."
    )


def review_synchronized_commit_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a SynchronizedCommitReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed_gates = extract(report, "passed_gates", True)
    result = extract(report, "result")
    success = extract(result, "success", True) if result else True
    errors = extract(result, "errors", []) if result else []
    
    if errors or not passed_gates or not success:
        reason = "; ".join(errors) if errors else "Commit validation gates failed"
        if "split_brain" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_SEQ_COMM_{int(time.time() * 1000)}",
                decision="rollback_entangled_epoch",
                justification=f"Split-brain state detected; rolling back: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_SEQ_COMM_{int(time.time() * 1000)}",
            decision="hold_entangled_epoch",
            justification=f"Sequencer commit timing hold: {reason}"
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_SEQ_COMM_{int(time.time() * 1000)}",
        decision="accept_shadow_entangled_commit",
        justification="Synchronized sequencer commits are verified stable."
    )


def review_entangled_commit_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates an EntangledCommitReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    errors = extract(report, "errors", []) or []
    epoch = extract(report, "epoch")
    meta = extract(epoch, "metadata", {}) if epoch else {}
    if not meta:
        meta = extract(report, "metadata", {}) or {}
        
    if meta.get("split_brain") or meta.get("split_brain_detected"):
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_COMM_{int(time.time() * 1000)}",
            decision="rollback_entangled_epoch",
            justification="Split-brain state detected; triggering rollback."
        )
        
    if meta.get("quarantine_link"):
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_COMM_{int(time.time() * 1000)}",
            decision="quarantine_entanglement_link",
            justification="Timing drift detected; quarantining entanglement link."
        )
        
    if meta.get("quarantine_manifold"):
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_COMM_{int(time.time() * 1000)}",
            decision="quarantine_manifold",
            justification="Critical error; quarantining manifold clock."
        )
        
    if errors or not success:
        reason = "; ".join(errors)
        if "outside_cadence_window" in reason.lower() or "outside of approved cadence window" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_COMM_{int(time.time() * 1000)}",
                decision="abort_entangled_epoch",
                justification=f"Commit attempted outside approved window: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_COMM_{int(time.time() * 1000)}",
            decision="hold_entangled_epoch",
            justification=f"Entangled commit timing hold: {reason}"
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_ENT_COMM_{int(time.time() * 1000)}",
        decision="accept_shadow_entangled_commit",
        justification="Entangled commit epoch verified successfully."
    )


def review_entangled_commit_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Evaluates a SovereignPacket containing Level 34 timing evidence.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    payload = extract(packet, "payload", {}) or {}
    evidence = extract(packet, "evidence", {}) or {}
    gates = extract(payload, "gates_status", {}) or extract(evidence, "gates_status", {})
    
    actor = extract(packet, "actor", "")
    if "Entangled" not in actor:
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_PROM_{int(time.time() * 1000)}",
            decision="needs_more_evidence",
            justification="Invalid ranger: Packet actor is not the Entangled Commit Ranger."
        )

    errors = []
    
    if gates.get("coordination_group_valid") is False:
        errors.append("Invalid coordination group")
    if gates.get("cadence_group_valid") is False:
        errors.append("Invalid cadence sync group")
        
    drift = extract(evidence, "phase_drift", 0.0)
    crosstalk = extract(evidence, "crosstalk", 0.0)
    reflection = extract(evidence, "boundary_reflection", 0.0)
    coherence = extract(evidence, "entanglement_coherence", 1.0)
    
    if drift > 0.05 or crosstalk > 0.05 or reflection > 0.05 or coherence < 0.90:
        errors.append("Timing parameters exceed safety thresholds")
        
    if extract(evidence, "local_quorum_status") != "passed":
        errors.append("Local quorum check failed")
    if extract(evidence, "global_quorum_status") != "passed":
        errors.append("Global quorum check failed")
    if extract(evidence, "synchronized_commit_barrier_status") != "satisfied":
        errors.append("Synchronized commit barrier unsatisfied")
        
    if extract(evidence, "propagation_path_status") != "valid":
        errors.append("Invalid geodesic propagation path")
        
    if extract(evidence, "lock_boundary_status") == "deadlock_detected":
        errors.append("Cross-manifold deadlock detected")
        
    if extract(evidence, "rollback_readiness") != "present":
        errors.append("Missing rollback snapshots references")
        
    if extract(evidence, "cadence_status") == "split_brain":
        errors.append("Split-brain clock synchronization detected")
        
    if gates.get("no_production_commit_mutation") is False:
        errors.append("Prohibited production commit mutation")
        
    if errors:
        reason = "; ".join(errors)
        if "split_brain" in reason.lower() or "deadlock" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_PROM_{int(time.time() * 1000)}",
                decision="rollback_entangled_epoch",
                justification=f"Court rollback due to timing/lock errors: {reason}"
            )
        if "drift" in reason.lower() or "threshold" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_PROM_{int(time.time() * 1000)}",
                decision="quarantine_entanglement_link",
                justification=f"Court entanglement link quarantine: {reason}"
            )
        if "mutation" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_PROM_{int(time.time() * 1000)}",
                decision="reject_entangled_commit",
                justification=f"Court rejection due to illegal mutation: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_PROM_{int(time.time() * 1000)}",
            decision="hold_entangled_epoch",
            justification=f"Court hold: {reason}"
        )
        
    if extract(packet, "sandbox_trial", False) or extract(payload, "sandbox_trial", False) or extract(evidence, "sandbox_trial", False):
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_PROM_{int(time.time() * 1000)}",
            decision="authorize_sandbox_entangled_commit_trial",
            justification="Authorized sandbox-only entangled commit trial."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_ENT_PROM_{int(time.time() * 1000)}",
        decision="promote_level34_candidate",
        justification="Entangled propagation and synchronized commit timing promoted to Level 34."
    )


def review_entangled_calibration_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates an EntangledCalibrationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed_gates = extract(report, "passed_gates", True)
    result = extract(report, "result")
    success = extract(result, "success", True) if result else True
    errors = extract(result, "errors", []) if result else []

    if errors or not passed_gates or not success:
        reason = "; ".join(errors) if errors else "Calibration validation gates failed"
        if "phase" in reason.lower() or "drift" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_CAL_{int(time.time() * 1000)}",
                decision="hold_entangled_feedback_loop",
                justification=f"Calibration drift hold: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_CAL_{int(time.time() * 1000)}",
            decision="reject_entangled_feedback_loop",
            justification=f"Calibration failure: {reason}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_ENT_CAL_{int(time.time() * 1000)}",
        decision="accept_shadow_entangled_feedback",
        justification="Entangled calibration is verified stable."
    )


def review_entangled_feedback_loop_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates an EntangledFeedbackLoopReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed_gates = extract(report, "passed_gates", True)
    result = extract(report, "result")
    success = extract(result, "success", True) if result else True
    errors = extract(result, "errors", []) if result else []

    if errors or not passed_gates or not success:
        reason = "; ".join(errors) if errors else "Feedback loop validation gates failed"
        if "unstable" in reason.lower() or "diverge" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_FDBK_{int(time.time() * 1000)}",
                decision="rollback_entangled_feedback_loop",
                justification=f"Feedback loop unstable; triggering rollback: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_FDBK_{int(time.time() * 1000)}",
            decision="hold_entangled_feedback_loop",
            justification=f"Feedback loop timing hold: {reason}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_ENT_FDBK_{int(time.time() * 1000)}",
        decision="accept_shadow_entangled_feedback",
        justification="Entangled feedback loop is verified stable."
    )


def review_entangled_stability_control_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates an EntangledStabilityControlReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    state = extract(report, "state", "stable")
    suggestions = extract(report, "suggestions", []) or []

    # If any quarantine suggestion is present, recommend quarantine
    for sug in suggestions:
        action = extract(sug, "action")
        if action == "quarantine_manifold":
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_STAB_{int(time.time() * 1000)}",
                decision="quarantine_manifold",
                justification="Stability control recommends quarantining manifold."
            )
        elif action == "quarantine_entanglement_link":
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_STAB_{int(time.time() * 1000)}",
                decision="quarantine_entanglement_link",
                justification="Stability control recommends quarantining entanglement link."
            )
        elif action == "rollback_feedback_loop":
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_STAB_{int(time.time() * 1000)}",
                decision="rollback_entangled_feedback_loop",
                justification="Stability control recommends rolling back feedback loop."
            )

    if state == "unstable":
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_STAB_{int(time.time() * 1000)}",
            decision="hold_entangled_feedback_loop",
            justification="Stability control state classified as unstable."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_ENT_STAB_{int(time.time() * 1000)}",
        decision="accept_shadow_entangled_feedback",
        justification="Entangled stability state is nominal."
    )


def review_entangled_feedback_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Evaluates a SovereignPacket containing Level 35 calibration/feedback evidence.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    payload = extract(packet, "payload", {}) or {}
    evidence = extract(packet, "evidence", {}) or {}
    gates = extract(payload, "gates_status", {}) or extract(evidence, "gates_status", {})
    if not gates:
        gates = {k: v for k, v in extract(packet, "invariants_checked", {}).items()} if isinstance(extract(packet, "invariants_checked"), dict) else {}
        
    actor = extract(packet, "actor", "")
    if "Feedback" not in actor:
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_FBP_{int(time.time() * 1000)}",
            decision="needs_more_evidence",
            justification="Invalid ranger: Packet actor is not the Entangled Feedback Ranger."
        )

    errors = []
    
    # 1. Check baseline
    if extract(evidence, "calibration_baseline_status") != "present":
        errors.append("Missing calibration baseline telemetry")
        
    # 2. Check drift, crosstalk, reflection bounds
    phase_drift = extract(evidence, "phase_drift_after", 0.0)
    cadence_drift = extract(evidence, "cadence_drift_after", 0.0)
    carrier_error = extract(evidence, "carrier_phase_error_after", 0.0)
    crosstalk = extract(evidence, "crosstalk_after", 0.0)
    reflection = extract(evidence, "boundary_reflection_after", 0.0)
    
    if phase_drift > 0.05:
        errors.append(f"Phase drift {phase_drift} exceeds threshold 0.05")
    if cadence_drift > 0.05:
        errors.append(f"Cadence drift {cadence_drift} exceeds threshold 0.05")
    if carrier_error > 0.05:
        errors.append(f"Carrier phase error {carrier_error} exceeds threshold 0.05")
    if crosstalk > 0.05:
        errors.append(f"Crosstalk {crosstalk} exceeds threshold 0.05")
    if reflection > 0.05:
        errors.append(f"Boundary reflection {reflection} exceeds threshold 0.05")
        
    # 3. Check active mass preservation
    if not extract(evidence, "active_mass_preservation", True):
        errors.append("Active mass preservation violated")
        
    # 4. Check rollback/synchronized commit
    if extract(evidence, "synchronized_commit_readiness") != "stable":
        errors.append("Synchronized commits not blocked during unstable feedback")
    if extract(evidence, "rollback_status") == "missing":
        errors.append("Missing rollback path references")

    if crosstalk > 0.05:
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_FBP_{int(time.time() * 1000)}",
            decision="quarantine_entanglement_link",
            justification=f"Court quarantine due to high crosstalk: {crosstalk}"
        )
    if reflection > 0.05:
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_FBP_{int(time.time() * 1000)}",
            decision="hold_entangled_feedback_loop",
            justification=f"Court hold due to boundary reflection breach: {reflection}"
        )

    if errors:
        reason = "; ".join(errors)
        if "rollback" in reason.lower() or "unstable" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_ENT_FBP_{int(time.time() * 1000)}",
                decision="rollback_entangled_feedback_loop",
                justification=f"Court rollback due to loop errors: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_FBP_{int(time.time() * 1000)}",
            decision="hold_entangled_feedback_loop",
            justification=f"Court hold due to calibration/feedback errors: {reason}"
        )
        
    if extract(packet, "sandbox_trial", False) or extract(payload, "sandbox_trial", False) or extract(evidence, "sandbox_trial", False):
        return CourtPromotionDecision(
            decision_id=f"DEC_ENT_FBP_{int(time.time() * 1000)}",
            decision="authorize_sandbox_entangled_feedback_trial",
            justification="Authorized sandbox-only entangled feedback trial."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_ENT_FBP_{int(time.time() * 1000)}",
        decision="promote_level35_candidate",
        justification="Entangled wavefront calibration and feedback loops promoted to Level 35."
    )


def review_sovereign_runtime_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a SovereignRuntimeReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed_gates = extract(report, "passed_gates", True)
    result = extract(report, "result")
    success = extract(result, "success", True) if result else True
    errors = extract(result, "errors", []) if result else []

    if errors or not passed_gates or not success:
        reason = "; ".join(errors) if errors else "Runtime validation gates failed"
        return CourtPromotionDecision(
            decision_id=f"DEC_RUN_{int(time.time() * 1000)}",
            decision="hold_runtime",
            justification=f"Runtime hold: {reason}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RUN_{int(time.time() * 1000)}",
        decision="accept_shadow_runtime",
        justification="Sovereign runtime is verified stable."
    )


def review_levelup_sequence_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a LevelUpSequenceReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", True)
    errors = extract(report, "errors", [])

    if errors or not success:
        reason = "; ".join(errors) if errors else "Sequence dependency checks failed"
        if "cycle" in reason.lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_SEQ_{int(time.time() * 1000)}",
                decision="reject_runtime_sequence",
                justification=f"Sequence reject due to cycle: {reason}"
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_SEQ_{int(time.time() * 1000)}",
            decision="hold_runtime",
            justification=f"Sequence hold: {reason}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_SEQ_{int(time.time() * 1000)}",
        decision="accept_shadow_runtime",
        justification="Level-up sequence is verified stable."
    )


def review_runtime_governance_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates a RuntimeGovernanceReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    policy_satisfied = extract(report, "policy_satisfied", True)
    decision_obj = extract(report, "decision")
    decision = extract(decision_obj, "decision", "continue_shadow") if decision_obj else "continue_shadow"

    if not policy_satisfied or decision in ["reject_sequence", "quarantine_step", "rollback_step"]:
        return CourtPromotionDecision(
            decision_id=f"DEC_GOV_{int(time.time() * 1000)}",
            decision="reject_runtime_sequence",
            justification="Runtime governance policy check failed."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_GOV_{int(time.time() * 1000)}",
        decision="accept_shadow_runtime",
        justification="Runtime governance checks passed."
    )


def authorize_runtime_sandbox_step(sequence: Any, token_request: Any) -> CourtPromotionDecision:
    """
    Issues a court decision authorizing a sandbox runtime step execution lease.
    """
    import uuid
    token_id = f"AUTH_TOK_{uuid.uuid4().hex[:8]}"
    return CourtPromotionDecision(
        decision_id=token_id,
        decision="authorize_sandbox_runtime_step",
        justification="Authorized sandbox-only runtime execution step."
    )


def review_sovereign_runtime_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Evaluates a SovereignPacket containing Level 36 runtime evidence.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    payload = extract(packet, "payload", {}) or {}
    evidence = extract(packet, "evidence", {}) or {}
    gates = extract(payload, "gates_status", {}) or extract(evidence, "gates_status", {})
    if not gates:
        gates = {k: v for k, v in extract(packet, "invariants_checked", {}).items()} if isinstance(extract(packet, "invariants_checked"), dict) else {}

    errors = []
    
    # 1. Check ledger completeness
    if extract(evidence, "ledger_completeness") != "complete":
        errors.append("Missing runtime ledger logging history")
        
    # 2. Check unresolved quarantine
    if extract(evidence, "quarantine_count", 0) > 0 or extract(evidence, "runtime_mode") == "quarantine":
        return CourtPromotionDecision(
            decision_id=f"DEC_RUN_RNG_{int(time.time() * 1000)}",
            decision="quarantine_runtime_step",
            justification="Court quarantine due to unresolved runtime flags."
        )
        
    if extract(evidence, "runtime_mode") == "production":
        return CourtPromotionDecision(
            decision_id=f"DEC_RUN_RNG_{int(time.time() * 1000)}",
            decision="reject_runtime_sequence",
            justification="Court rejection due to production mode execution attempt."
        )

    # 3. Check rollback reference presence
    if extract(evidence, "rollback_count", 0) == 0 and extract(evidence, "runtime_mode") == "sandbox":
        errors.append("Missing rollback path references for sandbox step execution")

    # 4. Check general gates
    if not extract(evidence, "promotion_readiness", False):
        errors.append("General security gates validation failed")

    if errors:
        reason = "; ".join(errors)
        return CourtPromotionDecision(
            decision_id=f"DEC_RUN_RNG_{int(time.time() * 1000)}",
            decision="hold_runtime",
            justification=f"Court hold due to runtime gates failure: {reason}"
        )

    if extract(packet, "sandbox_trial", False) or extract(payload, "sandbox_trial", False) or extract(evidence, "sandbox_trial", False):
        return CourtPromotionDecision(
            decision_id=f"DEC_RUN_RNG_{int(time.time() * 1000)}",
            decision="authorize_sandbox_runtime_step",
            justification="Authorized sandbox-only runtime trial step execution."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RUN_RNG_{int(time.time() * 1000)}",
        decision="promote_level36_candidate",
        justification="Sovereign execution runtime and scheduled level-up sequence promoted to Level 36."
    )


def review_hierarchical_waveguide_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates the waveguide topology and validation status from report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    valid = extract(report, "valid", False)
    errors = extract(report, "errors", []) or []
    
    if not valid:
        return CourtPromotionDecision(
            decision_id=f"DEC_HW_{int(time.time() * 1000)}",
            decision="reject_waveguide_arithmetic",
            justification=f"Hierarchical waveguide topology validation failed: {'; '.join(errors)}"
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_HW_{int(time.time() * 1000)}",
        decision="accept_shadow_waveguide_arithmetic",
        justification="Hierarchical waveguide topology and clusters are structurally valid."
    )


def review_interlane_prefix_carry_report(report: Any) -> CourtPromotionDecision:
    """
    Evaluates prefix carry tree validation and correctness.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    success = extract(report, "success", False)
    errors = extract(report, "errors", []) or []
    
    if not success:
        return CourtPromotionDecision(
            decision_id=f"DEC_PC_{int(time.time() * 1000)}",
            decision="reject_waveguide_arithmetic",
            justification=f"Interlane prefix carry execution failed: {'; '.join(errors)}"
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_PC_{int(time.time() * 1000)}",
        decision="accept_shadow_waveguide_arithmetic",
        justification="Interlane prefix carry tree is valid and execution matches correctness constraints."
    )


def review_waveguide_arithmetic_report(report: Any) -> CourtPromotionDecision:
    """
    Performs the final Promotion Court review of waveguide arithmetic.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    success = extract(report, "success", False)
    oracle_match = extract(report, "oracle_match", False)
    errors = extract(report, "errors", []) or []
    meta = extract(report, "metadata", {}) or {}
    
    if not oracle_match:
        return CourtPromotionDecision(
            decision_id=f"DEC_WA_{int(time.time() * 1000)}",
            decision="reject_waveguide_arithmetic",
            justification="Arithmetic oracle match failed: output does not match python reference."
        )
        
    if meta.get("quarantine_bridge"):
        return CourtPromotionDecision(
            decision_id=f"DEC_WA_{int(time.time() * 1000)}",
            decision="quarantine_carry_bridge",
            justification="Excessive reflection or crosstalk detected on inter-lane carry bridge."
        )
    if meta.get("quarantine_cluster"):
        return CourtPromotionDecision(
            decision_id=f"DEC_WA_{int(time.time() * 1000)}",
            decision="quarantine_waveguide_cluster",
            justification="Excessive drift or instability in waveguide cluster."
        )
        
    if meta.get("needs_more_evidence") or not success:
        return CourtPromotionDecision(
            decision_id=f"DEC_WA_{int(time.time() * 1000)}",
            decision="needs_more_evidence",
            justification=f"Execution plan requires further calibration or telemetry evidence: {'; '.join(errors)}"
        )
        
    if meta.get("sandbox_trial"):
        return CourtPromotionDecision(
            decision_id=f"DEC_WA_{int(time.time() * 1000)}",
            decision="authorize_sandbox_waveguide_arithmetic_trial",
            justification="Authorized sandbox waveguide arithmetic trial."
        )
        
    if meta.get("promotion_ready"):
        return CourtPromotionDecision(
            decision_id=f"DEC_WA_{int(time.time() * 1000)}",
            decision="promote_level37_candidate",
            justification="Hierarchical waveguide fabric and inter-lane prefix-carry arithmetic promoted to Level 37."
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_WA_{int(time.time() * 1000)}",
        decision="accept_shadow_waveguide_arithmetic",
        justification="Waveguide arithmetic shadow pipeline completed successfully."
    )


def review_waveguide_arithmetic_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Evaluates a SovereignPacket containing Level 37 waveguide arithmetic evidence.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    payload = extract(packet, "payload", {}) or {}
    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    
    if rec == "quarantine":
        quar_rec = evidence.get("quarantine_recommendation")
        if quar_rec == "quarantine_carry_bridge":
            return CourtPromotionDecision(
                decision_id=f"DEC_WA_RNG_{int(time.time() * 1000)}",
                decision="quarantine_carry_bridge",
                justification="Court quarantine on inter-lane carry bridge per ranger recommendation."
            )
        else:
            return CourtPromotionDecision(
                decision_id=f"DEC_WA_RNG_{int(time.time() * 1000)}",
                decision="quarantine_waveguide_cluster",
                justification="Court quarantine on waveguide cluster per ranger recommendation."
            )
            
    if rec == "reject":
        return CourtPromotionDecision(
            decision_id=f"DEC_WA_RNG_{int(time.time() * 1000)}",
            decision="reject_waveguide_arithmetic",
            justification="Court rejection on waveguide arithmetic per ranger recommendation."
        )
        
    if extract(packet, "sandbox_trial", False) or evidence.get("sandbox_trial"):
        return CourtPromotionDecision(
            decision_id=f"DEC_WA_RNG_{int(time.time() * 1000)}",
            decision="authorize_sandbox_waveguide_arithmetic_trial",
            justification="Authorized sandbox waveguide arithmetic trial step execution."
        )
        
    if evidence.get("promotion_readiness"):
        return CourtPromotionDecision(
            decision_id=f"DEC_WA_RNG_{int(time.time() * 1000)}",
            decision="promote_level37_candidate",
            justification="Hierarchical waveguide fabric and inter-lane prefix-carry arithmetic promoted to Level 37."
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_WA_RNG_{int(time.time() * 1000)}",
        decision="accept_shadow_waveguide_arithmetic",
        justification="Ranger evidence and shadow waveguide arithmetic accepted."
    )


def review_entangled_wavefront_consensus_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews the entangled wavefront consensus report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    success = extract(report, "success", False)
    meta = extract(report, "metadata", {}) or {}
    
    if not success:
        if meta.get("quarantine_link"):
            return CourtPromotionDecision(
                decision_id=f"DEC_EWC_{int(time.time() * 1000)}",
                decision="quarantine_entanglement_link",
                justification="Consensus failed; quarantine requested on entanglement link."
            )
        elif meta.get("quarantine_manifold"):
            return CourtPromotionDecision(
                decision_id=f"DEC_EWC_{int(time.time() * 1000)}",
                decision="quarantine_manifold",
                justification="Consensus failed; quarantine requested on manifold."
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_EWC_{int(time.time() * 1000)}",
            decision="reject_atomic_commit",
            justification="Consensus failed; reject atomic commit."
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_EWC_{int(time.time() * 1000)}",
        decision="accept_shadow_atomic_consensus",
        justification="Entangled wavefront consensus report accepted in shadow mode."
    )


def review_multimanifold_atomic_commit_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews the multi-manifold atomic commit report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    success = extract(report, "passed_gates", False) or extract(report, "success", False)
    result = extract(report, "result")
    if result:
        success = extract(result, "success", False)
        
    meta = extract(report, "metadata", {}) or {}
    
    if not success:
        if meta.get("cross_manifold_deadlock"):
            return CourtPromotionDecision(
                decision_id=f"DEC_MMAC_{int(time.time() * 1000)}",
                decision="rollback_atomic_epoch",
                justification="Cross-manifold deadlock detected; epoch rollback required."
            )
        if meta.get("missing_rollback_snapshot") or meta.get("missing_rollback_snapshot_for"):
            return CourtPromotionDecision(
                decision_id=f"DEC_MMAC_{int(time.time() * 1000)}",
                decision="reject_atomic_commit",
                justification="Missing rollback snapshot; reject commit epoch."
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_MMAC_{int(time.time() * 1000)}",
            decision="abort_atomic_epoch",
            justification="Multi-manifold atomic commit checks failed; aborting epoch."
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_MMAC_{int(time.time() * 1000)}",
        decision="accept_shadow_atomic_consensus",
        justification="Multi-manifold atomic commit report accepted in shadow mode."
    )


def review_entangled_atomic_epoch_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews the entangled atomic epoch report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    success = extract(report, "success", False)
    meta = extract(extract(report, "epoch"), "metadata", {}) or {}
    
    if not success:
        if meta.get("split_brain") or meta.get("split_brain_detected"):
            return CourtPromotionDecision(
                decision_id=f"DEC_EAE_{int(time.time() * 1000)}",
                decision="abort_atomic_epoch",
                justification="Split-brain timing detected; aborting commit epoch."
            )
        if meta.get("hold_epoch") or meta.get("hold"):
            return CourtPromotionDecision(
                decision_id=f"DEC_EAE_{int(time.time() * 1000)}",
                decision="hold_atomic_epoch",
                justification="Unsatisfied checkpoints or conditions; holding epoch."
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_EAE_{int(time.time() * 1000)}",
            decision="rollback_atomic_epoch",
            justification="Atomic epoch failed; recommending rollback."
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_EAE_{int(time.time() * 1000)}",
        decision="promote_level38_candidate",
        justification="Entangled atomic epoch checks passed; recommend Level 38 promotion."
    )


def review_atomic_consensus_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews the atomic consensus ranger packet.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    
    if rec == "quarantine":
        quar_rec = evidence.get("quarantine_recommendation")
        if quar_rec == "quarantine_atomic_participant":
            return CourtPromotionDecision(
                decision_id=f"DEC_AC_RNG_{int(time.time() * 1000)}",
                decision="quarantine_atomic_participant",
                justification="Court quarantine on participant per ranger recommendation."
            )
        elif quar_rec == "quarantine_entanglement_link":
            return CourtPromotionDecision(
                decision_id=f"DEC_AC_RNG_{int(time.time() * 1000)}",
                decision="quarantine_entanglement_link",
                justification="Court quarantine on entanglement link per ranger recommendation."
            )
        else:
            return CourtPromotionDecision(
                decision_id=f"DEC_AC_RNG_{int(time.time() * 1000)}",
                decision="quarantine_manifold",
                justification="Court quarantine on manifold per ranger recommendation."
            )
            
    if rec == "reject":
        return CourtPromotionDecision(
            decision_id=f"DEC_AC_RNG_{int(time.time() * 1000)}",
            decision="reject_atomic_commit",
            justification="Court rejection on atomic commit per ranger recommendation."
        )
        
    if extract(packet, "sandbox_trial", False) or evidence.get("sandbox_trial"):
        return CourtPromotionDecision(
            decision_id=f"DEC_AC_RNG_{int(time.time() * 1000)}",
            decision="authorize_sandbox_atomic_commit_trial",
            justification="Authorized sandbox atomic commit trial step execution."
        )
        
    if evidence.get("promotion_readiness"):
        return CourtPromotionDecision(
            decision_id=f"DEC_AC_RNG_{int(time.time() * 1000)}",
            decision="promote_level38_candidate",
            justification="Entangled wavefront consensus and atomic commit promoted to Level 38."
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_AC_RNG_{int(time.time() * 1000)}",
        decision="accept_shadow_atomic_consensus",
        justification="Ranger evidence and shadow atomic consensus accepted."
    )


def review_state_relocation_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a state relocation report and returns a CourtPromotionDecision.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed = extract(report, "passed_gates", False)
    res = extract(report, "result")
    errors = extract(res, "errors", []) or []
    
    if not passed or errors:
        if "deadlock" in "".join(errors).lower():
            return CourtPromotionDecision(
                decision_id=f"DEC_SR_{int(time.time() * 1000)}",
                decision="quarantine_manifold",
                justification="State relocation report shows cross-manifold deadlock."
            )
        if "rollback" in "".join(errors).lower() or (res and extract(res, "rolled_back")):
            return CourtPromotionDecision(
                decision_id=f"DEC_SR_{int(time.time() * 1000)}",
                decision="rollback_state_relocation",
                justification="State relocation report failed; recommending rollback."
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_SR_{int(time.time() * 1000)}",
            decision="reject_state_relocation",
            justification=f"State relocation report failed with errors: {', '.join(errors)}"
        )

    plan = extract(report, "plan")
    intent = extract(plan, "intent") if plan else None
    meta = extract(intent, "metadata", {}) or {} if intent else {}
    if not isinstance(meta, dict):
        meta = {}
        
    if meta.get("sandbox_trial"):
        return CourtPromotionDecision(
            decision_id=f"DEC_SR_{int(time.time() * 1000)}",
            decision="authorize_sandbox_state_relocation_trial",
            justification="State relocation trial step approved in sandbox mode."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_SR_{int(time.time() * 1000)}",
        decision="accept_shadow_state_relocation",
        justification="State relocation checks passed in shadow mode."
    )


def review_realtime_calibration_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a real-time calibration report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed = extract(report, "passed_gates", False)
    res = extract(report, "result")
    errors = extract(res, "errors", []) or []

    if not passed or errors:
        if "crosstalk" in "".join(errors).lower() or (res and extract(res, "quarantined")):
            return CourtPromotionDecision(
                decision_id=f"DEC_RTC_{int(time.time() * 1000)}",
                decision="quarantine_manifold",
                justification="High crosstalk or quarantine triggered in calibration."
            )
        if "rollback" in "".join(errors).lower() or (res and extract(res, "rolled_back")):
            return CourtPromotionDecision(
                decision_id=f"DEC_RTC_{int(time.time() * 1000)}",
                decision="rollback_state_relocation",
                justification="Calibration loop failed; recommending rollback."
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_RTC_{int(time.time() * 1000)}",
            decision="reject_state_relocation",
            justification=f"Real-time calibration loop failed: {', '.join(errors)}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RTC_{int(time.time() * 1000)}",
        decision="accept_shadow_state_relocation",
        justification="Real-time calibration loop checks passed."
    )


def review_relocation_protocol_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a relocation protocol report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed = extract(report, "passed_gates", False) or extract(report, "success", False)
    res = extract(report, "result") or extract(report, "protocol")
    errors = extract(report, "errors", []) or []
    if res and not errors:
        errors = extract(res, "errors", []) or []

    if not passed or errors:
        protocol = extract(report, "protocol") or res
        abort_state = extract(protocol, "abort_state")
        if (res and extract(res, "rolled_back")) or (abort_state and extract(abort_state, "rollback_triggered")):
            return CourtPromotionDecision(
                decision_id=f"DEC_RP_{int(time.time() * 1000)}",
                decision="rollback_state_relocation",
                justification="Relocation protocol rolled back."
            )
        if (res and extract(res, "aborted")) or (abort_state and extract(abort_state, "aborted")):
            return CourtPromotionDecision(
                decision_id=f"DEC_RP_{int(time.time() * 1000)}",
                decision="abort_state_relocation",
                justification="Relocation protocol aborted."
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_RP_{int(time.time() * 1000)}",
            decision="reject_state_relocation",
            justification=f"Relocation protocol checks failed: {', '.join(errors)}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RP_{int(time.time() * 1000)}",
        decision="accept_shadow_state_relocation",
        justification="Relocation protocol checks passed."
    )


def review_state_relocation_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews the state relocation ranger packet and issues a final verdict/decision.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    
    if rec == "quarantine":
        if evidence.get("quarantine_state_ref") or evidence.get("quarantine_state"):
            return CourtPromotionDecision(
                decision_id=f"DEC_SR_RNG_{int(time.time() * 1000)}",
                decision="quarantine_state_ref",
                justification="Quarantine state reference per ranger recommendation."
            )
        else:
            return CourtPromotionDecision(
                decision_id=f"DEC_SR_RNG_{int(time.time() * 1000)}",
                decision="quarantine_manifold",
                justification="Quarantine manifold per ranger recommendation."
            )
            
    if rec == "reject":
        if evidence.get("rollback_readiness") == "present" and (evidence.get("partial_relocation_risk") or evidence.get("state_hash_status") == "failed"):
            return CourtPromotionDecision(
                decision_id=f"DEC_SR_RNG_{int(time.time() * 1000)}",
                decision="rollback_state_relocation",
                justification="Relocation failed; rollback recommended."
            )
        return CourtPromotionDecision(
            decision_id=f"DEC_SR_RNG_{int(time.time() * 1000)}",
            decision="reject_state_relocation",
            justification="State relocation rejected per ranger recommendation."
        )

    if evidence.get("promotion_readiness"):
        if (evidence.get("state_hash_status") == "passed" and 
            evidence.get("rollback_readiness") == "present" and
            evidence.get("quorum_status") == "passed" and
            evidence.get("lock_boundary_status") == "valid" and
            evidence.get("calibration_loop_status") == "stable" and
            evidence.get("wavefront_coherence", 0.0) >= 0.90 and
            not evidence.get("partial_relocation_risk") and
            evidence.get("cadence_status") == "valid"):
            
            return CourtPromotionDecision(
                decision_id=f"DEC_SR_RNG_{int(time.time() * 1000)}",
                decision="promote_level39_candidate",
                justification="All Level 39 requirements satisfied; recommend Promotion."
            )
        else:
            return CourtPromotionDecision(
                decision_id=f"DEC_SR_RNG_{int(time.time() * 1000)}",
                decision="needs_more_evidence",
                justification="Promotion readiness is set, but details lack required proofs."
            )

    return CourtPromotionDecision(
        decision_id=f"DEC_SR_RNG_{int(time.time() * 1000)}",
        decision="accept_shadow_state_relocation",
        justification="Ranger evidence and shadow state relocation accepted."
    )


def review_relocation_fault_matrix_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a RelocationFaultMatrixReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    if not success:
        return CourtPromotionDecision(
            decision_id=f"DEC_RFM_{int(time.time() * 1000)}",
            decision="reject_level40_candidate",
            justification="Relocation fault matrix checks failed."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RFM_{int(time.time() * 1000)}",
        decision="accept_shadow_fault_matrix",
        justification="Relocation fault matrix checks passed."
    )


def review_calibration_fault_matrix_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a CalibrationFaultMatrixReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    if not success:
        return CourtPromotionDecision(
            decision_id=f"DEC_CFM_{int(time.time() * 1000)}",
            decision="reject_level40_candidate",
            justification="Calibration fault matrix checks failed."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_CFM_{int(time.time() * 1000)}",
        decision="accept_shadow_fault_matrix",
        justification="Calibration fault matrix checks passed."
    )


def review_rollback_proof_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a RollbackProofReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    if not success:
        return CourtPromotionDecision(
            decision_id=f"DEC_RBP_{int(time.time() * 1000)}",
            decision="rollback_fault_candidate",
            justification="Rollback proof checks failed; recommending rollback."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RBP_{int(time.time() * 1000)}",
        decision="accept_shadow_fault_matrix",
        justification="Rollback proof checks passed."
    )


def review_safety_oracle_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a RelocationSafetyOracleReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    agreement = extract(report, "agreement", True)
    if not agreement:
        return CourtPromotionDecision(
            decision_id=f"DEC_SO_{int(time.time() * 1000)}",
            decision="needs_more_evidence",
            justification="Safety oracle agreement failure."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_SO_{int(time.time() * 1000)}",
        decision="accept_shadow_fault_matrix",
        justification="Safety oracle agreement checks passed."
    )


def review_fault_matrix_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews a fault matrix ranger SovereignPacket.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    
    if rec == "reject" or not evidence.get("promotion_readiness"):
        return CourtPromotionDecision(
            decision_id=f"DEC_FMR_{int(time.time() * 1000)}",
            decision="reject_level40_candidate",
            justification="Ranger recommended rejection or gates did not pass."
        )

    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    
    if rec == "reject" or not evidence.get("promotion_readiness"):
        return CourtPromotionDecision(
            decision_id=f"DEC_FMR_{int(time.time() * 1000)}",
            decision="reject_level40_candidate",
            justification="Ranger recommended rejection or gates did not pass."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_FMR_{int(time.time() * 1000)}",
        decision="promote_level40_candidate",
        justification="All Level 40 requirements satisfied; recommend Promotion."
    )


def review_transactional_route_optimization_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a TransactionalRouteOptimizationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    if not success:
        return CourtPromotionDecision(
            decision_id=f"DEC_TRO_{int(time.time() * 1000)}",
            decision="reject_route_candidate",
            justification="Route optimization report checks failed."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_TRO_{int(time.time() * 1000)}",
        decision="accept_shadow_route_rebalance",
        justification="Route optimization report checks passed."
    )


def review_waveguide_rebalance_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a WaveguideRebalanceReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    errors = extract(report, "errors", []) or []
    if not success:
        if any("PML" in e for e in errors):
            dec = "quarantine_route"
        elif any("prefix-carry" in e for e in errors):
            dec = "quarantine_manifold"
        else:
            dec = "reject_route_candidate"
        return CourtPromotionDecision(
            decision_id=f"DEC_WGR_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Waveguide rebalance report checks failed: {'; '.join(errors)}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_WGR_{int(time.time() * 1000)}",
        decision="accept_shadow_route_rebalance",
        justification="Waveguide rebalance report checks passed."
    )


def review_route_rebalance_protocol_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a RouteRebalanceProtocolReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    errors = extract(report, "errors", []) or []
    if not success:
        if any("lock" in e.lower() for e in errors):
            dec = "hold_route_rebalance"
        elif any("cadence" in e.lower() for e in errors):
            dec = "needs_more_evidence"
        elif any("rollback" in e.lower() for e in errors):
            dec = "rollback_route_rebalance"
        elif any("safety oracle" in e.lower() for e in errors):
            dec = "reject_route_candidate"
        else:
            dec = "rollback_route_rebalance"
        return CourtPromotionDecision(
            decision_id=f"DEC_RRP_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Protocol checks failed: {'; '.join(errors)}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RRP_{int(time.time() * 1000)}",
        decision="accept_shadow_route_rebalance",
        justification="Route rebalance protocol checks passed."
    )


def review_waveguide_rebalance_oracle_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a WaveguideRebalanceOracleReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    agreement = extract(report, "agreement", True)
    if not agreement:
        return CourtPromotionDecision(
            decision_id=f"DEC_WSO_{int(time.time() * 1000)}",
            decision="needs_more_evidence",
            justification="Safety oracle agreement checks failed."
        )

    decision = extract(report, "decision")
    verdict = extract(decision, "verdict", "accept_shadow")
    if verdict == "accept_shadow":
        court_dec = "accept_shadow_route_rebalance"
    else:
        # Map oracle verdict directly to court decision
        court_dec = verdict

    return CourtPromotionDecision(
        decision_id=f"DEC_WSO_{int(time.time() * 1000)}",
        decision=court_dec,
        justification=f"Safety oracle checks completed with verdict: {verdict}"
    )


def review_route_rebalance_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews a RouteRebalanceRanger SovereignPacket.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    
    if rec == "quarantine" or not evidence.get("promotion_readiness"):
        # Map failure reasons
        lock_status = evidence.get("lock_boundary_status")
        cadence_status = evidence.get("cadence_status")
        wavefront_coh = evidence.get("wavefront_coherence")
        crosstalk = evidence.get("crosstalk")
        boundary_reflection = evidence.get("boundary_reflection")
        rollback = evidence.get("rollback_readiness")
        carrier = evidence.get("carrier_preservation_status")
        prefix_carry = evidence.get("prefix_carry_preservation_status")
        
        if crosstalk == "breached":
            dec = "quarantine_waveguide_segment"
        elif boundary_reflection == "breached":
            dec = "quarantine_route"
        elif wavefront_coh == "unstable":
            dec = "quarantine_manifold"
        elif rollback == "missing":
            dec = "rollback_route_rebalance"
        elif lock_status == "invalid":
            dec = "hold_route_rebalance"
        elif cadence_status == "invalid":
            dec = "hold_route_rebalance"
        elif carrier == "violated" or prefix_carry == "violated":
            dec = "reject_route_candidate"
        else:
            dec = "quarantine_route"

        return CourtPromotionDecision(
            decision_id=f"DEC_RRR_{int(time.time() * 1000)}",
            decision=dec,
            justification="Route rebalance ranger packet gates failed."
        )

    # Check for sandbox token authorization request
    metadata = extract(packet, "metadata", {}) or {}
    if metadata.get("sandbox_trial", True):
        return CourtPromotionDecision(
            decision_id=f"DEC_RRR_{int(time.time() * 1000)}",
            decision="promote_level41_candidate",
            justification="Route rebalance ranger packet checks passed. Authorized Level 41 promotion."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RRR_{int(time.time() * 1000)}",
        decision="promote_level41_candidate",
        justification="Route rebalance ranger packet checks passed."
    )







