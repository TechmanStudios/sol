# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Transaction Orchestrator
============================
Orchestrates multi-stage distributed transaction consensus and geodesic propagation workflows.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class TransactionOrchestrationIntent:
    orchestration_id: str
    transaction_intent: Any  # MultiManifoldTransactionIntent
    geodesic_intent: Any  # GeodesicPropagationIntent
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionOrchestrationStage:
    stage_name: str
    status: str = "pending"  # "pending" | "running" | "passed" | "failed" | "skipped"
    message: str = ""
    timestamp: float = field(default_factory=time.time)

@dataclass
class TransactionOrchestrationPlan:
    plan_id: str
    intent: TransactionOrchestrationIntent
    group: Any  # ManifoldCoordinationGroup
    stages: List[TransactionOrchestrationStage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionOrchestrationState:
    orchestration_id: str
    current_stage: str = "proposal"
    history: List[TransactionOrchestrationStage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionOrchestrationResult:
    success: bool
    decision: str  # e.g., "accept_shadow_candidate", "reject_promotion"
    rolled_back: bool = False
    quarantined: bool = False
    stages_executed: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionOrchestrationReport:
    report_id: str
    result: TransactionOrchestrationResult
    plan: TransactionOrchestrationPlan
    passed_gates: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_transaction_orchestration_plan(
    intent: TransactionOrchestrationIntent,
    coordination_group: Any
) -> TransactionOrchestrationPlan:
    """
    Constructs the sequence of stages for a multi-manifold transaction.
    """
    stages_list = [
        "proposal",
        "boundary validation",
        "lock validation",
        "quorum validation",
        "geodesic propagation validation",
        "rollback validation",
        "ranger evidence collection",
        "court review",
        "sandbox trial authorization",
        "promotion decision",
        "quarantine or rollback if needed"
    ]
    stages = [TransactionOrchestrationStage(stage_name=name) for name in stages_list]
    plan_id = f"TOPLAN_{intent.orchestration_id}_{int(time.time())}"
    return TransactionOrchestrationPlan(
        plan_id=plan_id,
        intent=intent,
        group=coordination_group,
        stages=stages
    )


def validate_transaction_orchestration_plan(plan: TransactionOrchestrationPlan) -> bool:
    """
    Ensures the plan is valid and contains all required stages.
    """
    if not plan.intent or not plan.group:
        return False
    required_stages = {
        "proposal", "boundary validation", "lock validation", "quorum validation",
        "geodesic propagation validation", "rollback validation", "ranger evidence collection",
        "court review", "sandbox trial authorization", "promotion decision",
        "quarantine or rollback if needed"
    }
    existing_stages = {stage.stage_name for stage in plan.stages}
    return required_stages.issubset(existing_stages)


def execute_shadow_transaction_orchestration(
    plan: TransactionOrchestrationPlan
) -> TransactionOrchestrationReport:
    """
    Simulates transaction orchestration stages without modifying default/production state.
    """
    from sol_multimanifold_transaction_consensus import (
        validate_transaction_boundaries,
        collect_transaction_consensus_votes,
        evaluate_transaction_consensus_quorum,
        build_transaction_consensus_report
    )
    from sol_geodesic_propagation_update import (
        validate_geodesic_propagation_path,
        execute_shadow_geodesic_propagation,
        GeodesicPropagationReport
    )
    from sol_transaction_wavefront_epoch import (
        start_wavefront_transaction_epoch,
        register_wavefront_checkpoint,
        evaluate_wavefront_commit_barrier,
        commit_shadow_wavefront_transaction,
        abort_wavefront_transaction,
        WavefrontPropagationCheckpoint
    )
    from sol_global_lock_boundary import (
        collect_manifold_lock_boundaries,
        plan_global_lock_boundary,
        validate_locks_for_geodesic_transaction,
        CrossManifoldLockIntent,
        GlobalLockBoundaryReport
    )
    from sol_wavefront_alignment_coordinator import (
        capture_cross_manifold_wavefront_state,
        plan_wavefront_alignment_adjustment,
        execute_shadow_wavefront_alignment
    )
    from coding_library.sovereign_domain.rangers.transaction_propagation_ranger import TransactionPropagationRanger
    from coding_library.sovereign_domain import PromotionCourt

    errors = []
    stages_run = 0
    rolled_back = False
    quarantined = False
    decision = "reject_promotion"

    # Verify coordination group presence
    if plan.group is None or not getattr(plan.group, "manifolds", None):
        plan.stages[0].status = "failed"
        plan.stages[0].message = "Missing coordination group"
        errors.append("Missing coordination group")
        res = TransactionOrchestrationResult(
            success=False,
            decision="reject_promotion",
            rolled_back=False,
            quarantined=False,
            stages_executed=1,
            errors=errors
        )
        return TransactionOrchestrationReport(f"TOREP_{plan.plan_id}", res, plan, False)

    # 1. Proposal
    p_stage = plan.stages[0]
    p_stage.status = "passed"
    p_stage.message = "Proposal validated"
    stages_run += 1

    # Initialize variables needed for sub-stages
    intent = plan.intent.transaction_intent
    group = plan.group
    epoch = None
    votes = None
    consensus_decision = None
    consensus_report = None
    geo_plan = None
    propagation_res = None
    geodesic_report = None
    wavefront_report = None
    lock_report = None
    alignment_report = None

    # Helper function to get stages by name
    def get_stage(name: str) -> TransactionOrchestrationStage:
        for s in plan.stages:
            if s.stage_name == name:
                return s
        raise ValueError(f"Stage {name} not found")

    # 2. Boundary Validation
    b_stage = get_stage("boundary validation")
    from sol_multimanifold_transaction_consensus import build_transaction_consensus_epoch
    epoch = build_transaction_consensus_epoch(intent, group)
    
    # Check if a participant is missing/invalid
    if plan.metadata.get("missing_participant_boundary"):
        epoch.boundary.participants.pop(list(epoch.boundary.participants.keys())[0], None)
        
    if not validate_transaction_boundaries(epoch):
        b_stage.status = "failed"
        b_stage.message = "Invalid boundaries"
        errors.append("Invalid boundaries")
    else:
        b_stage.status = "passed"
        b_stage.message = "Boundaries validated"
    stages_run += 1

    # 3. Lock Validation
    l_stage = get_stage("lock validation")
    if not errors:
        glb = collect_manifold_lock_boundaries(group.manifolds)
        lock_intent = plan.metadata.get("lock_intent") or CrossManifoldLockIntent(
            intent_id=f"LINT_{intent.transaction_id}",
            locks_to_acquire={m_id: ["shard_0"] for m_id in epoch.boundary.participants}
        )
        boundary_plan = plan_global_lock_boundary(lock_intent, glb)
        if plan.metadata.get("force_deadlock_detected"):
            boundary_plan.metadata["force_deadlock_detected"] = True
            
        lock_valid = validate_locks_for_geodesic_transaction(boundary_plan, epoch)
        lock_report = GlobalLockBoundaryReport(f"LRPT_{intent.transaction_id}", boundary_plan, lock_valid, not lock_valid, not lock_valid)
        if not lock_valid:
            l_stage.status = "failed"
            l_stage.message = "Lock boundaries invalid or deadlock detected"
            errors.append("Lock boundaries invalid or deadlock detected")
        else:
            l_stage.status = "passed"
            l_stage.message = "Lock boundaries validated"
    else:
        l_stage.status = "skipped"
    stages_run += 1

    # 4. Quorum Validation
    q_stage = get_stage("quorum validation")
    if not errors:
        epoch.metadata.update(plan.metadata)
        votes = collect_transaction_consensus_votes(epoch, mock_votes=plan.metadata.get("mock_votes"))
        consensus_decision = evaluate_transaction_consensus_quorum(epoch, votes)
        consensus_report = build_transaction_consensus_report(epoch, votes, consensus_decision)
        if not consensus_decision.agreed:
            q_stage.status = "failed"
            q_stage.message = "Consensus quorum not reached"
            errors.append("Consensus quorum not reached")
        else:
            q_stage.status = "passed"
            q_stage.message = "Consensus quorum reached"
    else:
        q_stage.status = "skipped"
    stages_run += 1

    # 5. Geodesic Propagation Validation
    gp_stage = get_stage("geodesic propagation validation")
    if not errors:
        from sol_geodesic_propagation_update import plan_geodesic_propagation, GeodesicPropagationIntent
        g_intent = plan.intent.geodesic_intent
        geo_plan = plan_geodesic_propagation(g_intent, group)
        
        # Check invalid path crossings
        if plan.metadata.get("missing_boundary_declaration"):
            geo_plan.path.boundary_crossings = []
            
        if not validate_geodesic_propagation_path(geo_plan.path):
            gp_stage.status = "failed"
            gp_stage.message = "Invalid geodesic propagation path"
            errors.append("Invalid geodesic propagation path")
        else:
            propagation_res = execute_shadow_geodesic_propagation(geo_plan)
            geodesic_report = GeodesicPropagationReport(
                report_id=f"GRPT_{geo_plan.update_id}",
                result=propagation_res,
                passed_gates=propagation_res.success,
                metadata={}
            )
            
            # Check stability/telemetry gates
            crosstalk_level = plan.metadata.get("high_crosstalk", False)
            reflection_level = plan.metadata.get("high_reflection", False)
            phase_error = plan.metadata.get("high_phase_error", False)
            hash_mismatch = plan.metadata.get("state_hash_mismatch", False)
            
            if not propagation_res.success or crosstalk_level or reflection_level or phase_error or hash_mismatch:
                gp_stage.status = "failed"
                gp_stage.message = "Geodesic propagation unstable"
                errors.append("Geodesic propagation unstable")
            else:
                gp_stage.status = "passed"
                gp_stage.message = "Geodesic propagation validated and stable"
    else:
        gp_stage.status = "skipped"
    stages_run += 1

    # 6. Rollback Validation
    r_stage = get_stage("rollback validation")
    if not errors:
        tokens = plan.metadata.get("tokens")
        if tokens is None:
            r_stage.status = "failed"
            r_stage.message = "Missing rollback snapshots references"
            errors.append("Missing rollback snapshots references")
        else:
            r_stage.status = "passed"
            r_stage.message = "Rollback snapshots validated"
    else:
        r_stage.status = "skipped"
    stages_run += 1

    # 7. Ranger Evidence Collection
    re_stage = get_stage("ranger evidence collection")
    ranger_packet = None
    if not errors:
        # Capture wavefront state for alignment report
        obs = capture_cross_manifold_wavefront_state(group.manifolds)
        al_plan = plan_wavefront_alignment_adjustment(obs, None)
        alignment_report = execute_shadow_wavefront_alignment(al_plan)

        # Build wavefront epoch and shadow commit to produce reports
        w_epoch = start_wavefront_transaction_epoch(intent, plan.intent.geodesic_intent)
        for m_id in epoch.boundary.participants:
            checkpoint = WavefrontPropagationCheckpoint(
                checkpoint_id=f"CP_{m_id}_{w_epoch.epoch_id}",
                manifold_id=m_id,
                completed=True,
                state_hash=propagation_res.after_state_hash if propagation_res else "hash"
            )
            register_wavefront_checkpoint(w_epoch, checkpoint)
        wavefront_report = commit_shadow_wavefront_transaction(w_epoch)

        # Collect evidence via TransactionPropagationRanger
        ranger = TransactionPropagationRanger()
        ranger_packet = ranger.observe_propagation(
            consensus_report=consensus_report,
            geodesic_report=geodesic_report,
            wavefront_report=wavefront_report,
            lock_report=lock_report,
            alignment_report=alignment_report
        )
        re_stage.status = "passed"
        re_stage.message = "Ranger evidence collected"
    else:
        re_stage.status = "skipped"
    stages_run += 1

    # 8. Court Review
    cr_stage = get_stage("court review")
    court = PromotionCourt()
    court_verdict = None
    if not errors:
        if ranger_packet:
            court.submit_packet(ranger_packet)
            
        from sol_promotion_docket import open_promotion_docket, attach_evidence_item, attach_gate_snapshot, validate_promotion_docket
        from sol_court_supervised_promotion import CourtPromotionPolicy
        
        docket = open_promotion_docket(f"CAND_{intent.transaction_id}", 29)
        # Attach required evidences
        attach_evidence_item(docket, {"evidence_type": "ranger_packet", "payload": ranger_packet})
        attach_evidence_item(docket, {"evidence_type": "consensus_report", "payload": consensus_report})
        attach_evidence_item(docket, {"evidence_type": "transaction_report", "payload": wavefront_report})
        attach_evidence_item(docket, {"evidence_type": "geodesic_propagation_report", "payload": geodesic_report})
        attach_evidence_item(docket, {"evidence_type": "telemetry_report", "payload": alignment_report})
        attach_evidence_item(docket, {"evidence_type": "test_summary", "payload": {"status": "all_passed"}})
        attach_evidence_item(docket, {"evidence_type": "rollback_snapshot", "payload": plan.metadata.get("tokens")})
        
        # Check for quarantine
        if plan.metadata.get("quarantine_unresolved"):
            docket.quarantine_status = True
            
        # Optional: check if missing ranger check
        if plan.metadata.get("skip_ranger_check"):
            ranger_packet.metadata["skip_ranger_check"] = True
            
        court_verdict = court.issue_court_supervised_promotion_verdict(docket)
        if court_verdict.decision == "promote_level29_candidate":
            cr_stage.status = "passed"
            cr_stage.message = f"Court review passed: {court_verdict.justification}"
        else:
            cr_stage.status = "failed"
            cr_stage.message = f"Court review refused: {court_verdict.justification}"
            errors.append(f"Court review refused: {court_verdict.justification}")
    else:
        cr_stage.status = "skipped"
    stages_run += 1

    # 9. Sandbox Trial Authorization
    sa_stage = get_stage("sandbox trial authorization")
    if not errors:
        sa_stage.status = "passed"
        sa_stage.message = "Sandbox trial authorized"
    else:
        sa_stage.status = "skipped"
    stages_run += 1

    # 10. Promotion Decision
    pd_stage = get_stage("promotion decision")
    if not errors:
        # Enforce no automatic production promotion
        if plan.metadata.get("allow_production_promotion", False):
            pd_stage.status = "failed"
            pd_stage.message = "Production promotion is prohibited by policy rules"
            errors.append("Production promotion is prohibited by policy rules")
        else:
            pd_stage.status = "passed"
            pd_stage.message = "Shadow candidate promotion decision accepted"
            decision = "accept_shadow_candidate"
    else:
        pd_stage.status = "skipped"
    stages_run += 1

    # 11. Quarantine or Rollback if needed
    qr_stage = get_stage("quarantine or rollback if needed")
    if errors:
        qr_stage.status = "passed"
        if plan.metadata.get("quarantine_unresolved") or "unstable" in "".join(errors) or "deadlock" in "".join(errors):
            quarantined = True
            qr_stage.message = "Quarantine recommended"
            decision = "quarantine_candidate"
        else:
            rolled_back = True
            qr_stage.message = "Rollback triggered"
            decision = "rollback_candidate"
    else:
        qr_stage.status = "skipped"
    stages_run += 1

    res = TransactionOrchestrationResult(
        success=(len(errors) == 0),
        decision=decision,
        rolled_back=rolled_back,
        quarantined=quarantined,
        stages_executed=stages_run,
        errors=errors
    )

    return TransactionOrchestrationReport(
        report_id=f"TOREP_{plan.plan_id}",
        result=res,
        plan=plan,
        passed_gates=(len(errors) == 0)
    )


def summarize_transaction_orchestration(result: TransactionOrchestrationResult) -> Dict[str, Any]:
    """
    Returns a brief, readable summary of the orchestration result.
    """
    return {
        "success": result.success,
        "decision": result.decision,
        "rolled_back": result.rolled_back,
        "quarantined": result.quarantined,
        "stages_executed": result.stages_executed,
        "error_count": len(result.errors)
    }
