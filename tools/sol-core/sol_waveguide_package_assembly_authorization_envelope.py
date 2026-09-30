# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Authorization Envelope.
Produces a deterministic authorization envelope based on the Final Package Readiness Report.
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
from sol_waveguide_distribution_package_manifest_validator import (
    validate_waveguide_final_package_readiness_audit_report
)


@dataclass
class WaveguidePackageAssemblyAuthorizationEnvelope:
    package_assembly_authorization_envelope_id: str
    package_assembly_authorization_envelope_version: int
    authorization_status: str  # package_assembly_authorized, package_assembly_blocked, etc.
    authorization_decision: str  # authorize_metadata_only_future_assembly, block_future_assembly, etc.
    authorization_scope: str  # metadata_only
    source_final_package_readiness_report_digest: str
    source_distribution_package_manifest_digest: str
    source_dry_run_audit_report_digest: str
    source_package_assembly_plan_digest: str
    source_artifact_catalog_digest: str
    verified_final_package_count: int
    blocked_final_package_count: int
    pending_final_package_count: int
    invalid_final_package_count: int
    total_authorized_file_count: int
    rc1_authorized_file_count: int
    rc2_authorized_file_count: int
    shared_authorized_file_count: int
    authorized_target_package_sections: List[str]
    authorized_package_roles: List[str]
    authorized_artifact_types: List[str]
    authorized_artifact_formats: List[str]
    authorized_source_artifact_paths: List[str]
    authorized_target_package_paths: List[str]
    authorized_source_artifact_digests: List[str]
    authorized_layout_entry_digests: List[str]
    authorized_dry_run_case_digests: List[str]
    authorized_package_content_entry_digests: List[str]
    authorized_final_package_audit_case_digests: List[str]
    blocked_operation_attempt_counts: Dict[str, int]
    authorization_constraints: List[str]
    authorization_allowances: List[str]
    authorization_prohibitions: List[str]
    metadata_only_authorization: bool
    future_operation_authorized: bool
    archive_creation_authorized: bool
    file_copy_authorized: bool
    directory_creation_authorized: bool
    upload_authorized: bool
    deployment_authorized: bool
    signing_authorized: bool
    external_publication_authorized: bool
    production_mutation_authorized: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    package_assembly_authorization_envelope_digest: str = ""


def hash_waveguide_package_assembly_authorization_envelope(envelope: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of envelope excluding self-referential digest.
    """
    if hasattr(envelope, "__dict__"):
        e_dict = asdict(envelope)
    elif isinstance(envelope, dict):
        e_dict = dict(envelope)
    else:
        raise TypeError("envelope must be a dictionary or a dataclass instance")

    e_dict_copy = dict(e_dict)
    e_dict_copy.pop("package_assembly_authorization_envelope_digest", None)
    return hash_data(e_dict_copy)


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


def validate_waveguide_package_assembly_authorization_scope(scope: str) -> bool:
    """
    Verifies that the scope is strictly metadata_only.
    """
    return scope == "metadata_only"


def validate_waveguide_package_assembly_blocked_operation_zero_counts(counts: Dict[str, int]) -> bool:
    """
    Verifies all blocked operations counters remain zero.
    """
    expected_ops = [
        "archive_creation", "file_copy", "directory_creation",
        "upload", "deployment", "external_signing",
        "external_publication", "production_mutation"
    ]
    for op in expected_ops:
        if counts.get(op, -1) != 0:
            if op == "external_signing" and counts.get("signing", -1) == 0:
                continue
            return False
    return True


def build_waveguide_package_assembly_authorization_envelope(
    readiness_report_path_or_dict: Any
) -> WaveguidePackageAssemblyAuthorizationEnvelope:
    """
    Builds the Package Assembly Authorization Envelope from a Final Package Readiness Report.
    """
    report_dict = _load_dict(readiness_report_path_or_dict) or {}

    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    # Pre-defined constraints, allowances, and prohibitions
    constraints = sorted([
        "metadata_only",
        "non_mutating",
        "sandbox_validation_only",
        "future_operation_only",
        "requires_preflight_authorization_audit",
        "requires_no_archive_creation",
        "requires_no_file_copy",
        "requires_no_directory_creation",
        "requires_no_upload",
        "requires_no_deployment",
        "requires_no_signing",
        "requires_no_external_publication",
        "requires_no_production_mutation"
    ])
    allowances = sorted([
        "future_package_assembly_may_be_requested",
        "future_package_assembly_requires_preflight_validation",
        "future_package_assembly_requires_same_manifest_digest",
        "future_package_assembly_requires_same_final_readiness_digest",
        "future_package_assembly_requires_zero_blocked_operation_attempts"
    ])
    prohibitions = sorted([
        "no_archive_creation_by_authorization_envelope",
        "no_file_copy_by_authorization_envelope",
        "no_directory_creation_by_authorization_envelope",
        "no_upload_by_authorization_envelope",
        "no_deployment_by_authorization_envelope",
        "no_signing_by_authorization_envelope",
        "no_external_publication_by_authorization_envelope",
        "no_production_mutation_by_authorization_envelope"
    ])

    if not report_dict:
        env = WaveguidePackageAssemblyAuthorizationEnvelope(
            package_assembly_authorization_envelope_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-AUTHORIZATION-ENVELOPE",
            package_assembly_authorization_envelope_version=1,
            authorization_status="package_assembly_invalid",
            authorization_decision="invalid_authorization",
            authorization_scope="metadata_only",
            source_final_package_readiness_report_digest="",
            source_distribution_package_manifest_digest="",
            source_dry_run_audit_report_digest="",
            source_package_assembly_plan_digest="",
            source_artifact_catalog_digest="",
            verified_final_package_count=0,
            blocked_final_package_count=0,
            pending_final_package_count=0,
            invalid_final_package_count=0,
            total_authorized_file_count=0,
            rc1_authorized_file_count=0,
            rc2_authorized_file_count=0,
            shared_authorized_file_count=0,
            authorized_target_package_sections=[],
            authorized_package_roles=[],
            authorized_artifact_types=[],
            authorized_artifact_formats=[],
            authorized_source_artifact_paths=[],
            authorized_target_package_paths=[],
            authorized_source_artifact_digests=[],
            authorized_layout_entry_digests=[],
            authorized_dry_run_case_digests=[],
            authorized_package_content_entry_digests=[],
            authorized_final_package_audit_case_digests=[],
            blocked_operation_attempt_counts={
                "archive_creation": 0, "file_copy": 0, "directory_creation": 0,
                "upload": 0, "deployment": 0, "external_signing": 0,
                "external_publication": 0, "production_mutation": 0
            },
            authorization_constraints=constraints,
            authorization_allowances=allowances,
            authorization_prohibitions=prohibitions,
            metadata_only_authorization=True,
            future_operation_authorized=False,
            archive_creation_authorized=False,
            file_copy_authorized=False,
            directory_creation_authorized=False,
            upload_authorized=False,
            deployment_authorized=False,
            signing_authorized=False,
            external_publication_authorized=False,
            production_mutation_authorized=False,
            reason_codes=["PACKAGE_ASSEMBLY_INVALID"],
            notes=[],
            software_validation_caveat=caveat,
            package_assembly_authorization_envelope_digest=""
        )
        env.package_assembly_authorization_envelope_digest = hash_waveguide_package_assembly_authorization_envelope(env)
        return env

    # Validate final package readiness report
    report_valid, _ = validate_waveguide_final_package_readiness_audit_report(report_dict)

    final_digest = report_dict.get("final_package_readiness_report_digest", "")
    manifest_digest = report_dict.get("source_distribution_package_manifest_digest", "")
    dry_run_digest = report_dict.get("source_dry_run_audit_report_digest", "")
    plan_digest = report_dict.get("source_package_assembly_plan_digest", "")
    catalog_digest = report_dict.get("source_artifact_catalog_digest", "")

    v_count = report_dict.get("verified_final_package_count", 0)
    b_count = report_dict.get("blocked_final_package_count", 0)
    p_count = report_dict.get("pending_final_package_count", 0)
    i_count = report_dict.get("invalid_final_package_count", 0)

    rc1_count = report_dict.get("rc1_final_package_count", 0)
    rc2_count = report_dict.get("rc2_final_package_count", 0)
    shared_count = report_dict.get("shared_final_package_count", 0)

    blocked_counts = report_dict.get("blocked_operation_attempt_counts", {})
    blocked_zero = validate_waveguide_package_assembly_blocked_operation_zero_counts(blocked_counts)

    reason_codes = [
        "PACKAGE_AUTHORIZATION_ENVELOPE_CANONICAL",
        "PACKAGE_AUTHORIZATION_METADATA_ONLY",
        "PACKAGE_AUTHORIZATION_ARCHIVE_CREATION_PROHIBITED",
        "PACKAGE_AUTHORIZATION_FILE_COPY_PROHIBITED",
        "PACKAGE_AUTHORIZATION_DIRECTORY_CREATION_PROHIBITED",
        "PACKAGE_AUTHORIZATION_UPLOAD_PROHIBITED",
        "PACKAGE_AUTHORIZATION_DEPLOYMENT_PROHIBITED",
        "PACKAGE_AUTHORIZATION_SIGNING_PROHIBITED",
        "PACKAGE_AUTHORIZATION_EXTERNAL_PUBLICATION_PROHIBITED",
        "PACKAGE_AUTHORIZATION_PRODUCTION_MUTATION_PROHIBITED",
        "PACKAGE_AUTHORIZATION_SOFTWARE_CAVEAT_INCLUDED"
    ]

    if report_valid:
        reason_codes.append("PACKAGE_AUTHORIZATION_SOURCE_FINAL_READINESS_REPORT_VALID")
    else:
        reason_codes.append("PACKAGE_AUTHORIZATION_SOURCE_FINAL_READINESS_REPORT_INVALID")

    if report_dict.get("final_package_readiness_report_status") == "final_package_readiness_verified":
        reason_codes.append("PACKAGE_AUTHORIZATION_SOURCE_FINAL_READINESS_VERIFIED")

    if final_digest:
        reason_codes.append("PACKAGE_AUTHORIZATION_FINAL_READINESS_DIGEST_REFERENCED")
    if manifest_digest:
        reason_codes.append("PACKAGE_AUTHORIZATION_PACKAGE_MANIFEST_DIGEST_REFERENCED")
    if dry_run_digest:
        reason_codes.append("PACKAGE_AUTHORIZATION_DRY_RUN_REPORT_DIGEST_REFERENCED")
    if plan_digest:
        reason_codes.append("PACKAGE_AUTHORIZATION_ASSEMBLY_PLAN_DIGEST_REFERENCED")
    if catalog_digest:
        reason_codes.append("PACKAGE_AUTHORIZATION_ARTIFACT_CATALOG_DIGEST_REFERENCED")

    if v_count > 0:
        reason_codes.append("PACKAGE_AUTHORIZATION_VERIFIED_COUNT_VALID")
    if b_count == 0:
        reason_codes.append("PACKAGE_AUTHORIZATION_BLOCKED_COUNT_ZERO")
    if p_count == 0:
        reason_codes.append("PACKAGE_AUTHORIZATION_PENDING_COUNT_ZERO")
    if i_count == 0:
        reason_codes.append("PACKAGE_AUTHORIZATION_INVALID_COUNT_ZERO")

    if blocked_zero:
        reason_codes.append("PACKAGE_AUTHORIZATION_BLOCKED_OPERATION_COUNTS_ZERO")

    authorized = False
    if (report_valid and
        report_dict.get("final_package_readiness_report_status") == "final_package_readiness_verified" and
        v_count > 0 and b_count == 0 and p_count == 0 and i_count == 0 and blocked_zero):
        authorized = True

    if authorized:
        status = "package_assembly_authorized"
        decision = "authorize_metadata_only_future_assembly"
        reason_codes.append("PACKAGE_AUTHORIZATION_FUTURE_OPERATION_ALLOWED_IN_PRINCIPLE")
        reason_codes.append("PACKAGE_ASSEMBLY_AUTHORIZED")
    else:
        status = "package_assembly_blocked"
        decision = "block_future_assembly"
        reason_codes.append("PACKAGE_ASSEMBLY_BLOCKED")

    # Load structures
    env = WaveguidePackageAssemblyAuthorizationEnvelope(
        package_assembly_authorization_envelope_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-AUTHORIZATION-ENVELOPE",
        package_assembly_authorization_envelope_version=1,
        authorization_status=status,
        authorization_decision=decision,
        authorization_scope="metadata_only",
        source_final_package_readiness_report_digest=final_digest,
        source_distribution_package_manifest_digest=manifest_digest,
        source_dry_run_audit_report_digest=dry_run_digest,
        source_package_assembly_plan_digest=plan_digest,
        source_artifact_catalog_digest=catalog_digest,
        verified_final_package_count=v_count,
        blocked_final_package_count=b_count,
        pending_final_package_count=p_count,
        invalid_final_package_count=i_count,
        total_authorized_file_count=v_count,
        rc1_authorized_file_count=rc1_count,
        rc2_authorized_file_count=rc2_count,
        shared_authorized_file_count=shared_count,
        authorized_target_package_sections=sorted(report_dict.get("target_package_sections", [])),
        authorized_package_roles=sorted(report_dict.get("package_roles_indexed", [])),
        authorized_artifact_types=sorted(report_dict.get("artifact_types_indexed", [])),
        authorized_artifact_formats=sorted(report_dict.get("artifact_formats_indexed", [])),
        authorized_source_artifact_paths=sorted(report_dict.get("source_artifact_paths", [])),
        authorized_target_package_paths=sorted(report_dict.get("target_package_paths", [])),
        authorized_source_artifact_digests=sorted(report_dict.get("source_artifact_digests", [])),
        authorized_layout_entry_digests=sorted(report_dict.get("layout_entry_digests", [])),
        authorized_dry_run_case_digests=sorted(report_dict.get("dry_run_case_digests", [])),
        authorized_package_content_entry_digests=sorted(report_dict.get("package_content_entry_digests", [])),
        authorized_final_package_audit_case_digests=sorted(report_dict.get("final_package_audit_case_digests", [])),
        blocked_operation_attempt_counts={
            "archive_creation": blocked_counts.get("archive_creation", 0),
            "file_copy": blocked_counts.get("file_copy", 0),
            "directory_creation": blocked_counts.get("directory_creation", 0),
            "upload": blocked_counts.get("upload", 0),
            "deployment": blocked_counts.get("deployment", 0),
            "external_signing": blocked_counts.get("external_signing", 0) if "external_signing" in blocked_counts else blocked_counts.get("signing", 0),
            "external_publication": blocked_counts.get("external_publication", 0),
            "production_mutation": blocked_counts.get("production_mutation", 0)
        },
        authorization_constraints=constraints,
        authorization_allowances=allowances,
        authorization_prohibitions=prohibitions,
        metadata_only_authorization=True,
        future_operation_authorized=authorized,
        archive_creation_authorized=False,
        file_copy_authorized=False,
        directory_creation_authorized=False,
        upload_authorized=False,
        deployment_authorized=False,
        signing_authorized=False,
        external_publication_authorized=False,
        production_mutation_authorized=False,
        reason_codes=sorted(list(set(reason_codes))),
        notes=[],
        software_validation_caveat=caveat,
        package_assembly_authorization_envelope_digest=""
    )
    env.package_assembly_authorization_envelope_digest = hash_waveguide_package_assembly_authorization_envelope(env)
    return env


def validate_waveguide_package_assembly_authorization_envelope(
    envelope: Any
) -> Tuple[bool, List[str]]:
    """
    Validates a Package Assembly Authorization Envelope.
    """
    e_dict = _load_dict(envelope)
    reasons = []
    is_valid = True

    if not e_dict:
        return False, ["PACKAGE_ASSEMBLY_INVALID"]

    # 1. Check self digest
    given_digest = e_dict.get("package_assembly_authorization_envelope_digest")
    if not given_digest:
        is_valid = False
        reasons.append("PACKAGE_ASSEMBLY_INVALID")
    else:
        recomputed = hash_waveguide_package_assembly_authorization_envelope(e_dict)
        if recomputed != given_digest:
            is_valid = False
            reasons.append("PACKAGE_ASSEMBLY_INVALID")
        else:
            reasons.append("PACKAGE_AUTHORIZATION_ENVELOPE_DIGEST_VALID")

    # 2. Check counts and fields
    status = e_dict.get("authorization_status")
    decision = e_dict.get("authorization_decision")
    scope = e_dict.get("authorization_scope")

    if not e_dict.get("source_final_package_readiness_report_digest"):
        is_valid = False
        reasons.append("PACKAGE_ASSEMBLY_INVALID")

    if not e_dict.get("source_distribution_package_manifest_digest"):
        is_valid = False
        reasons.append("PACKAGE_ASSEMBLY_INVALID")

    if not e_dict.get("source_dry_run_audit_report_digest"):
        is_valid = False
        reasons.append("PACKAGE_ASSEMBLY_INVALID")

    v_count = e_dict.get("verified_final_package_count", 0)
    b_count = e_dict.get("blocked_final_package_count", 0)
    p_count = e_dict.get("pending_final_package_count", 0)
    i_count = e_dict.get("invalid_final_package_count", 0)
    total_count = e_dict.get("total_authorized_file_count", 0)

    if total_count != v_count:
        is_valid = False
        reasons.append("PACKAGE_ASSEMBLY_INVALID")

    # Check zero counts of blocked operations
    blocked_counts = e_dict.get("blocked_operation_attempt_counts", {})
    if not validate_waveguide_package_assembly_blocked_operation_zero_counts(blocked_counts):
        is_valid = False
        reasons.append("PACKAGE_ASSEMBLY_INVALID")

    # Scope and constraints check
    if not validate_waveguide_package_assembly_authorization_scope(scope):
        is_valid = False
        reasons.append("PACKAGE_ASSEMBLY_INVALID")

    # Boolean flags checks
    if e_dict.get("metadata_only_authorization") is not True:
        is_valid = False
        reasons.append("PACKAGE_ASSEMBLY_INVALID")

    # Prohibitions on mutations
    if (e_dict.get("archive_creation_authorized") is not False or
        e_dict.get("file_copy_authorized") is not False or
        e_dict.get("directory_creation_authorized") is not False or
        e_dict.get("upload_authorized") is not False or
        e_dict.get("deployment_authorized") is not False or
        e_dict.get("signing_authorized") is not False or
        e_dict.get("external_publication_authorized") is not False or
        e_dict.get("production_mutation_authorized") is not False):
        is_valid = False
        reasons.append("PACKAGE_ASSEMBLY_INVALID")

    # Software validation caveat
    if not e_dict.get("software_validation_caveat"):
        is_valid = False
        reasons.append("PACKAGE_ASSEMBLY_INVALID")

    if status == "package_assembly_authorized":
        if b_count > 0 or p_count > 0 or i_count > 0 or v_count == 0:
            is_valid = False
            reasons.append("PACKAGE_ASSEMBLY_INVALID")
        elif decision != "authorize_metadata_only_future_assembly" or e_dict.get("future_operation_authorized") is not True:
            is_valid = False
            reasons.append("PACKAGE_ASSEMBLY_INVALID")
    elif status == "package_assembly_blocked":
        if decision != "block_future_assembly" or e_dict.get("future_operation_authorized") is not False:
            is_valid = False
            reasons.append("PACKAGE_ASSEMBLY_INVALID")

    if is_valid:
        for code in e_dict.get("reason_codes", []):
            if code.startswith("PACKAGE_AUTHORIZATION_") or code.startswith("PACKAGE_ASSEMBLY_"):
                reasons.append(code)
        reasons.append("PACKAGE_ASSEMBLY_AUTHORIZED")
    else:
        reasons.append("PACKAGE_ASSEMBLY_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_assembly_authorization_envelope(envelope: Any) -> str:
    """
    Formats a plaintext summary of the authorization envelope.
    """
    e_dict = asdict(envelope) if hasattr(envelope, "__dict__") else dict(envelope)
    lines = [
        "============================================================",
        "      SOL WAVEGUIDE PACKAGE ASSEMBLY AUTHORIZATION ENVELOPE",
        "============================================================",
        f"Envelope ID:        {e_dict.get('package_assembly_authorization_envelope_id')}",
        f"Version:            {e_dict.get('package_assembly_authorization_envelope_version')}",
        f"Status:             {e_dict.get('authorization_status', '').upper()}",
        f"Decision:           {e_dict.get('authorization_decision', '').upper()}",
        f"Scope:              {e_dict.get('authorization_scope')}",
        f"Report Digest:      {e_dict.get('source_final_package_readiness_report_digest')}",
        f"Envelope Digest:    {e_dict.get('package_assembly_authorization_envelope_digest')}",
        "------------------------------------------------------------",
        f"Authorized Files Count: {e_dict.get('total_authorized_file_count')}",
        f"  - RC1 Count:          {e_dict.get('rc1_authorized_file_count')}",
        f"  - RC2 Count:          {e_dict.get('rc2_authorized_file_count')}",
        f"  - Shared Count:       {e_dict.get('shared_authorized_file_count')}",
        "------------------------------------------------------------",
        "Constraints Met:",
    ]
    for c in e_dict.get("authorization_constraints", []):
        lines.append(f"  - {c}")
    lines.append("------------------------------------------------------------")
    lines.append("Allowances:")
    for a in e_dict.get("authorization_allowances", []):
        lines.append(f"  - {a}")
    lines.append("------------------------------------------------------------")
    lines.append("Prohibitions enforced:")
    for p in e_dict.get("authorization_prohibitions", []):
        lines.append(f"  - {p}")
    lines.append("------------------------------------------------------------")
    lines.append("Enforced Mutation Prohibitions (All must be False):")
    lines.append(f"  - archive_creation:      {e_dict.get('archive_creation_authorized')}")
    lines.append(f"  - file_copy:             {e_dict.get('file_copy_authorized')}")
    lines.append(f"  - directory_creation:    {e_dict.get('directory_creation_authorized')}")
    lines.append(f"  - upload:                {e_dict.get('upload_authorized')}")
    lines.append(f"  - deployment:            {e_dict.get('deployment_authorized')}")
    lines.append(f"  - signing:               {e_dict.get('signing_authorized')}")
    lines.append(f"  - external_publication:  {e_dict.get('external_publication_authorized')}")
    lines.append(f"  - production_mutation:   {e_dict.get('production_mutation_authorized')}")
    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in e_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")
    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {e_dict.get('software_validation_caveat')}")
    lines.append("============================================================")
    return "\n".join(lines)


def export_waveguide_package_assembly_authorization_envelope(envelope: Any, filepath: str) -> None:
    """
    Exports the envelope to a sorted JSON file.
    """
    e_dict = asdict(envelope) if hasattr(envelope, "__dict__") else dict(envelope)
    full_path = os.path.join(REPO_ROOT, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(e_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_assembly_authorization_envelopes(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two envelopes.
    """
    l_dict = asdict(left) if hasattr(left, "__dict__") else dict(left)
    r_dict = asdict(right) if hasattr(right, "__dict__") else dict(right)
    diff = {
        "envelope_id_match": l_dict.get("package_assembly_authorization_envelope_id") == r_dict.get("package_assembly_authorization_envelope_id"),
        "authorization_status_match": l_dict.get("authorization_status") == r_dict.get("authorization_status"),
        "authorization_decision_match": l_dict.get("authorization_decision") == r_dict.get("authorization_decision"),
        "envelope_digest_match": l_dict.get("package_assembly_authorization_envelope_digest") == r_dict.get("package_assembly_authorization_envelope_digest"),
        "authorized_count_diff": l_dict.get("total_authorized_file_count", 0) - r_dict.get("total_authorized_file_count", 0),
        "source_report_digest_match": l_dict.get("source_final_package_readiness_report_digest") == r_dict.get("source_final_package_readiness_report_digest")
    }
    diff["all_match"] = (
        diff["envelope_id_match"] and
        diff["authorization_status_match"] and
        diff["authorization_decision_match"] and
        diff["envelope_digest_match"] and
        diff["authorized_count_diff"] == 0 and
        diff["source_report_digest_match"]
    )
    return diff


def index_waveguide_package_authorization_references_by_source(envelope: Any) -> Dict[str, List[str]]:
    """
    Indexes authorized source artifact paths by their source repository category.
    """
    e_dict = asdict(envelope) if hasattr(envelope, "__dict__") else dict(envelope)
    idx = {}
    for path in e_dict.get("authorized_source_artifact_paths", []):
        prefix = path.split("/")[0] if "/" in path else "other"
        if prefix not in idx:
            idx[prefix] = []
        idx[prefix].append(path)
    return idx
