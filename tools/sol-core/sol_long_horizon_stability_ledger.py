# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Long-Horizon Stability Ledger
=================================
Implements hash-chained logging of all burn-in activities to enforce audit integrity.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib
import json

@dataclass
class StabilityLedgerEntry:
    entry_id: str
    timestamp: float
    cycle_index: int
    event_type: str  # cycle_start, cycle_end, command, levelup_step, ranger_packet, etc.
    details: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""
    current_hash: str = ""

@dataclass
class StabilityLedgerHash:
    hash_value: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class StabilityLedgerCheckpoint:
    checkpoint_id: str
    cycle_index: int
    ledger_length: int
    cumulative_hash: str
    timestamp: float = field(default_factory=time.time)

@dataclass
class StabilityLedger:
    run_id: str
    entries: List[StabilityLedgerEntry] = field(default_factory=list)
    checkpoints: List[StabilityLedgerCheckpoint] = field(default_factory=list)

@dataclass
class StabilityLedgerValidationReport:
    valid: bool
    entries_checked: int
    missing_indices: List[int] = field(default_factory=list)
    out_of_order: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


def compute_entry_hash(entry: StabilityLedgerEntry) -> str:
    """
    Computes SHA-256 hash of entry fields and previous_hash.
    """
    content = {
        "entry_id": entry.entry_id,
        "timestamp": entry.timestamp,
        "cycle_index": entry.cycle_index,
        "event_type": entry.event_type,
        "details": entry.details,
        "previous_hash": entry.previous_hash
    }
    serialized = json.dumps(content, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def create_stability_ledger(run_id: str) -> StabilityLedger:
    """
    Creates a new long-horizon stability ledger.
    """
    return StabilityLedger(run_id=run_id)


def append_stability_ledger_entry(ledger: StabilityLedger, entry: StabilityLedgerEntry) -> None:
    """
    Appends a new entry to the ledger, computing the hash-chain link.
    """
    prev_hash = "GENESIS_HASH"
    if ledger.entries:
        prev_hash = ledger.entries[-1].current_hash
        
    entry.previous_hash = prev_hash
    entry.current_hash = compute_entry_hash(entry)
    ledger.entries.append(entry)


def checkpoint_stability_ledger(ledger: StabilityLedger, cycle_index: int) -> StabilityLedgerCheckpoint:
    """
    Creates an audit checkpoint of the current ledger state.
    """
    import uuid
    cum_hash = ledger.entries[-1].current_hash if ledger.entries else "GENESIS_HASH"
    checkpoint = StabilityLedgerCheckpoint(
        checkpoint_id=f"CHK_{uuid.uuid4().hex[:8]}",
        cycle_index=cycle_index,
        ledger_length=len(ledger.entries),
        cumulative_hash=cum_hash
    )
    ledger.checkpoints.append(checkpoint)
    return checkpoint


def validate_stability_ledger_chain(ledger: StabilityLedger) -> StabilityLedgerValidationReport:
    """
    Validates ledger hash chain integrity, checking for gaps, reorderings, or omissions.
    """
    if not ledger.entries:
        return StabilityLedgerValidationReport(valid=True, entries_checked=0)
        
    prev_hash = "GENESIS_HASH"
    out_of_order = False
    missing_indices = []
    
    # Check for index gaps and ordering
    expected_index = ledger.entries[0].cycle_index
    
    for idx, entry in enumerate(ledger.entries):
        # Validate hash-link chain
        if entry.previous_hash != prev_hash:
            return StabilityLedgerValidationReport(
                valid=False,
                entries_checked=idx,
                out_of_order=True,
                details={"reason": f"Hash chain broken at index {idx}", "expected_prev_hash": prev_hash, "actual": entry.previous_hash}
            )
            
        # Recalculate hash to verify contents have not been modified
        calc_hash = compute_entry_hash(entry)
        if entry.current_hash != calc_hash:
            return StabilityLedgerValidationReport(
                valid=False,
                entries_checked=idx,
                details={"reason": f"Hash mismatch at index {idx}", "expected_hash": entry.current_hash, "recalculated": calc_hash}
            )
            
        prev_hash = entry.current_hash
        
    # Check for index sequence consistency (gaps)
    cycle_indices = [e.cycle_index for e in ledger.entries if e.event_type in ["cycle_start", "cycle_end"]]
    if cycle_indices:
        for i in range(cycle_indices[0], cycle_indices[-1] + 1):
            if i not in cycle_indices:
                missing_indices.append(i)
                
    valid = len(missing_indices) == 0
    return StabilityLedgerValidationReport(
        valid=valid,
        entries_checked=len(ledger.entries),
        missing_indices=missing_indices,
        out_of_order=out_of_order,
        details={"total_length": len(ledger.entries)}
    )


def summarize_stability_ledger(ledger: StabilityLedger) -> Dict[str, Any]:
    """
    Returns summary stats for the stability ledger.
    """
    report = validate_stability_ledger_chain(ledger)
    return {
        "run_id": ledger.run_id,
        "total_entries": len(ledger.entries),
        "checkpoints_count": len(ledger.checkpoints),
        "integrity_passed": report.valid,
        "missing_cycles": report.missing_indices,
        "validation_details": report.details
    }


def export_stability_ledger_for_release(ledger_report: Any) -> Dict[str, Any]:
    """
    Exports stability ledger metrics for release packaging.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    valid = extract(ledger_report, "valid", True) and extract(ledger_report, "integrity_passed", True)
    return {
        "integrity_passed": valid,
        "total_entries": extract(ledger_report, "total_entries", 0),
        "missing_cycles": extract(ledger_report, "missing_cycles", [])
    }


def validate_stability_ledger_for_release(ledger_report: Any) -> bool:
    """
    Validates that stability ledger passes integrity checks (no missing/reordered entries).
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    return extract(ledger_report, "valid", True) and extract(ledger_report, "integrity_passed", True)


def export_stability_ledger_for_finalization(ledger_report: Any) -> Dict[str, Any]:
    """
    Exports stability ledger parameters for system finalization.
    """
    return export_stability_ledger_for_release(ledger_report)


