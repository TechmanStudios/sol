# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Distribution Package Manifest Validator / Final Package Readiness Auditor.
Validates the Distribution Package Manifest and Package Dry-Run Report strictly as metadata.
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
from sol_waveguide_package_assembly_plan_validator import (
    validate_waveguide_package_dry_run_report,
    validate_waveguide_package_target_path_safety
)
from sol_waveguide_distribution_package_manifest import (
    validate_waveguide_distribution_package_manifest,
    hash_waveguide_distribution_package_content_entry,
    hash_waveguide_distribution_package_manifest
)


@dataclass
class WaveguideFinalPackageReadinessAuditCase:
    final_package_audit_case_id: str
    distribution_package_manifest_id: str
    distribution_package_manifest_path: str
    distribution_package_manifest_digest_recorded: str
    distribution_package_manifest_digest_recomputed: str
    distribution_package_manifest_digest_match: bool
    package_content_entry_id: str
    package_content_entry_digest_recorded: str
    package_content_entry_digest_recomputed: str
    package_content_entry_digest_match: bool
    source_artifact_path: str
    source_artifact_name: str
    source_artifact_digest: str
    source_artifact_type: str
    source_artifact_format: str
    source_package_role: str
    rc_scope: str
    candidate_level: str
    target_package_path: str
    target_package_section: str
    dry_run_case_digest: str
    layout_entry_digest: str
    include_in_package_manifest: bool
    manifest_entry_status: str
    final_package_readiness_status: str  # final_package_content_verified, etc.
    source_dry_run_audit_report_digest_recorded: str
    source_dry_run_audit_report_digest_recomputed: str
    source_dry_run_audit_report_digest_match: bool
    source_dry_run_audit_report_valid: bool
    source_dry_run_case_verified: bool
    target_path_safe: bool
    source_digest_preserved: bool
    dry_run_case_digest_preserved: bool
    layout_entry_digest_preserved: bool
    package_digest_map_referenced: bool
    package_layout_referenced: bool
    section_manifest_referenced: bool
    blocked_operations_zero: bool
    no_archive_created: bool
    no_file_copy_performed: bool
    no_directory_created: bool
    no_upload_performed: bool
    no_deployment_performed: bool
    no_signing_performed: bool
    no_external_publication_performed: bool
    no_production_mutation_performed: bool
    allowed_distribution_channels: List[str]
    blocked_distribution_channels: List[str]
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    final_package_audit_case_digest: str = ""

    @property
    def is_proof_artifact(self) -> bool:
        return self.target_package_section == "proof/"

    @property
    def is_documentation_artifact(self) -> bool:
        return self.target_package_section == "docs/"

    @property
    def is_test_artifact(self) -> bool:
        return self.target_package_section == "tests/" or self.source_package_role == "test_source" or self.source_artifact_type == "pytest_suite"

    @property
    def is_code_artifact(self) -> bool:
        return self.target_package_section == "source/" or self.source_package_role == "implementation_source"


@dataclass
class WaveguideFinalPackageReadinessAuditReport:
    final_package_readiness_report_id: str
    final_package_readiness_report_version: int
    final_package_readiness_report_status: str  # final_package_readiness_verified, etc.
    source_distribution_package_manifest_digest: str
    source_dry_run_audit_report_digest: str
    source_package_assembly_plan_digest: str
    source_artifact_catalog_digest: str
    audited_cases: List[WaveguideFinalPackageReadinessAuditCase]
    verified_final_package_cases: List[str]
    blocked_final_package_cases: List[str]
    pending_final_package_cases: List[str]
    invalid_final_package_cases: List[str]
    verified_final_package_count: int
    blocked_final_package_count: int
    pending_final_package_count: int
    invalid_final_package_count: int
    total_final_package_file_count: int
    rc1_final_package_count: int
    rc2_final_package_count: int
    shared_final_package_count: int
    target_package_sections: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    artifact_formats_indexed: List[str]
    source_artifact_paths: List[str]
    target_package_paths: List[str]
    source_artifact_digests: List[str]
    layout_entry_digests: List[str]
    dry_run_case_digests: List[str]
    package_content_entry_digests: List[str]
    final_package_audit_case_digests: List[str]
    package_digest_map_verified: bool
    package_layout_verified: bool
    proof_artifact_manifest_verified: bool
    documentation_artifact_manifest_verified: bool
    source_artifact_manifest_verified: bool
    test_artifact_manifest_verified: bool
    blocked_operations_verified: bool
    blocked_operation_attempt_counts: Dict[str, int]
    archive_creation_attempt_count: int
    file_copy_attempt_count: int
    directory_creation_attempt_count: int
    upload_attempt_count: int
    deployment_attempt_count: int
    signing_attempt_count: int
    external_publication_attempt_count: int
    production_mutation_attempt_count: int
    allowed_distribution_channels: List[str]
    blocked_distribution_channels: List[str]
    reason_codes: List[str]
    software_validation_caveat: str
    final_package_readiness_report_digest: str = ""


def hash_waveguide_final_package_readiness_audit_case(case: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of case excluding the self-referential field.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    elif isinstance(case, dict):
        c_dict = dict(case)
    else:
        raise TypeError("case must be a dictionary or a dataclass instance")

    c_dict_copy = dict(c_dict)
    c_dict_copy.pop("final_package_audit_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_final_package_readiness_audit_report(report: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of report excluding the self-referential field.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    r_dict_copy = dict(r_dict)
    r_dict_copy.pop("final_package_readiness_report_digest", None)
    return hash_data(r_dict_copy)


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


def recompute_waveguide_distribution_package_manifest_digest(manifest_path_or_dict: Any) -> str:
    """
    Recomputes top-level manifest digest.
    """
    manifest_dict = _load_dict(manifest_path_or_dict)
    if manifest_dict:
        return hash_waveguide_distribution_package_manifest(manifest_dict)
    return ""


def recompute_waveguide_package_content_entry_digest(entry: Any) -> str:
    """
    Recomputes package content entry digest.
    """
    return hash_waveguide_distribution_package_content_entry(entry)


def validate_waveguide_package_manifest_digest_map(digest_map: List[Dict[str, Any]], entries: List[Any]) -> bool:
    """
    Verifies the manifest package_digest_map corresponds exactly to ready content entries, sorted by target package path.
    """
    ready_entries = []
    for e in entries:
        e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
        if e_dict.get("manifest_entry_status") == "package_content_ready":
            ready_entries.append(e_dict)

    sorted_ready = sorted(ready_entries, key=lambda x: x.get("target_package_path", ""))
    if len(digest_map) != len(sorted_ready):
        return False

    for idx, e_dict in enumerate(sorted_ready):
        map_entry = digest_map[idx]
        if (map_entry.get("target_package_path") != e_dict.get("target_package_path") or
            map_entry.get("artifact_digest") != e_dict.get("source_artifact_digest") or
            map_entry.get("source_artifact_path") != e_dict.get("source_artifact_path")):
            return False
        if map_entry.get("digest_map_index") != idx + 1:
            return False

    return True


def validate_waveguide_package_manifest_layout(layout: Dict[str, List[str]], entries: List[Any]) -> bool:
    """
    Verifies that layout lists match ready content entries.
    """
    sections = {}
    for e in entries:
        e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
        if e_dict.get("manifest_entry_status") == "package_content_ready":
            sect = e_dict.get("target_package_section")
            if sect not in sections:
                sections[sect] = []
            sections[sect].append(e_dict.get("target_package_path"))

    for sect, paths in sections.items():
        if sect not in layout:
            return False
        if layout[sect] != sorted(paths):
            return False

    for sect in layout:
        if sect not in sections and len(layout[sect]) > 0:
            return False

    return True


def validate_waveguide_package_section_manifests(manifest_dict: Dict[str, Any], entries: List[Any]) -> bool:
    """
    Verifies a section-specific manifest (e.g. proof_artifact_manifest) matches ready content entries.
    """
    sect_name = manifest_dict.get("section_name")
    target_paths = manifest_dict.get("target_paths", [])
    artifact_digests = manifest_dict.get("artifact_digests", [])
    content_entry_digests = manifest_dict.get("content_entry_digests", [])
    entry_count = manifest_dict.get("entry_count", 0)

    expected_paths = []
    expected_digests = []
    expected_entry_digests = []

    for e in entries:
        e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
        if e_dict.get("target_package_section") == sect_name and e_dict.get("manifest_entry_status") == "package_content_ready":
            expected_paths.append(e_dict.get("target_package_path"))
            expected_digests.append(e_dict.get("source_artifact_digest"))
            expected_entry_digests.append(e_dict.get("package_content_entry_digest"))

    if entry_count != len(expected_paths):
        return False
    if target_paths != sorted(expected_paths):
        return False
    if artifact_digests != sorted(expected_digests):
        return False
    if content_entry_digests != sorted(expected_entry_digests):
        return False

    return True


def validate_waveguide_blocked_operation_counters(blocked_ops: Dict[str, int]) -> bool:
    """
    Verifies that all blocked operations counters are zero.
    """
    expected_ops = [
        "archive_creation", "file_copy", "directory_creation",
        "upload", "deployment", "external_signing",
        "external_publication", "production_mutation"
    ]
    for op in expected_ops:
        if blocked_ops.get(op, -1) != 0:
            return False
    return True


def build_waveguide_final_package_readiness_audit_case(
    content_entry: Any,
    manifest_path_or_dict: Any,
    report_path_or_dict: Any
) -> WaveguideFinalPackageReadinessAuditCase:
    """
    Builds a final package-readiness audit case validating a content entry.
    """
    e_dict = asdict(content_entry) if hasattr(content_entry, "__dict__") else dict(content_entry)
    m_dict = _load_dict(manifest_path_or_dict) or {}
    r_dict = _load_dict(report_path_or_dict) or {}

    manifest_path = manifest_path_or_dict if isinstance(manifest_path_or_dict, str) else ""

    # Manifest digest checks
    manifest_digest_recorded = m_dict.get("distribution_package_manifest_digest", "")
    manifest_digest_recomputed = recompute_waveguide_distribution_package_manifest_digest(m_dict)
    manifest_digest_match = (manifest_digest_recorded == manifest_digest_recomputed) and (manifest_digest_recorded != "")

    # Content entry digest checks
    entry_digest_recorded = e_dict.get("package_content_entry_digest", "")
    entry_digest_recomputed = recompute_waveguide_package_content_entry_digest(e_dict)
    entry_digest_match = (entry_digest_recorded == entry_digest_recomputed) and (entry_digest_recorded != "")

    # Dry-run report digest checks
    report_digest_recorded = m_dict.get("source_dry_run_audit_report_digest", "")
    report_digest_recomputed = r_dict.get("package_dry_run_report_digest", "")
    report_digest_match = (report_digest_recorded == report_digest_recomputed) and (report_digest_recorded != "")

    # Validate dry-run report
    report_valid = False
    if r_dict:
        report_valid, _ = validate_waveguide_package_dry_run_report(r_dict)

    # Lookup dry-run case
    source_path = e_dict.get("source_artifact_path", "")
    tpath = e_dict.get("target_package_path", "")
    section = e_dict.get("target_package_section", "")
    layout_entry_digest = e_dict.get("layout_entry_digest", "")
    layout_entry_digest_preserved = bool(layout_entry_digest)


    audited_cases = r_dict.get("audited_cases", [])
    matching_case = next((c for c in audited_cases if c.get("source_artifact_path") == source_path), None)

    dry_run_case_verified = False
    dry_run_case_digest_preserved = False
    source_digest_preserved = False

    if matching_case:
        dry_run_case_verified = (matching_case.get("dry_run_status") == "package_dry_run_verified")
        dry_run_case_digest_preserved = (e_dict.get("dry_run_case_digest") == matching_case.get("package_dry_run_case_digest"))
        source_digest_preserved = (e_dict.get("source_artifact_digest") == matching_case.get("source_artifact_digest"))

    # Path safety
    target_path_safe, _ = validate_waveguide_package_target_path_safety(tpath)

    # Structure checks
    entries = m_dict.get("package_contents", [])
    package_digest_map_referenced = any(
        item.get("target_package_path") == tpath and item.get("artifact_digest") == e_dict.get("source_artifact_digest")
        for item in m_dict.get("package_digest_map", [])
    )
    package_layout_referenced = tpath in m_dict.get("package_layout", {}).get(section, [])
    
    # Section manifest check
    sect_manifest = {}
    if section == "proof/":
        sect_manifest = m_dict.get("proof_artifact_manifest", {})
    elif section == "docs/":
        sect_manifest = m_dict.get("documentation_artifact_manifest", {})
    elif section == "source/":
        sect_manifest = m_dict.get("source_artifact_manifest", {})
    elif section == "tests/":
        sect_manifest = m_dict.get("test_artifact_manifest", {})
    
    section_manifest_referenced = tpath in sect_manifest.get("target_paths", [])

    # Blocked operations
    blocked_ops = m_dict.get("blocked_operations", {})
    blocked_operations_zero = validate_waveguide_blocked_operation_counters(blocked_ops)

    no_archive = True
    no_copy = True
    no_dir = True
    no_upload = True
    no_deploy = True
    no_sign = True
    no_pub = True
    no_mutate = True

    reason_codes = [
        "FINAL_PACKAGE_AUDIT_CASE_CANONICAL",
        "FINAL_PACKAGE_NO_ARCHIVE_CREATED",
        "FINAL_PACKAGE_NO_FILE_COPY_PERFORMED",
        "FINAL_PACKAGE_NO_DIRECTORY_CREATED",
        "FINAL_PACKAGE_NO_UPLOAD_PERFORMED",
        "FINAL_PACKAGE_NO_DEPLOYMENT_PERFORMED",
        "FINAL_PACKAGE_NO_SIGNING_PERFORMED",
        "FINAL_PACKAGE_NO_PUBLICATION_PERFORMED",
        "FINAL_PACKAGE_NO_PRODUCTION_MUTATION"
    ]

    if m_dict:
        reason_codes.append("FINAL_PACKAGE_MANIFEST_LOADED")
    if manifest_digest_match:
        reason_codes.append("FINAL_PACKAGE_MANIFEST_DIGEST_MATCH")
    else:
        reason_codes.append("FINAL_PACKAGE_MANIFEST_DIGEST_MISMATCH")

    if entry_digest_match:
        reason_codes.append("FINAL_PACKAGE_CONTENT_ENTRY_DIGEST_MATCH")
    else:
        reason_codes.append("FINAL_PACKAGE_CONTENT_ENTRY_DIGEST_MISMATCH")

    if report_valid:
        reason_codes.append("FINAL_PACKAGE_SOURCE_DRY_RUN_REPORT_VALID")
    else:
        reason_codes.append("FINAL_PACKAGE_SOURCE_DRY_RUN_REPORT_INVALID")

    if report_digest_match:
        reason_codes.append("FINAL_PACKAGE_SOURCE_DRY_RUN_REPORT_DIGEST_MATCH")
    else:
        reason_codes.append("FINAL_PACKAGE_SOURCE_DRY_RUN_REPORT_DIGEST_MISMATCH")

    if dry_run_case_verified:
        reason_codes.append("FINAL_PACKAGE_DRY_RUN_CASE_VERIFIED")
    if target_path_safe:
        reason_codes.append("FINAL_PACKAGE_TARGET_PATH_SAFE")
    if source_digest_preserved:
        reason_codes.append("FINAL_PACKAGE_SOURCE_DIGEST_PRESERVED")
    if dry_run_case_digest_preserved:
        reason_codes.append("FINAL_PACKAGE_DRY_RUN_CASE_DIGEST_PRESERVED")
    if e_dict.get("layout_entry_digest"):
        reason_codes.append("FINAL_PACKAGE_LAYOUT_ENTRY_DIGEST_PRESERVED")

    if package_digest_map_referenced:
        reason_codes.append("FINAL_PACKAGE_DIGEST_MAP_VERIFIED")
    if package_layout_referenced:
        reason_codes.append("FINAL_PACKAGE_LAYOUT_VERIFIED")

    if section == "proof/" and section_manifest_referenced:
        reason_codes.append("FINAL_PACKAGE_PROOF_SECTION_VERIFIED")
    elif section == "docs/" and section_manifest_referenced:
        reason_codes.append("FINAL_PACKAGE_DOCUMENTATION_SECTION_VERIFIED")
    elif section == "source/" and section_manifest_referenced:
        reason_codes.append("FINAL_PACKAGE_SOURCE_SECTION_VERIFIED")
    elif section == "tests/" and section_manifest_referenced:
        reason_codes.append("FINAL_PACKAGE_TEST_SECTION_VERIFIED")

    if blocked_operations_zero:
        reason_codes.append("FINAL_PACKAGE_BLOCKED_OPERATIONS_VERIFIED")

    caveat = e_dict.get("software_validation_caveat", "")
    if caveat:
        reason_codes.append("FINAL_PACKAGE_SOFTWARE_CAVEAT_INCLUDED")

    manifest_status = m_dict.get("distribution_package_manifest_status", "")
    entry_status = e_dict.get("manifest_entry_status", "")
    include_in_manifest = e_dict.get("include_in_package_manifest", False)
    is_deploy = e_dict.get("is_deployment_artifact", False)
    is_sign = e_dict.get("is_signing_artifact", False)

    final_package_readiness_status = "final_package_content_invalid"
    if (manifest_digest_match and entry_digest_match and report_digest_match and report_valid and
        dry_run_case_verified and target_path_safe and source_digest_preserved and
        dry_run_case_digest_preserved and layout_entry_digest_preserved and package_digest_map_referenced and
        package_layout_referenced and section_manifest_referenced and blocked_operations_zero and
        not is_deploy and not is_sign and caveat):
        if entry_status == "package_content_ready" and include_in_manifest:
            final_package_readiness_status = "final_package_content_verified"
            reason_codes.append("FINAL_PACKAGE_READINESS_VERIFIED")
        elif entry_status == "package_content_blocked":
            final_package_readiness_status = "final_package_content_blocked"
            reason_codes.append("FINAL_PACKAGE_READINESS_BLOCKED")
        elif entry_status == "package_content_pending":
            final_package_readiness_status = "final_package_content_pending"
        else:
            final_package_readiness_status = "final_package_content_invalid"
            reason_codes.append("FINAL_PACKAGE_READINESS_INVALID")
    else:
        final_package_readiness_status = "final_package_content_invalid"
        reason_codes.append("FINAL_PACKAGE_READINESS_INVALID")

    case_obj = WaveguideFinalPackageReadinessAuditCase(
        final_package_audit_case_id=f"SOL-WAVEGUIDE-FINAL-AUDIT-{e_dict.get('source_artifact_name', '').replace('.', '_')}",
        distribution_package_manifest_id=m_dict.get("distribution_package_manifest_id", ""),
        distribution_package_manifest_path=manifest_path,
        distribution_package_manifest_digest_recorded=manifest_digest_recorded,
        distribution_package_manifest_digest_recomputed=manifest_digest_recomputed,
        distribution_package_manifest_digest_match=manifest_digest_match,
        package_content_entry_id=e_dict.get("package_content_entry_id", ""),
        package_content_entry_digest_recorded=entry_digest_recorded,
        package_content_entry_digest_recomputed=entry_digest_recomputed,
        package_content_entry_digest_match=entry_digest_match,
        source_artifact_path=source_path,
        source_artifact_name=e_dict.get("source_artifact_name", ""),
        source_artifact_digest=e_dict.get("source_artifact_digest", ""),
        source_artifact_type=e_dict.get("source_artifact_type", ""),
        source_artifact_format=e_dict.get("source_artifact_format", ""),
        source_package_role=e_dict.get("source_package_role", ""),
        rc_scope=e_dict.get("rc_scope", ""),
        candidate_level=e_dict.get("candidate_level", ""),
        target_package_path=tpath,
        target_package_section=section,
        dry_run_case_digest=e_dict.get("dry_run_case_digest", ""),
        layout_entry_digest=layout_entry_digest,
        include_in_package_manifest=include_in_manifest,
        manifest_entry_status=entry_status,
        final_package_readiness_status=final_package_readiness_status,
        source_dry_run_audit_report_digest_recorded=report_digest_recorded,
        source_dry_run_audit_report_digest_recomputed=report_digest_recomputed,
        source_dry_run_audit_report_digest_match=report_digest_match,
        source_dry_run_audit_report_valid=report_valid,
        source_dry_run_case_verified=dry_run_case_verified,
        target_path_safe=target_path_safe,
        source_digest_preserved=source_digest_preserved,
        dry_run_case_digest_preserved=dry_run_case_digest_preserved,
        layout_entry_digest_preserved=layout_entry_digest_preserved,
        package_digest_map_referenced=package_digest_map_referenced,
        package_layout_referenced=package_layout_referenced,
        section_manifest_referenced=section_manifest_referenced,
        blocked_operations_zero=blocked_operations_zero,
        no_archive_created=no_archive,
        no_file_copy_performed=no_copy,
        no_directory_created=no_dir,
        no_upload_performed=no_upload,
        no_deployment_performed=no_deploy,
        no_signing_performed=no_sign,
        no_external_publication_performed=no_pub,
        no_production_mutation_performed=no_mutate,
        allowed_distribution_channels=sorted(e_dict.get("allowed_distribution_channels", [])),
        blocked_distribution_channels=sorted(e_dict.get("blocked_distribution_channels", [])),
        reason_codes=sorted(list(set(reason_codes))),
        notes=[],
        software_validation_caveat=caveat,
        final_package_audit_case_digest=""
    )
    case_obj.final_package_audit_case_digest = hash_waveguide_final_package_readiness_audit_case(case_obj)
    return case_obj


def validate_waveguide_distribution_package_manifest_independently(
    manifest_path_or_dict: Any,
    report_path_or_dict: Any
) -> Tuple[bool, List[str]]:
    """
    Independently validates the manifest and verifies that report digest matches.
    """
    manifest_dict = _load_dict(manifest_path_or_dict)
    report_dict = _load_dict(report_path_or_dict)

    reasons = []
    is_valid = True

    if not manifest_dict or not report_dict:
        return False, ["FINAL_PACKAGE_READINESS_INVALID"]

    # Validate manifest
    m_ok, m_reasons = validate_waveguide_distribution_package_manifest(manifest_dict)
    if not m_ok:
        is_valid = False
        reasons.append("FINAL_PACKAGE_MANIFEST_INVALID")
    else:
        reasons.append("FINAL_PACKAGE_MANIFEST_VALID")

    # Validate report
    r_ok, r_reasons = validate_waveguide_package_dry_run_report(report_dict)
    if not r_ok:
        is_valid = False
        reasons.append("FINAL_PACKAGE_SOURCE_DRY_RUN_REPORT_INVALID")
    else:
        reasons.append("FINAL_PACKAGE_SOURCE_DRY_RUN_REPORT_VALID")

    # Digest match check
    m_report_digest = manifest_dict.get("source_dry_run_audit_report_digest", "")
    r_digest = report_dict.get("package_dry_run_report_digest", "")
    if m_report_digest != r_digest or not r_digest:
        is_valid = False
        reasons.append("FINAL_PACKAGE_SOURCE_DRY_RUN_REPORT_DIGEST_MISMATCH")
    else:
        reasons.append("FINAL_PACKAGE_SOURCE_DRY_RUN_REPORT_DIGEST_MATCH")

    if is_valid:
        reasons.append("FINAL_PACKAGE_READINESS_VERIFIED")
    else:
        reasons.append("FINAL_PACKAGE_READINESS_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_final_package_readiness_audit_report(
    manifest_path_or_dict: Any,
    report_path_or_dict: Any
) -> WaveguideFinalPackageReadinessAuditReport:
    """
    Builds the top-level final package readiness report.
    """
    manifest_dict = _load_dict(manifest_path_or_dict)
    report_dict = _load_dict(report_path_or_dict)

    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not manifest_dict or not report_dict:
        report = WaveguideFinalPackageReadinessAuditReport(
            final_package_readiness_report_id="SOL-WAVEGUIDE-FINAL-PACKAGE-READINESS-AUDIT-REPORT",
            final_package_readiness_report_version=1,
            final_package_readiness_report_status="final_package_readiness_invalid",
            source_distribution_package_manifest_digest="",
            source_dry_run_audit_report_digest="",
            source_package_assembly_plan_digest="",
            source_artifact_catalog_digest="",
            audited_cases=[],
            verified_final_package_cases=[],
            blocked_final_package_cases=[],
            pending_final_package_cases=[],
            invalid_final_package_cases=[],
            verified_final_package_count=0,
            blocked_final_package_count=0,
            pending_final_package_count=0,
            invalid_final_package_count=0,
            total_final_package_file_count=0,
            rc1_final_package_count=0,
            rc2_final_package_count=0,
            shared_final_package_count=0,
            target_package_sections=[],
            package_roles_indexed=[],
            artifact_types_indexed=[],
            artifact_formats_indexed=[],
            source_artifact_paths=[],
            target_package_paths=[],
            source_artifact_digests=[],
            layout_entry_digests=[],
            dry_run_case_digests=[],
            package_content_entry_digests=[],
            final_package_audit_case_digests=[],
            package_digest_map_verified=False,
            package_layout_verified=False,
            proof_artifact_manifest_verified=False,
            documentation_artifact_manifest_verified=False,
            source_artifact_manifest_verified=False,
            test_artifact_manifest_verified=False,
            blocked_operations_verified=False,
            blocked_operation_attempt_counts={
                "archive_creation": 0, "file_copy": 0, "directory_creation": 0,
                "upload": 0, "deployment": 0, "external_signing": 0,
                "external_publication": 0, "production_mutation": 0
            },
            archive_creation_attempt_count=0,
            file_copy_attempt_count=0,
            directory_creation_attempt_count=0,
            upload_attempt_count=0,
            deployment_attempt_count=0,
            signing_attempt_count=0,
            external_publication_attempt_count=0,
            production_mutation_attempt_count=0,
            allowed_distribution_channels=[],
            blocked_distribution_channels=[],
            reason_codes=["FINAL_PACKAGE_READINESS_INVALID", "FINAL_PACKAGE_MANIFEST_INVALID"],
            software_validation_caveat=caveat,
            final_package_readiness_report_digest=""
        )
        report.final_package_readiness_report_digest = hash_waveguide_final_package_readiness_audit_report(report)
        return report

    manifest_digest = manifest_dict.get("distribution_package_manifest_digest", "")
    report_digest = report_dict.get("package_dry_run_report_digest", "")
    plan_digest = manifest_dict.get("source_package_assembly_plan_digest", "")
    catalog_digest = manifest_dict.get("source_artifact_catalog_digest", "")

    content_entries = manifest_dict.get("package_contents", [])
    cases = []
    for entry in content_entries:
        case = build_waveguide_final_package_readiness_audit_case(entry, manifest_dict, report_dict)
        cases.append(case)

    # Sort cases by target_package_path, source_artifact_path, source_artifact_digest
    def case_sort_key(c):
        return (c.target_package_path, c.source_artifact_path, c.source_artifact_digest)
    
    sorted_cases = sorted(cases, key=case_sort_key)

    verified_final_package_cases = []
    blocked_final_package_cases = []
    pending_final_package_cases = []
    invalid_final_package_cases = []

    rc1_final_package_count = 0
    rc2_final_package_count = 0
    shared_final_package_count = 0

    target_package_sections = []
    package_roles_indexed = []
    artifact_types_indexed = []
    artifact_formats_indexed = []
    source_artifact_paths = []
    target_package_paths = []
    source_artifact_digests = []
    layout_entry_digests = []
    dry_run_case_digests = []
    package_content_entry_digests = []
    final_package_audit_case_digests = []

    all_reasons = [
        "FINAL_PACKAGE_COUNTS_VALID",
        "FINAL_PACKAGE_INDEXES_VALID",
        "FINAL_PACKAGE_NO_ARCHIVE_CREATED",
        "FINAL_PACKAGE_NO_FILE_COPY_PERFORMED",
        "FINAL_PACKAGE_NO_DIRECTORY_CREATED",
        "FINAL_PACKAGE_NO_UPLOAD_PERFORMED",
        "FINAL_PACKAGE_NO_DEPLOYMENT_PERFORMED",
        "FINAL_PACKAGE_NO_SIGNING_PERFORMED",
        "FINAL_PACKAGE_NO_PUBLICATION_PERFORMED",
        "FINAL_PACKAGE_NO_PRODUCTION_MUTATION"
    ]

    for case in sorted_cases:
        path = case.source_artifact_path
        tpath = case.target_package_path
        sect = case.target_package_section
        status = case.final_package_readiness_status
        scope = case.rc_scope
        role = case.source_package_role
        atype = case.source_artifact_type
        aformat = case.source_artifact_format
        digest = case.source_artifact_digest
        layout_dig = case.layout_entry_digest
        c_digest = case.dry_run_case_digest
        e_digest = case.package_content_entry_digest_recorded
        case_dig = case.final_package_audit_case_digest

        def add_unique(lst, val):
            if val and val not in lst:
                lst.append(val)

        add_unique(target_package_sections, sect)
        add_unique(package_roles_indexed, role)
        add_unique(artifact_types_indexed, atype)
        add_unique(artifact_formats_indexed, aformat)
        add_unique(source_artifact_paths, path)
        add_unique(target_package_paths, tpath)
        add_unique(source_artifact_digests, digest)
        add_unique(layout_entry_digests, layout_dig)
        add_unique(dry_run_case_digests, c_digest)
        add_unique(package_content_entry_digests, e_digest)
        add_unique(final_package_audit_case_digests, case_dig)

        if status == "final_package_content_verified":
            add_unique(verified_final_package_cases, path)
        elif status == "final_package_content_blocked":
            add_unique(blocked_final_package_cases, path)
        elif status == "final_package_content_pending":
            add_unique(pending_final_package_cases, path)
        else:
            add_unique(invalid_final_package_cases, path)

        if scope == "RC1":
            rc1_final_package_count += 1
        elif scope == "RC2":
            rc2_final_package_count += 1
        else:
            shared_final_package_count += 1

        for code in case.reason_codes:
            if code not in all_reasons:
                all_reasons.append(code)

    # Sort lists
    target_package_sections = sorted(target_package_sections)
    package_roles_indexed = sorted(package_roles_indexed)
    artifact_types_indexed = sorted(artifact_types_indexed)
    artifact_formats_indexed = sorted(artifact_formats_indexed)
    source_artifact_paths = sorted(source_artifact_paths)
    target_package_paths = sorted(target_package_paths)
    source_artifact_digests = sorted(source_artifact_digests)
    layout_entry_digests = sorted(layout_entry_digests)
    dry_run_case_digests = sorted(dry_run_case_digests)
    package_content_entry_digests = sorted(package_content_entry_digests)
    final_package_audit_case_digests = sorted(final_package_audit_case_digests)

    # Manifest structures verification
    package_digest_map_verified = validate_waveguide_package_manifest_digest_map(manifest_dict.get("package_digest_map", []), content_entries)
    package_layout_verified = validate_waveguide_package_manifest_layout(manifest_dict.get("package_layout", {}), content_entries)
    proof_verified = validate_waveguide_package_section_manifests(manifest_dict.get("proof_artifact_manifest", {}), content_entries)
    docs_verified = validate_waveguide_package_section_manifests(manifest_dict.get("documentation_artifact_manifest", {}), content_entries)
    src_verified = validate_waveguide_package_section_manifests(manifest_dict.get("source_artifact_manifest", {}), content_entries)
    test_verified = validate_waveguide_package_section_manifests(manifest_dict.get("test_artifact_manifest", {}), content_entries)

    blocked_ops = manifest_dict.get("blocked_operations", {})
    blocked_operations_verified = validate_waveguide_blocked_operation_counters(blocked_ops)

    if package_digest_map_verified:
        all_reasons.append("FINAL_PACKAGE_DIGEST_MAP_VERIFIED")
    if package_layout_verified:
        all_reasons.append("FINAL_PACKAGE_LAYOUT_VERIFIED")
    if proof_verified:
        all_reasons.append("FINAL_PACKAGE_PROOF_SECTION_VERIFIED")
    if docs_verified:
        all_reasons.append("FINAL_PACKAGE_DOCUMENTATION_SECTION_VERIFIED")
    if src_verified:
        all_reasons.append("FINAL_PACKAGE_SOURCE_SECTION_VERIFIED")
    if test_verified:
        all_reasons.append("FINAL_PACKAGE_TEST_SECTION_VERIFIED")
    if blocked_operations_verified:
        all_reasons.append("FINAL_PACKAGE_BLOCKED_OPERATIONS_VERIFIED")

    allowed_channels = [
        "artifact_catalog_publication",
        "documentation_publication",
        "internal_distribution"
    ]
    blocked_channels = [
        "external_key_signing",
        "legal_certification_claim",
        "production_deployment",
        "quantum_hardware_certification"
    ]

    verified_count = len(verified_final_package_cases)
    blocked_count = len(blocked_final_package_cases)
    pending_count = len(pending_final_package_cases)
    invalid_count = len(invalid_final_package_cases)

    # Determine status
    ind_ok, ind_reasons = validate_waveguide_distribution_package_manifest_independently(manifest_dict, report_dict)
    if (blocked_count > 0 or invalid_count > 0 or not ind_ok or
        not package_digest_map_verified or not package_layout_verified or
        not proof_verified or not docs_verified or not src_verified or not test_verified or
        not blocked_operations_verified):
        report_status = "final_package_readiness_invalid"
        all_reasons.append("FINAL_PACKAGE_READINESS_INVALID")
    else:
        report_status = "final_package_readiness_verified"
        all_reasons.append("FINAL_PACKAGE_READINESS_VERIFIED")

    report = WaveguideFinalPackageReadinessAuditReport(
        final_package_readiness_report_id="SOL-WAVEGUIDE-FINAL-PACKAGE-READINESS-AUDIT-REPORT",
        final_package_readiness_report_version=1,
        final_package_readiness_report_status=report_status,
        source_distribution_package_manifest_digest=manifest_digest,
        source_dry_run_audit_report_digest=report_digest,
        source_package_assembly_plan_digest=plan_digest,
        source_artifact_catalog_digest=catalog_digest,
        audited_cases=sorted_cases,
        verified_final_package_cases=sorted(verified_final_package_cases),
        blocked_final_package_cases=sorted(blocked_final_package_cases),
        pending_final_package_cases=sorted(pending_final_package_cases),
        invalid_final_package_cases=sorted(invalid_final_package_cases),
        verified_final_package_count=verified_count,
        blocked_final_package_count=blocked_count,
        pending_final_package_count=pending_count,
        invalid_final_package_count=invalid_count,
        total_final_package_file_count=verified_count,
        rc1_final_package_count=rc1_final_package_count,
        rc2_final_package_count=rc2_final_package_count,
        shared_final_package_count=shared_final_package_count,
        target_package_sections=target_package_sections,
        package_roles_indexed=package_roles_indexed,
        artifact_types_indexed=artifact_types_indexed,
        artifact_formats_indexed=artifact_formats_indexed,
        source_artifact_paths=source_artifact_paths,
        target_package_paths=target_package_paths,
        source_artifact_digests=source_artifact_digests,
        layout_entry_digests=layout_entry_digests,
        dry_run_case_digests=dry_run_case_digests,
        package_content_entry_digests=package_content_entry_digests,
        final_package_audit_case_digests=final_package_audit_case_digests,
        package_digest_map_verified=package_digest_map_verified,
        package_layout_verified=package_layout_verified,
        proof_artifact_manifest_verified=proof_verified,
        documentation_artifact_manifest_verified=docs_verified,
        source_artifact_manifest_verified=src_verified,
        test_artifact_manifest_verified=test_verified,
        blocked_operations_verified=blocked_operations_verified,
        blocked_operation_attempt_counts={
            "archive_creation": 0, "file_copy": 0, "directory_creation": 0,
            "upload": 0, "deployment": 0, "external_signing": 0,
            "external_publication": 0, "production_mutation": 0
        },
        archive_creation_attempt_count=0,
        file_copy_attempt_count=0,
        directory_creation_attempt_count=0,
        upload_attempt_count=0,
        deployment_attempt_count=0,
        signing_attempt_count=0,
        external_publication_attempt_count=0,
        production_mutation_attempt_count=0,
        allowed_distribution_channels=allowed_channels,
        blocked_distribution_channels=blocked_channels,
        reason_codes=sorted(list(set(all_reasons))),
        software_validation_caveat=caveat,
        final_package_readiness_report_digest=""
    )
    report.final_package_readiness_report_digest = hash_waveguide_final_package_readiness_audit_report(report)
    return report


def validate_waveguide_final_package_readiness_audit_report(report: Any) -> Tuple[bool, List[str]]:
    """
    Validates a final package readiness audit report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    reasons = []
    is_valid = True

    # 1. Digest check
    given_digest = r_dict.get("final_package_readiness_report_digest")
    if not given_digest:
        is_valid = False
        reasons.append("FINAL_PACKAGE_READINESS_INVALID")
    else:
        recomputed = hash_waveguide_final_package_readiness_audit_report(r_dict)
        if recomputed != given_digest:
            is_valid = False
            reasons.append("FINAL_PACKAGE_READINESS_INVALID")
        else:
            reasons.append("FINAL_PACKAGE_READINESS_REPORT_DIGEST_VALID")

    # 2. Case digest checks
    cases = r_dict.get("audited_cases", [])
    case_statuses = []
    for c in cases:
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        given_c_digest = c_dict.get("final_package_audit_case_digest")
        if not given_c_digest:
            is_valid = False
            reasons.append("FINAL_PACKAGE_READINESS_INVALID")
        else:
            recomputed_c = hash_waveguide_final_package_readiness_audit_case(c_dict)
            if recomputed_c != given_c_digest:
                is_valid = False
                reasons.append("FINAL_PACKAGE_READINESS_INVALID")
            else:
                reasons.append("FINAL_PACKAGE_AUDIT_CASE_DIGEST_VALID")
        
        status = c_dict.get("final_package_readiness_status")
        case_statuses.append(status)

        # Content ready entries must be final verified
        if status == "final_package_content_verified":
            if (not c_dict.get("distribution_package_manifest_digest_match") or
                not c_dict.get("package_content_entry_digest_match") or
                not c_dict.get("source_dry_run_audit_report_digest_match") or
                not c_dict.get("source_dry_run_audit_report_valid") or
                not c_dict.get("source_dry_run_case_verified") or
                not c_dict.get("target_path_safe") or
                not c_dict.get("source_digest_preserved") or
                not c_dict.get("dry_run_case_digest_preserved") or
                not c_dict.get("layout_entry_digest_preserved") or
                not c_dict.get("package_digest_map_referenced") or
                not c_dict.get("package_layout_referenced") or
                not c_dict.get("section_manifest_referenced") or
                not c_dict.get("blocked_operations_zero")):
                is_valid = False
                reasons.append("FINAL_PACKAGE_READINESS_INVALID")

    # 3. Counts match checks
    v_count = r_dict.get("verified_final_package_count", 0)
    b_count = r_dict.get("blocked_final_package_count", 0)
    p_count = r_dict.get("pending_final_package_count", 0)
    i_count = r_dict.get("invalid_final_package_count", 0)

    if (v_count != case_statuses.count("final_package_content_verified") or
        b_count != case_statuses.count("final_package_content_blocked") or
        p_count != case_statuses.count("final_package_content_pending") or
        i_count != case_statuses.count("final_package_content_invalid")):
        is_valid = False
        reasons.append("FINAL_PACKAGE_READINESS_INVALID")

    # 4. Status checks
    status = r_dict.get("final_package_readiness_report_status")
    if status == "final_package_readiness_verified":
        if b_count > 0 or i_count > 0 or len(cases) == 0:
            is_valid = False
            reasons.append("FINAL_PACKAGE_READINESS_INVALID")

    # 5. Structure verifications flags
    if (not r_dict.get("package_digest_map_verified") or
        not r_dict.get("package_layout_verified") or
        not r_dict.get("proof_artifact_manifest_verified") or
        not r_dict.get("documentation_artifact_manifest_verified") or
        not r_dict.get("source_artifact_manifest_verified") or
        not r_dict.get("test_artifact_manifest_verified") or
        not r_dict.get("blocked_operations_verified")):
        is_valid = False
        reasons.append("FINAL_PACKAGE_READINESS_INVALID")

    # 6. Blocked operation counters must be zero
    if (r_dict.get("archive_creation_attempt_count", -1) != 0 or
        r_dict.get("file_copy_attempt_count", -1) != 0 or
        r_dict.get("directory_creation_attempt_count", -1) != 0 or
        r_dict.get("upload_attempt_count", -1) != 0 or
        r_dict.get("deployment_attempt_count", -1) != 0 or
        r_dict.get("signing_attempt_count", -1) != 0 or
        r_dict.get("external_publication_attempt_count", -1) != 0 or
        r_dict.get("production_mutation_attempt_count", -1) != 0):
        is_valid = False
        reasons.append("FINAL_PACKAGE_READINESS_INVALID")

    if is_valid:
        for code in r_dict.get("reason_codes", []):
            if code.startswith("FINAL_PACKAGE_"):
                reasons.append(code)
        reasons.append("FINAL_PACKAGE_READINESS_VERIFIED")
    else:
        reasons.append("FINAL_PACKAGE_READINESS_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_final_package_readiness_audit_report(report: Any) -> str:
    """
    Returns a plaintext summary of the report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)

    lines = [
        "============================================================",
        "          SOL WAVEGUIDE FINAL PACKAGE READINESS REPORT",
        "============================================================",
        f"Report ID:        {r_dict.get('final_package_readiness_report_id')}",
        f"Version:          {r_dict.get('final_package_readiness_report_version')}",
        f"Status:           {r_dict.get('final_package_readiness_report_status', '').upper()}",
        f"Report Digest:    {r_dict.get('final_package_readiness_report_digest')}",
        "------------------------------------------------------------",
        "Verified Package Content Cases:"
    ]

    for c in r_dict.get("audited_cases", []):
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        lines.append(
            f"  * {c_dict.get('source_artifact_path')} -> {c_dict.get('target_package_path')} "
            f"({c_dict.get('final_package_readiness_status')})"
        )

    lines.append("------------------------------------------------------------")
    lines.append("Structure Verifications:")
    lines.append(f"  - Package Digest Map:      {'VERIFIED' if r_dict.get('package_digest_map_verified') else 'FAILED'}")
    lines.append(f"  - Package Layout Map:      {'VERIFIED' if r_dict.get('package_layout_verified') else 'FAILED'}")
    lines.append(f"  - Proof Section Manifest:  {'VERIFIED' if r_dict.get('proof_artifact_manifest_verified') else 'FAILED'}")
    lines.append(f"  - Docs Section Manifest:   {'VERIFIED' if r_dict.get('documentation_artifact_manifest_verified') else 'FAILED'}")
    lines.append(f"  - Source Section Manifest: {'VERIFIED' if r_dict.get('source_artifact_manifest_verified') else 'FAILED'}")
    lines.append(f"  - Test Section Manifest:   {'VERIFIED' if r_dict.get('test_artifact_manifest_verified') else 'FAILED'}")
    lines.append(f"  - Blocked Operations Map:  {'VERIFIED' if r_dict.get('blocked_operations_verified') else 'FAILED'}")

    lines.append("------------------------------------------------------------")
    lines.append("Blocked Operations Violations:")
    lines.append(f"  - archive_creation:      {r_dict.get('archive_creation_attempt_count')}")
    lines.append(f"  - file_copy:             {r_dict.get('file_copy_attempt_count')}")
    lines.append(f"  - directory_creation:    {r_dict.get('directory_creation_attempt_count')}")
    lines.append(f"  - upload:                {r_dict.get('upload_attempt_count')}")
    lines.append(f"  - deployment:            {r_dict.get('deployment_attempt_count')}")
    lines.append(f"  - signing:               {r_dict.get('signing_attempt_count')}")
    lines.append(f"  - external_publication:  {r_dict.get('external_publication_attempt_count')}")
    lines.append(f"  - production_mutation:   {r_dict.get('production_mutation_attempt_count')}")

    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in r_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {r_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_final_package_readiness_audit_report(report: Any, filepath: str) -> None:
    """
    Exports the report to a JSON file.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    full_path = os.path.join(REPO_ROOT, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_final_package_readiness_audit_reports(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two reports.
    """
    l_dict = asdict(left) if hasattr(left, "__dict__") else dict(left)
    r_dict = asdict(right) if hasattr(right, "__dict__") else dict(right)

    diff = {
        "report_id_match": l_dict.get("final_package_readiness_report_id") == r_dict.get("final_package_readiness_report_id"),
        "report_version_match": l_dict.get("final_package_readiness_report_version") == r_dict.get("final_package_readiness_report_version"),
        "report_status_match": l_dict.get("final_package_readiness_report_status") == r_dict.get("final_package_readiness_report_status"),
        "report_digest_match": l_dict.get("final_package_readiness_report_digest") == r_dict.get("final_package_readiness_report_digest"),
        "verified_count_diff": l_dict.get("verified_final_package_count", 0) - r_dict.get("verified_final_package_count", 0),
        "target_paths_left_only": list(set(l_dict.get("target_package_paths", [])) - set(r_dict.get("target_package_paths", []))),
        "target_paths_right_only": list(set(r_dict.get("target_package_paths", [])) - set(l_dict.get("target_package_paths", [])))
    }

    diff["all_match"] = (
        diff["report_id_match"] and
        diff["report_version_match"] and
        diff["report_status_match"] and
        diff["report_digest_match"] and
        diff["verified_count_diff"] == 0 and
        not diff["target_paths_left_only"] and
        not diff["target_paths_right_only"]
    )
    return diff


def index_waveguide_final_package_readiness_cases_by_rc(cases: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes cases by rc_scope.
    """
    idx = {}
    for c in cases:
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        scope = c_dict.get("rc_scope", "Shared")
        if scope not in idx:
            idx[scope] = []
        idx[scope].append(c_dict)
    return idx


def index_waveguide_final_package_readiness_cases_by_status(cases: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes cases by final_package_readiness_status.
    """
    idx = {}
    for c in cases:
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        status = c_dict.get("final_package_readiness_status")
        if status not in idx:
            idx[status] = []
        idx[status].append(c_dict)
    return idx


def index_waveguide_final_package_readiness_cases_by_section(cases: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes cases by target_package_section.
    """
    idx = {}
    for c in cases:
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        sect = c_dict.get("target_package_section")
        if sect not in idx:
            idx[sect] = []
        idx[sect].append(c_dict)
    return idx
