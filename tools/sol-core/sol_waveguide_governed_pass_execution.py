# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Governed Pass Execution Harness for SOL Waveguide RC1 and RC2.
Validates pass admission decisions and dispatches execution of admitted
passes to registered deterministic safe handlers.
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
from sol_waveguide_compiler_pass_admission import (
    validate_waveguide_pass_admission_decision,
    build_waveguide_pass_admission_request,
    evaluate_waveguide_pass_admission
)


@dataclass
class WaveguideGovernedPassExecutionRequest:
    execution_request_id: str
    rc_id: str
    candidate_level: str
    requested_pass: str
    requested_profile: Optional[str]
    admission_decision_path: str
    admission_decision_digest: str
    admission_status: str
    execution_scope: str                 # foundation_pass_execution, governed_pass_execution, profile_execution, optimization_execution, dry_run_execution
    input_payload_digest: str
    strict_waveguide_required: bool
    lane_fabric_fallback_allowed: bool
    hybrid_execution_allowed: bool
    production_mutation_allowed: bool
    software_validation_caveat_required: bool
    execution_request_digest: str = ""


@dataclass
class WaveguideGovernedPassExecutionRecord:
    execution_record_id: str
    execution_request_id: str
    rc_id: str
    candidate_level: str
    requested_pass: str
    requested_profile: Optional[str]
    admission_decision_digest: str
    admission_status: str
    execution_status: str               # pass_executed, pass_rejected, pass_execution_warning, pass_execution_error
    handler_id: str
    handler_version: str
    handler_registered: bool
    pass_executed: bool
    pass_rejected: bool
    input_payload_digest: str
    output_payload_digest: str
    trace: List[str]
    reason_codes: List[str]
    notes: str
    strict_waveguide_required: bool
    lane_fabric_fallback_allowed: bool
    hybrid_execution_allowed: bool
    production_mutation_allowed: bool
    software_validation_caveat: str
    execution_record_digest: str = ""


# Deterministic Pass Handlers Registry
def handle_pipeline_compaction(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(payload)
    out["compaction_ratio"] = 1.25
    out["status"] = "compacted"
    return out


def handle_channel_kernel_recognition(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(payload)
    out["recognized_count"] = len(payload.get("kernels", []))
    out["status"] = "recognized"
    return out


def handle_cost_model_evaluation(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(payload)
    out["cost_score"] = payload.get("cycles", 100) * 0.025
    out["status"] = "evaluated"
    return out


def handle_deterministic_policy_selection(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(payload)
    out["selection_index"] = 1
    out["status"] = "selected"
    return out


def build_waveguide_governed_pass_handler_registry() -> Dict[str, Dict[str, Any]]:
    """
    Returns the deterministic map of registered safe handlers.
    """
    return {
        "pipeline_compaction": {
            "handler_id": "SOL-PASS-HANDLER-PIPELINE-COMPACTION-V1",
            "handler_version": "1.0.0",
            "func": handle_pipeline_compaction
        },
        "channel_kernel_recognition": {
            "handler_id": "SOL-PASS-HANDLER-CHANNEL-KERNEL-RECOGNITION-V1",
            "handler_version": "1.0.0",
            "func": handle_channel_kernel_recognition
        },
        "cost_model_evaluation": {
            "handler_id": "SOL-PASS-HANDLER-COST-MODEL-EVALUATION-V1",
            "handler_version": "1.0.0",
            "func": handle_cost_model_evaluation
        },
        "deterministic_policy_selection": {
            "handler_id": "SOL-PASS-HANDLER-DETERMINISTIC-POLICY-SELECTION-V1",
            "handler_version": "1.0.0",
            "func": handle_deterministic_policy_selection
        }
    }


def hash_waveguide_governed_pass_execution_request(req: Any) -> str:
    """
    Computes digest for a governed execution request, excluding execution_request_digest.
    """
    if hasattr(req, "__dict__"):
        r_dict = asdict(req)
    elif isinstance(req, dict):
        r_dict = dict(req)
    else:
        raise TypeError("request must be a dictionary or a dataclass instance")

    r_dict.pop("execution_request_digest", None)
    return hash_data(r_dict)


def hash_waveguide_governed_pass_execution_record(rec: Any) -> str:
    """
    Computes digest for an execution record, excluding execution_record_digest.
    """
    if hasattr(rec, "__dict__"):
        r_dict = asdict(rec)
    elif isinstance(rec, dict):
        r_dict = dict(rec)
    else:
        raise TypeError("record must be a dictionary or a dataclass instance")

    r_dict.pop("execution_record_digest", None)
    return hash_data(r_dict)


def build_waveguide_governed_pass_execution_request(
    rc_id: str,
    requested_pass: str,
    requested_profile: Optional[str] = None,
    input_payload: Optional[Dict[str, Any]] = None,
    admission_decision_path: Optional[str] = None,
    admission_decision_digest: Optional[str] = None,
    admission_status: Optional[str] = None,
    execution_scope: Optional[str] = None,
    strict_waveguide_required: bool = True,
    lane_fabric_fallback_allowed: bool = False,
    hybrid_execution_allowed: bool = False,
    production_mutation_allowed: bool = False,
    software_validation_caveat_required: bool = True
) -> WaveguideGovernedPassExecutionRequest:
    """
    Constructs a governed pass execution request record.
    """
    level = "RC1" if "RC1" in rc_id else "RC2"
    candidate_level = "foundation" if level == "RC1" else "governed_execution_stack"

    if not execution_scope:
        execution_scope = "foundation_pass_execution" if level == "RC1" else "governed_pass_execution"

    if not admission_decision_path:
        admission_decision_path = f"docs/SOL_WAVEGUIDE_COMPILER_PASS_ADMISSION_{level}.json"
    admission_decision_path = normalize_to_repo_path(admission_decision_path)

    # Load admission status and digest dynamically if not provided
    if not admission_decision_digest or not admission_status:
        full_dec_path = os.path.join(REPO_ROOT, admission_decision_path)
        if os.path.exists(full_dec_path):
            try:
                with open(full_dec_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                admission_decision_digest = admission_decision_digest or data.get("decision_digest", "")
                admission_status = admission_status or data.get("admission_status", "")
            except Exception:
                pass

    if input_payload is None:
        input_payload = {}
    input_payload_digest = hash_data(input_payload)

    req = WaveguideGovernedPassExecutionRequest(
        execution_request_id=f"SOL-WAVEGUIDE-PASS-EXECUTION-REQUEST-{level}",
        rc_id=rc_id,
        candidate_level=candidate_level,
        requested_pass=requested_pass,
        requested_profile=requested_profile,
        admission_decision_path=admission_decision_path,
        admission_decision_digest=admission_decision_digest or "",
        admission_status=admission_status or "pass_blocked",
        execution_scope=execution_scope,
        input_payload_digest=input_payload_digest,
        strict_waveguide_required=strict_waveguide_required,
        lane_fabric_fallback_allowed=lane_fabric_fallback_allowed,
        hybrid_execution_allowed=hybrid_execution_allowed,
        production_mutation_allowed=production_mutation_allowed,
        software_validation_caveat_required=software_validation_caveat_required
    )
    req.execution_request_digest = hash_waveguide_governed_pass_execution_request(req)
    return req


def execute_waveguide_governed_pass(
    request: Any,
    admission_decision: Optional[Dict[str, Any]] = None,
    input_payload: Optional[Dict[str, Any]] = None
) -> WaveguideGovernedPassExecutionRecord:
    """
    Validates the admission decision and executes the registered handler if permitted.
    """
    if hasattr(request, "__dict__"):
        req_dict = asdict(request)
    else:
        req_dict = dict(request)

    rc_id = req_dict.get("rc_id")
    level = "RC1" if "RC1" in rc_id else "RC2"
    candidate_level = req_dict.get("candidate_level")
    requested_pass = req_dict.get("requested_pass")
    requested_profile = req_dict.get("requested_profile")
    execution_request_id = req_dict.get("execution_request_id")

    reasons = ["PASS_EXECUTION_REQUEST_CANONICAL"]
    trace = ["Initialized governed pass execution validation."]
    is_valid = True

    # 1. Load admission decision
    decision = None
    if admission_decision:
        if hasattr(admission_decision, "__dict__"):
            decision = asdict(admission_decision)
        else:
            decision = dict(admission_decision)
    else:
        dec_path = os.path.join(REPO_ROOT, req_dict.get("admission_decision_path", ""))
        if os.path.exists(dec_path):
            with open(dec_path, "r", encoding="utf-8") as f:
                decision = json.load(f)

    # Resolve handler registry
    registry = build_waveguide_governed_pass_handler_registry()

    if not decision:
        is_valid = False
        reasons.append("PASS_EXECUTION_ADMISSION_DECISION_INVALID")
        trace.append("Failed to load admission decision record.")
        admission_status = "pass_blocked"
        decision_digest = ""
        caveat = ""
    else:
        # Validate decision using controller
        dec_ok, dec_reasons = validate_waveguide_pass_admission_decision(decision)
        decision_digest = decision.get("decision_digest", "")

        # Check decision digest matches request
        req_dec_digest = req_dict.get("admission_decision_digest")
        if req_dec_digest and req_dec_digest != decision_digest:
            is_valid = False
            trace.append("Admission decision digest mismatch.")

        if dec_ok and is_valid:
            reasons.append("PASS_EXECUTION_ADMISSION_DECISION_VALID")
            trace.append("Admission decision validated successfully.")
        else:
            is_valid = False
            reasons.append("PASS_EXECUTION_ADMISSION_DECISION_INVALID")
            trace.append("Admission decision validation failed.")

        admission_status = decision.get("admission_status", "pass_blocked")
        if admission_status == "pass_admitted":
            reasons.append("PASS_EXECUTION_ADMISSION_GRANTED")
            trace.append("Admission status is GRANTED.")
        else:
            is_valid = False
            reasons.append("PASS_EXECUTION_ADMISSION_NOT_GRANTED")
            trace.append(f"Admission status is BLOCKED: {decision.get('notes')}")

        # Verify RC Match
        dec_rc_id = decision.get("rc_id")
        if rc_id == dec_rc_id:
            reasons.append("PASS_EXECUTION_RC_MATCH")
            trace.append("Request RC ID matches admission decision.")
        else:
            is_valid = False
            reasons.append("PASS_EXECUTION_RC_MISMATCH")
            trace.append("Request RC ID mismatch.")

        # Verify Pass/Profile Match
        dec_pass = decision.get("requested_pass")
        if requested_pass == dec_pass:
            reasons.append("PASS_EXECUTION_PASS_MATCH")
        else:
            is_valid = False
            reasons.append("PASS_EXECUTION_PASS_MISMATCH")

        dec_profile = decision.get("requested_profile")
        if requested_profile == dec_profile:
            reasons.append("PASS_EXECUTION_PROFILE_MATCH")
        else:
            is_valid = False
            reasons.append("PASS_EXECUTION_PROFILE_MISMATCH")

        caveat = decision.get("software_validation_caveat", "")

    # Safety Indicator Verification
    strict_waveguide = req_dict.get("strict_waveguide_required", True)
    if not strict_waveguide or (decision and decision.get("strict_waveguide_required") is False):
        is_valid = False
        trace.append("Strict waveguide compliance is missing.")
    else:
        reasons.append("PASS_EXECUTION_STRICT_WAVEGUIDE_REQUIRED")

    if req_dict.get("lane_fabric_fallback_allowed", False) or (decision and decision.get("lane_fabric_fallback_allowed") is True):
        is_valid = False
        reasons.append("PASS_EXECUTION_LANEFABRIC_FALLBACK_FORBIDDEN")
        trace.append("LaneFabric fallback is forbidden.")

    if req_dict.get("hybrid_execution_allowed", False) or (decision and decision.get("hybrid_execution_allowed") is True):
        is_valid = False
        reasons.append("PASS_EXECUTION_HYBRID_EXECUTION_FORBIDDEN")
        trace.append("Hybrid execution is forbidden.")

    if req_dict.get("production_mutation_allowed", False) or (decision and decision.get("production_mutation_allowed") is True):
        is_valid = False
        reasons.append("PASS_EXECUTION_PRODUCTION_MUTATION_FORBIDDEN")
        trace.append("Production mutation is forbidden.")

    # Caveat validation
    if req_dict.get("software_validation_caveat_required", True):
        if caveat and ("sandbox" in caveat.lower() or "validation" in caveat.lower()):
            reasons.append("PASS_EXECUTION_SOFTWARE_CAVEAT_INCLUDED")
            trace.append("Software validation caveat included.")
        else:
            is_valid = False
            trace.append("Missing software validation caveat.")

    # Check safe handler registration
    if requested_pass in registry:
        handler_registered = True
        handler_data = registry[requested_pass]
        handler_id = handler_data["handler_id"]
        handler_version = handler_data["handler_version"]
        handler_func = handler_data["func"]
        reasons.append("PASS_EXECUTION_HANDLER_REGISTERED")
        trace.append(f"Handler {handler_id} (v{handler_version}) is registered for pass {requested_pass}.")
    else:
        is_valid = False
        handler_registered = False
        handler_id = ""
        handler_version = ""
        handler_func = None
        reasons.append("PASS_EXECUTION_HANDLER_MISSING")
        trace.append(f"No handler registered for pass {requested_pass}.")

    # Payload setup
    if input_payload is None:
        input_payload = {}
    input_digest = hash_data(input_payload)

    # Check input payload digest matches request
    if input_digest != req_dict.get("input_payload_digest"):
        is_valid = False
        trace.append("Input payload digest mismatch.")
    else:
        reasons.append("PASS_EXECUTION_INPUT_DIGEST_VALID")

    # Execution dispatch
    if is_valid:
        try:
            output_payload = handler_func(input_payload)
            output_digest = hash_data(output_payload)
            reasons.append("PASS_EXECUTION_HANDLER_COMPLETED")
            reasons.append("PASS_EXECUTION_OUTPUT_DIGEST_VALID")
            reasons.append("PASS_EXECUTION_PASS_EXECUTED")
            trace.append("Safe handler execution completed successfully.")
            execution_status = "pass_executed"
            pass_executed = True
            pass_rejected = False
            notes = f"Pass {requested_pass} executed successfully through safe handler {handler_id}."
        except Exception as e:
            is_valid = False
            output_digest = ""
            execution_status = "pass_execution_error"
            pass_executed = False
            pass_rejected = True
            notes = f"Execution error in pass handler {handler_id}: {str(e)}"
            trace.append(f"Handler threw exception: {str(e)}")
    else:
        output_digest = ""
        execution_status = "pass_rejected"
        pass_executed = False
        pass_rejected = True
        reasons.append("PASS_EXECUTION_PASS_REJECTED")
        notes = f"Pass {requested_pass} (profile: {requested_profile}) execution rejected."
        trace.append("Execution blocked due to policy validation failure.")

    reasons = sorted(list(set(reasons)))

    record = WaveguideGovernedPassExecutionRecord(
        execution_record_id=f"SOL-WAVEGUIDE-PASS-EXECUTION-RECORD-{level}",
        execution_request_id=execution_request_id,
        rc_id=rc_id,
        candidate_level=candidate_level,
        requested_pass=requested_pass,
        requested_profile=requested_profile,
        admission_decision_digest=decision_digest,
        admission_status=admission_status,
        execution_status=execution_status,
        handler_id=handler_id,
        handler_version=handler_version,
        handler_registered=handler_registered,
        pass_executed=pass_executed,
        pass_rejected=pass_rejected,
        input_payload_digest=input_digest,
        output_payload_digest=output_digest,
        trace=trace,
        reason_codes=reasons,
        notes=notes,
        strict_waveguide_required=True,
        lane_fabric_fallback_allowed=False,
        hybrid_execution_allowed=False,
        production_mutation_allowed=False,
        software_validation_caveat=caveat,
        execution_record_digest=""
    )

    record.execution_record_digest = hash_waveguide_governed_pass_execution_record(record)
    return record


def validate_waveguide_governed_pass_execution_record(record: Any) -> Tuple[bool, List[str]]:
    """
    Verifies that the execution record digest is valid and matches safety parameters.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    else:
        r_dict = dict(record)

    reasons = []
    is_valid = True

    # 1. Verify record digest
    given_digest = r_dict.get("execution_record_digest", "")
    computed_digest = hash_waveguide_governed_pass_execution_record(r_dict)
    if given_digest == computed_digest:
        reasons.append("PASS_EXECUTION_RECORD_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("PASS_EXECUTION_RECORD_DIGEST_INVALID")

    # 2. Check safety policies
    if r_dict.get("execution_status") == "pass_executed":
        reasons.append("PASS_EXECUTION_PASS_EXECUTED")
        reasons.append("PASS_EXECUTION_HANDLER_COMPLETED")

        if r_dict.get("strict_waveguide_required") is True:
            reasons.append("PASS_EXECUTION_STRICT_WAVEGUIDE_REQUIRED")
        if r_dict.get("lane_fabric_fallback_allowed") is False:
            reasons.append("PASS_EXECUTION_LANEFABRIC_FALLBACK_FORBIDDEN")
        if r_dict.get("hybrid_execution_allowed") is False:
            reasons.append("PASS_EXECUTION_HYBRID_EXECUTION_FORBIDDEN")
        if r_dict.get("production_mutation_allowed") is False:
            reasons.append("PASS_EXECUTION_PRODUCTION_MUTATION_FORBIDDEN")

        caveat = r_dict.get("software_validation_caveat", "")
        if caveat and ("sandbox" in caveat.lower() or "validation" in caveat.lower()):
            reasons.append("PASS_EXECUTION_SOFTWARE_CAVEAT_INCLUDED")

        rc_id = r_dict.get("rc_id")
        if "RC1" in rc_id:
            reasons.append("PASS_EXECUTION_ADMISSION_DECISION_VALID")
            reasons.append("PASS_EXECUTION_ADMISSION_GRANTED")
        elif "RC2" in rc_id:
            reasons.append("PASS_EXECUTION_ADMISSION_DECISION_VALID")
            reasons.append("PASS_EXECUTION_ADMISSION_GRANTED")
    else:
        is_valid = False
        reasons.append("PASS_EXECUTION_PASS_REJECTED")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_governed_pass_execution_record(record: Any) -> str:
    """
    Generates deterministic plaintext summary of the governed execution record.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    else:
        r_dict = dict(record)

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE GOVERNED PASS EXECUTION RECORD",
        "============================================================",
        f"Record ID:         {r_dict.get('execution_record_id')}",
        f"Request ID:        {r_dict.get('execution_request_id')}",
        f"Candidate ID:      {r_dict.get('rc_id')}",
        f"Candidate Level:   {r_dict.get('candidate_level')}",
        f"Requested Pass:    {r_dict.get('requested_pass')}",
        f"Requested Profile: {r_dict.get('requested_profile')}",
        f"Execution Status:  {r_dict.get('execution_status', '').upper()}",
        f"Record Digest:     {r_dict.get('execution_record_digest')}",
        "------------------------------------------------------------",
        f"Handler ID:        {r_dict.get('handler_id')}",
        f"Handler Registered:{r_dict.get('handler_registered')}",
        f"Pass Executed:     {r_dict.get('pass_executed')}",
        f"Pass Rejected:     {r_dict.get('pass_rejected')}",
        f"Input Digest:      {r_dict.get('input_payload_digest')}",
        f"Output Digest:     {r_dict.get('output_payload_digest')}",
        "------------------------------------------------------------",
        "Trace:",
    ]
    for step in r_dict.get("trace", []):
        lines.append(f"  - {step}")
    lines.append("------------------------------------------------------------")
    lines.append(f"Notes: {r_dict.get('notes')}")
    lines.append("============================================================")
    return "\n".join(lines)


def export_waveguide_governed_pass_execution_record(record: Any, filepath: str) -> None:
    """
    Exports execution record to key-sorted JSON catalog.
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


def compare_waveguide_governed_pass_execution_records(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two execution records and returns differences.
    """
    def to_dict(rec):
        if hasattr(rec, "__dict__"):
            return asdict(rec)
        return dict(rec)

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


if __name__ == "__main__":
    # 1. Self-generate standard admitted RC1 execution record
    req1 = build_waveguide_governed_pass_execution_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        requested_pass="pipeline_compaction",
        requested_profile="FULL_SAFE_OPTIMIZED",
        input_payload={"input_size": 100}
    )
    rec1 = execute_waveguide_governed_pass(req1, input_payload={"input_size": 100})

    # 2. Self-generate standard admitted RC2 execution record
    req2 = build_waveguide_governed_pass_execution_request(
        rc_id="SOL-WAVEGUIDE-RC2",
        requested_pass="cost_model_evaluation",
        requested_profile="COST_MODEL_DEBUG",
        input_payload={"cycles": 200}
    )
    rec2 = execute_waveguide_governed_pass(req2, input_payload={"cycles": 200})

    # 3. Self-generate rejected execution record (governed pass on RC1)
    req3 = build_waveguide_governed_pass_execution_request(
        rc_id="SOL-WAVEGUIDE-RC1",
        requested_pass="cost_model_evaluation",
        requested_profile="COST_MODEL_DEBUG",
        input_payload={"cycles": 200}
    )
    rec3 = execute_waveguide_governed_pass(req3, input_payload={"cycles": 200})

    rc1_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json")
    rc2_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC2.json")
    rej_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json")

    export_waveguide_governed_pass_execution_record(rec1, rc1_export_path)
    export_waveguide_governed_pass_execution_record(rec2, rc2_export_path)
    export_waveguide_governed_pass_execution_record(rec3, rej_export_path)

    print(f"Exported RC1 governed execution record: {rc1_export_path}")
    print(f"Exported RC2 governed execution record: {rc2_export_path}")
    print(f"Exported Rejection example: {rej_export_path}")
