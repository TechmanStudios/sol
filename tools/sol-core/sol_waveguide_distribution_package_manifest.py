# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Distribution Package Manifest generation and validation layer.
Describes the package contents, layout, section indices, and safety assertions as metadata.
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
    validate_waveguide_package_dry_run_report
)


@dataclass
class WaveguideDistributionPackageContentEntry:
    package_content_entry_id: str
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
    manifest_entry_status: str  # package_content_ready, package_content_blocked, etc.
    artifact_size_bytes: int
    is_proof_artifact: bool
    is_documentation_artifact: bool
    is_code_artifact: bool
    is_test_artifact: bool
    is_deployment_artifact: bool
    is_signing_artifact: bool
    allowed_distribution_channels: List[str]
    blocked_distribution_channels: List[str]
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    package_content_entry_digest: str = ""


@dataclass
class WaveguideDistributionPackageManifest:
    distribution_package_manifest_id: str
    distribution_package_manifest_version: int
    distribution_package_manifest_status: str  # package_manifest_ready, package_manifest_blocked, etc.
    source_dry_run_audit_report_digest: str
    source_package_assembly_plan_digest: str
    source_artifact_catalog_digest: str
    package_contents: List[WaveguideDistributionPackageContentEntry]
    ready_package_contents: List[str]
    blocked_package_contents: List[str]
    pending_package_contents: List[str]
    invalid_package_contents: List[str]
    ready_package_content_count: int
    blocked_package_content_count: int
    pending_package_content_count: int
    invalid_package_content_count: int
    total_manifest_file_count: int
    rc1_manifest_count: int
    rc2_manifest_count: int
    shared_manifest_count: int
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
    package_digest_map: List[Dict[str, Any]]
    package_layout: Dict[str, List[str]]
    proof_artifact_manifest: Dict[str, Any]
    documentation_artifact_manifest: Dict[str, Any]
    source_artifact_manifest: Dict[str, Any]
    test_artifact_manifest: Dict[str, Any]
    blocked_operations: Dict[str, int]
    allowed_distribution_channels: List[str]
    blocked_distribution_channels: List[str]
    reason_codes: List[str]
    software_validation_caveat: str
    distribution_package_manifest_digest: str = ""


def hash_waveguide_distribution_package_content_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a package content entry, excluding the self-referential field.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or a dataclass instance")

    e_dict_copy = dict(e_dict)
    e_dict_copy.pop("package_content_entry_digest", None)
    return hash_data(e_dict_copy)


def hash_waveguide_distribution_package_manifest(manifest: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a top-level manifest, excluding the self-referential field.
    """
    if hasattr(manifest, "__dict__"):
        m_dict = asdict(manifest)
    elif isinstance(manifest, dict):
        m_dict = dict(manifest)
    else:
        raise TypeError("manifest must be a dictionary or a dataclass instance")

    m_dict_copy = dict(m_dict)
    m_dict_copy.pop("distribution_package_manifest_digest", None)
    return hash_data(m_dict_copy)


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


def build_waveguide_distribution_package_content_entry(
    dry_run_case: Any,
    plan_path_or_dict: Any,
    catalog_path_or_dict: Any
) -> WaveguideDistributionPackageContentEntry:
    """
    Builds a single package content entry from a verified dry-run case and catalog metadata.
    """
    c_dict = asdict(dry_run_case) if hasattr(dry_run_case, "__dict__") else dict(dry_run_case)
    plan_dict = _load_dict(plan_path_or_dict) or {}
    catalog_dict = _load_dict(catalog_path_or_dict) or {}

    source_path = c_dict.get("source_artifact_path", "")
    source_name = os.path.basename(source_path)

    # Lookup size in catalog
    cat_entries = catalog_dict.get("entries", [])
    cat_entry = next((e for e in cat_entries if e.get("artifact_path") == source_path), None)
    size_bytes = cat_entry.get("artifact_size_bytes", 0) if cat_entry else 0

    section = c_dict.get("target_package_section", "")

    # Layout entry digest from plan
    plan_entries = plan_dict.get("layout_entries", [])
    plan_entry = next((e for e in plan_entries if e.get("source_artifact_path") == source_path), None)
    layout_entry_digest = plan_entry.get("package_layout_entry_digest", "") if plan_entry else ""

    dry_run_status = c_dict.get("dry_run_status", "")
    include_in_manifest = False
    manifest_entry_status = "package_content_invalid"
    
    if dry_run_status == "package_dry_run_verified":
        include_in_manifest = True
        manifest_entry_status = "package_content_ready"
    elif dry_run_status == "package_dry_run_blocked":
        manifest_entry_status = "package_content_blocked"
    elif dry_run_status == "package_dry_run_pending":
        manifest_entry_status = "package_content_pending"

    # Identify categories
    is_proof = section == "proof/"
    is_docs = section == "docs/"
    is_code = section == "source/"
    is_test = section == "tests/"
    is_deploy = c_dict.get("is_deployment_artifact", False) or "deploy" in source_name.lower()
    is_sign = c_dict.get("is_signing_artifact", False) or "signing" in source_name.lower()

    reason_codes = ["PACKAGE_MANIFEST_CONTENT_ENTRY_CANONICAL"]
    if manifest_entry_status == "package_content_ready":
        reason_codes.append("PACKAGE_MANIFEST_CONTENT_READY")
    
    if c_dict.get("source_artifact_digest"):
        reason_codes.append("PACKAGE_MANIFEST_SOURCE_DIGEST_PRESERVED")
    if c_dict.get("target_package_path"):
        reason_codes.append("PACKAGE_MANIFEST_TARGET_PATH_REFERENCED")
    if c_dict.get("package_dry_run_case_digest"):
        reason_codes.append("PACKAGE_MANIFEST_DRY_RUN_CASE_DIGEST_REFERENCED")
    if layout_entry_digest:
        reason_codes.append("PACKAGE_MANIFEST_LAYOUT_ENTRY_DIGEST_REFERENCED")

    entry = WaveguideDistributionPackageContentEntry(
        package_content_entry_id=f"SOL-WAVEGUIDE-CONTENT-{source_name.replace('.', '_')}",
        source_artifact_path=source_path,
        source_artifact_name=source_name,
        source_artifact_digest=c_dict.get("source_artifact_digest", ""),
        source_artifact_type=c_dict.get("source_artifact_type", ""),
        source_artifact_format=c_dict.get("source_artifact_format", ""),
        source_package_role=c_dict.get("source_package_role", ""),
        rc_scope=c_dict.get("rc_scope", ""),
        candidate_level=c_dict.get("candidate_level", ""),
        target_package_path=c_dict.get("target_package_path", ""),
        target_package_section=section,
        dry_run_case_digest=c_dict.get("package_dry_run_case_digest", ""),
        layout_entry_digest=layout_entry_digest,
        include_in_package_manifest=include_in_manifest,
        manifest_entry_status=manifest_entry_status,
        artifact_size_bytes=size_bytes,
        is_proof_artifact=is_proof,
        is_documentation_artifact=is_docs,
        is_code_artifact=is_code,
        is_test_artifact=is_test,
        is_deployment_artifact=is_deploy,
        is_signing_artifact=is_sign,
        allowed_distribution_channels=sorted(c_dict.get("allowed_distribution_channels", [])),
        blocked_distribution_channels=sorted(c_dict.get("blocked_distribution_channels", [])),
        reason_codes=sorted(list(set(reason_codes))),
        notes=[],
        software_validation_caveat=c_dict.get("software_validation_caveat", ""),
        package_content_entry_digest=""
    )
    entry.package_content_entry_digest = hash_waveguide_distribution_package_content_entry(entry)
    return entry


def validate_waveguide_distribution_package_content_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Validates the structure and safety rules of a content entry.
    """
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    reasons = []
    is_valid = True

    # 1. Required fields
    required = [
        "source_artifact_path", "source_artifact_digest", "source_artifact_type",
        "source_artifact_format", "source_package_role", "rc_scope",
        "target_package_path", "target_package_section", "dry_run_case_digest",
        "layout_entry_digest", "manifest_entry_status", "software_validation_caveat"
    ]
    for req in required:
        if not e_dict.get(req):
            is_valid = False
            reasons.append("PACKAGE_MANIFEST_INVALID")

    # Validate entry digest
    given_digest = e_dict.get("package_content_entry_digest")
    if not given_digest:
        is_valid = False
        reasons.append("PACKAGE_MANIFEST_INVALID")
    else:
        recomputed = hash_waveguide_distribution_package_content_entry(e_dict)
        if recomputed != given_digest:
            is_valid = False
            reasons.append("PACKAGE_MANIFEST_INVALID")
        else:
            reasons.append("PACKAGE_MANIFEST_CONTENT_ENTRY_DIGEST_VALID")

    # Safety rules for ready entries
    status = e_dict.get("manifest_entry_status")
    tpath = e_dict.get("target_package_path", "")

    if status == "package_content_ready":
        # Target path safety
        if os.path.isabs(tpath) or tpath.startswith("/") or ".." in tpath or "\\" in tpath:
            is_valid = False
            reasons.append("PACKAGE_MANIFEST_INVALID")

        # Exclude deploy/signing
        if e_dict.get("is_deployment_artifact") or e_dict.get("is_signing_artifact"):
            is_valid = False
            reasons.append("PACKAGE_MANIFEST_BLOCKED")

    if is_valid:
        reasons.append("PACKAGE_MANIFEST_READY")
    else:
        if "PACKAGE_MANIFEST_BLOCKED" not in reasons:
            reasons.append("PACKAGE_MANIFEST_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_content_digest_map(entries: List[Any]) -> List[Dict[str, Any]]:
    """
    Creates a deterministic list mapping target paths to digests, sorted by target path.
    """
    digest_map = []
    sorted_entries = sorted(
        entries,
        key=lambda e: e.target_package_path if hasattr(e, "target_package_path") else e.get("target_package_path", "")
    )
    for idx, e in enumerate(sorted_entries):
        e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
        if e_dict.get("manifest_entry_status") == "package_content_ready":
            digest_map.append({
                "digest_map_index": idx + 1,
                "source_artifact_path": e_dict.get("source_artifact_path", ""),
                "target_package_path": e_dict.get("target_package_path", ""),
                "artifact_digest": e_dict.get("source_artifact_digest", ""),
                "artifact_type": e_dict.get("source_artifact_type", ""),
                "package_role": e_dict.get("source_package_role", ""),
                "rc_scope": e_dict.get("rc_scope", "")
            })
    return digest_map


def build_waveguide_package_content_layout(entries: List[Any]) -> Dict[str, List[str]]:
    """
    Creates a deterministic section layout map.
    """
    layout = {}
    sections = sorted(list(set(e.target_package_section if hasattr(e, "target_package_section") else e.get("target_package_section", "") for e in entries)))
    for sect in sections:
        if sect:
            paths = []
            for e in entries:
                e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
                if e_dict.get("target_package_section") == sect and e_dict.get("manifest_entry_status") == "package_content_ready":
                    paths.append(e_dict.get("target_package_path"))
            layout[sect] = sorted(paths)
    return layout


def build_waveguide_package_section_manifest(section_name: str, entries: List[Any]) -> Dict[str, Any]:
    """
    Compiles a deterministic section manifest.
    """
    paths = []
    digests = []
    entry_digests = []

    for e in entries:
        e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
        if e_dict.get("target_package_section") == section_name and e_dict.get("manifest_entry_status") == "package_content_ready":
            paths.append(e_dict.get("target_package_path"))
            digests.append(e_dict.get("source_artifact_digest"))
            entry_digests.append(e_dict.get("package_content_entry_digest"))

    return {
        "section_name": section_name,
        "entry_count": len(paths),
        "target_paths": sorted(paths),
        "artifact_digests": sorted(digests),
        "content_entry_digests": sorted(entry_digests)
    }


def build_waveguide_distribution_package_manifest(
    report_path_or_dict: Any,
    plan_path_or_dict: Any,
    catalog_path_or_dict: Any
) -> WaveguideDistributionPackageManifest:
    """
    Builds the top-level package manifest by verifying the dry-run report and mapping cases to content entries.
    """
    report_dict = _load_dict(report_path_or_dict) or {}
    plan_dict = _load_dict(plan_path_or_dict) or {}
    catalog_dict = _load_dict(catalog_path_or_dict) or {}

    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    # Validate dry-run report
    report_ok, report_reasons = validate_waveguide_package_dry_run_report(report_dict)
    report_status = report_dict.get("package_dry_run_report_status", "")

    if not report_dict or not report_ok or report_status != "package_dry_run_verified":
        # Return invalid manifest
        manifest = WaveguideDistributionPackageManifest(
            distribution_package_manifest_id="SOL-WAVEGUIDE-DISTRIBUTION-PACKAGE-MANIFEST",
            distribution_package_manifest_version=1,
            distribution_package_manifest_status="package_manifest_invalid",
            source_dry_run_audit_report_digest=report_dict.get("package_dry_run_report_digest", ""),
            source_package_assembly_plan_digest=plan_dict.get("package_assembly_plan_digest", ""),
            source_artifact_catalog_digest=catalog_dict.get("artifact_catalog_digest", ""),
            package_contents=[],
            ready_package_contents=[],
            blocked_package_contents=[],
            pending_package_contents=[],
            invalid_package_contents=[],
            ready_package_content_count=0,
            blocked_package_content_count=0,
            pending_package_content_count=0,
            invalid_package_content_count=0,
            total_manifest_file_count=0,
            rc1_manifest_count=0,
            rc2_manifest_count=0,
            shared_manifest_count=0,
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
            package_digest_map=[],
            package_layout={},
            proof_artifact_manifest=build_waveguide_package_section_manifest("proof/", []),
            documentation_artifact_manifest=build_waveguide_package_section_manifest("docs/", []),
            source_artifact_manifest=build_waveguide_package_section_manifest("source/", []),
            test_artifact_manifest=build_waveguide_package_section_manifest("tests/", []),
            blocked_operations={
                "archive_creation": 0,
                "file_copy": 0,
                "directory_creation": 0,
                "upload": 0,
                "deployment": 0,
                "external_signing": 0,
                "external_publication": 0,
                "production_mutation": 0
            },
            allowed_distribution_channels=[],
            blocked_distribution_channels=[],
            reason_codes=["PACKAGE_MANIFEST_SOURCE_DRY_RUN_REPORT_INVALID", "PACKAGE_MANIFEST_INVALID"],
            software_validation_caveat=caveat,
            distribution_package_manifest_digest=""
        )
        manifest.distribution_package_manifest_digest = hash_waveguide_distribution_package_manifest(manifest)
        return manifest

    # Map dry run cases to content entries
    audited_cases = report_dict.get("audited_cases", [])
    entries = []
    for case in audited_cases:
        entry = build_waveguide_distribution_package_content_entry(case, plan_dict, catalog_dict)
        entries.append(entry)

    # Sort entries by target_package_path, source_artifact_path, source_artifact_digest
    def entry_sort_key(e):
        return (e.target_package_path, e.source_artifact_path, e.source_artifact_digest)
    
    sorted_entries = sorted(entries, key=entry_sort_key)

    ready_package_contents = []
    blocked_package_contents = []
    pending_package_contents = []
    invalid_package_contents = []

    rc1_manifest_count = 0
    rc2_manifest_count = 0
    shared_manifest_count = 0

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

    all_reasons = [
        "PACKAGE_MANIFEST_COUNTS_VALID",
        "PACKAGE_MANIFEST_INDEXES_VALID",
        "PACKAGE_MANIFEST_DIGEST_MAP_CANONICAL",
        "PACKAGE_MANIFEST_LAYOUT_CANONICAL",
        "PACKAGE_MANIFEST_SOURCE_DRY_RUN_REPORT_VALID",
        "PACKAGE_MANIFEST_SOURCE_DRY_RUN_REPORT_VERIFIED",
        "PACKAGE_MANIFEST_NO_ARCHIVE_CREATED",
        "PACKAGE_MANIFEST_NO_FILE_COPY_PERFORMED",
        "PACKAGE_MANIFEST_NO_DIRECTORY_CREATED",
        "PACKAGE_MANIFEST_NO_UPLOAD_PERFORMED",
        "PACKAGE_MANIFEST_NO_DEPLOYMENT_PERFORMED",
        "PACKAGE_MANIFEST_NO_SIGNING_PERFORMED",
        "PACKAGE_MANIFEST_NO_PUBLICATION_PERFORMED",
        "PACKAGE_MANIFEST_NO_PRODUCTION_MUTATION"
    ]

    if plan_dict.get("package_assembly_plan_id"):
        all_reasons.append("PACKAGE_MANIFEST_SOURCE_ASSEMBLY_PLAN_REFERENCED")
    if catalog_dict.get("artifact_catalog_id"):
        all_reasons.append("PACKAGE_MANIFEST_SOURCE_ARTIFACT_CATALOG_REFERENCED")

    for entry in sorted_entries:
        path = entry.source_artifact_path
        tpath = entry.target_package_path
        sect = entry.target_package_section
        status = entry.manifest_entry_status
        scope = entry.rc_scope
        role = entry.source_package_role
        atype = entry.source_artifact_type
        aformat = entry.source_artifact_format
        digest = entry.source_artifact_digest
        layout_digest = entry.layout_entry_digest
        case_digest = entry.dry_run_case_digest
        entry_digest = entry.package_content_entry_digest

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
        add_unique(layout_entry_digests, layout_digest)
        add_unique(dry_run_case_digests, case_digest)
        add_unique(package_content_entry_digests, entry_digest)

        if status == "package_content_ready":
            add_unique(ready_package_contents, path)
        elif status == "package_content_blocked":
            add_unique(blocked_package_contents, path)
        elif status == "package_content_pending":
            add_unique(pending_package_contents, path)
        else:
            add_unique(invalid_package_contents, path)

        if scope == "RC1":
            rc1_manifest_count += 1
        elif scope == "RC2":
            rc2_manifest_count += 1
        else:
            shared_manifest_count += 1

        for code in entry.reason_codes:
            if code not in all_reasons:
                all_reasons.append(code)

    # Sort arrays
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

    ready_package_contents = sorted(ready_package_contents)
    blocked_package_contents = sorted(blocked_package_contents)
    pending_package_contents = sorted(pending_package_contents)
    invalid_package_contents = sorted(invalid_package_contents)

    # Digest map & layout
    package_digest_map = build_waveguide_package_content_digest_map(sorted_entries)
    package_layout = build_waveguide_package_content_layout(sorted_entries)

    # Section manifests
    proof_manifest = build_waveguide_package_section_manifest("proof/", sorted_entries)
    docs_manifest = build_waveguide_package_section_manifest("docs/", sorted_entries)
    source_manifest = build_waveguide_package_section_manifest("source/", sorted_entries)
    test_manifest = build_waveguide_package_section_manifest("tests/", sorted_entries)

    if proof_manifest["entry_count"] > 0:
        all_reasons.append("PACKAGE_MANIFEST_PROOF_SECTION_INCLUDED")
    if docs_manifest["entry_count"] > 0:
        all_reasons.append("PACKAGE_MANIFEST_DOCS_SECTION_INCLUDED")
    if source_manifest["entry_count"] > 0:
        all_reasons.append("PACKAGE_MANIFEST_SOURCE_SECTION_INCLUDED")
    if test_manifest["entry_count"] > 0:
        all_reasons.append("PACKAGE_MANIFEST_TEST_SECTION_INCLUDED")

    ready_count = len(ready_package_contents)
    blocked_count = len(blocked_package_contents)
    pending_count = len(pending_package_contents)
    invalid_count = len(invalid_package_contents)

    manifest_status = "package_manifest_invalid"
    if blocked_count == 0 and invalid_count == 0 and ready_count > 0:
        manifest_status = "package_manifest_ready"
        all_reasons.append("PACKAGE_MANIFEST_READY")
    else:
        all_reasons.append("PACKAGE_MANIFEST_BLOCKED")

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

    manifest = WaveguideDistributionPackageManifest(
        distribution_package_manifest_id="SOL-WAVEGUIDE-DISTRIBUTION-PACKAGE-MANIFEST",
        distribution_package_manifest_version=1,
        distribution_package_manifest_status=manifest_status,
        source_dry_run_audit_report_digest=report_dict.get("package_dry_run_report_digest", ""),
        source_package_assembly_plan_digest=plan_dict.get("package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=catalog_dict.get("artifact_catalog_digest", ""),
        package_contents=sorted_entries,
        ready_package_contents=ready_package_contents,
        blocked_package_contents=blocked_package_contents,
        pending_package_contents=pending_package_contents,
        invalid_package_contents=invalid_package_contents,
        ready_package_content_count=ready_count,
        blocked_package_content_count=blocked_count,
        pending_package_content_count=pending_count,
        invalid_package_content_count=invalid_count,
        total_manifest_file_count=ready_count,
        rc1_manifest_count=rc1_manifest_count,
        rc2_manifest_count=rc2_manifest_count,
        shared_manifest_count=shared_manifest_count,
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
        package_digest_map=package_digest_map,
        package_layout=package_layout,
        proof_artifact_manifest=proof_manifest,
        documentation_artifact_manifest=docs_manifest,
        source_artifact_manifest=source_manifest,
        test_artifact_manifest=test_manifest,
        blocked_operations={
            "archive_creation": 0,
            "file_copy": 0,
            "directory_creation": 0,
            "upload": 0,
            "deployment": 0,
            "external_signing": 0,
            "external_publication": 0,
            "production_mutation": 0
        },
        allowed_distribution_channels=allowed_channels,
        blocked_distribution_channels=blocked_channels,
        reason_codes=sorted(list(set(all_reasons))),
        software_validation_caveat=caveat,
        distribution_package_manifest_digest=""
    )
    manifest.distribution_package_manifest_digest = hash_waveguide_distribution_package_manifest(manifest)
    return manifest


def validate_waveguide_distribution_package_manifest(manifest: Any) -> Tuple[bool, List[str]]:
    """
    Validates a distribution package manifest.
    """
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    reasons = []
    is_valid = True

    # 1. Digest checks
    given_digest = m_dict.get("distribution_package_manifest_digest")
    if not given_digest:
        is_valid = False
        reasons.append("PACKAGE_MANIFEST_INVALID")
    else:
        recomputed = hash_waveguide_distribution_package_manifest(m_dict)
        if recomputed != given_digest:
            is_valid = False
            reasons.append("PACKAGE_MANIFEST_INVALID")
        else:
            reasons.append("PACKAGE_MANIFEST_DIGEST_VALID")

    # 2. Content entries checks
    contents = m_dict.get("package_contents", [])
    entry_statuses = []
    for entry in contents:
        ok, entry_reasons = validate_waveguide_distribution_package_content_entry(entry)
        if not ok:
            is_valid = False
            reasons.append("PACKAGE_MANIFEST_INVALID")
        e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
        entry_statuses.append(e_dict.get("manifest_entry_status"))

    # 3. Counts check
    ready_cnt = m_dict.get("ready_package_content_count", 0)
    blocked_cnt = m_dict.get("blocked_package_content_count", 0)
    pending_cnt = m_dict.get("pending_package_content_count", 0)
    invalid_cnt = m_dict.get("invalid_package_content_count", 0)

    if (ready_cnt != entry_statuses.count("package_content_ready") or
        blocked_cnt != entry_statuses.count("package_content_blocked") or
        pending_cnt != entry_statuses.count("package_content_pending") or
        invalid_cnt != entry_statuses.count("package_content_invalid")):
        is_valid = False
        reasons.append("PACKAGE_MANIFEST_INVALID")

    # 4. Status check
    status = m_dict.get("distribution_package_manifest_status")
    if status == "package_manifest_ready":
        if blocked_cnt > 0 or invalid_cnt > 0 or len(contents) == 0:
            is_valid = False
            reasons.append("PACKAGE_MANIFEST_INVALID")

    # 5. Check blocked operation counts are 0
    blocked_ops = m_dict.get("blocked_operations", {})
    for op, cnt in blocked_ops.items():
        if cnt != 0:
            is_valid = False
            reasons.append("PACKAGE_MANIFEST_INVALID")

    if is_valid:
        for r in m_dict.get("reason_codes", []):
            if r.startswith("PACKAGE_MANIFEST_"):
                reasons.append(r)
        reasons.append("PACKAGE_MANIFEST_READY")
    else:
        reasons.append("PACKAGE_MANIFEST_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_distribution_package_manifest(manifest: Any) -> str:
    """
    Returns a plaintext summary of the distribution package manifest.
    """
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    
    lines = [
        "============================================================",
        "          SOL WAVEGUIDE DISTRIBUTION PACKAGE MANIFEST",
        "============================================================",
        f"Manifest ID:      {m_dict.get('distribution_package_manifest_id')}",
        f"Version:          {m_dict.get('distribution_package_manifest_version')}",
        f"Status:           {m_dict.get('distribution_package_manifest_status', '').upper()}",
        f"Manifest Digest:  {m_dict.get('distribution_package_manifest_digest')}",
        "------------------------------------------------------------",
        "Package Contents Layout:"
    ]

    for sect, paths in m_dict.get("package_layout", {}).items():
        lines.append(f"  * {sect}: {len(paths)} files")
        for p in paths:
            lines.append(f"    - {p}")

    lines.append("------------------------------------------------------------")
    lines.append("Digest Map Index:")
    for entry in m_dict.get("package_digest_map", []):
        lines.append(
            f"  [{entry.get('digest_map_index')}] {entry.get('target_package_path')} "
            f"-> sha256:{entry.get('artifact_digest')[:16]}..."
        )

    lines.append("------------------------------------------------------------")
    lines.append("Blocked Operations:")
    for op, count in m_dict.get("blocked_operations", {}).items():
        lines.append(f"  - {op}: {count} violations")

    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in m_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {m_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_distribution_package_manifest(manifest: Any, filepath: str) -> None:
    """
    Exports the manifest to a JSON file.
    """
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    full_path = os.path.join(REPO_ROOT, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(m_dict, f, indent=4, sort_keys=True)


def compare_waveguide_distribution_package_manifests(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two manifests.
    """
    l_dict = asdict(left) if hasattr(left, "__dict__") else dict(left)
    r_dict = asdict(right) if hasattr(right, "__dict__") else dict(right)

    diff = {
        "manifest_id_match": l_dict.get("distribution_package_manifest_id") == r_dict.get("distribution_package_manifest_id"),
        "manifest_version_match": l_dict.get("distribution_package_manifest_version") == r_dict.get("distribution_package_manifest_version"),
        "manifest_status_match": l_dict.get("distribution_package_manifest_status") == r_dict.get("distribution_package_manifest_status"),
        "manifest_digest_match": l_dict.get("distribution_package_manifest_digest") == r_dict.get("distribution_package_manifest_digest"),
        "ready_count_diff": l_dict.get("ready_package_content_count", 0) - r_dict.get("ready_package_content_count", 0),
        "target_paths_left_only": list(set(l_dict.get("target_package_paths", [])) - set(r_dict.get("target_package_paths", []))),
        "target_paths_right_only": list(set(r_dict.get("target_package_paths", [])) - set(l_dict.get("target_package_paths", [])))
    }

    diff["all_match"] = (
        diff["manifest_id_match"] and
        diff["manifest_version_match"] and
        diff["manifest_status_match"] and
        diff["manifest_digest_match"] and
        diff["ready_count_diff"] == 0 and
        not diff["target_paths_left_only"] and
        not diff["target_paths_right_only"]
    )
    return diff


def index_waveguide_package_contents_by_rc(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes content entries by rc_scope.
    """
    idx = {}
    for e in entries:
        e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
        scope = e_dict.get("rc_scope", "Shared")
        if scope not in idx:
            idx[scope] = []
        idx[scope].append(e_dict)
    return idx


def index_waveguide_package_contents_by_section(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes content entries by target_package_section.
    """
    idx = {}
    for e in entries:
        e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
        sect = e_dict.get("target_package_section", "")
        if sect not in idx:
            idx[sect] = []
        idx[sect].append(e_dict)
    return idx


def index_waveguide_package_contents_by_role(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes content entries by source_package_role.
    """
    idx = {}
    for e in entries:
        e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
        role = e_dict.get("source_package_role", "")
        if role not in idx:
            idx[role] = []
        idx[role].append(e_dict)
    return idx


def index_waveguide_package_contents_by_artifact_type(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes content entries by source_artifact_type.
    """
    idx = {}
    for e in entries:
        e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
        atype = e_dict.get("source_artifact_type", "")
        if atype not in idx:
            idx[atype] = []
        idx[atype].append(e_dict)
    return idx
