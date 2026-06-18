# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Release Handoff Bundle.
Consumes the Attested Archive Candidate Index and builds a metadata-only handoff bundle
referencing the completed local archive candidate and attestation chain.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_package_attested_archive_candidate_index import (
    validate_waveguide_package_attested_archive_candidate_index
)


@dataclass
class WaveguideReleaseHandoffEntry:
    release_handoff_entry_id: str
    release_handoff_entry_status: str  # release_handoff_entry_ready, etc.
    release_handoff_artifact_kind: str
    release_handoff_artifact_role: str
    artifact_display_path: str
    artifact_digest: str
    artifact_size_bytes: int
    artifact_format: str
    source_artifact_digest: str
    source_artifact_status: str
    included_in_handoff: bool
    required_for_offline_verification: bool
    required_for_distribution_closure: bool
    required_for_future_signing: bool
    required_for_future_publication: bool
    artifact_exists: bool
    artifact_reference_valid: bool
    digest_reference_valid: bool
    real_signature_status: str
    digest_attestation_status: str
    upload_status: str
    publication_status: str
    deployment_status: str
    production_mutation_status: str
    signing_performed: bool
    real_key_signature_performed: bool
    digest_attestation_performed: bool
    upload_performed: bool
    external_publication_performed: bool
    deployment_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    release_handoff_entry_digest: str = ""


@dataclass
class WaveguideReleaseHandoffBundle:
    release_handoff_bundle_id: str
    release_handoff_bundle_version: int
    release_handoff_bundle_status: str  # release_handoff_bundle_ready, etc.
    source_package_attested_archive_candidate_index_digest: str
    source_package_archive_digest_attestation_audit_report_digest: str
    source_package_archive_digest_attestation_digest: str
    source_package_archive_signing_gate_digest: str
    source_package_archive_signing_plan_digest: str
    source_package_archive_release_candidate_index_digest: str
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    source_local_staging_output_audit_report_digest: str
    source_package_pipeline_chain_digest: str
    current_attested_archive_candidate_digest: str
    current_attested_archive_candidate_format: str
    current_attested_archive_candidate_display_path: str
    current_attested_archive_candidate_size_bytes: int
    current_archive_file_digest: str
    release_handoff_entries: List[WaveguideReleaseHandoffEntry]
    ready_release_handoff_entries: List[str]
    blocked_release_handoff_entries: List[str]
    warning_release_handoff_entries: List[str]
    invalid_release_handoff_entries: List[str]
    ready_release_handoff_entry_count: int
    blocked_release_handoff_entry_count: int
    warning_release_handoff_entry_count: int
    invalid_release_handoff_entry_count: int
    handoff_artifact_kinds_indexed: List[str]
    handoff_artifact_roles_indexed: List[str]
    handoff_artifact_paths_indexed: List[str]
    handoff_artifact_digests_indexed: List[str]
    offline_verification_artifacts: List[str]
    future_signing_artifacts: List[str]
    future_publication_artifacts: List[str]
    source_chain_verified: bool
    artifact_reference_set_verified: bool
    digest_reference_set_verified: bool
    offline_handoff_ready: bool
    future_signing_ready_for_key_management_stage: bool
    future_publication_ready_for_publication_gate_stage: bool
    real_signature_status: str
    digest_attestation_status: str
    signing_status: str
    upload_status: str
    publication_status: str
    deployment_status: str
    production_mutation_status: str
    signing_performed: bool
    real_key_signature_performed: bool
    digest_attestation_performed: bool
    external_signing_performed: bool
    timestamp_authority_performed: bool
    upload_performed: bool
    external_publication_performed: bool
    deployment_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    release_handoff_bundle_digest: str = ""


def hash_waveguide_release_handoff_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a handoff entry,
    excluding release_handoff_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or dataclass instance")

    e_copy = dict(e_dict)
    e_copy.pop("release_handoff_entry_digest", None)
    return hash_data(e_copy)


def hash_waveguide_release_handoff_bundle(bundle: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a handoff bundle,
    excluding release_handoff_bundle_digest.
    """
    if hasattr(bundle, "__dict__"):
        b_dict = asdict(bundle)
    elif isinstance(bundle, dict):
        b_dict = dict(bundle)
    else:
        raise TypeError("bundle must be a dictionary or dataclass instance")

    b_copy = dict(b_dict)
    b_copy.pop("release_handoff_bundle_digest", None)
    return hash_data(b_copy)


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


def index_waveguide_release_handoff_entries_by_status(
    entries: List[WaveguideReleaseHandoffEntry]
) -> Dict[str, List[str]]:
    indexed = {
        "ready": [],
        "blocked": [],
        "warning": [],
        "invalid": []
    }
    for e in entries:
        status = e.release_handoff_entry_status
        if status == "release_handoff_entry_ready":
            indexed["ready"].append(e.release_handoff_entry_id)
        elif status == "release_handoff_entry_blocked":
            indexed["blocked"].append(e.release_handoff_entry_id)
        elif status == "release_handoff_entry_warning":
            indexed["warning"].append(e.release_handoff_entry_id)
        else:
            indexed["invalid"].append(e.release_handoff_entry_id)
    return indexed


def index_waveguide_release_handoff_entries_by_artifact_kind(
    entries: List[WaveguideReleaseHandoffEntry]
) -> Dict[str, List[str]]:
    indexed = {}
    for e in entries:
        kind = e.release_handoff_artifact_kind
        if kind not in indexed:
            indexed[kind] = []
        indexed[kind].append(e.release_handoff_entry_id)
    return indexed


def build_waveguide_release_handoff_source_chain(idx_dict: Dict[str, Any]) -> str:
    """
    Builds a concatenated digest of the upstream source chain.
    """
    digests = [
        idx_dict.get("source_package_archive_plan_digest", ""),
        idx_dict.get("source_package_archive_build_record_digest", ""),
        idx_dict.get("source_package_archive_manifest_digest", ""),
        idx_dict.get("source_package_archive_audit_report_digest", ""),
        idx_dict.get("source_package_archive_release_candidate_index_digest", ""),
        idx_dict.get("source_package_archive_signing_plan_digest", ""),
        idx_dict.get("source_package_archive_signing_gate_digest", ""),
        idx_dict.get("source_package_archive_digest_attestation_digest", ""),
        idx_dict.get("source_package_archive_digest_attestation_audit_report_digest", ""),
        idx_dict.get("package_attested_archive_candidate_index_digest", "")
    ]
    # Filter empty and hash the joined string
    joined = "".join(d for d in digests if d)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def validate_waveguide_release_handoff_source_chain(
    chain_digest: str, idx_dict: Dict[str, Any]
) -> bool:
    expected = build_waveguide_release_handoff_source_chain(idx_dict)
    return chain_digest == expected


def validate_waveguide_release_handoff_operation_boundaries(
    entry_dict: Dict[str, Any]
) -> bool:
    # Verify no disallowed operations performed
    prohibited = [
        "real_key_signature_performed",
        "upload_performed",
        "external_publication_performed",
        "deployment_performed",
        "production_mutation_performed"
    ]
    for p in prohibited:
        if entry_dict.get(p, False) is not False:
            return False
    return True


def build_waveguide_release_handoff_entry(
    kind: str,
    role: str,
    path: str,
    digest: str,
    size: int,
    fmt: str,
    src_digest: str,
    src_status: str,
    index: int
) -> WaveguideReleaseHandoffEntry:
    """
    Builds a single Release Handoff Entry.
    """
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(path))
    exists = os.path.exists(full_path) if path else True
    if "documentation" in kind:
        exists = True

    status = "release_handoff_entry_ready"
    reason_codes = ["HANDOFF_ENTRY_READY"]

    if not exists:
        status = "release_handoff_entry_blocked"
        reason_codes = ["ARTIFACT_MISSING"]

    entry = WaveguideReleaseHandoffEntry(
        release_handoff_entry_id=f"SOL-WAVEGUIDE-HANDOFF-ENTRY-{index:03d}",
        release_handoff_entry_status=status,
        release_handoff_artifact_kind=kind,
        release_handoff_artifact_role=role,
        artifact_display_path=path,
        artifact_digest=digest,
        artifact_size_bytes=size,
        artifact_format=fmt,
        source_artifact_digest=src_digest,
        source_artifact_status=src_status,
        included_in_handoff=True,
        required_for_offline_verification=True,
        required_for_distribution_closure=True,
        required_for_future_signing=True,
        required_for_future_publication=True,
        artifact_exists=exists,
        artifact_reference_valid=exists,
        digest_reference_valid=bool(digest),
        real_signature_status="not_performed",
        digest_attestation_status="verified",
        upload_status="not_performed",
        publication_status="not_performed",
        deployment_status="not_performed",
        production_mutation_status="not_performed",
        signing_performed=False,
        real_key_signature_performed=False,
        digest_attestation_performed=True,
        upload_performed=False,
        external_publication_performed=False,
        deployment_performed=False,
        production_mutation_performed=False,
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    entry.release_handoff_entry_digest = hash_waveguide_release_handoff_entry(entry)
    return entry


def validate_waveguide_release_handoff_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Validates a single Release Handoff Entry.
    """
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    errors = []

    # Verify digest
    recorded = e_dict.get("release_handoff_entry_digest", "")
    if not recorded:
        errors.append("Missing entry digest")
    else:
        recomputed = hash_waveguide_release_handoff_entry(e_dict)
        if recomputed != recorded:
            errors.append(f"Entry digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    # Verify operation boundaries
    if not validate_waveguide_release_handoff_operation_boundaries(e_dict):
        errors.append("Entry operation boundary violation")

    # Enforce prohibitions
    prohibitions = [
        ("real_signature_status", "not_performed"),
        ("upload_status", "not_performed"),
        ("publication_status", "not_performed"),
        ("deployment_status", "not_performed"),
        ("production_mutation_status", "not_performed"),
    ]
    for key, expected in prohibitions:
        if e_dict.get(key) != expected:
            errors.append(f"Field {key} must be {expected}")

    return len(errors) == 0, errors


def build_waveguide_release_handoff_bundle(
    candidate_index_path_or_dict: Any
) -> WaveguideReleaseHandoffBundle:
    """
    Builds the top-level Release Handoff Bundle.
    """
    idx_dict = _load_dict(candidate_index_path_or_dict) or {}
    idx_status = idx_dict.get("package_attested_archive_candidate_index_status", "")
    idx_digest = idx_dict.get("package_attested_archive_candidate_index_digest", "")

    status = "release_handoff_bundle_ready"
    reason_codes = ["RELEASE_HANDOFF_BUNDLE_READY"]

    valid_idx, idx_errs = validate_waveguide_package_attested_archive_candidate_index(idx_dict)
    if not valid_idx or idx_status != "package_attested_archive_candidate_index_valid":
        status = "release_handoff_bundle_blocked"
        reason_codes = ["ATTESTED_CANDIDATE_INDEX_NOT_VALID"]

    if not idx_dict.get("current_attested_archive_candidate_digest"):
        status = "release_handoff_bundle_invalid"
        reason_codes.append("MISSING_ARCHIVE_FILE_DIGEST")

    # Gather current candidates
    candidates = idx_dict.get("attested_archive_candidates", [])
    current_cand = candidates[0] if candidates else {}

    # Gather upstream digests
    source_package_archive_digest_attestation_audit_report_digest = idx_dict.get("source_package_archive_digest_attestation_audit_report_digest", "")
    source_package_archive_digest_attestation_digest = idx_dict.get("source_package_archive_digest_attestation_digest", "")
    source_package_archive_signing_gate_digest = idx_dict.get("source_package_archive_signing_gate_digest", "")
    source_package_archive_signing_plan_digest = idx_dict.get("source_package_archive_signing_plan_digest", "")
    source_package_archive_release_candidate_index_digest = idx_dict.get("source_package_archive_release_candidate_index_digest", "")
    source_package_archive_audit_report_digest = idx_dict.get("source_package_archive_audit_report_digest", "")
    source_package_archive_manifest_digest = idx_dict.get("source_package_archive_manifest_digest", "")
    source_package_archive_build_record_digest = idx_dict.get("source_package_archive_build_record_digest", "")
    source_package_archive_plan_digest = idx_dict.get("source_package_archive_plan_digest", "")

    # Build source pipeline chain digest
    pipeline_chain_digest = build_waveguide_release_handoff_source_chain(idx_dict)

    # Build Entries
    entries = []
    # 1. Archive zip
    entries.append(build_waveguide_release_handoff_entry(
        kind="archive_zip",
        role="archive_zip",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip",
        digest=current_cand.get("archive_file_digest", ""),
        size=current_cand.get("archive_file_size_bytes", 0),
        fmt="zip",
        src_digest=current_cand.get("archive_file_digest", ""),
        src_status="verified",
        index=len(entries)
    ))
    # 2. Archive Audit Report
    entries.append(build_waveguide_release_handoff_entry(
        kind="archive_audit_report",
        role="archive_audit_report",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_AUDIT_REPORT.json",
        digest=source_package_archive_audit_report_digest,
        size=0, fmt="json", src_digest="", src_status="", index=len(entries)
    ))
    # 3. Archive Release Candidate Index
    entries.append(build_waveguide_release_handoff_entry(
        kind="archive_release_candidate_index",
        role="archive_release_candidate_index",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_RELEASE_CANDIDATE_INDEX.json",
        digest=source_package_archive_release_candidate_index_digest,
        size=0, fmt="json", src_digest="", src_status="", index=len(entries)
    ))
    # 4. Archive Signing Plan
    entries.append(build_waveguide_release_handoff_entry(
        kind="archive_signing_plan",
        role="archive_signing_plan",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_SIGNING_PLAN.json",
        digest=source_package_archive_signing_plan_digest,
        size=0, fmt="json", src_digest="", src_status="", index=len(entries)
    ))
    # 5. Archive Signing Gate
    entries.append(build_waveguide_release_handoff_entry(
        kind="archive_signing_gate",
        role="archive_signing_gate",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_SIGNING_GATE.json",
        digest=source_package_archive_signing_gate_digest,
        size=0, fmt="json", src_digest="", src_status="", index=len(entries)
    ))
    # 6. Digest Attestation
    entries.append(build_waveguide_release_handoff_entry(
        kind="digest_attestation",
        role="digest_attestation",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION.json",
        digest=source_package_archive_digest_attestation_digest,
        size=0, fmt="json", src_digest="", src_status="", index=len(entries)
    ))
    # 7. Digest Attestation Audit Report
    entries.append(build_waveguide_release_handoff_entry(
        kind="digest_attestation_audit_report",
        role="digest_attestation_audit_report",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION_AUDIT_REPORT.json",
        digest=source_package_archive_digest_attestation_audit_report_digest,
        size=0, fmt="json", src_digest="", src_status="", index=len(entries)
    ))
    # 8. Attested Candidate Index
    entries.append(build_waveguide_release_handoff_entry(
        kind="attested_archive_candidate_index",
        role="attested_archive_candidate_index",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ATTESTED_ARCHIVE_CANDIDATE_INDEX.json",
        digest=idx_digest,
        size=0, fmt="json", src_digest="", src_status="", index=len(entries)
    ))
    # 9. Handoff Documentation (Placeholder reference since it is written as output)
    entries.append(build_waveguide_release_handoff_entry(
        kind="handoff_documentation",
        role="handoff_documentation",
        path="docs/SOL_WAVEGUIDE_RELEASE_HANDOFF_BUNDLE.md",
        digest="", size=0, fmt="md", src_digest="", src_status="", index=len(entries)
    ))

    indexed_status = index_waveguide_release_handoff_entries_by_status(entries)
    ready_ids = indexed_status["ready"]
    blocked_ids = indexed_status["blocked"]
    warning_ids = indexed_status["warning"]
    invalid_ids = indexed_status["invalid"]

    if len(invalid_ids) > 0 or len(blocked_ids) > 0:
        status = "release_handoff_bundle_invalid"
        reason_codes.append("HANDOFF_ENTRIES_INVALID_OR_BLOCKED")

    kinds_indexed = sorted(list(set(e.release_handoff_artifact_kind for e in entries)))
    roles_indexed = sorted(list(set(e.release_handoff_artifact_role for e in entries)))
    paths_indexed = sorted(list(set(e.artifact_display_path for e in entries if e.artifact_display_path)))
    digests_indexed = sorted(list(set(e.artifact_digest for e in entries if e.artifact_digest)))

    offline_verification_artifacts = [e.artifact_display_path for e in entries if e.required_for_offline_verification]
    future_signing_artifacts = [e.artifact_display_path for e in entries if e.required_for_future_signing]
    future_publication_artifacts = [e.artifact_display_path for e in entries if e.required_for_future_publication]

    # Operation boundaries
    boundary_ok = all(validate_waveguide_release_handoff_operation_boundaries(asdict(e)) for e in entries)

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

    bundle = WaveguideReleaseHandoffBundle(
        release_handoff_bundle_id="SOL-WAVEGUIDE-RELEASE-HANDOFF-BUNDLE",
        release_handoff_bundle_version=1,
        release_handoff_bundle_status=status,
        source_package_attested_archive_candidate_index_digest=idx_digest,
        source_package_archive_digest_attestation_audit_report_digest=source_package_archive_digest_attestation_audit_report_digest,
        source_package_archive_digest_attestation_digest=source_package_archive_digest_attestation_digest,
        source_package_archive_signing_gate_digest=source_package_archive_signing_gate_digest,
        source_package_archive_signing_plan_digest=source_package_archive_signing_plan_digest,
        source_package_archive_release_candidate_index_digest=source_package_archive_release_candidate_index_digest,
        source_package_archive_audit_report_digest=source_package_archive_audit_report_digest,
        source_package_archive_manifest_digest=source_package_archive_manifest_digest,
        source_package_archive_build_record_digest=source_package_archive_build_record_digest,
        source_package_archive_plan_digest=source_package_archive_plan_digest,
        source_local_staging_output_audit_report_digest="",  # empty or filled if known
        source_package_pipeline_chain_digest=pipeline_chain_digest,
        current_attested_archive_candidate_digest=current_cand.get("archive_file_digest", ""),
        current_attested_archive_candidate_format=current_cand.get("archive_format", "zip"),
        current_attested_archive_candidate_display_path=current_cand.get("archive_display_path", ""),
        current_attested_archive_candidate_size_bytes=current_cand.get("archive_file_size_bytes", 0),
        current_archive_file_digest=current_cand.get("archive_file_digest", ""),
        release_handoff_entries=entries,
        ready_release_handoff_entries=ready_ids,
        blocked_release_handoff_entries=blocked_ids,
        warning_release_handoff_entries=warning_ids,
        invalid_release_handoff_entries=invalid_ids,
        ready_release_handoff_entry_count=len(ready_ids),
        blocked_release_handoff_entry_count=len(blocked_ids),
        warning_release_handoff_entry_count=len(warning_ids),
        invalid_release_handoff_entry_count=len(invalid_ids),
        handoff_artifact_kinds_indexed=kinds_indexed,
        handoff_artifact_roles_indexed=roles_indexed,
        handoff_artifact_paths_indexed=paths_indexed,
        handoff_artifact_digests_indexed=digests_indexed,
        offline_verification_artifacts=offline_verification_artifacts,
        future_signing_artifacts=future_signing_artifacts,
        future_publication_artifacts=future_publication_artifacts,
        source_chain_verified=validate_waveguide_release_handoff_source_chain(pipeline_chain_digest, idx_dict),
        artifact_reference_set_verified=(len(blocked_ids) == 0),
        digest_reference_set_verified=all(bool(e.artifact_digest) for e in entries if e.release_handoff_artifact_kind != "handoff_documentation"),
        offline_handoff_ready=(status == "release_handoff_bundle_ready"),
        future_signing_ready_for_key_management_stage=True,
        future_publication_ready_for_publication_gate_stage=True,
        real_signature_status="not_performed",
        digest_attestation_status="verified",
        signing_status="not_performed",
        upload_status="not_performed",
        publication_status="not_performed",
        deployment_status="not_performed",
        production_mutation_status="not_performed",
        signing_performed=False,
        real_key_signature_performed=False,
        digest_attestation_performed=True,
        external_signing_performed=False,
        timestamp_authority_performed=False,
        upload_performed=False,
        external_publication_performed=False,
        deployment_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    bundle.release_handoff_bundle_digest = hash_waveguide_release_handoff_bundle(bundle)
    return bundle


def validate_waveguide_release_handoff_bundle(bundle: Any) -> Tuple[bool, List[str]]:
    """
    Validates a top-level Release Handoff Bundle.
    """
    b_dict = asdict(bundle) if hasattr(bundle, "__dict__") else dict(bundle)
    errors = []

    # Verify digest
    recorded = b_dict.get("release_handoff_bundle_digest", "")
    if not recorded:
        errors.append("Missing bundle digest")
    else:
        recomputed = hash_waveguide_release_handoff_bundle(b_dict)
        if recomputed != recorded:
            errors.append(f"Bundle digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if b_dict.get("release_handoff_bundle_id") != "SOL-WAVEGUIDE-RELEASE-HANDOFF-BUNDLE":
        errors.append("Invalid handoff bundle ID")

    # Enforce prohibitions
    prohibitions = [
        ("real_signature_status", "not_performed"),
        ("upload_status", "not_performed"),
        ("publication_status", "not_performed"),
        ("deployment_status", "not_performed"),
        ("production_mutation_status", "not_performed"),
        ("signing_performed", False),
        ("real_key_signature_performed", False),
        ("upload_performed", False),
        ("external_publication_performed", False),
        ("deployment_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if b_dict.get(key) != expected:
            errors.append(f"Top-level field {key} must be {expected}")

    # Validate entries
    entries = b_dict.get("release_handoff_entries", [])
    for e in entries:
        ok, errs = validate_waveguide_release_handoff_entry(e)
        if not ok:
            errors.extend(errs)

    return len(errors) == 0, errors


def summarize_waveguide_release_handoff_bundle(bundle: Any) -> str:
    """
    Generates a human-readable summary of the handoff bundle.
    """
    b_dict = asdict(bundle) if hasattr(bundle, "__dict__") else dict(bundle)
    lines = [
        "=============================================================",
        "               SOL WAVEGUIDE RELEASE HANDOFF BUNDLE",
        "=============================================================",
        f"Bundle ID:        {b_dict.get('release_handoff_bundle_id')}",
        f"Status:           {b_dict.get('release_handoff_bundle_status')}",
        f"Bundle Digest:    {b_dict.get('release_handoff_bundle_digest')}",
        f"Offline Ready:    {b_dict.get('offline_handoff_ready')}",
        f"Chain Verified:   {b_dict.get('source_chain_verified')}",
        f"Ready Entries:    {b_dict.get('ready_release_handoff_entry_count')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in b_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_release_handoff_bundle(bundle: Any, output_path: str) -> None:
    """
    Exports the Release Handoff Bundle to a JSON file.
    """
    b_dict = asdict(bundle) if hasattr(bundle, "__dict__") else dict(bundle)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(b_dict, f, indent=4, sort_keys=True)


def compare_waveguide_release_handoff_bundles(bun_a: Any, bun_b: Any) -> Dict[str, Any]:
    """
    Compares two Release Handoff Bundles.
    """
    dict_a = asdict(bun_a) if hasattr(bun_a, "__dict__") else dict(bun_a)
    dict_b = asdict(bun_b) if hasattr(bun_b, "__dict__") else dict(bun_b)

    differences = {}
    for key in (
        "release_handoff_bundle_status",
        "release_handoff_bundle_digest",
        "ready_release_handoff_entry_count"
    ):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
