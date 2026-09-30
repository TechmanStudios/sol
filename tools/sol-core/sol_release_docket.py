# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Release Docket
==================
Groups manifests, contracts, and readiness reports into a unified release docket for court review.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid
import time

@dataclass
class ReleaseDocketEvidence:
    evidence_id: str
    evidence_type: str  # rc_manifest, governance_freeze_report, api_stability_contract, release_readiness_report, package_report, burn_in_report, test_summary, ranger_packet, court_verdict
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class ReleaseDocketReview:
    reviewer: str
    decision: str  # approve, hold, reject
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class ReleaseDocketVerdict:
    verdict: str  # approve, reject, hold
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class ReleaseDocket:
    docket_id: str
    candidate_id: str
    evidence: List[ReleaseDocketEvidence] = field(default_factory=list)
    reviews: List[ReleaseDocketReview] = field(default_factory=list)
    verdict: Optional[ReleaseDocketVerdict] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class ReleaseDocketReport:
    report_id: str
    docket: ReleaseDocket
    valid: bool
    verdict: ReleaseDocketVerdict
    timestamp: float = field(default_factory=time.time)


def open_release_docket(candidate_id: str) -> ReleaseDocket:
    """
    Opens a new release docket.
    """
    return ReleaseDocket(
        docket_id=f"DCK_{uuid.uuid4().hex[:8]}",
        candidate_id=candidate_id
    )


def attach_release_docket_evidence(docket: ReleaseDocket, evidence: ReleaseDocketEvidence) -> None:
    """
    Attaches a release docket evidence item.
    """
    docket.evidence.append(evidence)


def validate_release_docket(docket: ReleaseDocket) -> bool:
    """
    Ensures all 9 required release evidence items are present:
    rc_manifest, governance_freeze_report, api_stability_contract, release_readiness_report, 
    package_report, burn_in_report, test_summary, ranger_packet, court_verdict.
    """
    evidence_types = {item.evidence_type for item in docket.evidence}
    required = {
        "rc_manifest", "governance_freeze_report", "api_stability_contract", 
        "release_readiness_report", "package_report", "burn_in_report", 
        "test_summary", "ranger_packet", "court_verdict"
    }
    
    for req in required:
        if req not in evidence_types:
            return False
            
    # Explicitly verify the court verdict isn't missing or rejected
    for item in docket.evidence:
        if item.evidence_type == "court_verdict":
            verdict_val = item.payload.get("verdict")
            if verdict_val == "reject" or not verdict_val:
                return False
                
    return True


def summarize_release_docket(docket: ReleaseDocket) -> ReleaseDocketReport:
    """
    Validates release docket and returns a summary report.
    """
    valid = validate_release_docket(docket)
    
    if valid:
        verd = ReleaseDocketVerdict(
            verdict="approve",
            justification="All 9 required evidence categories are attached, and court verdict is approved."
        )
    else:
        # Check if missing court verdict
        types = {item.evidence_type for item in docket.evidence}
        if "court_verdict" not in types:
            verd = ReleaseDocketVerdict(
                verdict="hold",
                justification="Release docket lacks the required court verdict."
            )
        else:
            verd = ReleaseDocketVerdict(
                verdict="reject",
                justification="Release docket failed validation checks or contains a rejected verdict."
            )
            
    return ReleaseDocketReport(
        report_id=f"DCK_RPT_{uuid.uuid4().hex[:8]}",
        docket=docket,
        valid=valid,
        verdict=verd
    )
