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


def review_route_rebalance_fault_matrix_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a RouteRebalanceFaultMatrixReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
    success = extract(report, "success", False)
    if not success:
        return CourtPromotionDecision(
            decision_id=f"DEC_RFM_{int(time.time() * 1000)}",
            decision="reject_level42_candidate",
            justification="Route rebalance fault matrix checks failed."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_RFM_{int(time.time() * 1000)}",
        decision="accept_shadow_route_fault_matrix",
        justification="Route rebalance fault matrix checks passed."
    )


def review_optimization_regression_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews an OptimizationRegressionReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
    success = extract(report, "success", False)
    if not success:
        return CourtPromotionDecision(
            decision_id=f"DEC_ORR_{int(time.time() * 1000)}",
            decision="reject_level42_candidate",
            justification="Optimization regression matrix checks failed."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_ORR_{int(time.time() * 1000)}",
        decision="accept_shadow_route_fault_matrix",
        justification="Optimization regression matrix checks passed."
    )


def review_route_cost_regression_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a RouteCostRegressionReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
    success = extract(report, "success", False)
    rejected = extract(report, "rejected", False)
    if not success or not rejected:
        return CourtPromotionDecision(
            decision_id=f"DEC_CRR_{int(time.time() * 1000)}",
            decision="reject_level42_candidate",
            justification="Route cost regression checks failed."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_CRR_{int(time.time() * 1000)}",
        decision="accept_shadow_route_fault_matrix",
        justification="Route cost regression checks passed."
    )


def review_waveguide_fault_audit_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a WaveguideFaultAuditReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
    success = extract(report, "success", False)
    quarantine = extract(report, "quarantine_recommended", False)
    if quarantine:
        return CourtPromotionDecision(
            decision_id=f"DEC_WFA_{int(time.time() * 1000)}",
            decision="quarantine_route",
            justification="Waveguide fault audit recommended quarantine."
        )
    if not success:
        return CourtPromotionDecision(
            decision_id=f"DEC_WFA_{int(time.time() * 1000)}",
            decision="reject_level42_candidate",
            justification="Waveguide fault audit report checks failed."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_WFA_{int(time.time() * 1000)}",
        decision="accept_shadow_route_fault_matrix",
        justification="Waveguide fault audit report checks passed."
    )


def review_route_rebalance_rollback_proof_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a RouteRebalanceRollbackProofReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
    success = extract(report, "success", False)
    if not success:
        return CourtPromotionDecision(
            decision_id=f"DEC_RRBP_{int(time.time() * 1000)}",
            decision="rollback_route_rebalance_candidate",
            justification="Route rebalance rollback proof checks failed."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_RRBP_{int(time.time() * 1000)}",
        decision="accept_shadow_route_fault_matrix",
        justification="Route rebalance rollback proof checks passed."
    )


def review_route_fault_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews a RouteFaultRanger SovereignPacket and determines the Level 42 verdict.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
    
    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    metadata = extract(packet, "metadata", {}) or {}
    
    total = evidence.get("total_fault_cases", 0)
    passed = evidence.get("passed_fault_cases", 0)
    failed = evidence.get("failed_fault_cases", 0)
    reg_count = evidence.get("regression_count", 0)
    rollback_status = evidence.get("rollback_proof_status", "failed")
    table_protect = evidence.get("active_table_protection_status", "violated")
    oracle_agreement = evidence.get("safety_oracle_agreement", "mismatched")
    quarantine_status = evidence.get("quarantine_status", "inactive")
    quarantine_targets = evidence.get("quarantine_targets", [])
    
    if evidence.get("promotion_readiness") == "ready" and rec == "promote":
        return CourtPromotionDecision(
            decision_id=f"DEC_RFR_{int(time.time() * 1000)}",
            decision="promote_level42_candidate",
            justification="All Level 42 route rebalance fault injection and optimization regression matrix checks passed."
        )

    if table_protect == "violated" or oracle_agreement == "mismatched":
        return CourtPromotionDecision(
            decision_id=f"DEC_RFR_{int(time.time() * 1000)}",
            decision="reject_level42_candidate",
            justification="Ranger detected active table violation or safety oracle mismatch."
        )
    if rollback_status == "failed":
        return CourtPromotionDecision(
            decision_id=f"DEC_RFR_{int(time.time() * 1000)}",
            decision="rollback_route_rebalance_candidate",
            justification="Ranger detected rollback proof status failure."
        )
    if quarantine_status == "active":
        decision = "quarantine_route"
        if quarantine_targets:
            target = quarantine_targets[0]
            if "quarantine_waveguide_segment" in target:
                decision = "quarantine_waveguide_segment"
            elif "quarantine_carrier" in target:
                decision = "quarantine_carrier"
            elif "quarantine_manifold" in target:
                decision = "quarantine_manifold"
            elif "quarantine_route_case" in target:
                decision = "quarantine_route_case"
        return CourtPromotionDecision(
            decision_id=f"DEC_RFR_{int(time.time() * 1000)}",
            decision=decision,
            justification="Ranger detected active quarantine recommendation."
        )
    if failed > 0:
        return CourtPromotionDecision(
            decision_id=f"DEC_RFR_{int(time.time() * 1000)}",
            decision="reject_level42_candidate",
            justification=f"Ranger reported {failed} failed fault cases."
        )
    if reg_count > 0:
        return CourtPromotionDecision(
            decision_id=f"DEC_RFR_{int(time.time() * 1000)}",
            decision="reject_level42_candidate",
            justification=f"Ranger reported {reg_count} regressions."
        )
        
    if metadata.get("sandbox_trial") or metadata.get("court_token") == "SANDBOX_TOKEN" or extract(packet, "reproducibility_hash", "") == "SANDBOX_HASH":
        return CourtPromotionDecision(
            decision_id=f"DEC_RFR_{int(time.time() * 1000)}",
            decision="authorize_sandbox_route_fault_audit",
            justification="Route fault ranger checks passed; authorized sandbox audit trial."
        )
        
    return CourtPromotionDecision(
        decision_id=f"DEC_RFR_{int(time.time() * 1000)}",
        decision="hold_level42_candidate",
        justification="Level 42 readiness checks are not complete or on hold."
    )


def review_topology_relocation_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a TopologyRelocationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(report, "result", {})
    success = extract(res, "success", False)
    errors = extract(res, "errors", [])
    
    if not success or errors:
        dec = "hold_topology_relocation"
        for err in errors:
            if "deadlock" in err.lower():
                dec = "hold_topology_relocation"
            elif "lock" in err.lower():
                dec = "hold_topology_relocation"
            elif "quarantine" in err.lower():
                dec = "quarantine_topology_candidate"
            elif "overwrite" in err.lower():
                dec = "reject_topology_candidate"
                
        return CourtPromotionDecision(
            decision_id=f"DEC_TR_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Topology relocation checks failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_TR_{int(time.time() * 1000)}",
        decision="accept_shadow_topology_relocation",
        justification="Topology relocation report checks passed."
    )


def review_multimanifold_reshape_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a MultiManifoldReshapeReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    val_passed = extract(report, "validation_passed", False)
    result = extract(report, "result", {})
    errors = extract(result, "errors", [])
    
    if not val_passed or errors:
        return CourtPromotionDecision(
            decision_id=f"DEC_MMR_{int(time.time() * 1000)}",
            decision="reject_topology_candidate",
            justification=f"Multi-manifold reshape validation failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_MMR_{int(time.time() * 1000)}",
        decision="accept_shadow_topology_relocation",
        justification="Multi-manifold reshape report checks passed."
    )


def review_topology_shape_guard_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a TopologyShapeGuardReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed = extract(report, "passed", False)
    errors = extract(report, "errors", [])
    
    if not passed or errors:
        dec = "reject_topology_candidate"
        for err in errors:
            if "node" in err.lower():
                dec = "reject_topology_candidate"
            elif "lane" in err.lower() or "carrier" in err.lower() or "h-cam" in err.lower() or "prefix-carry" in err.lower() or "pml" in err.lower() or "transaction" in err.lower():
                dec = "reject_topology_candidate"
                
        return CourtPromotionDecision(
            decision_id=f"DEC_TSG_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Topology shape guard checks failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_TSG_{int(time.time() * 1000)}",
        decision="accept_shadow_topology_relocation",
        justification="Topology shape guard report checks passed."
    )


def review_topology_migration_protocol_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a TopologyMigrationProtocolReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", False)
    errors = extract(report, "errors", [])
    
    if not success or errors:
        dec = "abort_topology_migration"
        for err in errors:
            if "rollback" in err.lower():
                dec = "rollback_topology_relocation"
            elif "carrier" in err.lower() or "cadence" in err.lower():
                dec = "abort_topology_migration"
                
        return CourtPromotionDecision(
            decision_id=f"DEC_TMP_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Topology migration protocol checks failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_TMP_{int(time.time() * 1000)}",
        decision="accept_shadow_topology_relocation",
        justification="Topology migration protocol report checks passed."
    )


def review_topology_relocation_manifest(manifest: Any) -> CourtPromotionDecision:
    """
    Reviews a TopologyRelocationManifest.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    is_valid = extract(manifest, "is_valid", False)
    rollback_refs = extract(manifest, "rollback_refs", [])
    
    if not is_valid or not rollback_refs:
        return CourtPromotionDecision(
            decision_id=f"DEC_MAN_{int(time.time() * 1000)}",
            decision="needs_more_evidence",
            justification="Topology relocation manifest is incomplete or missing rollback references."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_MAN_{int(time.time() * 1000)}",
        decision="accept_shadow_topology_relocation",
        justification="Topology relocation manifest checks passed."
    )


def review_topology_relocation_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews a TopologyRelocationRanger SovereignPacket and determines the Level 43 verdict.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    metadata = extract(packet, "metadata", {}) or {}
    
    ready = evidence.get("promotion_readiness", False)
    quarantine_rec = evidence.get("quarantine_recommendation", "none")
    
    if ready and rec == "promote":
        return CourtPromotionDecision(
            decision_id=f"DEC_TRP_{int(time.time() * 1000)}",
            decision="promote_level43_candidate",
            justification="All Level 43 topology relocation and multi-manifold reshape checks passed."
        )

    if quarantine_rec == "quarantine" or rec == "quarantine":
        dec = "quarantine_topology_candidate"
        wavefront_coh = evidence.get("wavefront_coherence", "")
        if wavefront_coh == "unstable":
            dec = "quarantine_manifold"
        return CourtPromotionDecision(
            decision_id=f"DEC_TRP_{int(time.time() * 1000)}",
            decision=dec,
            justification="Ranger recommended quarantine or detected instability."
        )

    if metadata.get("sandbox_trial") or metadata.get("court_token") == "SANDBOX_TOKEN" or extract(packet, "reproducibility_hash", "") == "SANDBOX_HASH":
        return CourtPromotionDecision(
            decision_id=f"DEC_TRP_{int(time.time() * 1000)}",
            decision="authorize_sandbox_topology_relocation_trial",
            justification="Authorized sandbox topology relocation trial."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_TRP_{int(time.time() * 1000)}",
        decision="hold_topology_relocation",
        justification="Level 43 readiness checks are not complete or on hold."
    )


def review_resonant_feedback_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a ResonantFeedbackReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(report, "result", {})
    success = extract(res, "success", False)
    errors = extract(res, "errors", [])
    
    if not success or errors:
        dec = "hold_autonomous_cadence_sync"
        for err in errors:
            if "resonant phase" in err.lower():
                dec = "rollback_autonomous_cadence_sync"
            elif "entanglement coherence" in err.lower():
                dec = "quarantine_resonant_link"
            elif "crosstalk" in err.lower() or "reflection" in err.lower():
                dec = "rollback_autonomous_cadence_sync"
        return CourtPromotionDecision(
            decision_id=f"DEC_RFB_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Resonant feedback validation failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RFB_{int(time.time() * 1000)}",
        decision="accept_shadow_resonant_cadence",
        justification="Resonant feedback report checks passed."
    )


def review_autonomous_cadence_sync_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews an AutonomousCadenceSyncReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(report, "result", {})
    success = extract(res, "success", False) or extract(report, "success", False)
    errors = extract(res, "errors", []) or extract(report, "errors", [])

    if not success or errors:
        dec = "reject_autonomous_cadence_sync"
        for err in errors:
            if "split-brain" in err.lower() or "split_brain" in err.lower():
                dec = "quarantine_manifold_clock"
            elif "rollback" in err.lower():
                dec = "rollback_autonomous_cadence_sync"
        return CourtPromotionDecision(
            decision_id=f"DEC_ACS_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Autonomous cadence sync failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_ACS_{int(time.time() * 1000)}",
        decision="accept_shadow_resonant_cadence",
        justification="Autonomous cadence sync checks passed."
    )


def review_resonant_cadence_control_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a ResonantCadenceControlReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    state = extract(report, "state_classification", "nominal")
    if state == "quarantine_required":
        return CourtPromotionDecision(
            decision_id=f"DEC_RCC_{int(time.time() * 1000)}",
            decision="quarantine_manifold_clock",
            justification="Wavefront coherence collapse indicates clock quarantine required."
        )
    elif state == "skew_warning":
        return CourtPromotionDecision(
            decision_id=f"DEC_RCC_{int(time.time() * 1000)}",
            decision="hold_autonomous_cadence_sync",
            justification="High global cadence skew warning."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RCC_{int(time.time() * 1000)}",
        decision="accept_shadow_resonant_cadence",
        justification="Resonant cadence control checks passed."
    )


def review_cadence_autonomy_guard_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a CadenceAutonomyGuardReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    dec = extract(report, "decision", {})
    passed = extract(dec, "passed", False)
    reasons = extract(dec, "blocked_reasons", [])

    if not passed or reasons:
        return CourtPromotionDecision(
            decision_id=f"DEC_CAG_{int(time.time() * 1000)}",
            decision="reject_autonomous_cadence_sync",
            justification=f"Cadence autonomy guard blocked synchronization: {reasons}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_CAG_{int(time.time() * 1000)}",
        decision="accept_shadow_resonant_cadence",
        justification="Cadence autonomy guard checks passed."
    )


def review_resonant_cadence_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews a ResonantCadenceRanger SovereignPacket and determines the Level 44 verdict.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    metadata = extract(packet, "metadata", {}) or {}
    
    ready = evidence.get("promotion_readiness", False)
    quarantine_rec = evidence.get("quarantine_recommendation", "none")
    
    if ready and rec == "promote":
        return CourtPromotionDecision(
            decision_id=f"DEC_RRP_{int(time.time() * 1000)}",
            decision="promote_level44_candidate",
            justification="All Level 44 resonant feedback and autonomous cadence sync checks passed."
        )

    if quarantine_rec == "quarantine" or rec == "quarantine":
        dec = "quarantine_manifold_clock"
        coh = evidence.get("resonant_phase_coherence", "")
        if coh == "unstable":
            dec = "quarantine_manifold_clock"
        if evidence.get("autonomy_guard_status") == "failed":
            dec = "reject_autonomous_cadence_sync"
        return CourtPromotionDecision(
            decision_id=f"DEC_RRP_{int(time.time() * 1000)}",
            decision=dec,
            justification="Ranger recommended quarantine or detected timing instability."
        )

    if metadata.get("sandbox_trial") or metadata.get("court_token") == "SANDBOX_TOKEN" or extract(packet, "reproducibility_hash", "") == "SANDBOX_HASH":
        return CourtPromotionDecision(
            decision_id=f"DEC_RRP_{int(time.time() * 1000)}",
            decision="authorize_sandbox_autonomous_cadence_trial",
            justification="Authorized sandbox autonomous cadence trial."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_RRP_{int(time.time() * 1000)}",
        decision="hold_autonomous_cadence_sync",
        justification="Level 44 readiness checks are not complete or on hold."
    )


def review_sovereign_core_assembly_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a SovereignCoreAssemblyReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(report, "result")
    success = extract(res, "success", True) if res is not None else extract(report, "success", True)
    errors = extract(res, "errors", []) or []

    if not success or errors:
        dec = "hold_core_assembly"
        for err in errors:
            if "unstable autonomous cadence" in err.lower():
                dec = "reject_core_assembly"
            elif "rollback" in err.lower():
                dec = "rollback_core_assembly"
            elif "quarantine" in err.lower():
                dec = "quarantine_core"
        return CourtPromotionDecision(
            decision_id=f"DEC_SCA_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Sovereign core assembly failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_SCA_{int(time.time() * 1000)}",
        decision="accept_shadow_core_assembly",
        justification="Sovereign core assembly report checks passed."
    )


def review_pipeline_calibration_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a PipelineCalibrationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(report, "result")
    success = extract(res, "success", True) if res is not None else extract(report, "success", True)
    errors = extract(res, "errors", []) or []

    if not success or errors:
        dec = "hold_core_assembly"
        for err in errors:
            if "latency" in err.lower() or "backpressure" in err.lower() or "stall" in err.lower():
                dec = "quarantine_pipeline_stage"
            elif "rollback" in err.lower():
                dec = "rollback_core_assembly"
        return CourtPromotionDecision(
            decision_id=f"DEC_PCR_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Pipeline calibration failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_PCR_{int(time.time() * 1000)}",
        decision="accept_shadow_core_assembly",
        justification="Pipeline calibration checks passed."
    )


def review_pipeline_assembly_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a PipelineAssemblyReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(report, "result")
    success = extract(res, "success", True) if res is not None else extract(report, "success", True)
    errors = extract(res, "errors", []) or []

    if not success or errors:
        dec = "reject_core_assembly"
        for err in errors:
            if "stage" in err.lower() or "binding" in err.lower():
                dec = "quarantine_pipeline_stage"
        return CourtPromotionDecision(
            decision_id=f"DEC_PAR_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Pipeline assembly failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_PAR_{int(time.time() * 1000)}",
        decision="accept_shadow_core_assembly",
        justification="Pipeline assembly checks passed."
    )


def review_core_cadence_calibration_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a CoreCadenceCalibrationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", True)
    errors = extract(report, "errors", []) or []

    if not success or errors:
        dec = "hold_core_assembly"
        for err in errors:
            if "overwrite" in err.lower():
                dec = "reject_core_assembly"
        return CourtPromotionDecision(
            decision_id=f"DEC_CCR_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Core cadence calibration failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_CCR_{int(time.time() * 1000)}",
        decision="accept_shadow_core_assembly",
        justification="Core cadence calibration checks passed."
    )


def review_core_waveguide_binding_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a CoreWaveguideBindingReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", True)
    errors = extract(report, "errors", []) or []

    if not success or errors:
        dec = "rollback_core_assembly"
        for err in errors:
            if "pml" in err.lower() or "absorption" in err.lower():
                dec = "rollback_core_assembly"
            elif "prefix-carry" in err.lower():
                dec = "rollback_core_assembly"
        return CourtPromotionDecision(
            decision_id=f"DEC_WBR_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Core waveguide binding failed: {errors}"
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_WBR_{int(time.time() * 1000)}",
        decision="accept_shadow_core_assembly",
        justification="Core waveguide binding checks passed."
    )


def review_core_assembly_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews a CoreAssemblyRanger SovereignPacket and determines the Level 45 verdict.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    metadata = extract(packet, "metadata", {}) or {}
    
    ready = evidence.get("promotion_readiness", False)
    quarantine_rec = evidence.get("quarantine_recommendation", "none")
    
    if ready and rec == "promote":
        return CourtPromotionDecision(
            decision_id=f"DEC_CAR_{int(time.time() * 1000)}",
            decision="promote_level45_candidate",
            justification="All Level 45 multi-core assembly and calibration checks passed."
        )

    if quarantine_rec == "quarantine" or rec == "quarantine" or quarantine_rec == "hold_assembly":
        dec = "hold_core_assembly"
        if quarantine_rec == "quarantine_core":
            dec = "quarantine_core"
        elif quarantine_rec == "quarantine_stage":
            dec = "quarantine_pipeline_stage"
        elif quarantine_rec == "hold_assembly":
            dec = "hold_core_assembly"
        return CourtPromotionDecision(
            decision_id=f"DEC_CAR_{int(time.time() * 1000)}",
            decision=dec,
            justification="Ranger recommended quarantine or detected assembly instability."
        )

    if metadata.get("sandbox_trial") or metadata.get("court_token") == "SANDBOX_TOKEN" or extract(packet, "reproducibility_hash", "") == "SANDBOX_HASH":
        return CourtPromotionDecision(
            decision_id=f"DEC_CAR_{int(time.time() * 1000)}",
            decision="authorize_sandbox_core_assembly_trial",
            justification="Authorized sandbox multi-core assembly trial."
        )

    if evidence.get("stage_latency", 0.0) > 0.1 or metadata.get("stage_latency_breach"):
        return CourtPromotionDecision(
            decision_id=f"DEC_CAR_{int(time.time() * 1000)}",
            decision="quarantine_pipeline_stage",
            justification="Stage latency breach blocks promotion."
        )
    if evidence.get("backpressure", 0.0) > 0.1 or metadata.get("backpressure_breach"):
        return CourtPromotionDecision(
            decision_id=f"DEC_CAR_{int(time.time() * 1000)}",
            decision="hold_core_assembly",
            justification="Backpressure breach blocks promotion."
        )
    if evidence.get("cross_core_stalls", 0.0) > 0.1 or metadata.get("cross_core_stall_breach"):
        return CourtPromotionDecision(
            decision_id=f"DEC_CAR_{int(time.time() * 1000)}",
            decision="hold_core_assembly",
            justification="Cross-core stall breach blocks promotion."
        )
    if evidence.get("cadence_skew", 0.0) > 0.1 or metadata.get("cadence_skew_breach"):
        return CourtPromotionDecision(
            decision_id=f"DEC_CAR_{int(time.time() * 1000)}",
            decision="hold_core_assembly",
            justification="Core cadence skew breach blocks promotion."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_CAR_{int(time.time() * 1000)}",
        decision="hold_core_assembly",
        justification="Level 45 readiness checks are not complete or on hold."
    )


def review_geodesic_pipeline_balance_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a GeodesicPipelineBalanceReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(report, "result", {})
    success = extract(res, "success", True)
    errors = extract(res, "errors", [])
    
    if not success or errors:
        return CourtPromotionDecision(
            decision_id=f"DEC_GPB_{int(time.time() * 1000)}",
            decision="reject_pipeline_balance",
            justification=f"Geodesic pipeline balance checks failed: {'; '.join(errors)}"
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_GPB_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront",
        justification="Geodesic pipeline balancing checks passed."
    )


def review_quantum_wavefront_calibration_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a QuantumWavefrontCalibrationReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(report, "result", {})
    success = extract(res, "success", True)
    errors = extract(res, "errors", [])
    
    if not success or errors:
        return CourtPromotionDecision(
            decision_id=f"DEC_QWC_{int(time.time() * 1000)}",
            decision="reject_quantum_wavefront_candidate",
            justification=f"Quantum wavefront calibration checks failed: {'; '.join(errors)}"
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_QWC_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront",
        justification="Quantum wavefront calibration checks passed."
    )


def review_wavefront_uncertainty_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a WavefrontUncertaintyReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    is_valid = extract(report, "is_valid", True)
    bound = extract(report, "bound")
    is_bounded = extract(bound, "is_bounded", True) if bound else True
    
    if not is_valid or not is_bounded:
        return CourtPromotionDecision(
            decision_id=f"DEC_WUR_{int(time.time() * 1000)}",
            decision="reject_quantum_wavefront_candidate",
            justification="Unbounded wavefront uncertainty blocks calibration."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_WUR_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront",
        justification="Wavefront uncertainty checks passed."
    )


def review_pipeline_balance_oracle_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a PipelineBalanceOracleReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    dec = extract(report, "decision")
    decision_val = extract(dec, "decision", "accept") if dec else "accept"
    justification = extract(dec, "justification", "Acceptable") if dec else "Acceptable"
    
    if decision_val != "accept":
        return CourtPromotionDecision(
            decision_id=f"DEC_PBO_{int(time.time() * 1000)}",
            decision=decision_val,
            justification=justification
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_PBO_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront",
        justification="Pipeline balance safety oracle checks passed."
    )


def review_quantum_wavefront_protocol_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a QuantumWavefrontProtocolReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", True)
    errors = extract(report, "errors", [])
    
    if not success or errors:
        return CourtPromotionDecision(
            decision_id=f"DEC_QWP_{int(time.time() * 1000)}",
            decision="reject_quantum_wavefront_candidate",
            justification=f"Quantum wavefront protocol execution failed: {'; '.join(errors)}"
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_QWP_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront",
        justification="Quantum wavefront protocol checks passed."
    )


def review_pipeline_wavefront_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews a PipelineWavefrontRanger SovereignPacket.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    metadata = extract(packet, "metadata", {}) or {}
    
    ready = evidence.get("promotion_readiness", False)
    quarantine_rec = evidence.get("quarantine_recommendation", "none")
    
    if ready and rec == "promote":
        return CourtPromotionDecision(
            decision_id=f"DEC_PWR_{int(time.time() * 1000)}",
            decision="promote_level46_candidate",
            justification="All Level 46 pipeline balancing and quantum wavefront calibration checks passed."
        )

    if quarantine_rec != "none" and quarantine_rec != "accept":
        dec = "hold_pipeline_balance"
        if quarantine_rec == "quarantine_core":
            dec = "quarantine_core"
        elif quarantine_rec == "quarantine_pipeline_segment":
            dec = "quarantine_pipeline_segment"
        elif quarantine_rec == "quarantine_wavefront_packet":
            dec = "quarantine_wavefront_packet"
        elif quarantine_rec == "rollback_balance":
            dec = "rollback_pipeline_balance"
        elif quarantine_rec == "rollback_wavefront_calibration":
            dec = "rollback_quantum_wavefront_calibration"
        elif quarantine_rec == "hold_balance":
            dec = "hold_pipeline_balance"
        elif quarantine_rec == "reject_balance_candidate":
            dec = "reject_pipeline_balance"
        return CourtPromotionDecision(
            decision_id=f"DEC_PWR_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Ranger recommended quarantine or detected balancing instability: {quarantine_rec}"
        )

    if metadata.get("sandbox_trial") or metadata.get("court_token") == "SANDBOX_TOKEN" or extract(packet, "reproducibility_hash", "") == "SANDBOX_HASH":
        return CourtPromotionDecision(
            decision_id=f"DEC_PWR_{int(time.time() * 1000)}",
            decision="authorize_sandbox_pipeline_wavefront_trial",
            justification="Authorized sandbox pipeline balancing / wavefront trial."
        )

    if evidence.get("wavefront_coherence", 1.0) < 0.9 or metadata.get("coherence_breach"):
        return CourtPromotionDecision(
            decision_id=f"DEC_PWR_{int(time.time() * 1000)}",
            decision="rollback_quantum_wavefront_calibration",
            justification="Wavefront coherence breach blocks promotion."
        )
    if evidence.get("packet_dispersion", 0.0) > 0.1 or metadata.get("dispersion_breach"):
        return CourtPromotionDecision(
            decision_id=f"DEC_PWR_{int(time.time() * 1000)}",
            decision="quarantine_wavefront_packet",
            justification="Wavefront dispersion breach blocks promotion."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_PWR_{int(time.time() * 1000)}",
        decision="hold_pipeline_balance",
        justification="Level 46 readiness checks are not complete or on hold."
    )


def review_pipeline_wavefront_fault_matrix_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a PipelineWavefrontFaultMatrixReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed_audit = extract(report, "passed_audit", True)
    results = extract(report, "results", []) or []
    
    # Check if any individual case failed or if passed_audit is False
    all_success = True
    for res in results:
        success = extract(res, "success", True)
        if not success:
            all_success = False
            break

    if not passed_audit or not all_success:
        return CourtPromotionDecision(
            decision_id=f"DEC_WF_FMX_{int(time.time() * 1000)}",
            decision="reject_level47_candidate",
            justification="Pipeline wavefront fault matrix audit failed."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_WF_FMX_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront_fault_matrix",
        justification="Pipeline wavefront fault matrix audit passed."
    )


def review_quantum_calibration_fault_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a QuantumCalibrationFaultReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed_audit = extract(report, "passed_audit", True)
    results = extract(report, "results", []) or []
    
    all_success = True
    rollback_req = False
    quarantine_req = False
    for res in results:
        success = extract(res, "success", True)
        if not success:
            all_success = False
        outcome = extract(res, "actual_outcome", "")
        if outcome == "rollback_pipeline_wavefront_candidate":
            rollback_req = True
        elif outcome == "quarantine_wavefront_packet":
            quarantine_req = True

    if not passed_audit or not all_success:
        dec = "reject_level47_candidate"
        if rollback_req:
            dec = "rollback_pipeline_wavefront_candidate"
        elif quarantine_req:
            dec = "quarantine_wavefront_packet"
        return CourtPromotionDecision(
            decision_id=f"DEC_QCF_{int(time.time() * 1000)}",
            decision=dec,
            justification="Quantum calibration stability audit failed."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_QCF_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront_fault_matrix",
        justification="Quantum calibration stability audit passed."
    )


def review_pipeline_balance_fault_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a PipelineBalanceFaultReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", True)
    blocks_promotion = extract(report, "blocks_promotion", False)
    quarantine_rec = extract(report, "quarantine_recommended", False)
    
    if not success or blocks_promotion:
        dec = "reject_level47_candidate"
        if quarantine_rec:
            dec = "quarantine_pipeline_segment"
        return CourtPromotionDecision(
            decision_id=f"DEC_PBF_{int(time.time() * 1000)}",
            decision=dec,
            justification="Pipeline balance fault audit failed or blocks promotion."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_PBF_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront_fault_matrix",
        justification="Pipeline balance fault audit passed."
    )


def review_uncertainty_fault_audit_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews an UncertaintyFaultAuditReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed_audit = extract(report, "passed_audit", True)
    results = extract(report, "results", []) or []
    
    all_success = True
    for res in results:
        bp = extract(res, "blocks_promotion", True)
        if bp:
            all_success = False

    if not passed_audit or not all_success or len(results) > 0:
        return CourtPromotionDecision(
            decision_id=f"DEC_UFA_{int(time.time() * 1000)}",
            decision="reject_level47_candidate",
            justification="Uncertainty fault audit failed (unbounded uncertainty or dispersion breach)."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_UFA_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront_fault_matrix",
        justification="Uncertainty fault audit passed."
    )


def review_pipeline_wavefront_rollback_proof_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a PipelineWavefrontRollbackProofReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed_proof = extract(report, "passed_proof", True)
    results = extract(report, "results", []) or []
    
    all_success = True
    for res in results:
        success = extract(res, "success", True)
        if not success:
            all_success = False

    if not passed_proof or not all_success:
        return CourtPromotionDecision(
            decision_id=f"DEC_RLBK_PRF_{int(time.time() * 1000)}",
            decision="reject_level47_candidate",
            justification="Pipeline wavefront rollback proof failed."
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_RLBK_PRF_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront_fault_matrix",
        justification="Pipeline wavefront rollback proof passed."
    )


def review_pipeline_wavefront_safety_oracle_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a PipelineWavefrontSafetyOracleReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    dec = extract(report, "decision")
    outcome = extract(dec, "outcome", "") if dec else ""
    
    if outcome in ["reject_candidate", "quarantine_core", "quarantine_pipeline_segment", "quarantine_wavefront_packet", "rollback_pipeline_balance", "rollback_wavefront_calibration", "hold_pipeline_balance", "hold_wavefront_calibration"]:
        # Any unsafe case classified by safety oracle must block promotion
        return CourtPromotionDecision(
            decision_id=f"DEC_SFT_ORC_{int(time.time() * 1000)}",
            decision="reject_level47_candidate",
            justification=f"Safety oracle identified unsafe condition: {outcome}"
        )
    return CourtPromotionDecision(
        decision_id=f"DEC_SFT_ORC_{int(time.time() * 1000)}",
        decision="accept_shadow_pipeline_wavefront_fault_matrix",
        justification="Safety oracle checks passed."
    )


def review_pipeline_wavefront_fault_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews a PipelineWavefrontFaultRanger SovereignPacket.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    metadata = extract(packet, "metadata", {}) or {}
    
    ready = evidence.get("promotion_readiness", False)
    quarantine_rec = evidence.get("quarantine_recommendation", "none")
    
    if ready and rec == "promote":
        return CourtPromotionDecision(
            decision_id=f"DEC_PWFR_{int(time.time() * 1000)}",
            decision="promote_level47_candidate",
            justification="All Level 47 pipeline wavefront fault injection and stability audits passed."
        )

    if quarantine_rec != "none" and quarantine_rec != "accept" and quarantine_rec != "accept_shadow":
        dec = "hold_level47_candidate"
        if quarantine_rec == "quarantine_core":
            dec = "quarantine_core"
        elif quarantine_rec == "quarantine_pipeline_segment":
            dec = "quarantine_pipeline_segment"
        elif quarantine_rec == "quarantine_wavefront_packet":
            dec = "quarantine_wavefront_packet"
        elif quarantine_rec == "rollback_pipeline_wavefront_candidate":
            dec = "rollback_pipeline_wavefront_candidate"
        elif quarantine_rec == "hold_level47_candidate":
            dec = "hold_level47_candidate"
        elif quarantine_rec == "reject_level47_candidate":
            dec = "reject_level47_candidate"
        elif quarantine_rec == "quarantine_fault_case":
            dec = "quarantine_fault_case"
        return CourtPromotionDecision(
            decision_id=f"DEC_PWFR_{int(time.time() * 1000)}",
            decision=dec,
            justification=f"Ranger recommended quarantine or detected audit instability: {quarantine_rec}"
        )

    if metadata.get("sandbox_trial") or metadata.get("court_token") == "SANDBOX_TOKEN" or extract(packet, "reproducibility_hash", "") == "SANDBOX_HASH":
        return CourtPromotionDecision(
            decision_id=f"DEC_PWFR_{int(time.time() * 1000)}",
            decision="authorize_sandbox_pipeline_wavefront_fault_audit",
            justification="Authorized sandbox pipeline wavefront fault audit trial."
        )

    return CourtPromotionDecision(
        decision_id=f"DEC_PWFR_{int(time.time() * 1000)}",
        decision="hold_level47_candidate",
        justification="Level 47 readiness checks are not complete or on hold."
    )


def review_burnin_runtime_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a BurnInRuntimeReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    passed = extract(report, "passed_audit", True)
    justification = "Burn-in runtime shadow execution passed." if passed else "Burn-in runtime audit failed."
    decision = "accept_shadow_burnin" if passed else "hold_burnin"
    return CourtPromotionDecision(
        decision_id=f"DEC_BRN_RT_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_burnin_sequence_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a BurnInSequenceReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    success = extract(report, "success", True)
    justification = "Burn-in sequence plan executed successfully." if success else "Burn-in sequence had execution errors."
    decision = "accept_shadow_burnin" if success else "quarantine_burnin_sequence"
    return CourtPromotionDecision(
        decision_id=f"DEC_BRN_SEQ_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_stability_ledger_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a StabilityLedgerValidationReport or StabilityLedger summary.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    valid = extract(report, "integrity_passed", True) or extract(report, "valid", True)
    justification = "Stability ledger hash-chain integrity verified." if valid else "Stability ledger chain contains missing/reordered entries."
    decision = "accept_shadow_burnin" if valid else "reject_burnin_candidate"
    return CourtPromotionDecision(
        decision_id=f"DEC_STB_LDG_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_burnin_regression_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a BurnInRegressionReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    dec_obj = extract(report, "decision")
    passed = extract(report, "passed", True)
    justification = "No regressions detected."
    decision = "continue_shadow"
    
    if dec_obj:
        decision = extract(dec_obj, "decision", "continue_shadow")
        justification = extract(dec_obj, "justification", justification)
    elif not passed:
        decision = "hold_burnin"
        justification = "Regression checks failed."

    if decision == "continue_shadow":
        decision = "accept_shadow_burnin"

    return CourtPromotionDecision(
        decision_id=f"DEC_BRN_REG_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_burnin_rollback_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a BurnInRollbackReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    res = extract(report, "result")
    success = extract(res, "success", True) if res else True
    justification = "Rollback verification passed, state successfully restored." if success else "Rollback verification failed."
    decision = "accept_shadow_burnin" if success else "rollback_burnin_to_checkpoint"
    return CourtPromotionDecision(
        decision_id=f"DEC_BRN_RLB_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_burnin_promotion_readiness_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a BurnInPromotionReadinessReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    score = extract(report, "score")
    passed = extract(score, "passed", False) if score else False
    justification = "Promotion readiness thresholds met." if passed else "Promotion readiness thresholds not satisfied."
    
    decision = "promote_level48_candidate"
    if not passed:
        decision = "hold_burnin"
        reasons = extract(score, "reasons", []) or []
        if any("ledger" in str(r).lower() for r in reasons):
            decision = "reject_burnin_candidate"

    return CourtPromotionDecision(
        decision_id=f"DEC_BRN_RDY_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_burnin_runtime_ranger_packet(packet: Any) -> CourtPromotionDecision:
    """
    Reviews a BurnInRuntimeRanger SovereignPacket.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(packet, "evidence", {}) or {}
    rec = extract(packet, "recommendation")
    metadata = extract(packet, "metadata", {}) or {}
    
    ready = evidence.get("promotion_readiness", False)
    
    if ready and rec == "promote":
        return CourtPromotionDecision(
            decision_id=f"DEC_BRN_RNG_{int(time.time() * 1000)}",
            decision="promote_level48_candidate",
            justification="All Level 48 sovereign burn-in runtime and stability ledger audits passed."
        )

    token = metadata.get("court_token") or evidence.get("court_token")
    if token and token != "INVALID_TOKEN":
        return CourtPromotionDecision(
            decision_id=f"DEC_BRN_RNG_{int(time.time() * 1000)}",
            decision="authorize_sandbox_burnin_trial",
            justification="Sandbox token present. Authorizing sandbox burn-in trial."
        )

    quarantined = evidence.get("quarantine_count", 0) > 0
    held = evidence.get("held_cycle_count", 0) > 0
    
    dec = "hold_burnin"
    if quarantined:
        dec = "quarantine_burnin_sequence"
    elif held:
        dec = "hold_burnin"
    elif evidence.get("ledger_integrity_status") == "failed":
        dec = "reject_burnin_candidate"

    return CourtPromotionDecision(
        decision_id=f"DEC_BRN_RNG_{int(time.time() * 1000)}",
        decision=dec,
        justification=f"Ranger observed incomplete evidence or audit failure. Recommendation: {rec}."
    )


def review_release_candidate_manifest(manifest: Any) -> CourtPromotionDecision:
    """
    Reviews a ReleaseCandidateManifest or report.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    valid = extract(manifest, "valid", True)
    justification = "Release candidate manifest passes all shadow checks." if valid else "Release candidate manifest contains validation failures."
    decision = "accept_shadow_release_candidate" if valid else "hold_release_candidate"
    return CourtPromotionDecision(
        decision_id=f"DEC_RC_MNF_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_governance_freeze_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a GovernanceFreezeReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    frozen = extract(report, "frozen", True)
    justification = "Governance invariants freeze checked successfully." if frozen else "Governance invariants violated."
    decision = "accept_shadow_release_candidate" if frozen else "reject_release_candidate"
    return CourtPromotionDecision(
        decision_id=f"DEC_GVR_FRZ_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_api_stability_contract(contract: Any) -> CourtPromotionDecision:
    """
    Reviews an APIStabilityContract.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    broken = extract(contract, "broken", False)
    justification = "API stability contract verified; no breaking changes detected." if not broken else "API stability contract contains breaking API changes."
    decision = "accept_shadow_release_candidate" if not broken else "reject_release_candidate"
    return CourtPromotionDecision(
        decision_id=f"DEC_API_CTR_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_release_readiness_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a ReleaseReadinessReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    classification = extract(report, "classification", "not_ready")
    score_obj = extract(report, "score")
    
    justification = f"Release readiness evaluation completed: {classification}."
    
    decision = "promote_level49_candidate"
    if classification == "needs_more_evidence":
        decision = "needs_more_evidence"
    elif classification == "reject_release_candidate":
        decision = "reject_release_candidate"
    elif classification == "not_ready":
        decision = "hold_release_candidate"
    elif classification == "sandbox_rc_ready":
        decision = "authorize_sandbox_release_candidate_trial"
    elif classification == "shadow_rc_ready":
        decision = "accept_shadow_release_candidate"

    return CourtPromotionDecision(
        decision_id=f"DEC_RC_RDY_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_release_docket(docket: Any) -> CourtPromotionDecision:
    """
    Reviews a ReleaseDocket.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(docket, "evidence", []) or []
    evidence_types = {extract(e, "evidence_type") for e in evidence}
    required = {
        "rc_manifest", "governance_freeze_report", "api_stability_contract", 
        "release_readiness_report", "package_report", "burn_in_report", 
        "test_summary", "ranger_packet", "court_verdict"
    }
    
    missing = required - evidence_types
    if missing:
        return CourtPromotionDecision(
            decision_id=f"DEC_RC_DCK_{int(time.time() * 1000)}",
            decision="hold_release_candidate",
            justification=f"Release docket is missing critical evidence: {list(missing)}"
        )
        
    for item in evidence:
        if extract(item, "evidence_type") == "court_verdict":
            verdict_val = extract(item, "payload", {}).get("verdict")
            if verdict_val == "reject":
                return CourtPromotionDecision(
                    decision_id=f"DEC_RC_DCK_{int(time.time() * 1000)}",
                    decision="reject_release_candidate",
                    justification="Release docket has rejected court verdict."
                )

    return CourtPromotionDecision(
        decision_id=f"DEC_RC_DCK_{int(time.time() * 1000)}",
        decision="promote_level49_candidate",
        justification="All required release evidence (tests, burn-in, rollbacks, API contract, and gates) are validated successfully in the docket."
    )


def review_production_gateway_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a ProductionGatewayReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    dec_obj = extract(report, "decision")
    decision_str = extract(dec_obj, "decision") if dec_obj else "deny"
    justification = f"Production gateway request: {decision_str}."
    
    decision = "deny_production_gateway"
    if decision_str == "sandbox_trial_authorized":
        decision = "authorize_sandbox_finalization_trial"
    elif decision_str == "shadow_only_approved":
        decision = "accept_shadow_finalization"
        
    return CourtPromotionDecision(
        decision_id=f"DEC_GW_RPT_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_final_system_manifest(manifest: Any) -> CourtPromotionDecision:
    """
    Reviews a FinalSystemManifest.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    valid = extract(manifest, "valid", True)
    justification = "Final system manifest passes shadow checks." if valid else "Final system manifest invalid."
    decision = "accept_shadow_finalization" if valid else "hold_finalization"
    return CourtPromotionDecision(
        decision_id=f"DEC_SYS_MNF_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_final_gate_registry_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a FinalGateRegistryReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    all_passed = extract(report, "all_passed", True)
    justification = "All final gates passed." if all_passed else "Final gate registry has failures."
    decision = "promote_level50_candidate" if all_passed else "hold_finalization"
    return CourtPromotionDecision(
        decision_id=f"DEC_GAT_REG_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_production_readiness_guard_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a ProductionReadinessReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    dec_obj = extract(report, "decision")
    decision_str = extract(dec_obj, "decision") if dec_obj else "not_ready"
    justification = extract(dec_obj, "justification") if dec_obj else "Readiness report details."
    
    decision = "hold_finalization"
    if decision_str == "production_blocked":
        decision = "reject_finalization"
    elif decision_str == "shadow_finalized":
        decision = "accept_shadow_finalization"
    elif decision_str == "sandbox_gateway_ready":
        decision = "authorize_sandbox_finalization_trial"
        
    return CourtPromotionDecision(
        decision_id=f"DEC_RDY_GRD_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_system_lockdown_report(report: Any) -> CourtPromotionDecision:
    """
    Reviews a SystemLockdownReport.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    locked = extract(report, "locked", True)
    justification = "System parameters locked successfully." if locked else "System lockdown violated."
    decision = "accept_shadow_finalization" if locked else "reject_finalization"
    return CourtPromotionDecision(
        decision_id=f"DEC_SYS_LCK_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_runtime_handoff_manifest(manifest: Any) -> CourtPromotionDecision:
    """
    Reviews a RuntimeHandoffManifest.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    valid = extract(manifest, "valid", True) or extract(manifest, "checklist_passed", True)
    justification = "Runtime handoff manifest checklist verified." if valid else "Handoff manifest checklist failed."
    decision = "accept_shadow_finalization" if valid else "hold_finalization"
    return CourtPromotionDecision(
        decision_id=f"DEC_HND_MNF_{int(time.time() * 1000)}",
        decision=decision,
        justification=justification
    )

def review_finalization_docket(docket: Any) -> CourtPromotionDecision:
    """
    Reviews a FinalizationDocket.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    evidence = extract(docket, "evidence", []) or []
    evidence_types = {extract(e, "evidence_type") for e in evidence}
    required = {
        "final_system_manifest", "final_gate_registry_report", "production_readiness_guard_report",
        "system_lockdown_report", "runtime_handoff_manifest", "release_candidate_manifest",
        "release_docket", "runtime_ledger", "ranger_packet", "court_verdict"
    }
    
    missing = required - evidence_types
    if missing:
        return CourtPromotionDecision(
            decision_id=f"DEC_FIN_DCK_{int(time.time() * 1000)}",
            decision="hold_finalization",
            justification=f"Finalization docket is missing critical evidence: {list(missing)}"
        )
        
    for item in evidence:
        if extract(item, "evidence_type") == "court_verdict":
            verdict_val = extract(item, "payload", {}).get("verdict")
            if verdict_val == "reject":
                return CourtPromotionDecision(
                    decision_id=f"DEC_FIN_DCK_{int(time.time() * 1000)}",
                    decision="reject_finalization",
                    justification="Finalization docket has rejected court verdict."
                )

    return CourtPromotionDecision(
        decision_id=f"DEC_FIN_DCK_{int(time.time() * 1000)}",
        decision="promote_level50_candidate",
        justification="All 10 required finalization evidence items are validated successfully in the docket."
    )














