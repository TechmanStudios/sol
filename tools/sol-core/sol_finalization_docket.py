# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Finalization Docket
=======================
Aggregates and validates all final system finalization evidence items for Level 50 court review.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid
import time

@dataclass
class FinalizationDocketEvidence:
    evidence_id: str
    evidence_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class FinalizationDocketReview:
    reviewer: str
    decision: str  # approve, hold, reject
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class FinalizationDocketVerdict:
    verdict: str  # approve, hold, reject
    justification: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class FinalizationDocket:
    docket_id: str
    system_id: str
    evidence: List[FinalizationDocketEvidence] = field(default_factory=list)
    reviews: List[FinalizationDocketReview] = field(default_factory=list)
    verdict: Optional[FinalizationDocketVerdict] = None
    timestamp: float = field(default_factory=time.time)

@dataclass
class FinalizationDocketReport:
    report_id: str
    docket: FinalizationDocket
    valid: bool
    verdict: FinalizationDocketVerdict
    timestamp: float = field(default_factory=time.time)


def open_finalization_docket(system_id: str) -> FinalizationDocket:
    """
    Opens a new finalization docket.
    """
    return FinalizationDocket(
        docket_id=f"FIN_DCK_{uuid.uuid4().hex[:8]}",
        system_id=system_id
    )


def attach_finalization_evidence(docket: FinalizationDocket, evidence: Any) -> None:
    """
    Attaches an evidence item.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    ev_id = extract(evidence, "evidence_id") or extract(evidence, "report_id") or f"EV_{uuid.uuid4().hex[:8]}"
    ev_type = extract(evidence, "evidence_type") or "report"
    
    docket.evidence.append(FinalizationDocketEvidence(
        evidence_id=ev_id,
        evidence_type=ev_type,
        payload={"evidence_id": ev_id}
    ))


def validate_finalization_docket(docket: FinalizationDocket) -> bool:
    """
    Ensures all 10 required finalization evidence items are present.
    """
    evidence_types = {item.evidence_type for item in docket.evidence}
    required = {
        "final_system_manifest", "final_gate_registry_report", "production_readiness_guard_report",
        "system_lockdown_report", "runtime_handoff_manifest", "release_candidate_manifest",
        "release_docket", "runtime_ledger", "ranger_packet", "court_verdict"
    }
    
    for req in required:
        if req not in evidence_types:
            return False
            
    # Explicitly check court verdict is not rejected
    for item in docket.evidence:
        if item.evidence_type == "court_verdict":
            verdict_val = item.payload.get("verdict")
            if verdict_val == "reject" or not verdict_val:
                return False
                
    return True


def summarize_finalization_docket(docket: FinalizationDocket) -> FinalizationDocketReport:
    """
    Summarizes the docket and returns a validation report.
    """
    valid = validate_finalization_docket(docket)
    if valid:
        verd = FinalizationDocketVerdict(
            verdict="approve",
            justification="All 10 required finalization evidence items are attached, and court verdict is approved."
        )
    else:
        # Check if missing court verdict
        types = {item.evidence_type for item in docket.evidence}
        if "court_verdict" not in types:
            verd = FinalizationDocketVerdict(
                verdict="hold",
                justification="Finalization docket lacks the required court verdict."
            )
        else:
            verd = FinalizationDocketVerdict(
                verdict="reject",
                justification="Finalization docket failed validation checks or contains a rejected verdict."
            )
            
    return FinalizationDocketReport(
        report_id=f"FIN_DCK_RPT_{uuid.uuid4().hex[:8]}",
        docket=docket,
        valid=valid,
        verdict=verd
    )
