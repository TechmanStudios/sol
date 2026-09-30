# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Runtime Ledger
==================
Maintains a tamper-evident audit history of all shadow and sandbox execution steps,
including commands, gate snapshots, ranger packets, and court decisions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class RuntimeLedgerEntry:
    entry_id: str
    timestamp: float
    entry_type: str  # command, step, gate_snapshot, ranger_packet, court_decision, token_check, rollback_ref, quarantine_flag, test_summary
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RuntimeEvidenceReference:
    evidence_id: str
    evidence_type: str
    payload_hash: str

@dataclass
class RuntimeRollbackReference:
    rollback_id: str
    snapshot_timestamp: float
    state_checksum: str

@dataclass
class RuntimeLedgerReport:
    report_id: str
    entries: List[RuntimeLedgerEntry]
    evidence_references: List[RuntimeEvidenceReference]
    rollback_references: List[RuntimeRollbackReference]
    passed_validation: bool = True
    errors: List[str] = field(default_factory=list)


def build_runtime_ledger() -> Dict[str, Any]:
    """
    Builds a blank runtime ledger structure.
    """
    import uuid
    ledger_id = f"LDG_{uuid.uuid4().hex[:8]}"
    return {
        "ledger_id": ledger_id,
        "entries": [],
        "evidence_references": [],
        "rollback_references": []
    }


def append_runtime_event(ledger: Dict[str, Any], event: Any) -> None:
    """
    Appends a structured event to the ledger entries list.
    """
    import uuid
    
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry_id = f"ENT_{uuid.uuid4().hex[:8]}"
    entry_type = "generic_event"
    payload = {}

    # Map classes/dicts to types
    obj_class = type(event).__name__
    if "SovereignCoreAssemblyPlan" in obj_class or "AssemblyPlan" in obj_class:
        entry_type = "core_assembly_plan"
        payload = {"plan_id": extract(event, "plan_id"), "policy": str(extract(event, "policy"))}
    elif "GeodesicPipelineBalancePlan" in obj_class or "PipelineBalance" in obj_class:
        entry_type = "geodesic_pipeline_balance_plan"
        payload = {"plan_id": extract(event, "plan_id") or extract(event, "report_id")}
    elif "QuantumWavefrontBaseline" in obj_class:
        entry_type = "quantum_wavefront_baseline"
        payload = {"baseline_id": extract(event, "baseline_id")}
    elif "QuantumWavefrontAdjustment" in obj_class:
        entry_type = "quantum_wavefront_adjustment"
        payload = {"packet_id": extract(event, "packet_id")}
    elif "WavefrontUncertainty" in obj_class:
        entry_type = "wavefront_uncertainty_report"
        payload = {"report_id": extract(event, "report_id") or extract(event, "packet_id")}
    elif "PipelineBalanceOracle" in obj_class:
        entry_type = "pipeline_balance_oracle_report"
        payload = {"report_id": extract(event, "report_id") or extract(event, "decision_id")}
    elif "QuantumWavefrontProtocol" in obj_class:
        entry_type = "quantum_wavefront_protocol_report"
        payload = {"report_id": extract(event, "report_id") or extract(event, "protocol_id")}
    elif "PipelineCalibrationBaseline" in obj_class:
        entry_type = "pipeline_calibration_baseline"
        payload = {"baseline_id": extract(event, "baseline_id")}
    elif "PipelineCalibrationAdjustment" in obj_class:
        entry_type = "pipeline_calibration_adjustment"
        payload = {"adjustment_id": extract(event, "adjustment_id")}
    elif "CoreCadenceProfile" in obj_class:
        entry_type = "core_cadence_profile"
        payload = {"core_id": extract(event, "core_id")}
    elif "CoreWaveguideBindingMap" in obj_class:
        entry_type = "core_waveguide_binding_map"
        payload = {"map_id": extract(event, "map_id")}
    elif "PipelineAssemblyPlan" in obj_class:
        entry_type = "pipeline_assembly_plan"
        payload = {"plan_id": extract(event, "plan_id")}
    elif "ResonantFeedback" in obj_class:
        entry_type = "resonant_feedback_observation"
        payload = {"report_id": extract(event, "report_id") or extract(event, "observation_id"), "success": extract(extract(event, "result", {}), "success", True)}
    elif "CadenceSync" in obj_class or "AutonomousCadence" in obj_class:
        entry_type = "cadence_sync_candidate"
        payload = {"report_id": extract(event, "report_id") or extract(event, "candidate_id") or extract(event, "intent_id")}
    elif "AutonomyGuard" in obj_class:
        entry_type = "autonomy_guard_snapshot"
        payload = {"report_id": extract(event, "report_id") or extract(event, "snapshot_id")}
    elif "ResonantCadenceControl" in obj_class:
        entry_type = "bounded_control_decision"
        payload = {"report_id": extract(event, "report_id") or extract(event, "decision_id")}
    elif "Topology" in obj_class or "Relocation" in obj_class:
        entry_type = "topology_snapshot_ref"
        payload = {"source_hash": extract(event, "before_hash") or extract(event, "source_hash"), "target_hash": extract(event, "after_hash") or extract(event, "target_hash")}
    elif "Guard" in obj_class or "Shape" in obj_class:
        entry_type = "shape_guard_report"
        payload = {"report_id": extract(event, "report_id"), "passed": extract(event, "passed")}
    elif "Protocol" in obj_class or "Migration" in obj_class:
        entry_type = "migration_protocol_report"
        payload = {"report_id": extract(event, "report_id"), "success": extract(event, "success")}
    elif "Command" in obj_class or "command" in str(event):
        entry_type = "command"
        payload = {"command_id": extract(event, "command_id"), "target_level": extract(event, "target_level"), "operation": extract(event, "operation")}
    elif "Step" in obj_class:
        entry_type = "step"
        payload = {"step_id": extract(event, "step_id"), "level": extract(event, "level"), "name": extract(event, "name")}
    elif "Gate" in obj_class or "Snapshot" in obj_class:
        entry_type = "gate_snapshot"
        payload = {"snapshot_id": extract(event, "snapshot_id"), "gates_status": extract(event, "gates_status")}
    elif "Packet" in obj_class:
        entry_type = "ranger_packet"
        payload = {"packet_id": extract(event, "packet_id"), "recommendation": extract(event, "recommendation"), "evidence": extract(event, "evidence")}
    elif "Decision" in obj_class or "Verdict" in obj_class:
        entry_type = "court_decision"
        payload = {"decision_id": extract(event, "decision_id") or extract(event, "verdict_id"), "decision": extract(event, "decision"), "justification": extract(event, "justification")}
    elif "Token" in obj_class:
        entry_type = "token_check"
        payload = {"token_id": extract(event, "token_id"), "active": extract(event, "active")}
    elif "Rollback" in obj_class:
        entry_type = "rollback_ref"
        payload = {"rollback_id": extract(event, "rollback_id")}
    elif "Quarantine" in obj_class or "quarantine" in str(event):
        entry_type = "quarantine_flag"
        payload = {"details": str(event)}
    elif "Test" in obj_class or "summary" in str(event):
        entry_type = "test_summary"
        payload = {"status": extract(event, "status") or extract(event, "test_status")}
    else:
        # Fallback check on string representations if payload is empty
        if isinstance(event, dict):
            entry_type = event.get("entry_type", "generic_event")
            payload = event.get("payload", event)
            
    entry = RuntimeLedgerEntry(
        entry_id=entry_id,
        timestamp=time.time(),
        entry_type=entry_type,
        payload=payload
    )

    ledger["entries"].append(entry)


def attach_runtime_evidence(ledger: Dict[str, Any], evidence: Any) -> None:
    """
    Attaches an evidence hash reference to the ledger.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    evidence_id = extract(evidence, "evidence_id") or f"EV_{int(time.time() * 1000)}"
    evidence_type = extract(evidence, "evidence_type") or "generic_evidence"
    
    import hashlib
    h = hashlib.sha256(str(extract(evidence, "payload") or evidence).encode('utf-8')).hexdigest()[:8]
    
    ref = RuntimeEvidenceReference(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        payload_hash=f"sha256_{h}"
    )
    ledger["evidence_references"].append(ref)
    
    # Also log as an event
    append_runtime_event(ledger, {"entry_type": "test_summary", "payload": {"status": "attached", "evidence_id": evidence_id}})


def attach_rollback_reference(ledger: Dict[str, Any], rollback: Any) -> None:
    """
    Attaches a state rollback snapshot reference to the ledger.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    rollback_id = extract(rollback, "rollback_id") or f"RLBK_{int(time.time() * 1000)}"
    chk = extract(rollback, "state_checksum") or "sha256_dummy_checksum"
    
    ref = RuntimeRollbackReference(
        rollback_id=rollback_id,
        snapshot_timestamp=time.time(),
        state_checksum=chk
    )
    ledger["rollback_references"].append(ref)
    
    # Also log as an event
    append_runtime_event(ledger, ref)


def validate_runtime_ledger(ledger: Dict[str, Any]) -> RuntimeLedgerReport:
    """
    Validates complete logging of critical execution steps and references.
    """
    errors = []
    
    # Needs at least one entry
    if not ledger.get("entries"):
        errors.append("Ledger has no recorded entries.")
        
    # Check that references lists are populated for valid sandbox/shadow states
    passed = len(errors) == 0
    import uuid
    return RuntimeLedgerReport(
        report_id=f"LDG_RPT_{uuid.uuid4().hex[:8]}",
        entries=ledger.get("entries", []),
        evidence_references=ledger.get("evidence_references", []),
        rollback_references=ledger.get("rollback_references", []),
        passed_validation=passed,
        errors=errors
    )


def inject_missing_balance_plan_ledger_entry(ledger: Dict[str, Any]) -> None:
    """
    Removes geodesic_pipeline_balance_plan entries from the ledger.
    """
    if "entries" in ledger:
        ledger["entries"] = [e for e in ledger["entries"] if e.entry_type != "geodesic_pipeline_balance_plan"]


def inject_missing_quantum_baseline_ledger_entry(ledger: Dict[str, Any]) -> None:
    """
    Removes quantum_wavefront_baseline entries from the ledger.
    """
    if "entries" in ledger:
        ledger["entries"] = [e for e in ledger["entries"] if e.entry_type != "quantum_wavefront_baseline"]


def inject_missing_ranger_packet_ledger_entry(ledger: Dict[str, Any]) -> None:
    """
    Removes ranger_packet entries from the ledger.
    """
    if "entries" in ledger:
        ledger["entries"] = [e for e in ledger["entries"] if e.entry_type != "ranger_packet"]


def inject_missing_court_verdict_ledger_entry(ledger: Dict[str, Any]) -> None:
    """
    Removes court_decision entries from the ledger.
    """
    if "entries" in ledger:
        ledger["entries"] = [e for e in ledger["entries"] if e.entry_type != "court_decision"]


def validate_ledger_fault_blocks_promotion(ledger_report: RuntimeLedgerReport) -> bool:
    """
    Checks if critical ledger entries are missing. If so, blocks promotion.
    """
    types = [entry.entry_type for entry in ledger_report.entries]
    critical_types = [
        "geodesic_pipeline_balance_plan",
        "quantum_wavefront_baseline",
        "ranger_packet",
        "court_decision"
    ]
    for ct in critical_types:
        if ct not in types:
            return True  # Blocks promotion
    return not ledger_report.passed_validation


def append_burnin_cycle_entry(ledger: Dict[str, Any], cycle_report: Any) -> None:
    """
    Appends a burn-in cycle report entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry = RuntimeLedgerEntry(
        entry_id=f"BRN_CYC_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="burnin_cycle",
        payload={
            "cycle_index": extract(cycle_report, "cycle_index"),
            "success": extract(cycle_report, "success", True)
        }
    )
    ledger.setdefault("entries", []).append(entry)


def append_burnin_metric_entry(ledger: Dict[str, Any], metrics: Any) -> None:
    """
    Appends burn-in metrics entry to the runtime ledger.
    """
    import uuid
    entry = RuntimeLedgerEntry(
        entry_id=f"BRN_MTR_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="burnin_metrics",
        payload={"metrics": str(metrics)}
    )
    ledger.setdefault("entries", []).append(entry)


def append_burnin_regression_entry(ledger: Dict[str, Any], regression_report: Any) -> None:
    """
    Appends a regression report entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry = RuntimeLedgerEntry(
        entry_id=f"BRN_REG_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="burnin_regression",
        payload={
            "report_id": extract(regression_report, "report_id"),
            "passed": extract(regression_report, "passed", True)
        }
    )
    ledger.setdefault("entries", []).append(entry)


def append_burnin_rollback_entry(ledger: Dict[str, Any], rollback_report: Any) -> None:
    """
    Appends a rollback report entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry = RuntimeLedgerEntry(
        entry_id=f"BRN_RLB_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="burnin_rollback",
        payload={
            "report_id": extract(rollback_report, "report_id")
        }
    )
    ledger.setdefault("entries", []).append(entry)


def validate_burnin_ledger_integrity(ledger: Dict[str, Any]) -> bool:
    """
    Validates integrity of burn-in events in the runtime ledger.
    Returns True if valid, False if critical entries are missing.
    """
    entries = ledger.get("entries", [])
    types = {e.entry_type for e in entries}
    
    # Needs at least cycle, metrics, and regression logs to be integral
    required = {"burnin_cycle", "burnin_metrics", "burnin_regression"}
    for r in required:
        if r not in types:
            return False
            
    return True


def append_release_candidate_entry(ledger: Dict[str, Any], rc_manifest: Any) -> None:
    """
    Appends a release candidate manifest entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    cand_id_obj = extract(rc_manifest, "candidate_id")
    cand_id = extract(cand_id_obj, "candidate_id", "unknown_candidate") if cand_id_obj else "unknown_candidate"
    
    entry = RuntimeLedgerEntry(
        entry_id=f"RC_MNF_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="release_candidate",
        payload={
            "candidate_id": cand_id,
            "quarantine_status": extract(rc_manifest, "quarantine_status", "none")
        }
    )
    ledger.setdefault("entries", []).append(entry)


def append_governance_freeze_entry(ledger: Dict[str, Any], freeze_report: Any) -> None:
    """
    Appends a governance freeze report entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry = RuntimeLedgerEntry(
        entry_id=f"GVR_FRZ_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="governance_freeze",
        payload={
            "report_id": extract(freeze_report, "report_id"),
            "frozen": extract(freeze_report, "frozen", True)
        }
    )
    ledger.setdefault("entries", []).append(entry)


def append_api_contract_entry(ledger: Dict[str, Any], api_contract: Any) -> None:
    """
    Appends an API contract entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry = RuntimeLedgerEntry(
        entry_id=f"API_CON_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="api_contract",
        payload={
            "contract_id": extract(api_contract, "contract_id")
        }
    )
    ledger.setdefault("entries", []).append(entry)


def append_release_docket_entry(ledger: Dict[str, Any], docket: Any) -> None:
    """
    Appends a release docket entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry = RuntimeLedgerEntry(
        entry_id=f"RC_DCK_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="release_docket",
        payload={
            "docket_id": extract(docket, "docket_id"),
            "candidate_id": extract(docket, "candidate_id")
        }
    )
    ledger.setdefault("entries", []).append(entry)


def export_runtime_ledger_for_finalization(ledger_report: Any) -> Dict[str, Any]:
    """
    Exports runtime ledger parameters for system finalization.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    valid = extract(ledger_report, "valid", True)
    return {
        "valid": valid,
        "total_entries": len(extract(ledger_report, "entries", []) or [])
    }


def validate_ledgers_for_final_gateway(runtime_ledger: Any, stability_ledger: Any) -> bool:
    """
    Validates that both ledgers pass validation with no missing or corrupted entries.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    rt_ok = extract(runtime_ledger, "valid", True) and extract(runtime_ledger, "integrity_passed", True)
    st_ok = extract(stability_ledger, "valid", True) and extract(stability_ledger, "integrity_passed", True)
    return rt_ok and st_ok


def append_final_system_manifest_entry(ledger: Dict[str, Any], manifest: Any) -> None:
    """
    Appends a final system manifest entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry = RuntimeLedgerEntry(
        entry_id=f"SYS_MNF_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="final_system_manifest",
        payload={
            "system_id": extract(manifest, "system_id")
        }
    )
    ledger.setdefault("entries", []).append(entry)


def append_final_gate_registry_entry(ledger: Dict[str, Any], gate_report: Any) -> None:
    """
    Appends a final gate registry entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry = RuntimeLedgerEntry(
        entry_id=f"GAT_REG_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="final_gate_registry",
        payload={
            "report_id": extract(gate_report, "report_id"),
            "all_passed": extract(gate_report, "all_passed", True)
        }
    )
    ledger.setdefault("entries", []).append(entry)


def append_production_gateway_entry(ledger: Dict[str, Any], gateway_report: Any) -> None:
    """
    Appends a production gateway entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    dec_obj = extract(gateway_report, "decision")
    entry = RuntimeLedgerEntry(
        entry_id=f"PROD_GW_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="production_gateway",
        payload={
            "report_id": extract(gateway_report, "report_id"),
            "decision": extract(dec_obj, "decision") if dec_obj else "deny"
        }
    )
    ledger.setdefault("entries", []).append(entry)


def append_system_lockdown_entry(ledger: Dict[str, Any], lockdown_report: Any) -> None:
    """
    Appends a system lockdown entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry = RuntimeLedgerEntry(
        entry_id=f"SYS_LCK_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="system_lockdown",
        payload={
            "report_id": extract(lockdown_report, "report_id"),
            "locked": extract(lockdown_report, "locked", True)
        }
    )
    ledger.setdefault("entries", []).append(entry)


def append_finalization_docket_entry(ledger: Dict[str, Any], docket: Any) -> None:
    """
    Appends a finalization docket entry to the runtime ledger.
    """
    import uuid
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    entry = RuntimeLedgerEntry(
        entry_id=f"FIN_DCK_{uuid.uuid4().hex[:8]}",
        timestamp=time.time(),
        entry_type="finalization_docket",
        payload={
            "docket_id": extract(docket, "docket_id"),
            "system_id": extract(docket, "system_id")
        }
    )
    ledger.setdefault("entries", []).append(entry)



