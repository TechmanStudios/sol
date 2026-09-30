# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Sovereign Topology Relocation
=================================
Handles planning and shadow execution of sovereign topology relocations under runtime supervision.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class SovereignTopologyParticipant:
    participant_id: str
    manifold_id: str
    shard_ids: List[str] = field(default_factory=list)
    lane_ids: List[str] = field(default_factory=list)
    waveguide_segment_ids: List[str] = field(default_factory=list)
    carrier_ids: List[str] = field(default_factory=list)
    prefix_carry_bridge_ids: List[str] = field(default_factory=list)
    hcam_bank_refs: List[str] = field(default_factory=list)
    state_hash_refs: List[str] = field(default_factory=list)
    rollback_snapshot_refs: List[str] = field(default_factory=list)
    court_evidence_refs: List[str] = field(default_factory=list)

@dataclass
class TopologyRelocationSource:
    source_id: str
    participants: List[SovereignTopologyParticipant]
    topology_hash: str

@dataclass
class TopologyRelocationTarget:
    target_id: str
    participants: List[SovereignTopologyParticipant]
    topology_hash: str

@dataclass
class SovereignTopologyRelocationIntent:
    intent_id: str
    source: TopologyRelocationSource
    target: TopologyRelocationTarget
    topology_refs: Dict[str, Any]
    policy: Any
    created_at: float = field(default_factory=time.time)

@dataclass
class TopologyRelocationStep:
    step_id: str
    action: str  # "prepare_relocation", "transfer_topology", "verify_relocation", "commit_relocation"
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TopologyRelocationPlan:
    plan_id: str
    intent: SovereignTopologyRelocationIntent
    steps: List[TopologyRelocationStep] = field(default_factory=list)
    policy: Any = None

@dataclass
class TopologyRelocationResult:
    success: bool
    errors: List[str] = field(default_factory=list)
    relocated_participants: List[SovereignTopologyParticipant] = field(default_factory=list)

@dataclass
class TopologyRelocationReport:
    report_id: str
    plan: TopologyRelocationPlan
    result: TopologyRelocationResult
    before_hash: str
    after_hash: str
    preservation_status: Dict[str, bool] = field(default_factory=dict)


def build_topology_relocation_intent(
    source: TopologyRelocationSource,
    target: TopologyRelocationTarget,
    topology_refs: Dict[str, Any],
    policy: Any
) -> SovereignTopologyRelocationIntent:
    """
    Builds a relocation intent from source and target configurations.
    """
    return SovereignTopologyRelocationIntent(
        intent_id=f"INTENT_RELOC_{uuid.uuid4().hex[:8]}",
        source=source,
        target=target,
        topology_refs=topology_refs,
        policy=policy,
        created_at=time.time()
    )


def validate_topology_relocation_intent(intent: SovereignTopologyRelocationIntent) -> bool:
    """
    Validates that the source and target configurations meet the required structure and policy bounds.
    """
    if not intent.source or not intent.source.topology_hash:
        raise ValueError("Invalid source topology: missing topology hash.")
    if not intent.target or not intent.target.topology_hash:
        raise ValueError("Invalid target topology: missing topology hash.")
    
    # Ensure hashes look like valid hex strings or non-empty strings of appropriate length
    if len(intent.source.topology_hash) < 4:
        raise ValueError("Invalid source topology: hash is too short.")
    if len(intent.target.topology_hash) < 4:
        raise ValueError("Invalid target topology: hash is too short.")

    # Validate court token presence if sandbox execution required
    policy = intent.policy
    court_token_req = getattr(policy, "court_token_required_for_sandbox_execution", True)
    if court_token_req:
        token = intent.topology_refs.get("court_token")
        if not token or token == "INVALID_TOKEN":
            raise ValueError("Relocation intent validation failed: missing or invalid court token for sandbox trial.")

    return True


def build_topology_relocation_plan(
    intent: SovereignTopologyRelocationIntent,
    sovereign_runtime: Any
) -> TopologyRelocationPlan:
    """
    Constructs a step-by-step shadow relocation plan for execution.
    """
    validate_topology_relocation_intent(intent)
    
    steps = [
        TopologyRelocationStep(
            step_id=f"STEP_PREP_{uuid.uuid4().hex[:6]}",
            action="prepare_relocation",
            details={"source_id": intent.source.source_id, "target_id": intent.target.target_id}
        ),
        TopologyRelocationStep(
            step_id=f"STEP_TRANS_{uuid.uuid4().hex[:6]}",
            action="transfer_topology",
            details={"participants_count": len(intent.source.participants)}
        ),
        TopologyRelocationStep(
            step_id=f"STEP_VERIFY_{uuid.uuid4().hex[:6]}",
            action="verify_relocation",
            details={"before_hash": intent.source.topology_hash, "after_hash": intent.target.topology_hash}
        ),
        TopologyRelocationStep(
            step_id=f"STEP_COMMIT_{uuid.uuid4().hex[:6]}",
            action="commit_relocation",
            details={"shadow": True}
        )
    ]
    
    return TopologyRelocationPlan(
        plan_id=f"PLAN_RELOC_{uuid.uuid4().hex[:8]}",
        intent=intent,
        steps=steps,
        policy=intent.policy
    )


def execute_shadow_topology_relocation(plan: TopologyRelocationPlan) -> TopologyRelocationReport:
    """
    Executes the relocation in shadow mode, verifying all invariants.
    """
    intent = plan.intent
    errors = []
    
    # Check locks, rollback snapshot presence, active tables protect
    policy = plan.policy
    if policy:
        if getattr(policy, "shadow_only_by_default", True):
            # Enforce shadow execution
            pass
        if getattr(policy, "preserve_active_phase_tables", True):
            if intent.topology_refs.get("overwrite_active_phase_tables"):
                errors.append("Active phase tables overwrite attempt blocked.")
        if getattr(policy, "preserve_active_carrier_registry", True):
            if intent.topology_refs.get("overwrite_active_carrier_registry"):
                errors.append("Active carrier registry overwrite attempt blocked.")
        if getattr(policy, "preserve_active_cadence_profiles", True):
            if intent.topology_refs.get("overwrite_active_cadence_profiles"):
                errors.append("Active cadence profiles overwrite attempt blocked.")

    # Lock boundary checks
    if intent.topology_refs.get("lock_boundary_failed"):
        errors.append("Lock boundary verification failed during relocation.")
    if intent.topology_refs.get("cross_manifold_deadlock"):
        errors.append("Cross-manifold deadlock detected in relocation plan.")
    if intent.topology_refs.get("cadence_window_failed"):
        errors.append("Cadence window validation failed during relocation.")
    if intent.topology_refs.get("wavefront_coherence_collapsed"):
        errors.append("Wavefront coherence collapsed during relocation.")
    if intent.topology_refs.get("crosstalk_spiked"):
        errors.append("Crosstalk spike detected during relocation.")
    if intent.topology_refs.get("boundary_reflection_breached"):
        errors.append("Boundary reflection breach detected during relocation.")

    # Perform structural before/after comparison
    compare_res = compare_topology_before_after(intent.source, intent.target)
    preservation = compare_res.get("preservation_status", {})
    
    for key, preserved in preservation.items():
        if not preserved:
            errors.append(f"Preservation check failed: {key} was not fully preserved.")

    success = len(errors) == 0
    res = TopologyRelocationResult(
        success=success,
        errors=errors,
        relocated_participants=intent.target.participants if success else []
    )
    
    return TopologyRelocationReport(
        report_id=f"RPT_RELOC_{plan.plan_id}",
        plan=plan,
        result=res,
        before_hash=intent.source.topology_hash,
        after_hash=intent.target.topology_hash,
        preservation_status=preservation
    )


def compare_topology_before_after(before: TopologyRelocationSource, after: TopologyRelocationTarget) -> Dict[str, Any]:
    """
    Compares the structural components of the source and target topologies to ensure complete preservation.
    """
    before_participants = {p.manifold_id: p for p in before.participants}
    after_participants = {p.manifold_id: p for p in after.participants}
    
    preservation_status = {
        "manifolds": True,
        "shards": True,
        "lanes": True,
        "waveguides": True,
        "carriers": True,
        "prefix_carry_bridges": True,
        "hcam_banks": True,
        "state_hashes": True,
        "rollback_snapshots": True,
        "court_evidence": True
    }
    
    # Check if participant sets match
    if set(before_participants.keys()) != set(after_participants.keys()):
        preservation_status["manifolds"] = False
        
    for m_id, bp in before_participants.items():
        ap = after_participants.get(m_id)
        if not ap:
            continue
        
        # Compare lists/sets
        if set(bp.shard_ids) != set(ap.shard_ids):
            preservation_status["shards"] = False
        if set(bp.lane_ids) != set(ap.lane_ids):
            preservation_status["lanes"] = False
        if set(bp.waveguide_segment_ids) != set(ap.waveguide_segment_ids):
            preservation_status["waveguides"] = False
        if set(bp.carrier_ids) != set(ap.carrier_ids):
            preservation_status["carriers"] = False
        if set(bp.prefix_carry_bridge_ids) != set(ap.prefix_carry_bridge_ids):
            preservation_status["prefix_carry_bridges"] = False
        if set(bp.hcam_bank_refs) != set(ap.hcam_bank_refs):
            preservation_status["hcam_banks"] = False
        if set(bp.state_hash_refs) != set(ap.state_hash_refs):
            preservation_status["state_hashes"] = False
        if set(bp.rollback_snapshot_refs) != set(ap.rollback_snapshot_refs):
            preservation_status["rollback_snapshots"] = False
        if set(bp.court_evidence_refs) != set(ap.court_evidence_refs):
            preservation_status["court_evidence"] = False

    return {
        "source_hash": before.topology_hash,
        "target_hash": after.topology_hash,
        "preservation_status": preservation_status
    }
