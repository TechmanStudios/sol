# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Execution Trace Registry and Rejection Ledger for SOL Waveguide.
Indexes and validates pass execution records and rejection records
into a deterministic, canonical audit ledger.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_governed_pass_execution import (
    validate_waveguide_governed_pass_execution_record
)


@dataclass
class WaveguideExecutionTraceEntry:
    trace_entry_id: str
    rc_id: str
    candidate_level: str
    requested_pass: str
    requested_profile: Optional[str]
    execution_status: str               # trace_executed, trace_rejected, trace_warning, trace_invalid
    admission_status: str
    admission_decision_digest: str
    execution_record_path: str
    execution_record_digest: str
    handler_id: str
    handler_version: str
    handler_registered: bool
    input_payload_digest: str
    output_payload_digest: str
    pass_executed: bool
    pass_rejected: bool
    reason_codes: List[str]
    notes: str
    software_validation_caveat: str
    trace_entry_digest: str = ""


@dataclass
class WaveguideExecutionTraceLedger:
    ledger_id: str
    ledger_version: str
    ledger_status: str                  # ledger_valid, ledger_blocked, ledger_warning
    entries: List[Dict[str, Any]]
    executed_entries: List[Dict[str, Any]]
    rejected_entries: List[Dict[str, Any]]
    invalid_entries: List[Dict[str, Any]]
    executed_count: int
    rejected_count: int
    invalid_count: int
    rc1_execution_count: int
    rc2_execution_count: int
    rc1_rejection_count: int
    rc2_rejection_count: int
    approved_handler_ids: List[str]
    artifact_paths: List[str]
    source_execution_record_digests: List[str]
    software_validation_caveat: str
    reason_codes: List[str]
    ledger_digest: str = ""


def hash_waveguide_execution_trace_entry(entry: Any) -> str:
    """
    Computes digest for a trace entry, excluding trace_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or a dataclass instance")

    e_dict.pop("trace_entry_digest", None)
    return hash_data(e_dict)


def hash_waveguide_execution_trace_ledger(ledger: Any) -> str:
    """
    Computes digest for the ledger, excluding ledger_digest.
    """
    if hasattr(ledger, "__dict__"):
        l_dict = asdict(ledger)
    elif isinstance(ledger, dict):
        l_dict = dict(ledger)
    else:
        raise TypeError("ledger must be a dictionary or a dataclass instance")

    l_dict.pop("ledger_digest", None)
    return hash_data(l_dict)


def build_waveguide_execution_trace_entry(
    execution_record: Any,
    record_path: Optional[str] = None
) -> WaveguideExecutionTraceEntry:
    """
    Builds a deterministic trace entry from an execution record.
    """
    record = None
    if isinstance(execution_record, str):
        record_path = execution_record
        full_rec_path = os.path.join(REPO_ROOT, record_path)
        if os.path.exists(full_rec_path):
            with open(full_rec_path, "r", encoding="utf-8") as f:
                record = json.load(f)
    elif hasattr(execution_record, "__dict__"):
        record = asdict(execution_record)
    else:
        record = dict(execution_record)

    if not record_path:
        record_path = ""
    record_path = normalize_to_repo_path(record_path)

    reasons = ["TRACE_LEDGER_ENTRY_CANONICAL"]

    if not record:
        status = "trace_invalid"
        reasons.append("TRACE_LEDGER_EXECUTION_RECORD_INVALID")
        entry = WaveguideExecutionTraceEntry(
            trace_entry_id="SOL-WAVEGUIDE-TRACE-ENTRY-INVALID",
            rc_id="",
            candidate_level="",
            requested_pass="",
            requested_profile=None,
            execution_status=status,
            admission_status="pass_blocked",
            admission_decision_digest="",
            execution_record_path=record_path,
            execution_record_digest="",
            handler_id="",
            handler_version="",
            handler_registered=False,
            input_payload_digest="",
            output_payload_digest="",
            pass_executed=False,
            pass_rejected=True,
            reason_codes=reasons,
            notes="Empty or missing execution record.",
            software_validation_caveat=""
        )
        entry.trace_entry_digest = hash_waveguide_execution_trace_entry(entry)
        return entry

    # Validate the execution record
    rec_ok, rec_reasons = validate_waveguide_governed_pass_execution_record(record)
    rec_digest = record.get("execution_record_digest", "")

    if rec_ok:
        reasons.append("TRACE_LEDGER_EXECUTION_RECORD_VALID")
        reasons.append("TRACE_LEDGER_EXECUTION_RECORD_DIGEST_VALID")
    else:
        reasons.append("TRACE_LEDGER_EXECUTION_RECORD_INVALID")
        reasons.append("TRACE_LEDGER_EXECUTION_RECORD_DIGEST_INVALID")

    rc_id = record.get("rc_id", "")
    level = "RC1" if "RC1" in rc_id else "RC2"
    requested_pass = record.get("requested_pass", "")
    requested_profile = record.get("requested_profile")

    pass_executed = record.get("pass_executed", False)
    pass_rejected = record.get("pass_rejected", False)

    if pass_executed:
        status = "trace_executed"
        reasons.append("TRACE_LEDGER_EXECUTED_ENTRY_INDEXED")
        if record.get("handler_id"):
            reasons.append("TRACE_LEDGER_HANDLER_REFERENCED")
    elif pass_rejected:
        status = "trace_rejected"
        reasons.append("TRACE_LEDGER_REJECTED_ENTRY_INDEXED")
        if record.get("reason_codes"):
            reasons.append("TRACE_LEDGER_REJECTION_REASON_RECORDED")
    else:
        status = "trace_invalid"
        reasons.append("TRACE_LEDGER_EXECUTION_RECORD_INVALID")

    if record.get("admission_decision_digest"):
        reasons.append("TRACE_LEDGER_ADMISSION_DIGEST_REFERENCED")
    if record.get("input_payload_digest"):
        reasons.append("TRACE_LEDGER_INPUT_DIGEST_REFERENCED")
    if record.get("output_payload_digest"):
        reasons.append("TRACE_LEDGER_OUTPUT_DIGEST_REFERENCED")

    caveat = record.get("software_validation_caveat", "")
    if caveat and ("sandbox" in caveat.lower() or "validation" in caveat.lower()):
        reasons.append("TRACE_LEDGER_SOFTWARE_CAVEAT_INCLUDED")

    reasons.append("TRACE_LEDGER_ENTRY_DIGEST_VALID")
    reasons = sorted(list(set(reasons)))

    profile_suffix = f"-{requested_profile}" if requested_profile else ""
    trace_entry_id = f"SOL-WAVEGUIDE-TRACE-ENTRY-{level}-{requested_pass}{profile_suffix}"

    entry = WaveguideExecutionTraceEntry(
        trace_entry_id=trace_entry_id,
        rc_id=rc_id,
        candidate_level=record.get("candidate_level", ""),
        requested_pass=requested_pass,
        requested_profile=requested_profile,
        execution_status=status,
        admission_status=record.get("admission_status", "pass_blocked"),
        admission_decision_digest=record.get("admission_decision_digest", ""),
        execution_record_path=record_path,
        execution_record_digest=rec_digest,
        handler_id=record.get("handler_id", ""),
        handler_version=record.get("handler_version", ""),
        handler_registered=record.get("handler_registered", False),
        input_payload_digest=record.get("input_payload_digest", ""),
        output_payload_digest=record.get("output_payload_digest", ""),
        pass_executed=pass_executed,
        pass_rejected=pass_rejected,
        reason_codes=reasons,
        notes=record.get("notes", ""),
        software_validation_caveat=caveat
    )
    entry.trace_entry_digest = hash_waveguide_execution_trace_entry(entry)
    return entry


def validate_waveguide_execution_trace_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Validates a trace entry's integrity and specifications.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    else:
        e_dict = dict(entry)

    reasons = []
    is_valid = True

    # 1. Verify digest
    given_digest = e_dict.get("trace_entry_digest", "")
    computed_digest = hash_waveguide_execution_trace_entry(e_dict)
    if given_digest == computed_digest:
        reasons.append("TRACE_LEDGER_ENTRY_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("TRACE_LEDGER_ENTRY_DIGEST_INVALID")

    # 2. Check fields based on status
    status = e_dict.get("execution_status")
    if status == "trace_executed":
        reasons.append("TRACE_LEDGER_EXECUTED_ENTRY_INDEXED")
        if not e_dict.get("handler_id") or not e_dict.get("handler_version"):
            is_valid = False
        if not e_dict.get("input_payload_digest") or not e_dict.get("output_payload_digest"):
            is_valid = False
        if e_dict.get("pass_executed") is not True or e_dict.get("pass_rejected") is not False:
            is_valid = False
    elif status == "trace_rejected":
        reasons.append("TRACE_LEDGER_REJECTED_ENTRY_INDEXED")
        if e_dict.get("pass_executed") is not False or e_dict.get("pass_rejected") is not True:
            is_valid = False
    else:
        is_valid = False
        reasons.append("TRACE_LEDGER_EXECUTION_RECORD_INVALID")

    if is_valid:
        reasons.append("TRACE_LEDGER_ENTRY_CANONICAL")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_execution_trace_ledger(
    records_or_entries: List[Any]
) -> WaveguideExecutionTraceLedger:
    """
    Compiles a set of entries or execution records into a top-level ledger.
    """
    entries = []
    for item in records_or_entries:
        if isinstance(item, WaveguideExecutionTraceEntry) or (isinstance(item, dict) and "trace_entry_id" in item):
            entries.append(item)
        else:
            # Assume it is an execution record
            entries.append(build_waveguide_execution_trace_entry(item))

    # Convert to dict representation for sorting/indexing
    serialized_entries = []
    for entry in entries:
        if hasattr(entry, "__dict__"):
            serialized_entries.append(asdict(entry))
        else:
            serialized_entries.append(dict(entry))

    # Sort entries by stable keys
    def sort_key(e):
        return (
            e.get("rc_id") or "",
            e.get("requested_pass") or "",
            e.get("requested_profile") or "",
            e.get("execution_status") or "",
            e.get("execution_record_digest") or ""
        )
    serialized_entries.sort(key=sort_key)

    executed_entries = []
    rejected_entries = []
    invalid_entries = []

    executed_count = 0
    rejected_count = 0
    invalid_count = 0

    rc1_execution_count = 0
    rc2_execution_count = 0
    rc1_rejection_count = 0
    rc2_rejection_count = 0

    approved_handler_ids = []
    artifact_paths = []
    source_record_digests = []

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reasons = ["TRACE_LEDGER_COUNTS_VALID"]

    for e in serialized_entries:
        # Validate child entry
        is_ok, entry_reasons = validate_waveguide_execution_trace_entry(e)
        status = e.get("execution_status")

        if is_ok:
            if status == "trace_executed":
                executed_entries.append(e)
                executed_count += 1
                if "RC1" in e.get("rc_id", ""):
                    rc1_execution_count += 1
                elif "RC2" in e.get("rc_id", ""):
                    rc2_execution_count += 1
                if e.get("handler_id"):
                    approved_handler_ids.append(e.get("handler_id"))
            elif status == "trace_rejected":
                rejected_entries.append(e)
                rejected_count += 1
                if "RC1" in e.get("rc_id", ""):
                    rc1_rejection_count += 1
                elif "RC2" in e.get("rc_id", ""):
                    rc2_rejection_count += 1
        else:
            invalid_entries.append(e)
            invalid_count += 1

        if e.get("execution_record_path"):
            artifact_paths.append(e.get("execution_record_path"))
        if e.get("execution_record_digest"):
            source_record_digests.append(e.get("execution_record_digest"))

    approved_handler_ids = sorted(list(set(approved_handler_ids)))
    artifact_paths = sorted(list(set(artifact_paths)))
    source_record_digests = sorted(list(set(source_record_digests)))

    if invalid_count > 0:
        ledger_status = "ledger_blocked"
        reasons.append("TRACE_LEDGER_BLOCKED")
    else:
        ledger_status = "ledger_valid"
        reasons.append("TRACE_LEDGER_VALID")

    reasons.append("TRACE_LEDGER_DIGEST_VALID")
    reasons = sorted(list(set(reasons)))

    ledger = WaveguideExecutionTraceLedger(
        ledger_id="SOL-WAVEGUIDE-EXECUTION-TRACE-LEDGER",
        ledger_version="1",
        ledger_status=ledger_status,
        entries=serialized_entries,
        executed_entries=executed_entries,
        rejected_entries=rejected_entries,
        invalid_entries=invalid_entries,
        executed_count=executed_count,
        rejected_count=rejected_count,
        invalid_count=invalid_count,
        rc1_execution_count=rc1_execution_count,
        rc2_execution_count=rc2_execution_count,
        rc1_rejection_count=rc1_rejection_count,
        rc2_rejection_count=rc2_rejection_count,
        approved_handler_ids=approved_handler_ids,
        artifact_paths=artifact_paths,
        source_execution_record_digests=source_record_digests,
        software_validation_caveat=software_validation_caveat,
        reason_codes=reasons,
        ledger_digest=""
    )
    ledger.ledger_digest = hash_waveguide_execution_trace_ledger(ledger)
    return ledger


def validate_waveguide_execution_trace_ledger(ledger: Any) -> Tuple[bool, List[str]]:
    """
    Validates the top-level trace ledger and all indexed entries.
    """
    if hasattr(ledger, "__dict__"):
        l_dict = asdict(ledger)
    else:
        l_dict = dict(ledger)

    reasons = []
    is_valid = True

    # 1. Verify ledger digest
    given_digest = l_dict.get("ledger_digest", "")
    computed_digest = hash_waveguide_execution_trace_ledger(l_dict)
    if given_digest == computed_digest:
        reasons.append("TRACE_LEDGER_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("TRACE_LEDGER_DIGEST_INVALID")

    # 2. Verify all entries
    for entry in l_dict.get("entries", []):
        ok, entry_reasons = validate_waveguide_execution_trace_entry(entry)
        if not ok:
            is_valid = False

    # 3. Verify counts
    executed_count = len(l_dict.get("executed_entries", []))
    rejected_count = len(l_dict.get("rejected_entries", []))
    invalid_count = len(l_dict.get("invalid_entries", []))

    if l_dict.get("executed_count") == executed_count and l_dict.get("rejected_count") == rejected_count and l_dict.get("invalid_count") == invalid_count:
        reasons.append("TRACE_LEDGER_COUNTS_VALID")
    else:
        is_valid = False

    if l_dict.get("ledger_status") == "ledger_valid" and is_valid:
        reasons.append("TRACE_LEDGER_VALID")
    else:
        is_valid = False
        reasons.append("TRACE_LEDGER_BLOCKED")

    caveat = l_dict.get("software_validation_caveat", "")
    if caveat and ("sandbox" in caveat.lower() or "validation" in caveat.lower()):
        reasons.append("TRACE_LEDGER_SOFTWARE_CAVEAT_INCLUDED")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_execution_trace_ledger(ledger: Any) -> str:
    """
    Generates deterministic plaintext summary of the trace ledger.
    """
    if hasattr(ledger, "__dict__"):
        l_dict = asdict(ledger)
    else:
        l_dict = dict(ledger)

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE EXECUTION TRACE LEDGER RECORD",
        "============================================================",
        f"Ledger ID:         {l_dict.get('ledger_id')}",
        f"Ledger Version:    {l_dict.get('ledger_version')}",
        f"Ledger Status:     {l_dict.get('ledger_status', '').upper()}",
        f"Ledger Digest:     {l_dict.get('ledger_digest')}",
        "------------------------------------------------------------",
        f"Executed Count:    {l_dict.get('executed_count')}",
        f"Rejected Count:    {l_dict.get('rejected_count')}",
        f"Invalid Count:     {l_dict.get('invalid_count')}",
        f"RC1 Executions:    {l_dict.get('rc1_execution_count')}",
        f"RC2 Executions:    {l_dict.get('rc2_execution_count')}",
        f"RC1 Rejections:    {l_dict.get('rc1_rejection_count')}",
        f"RC2 Rejections:    {l_dict.get('rc2_rejection_count')}",
        "------------------------------------------------------------",
        "Approved Handlers:",
    ]
    for h_id in l_dict.get("approved_handler_ids", []):
        lines.append(f"  - {h_id}")
    lines.append("Artifact Paths:")
    for path in l_dict.get("artifact_paths", []):
        lines.append(f"  - {path}")
    lines.append("============================================================")
    return "\n".join(lines)


def export_waveguide_execution_trace_ledger(ledger: Any, filepath: str) -> None:
    """
    Exports trace ledger record to key-sorted JSON catalog.
    """
    if hasattr(ledger, "__dict__"):
        l_dict = asdict(ledger)
    else:
        l_dict = dict(ledger)

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(l_dict, f, indent=4, sort_keys=True)


def compare_waveguide_execution_trace_ledgers(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two trace ledgers and returns differences.
    """
    def to_dict(l):
        if hasattr(l, "__dict__"):
            return asdict(l)
        return dict(l)

    left_dict = to_dict(left)
    right_dict = to_dict(right)

    diffs = {}
    for key in set(left_dict.keys()) | set(right_dict.keys()):
        val_l = left_dict.get(key)
        val_r = right_dict.get(key)
        if val_l != val_r:
            diffs[key] = {
                "left": val_l,
                "right": val_r
            }
    return diffs


def index_waveguide_execution_trace_entries_by_status(
    ledger: Any
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Indexes entries inside the ledger by their execution status.
    """
    if hasattr(ledger, "__dict__"):
        l_dict = asdict(ledger)
    else:
        l_dict = dict(ledger)

    out = {
        "executed": [],
        "rejected": [],
        "invalid": []
    }
    for entry in l_dict.get("entries", []):
        status = entry.get("execution_status")
        if status == "trace_executed":
            out["executed"].append(entry)
        elif status == "trace_rejected":
            out["rejected"].append(entry)
        else:
            out["invalid"].append(entry)
    return out


if __name__ == "__main__":
    # Load default execution record JSON files from docs/
    rec1_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json"
    rec2_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC2.json"
    rej_path = "docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json"

    # Build trace entries
    entry1 = build_waveguide_execution_trace_entry(rec1_path, record_path=rec1_path)
    entry2 = build_waveguide_execution_trace_entry(rec2_path, record_path=rec2_path)
    entry3 = build_waveguide_execution_trace_entry(rej_path, record_path=rej_path)

    # Build top-level ledger
    ledger = build_waveguide_execution_trace_ledger([entry1, entry2, entry3])

    # Export trace ledger
    ledger_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json")
    export_waveguide_execution_trace_ledger(ledger, ledger_export_path)

    print(f"Exported trace ledger to: {ledger_export_path}")
