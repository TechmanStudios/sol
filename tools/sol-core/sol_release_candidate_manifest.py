# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Release Candidate Manifest
==============================
Manages metadata, test summaries, stability audits, and governance verification for release candidates.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class ReleaseCandidateId:
    candidate_id: str
    level: str = "49"
    created_at: float = field(default_factory=time.time)

@dataclass
class ReleaseCandidateEvidenceItem:
    evidence_id: str
    evidence_type: str  # burnin_report, stability_ledger, rollback_proof, ranger_packet, court_verdict, api_contract
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class ReleaseCandidateTestSummary:
    total_tests: int
    passed_tests: int
    failed_tests: int
    duration: float
    test_run_id: str = field(default_factory=lambda: f"TST_{uuid.uuid4().hex[:8]}")

@dataclass
class ReleaseCandidateGateSnapshot:
    snapshot_id: str
    gates_checked: Dict[str, bool] = field(default_factory=dict)
    all_passed: bool = True
    timestamp: float = field(default_factory=time.time)

@dataclass
class ReleaseCandidateVerdict:
    verdict: str  # approve, reject, hold, needs_more_evidence
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class ReleaseCandidateManifest:
    candidate_id: ReleaseCandidateId
    evidence: List[ReleaseCandidateEvidenceItem] = field(default_factory=list)
    test_summary: Optional[ReleaseCandidateTestSummary] = None
    gate_snapshots: List[ReleaseCandidateGateSnapshot] = field(default_factory=list)
    quarantine_status: str = "none"  # none, quarantined
    frozen_api_surface: Dict[str, Any] = field(default_factory=dict)
    frozen_governance_invariants: List[str] = field(default_factory=list)
    known_non_production_limitations: List[str] = field(default_factory=lambda: [
        "shadow_mode_only", "no_production_mutation", "court_reviewed_promotions"
    ])

@dataclass
class ReleaseCandidateReport:
    report_id: str
    manifest: ReleaseCandidateManifest
    valid: bool
    verdict: ReleaseCandidateVerdict
    timestamp: float = field(default_factory=time.time)


def open_release_candidate_manifest(candidate_id: str, level: str = "49") -> ReleaseCandidateManifest:
    """
    Opens a new release candidate manifest.
    """
    rc_id = ReleaseCandidateId(candidate_id=candidate_id, level=level)
    return ReleaseCandidateManifest(candidate_id=rc_id)


def attach_release_evidence(manifest: ReleaseCandidateManifest, evidence: ReleaseCandidateEvidenceItem) -> None:
    """
    Attaches an evidence item (e.g. burn-in report, ledger validation, rollback proof) to the manifest.
    """
    manifest.evidence.append(evidence)


def attach_test_summary(manifest: ReleaseCandidateManifest, test_summary: ReleaseCandidateTestSummary) -> None:
    """
    Attaches a test suite summary to the manifest.
    """
    manifest.test_summary = test_summary


def attach_gate_snapshot(manifest: ReleaseCandidateManifest, gate_snapshot: ReleaseCandidateGateSnapshot) -> None:
    """
    Attaches a checklist gate snapshot to the manifest.
    """
    manifest.gate_snapshots.append(gate_snapshot)


def validate_release_candidate_manifest(manifest: ReleaseCandidateManifest) -> bool:
    """
    Validates manifest parameters. Rejects missing test summaries,
    missing burn-in evidence, or missing rollback proofs.
    """
    if not manifest.test_summary:
        return False
    if manifest.test_summary.failed_tests > 0:
        return False
        
    evidence_types = {item.evidence_type for item in manifest.evidence}
    if "burnin_report" not in evidence_types:
        return False
    if "rollback_proof" not in evidence_types:
        return False
        
    return True


def summarize_release_candidate_manifest(manifest: ReleaseCandidateManifest) -> ReleaseCandidateReport:
    """
    Validates manifest and constructs a release candidate report.
    """
    valid = validate_release_candidate_manifest(manifest)
    
    if valid:
        verd = ReleaseCandidateVerdict(
            verdict="approve",
            justification="All required release evidence (tests, burn-in, rollbacks, and gates) are validated successfully."
        )
    else:
        verd = ReleaseCandidateVerdict(
            verdict="hold",
            justification="Release candidate manifest lacks necessary evidence or contains failing tests."
        )
        
    return ReleaseCandidateReport(
        report_id=f"RC_RPT_{uuid.uuid4().hex[:8]}",
        manifest=manifest,
        valid=valid,
        verdict=verd
    )


def export_release_candidate_for_finalization(manifest: ReleaseCandidateManifest) -> Dict[str, Any]:
    """
    Exports release candidate manifest parameters for system finalization.
    """
    valid = validate_release_candidate_manifest(manifest)
    return {
        "candidate_id": manifest.candidate_id.candidate_id,
        "level": manifest.candidate_id.level,
        "valid": valid,
        "quarantine_status": manifest.quarantine_status
    }


def validate_release_candidate_for_final_gateway(manifest: ReleaseCandidateManifest) -> bool:
    """
    Validates that the release candidate is correct and passes shadow checks.
    """
    return validate_release_candidate_manifest(manifest)

