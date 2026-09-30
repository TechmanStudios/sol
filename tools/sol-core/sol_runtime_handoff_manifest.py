# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Runtime Handoff Manifest
============================
Documents module inventory, ranger checklists, and explicit default-deny production gates.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid
import time

@dataclass
class RuntimeHandoffEvidence:
    evidence_id: str
    evidence_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class RuntimeHandoffChecklist:
    checklist_id: str
    items: Dict[str, bool] = field(default_factory=dict)
    all_passed: bool = False
    timestamp: float = field(default_factory=time.time)

@dataclass
class RuntimeHandoffManifest:
    system_id: str
    evidence: List[RuntimeHandoffEvidence] = field(default_factory=list)
    inventory: Dict[str, Any] = field(default_factory=lambda: {
        "install_command_summary": "pytest tests/regression/",
        "module_inventory": ["sol_sovereign_runtime", "sol_production_gateway", "sol_system_lockdown"],
        "ranger_inventory": ["release_candidate_ranger", "finalization_ranger"],
        "court_review_inventory": ["review_release_candidate_manifest", "review_production_gateway_report"],
        "gate_registry_summary": "Level 50 Finalization gates",
        "rollback_instructions": "Check rollback manager proof and execute rollback checkpoint restoration",
        "ledger_validation_instructions": "Verify stability ledger hash-chain sequence integrity"
    })
    checklist_passed: bool = False
    limitations: List[str] = field(default_factory=lambda: ["shadow_mode_only", "no_production_mutation"])
    production_status: str = "default_deny"
    created_at: float = field(default_factory=time.time)

@dataclass
class RuntimeHandoffReport:
    report_id: str
    manifest: RuntimeHandoffManifest
    checklist: RuntimeHandoffChecklist
    valid: bool
    timestamp: float = field(default_factory=time.time)


def open_runtime_handoff_manifest(system_id: str) -> RuntimeHandoffManifest:
    """
    Opens a new handoff manifest.
    """
    return RuntimeHandoffManifest(system_id=system_id)


def attach_runtime_handoff_evidence(manifest: RuntimeHandoffManifest, evidence: Any) -> None:
    """
    Attaches handoff evidence.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    ev_id = extract(evidence, "evidence_id") or extract(evidence, "report_id") or f"EV_{uuid.uuid4().hex[:8]}"
    ev_type = extract(evidence, "evidence_type") or "report"
    
    manifest.evidence.append(RuntimeHandoffEvidence(
        evidence_id=ev_id,
        evidence_type=ev_type,
        payload={"evidence_id": ev_id}
    ))


def validate_runtime_handoff_checklist(manifest: RuntimeHandoffManifest) -> bool:
    """
    Validates handoff manifest. Ensures checklist includes install, inventory, gates, rollbacks, and default-deny production.
    """
    inv = manifest.inventory
    required_keys = [
        "install_command_summary", "module_inventory", "ranger_inventory", 
        "court_review_inventory", "gate_registry_summary", "rollback_instructions", 
        "ledger_validation_instructions"
    ]
    for key in required_keys:
        if key not in inv or not inv[key]:
            return False
            
    if manifest.production_status != "default_deny":
        return False
        
    manifest.checklist_passed = True
    return True


def summarize_runtime_handoff(manifest: RuntimeHandoffManifest) -> RuntimeHandoffReport:
    """
    Validates and summarizes handoff checklist.
    """
    valid = validate_runtime_handoff_checklist(manifest)
    
    items = {
        "inventory_keys_present": valid,
        "default_deny_status_explicit": manifest.production_status == "default_deny",
        "limitations_declared": len(manifest.limitations) > 0
    }
    
    checklist = RuntimeHandoffChecklist(
        checklist_id=f"CHK_{uuid.uuid4().hex[:8]}",
        items=items,
        all_passed=valid
    )
    
    return RuntimeHandoffReport(
        report_id=f"HND_RPT_{uuid.uuid4().hex[:8]}",
        manifest=manifest,
        checklist=checklist,
        valid=valid
    )
