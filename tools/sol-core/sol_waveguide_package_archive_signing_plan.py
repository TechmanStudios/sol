# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Package Archive Signing Plan.
Consumes the Package Archive Release Candidate Index and constructs a deterministic
signing plan that restricts operations to local digest attestation only.
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
from sol_waveguide_package_archive_release_candidate_index import (
    validate_waveguide_package_archive_release_candidate_index
)


@dataclass
class WaveguidePackageArchiveSigningPlanEntry:
    archive_signing_plan_entry_id: str
    archive_signing_plan_entry_status: str  # archive_signing_plan_entry_ready, etc.
    archive_candidate_entry_id: str
    archive_candidate_digest: str
    archive_candidate_kind: str
    source_archive_candidate_entry_digest: str
    source_package_archive_release_candidate_index_digest: str
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_format: str
    archive_filename: str
    archive_display_path: str
    archive_file_digest: str
    archive_file_size_bytes: int
    expected_archive_file_count: int
    verified_archive_member_count: int
    archive_digest_verified: bool
    archive_file_set_verified: bool
    archive_member_paths_safe: bool
    digest_attestation_required: bool
    digest_attestation_allowed: bool
    real_key_signing_required: bool
    real_key_signing_allowed: bool
    external_signing_allowed: bool
    timestamp_authority_allowed: bool
    upload_allowed: bool
    deployment_allowed: bool
    external_publication_allowed: bool
    production_mutation_allowed: bool
    signing_policy: str
    signing_constraints: List[str]
    signing_allowances: List[str]
    signing_prohibitions: List[str]
    signing_guard_requirements: List[str]
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    archive_signing_plan_entry_digest: str = ""


@dataclass
class WaveguidePackageArchiveSigningPlan:
    package_archive_signing_plan_id: str
    package_archive_signing_plan_version: int
    package_archive_signing_plan_status: str  # package_archive_signing_plan_ready, etc.
    source_package_archive_release_candidate_index_digest: str
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_signing_plan_entries: List[WaveguidePackageArchiveSigningPlanEntry]
    ready_archive_signing_plan_entries: List[str]
    blocked_archive_signing_plan_entries: List[str]
    warning_archive_signing_plan_entries: List[str]
    invalid_archive_signing_plan_entries: List[str]
    ready_archive_signing_plan_entry_count: int
    blocked_archive_signing_plan_entry_count: int
    warning_archive_signing_plan_entry_count: int
    invalid_archive_signing_plan_entry_count: int
    archive_candidate_count: int
    verified_archive_candidate_count: int
    current_archive_candidate_digest: str
    current_archive_candidate_format: str
    current_archive_candidate_display_path: str
    current_archive_candidate_size_bytes: int
    signing_policy: str
    signing_constraints: List[str]
    signing_allowances: List[str]
    signing_prohibitions: List[str]
    signing_guard_requirements: List[str]
    digest_attestation_required: bool
    digest_attestation_allowed: bool
    real_key_signing_required: bool
    real_key_signing_allowed: bool
    external_signing_allowed: bool
    timestamp_authority_allowed: bool
    upload_allowed: bool
    deployment_allowed: bool
    external_publication_allowed: bool
    production_mutation_allowed: bool
    signing_performed: bool
    real_key_signature_performed: bool
    digest_attestation_performed: bool
    external_signing_performed: bool
    timestamp_authority_performed: bool
    upload_performed: bool
    deployment_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    package_archive_signing_plan_digest: str = ""


def hash_waveguide_package_archive_signing_plan_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a signing plan entry,
    excluding archive_signing_plan_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or dataclass instance")

    e_copy = dict(e_dict)
    e_copy.pop("archive_signing_plan_entry_digest", None)
    return hash_data(e_copy)


def hash_waveguide_package_archive_signing_plan(plan: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a signing plan,
    excluding package_archive_signing_plan_digest.
    """
    if hasattr(plan, "__dict__"):
        p_dict = asdict(plan)
    elif isinstance(plan, dict):
        p_dict = dict(plan)
    else:
        raise TypeError("plan must be a dictionary or dataclass instance")

    p_copy = dict(p_dict)
    p_copy.pop("package_archive_signing_plan_digest", None)
    return hash_data(p_copy)


def build_waveguide_package_archive_signing_policy() -> str:
    return "SOL Waveguide Digest Attestation Policy - Real private key signing is strictly disabled. Local digest attestation only."


def validate_waveguide_package_archive_signing_policy(policy: str) -> bool:
    return policy == build_waveguide_package_archive_signing_policy()


def validate_waveguide_package_archive_signing_scope(scope: str) -> bool:
    return scope == "controlled_local_archive_attestation_scope"


def validate_waveguide_package_archive_digest_attestation_policy(
    req: bool, allowed: bool
) -> bool:
    return req is True and allowed is True


def validate_waveguide_package_archive_real_key_signing_disabled(
    req: bool, allowed: bool, ext_allowed: bool, ts_allowed: bool
) -> bool:
    return req is False and allowed is False and ext_allowed is False and ts_allowed is False


def index_waveguide_package_archive_signing_entries_by_status(
    entries: List[WaveguidePackageArchiveSigningPlanEntry]
) -> Dict[str, List[str]]:
    indexed = {
        "ready": [],
        "blocked": [],
        "warning": [],
        "invalid": []
    }
    for e in entries:
        status = e.archive_signing_plan_entry_status
        if status == "archive_signing_plan_entry_ready":
            indexed["ready"].append(e.archive_signing_plan_entry_id)
        elif status == "archive_signing_plan_entry_blocked":
            indexed["blocked"].append(e.archive_signing_plan_entry_id)
        elif status == "archive_signing_plan_entry_warning":
            indexed["warning"].append(e.archive_signing_plan_entry_id)
        else:
            indexed["invalid"].append(e.archive_signing_plan_entry_id)
    return indexed


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


def build_waveguide_package_archive_signing_plan_entry(
    candidate_entry: Dict[str, Any],
    index: int,
    rc_digest: str
) -> WaveguidePackageArchiveSigningPlanEntry:
    """
    Builds a single archive signing plan entry from a candidate entry.
    """
    cand_status = candidate_entry.get("archive_candidate_status", "")
    cand_id = candidate_entry.get("archive_candidate_entry_id", "")
    cand_digest = candidate_entry.get("archive_file_digest", "")

    status = "archive_signing_plan_entry_ready"
    reason_codes = ["SIGNING_ENTRY_READY"]

    if cand_status != "archive_candidate_verified":
        status = "archive_signing_plan_entry_blocked"
        reason_codes = ["CANDIDATE_ENTRY_NOT_VERIFIED"]

    if not cand_digest:
        status = "archive_signing_plan_entry_invalid"
        reason_codes = ["MISSING_CANDIDATE_DIGEST"]

    # Enforce performance boundaries checks
    signing_performed = candidate_entry.get("signing_performed", False)
    upload_performed = candidate_entry.get("upload_performed", False)
    publication_performed = candidate_entry.get("external_publication_performed", False)
    deployment_performed = candidate_entry.get("deployment_performed", False)
    production_mutation_performed = candidate_entry.get("production_mutation_performed", False)

    if signing_performed or upload_performed or publication_performed or deployment_performed or production_mutation_performed:
        status = "archive_signing_plan_entry_invalid"
        reason_codes.append("CANDIDATE_MUTATION_VIOLATION")

    entry = WaveguidePackageArchiveSigningPlanEntry(
        archive_signing_plan_entry_id=f"SOL-WAVEGUIDE-SIGNING-PLAN-ENTRY-{index:03d}",
        archive_signing_plan_entry_status=status,
        archive_candidate_entry_id=cand_id,
        archive_candidate_digest=cand_digest,
        archive_candidate_kind=candidate_entry.get("archive_candidate_kind", ""),
        source_archive_candidate_entry_digest=candidate_entry.get("archive_candidate_entry_digest", ""),
        source_package_archive_release_candidate_index_digest=rc_digest,
        source_package_archive_audit_report_digest=candidate_entry.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=candidate_entry.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=candidate_entry.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=candidate_entry.get("source_package_archive_plan_digest", ""),
        archive_format=candidate_entry.get("archive_format", ""),
        archive_filename=candidate_entry.get("archive_filename", ""),
        archive_display_path=candidate_entry.get("archive_display_path", ""),
        archive_file_digest=cand_digest,
        archive_file_size_bytes=candidate_entry.get("archive_file_size_bytes", 0),
        expected_archive_file_count=candidate_entry.get("expected_archive_file_count", 0),
        verified_archive_member_count=candidate_entry.get("verified_archive_member_count", 0),
        archive_digest_verified=candidate_entry.get("archive_digest_verified", False),
        archive_file_set_verified=candidate_entry.get("archive_file_set_verified", False),
        archive_member_paths_safe=candidate_entry.get("archive_member_paths_safe", False),
        digest_attestation_required=True,
        digest_attestation_allowed=True,
        real_key_signing_required=False,
        real_key_signing_allowed=False,
        external_signing_allowed=False,
        timestamp_authority_allowed=False,
        upload_allowed=False,
        deployment_allowed=False,
        external_publication_allowed=False,
        production_mutation_allowed=False,
        signing_policy=build_waveguide_package_archive_signing_policy(),
        signing_constraints=["REAL_KEY_SIGNING_DISABLED", "NO_EXTERNAL_SIGNING_SERVICES", "NO_TIMESTAMP_AUTHORITY"],
        signing_allowances=["LOCAL_DIGEST_ATTESTATION_ALLOWED"],
        signing_prohibitions=["REAL_KEY_SIGNING_PROHIBITED", "UPLOAD_PROHIBITED", "DEPLOYMENT_PROHIBITED", "EXTERNAL_PUBLICATION_PROHIBITED", "PRODUCTION_MUTATION_PROHIBITED"],
        signing_guard_requirements=["REQUIRES_DIGEST_ATTESTATION_VALIDATOR", "REQUIRES_FUTURE_KEY_MANAGEMENT_GATE"],
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    entry.archive_signing_plan_entry_digest = hash_waveguide_package_archive_signing_plan_entry(entry)
    return entry


def validate_waveguide_package_archive_signing_plan_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a signing plan entry.
    """
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    errors = []

    # Verify digest
    recorded = e_dict.get("archive_signing_plan_entry_digest", "")
    if not recorded:
        errors.append("Missing entry digest")
    else:
        recomputed = hash_waveguide_package_archive_signing_plan_entry(e_dict)
        if recomputed != recorded:
            errors.append(f"Entry digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    # Enforce prohibitions and allowances
    prohibitions = [
        ("real_key_signing_required", False),
        ("real_key_signing_allowed", False),
        ("external_signing_allowed", False),
        ("timestamp_authority_allowed", False),
        ("upload_allowed", False),
        ("deployment_allowed", False),
        ("external_publication_allowed", False),
        ("production_mutation_allowed", False),
    ]
    for key, expected in prohibitions:
        if e_dict.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    allowances = [
        ("digest_attestation_required", True),
        ("digest_attestation_allowed", True),
    ]
    for key, expected in allowances:
        if e_dict.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    policy = e_dict.get("signing_policy", "")
    if not validate_waveguide_package_archive_signing_policy(policy):
        errors.append("Invalid signing policy")

    return len(errors) == 0, errors


def build_waveguide_package_archive_signing_plan(
    candidate_index_path_or_dict: Any
) -> WaveguidePackageArchiveSigningPlan:
    """
    Builds the Package Archive Signing Plan from the Candidate Index.
    """
    idx_dict = _load_dict(candidate_index_path_or_dict) or {}
    rc_digest = idx_dict.get("package_archive_release_candidate_index_digest", "")
    rc_status = idx_dict.get("package_archive_release_candidate_index_status", "")

    plan_status = "package_archive_signing_plan_ready"
    reason_codes = ["PACKAGE_ARCHIVE_SIGNING_PLAN_READY"]

    valid_rc, rc_errs = validate_waveguide_package_archive_release_candidate_index(idx_dict)
    if not valid_rc or rc_status != "package_archive_candidate_index_valid":
        plan_status = "package_archive_signing_plan_blocked"
        reason_codes = ["RELEASE_CANDIDATE_INDEX_NOT_VALID"]

    # Enforce prohibitions check
    signing_performed = idx_dict.get("signing_performed", False)
    upload_performed = idx_dict.get("upload_performed", False)
    publication_performed = idx_dict.get("external_publication_performed", False)
    deployment_performed = idx_dict.get("deployment_performed", False)
    production_mutation_performed = idx_dict.get("production_mutation_performed", False)

    if signing_performed or upload_performed or publication_performed or deployment_performed or production_mutation_performed:
        plan_status = "package_archive_signing_plan_invalid"
        reason_codes.append("CANDIDATE_MUTATION_VIOLATION")

    candidate_entries = idx_dict.get("archive_candidates", [])
    entries = []
    for i, ce in enumerate(candidate_entries):
        entry = build_waveguide_package_archive_signing_plan_entry(ce, i, rc_digest)
        entries.append(entry)

    indexed = index_waveguide_package_archive_signing_entries_by_status(entries)

    ready_ids = indexed["ready"]
    blocked_ids = indexed["blocked"]
    warning_ids = indexed["warning"]
    invalid_ids = indexed["invalid"]

    if len(invalid_ids) > 0 or len(blocked_ids) > 0 or plan_status == "package_archive_signing_plan_invalid":
        plan_status = "package_archive_signing_plan_invalid"
        reason_codes.append("PLAN_ENTRIES_INVALID_OR_BLOCKED")

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

    plan = WaveguidePackageArchiveSigningPlan(
        package_archive_signing_plan_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-SIGNING-PLAN",
        package_archive_signing_plan_version=1,
        package_archive_signing_plan_status=plan_status,
        source_package_archive_release_candidate_index_digest=rc_digest,
        source_package_archive_audit_report_digest=idx_dict.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=idx_dict.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=idx_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=idx_dict.get("source_package_archive_plan_digest", ""),
        archive_signing_plan_entries=entries,
        ready_archive_signing_plan_entries=ready_ids,
        blocked_archive_signing_plan_entries=blocked_ids,
        warning_archive_signing_plan_entries=warning_ids,
        invalid_archive_signing_plan_entries=invalid_ids,
        ready_archive_signing_plan_entry_count=len(ready_ids),
        blocked_archive_signing_plan_entry_count=len(blocked_ids),
        warning_archive_signing_plan_entry_count=len(warning_ids),
        invalid_archive_signing_plan_entry_count=len(invalid_ids),
        archive_candidate_count=idx_dict.get("verified_archive_candidate_count", 0),
        verified_archive_candidate_count=len(ready_ids),
        current_archive_candidate_digest=idx_dict.get("current_archive_candidate_digest", ""),
        current_archive_candidate_format=idx_dict.get("current_archive_candidate_format", ""),
        current_archive_candidate_display_path=idx_dict.get("current_archive_candidate_display_path", ""),
        current_archive_candidate_size_bytes=idx_dict.get("current_archive_candidate_size_bytes", 0),
        signing_policy=build_waveguide_package_archive_signing_policy(),
        signing_constraints=["REAL_KEY_SIGNING_DISABLED", "NO_EXTERNAL_SIGNING_SERVICES", "NO_TIMESTAMP_AUTHORITY"],
        signing_allowances=["LOCAL_DIGEST_ATTESTATION_ALLOWED"],
        signing_prohibitions=["REAL_KEY_SIGNING_PROHIBITED", "UPLOAD_PROHIBITED", "DEPLOYMENT_PROHIBITED", "EXTERNAL_PUBLICATION_PROHIBITED", "PRODUCTION_MUTATION_PROHIBITED"],
        signing_guard_requirements=["REQUIRES_DIGEST_ATTESTATION_VALIDATOR", "REQUIRES_FUTURE_KEY_MANAGEMENT_GATE"],
        digest_attestation_required=True,
        digest_attestation_allowed=True,
        real_key_signing_required=False,
        real_key_signing_allowed=False,
        external_signing_allowed=False,
        timestamp_authority_allowed=False,
        upload_allowed=False,
        deployment_allowed=False,
        external_publication_allowed=False,
        production_mutation_allowed=False,
        signing_performed=False,
        real_key_signature_performed=False,
        digest_attestation_performed=False,
        external_signing_performed=False,
        timestamp_authority_performed=False,
        upload_performed=False,
        deployment_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    plan.package_archive_signing_plan_digest = hash_waveguide_package_archive_signing_plan(plan)
    return plan


def validate_waveguide_package_archive_signing_plan(plan: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a top-level Package Archive Signing Plan.
    """
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    errors = []

    # Verify digest
    recorded = p_dict.get("package_archive_signing_plan_digest", "")
    if not recorded:
        errors.append("Missing plan digest")
    else:
        recomputed = hash_waveguide_package_archive_signing_plan(p_dict)
        if recomputed != recorded:
            errors.append(f"Plan digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if p_dict.get("package_archive_signing_plan_id") != "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-SIGNING-PLAN":
        errors.append("Invalid signing plan ID")

    # Enforce prohibitions
    prohibitions = [
        ("real_key_signing_required", False),
        ("real_key_signing_allowed", False),
        ("external_signing_allowed", False),
        ("timestamp_authority_allowed", False),
        ("upload_allowed", False),
        ("deployment_allowed", False),
        ("external_publication_allowed", False),
        ("production_mutation_allowed", False),
        ("signing_performed", False),
        ("real_key_signature_performed", False),
        ("digest_attestation_performed", False),
        ("external_signing_performed", False),
        ("timestamp_authority_performed", False),
        ("upload_performed", False),
        ("deployment_performed", False),
        ("external_publication_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if p_dict.get(key) is not expected:
            errors.append(f"Top-level {key} must be {expected}")

    allowances = [
        ("digest_attestation_required", True),
        ("digest_attestation_allowed", True),
    ]
    for key, expected in allowances:
        if p_dict.get(key) is not expected:
            errors.append(f"Top-level {key} must be {expected}")

    policy = p_dict.get("signing_policy", "")
    if not validate_waveguide_package_archive_signing_policy(policy):
        errors.append("Invalid top-level signing policy")

    # Validate entries
    entries = p_dict.get("archive_signing_plan_entries", [])
    for e in entries:
        ok, errs = validate_waveguide_package_archive_signing_plan_entry(e)
        if not ok:
            errors.extend(errs)

    return len(errors) == 0, errors


def summarize_waveguide_package_archive_signing_plan(plan: Any) -> str:
    """
    Generates a human-readable summary of the Signing Plan.
    """
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    lines = [
        "=============================================================",
        "               SOL WAVEGUIDE PACKAGE SIGNING PLAN",
        "=============================================================",
        f"Plan ID:          {p_dict.get('package_archive_signing_plan_id')}",
        f"Status:           {p_dict.get('package_archive_signing_plan_status')}",
        f"Digest:           {p_dict.get('package_archive_signing_plan_digest')}",
        f"Format / Size:    {p_dict.get('current_archive_candidate_format')} / {p_dict.get('current_archive_candidate_size_bytes')} bytes",
        f"Candidate Digest: {p_dict.get('current_archive_candidate_digest')}",
        f"Ready Entries:    {p_dict.get('ready_archive_signing_plan_entry_count')}",
        f"Attest Required:  {p_dict.get('digest_attestation_required')}",
        f"Real Sign Allowed: {p_dict.get('real_key_signing_allowed')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in p_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_archive_signing_plan(plan: Any, output_path: str) -> None:
    """
    Exports the Signing Plan to a JSON file.
    """
    p_dict = asdict(plan) if hasattr(plan, "__dict__") else dict(plan)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(p_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_archive_signing_plans(plan_a: Any, plan_b: Any) -> Dict[str, Any]:
    """
    Compares two Signing Plans.
    """
    dict_a = asdict(plan_a) if hasattr(plan_a, "__dict__") else dict(plan_a)
    dict_b = asdict(plan_b) if hasattr(plan_b, "__dict__") else dict(plan_b)

    differences = {}
    for key in (
        "package_archive_signing_plan_status",
        "package_archive_signing_plan_digest",
        "ready_archive_signing_plan_entry_count"
    ):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
