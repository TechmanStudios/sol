# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Governed Compiler Invocation Envelope for SOL Waveguide.
Binds runtime capability resolution, pass admission decisions, pass execution records,
trace indexing, and replay verification reports into a single compiler session transaction.
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
from sol_waveguide_runtime_capability_resolver import (
    validate_waveguide_runtime_capability_resolution,
    build_waveguide_runtime_capability_request,
    resolve_waveguide_runtime_capabilities
)
from sol_waveguide_compiler_pass_admission import (
    validate_waveguide_pass_admission_decision,
    build_waveguide_pass_admission_request,
    evaluate_waveguide_pass_admission
)
from sol_waveguide_governed_pass_execution import (
    build_waveguide_governed_pass_execution_request,
    execute_waveguide_governed_pass,
    validate_waveguide_governed_pass_execution_record,
    build_waveguide_governed_pass_handler_registry,
    export_waveguide_governed_pass_execution_record
)
from sol_waveguide_execution_trace_ledger import (
    build_waveguide_execution_trace_entry,
    build_waveguide_execution_trace_ledger,
    validate_waveguide_execution_trace_ledger
)
from sol_waveguide_governed_pass_replay import (
    verify_waveguide_governed_pass_replay,
    validate_waveguide_governed_pass_replay_report,
    replay_waveguide_registered_safe_handler
)

# Standard input payloads mapping for deterministic stubs
KNOWN_PAYLOADS = {
    "705d0f3e3d54c1f368ad5a38fd2d156dcba3575d82783251fc8e2c2b496bdf42": {"input_size": 100},
    "8c8149029cf90bc1051a181e0d4dbbdaee866ee2ba983bf833fd2b590d69a969": {"cycles": 200}
}


@dataclass
class WaveguideInvocationPassPlanItem:
    pass_index: int
    requested_pass: str
    requested_profile: Optional[str]
    requested_scope: str
    expected_admission_status: str
    expected_execution_status: str
    required_handler_id: str
    strict_waveguide_required: bool
    lane_fabric_fallback_allowed: bool
    hybrid_execution_allowed: bool
    production_mutation_allowed: bool


@dataclass
class WaveguideGovernedCompilerInvocationRequest:
    invocation_request_id: str
    rc_id: str
    candidate_level: str
    compiler_profile: Optional[str]
    requested_pass_sequence: List[str]
    requested_scope: str                 # foundation_compiler_invocation, governed_compiler_invocation, dry_run_compiler_invocation
    capability_resolution_path: str
    capability_resolution_digest: str
    registry_digest: str
    strict_waveguide_required: bool
    lane_fabric_fallback_requested: bool
    hybrid_execution_requested: bool
    production_mutation_requested: bool
    software_validation_caveat_required: bool
    input_payload_digest: str
    invocation_request_digest: str = ""


@dataclass
class WaveguideGovernedCompilerInvocationRecord:
    invocation_record_id: str
    invocation_request_id: str
    rc_id: str
    candidate_level: str
    compiler_profile: Optional[str]
    requested_pass_sequence: List[str]
    pass_plan: List[Dict[str, Any]]
    invocation_status: str               # invocation_verified, invocation_blocked, invocation_rejected_verified, invocation_failed, invocation_warning
    capability_resolution_digest: str
    admission_decision_digests: List[str]
    execution_record_digests: List[str]
    trace_entry_digests: List[str]
    trace_ledger_digest: str
    replay_report_digest: str
    executed_pass_count: int
    rejected_pass_count: int
    verified_execution_count: int
    verified_rejection_count: int
    failed_replay_count: int
    handler_ids_used: List[str]
    input_payload_digest: str
    final_output_payload_digest: str
    reason_codes: List[str]
    notes: str
    software_validation_caveat: str
    invocation_record_digest: str = ""


def hash_waveguide_governed_compiler_invocation_request(req: Any) -> str:
    """
    Computes digest for an invocation request, excluding invocation_request_digest.
    """
    if hasattr(req, "__dict__"):
        r_dict = asdict(req)
    elif isinstance(req, dict):
        r_dict = dict(req)
    else:
        raise TypeError("request must be a dictionary or a dataclass instance")

    r_dict_copy = dict(r_dict)
    r_dict_copy.pop("invocation_request_digest", None)
    return hash_data(r_dict_copy)


def hash_waveguide_governed_compiler_invocation_record(rec: Any) -> str:
    """
    Computes digest for an invocation record, excluding invocation_record_digest.
    """
    if hasattr(rec, "__dict__"):
        r_dict = asdict(rec)
    elif isinstance(rec, dict):
        r_dict = dict(rec)
    else:
        raise TypeError("record must be a dictionary or a dataclass instance")

    r_dict_copy = dict(r_dict)
    r_dict_copy.pop("invocation_record_digest", None)
    return hash_data(r_dict_copy)


def recompute_waveguide_invocation_final_output_digest(
    rc_id: str,
    compiler_profile: Optional[str],
    requested_pass_sequence: List[str],
    executed_pass_output_payload_digests: List[str],
    rejection_execution_record_digests: List[str]
) -> str:
    """
    Recomputes the final output payload digest as a deterministic aggregate digest over
    the executed output payload digests, rejection record digests, sequence, RC ID, and profile.
    """
    aggregate_data = {
        "rc_id": rc_id,
        "compiler_profile": compiler_profile,
        "requested_pass_sequence": requested_pass_sequence,
        "executed_pass_output_payload_digests": executed_pass_output_payload_digests,
        "rejection_execution_record_digests": rejection_execution_record_digests
    }
    return hash_data(aggregate_data)



def build_waveguide_invocation_pass_plan(
    rc_id: str,
    profile: Optional[str],
    sequence: List[str],
    capability_resolution: Optional[Dict[str, Any]] = None
) -> List[WaveguideInvocationPassPlanItem]:
    """
    Generates a deterministic pass plan detailing expected admission and execution outcomes.
    """
    level = "RC1" if "RC1" in rc_id else "RC2"
    plan = []

    handler_registry = build_waveguide_governed_pass_handler_registry()

    for idx, pass_name in enumerate(sequence):
        # Build admission request dynamically to evaluate expected behavior
        adm_req = build_waveguide_pass_admission_request(
            rc_id=rc_id,
            requested_pass=pass_name,
            requested_profile=profile
        )

        dec = evaluate_waveguide_pass_admission(adm_req, capability_resolution=capability_resolution)

        expected_admission_status = dec.admission_status
        if dec.pass_allowed:
            expected_execution_status = "pass_executed"
        else:
            expected_execution_status = "pass_rejected"

        handler_id = ""
        if pass_name in handler_registry:
            handler_id = handler_registry[pass_name]["handler_id"]

        item = WaveguideInvocationPassPlanItem(
            pass_index=idx,
            requested_pass=pass_name,
            requested_profile=profile,
            requested_scope=adm_req.requested_scope,
            expected_admission_status=expected_admission_status,
            expected_execution_status=expected_execution_status,
            required_handler_id=handler_id,
            strict_waveguide_required=True,
            lane_fabric_fallback_allowed=False,
            hybrid_execution_allowed=False,
            production_mutation_allowed=False
        )
        plan.append(item)

    return plan


def build_waveguide_governed_compiler_invocation_request(
    rc_id: str,
    compiler_profile: Optional[str],
    requested_pass_sequence: List[str],
    requested_scope: Optional[str] = None,
    capability_resolution_path: Optional[str] = None,
    capability_resolution_digest: Optional[str] = None,
    registry_digest: Optional[str] = None,
    strict_waveguide_required: bool = True,
    lane_fabric_fallback_requested: bool = False,
    hybrid_execution_requested: bool = False,
    production_mutation_requested: bool = False,
    software_validation_caveat_required: bool = True,
    input_payload: Optional[Dict[str, Any]] = None
) -> WaveguideGovernedCompilerInvocationRequest:
    """
    Constructs an invocation request record.
    """
    level = "RC1" if "RC1" in rc_id else "RC2"
    candidate_level = "foundation" if level == "RC1" else "governed_execution_stack"

    if not requested_scope:
        requested_scope = "foundation_compiler_invocation" if level == "RC1" else "governed_compiler_invocation"

    if not capability_resolution_path:
        capability_resolution_path = f"docs/SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_{level}.json"
    capability_resolution_path = normalize_to_repo_path(capability_resolution_path)

    # Dynamic capability resolution digest lookup
    if not capability_resolution_digest:
        full_res_path = os.path.join(REPO_ROOT, capability_resolution_path)
        if os.path.exists(full_res_path):
            try:
                with open(full_res_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                capability_resolution_digest = data.get("resolution_digest", "")
                registry_digest = registry_digest or data.get("registry_digest", "")
            except Exception:
                pass

    if input_payload is None:
        input_payload = {}
    input_payload_digest = hash_data(input_payload)

    req = WaveguideGovernedCompilerInvocationRequest(
        invocation_request_id=f"SOL-WAVEGUIDE-COMPILER-INVOCATION-REQUEST-{level}",
        rc_id=rc_id,
        candidate_level=candidate_level,
        compiler_profile=compiler_profile,
        requested_pass_sequence=requested_pass_sequence,
        requested_scope=requested_scope,
        capability_resolution_path=capability_resolution_path,
        capability_resolution_digest=capability_resolution_digest or "",
        registry_digest=registry_digest or "",
        strict_waveguide_required=strict_waveguide_required,
        lane_fabric_fallback_requested=lane_fabric_fallback_requested,
        hybrid_execution_requested=hybrid_execution_requested,
        production_mutation_requested=production_mutation_requested,
        software_validation_caveat_required=software_validation_caveat_required,
        input_payload_digest=input_payload_digest
    )
    req.invocation_request_digest = hash_waveguide_governed_compiler_invocation_request(req)
    return req


def execute_waveguide_governed_compiler_invocation(
    request: Any,
    registry_data: Optional[Dict[str, Any]] = None,
    capability_resolution_data: Optional[Dict[str, Any]] = None,
    input_payload: Optional[Dict[str, Any]] = None
) -> WaveguideGovernedCompilerInvocationRecord:
    """
    Executes the planned passes sequentially under safety policies, producing admission,
    execution, trace registry, and replay verification records.
    """
    if hasattr(request, "__dict__"):
        req_dict = asdict(request)
    else:
        req_dict = dict(request)

    rc_id = req_dict.get("rc_id")
    level = "RC1" if "RC1" in rc_id else "RC2"
    candidate_level = req_dict.get("candidate_level")
    compiler_profile = req_dict.get("compiler_profile")
    requested_pass_sequence = req_dict.get("requested_pass_sequence", [])
    capability_resolution_path = req_dict.get("capability_resolution_path")

    reasons = ["COMPILER_INVOCATION_REQUEST_CANONICAL"]
    is_valid = True

    # 1. Load and validate capability resolution
    resolution = None
    if capability_resolution_data:
        resolution = capability_resolution_data
    else:
        res_path = os.path.join(REPO_ROOT, capability_resolution_path)
        if os.path.exists(res_path):
            with open(res_path, "r", encoding="utf-8") as f:
                resolution = json.load(f)

    if not resolution:
        is_valid = False
        reasons.append("COMPILER_INVOCATION_FAILED")
    else:
        res_ok, res_reasons = validate_waveguide_runtime_capability_resolution(resolution)
        if res_ok and resolution.get("resolution_digest") == req_dict.get("capability_resolution_digest"):
            reasons.append("COMPILER_INVOCATION_CAPABILITY_RESOLUTION_VALID")
        else:
            is_valid = False
            reasons.append("COMPILER_INVOCATION_BLOCKED")

    # Determine input payload
    if input_payload is None:
        ip_digest = req_dict.get("input_payload_digest")
        if ip_digest in KNOWN_PAYLOADS:
            input_payload = KNOWN_PAYLOADS[ip_digest]
        else:
            input_payload = {}

    current_payload = dict(input_payload)
    execution_payloads_map = {hash_data(current_payload): current_payload}

    # 2. Build pass plan
    plan_items = build_waveguide_invocation_pass_plan(rc_id, compiler_profile, requested_pass_sequence, capability_resolution=resolution)
    pass_plan_serialized = [asdict(item) for item in plan_items]
    reasons.append("COMPILER_INVOCATION_PASS_PLAN_CANONICAL")

    admission_decision_digests = []
    execution_record_digests = []
    trace_entry_digests = []
    trace_entries = []
    executed_pass_output_payload_digests = []
    rejection_execution_record_digests = []

    executed_pass_count = 0
    rejected_pass_count = 0
    handler_ids_used = []

    # Execute sequence
    for item in plan_items:
        pass_name = item.requested_pass

        # Perform pass admission evaluation
        adm_req = build_waveguide_pass_admission_request(
            rc_id=rc_id,
            requested_pass=pass_name,
            requested_profile=compiler_profile
        )
        dec = evaluate_waveguide_pass_admission(adm_req, capability_resolution=resolution)
        admission_decision_digests.append(dec.decision_digest)

        # Build path references for this session execution
        if rc_id == "SOL-WAVEGUIDE-RC1" and pass_name == "cost_model_evaluation":
            rec_path = f"docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_SESSION_{level}_rejection_{pass_name}.json"
        else:
            rec_path = f"docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_SESSION_{level}_{pass_name}.json"

        # Check safety options
        if not dec.pass_allowed:
            # Blocked pass, build execution request leading to rejection record
            exec_req = build_waveguide_governed_pass_execution_request(
                rc_id=rc_id,
                requested_pass=pass_name,
                requested_profile=compiler_profile,
                input_payload=current_payload,
                admission_decision_digest=dec.decision_digest,
                admission_status=dec.admission_status,
                strict_waveguide_required=True,
                lane_fabric_fallback_allowed=False,
                hybrid_execution_allowed=False,
                production_mutation_allowed=False,
                software_validation_caveat_required=True
            )
            rec = execute_waveguide_governed_pass(exec_req, admission_decision=dec, input_payload=current_payload)
            rejected_pass_count += 1
            reasons.append("COMPILER_INVOCATION_PASS_REJECTED")
            rejection_execution_record_digests.append(rec.execution_record_digest)
        else:
            # Admitted pass, execute safe handler
            exec_req = build_waveguide_governed_pass_execution_request(
                rc_id=rc_id,
                requested_pass=pass_name,
                requested_profile=compiler_profile,
                input_payload=current_payload,
                admission_decision_digest=dec.decision_digest,
                admission_status=dec.admission_status,
                strict_waveguide_required=True,
                lane_fabric_fallback_allowed=False,
                hybrid_execution_allowed=False,
                production_mutation_allowed=False,
                software_validation_caveat_required=True
            )
            rec = execute_waveguide_governed_pass(exec_req, admission_decision=dec, input_payload=current_payload)
            
            # Mutate payload sequentially
            replayed_output = replay_waveguide_registered_safe_handler(pass_name, current_payload)
            current_payload = replayed_output
            execution_payloads_map[hash_data(current_payload)] = current_payload

            executed_pass_count += 1
            if rec.handler_id:
                handler_ids_used.append(rec.handler_id)
            reasons.append("COMPILER_INVOCATION_PASS_EXECUTED")
            executed_pass_output_payload_digests.append(rec.output_payload_digest)

        execution_record_digests.append(rec.execution_record_digest)

        # Write to disk so replay verifier can read it
        full_rec_path = os.path.join(REPO_ROOT, rec_path)
        export_waveguide_governed_pass_execution_record(rec, full_rec_path)

        # Build trace entry
        trace_entry = build_waveguide_execution_trace_entry(rec, record_path=rec_path)
        trace_entry_digests.append(trace_entry.trace_entry_digest)
        trace_entries.append(trace_entry)

    # 3. Compile trace ledger
    trace_ledger = build_waveguide_execution_trace_ledger(trace_entries)
    trace_ledger_digest = trace_ledger.ledger_digest

    ledger_ok, ledger_reasons = validate_waveguide_execution_trace_ledger(trace_ledger)
    if ledger_ok:
        reasons.append("COMPILER_INVOCATION_TRACE_LEDGER_VALID")
    else:
        is_valid = False
        reasons.append("COMPILER_INVOCATION_BLOCKED")

    # 4. Perform replay verification
    replay_report = verify_waveguide_governed_pass_replay(trace_ledger, input_payloads=execution_payloads_map)
    replay_report_digest = replay_report.replay_report_digest

    report_ok, report_reasons = validate_waveguide_governed_pass_replay_report(replay_report)
    if report_ok:
        reasons.append("COMPILER_INVOCATION_REPLAY_REPORT_VALID")
    else:
        is_valid = False
        reasons.append("COMPILER_INVOCATION_BLOCKED")

    # 5. Evaluate overall verification status
    verified_execution_count = replay_report.verified_execution_count
    verified_rejection_count = replay_report.verified_rejection_count
    failed_replay_count = replay_report.failed_replay_count

    if failed_replay_count > 0:
        is_valid = False

    # Check for forbidden execution parameters
    if (req_dict.get("lane_fabric_fallback_requested") or
        req_dict.get("hybrid_execution_requested") or
        req_dict.get("production_mutation_requested")):
        is_valid = False
        reasons.append("COMPILER_INVOCATION_BLOCKED")

    if not req_dict.get("strict_waveguide_required"):
        is_valid = False

    # Check software caveat
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    if req_dict.get("software_validation_caveat_required"):
        reasons.append("COMPILER_INVOCATION_SOFTWARE_CAVEAT_INCLUDED")
    else:
        is_valid = False

    if is_valid:
        if executed_pass_count > 0 and rejected_pass_count == 0:
            invocation_status = "invocation_verified"
            reasons.append("COMPILER_INVOCATION_VERIFIED")
            reasons.append("COMPILER_INVOCATION_ALL_REPLAYS_VERIFIED")
        elif executed_pass_count == 0 and rejected_pass_count > 0:
            invocation_status = "invocation_rejected_verified"
            reasons.append("COMPILER_INVOCATION_REJECTIONS_VERIFIED")
        else:
            # Mixed execution and rejections (or warning states)
            invocation_status = "invocation_warning"
    else:
        if "COMPILER_INVOCATION_BLOCKED" in reasons or (
            req_dict.get("lane_fabric_fallback_requested") or
            req_dict.get("hybrid_execution_requested") or
            req_dict.get("production_mutation_requested")
        ):
            invocation_status = "invocation_blocked"
            if req_dict.get("lane_fabric_fallback_requested"):
                reasons.append("COMPILER_INVOCATION_LANEFABRIC_FALLBACK_FORBIDDEN")
            if req_dict.get("hybrid_execution_requested"):
                reasons.append("COMPILER_INVOCATION_HYBRID_EXECUTION_FORBIDDEN")
            if req_dict.get("production_mutation_requested"):
                reasons.append("COMPILER_INVOCATION_PRODUCTION_MUTATION_FORBIDDEN")
        else:
            invocation_status = "invocation_failed"
            reasons.append("COMPILER_INVOCATION_FAILED")

    # Confirm safety options
    if req_dict.get("strict_waveguide_required"):
        reasons.append("COMPILER_INVOCATION_STRICT_WAVEGUIDE_REQUIRED")

    # Deterministic output payload digest
    final_output_payload_digest = recompute_waveguide_invocation_final_output_digest(
        rc_id=rc_id,
        compiler_profile=compiler_profile,
        requested_pass_sequence=requested_pass_sequence,
        executed_pass_output_payload_digests=executed_pass_output_payload_digests,
        rejection_execution_record_digests=rejection_execution_record_digests
    )

    # Sort referencing list digests
    admission_decision_digests = sorted(list(set(admission_decision_digests)))
    execution_record_digests = sorted(list(set(execution_record_digests)))
    trace_entry_digests = sorted(list(set(trace_entry_digests)))
    handler_ids_used = sorted(list(set(handler_ids_used)))

    record = WaveguideGovernedCompilerInvocationRecord(
        invocation_record_id=f"SOL-WAVEGUIDE-COMPILER-INVOCATION-RECORD-{level}",
        invocation_request_id=req_dict.get("invocation_request_id"),
        rc_id=rc_id,
        candidate_level=candidate_level,
        compiler_profile=compiler_profile,
        requested_pass_sequence=requested_pass_sequence,
        pass_plan=pass_plan_serialized,
        invocation_status=invocation_status,
        capability_resolution_digest=resolution.get("resolution_digest", "") if resolution else "",
        admission_decision_digests=admission_decision_digests,
        execution_record_digests=execution_record_digests,
        trace_entry_digests=trace_entry_digests,
        trace_ledger_digest=trace_ledger_digest,
        replay_report_digest=replay_report_digest,
        executed_pass_count=executed_pass_count,
        rejected_pass_count=rejected_pass_count,
        verified_execution_count=verified_execution_count,
        verified_rejection_count=verified_rejection_count,
        failed_replay_count=failed_replay_count,
        handler_ids_used=handler_ids_used,
        input_payload_digest=req_dict.get("input_payload_digest"),
        final_output_payload_digest=final_output_payload_digest,
        reason_codes=sorted(list(set(reasons))),
        notes=f"Governed compiler session completed with status {invocation_status}.",
        software_validation_caveat=caveat
    )
    record.invocation_record_digest = hash_waveguide_governed_compiler_invocation_record(record)
    return record


def validate_waveguide_governed_compiler_invocation_record(record: Any) -> Tuple[bool, List[str]]:
    """
    Validates the session transaction record signature, plan consistency, and safety parameters.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    else:
        r_dict = dict(record)

    reasons = []
    is_valid = True

    # 1. Verify record signature
    given_digest = r_dict.get("invocation_record_digest", "")
    computed_digest = hash_waveguide_governed_compiler_invocation_record(r_dict)
    if given_digest == computed_digest and given_digest != "":
        reasons.append("COMPILER_INVOCATION_RECORD_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("COMPILER_INVOCATION_FAILED")
        return False, ["COMPILER_INVOCATION_FAILED"]

    # 2. Check safety policies
    status = r_dict.get("invocation_status")
    if status in ("invocation_verified", "invocation_rejected_verified", "invocation_warning"):
        if status == "invocation_rejected_verified":
            reasons.append("COMPILER_INVOCATION_REJECTIONS_VERIFIED")
        else:
            reasons.append("COMPILER_INVOCATION_VERIFIED")

        # Plan counts consistency
        executed_count = r_dict.get("executed_pass_count", 0)
        rejected_count = r_dict.get("rejected_pass_count", 0)
        total_count = len(r_dict.get("requested_pass_sequence", []))

        if executed_count + rejected_count != total_count:
            is_valid = False

        caveat = r_dict.get("software_validation_caveat", "")
        if caveat and ("sandbox" in caveat.lower() or "validation" in caveat.lower()):
            reasons.append("COMPILER_INVOCATION_SOFTWARE_CAVEAT_INCLUDED")
    else:
        is_valid = False
        if status == "invocation_blocked":
            reasons.append("COMPILER_INVOCATION_BLOCKED")
        else:
            reasons.append("COMPILER_INVOCATION_FAILED")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_governed_compiler_invocation_record(record: Any) -> str:
    """
    Generates a deterministic plaintext summary of the session transaction record.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    else:
        r_dict = dict(record)

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE GOVERNED COMPILER INVOCATION SUMMARY",
        "============================================================",
        f"Record ID:      {r_dict.get('invocation_record_id')}",
        f"Request ID:     {r_dict.get('invocation_request_id')}",
        f"RC ID:          {r_dict.get('rc_id')}",
        f"Status:         {r_dict.get('invocation_status')}",
        f"Profile:        {r_dict.get('compiler_profile')}",
        f"Sequence:       {', '.join(r_dict.get('requested_pass_sequence', []))}",
        "------------------------------------------------------------",
        f"Executed Passes: {r_dict.get('executed_pass_count')}",
        f"Rejected Passes: {r_dict.get('rejected_pass_count')}",
        f"Replay Verified: {r_dict.get('verified_execution_count')}",
        f"Rejection Verified: {r_dict.get('verified_rejection_count')}",
        f"Replay Failures: {r_dict.get('failed_replay_count')}",
        "------------------------------------------------------------",
        "Handlers Used:",
    ]
    for h_id in r_dict.get("handler_ids_used", []):
        lines.append(f"  - {h_id}")

    lines.extend([
        "------------------------------------------------------------",
        f"Input Digest:   {r_dict.get('input_payload_digest')}",
        f"Output Digest:  {r_dict.get('final_output_payload_digest')}",
        f"Record Digest:  {r_dict.get('invocation_record_digest')}",
        "============================================================"
    ])
    return "\n".join(lines)


def export_waveguide_governed_compiler_invocation_record(record: Any, filepath: str) -> None:
    """
    Exports the invocation record to a key-sorted JSON file.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    else:
        r_dict = dict(record)

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_governed_compiler_invocation_records(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two invocation records and returns differences.
    """
    def to_dict(rec):
        if hasattr(rec, "__dict__"):
            return asdict(rec)
        return dict(rec)

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
    # 1. Self-generate standard RC1 Invocation Record
    req_rc1 = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="FULL_SAFE_OPTIMIZED",
        requested_pass_sequence=["pipeline_compaction"],
        input_payload={"input_size": 100}
    )
    rec_rc1 = execute_waveguide_governed_compiler_invocation(req_rc1, input_payload={"input_size": 100})

    # 2. Self-generate standard RC2 Invocation Record
    req_rc2 = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC2",
        compiler_profile="COST_MODEL_DEBUG",
        requested_pass_sequence=["pipeline_compaction", "cost_model_evaluation", "deterministic_policy_selection"],
        input_payload={"cycles": 200}
    )
    rec_rc2 = execute_waveguide_governed_compiler_invocation(req_rc2, input_payload={"cycles": 200})

    # 3. Self-generate rejection session example (RC1 trying governed pass)
    req_rej = build_waveguide_governed_compiler_invocation_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        compiler_profile="COST_MODEL_DEBUG",
        requested_pass_sequence=["cost_model_evaluation"],
        input_payload={"cycles": 200}
    )
    rec_rej = execute_waveguide_governed_compiler_invocation(req_rej, input_payload={"cycles": 200})

    rc1_export = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC1.json")
    rc2_export = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_RC2.json")
    rej_export = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_COMPILER_INVOCATION_REJECTION_EXAMPLE.json")

    export_waveguide_governed_compiler_invocation_record(rec_rc1, rc1_export)
    export_waveguide_governed_compiler_invocation_record(rec_rc2, rc2_export)
    export_waveguide_governed_compiler_invocation_record(rec_rej, rej_export)

    print("Successfully exported session records:")
    print(f"  - RC1: {rc1_export}")
    print(f"  - RC2: {rc2_export}")
    print(f"  - Rejection Example: {rej_export}")
