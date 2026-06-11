# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Final System Manifest
=========================
Wraps all Level 49 manifests, freezes, API contracts, test summaries, ledgers, and gateways.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class FinalSystemEvidenceItem:
    evidence_id: str
    evidence_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class FinalSystemInvariantSnapshot:
    snapshot_id: str
    invariants: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class FinalSystemGateSummary:
    summary_id: str
    gates: Dict[str, bool] = field(default_factory=dict)
    all_passed: bool = True
    timestamp: float = field(default_factory=time.time)

@dataclass
class FinalSystemVerdict:
    verdict: str  # approve, hold, reject
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class FinalSystemManifest:
    system_id: str
    release_candidate_manifest: Optional[Any] = None
    release_docket: Optional[Any] = None
    governance_freeze_report: Optional[Any] = None
    api_stability_contract: Optional[Any] = None
    test_summary: Optional[Any] = None
    burnin_report: Optional[Any] = None
    stability_ledger: Optional[Any] = None
    rollback_proof: Optional[Any] = None
    ranger_registry_snapshot: Optional[Any] = None
    court_verdicts: List[Any] = field(default_factory=list)
    quarantine_status: str = "none"
    known_limitations: List[str] = field(default_factory=lambda: ["shadow_mode_only", "no_production_mutation"])
    final_gateway_policy: Optional[Any] = None
    evidence: List[FinalSystemEvidenceItem] = field(default_factory=list)
    invariant_snapshots: List[FinalSystemInvariantSnapshot] = field(default_factory=list)
    gate_summaries: List[FinalSystemGateSummary] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

@dataclass
class FinalSystemReport:
    report_id: str
    manifest: FinalSystemManifest
    valid: bool
    verdict: FinalSystemVerdict
    timestamp: float = field(default_factory=time.time)


def open_final_system_manifest(system_id: str) -> FinalSystemManifest:
    """
    Opens a new final system manifest.
    """
    return FinalSystemManifest(system_id=system_id)


def attach_final_system_evidence(manifest: FinalSystemManifest, evidence: FinalSystemEvidenceItem) -> None:
    """
    Attaches a final system evidence item.
    """
    manifest.evidence.append(evidence)


def attach_final_invariant_snapshot(manifest: FinalSystemManifest, snapshot: FinalSystemInvariantSnapshot) -> None:
    """
    Attaches a final invariant snapshot.
    """
    manifest.invariant_snapshots.append(snapshot)


def attach_final_gate_summary(manifest: FinalSystemManifest, gate_summary: FinalSystemGateSummary) -> None:
    """
    Attaches a final gate summary.
    """
    manifest.gate_summaries.append(gate_summary)


def validate_final_system_manifest(manifest: FinalSystemManifest) -> bool:
    """
    Validates manifest completeness. Rejects missing release candidate evidence or missing rollback proof.
    """
    evidence_types = {item.evidence_type for item in manifest.evidence}
    
    # Check if release candidate evidence exists
    if "release_candidate_manifest" not in evidence_types and not manifest.release_candidate_manifest:
        return False
        
    # Check if rollback proof exists
    if "rollback_proof" not in evidence_types and not manifest.rollback_proof:
        return False
        
    # Validate quarantine status
    if manifest.quarantine_status == "quarantined":
        return False
        
    return True


def summarize_final_system_manifest(manifest: FinalSystemManifest) -> FinalSystemReport:
    """
    Summarizes the manifest and constructs a final system report.
    """
    valid = validate_final_system_manifest(manifest)
    if valid:
        verd = FinalSystemVerdict(
            verdict="approve",
            justification="All required system finalization evidence is validated successfully."
        )
    else:
        verd = FinalSystemVerdict(
            verdict="hold",
            justification="Final system manifest lacks necessary evidence or is in quarantine."
        )
        
    return FinalSystemReport(
        report_id=f"SYS_RPT_{uuid.uuid4().hex[:8]}",
        manifest=manifest,
        valid=valid,
        verdict=verd
    )
