# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Package Archive Signing Gate.
Consumes the Package Archive Signing Plan and creates a gate that authorizes local digest
attestation only, strictly blocking real key signing and external operations.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_package_archive_signing_plan import (
    validate_waveguide_package_archive_signing_plan
)


@dataclass
class WaveguidePackageArchiveSigningGate:
    package_archive_signing_gate_id: str
    package_archive_signing_gate_version: int
    package_archive_signing_gate_status: str  # package_archive_signing_gate_ready, etc.
    package_archive_signing_gate_decision: str  # allow_local_digest_attestation, etc.
    package_archive_signing_gate_scope: str
    source_package_archive_signing_plan_digest: str
    source_package_archive_release_candidate_index_digest: str
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_candidate_count: int
    verified_archive_candidate_count: int
    current_archive_candidate_digest: str
    current_archive_candidate_format: str
    current_archive_candidate_display_path: str
    current_archive_candidate_size_bytes: int
    digest_attestation_allowed: bool
    local_digest_attestation_allowed: bool
    real_key_signing_allowed: bool
    external_signing_allowed: bool
    timestamp_authority_allowed: bool
    upload_allowed: bool
    deployment_allowed: bool
    external_publication_allowed: bool
    production_mutation_allowed: bool
    requires_digest_attestation_validator: bool
    requires_future_key_management_gate: bool
    requires_future_signing_key_gate: bool
    requires_explicit_operator_approval_for_real_signing: bool
    requires_no_network_signing: bool
    requires_no_credentials_loaded: bool
    signing_gate_constraints: List[str]
    signing_gate_allowances: List[str]
    signing_gate_prohibitions: List[str]
    signing_gate_guard_requirements: List[str]
    blocked_operation_attempt_counts: Dict[str, int]
    signing_performed: bool
    real_key_signature_performed: bool
    digest_attestation_performed: bool
    external_signing_performed: bool
    timestamp_authority_performed: bool
    upload_performed: bool
    deployment_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    package_archive_signing_gate_digest: str = ""


def hash_waveguide_package_archive_signing_gate(gate: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a signing gate,
    excluding package_archive_signing_gate_digest.
    """
    if hasattr(gate, "__dict__"):
        g_dict = asdict(gate)
    elif isinstance(gate, dict):
        g_dict = dict(gate)
    else:
        raise TypeError("gate must be a dictionary or dataclass instance")

    g_copy = dict(g_dict)
    g_copy.pop("package_archive_signing_gate_digest", None)
    return hash_data(g_copy)


def build_waveguide_package_archive_signing_gate_decision(
    status: str,
    ready: bool
) -> str:
    if status == "package_archive_signing_gate_ready" and ready:
        return "allow_local_digest_attestation"
    elif status == "package_archive_signing_gate_blocked":
        return "block_archive_signing"
    elif status == "package_archive_signing_gate_warning":
        return "manual_review_required"
    else:
        return "invalid_archive_signing_gate"


def validate_waveguide_package_archive_signing_gate_scope(scope: str) -> bool:
    return scope == "controlled_local_archive_attestation_scope"


def validate_waveguide_package_archive_signing_gate_boolean_matrix(gate_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors = []
    # Attestation must be allowed
    if gate_dict.get("digest_attestation_allowed") is not True:
        errors.append("digest_attestation_allowed must be True")
    if gate_dict.get("local_digest_attestation_allowed") is not True:
        errors.append("local_digest_attestation_allowed must be True")

    # Real key signing and external operations must be strictly disabled
    prohibitions = [
        "real_key_signing_allowed",
        "external_signing_allowed",
        "timestamp_authority_allowed",
        "upload_allowed",
        "deployment_allowed",
        "external_publication_allowed",
        "production_mutation_allowed",
    ]
    for key in prohibitions:
        if gate_dict.get(key) is not False:
            errors.append(f"{key} must be False")

    # Guard requirements must be enabled
    guards = [
        "requires_digest_attestation_validator",
        "requires_future_key_management_gate",
        "requires_future_signing_key_gate",
        "requires_explicit_operator_approval_for_real_signing",
        "requires_no_network_signing",
        "requires_no_credentials_loaded",
    ]
    for key in guards:
        if gate_dict.get(key) is not True:
            errors.append(f"{key} must be True")

    # All performed flags must be False (signing hasn't happened yet)
    performed = [
        "signing_performed",
        "real_key_signature_performed",
        "digest_attestation_performed",
        "external_signing_performed",
        "timestamp_authority_performed",
        "upload_performed",
        "deployment_performed",
        "external_publication_performed",
        "production_mutation_performed",
    ]
    for key in performed:
        if gate_dict.get(key) is not False:
            errors.append(f"{key} must be False")

    return len(errors) == 0, errors


def validate_waveguide_package_archive_signing_gate_blocked_operation_counts(
    counts: Dict[str, int]
) -> bool:
    return all(v == 0 for v in counts.values())


def validate_waveguide_package_archive_digest_attestation_gate_policy(
    allowed: bool, local_allowed: bool
) -> bool:
    return allowed is True and local_allowed is True


def validate_waveguide_package_archive_real_key_signing_gate_policy(
    allowed: bool, ext_allowed: bool, ts_allowed: bool
) -> bool:
    return allowed is False and ext_allowed is False and ts_allowed is False


def _load_dict(path_or_dict: Any) -> Optional[Dict[str, Any]]:
    if isinstance(path_or_dict, str):
        path = normalize_to_repo_path(path_or_dict)
        full_path = os.path.join(REPO_ROOT, path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    elif hasattr(path_or_dict, "__dict__"):
        return asdict(path_or_dict)
    elif isinstance(path_or_dict, dict):
        return dict(path_or_dict)
    return None


def build_waveguide_package_archive_signing_gate(
    plan_path_or_dict: Any
) -> WaveguidePackageArchiveSigningGate:
    """
    Builds the Package Archive Signing Gate from the Signing Plan.
    """
    plan_dict = _load_dict(plan_path_or_dict) or {}
    plan_digest = plan_dict.get("package_archive_signing_plan_digest", "")
    plan_status = plan_dict.get("package_archive_signing_plan_status", "")

    status = "package_archive_signing_gate_ready"
    reason_codes = ["SIGNING_GATE_READY"]

    valid_plan, plan_errs = validate_waveguide_package_archive_signing_plan(plan_dict)
    if not valid_plan or plan_status != "package_archive_signing_plan_ready":
        status = "package_archive_signing_gate_blocked"
        reason_codes = ["SIGNING_PLAN_NOT_READY"]

    # Check for any mutations/performed flag violations in plan
    signing_performed = plan_dict.get("signing_performed", False)
    upload_performed = plan_dict.get("upload_performed", False)
    publication_performed = plan_dict.get("external_publication_performed", False)
    deployment_performed = plan_dict.get("deployment_performed", False)
    production_mutation_performed = plan_dict.get("production_mutation_performed", False)

    if signing_performed or upload_performed or publication_performed or deployment_performed or production_mutation_performed:
        status = "package_archive_signing_gate_invalid"
        reason_codes.append("SIGNING_PLAN_MUTATION_VIOLATION")

    decision = build_waveguide_package_archive_signing_gate_decision(status, True)

    blocked_counts = {
        "archive_creation": 0,
        "deployment": 0,
        "directory_creation": 0,
        "external_publication": 0,
        "external_signing": 0,
        "file_copy": 0,
        "production_mutation": 0,
        "upload": 0
    }

    gate = WaveguidePackageArchiveSigningGate(
        package_archive_signing_gate_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-SIGNING-GATE",
        package_archive_signing_gate_version=1,
        package_archive_signing_gate_status=status,
        package_archive_signing_gate_decision=decision,
        package_archive_signing_gate_scope="controlled_local_archive_attestation_scope",
        source_package_archive_signing_plan_digest=plan_digest,
        source_package_archive_release_candidate_index_digest=plan_dict.get("source_package_archive_release_candidate_index_digest", ""),
        source_package_archive_audit_report_digest=plan_dict.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=plan_dict.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=plan_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=plan_dict.get("source_package_archive_plan_digest", ""),
        archive_candidate_count=plan_dict.get("archive_candidate_count", 0),
        verified_archive_candidate_count=plan_dict.get("verified_archive_candidate_count", 0),
        current_archive_candidate_digest=plan_dict.get("current_archive_candidate_digest", ""),
        current_archive_candidate_format=plan_dict.get("current_archive_candidate_format", ""),
        current_archive_candidate_display_path=plan_dict.get("current_archive_candidate_display_path", ""),
        current_archive_candidate_size_bytes=plan_dict.get("current_archive_candidate_size_bytes", 0),
        digest_attestation_allowed=True,
        local_digest_attestation_allowed=True,
        real_key_signing_allowed=False,
        external_signing_allowed=False,
        timestamp_authority_allowed=False,
        upload_allowed=False,
        deployment_allowed=False,
        external_publication_allowed=False,
        production_mutation_allowed=False,
        requires_digest_attestation_validator=True,
        requires_future_key_management_gate=True,
        requires_future_signing_key_gate=True,
        requires_explicit_operator_approval_for_real_signing=True,
        requires_no_network_signing=True,
        requires_no_credentials_loaded=True,
        signing_gate_constraints=["REAL_KEY_SIGNING_DISABLED", "NO_EXTERNAL_SIGNING_SERVICES", "NO_TIMESTAMP_AUTHORITY"],
        signing_gate_allowances=["LOCAL_DIGEST_ATTESTATION_ALLOWED"],
        signing_gate_prohibitions=["REAL_KEY_SIGNING_PROHIBITED", "UPLOAD_PROHIBITED", "DEPLOYMENT_PROHIBITED", "EXTERNAL_PUBLICATION_PROHIBITED", "PRODUCTION_MUTATION_PROHIBITED"],
        signing_gate_guard_requirements=["REQUIRES_DIGEST_ATTESTATION_VALIDATOR", "REQUIRES_FUTURE_KEY_MANAGEMENT_GATE", "REQUIRES_FUTURE_SIGNING_KEY_GATE", "REQUIRES_EXPLICIT_OPERATOR_APPROVAL_FOR_REAL_SIGNING", "REQUIRES_NO_NETWORK_SIGNING", "REQUIRES_NO_CREDENTIALS_LOADED"],
        blocked_operation_attempt_counts=blocked_counts,
        signing_performed=False,
        real_key_signature_performed=False,
        digest_attestation_performed=False,
        external_signing_performed=False,
        timestamp_authority_performed=False,
        upload_performed=False,
        deployment_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    gate.package_archive_signing_gate_digest = hash_waveguide_package_archive_signing_gate(gate)
    return gate


def validate_waveguide_package_archive_signing_gate(gate: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a Package Archive Signing Gate.
    """
    g_dict = asdict(gate) if hasattr(gate, "__dict__") else dict(gate)
    errors = []

    # Verify digest
    recorded = g_dict.get("package_archive_signing_gate_digest", "")
    if not recorded:
        errors.append("Missing gate digest")
    else:
        recomputed = hash_waveguide_package_archive_signing_gate(g_dict)
        if recomputed != recorded:
            errors.append(f"Gate digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if g_dict.get("package_archive_signing_gate_id") != "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-SIGNING-GATE":
        errors.append("Invalid signing gate ID")

    # Validate gate status
    status = g_dict.get("package_archive_signing_gate_status", "")
    if status not in [
        "package_archive_signing_gate_ready",
        "package_archive_signing_gate_blocked",
        "package_archive_signing_gate_warning",
        "package_archive_signing_gate_invalid"
    ]:
        errors.append("Invalid signing gate status")

    # Validate scope
    scope = g_dict.get("package_archive_signing_gate_scope", "")
    if not validate_waveguide_package_archive_signing_gate_scope(scope):
        errors.append("Invalid signing gate scope")

    # Validate boolean matrix
    ok_matrix, matrix_errs = validate_waveguide_package_archive_signing_gate_boolean_matrix(g_dict)
    if not ok_matrix:
        errors.extend(matrix_errs)

    # Validate blocked operations
    counts = g_dict.get("blocked_operation_attempt_counts", {})
    if not validate_waveguide_package_archive_signing_gate_blocked_operation_counts(counts):
        errors.append("Invalid blocked operation counts")

    return len(errors) == 0, errors


def summarize_waveguide_package_archive_signing_gate(gate: Any) -> str:
    """
    Generates a human-readable summary of the Signing Gate.
    """
    g_dict = asdict(gate) if hasattr(gate, "__dict__") else dict(gate)
    lines = [
        "=============================================================",
        "               SOL WAVEGUIDE PACKAGE SIGNING GATE",
        "=============================================================",
        f"Gate ID:          {g_dict.get('package_archive_signing_gate_id')}",
        f"Status:           {g_dict.get('package_archive_signing_gate_status')}",
        f"Decision:         {g_dict.get('package_archive_signing_gate_decision')}",
        f"Scope:            {g_dict.get('package_archive_signing_gate_scope')}",
        f"Gate Digest:      {g_dict.get('package_archive_signing_gate_digest')}",
        f"Candidate Digest: {g_dict.get('current_archive_candidate_digest')}",
        f"Attest Allowed:   {g_dict.get('digest_attestation_allowed')}",
        f"Real Sign Allowed: {g_dict.get('real_key_signing_allowed')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in g_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_archive_signing_gate(gate: Any, output_path: str) -> None:
    """
    Exports the Signing Gate to a JSON file.
    """
    g_dict = asdict(gate) if hasattr(gate, "__dict__") else dict(gate)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(g_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_archive_signing_gates(gate_a: Any, gate_b: Any) -> Dict[str, Any]:
    """
    Compares two Signing Gates.
    """
    dict_a = asdict(gate_a) if hasattr(gate_a, "__dict__") else dict(gate_a)
    dict_b = asdict(gate_b) if hasattr(gate_b, "__dict__") else dict(gate_b)

    differences = {}
    for key in (
        "package_archive_signing_gate_status",
        "package_archive_signing_gate_decision",
        "package_archive_signing_gate_digest"
    ):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
