# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Promotion Docket
====================
Manages the promotion dockets, hearings, verdicts, and manifests for court reviews.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class PromotionEvidenceItem:
    evidence_id: str
    evidence_type: str  # "ranger_packet" | "consensus_report" | "transaction_report" | "geodesic_propagation_report" | "telemetry_report" | "test_summary" | "rollback_snapshot"
    payload: Any
    timestamp: float = field(default_factory=time.time)

@dataclass
class PromotionGateSnapshot:
    snapshot_id: str
    gates: Dict[str, bool]
    passed: bool
    timestamp: float = field(default_factory=time.time)

@dataclass
class PromotionHearing:
    hearing_id: str
    justification: str
    participants: List[str]
    timestamp: float = field(default_factory=time.time)

@dataclass
class PromotionVerdict:
    verdict_id: str
    decision: str  # "accept_shadow_candidate" | "reject_promotion" | "promote_level29_candidate"
    justification: str
    judge_signatures: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

@dataclass
class PromotionDocket:
    docket_id: str
    candidate_id: str
    level: int
    evidence: List[PromotionEvidenceItem] = field(default_factory=list)
    gate_snapshots: List[PromotionGateSnapshot] = field(default_factory=list)
    hearings: List[PromotionHearing] = field(default_factory=list)
    quarantine_status: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PromotionManifest:
    manifest_id: str
    docket_id: str
    candidate_id: str
    level: int
    verdict: PromotionVerdict
    promoted_components: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def open_promotion_docket(candidate_id: str, level: int) -> PromotionDocket:
    """
    Opens a new docket for tracking level promotion candidates.
    """
    docket_id = f"DOCKET_{candidate_id}_{int(time.time())}"
    return PromotionDocket(docket_id=docket_id, candidate_id=candidate_id, level=level)


def attach_evidence_item(docket: PromotionDocket, evidence: Any) -> None:
    """
    Attaches an evidence item or dictionary payload to the docket.
    """
    if isinstance(evidence, PromotionEvidenceItem):
        docket.evidence.append(evidence)
    else:
        # Construct from dictionary or generic object
        evidence_type = "unknown"
        evidence_id = f"EV_{int(time.time())}_{len(docket.evidence)}"
        if isinstance(evidence, dict):
            evidence_type = evidence.get("evidence_type", "unknown")
            payload = evidence.get("payload")
        else:
            payload = evidence
            obj_class = evidence.__class__.__name__
            if "SovereignPacket" in obj_class:
                evidence_type = "ranger_packet"
            elif "ConsensusReport" in obj_class:
                evidence_type = "consensus_report"
            elif "TransactionReport" in obj_class:
                evidence_type = "transaction_report"
            elif "PropagationReport" in obj_class:
                evidence_type = "geodesic_propagation_report"
            elif "AlignmentReport" in obj_class:
                evidence_type = "telemetry_report"
            elif "CalibrationReport" in obj_class:
                evidence_type = "entangled_calibration_report"
            elif "FeedbackLoopReport" in obj_class:
                evidence_type = "entangled_feedback_loop_report"
            elif "StabilityControlReport" in obj_class:
                evidence_type = "entangled_stability_control_report"
            elif "SovereignRuntimeReport" in obj_class:
                evidence_type = "sovereign_runtime_report"
            elif "LevelUpSequenceReport" in obj_class:
                evidence_type = "levelup_sequence_report"
            elif "RuntimeGovernanceReport" in obj_class:
                evidence_type = "runtime_governance_report"

        item = PromotionEvidenceItem(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            payload=payload
        )
        docket.evidence.append(item)


def attach_gate_snapshot(docket: PromotionDocket, gate_snapshot: PromotionGateSnapshot) -> None:
    """
    Attaches a checklist snapshot of gate checks to the docket.
    """
    docket.gate_snapshots.append(gate_snapshot)


def validate_promotion_docket(docket: PromotionDocket) -> bool:
    """
    Enforces completeness constraints on the docket.
    Requires ranger packets, gate results, rollback snapshot references, consensus reports,
    transaction reports, geodesic propagation reports, telemetry reports, and test summaries.
    For Level 30, also requires calibration reports.
    For Level 31, requires synthesis, SIMD integration, and layout optimization reports.
    For Level 32, requires reshape, carrier relocation, and registry reports.
    """
    if getattr(docket, "level", 0) == 36:
        required_types = {
            "ranger_packet",
            "sovereign_runtime_report",
            "levelup_sequence_report",
            "runtime_governance_report",
            "rollback_snapshot",
            "test_summary"
        }
    elif getattr(docket, "level", 0) == 35:
        required_types = {
            "ranger_packet",
            "entangled_calibration_report",
            "entangled_feedback_loop_report",
            "entangled_stability_control_report",
            "rollback_snapshot",
            "test_summary"
        }
    elif getattr(docket, "level", 0) == 34:
        required_types = {
            "ranger_packet",
            "entangled_propagation_report",
            "synchronized_commit_report",
            "entangled_commit_report",
            "rollback_snapshot",
            "test_summary"
        }
    elif getattr(docket, "level", 0) == 33:
        required_types = {
            "ranger_packet",
            "cadence_stability_report",
            "cadence_sync_report",
            "transaction_cadence_report",
            "rollback_snapshot",
            "test_summary"
        }
    elif getattr(docket, "level", 0) == 32:
        required_types = {
            "ranger_packet",
            "manifold_reshape_report",
            "pdm_carrier_relocation_report",
            "carrier_registry_report",
            "rollback_snapshot",
            "test_summary"
        }
    elif getattr(docket, "level", 0) == 31:
        required_types = {
            "ranger_packet",
            "waveguide_synthesis_report",
            "simd_core_integration_report",
            "waveguide_layout_optimization_report",
            "rollback_snapshot",
            "test_summary"
        }
    else:
        required_types = {
            "ranger_packet",
            "consensus_report",
            "transaction_report",
            "geodesic_propagation_report",
            "telemetry_report",
            "test_summary",
            "rollback_snapshot"
        }
        if getattr(docket, "level", 0) == 30:
            required_types.update({
                "calibration_loop_report",
                "boundary_calibration_report",
                "wavefront_stabilization_report",
                "calibration_control_report"
            })
            
    present_types = {item.evidence_type for item in docket.evidence}
    return required_types.issubset(present_types)


def build_promotion_manifest(docket: PromotionDocket, verdict: PromotionVerdict) -> PromotionManifest:
    """
    Generates a PromotionManifest detailing components to promote if docket validation passes.
    """
    if not validate_promotion_docket(docket):
        raise ValueError("Cannot build manifest: Promotion docket is incomplete.")
    if verdict.decision not in ["promote_level28_candidate", "promote_level29_candidate", "promote_level30_candidate", "promote_level31_candidate", "promote_level32_candidate", "promote_level33_candidate", "promote_level34_candidate", "promote_level35_candidate", "promote_level36_candidate"]:
        raise ValueError(f"Cannot build manifest: Invalid verdict decision for promotion: {verdict.decision}")

    manifest_id = f"MANIFEST_{docket.docket_id}_{int(time.time())}"
    return PromotionManifest(
        manifest_id=manifest_id,
        docket_id=docket.docket_id,
        candidate_id=docket.candidate_id,
        level=docket.level,
        verdict=verdict,
        promoted_components=[f"level_{docket.level}_scaffold_firmware"],
        metadata=dict(docket.metadata)
    )

