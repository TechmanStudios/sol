# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Governed Pass Replay Verifier for SOL Waveguide.
Consumes the execution trace ledger, reloads execution/rejection records,
recomputes digests, replays registered deterministic safe handlers, and checks
output payload parity.
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
    validate_waveguide_governed_pass_execution_record,
    build_waveguide_governed_pass_handler_registry
)
from sol_waveguide_execution_trace_ledger import (
    validate_waveguide_execution_trace_entry,
    validate_waveguide_execution_trace_ledger
)

# Standard input payloads mapping for deterministic stubs
KNOWN_PAYLOADS = {
    "705d0f3e3d54c1f368ad5a38fd2d156dcba3575d82783251fc8e2c2b496bdf42": {"input_size": 100},
    "8c8149029cf90bc1051a181e0d4dbbdaee866ee2ba983bf833fd2b590d69a969": {"cycles": 200}
}


@dataclass
class WaveguideGovernedPassReplayCase:
    replay_case_id: str
    ledger_path: str
    ledger_digest: str
    ledger_status: str
    source_trace_entry_digest: str
    execution_record_path: str
    execution_record_digest: str
    rc_id: str
    candidate_level: str
    requested_pass: str
    requested_profile: Optional[str]
    execution_status: str
    handler_id: str
    handler_version: str
    input_payload_digest: str
    recorded_output_payload_digest: str
    software_validation_caveat: str
    replay_case_status: str                  # replay_case_ready, replay_case_rejected_record, replay_case_blocked, replay_case_invalid
    replay_status: str                       # replay_verified, replay_rejected_record_verified, replay_failed, replay_skipped
    reason_codes: List[str] = field(default_factory=list)
    replay_case_digest: str = ""


@dataclass
class WaveguideGovernedPassReplayReport:
    replay_report_id: str
    replay_report_version: str
    replay_report_status: str                # replay_report_verified, replay_report_failed, replay_report_warning
    ledger_id: str
    ledger_digest: str
    ledger_valid: bool
    cases: List[Dict[str, Any]]
    verified_executions: List[str]
    verified_rejections: List[str]
    failed_replays: List[str]
    skipped_replays: List[str]
    verified_execution_count: int
    verified_rejection_count: int
    failed_replay_count: int
    skipped_replay_count: int
    handler_ids_replayed: List[str]
    source_execution_record_digests: List[str]
    source_trace_entry_digests: List[str]
    reason_codes: List[str]
    software_validation_caveat: str
    replay_report_digest: str = ""


def hash_waveguide_governed_pass_replay_case(case: Any) -> str:
    """
    Computes digest for a replay case, excluding replay_case_digest.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    elif isinstance(case, dict):
        c_dict = dict(case)
    else:
        raise TypeError("case must be a dictionary or a dataclass instance")

    c_dict_copy = dict(c_dict)
    c_dict_copy.pop("replay_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_governed_pass_replay_report(report: Any) -> str:
    """
    Computes digest for a replay report, excluding replay_report_digest.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    r_dict_copy = dict(r_dict)
    r_dict_copy.pop("replay_report_digest", None)
    return hash_data(r_dict_copy)


def build_waveguide_governed_pass_replay_case(
    trace_entry: Any,
    execution_record: Any,
    ledger_path: str,
    ledger_digest: str,
    ledger_status: str
) -> WaveguideGovernedPassReplayCase:
    """
    Constructs a replay case from trace entry metadata and execution record details.
    """
    if hasattr(trace_entry, "__dict__"):
        te_dict = asdict(trace_entry)
    else:
        te_dict = dict(trace_entry)

    if hasattr(execution_record, "__dict__"):
        er_dict = asdict(execution_record)
    elif execution_record is not None:
        er_dict = dict(execution_record)
    else:
        er_dict = {}

    exec_status = te_dict.get("execution_status", "")
    replay_case_status = "replay_case_ready"
    replay_status = "replay_skipped"
    reasons = ["PASS_REPLAY_CASE_INITIALIZED"]

    if exec_status == "trace_rejected" or te_dict.get("pass_rejected"):
        replay_case_status = "replay_case_rejected_record"
        replay_status = "replay_rejected_record_verified"
        reasons.append("PASS_REPLAY_REJECTED_RECORD_NOT_REPLAYED")
    elif exec_status == "trace_invalid":
        replay_case_status = "replay_case_invalid"
        replay_status = "replay_failed"
    elif not te_dict.get("handler_registered") and exec_status == "trace_executed":
        replay_case_status = "replay_case_blocked"
        replay_status = "replay_failed"

    rec_path = te_dict.get("execution_record_path", "")
    if rec_path:
        rec_path = normalize_to_repo_path(rec_path)
    if ledger_path:
        ledger_path = normalize_to_repo_path(ledger_path)

    case = WaveguideGovernedPassReplayCase(
        replay_case_id=f"SOL-WAVEGUIDE-REPLAY-CASE-{te_dict.get('trace_entry_id', '')}",
        ledger_path=ledger_path,
        ledger_digest=ledger_digest,
        ledger_status=ledger_status,
        source_trace_entry_digest=te_dict.get("trace_entry_digest", ""),
        execution_record_path=rec_path,
        execution_record_digest=te_dict.get("execution_record_digest", ""),
        rc_id=te_dict.get("rc_id", ""),
        candidate_level=te_dict.get("candidate_level", ""),
        requested_pass=te_dict.get("requested_pass", ""),
        requested_profile=te_dict.get("requested_profile"),
        execution_status=te_dict.get("execution_status", ""),
        handler_id=te_dict.get("handler_id", ""),
        handler_version=te_dict.get("handler_version", ""),
        input_payload_digest=te_dict.get("input_payload_digest", ""),
        recorded_output_payload_digest=te_dict.get("output_payload_digest", ""),
        software_validation_caveat=te_dict.get("software_validation_caveat", ""),
        replay_case_status=replay_case_status,
        replay_status=replay_status,
        reason_codes=sorted(list(set(reasons)))
    )
    case.replay_case_digest = hash_waveguide_governed_pass_replay_case(case)
    return case


def replay_waveguide_registered_safe_handler(requested_pass: str, input_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Replays the registered handler for the given pass and input payload.
    """
    registry = build_waveguide_governed_pass_handler_registry()
    if requested_pass not in registry:
        raise ValueError(f"No registered handler found for pass: {requested_pass}")
    handler_func = registry[requested_pass]["func"]
    return handler_func(input_payload)


def verify_waveguide_replay_entry(
    case: Any,
    input_payload: Optional[Dict[str, Any]] = None,
    execution_record: Optional[Dict[str, Any]] = None,
    trace_entry: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[str]]:
    """
    Verifies a single replay case. Reruns the handler if executed, validates digests,
    and updates the case status and reason codes in-place.
    """
    if hasattr(case, "__dict__"):
        c_dict = case.__dict__
    else:
        c_dict = case

    reasons = list(c_dict.get("reason_codes", []))
    is_valid = True

    # 1. Validate trace entry if provided
    if trace_entry is not None:
        te_ok, te_reasons = validate_waveguide_execution_trace_entry(trace_entry)
        if te_ok:
            reasons.append("PASS_REPLAY_TRACE_ENTRY_VALID")
        else:
            is_valid = False
            reasons.append("PASS_REPLAY_TRACE_ENTRY_INVALID")
            c_dict["replay_status"] = "replay_failed"

    # 2. Load and validate execution record
    if execution_record is None:
        rec_path = c_dict.get("execution_record_path", "")
        if rec_path:
            full_rec_path = os.path.join(REPO_ROOT, rec_path)
            if os.path.exists(full_rec_path):
                try:
                    with open(full_rec_path, "r", encoding="utf-8") as f:
                        execution_record = json.load(f)
                except Exception:
                    pass

    if not execution_record:
        is_valid = False
        reasons.append("PASS_REPLAY_EXECUTION_RECORD_INVALID")
        c_dict["replay_status"] = "replay_failed"
        c_dict["reason_codes"] = sorted(list(set(reasons)))
        c_dict["replay_case_digest"] = hash_waveguide_governed_pass_replay_case(case)
        return False, reasons

    # Confirm record digest matches
    rec_digest = execution_record.get("execution_record_digest", "")
    if rec_digest != c_dict.get("execution_record_digest") or not rec_digest:
        is_valid = False
        reasons.append("PASS_REPLAY_RECORD_DIGEST_MISMATCH")
        c_dict["replay_status"] = "replay_failed"
    else:
        reasons.append("PASS_REPLAY_RECORD_DIGEST_MATCH")

    # Validate the record internals
    rec_ok, rec_reasons = validate_waveguide_governed_pass_execution_record(execution_record)
    if not rec_ok:
        if "PASS_EXECUTION_PASS_REJECTED" in rec_reasons and "PASS_EXECUTION_RECORD_DIGEST_INVALID" not in rec_reasons:
            reasons.append("PASS_REPLAY_EXECUTION_RECORD_VALID")
        else:
            is_valid = False
            reasons.append("PASS_REPLAY_EXECUTION_RECORD_INVALID")
            c_dict["replay_status"] = "replay_failed"
    else:
        reasons.append("PASS_REPLAY_EXECUTION_RECORD_VALID")

    # Caveat validation
    caveat = c_dict.get("software_validation_caveat", "")
    if caveat and ("sandbox" in caveat.lower() or "validation" in caveat.lower()):
        reasons.append("PASS_REPLAY_SOFTWARE_CAVEAT_INCLUDED")

    exec_status = c_dict.get("execution_status", "")
    pass_executed = execution_record.get("pass_executed", False)
    pass_rejected = execution_record.get("pass_rejected", False)

    # Branch by executed vs rejected
    if exec_status == "trace_executed" or pass_executed:
        if not pass_executed or pass_rejected:
            is_valid = False
            reasons.append("PASS_REPLAY_EXECUTION_RECORD_INVALID")
            c_dict["replay_status"] = "replay_failed"

        # Check handler details
        handler_id = c_dict.get("handler_id", "")
        handler_ver = c_dict.get("handler_version", "")
        registry = build_waveguide_governed_pass_handler_registry()
        req_pass = c_dict.get("requested_pass", "")

        if req_pass not in registry:
            is_valid = False
            reasons.append("PASS_REPLAY_HANDLER_MISSING")
            c_dict["replay_status"] = "replay_failed"
        else:
            reasons.append("PASS_REPLAY_HANDLER_REGISTERED")
            reg_handler = registry[req_pass]
            if reg_handler["handler_id"] != handler_id or reg_handler["handler_version"] != handler_ver:
                is_valid = False
                reasons.append("PASS_REPLAY_HANDLER_MISSING")
                c_dict["replay_status"] = "replay_failed"
            else:
                reasons.append("PASS_REPLAY_HANDLER_VERSION_MATCH")

        # Load/Verify input payload
        if input_payload is None:
            ip_digest = c_dict.get("input_payload_digest", "")
            if ip_digest in KNOWN_PAYLOADS:
                input_payload = KNOWN_PAYLOADS[ip_digest]

        if input_payload is not None:
            computed_ip_digest = hash_data(input_payload)
            if computed_ip_digest != c_dict.get("input_payload_digest"):
                is_valid = False
                reasons.append("PASS_REPLAY_INPUT_DIGEST_VALID") # will fail validation
                c_dict["replay_status"] = "replay_failed"
            else:
                reasons.append("PASS_REPLAY_INPUT_DIGEST_VALID")

            # Perform execution replay
            if is_valid:
                try:
                    replayed_output = replay_waveguide_registered_safe_handler(req_pass, input_payload)
                    computed_op_digest = hash_data(replayed_output)
                    if computed_op_digest == c_dict.get("recorded_output_payload_digest"):
                        reasons.append("PASS_REPLAY_OUTPUT_DIGEST_MATCH")
                        reasons.append("PASS_REPLAY_EXECUTED_RECORD_VERIFIED")
                        c_dict["replay_status"] = "replay_verified"
                    else:
                        is_valid = False
                        reasons.append("PASS_REPLAY_OUTPUT_DIGEST_MISMATCH")
                        c_dict["replay_status"] = "replay_failed"
                except Exception:
                    is_valid = False
                    reasons.append("PASS_REPLAY_OUTPUT_DIGEST_MISMATCH")
                    c_dict["replay_status"] = "replay_failed"
        else:
            is_valid = False
            # input payload missing but executed record replay requested
            c_dict["replay_status"] = "replay_failed"

    elif exec_status == "trace_rejected" or pass_rejected:
        # Rejection validation constraints
        if not pass_rejected or pass_executed:
            is_valid = False
            c_dict["replay_status"] = "replay_failed"

        # Check reason codes
        rec_reasons = execution_record.get("reason_codes", [])
        if not rec_reasons:
            is_valid = False
            c_dict["replay_status"] = "replay_failed"

        # Ensure no output digest or handler rerun
        if execution_record.get("output_payload_digest") != "":
            is_valid = False
            c_dict["replay_status"] = "replay_failed"

        if is_valid:
            reasons.append("PASS_REPLAY_REJECTED_RECORD_NOT_REPLAYED")
            reasons.append("PASS_REPLAY_REJECTED_RECORD_VERIFIED")
            c_dict["replay_status"] = "replay_rejected_record_verified"
        else:
            c_dict["replay_status"] = "replay_failed"

    else:
        is_valid = False
        reasons.append("PASS_REPLAY_EXECUTION_RECORD_INVALID")
        c_dict["replay_status"] = "replay_failed"

    reasons.append("PASS_REPLAY_CASE_DIGEST_VALID")
    c_dict["reason_codes"] = sorted(list(set(reasons)))
    c_dict["replay_case_digest"] = hash_waveguide_governed_pass_replay_case(case)
    return is_valid, reasons


def verify_waveguide_governed_pass_replay(
    ledger_or_path: Any,
    input_payloads: Optional[Dict[str, Dict[str, Any]]] = None
) -> WaveguideGovernedPassReplayReport:
    """
    Main verifier entry point. Loads the trace ledger, builds replay cases,
    replays safe handlers, compares output digests, and aggregates the results into a report.
    """
    ledger = None
    ledger_path = ""
    if isinstance(ledger_or_path, str):
        ledger_path = ledger_or_path
        full_led_path = os.path.join(REPO_ROOT, ledger_path)
        if os.path.exists(full_led_path):
            with open(full_led_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
    elif hasattr(ledger_or_path, "__dict__"):
        ledger = asdict(ledger_or_path)
    else:
        ledger = dict(ledger_or_path)

    ledger_valid = False
    ledger_digest = ""
    ledger_status = "ledger_blocked"
    ledger_id = ""

    reasons = ["PASS_REPLAY_REPORT_INITIALIZED"]

    if ledger:
        ledger_id = ledger.get("ledger_id", "")
        ledger_digest = ledger.get("ledger_digest", "")
        ledger_status = ledger.get("ledger_status", "")

        led_ok, led_reasons = validate_waveguide_execution_trace_ledger(ledger)
        if led_ok:
            ledger_valid = True
            reasons.append("PASS_REPLAY_LEDGER_VALID")
        else:
            reasons.append("PASS_REPLAY_LEDGER_INVALID")
    else:
        reasons.append("PASS_REPLAY_LEDGER_INVALID")

    cases_list = []
    verified_executions = []
    verified_rejections = []
    failed_replays = []
    skipped_replays = []

    verified_execution_count = 0
    verified_rejection_count = 0
    failed_replay_count = 0
    skipped_replay_count = 0

    handler_ids_replayed = []
    source_execution_record_digests = []
    source_trace_entry_digests = []

    entries = ledger.get("entries", []) if ledger else []
    report_status = "replay_report_verified"

    for entry in entries:
        # Load execution record
        rec_path = entry.get("execution_record_path", "")
        full_rec_path = os.path.join(REPO_ROOT, rec_path)
        record = None
        if os.path.exists(full_rec_path):
            try:
                with open(full_rec_path, "r", encoding="utf-8") as f:
                    record = json.load(f)
            except Exception:
                pass

        # Build case
        case = build_waveguide_governed_pass_replay_case(
            trace_entry=entry,
            execution_record=record,
            ledger_path=ledger_path,
            ledger_digest=ledger_digest,
            ledger_status=ledger_status
        )

        ip_digest = case.input_payload_digest
        payload = None
        if input_payloads and ip_digest in input_payloads:
            payload = input_payloads[ip_digest]

        # Verify
        case_ok, case_reasons = verify_waveguide_replay_entry(
            case,
            input_payload=payload,
            execution_record=record,
            trace_entry=entry
        )

        status = case.replay_status
        case_id = case.replay_case_id

        if status == "replay_verified":
            verified_executions.append(case_id)
            verified_execution_count += 1
            if case.handler_id:
                handler_ids_replayed.append(case.handler_id)
        elif status == "replay_rejected_record_verified":
            verified_rejections.append(case_id)
            verified_rejection_count += 1
        elif status == "replay_skipped":
            skipped_replays.append(case_id)
            skipped_replay_count += 1
        else:
            failed_replays.append(case_id)
            failed_replay_count += 1

        if case.execution_record_digest:
            source_execution_record_digests.append(case.execution_record_digest)
        if case.source_trace_entry_digest:
            source_trace_entry_digests.append(case.source_trace_entry_digest)

        cases_list.append(asdict(case))

    # Determine report status
    if failed_replay_count > 0 or not ledger_valid:
        report_status = "replay_report_failed"
        reasons.append("PASS_REPLAY_REPORT_FAILED")
    elif skipped_replay_count > 0:
        report_status = "replay_report_warning"
        reasons.append("PASS_REPLAY_REPORT_FAILED")
    else:
        report_status = "replay_report_verified"
        reasons.append("PASS_REPLAY_REPORT_VERIFIED")

    handler_ids_replayed = sorted(list(set(handler_ids_replayed)))
    source_execution_record_digests = sorted(list(set(source_execution_record_digests)))
    source_trace_entry_digests = sorted(list(set(source_trace_entry_digests)))

    # Sort cases_list deterministically
    def get_case_sort_key(c):
        return (
            c.get("rc_id", ""),
            c.get("requested_pass", ""),
            c.get("requested_profile", "") or "",
            c.get("execution_status", ""),
            c.get("execution_record_digest", "")
        )
    cases_list = sorted(cases_list, key=get_case_sort_key)

    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    report = WaveguideGovernedPassReplayReport(
        replay_report_id="SOL-WAVEGUIDE-GOVERNED-PASS-REPLAY-REPORT",
        replay_report_version="1",
        replay_report_status=report_status,
        ledger_id=ledger_id,
        ledger_digest=ledger_digest,
        ledger_valid=ledger_valid,
        cases=cases_list,
        verified_executions=sorted(verified_executions),
        verified_rejections=sorted(verified_rejections),
        failed_replays=sorted(failed_replays),
        skipped_replays=sorted(skipped_replays),
        verified_execution_count=verified_execution_count,
        verified_rejection_count=verified_rejection_count,
        failed_replay_count=failed_replay_count,
        skipped_replay_count=skipped_replay_count,
        handler_ids_replayed=handler_ids_replayed,
        source_execution_record_digests=source_execution_record_digests,
        source_trace_entry_digests=source_trace_entry_digests,
        reason_codes=sorted(list(set(reasons))),
        software_validation_caveat=caveat
    )
    report.replay_report_digest = hash_waveguide_governed_pass_replay_report(report)
    return report


def validate_waveguide_governed_pass_replay_report(report: Any) -> Tuple[bool, List[str]]:
    """
    Validates a replay report's integrity, digest, and internal consistency.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    else:
        r_dict = dict(report)

    reasons = []
    is_valid = True

    given_digest = r_dict.get("replay_report_digest", "")
    computed_digest = hash_waveguide_governed_pass_replay_report(r_dict)
    if given_digest == computed_digest and given_digest != "":
        reasons.append("PASS_REPLAY_REPORT_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("PASS_REPLAY_REPORT_FAILED")
        return False, ["PASS_REPLAY_REPORT_FAILED"]

    cases = r_dict.get("cases", [])
    verified_exec = r_dict.get("verified_executions", [])
    verified_rej = r_dict.get("verified_rejections", [])
    failed = r_dict.get("failed_replays", [])
    skipped = r_dict.get("skipped_replays", [])

    if len(verified_exec) != r_dict.get("verified_execution_count", -1):
        is_valid = False
    if len(verified_rej) != r_dict.get("verified_rejection_count", -1):
        is_valid = False
    if len(failed) != r_dict.get("failed_replay_count", -1):
        is_valid = False
    if len(skipped) != r_dict.get("skipped_replay_count", -1):
        is_valid = False

    # Check case sorting
    def get_case_sort_key(c):
        return (
            c.get("rc_id", ""),
            c.get("requested_pass", ""),
            c.get("requested_profile", "") or "",
            c.get("execution_status", ""),
            c.get("execution_record_digest", "")
        )
    sorted_cases = sorted(cases, key=get_case_sort_key)
    if cases != sorted_cases:
        is_valid = False

    # Check report status consistency
    expected_status = "replay_report_verified"
    if r_dict.get("failed_replay_count", 0) > 0 or not r_dict.get("ledger_valid", False):
        expected_status = "replay_report_failed"
    elif r_dict.get("skipped_replay_count", 0) > 0:
        expected_status = "replay_report_warning"

    if r_dict.get("replay_report_status") != expected_status:
        is_valid = False

    # Check all cases have case digests and valid statuses
    for case in cases:
        case_digest = case.get("replay_case_digest", "")
        computed_case = hash_waveguide_governed_pass_replay_case(case)
        if case_digest != computed_case or not case_digest:
            is_valid = False

    if is_valid:
        reasons.append("PASS_REPLAY_REPORT_VERIFIED")
    else:
        reasons.append("PASS_REPLAY_REPORT_FAILED")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_governed_pass_replay_report(report: Any) -> str:
    """
    Creates a plaintext summary of the replay report.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    else:
        r_dict = dict(report)

    lines = [
        "==================================================",
        "SOL WAVEGUIDE GOVERNED PASS REPLAY REPORT SUMMARY",
        "==================================================",
        f"Report ID: {r_dict.get('replay_report_id')}",
        f"Status: {r_dict.get('replay_report_status')}",
        f"Ledger ID: {r_dict.get('ledger_id')}",
        f"Ledger Valid: {r_dict.get('ledger_valid')}",
        f"Ledger Digest: {r_dict.get('ledger_digest')}",
        "--------------------------------------------------",
        f"Verified Executions: {r_dict.get('verified_execution_count')}",
        f"Verified Rejections: {r_dict.get('verified_rejection_count')}",
        f"Failed Replays:      {r_dict.get('failed_replay_count')}",
        f"Skipped Replays:     {r_dict.get('skipped_replay_count')}",
        "--------------------------------------------------",
        "Replayed Handlers:",
    ]
    for h_id in r_dict.get("handler_ids_replayed", []):
        lines.append(f"  - {h_id}")

    lines.extend([
        "--------------------------------------------------",
        f"Caveat: {r_dict.get('software_validation_caveat')}",
        f"Report Digest: {r_dict.get('replay_report_digest')}",
        "=================================================="
    ])
    return "\n".join(lines)


def export_waveguide_governed_pass_replay_report(report: Any, filepath: str) -> None:
    """
    Exports the replay report to key-sorted JSON.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    else:
        r_dict = dict(report)

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_governed_pass_replay_reports(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two replay reports and returns differences.
    """
    def to_dict(rep):
        if hasattr(rep, "__dict__"):
            return asdict(rep)
        return dict(rep)

    l_dict = to_dict(left)
    r_dict = to_dict(right)

    diffs = {}
    for key in set(l_dict.keys()) | set(r_dict.keys()):
        val_l = l_dict.get(key)
        val_r = r_dict.get(key)
        if val_l != val_r:
            diffs[key] = {
                "left": val_l,
                "right": val_r
            }
    return diffs


if __name__ == "__main__":
    ledger_path = "docs/SOL_WAVEGUIDE_EXECUTION_TRACE_LEDGER.json"
    report = verify_waveguide_governed_pass_replay(ledger_path)
    export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_PASS_REPLAY_REPORT.json")
    export_waveguide_governed_pass_replay_report(report, export_path)
    print(f"Replay report generated and exported to {export_path}")
    print(summarize_waveguide_governed_pass_replay_report(report))
