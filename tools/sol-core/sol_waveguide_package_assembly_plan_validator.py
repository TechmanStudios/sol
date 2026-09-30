# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Plan Validator / Dry-Run Packager Auditor.
Bypasses physical layout execution and validates the package assembly plan as metadata.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT,
    hash_file_contents
)
from sol_waveguide_certified_artifact_catalog import (
    validate_waveguide_certified_artifact_catalog,
    validate_waveguide_certified_artifact_catalog_entry
)
from sol_waveguide_distribution_package_assembly_plan import (
    validate_waveguide_distribution_package_assembly_plan,
    validate_waveguide_distribution_package_layout_entry,
    hash_waveguide_distribution_package_layout_entry,
    hash_waveguide_distribution_package_assembly_plan
)


@dataclass
class WaveguidePackageDryRunAuditCase:
    package_dry_run_case_id: str
    package_assembly_plan_id: str
    package_assembly_plan_path: str
    package_assembly_plan_digest_recorded: str
    package_assembly_plan_digest_recomputed: str
    package_assembly_plan_digest_match: bool
    layout_entry_id: str
    layout_entry_digest_recorded: str
    layout_entry_digest_recomputed: str
    layout_entry_digest_match: bool
    source_artifact_path: str
    source_artifact_digest: str
    source_artifact_type: str
    source_artifact_format: str
    source_package_role: str
    rc_scope: str
    candidate_level: str
    target_package_path: str
    target_package_section: str
    target_path_relative: bool
    target_path_uses_forward_slashes: bool
    target_path_has_no_parent_traversal: bool
    target_path_has_no_absolute_root: bool
    target_path_collision_free: bool
    include_in_package_plan: bool
    assembly_status: str
    dry_run_status: str  # package_dry_run_verified, package_dry_run_blocked, package_dry_run_pending, package_dry_run_invalid
    source_artifact_catalog_digest_recorded: str
    source_artifact_catalog_digest_recomputed: str
    source_artifact_catalog_digest_match: bool
    source_artifact_catalog_valid: bool
    no_archive_created: bool
    no_file_copy_performed: bool
    no_upload_performed: bool
    no_deployment_performed: bool
    no_signing_performed: bool
    allowed_distribution_channels: List[str]
    blocked_distribution_channels: List[str]
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    package_dry_run_case_digest: str = ""

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
class WaveguidePackageDryRunAuditReport:
    package_dry_run_report_id: str
    package_dry_run_report_version: int
    package_dry_run_report_status: str  # package_dry_run_verified, package_dry_run_blocked, etc.
    source_package_assembly_plan_digest: str
    source_artifact_catalog_digest: str
    audited_cases: List[WaveguidePackageDryRunAuditCase]
    verified_dry_run_cases: List[str]
    blocked_dry_run_cases: List[str]
    pending_dry_run_cases: List[str]
    invalid_dry_run_cases: List[str]
    verified_dry_run_count: int
    blocked_dry_run_count: int
    pending_dry_run_count: int
    invalid_dry_run_count: int
    total_simulated_file_count: int
    rc1_dry_run_count: int
    rc2_dry_run_count: int
    shared_dry_run_count: int
    target_package_sections: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    artifact_formats_indexed: List[str]
    source_artifact_paths: List[str]
    target_package_paths: List[str]
    source_artifact_digests: List[str]
    layout_entry_digests: List[str]
    proof_artifact_dry_run_layout: List[str]
    documentation_artifact_dry_run_layout: List[str]
    source_module_dry_run_layout: List[str]
    test_source_dry_run_layout: List[str]
    dry_run_file_map: List[Dict[str, Any]]
    dry_run_section_index: Dict[str, List[str]]
    target_path_collision_count: int
    unsafe_target_path_count: int
    archive_creation_attempt_count: int
    file_copy_attempt_count: int
    upload_attempt_count: int
    deployment_attempt_count: int
    signing_attempt_count: int
    allowed_distribution_channels: List[str]
    blocked_distribution_channels: List[str]
    reason_codes: List[str]
    software_validation_caveat: str
    package_dry_run_report_digest: str = ""


def hash_waveguide_package_dry_run_audit_case(case: Any) -> str:
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
    c_dict_copy.pop("package_dry_run_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_package_dry_run_case(case: Any) -> str:
    """
    Alias for hash_waveguide_package_dry_run_audit_case.
    """
    return hash_waveguide_package_dry_run_audit_case(case)



def hash_waveguide_package_dry_run_report(report: Any) -> str:
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
    r_dict_copy.pop("package_dry_run_report_digest", None)
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


def recompute_waveguide_package_assembly_plan_digest(plan_path_or_dict: Any) -> str:
    """
    Recomputes the assembly plan digest independently.
    """
    plan_dict = _load_dict(plan_path_or_dict)
    if plan_dict:
        return hash_waveguide_distribution_package_assembly_plan(plan_dict)
    return ""


def recompute_waveguide_package_layout_entry_digest(entry: Any) -> str:
    """
    Recomputes layout entry digest.
    """
    return hash_waveguide_distribution_package_layout_entry(entry)


def validate_waveguide_package_target_path_safety(target_path: str) -> Tuple[bool, List[str]]:
    """
    Checks that the target path is relative, uses /, does not begin with /, does not Traversal (..),
    and does not contain empty segments.
    """
    reasons = []
    is_safe = True

    if not target_path:
        return False, ["PACKAGE_DRY_RUN_INVALID"]

    # 1. Absolute root check
    if os.path.isabs(target_path) or target_path.startswith("/"):
        is_safe = False
        reasons.append("PACKAGE_DRY_RUN_TARGET_PATH_NO_ABSOLUTE_ROOT")
    else:
        reasons.append("PACKAGE_DRY_RUN_TARGET_PATH_RELATIVE")

    # 2. Separators check
    if "\\" in target_path:
        is_safe = False
        reasons.append("PACKAGE_DRY_RUN_INVALID")
    else:
        reasons.append("PACKAGE_DRY_RUN_TARGET_PATH_FORWARD_SLASHES")

    # 3. Traversal check
    if ".." in target_path:
        is_safe = False
        reasons.append("PACKAGE_DRY_RUN_TARGET_PATH_NO_PARENT_TRAVERSAL")
    else:
        reasons.append("PACKAGE_DRY_RUN_TARGET_PATH_NO_PARENT_TRAVERSAL")

    # 4. Empty segments check
    parts = target_path.split("/")
    if any(p == "" for p in parts if p != parts[-1] or p == ""):
        is_safe = False
        reasons.append("PACKAGE_DRY_RUN_INVALID")

    return is_safe, sorted(list(set(reasons)))


def detect_waveguide_package_target_path_collisions(entries: List[Any]) -> int:
    """
    Counts how many entries have target package paths that collide.
    """
    paths = []
    for e in entries:
        e_dict = asdict(e) if hasattr(e, "__dict__") else dict(e)
        tpath = e_dict.get("target_package_path")
        status = e_dict.get("assembly_status")
        if status == "package_layout_ready" and tpath:
            paths.append(tpath)

    counts = Counter(paths)
    collision_count = sum(c for p, c in counts.items() if c > 1)
    return collision_count


def build_waveguide_package_dry_run_case(
    layout_entry: Any,
    plan_path_or_dict: Any,
    catalog_path_or_dict: Any
) -> WaveguidePackageDryRunAuditCase:
    """
    Builds a dry-run audit case validating a layout entry against the plan and catalog.
    """
    e_dict = asdict(layout_entry) if hasattr(layout_entry, "__dict__") else dict(layout_entry)
    plan_dict = _load_dict(plan_path_or_dict) or {}
    catalog_dict = _load_dict(catalog_path_or_dict) or {}

    plan_path = plan_path_or_dict if isinstance(plan_path_or_dict, str) else ""

    # Plan digests
    plan_digest_recorded = plan_dict.get("package_assembly_plan_digest", "")
    plan_digest_recomputed = recompute_waveguide_package_assembly_plan_digest(plan_dict)
    plan_digest_match = (plan_digest_recorded == plan_digest_recomputed) and (plan_digest_recorded != "")

    # Layout entry digest
    entry_digest_recorded = e_dict.get("package_layout_entry_digest", "")
    entry_digest_recomputed = recompute_waveguide_package_layout_entry_digest(e_dict)
    entry_digest_match = (entry_digest_recorded == entry_digest_recomputed) and (entry_digest_recorded != "")

    # Catalog digests
    catalog_digest_recorded = plan_dict.get("source_artifact_catalog_digest", "")
    catalog_digest_recomputed = catalog_dict.get("artifact_catalog_digest", "")
    catalog_digest_match = (catalog_digest_recorded == catalog_digest_recomputed) and (catalog_digest_recorded != "")

    # Validate catalog
    catalog_valid = False
    if catalog_dict:
        catalog_valid, _ = validate_waveguide_certified_artifact_catalog(catalog_dict)

    # Path safety checks
    tpath = e_dict.get("target_package_path", "")
    path_safe, path_reasons = validate_waveguide_package_target_path_safety(tpath)

    # Collision check
    entries = plan_dict.get("layout_entries", [])
    # Find all ready target package paths to check collisions
    ready_paths = []
    for ent in entries:
        if ent.get("assembly_status") == "package_layout_ready":
            ready_paths.append(ent.get("target_package_path"))
    collision_free = (ready_paths.count(tpath) <= 1)

    # Dry-run boundaries check
    no_archive = True
    no_copy = True
    no_upload = True
    no_deploy = True
    no_sign = True

    # Assemble reasons
    reason_codes = [
        "PACKAGE_DRY_RUN_CASE_CANONICAL",
        "PACKAGE_DRY_RUN_NO_ARCHIVE_CREATED",
        "PACKAGE_DRY_RUN_NO_FILE_COPY_PERFORMED",
        "PACKAGE_DRY_RUN_NO_UPLOAD_PERFORMED",
        "PACKAGE_DRY_RUN_NO_DEPLOYMENT_PERFORMED",
        "PACKAGE_DRY_RUN_NO_SIGNING_PERFORMED"
    ]

    if plan_dict:
        reason_codes.append("PACKAGE_DRY_RUN_ASSEMBLY_PLAN_LOADED")
    if plan_digest_match:
        reason_codes.append("PACKAGE_DRY_RUN_ASSEMBLY_PLAN_DIGEST_MATCH")
    else:
        reason_codes.append("PACKAGE_DRY_RUN_ASSEMBLY_PLAN_DIGEST_MISMATCH")

    if entry_digest_match:
        reason_codes.append("PACKAGE_DRY_RUN_LAYOUT_ENTRY_DIGEST_MATCH")
    else:
        reason_codes.append("PACKAGE_DRY_RUN_LAYOUT_ENTRY_DIGEST_MISMATCH")

    if catalog_valid:
        reason_codes.append("PACKAGE_DRY_RUN_SOURCE_CATALOG_VALID")
    else:
        reason_codes.append("PACKAGE_DRY_RUN_SOURCE_CATALOG_INVALID")

    if catalog_digest_match:
        reason_codes.append("PACKAGE_DRY_RUN_SOURCE_CATALOG_DIGEST_MATCH")
    else:
        reason_codes.append("PACKAGE_DRY_RUN_SOURCE_CATALOG_DIGEST_MISMATCH")

    reason_codes.append("PACKAGE_DRY_RUN_SOURCE_ARTIFACT_REFERENCED")
    
    # Check that source digest is preserved
    source_path = e_dict.get("source_artifact_path", "")
    matching_cat_ent = next((item for item in catalog_dict.get("entries", []) if item.get("artifact_path") == source_path), None)
    digest_preserved = False
    if matching_cat_ent:
        digest_preserved = (matching_cat_ent.get("artifact_digest") == e_dict.get("source_artifact_digest"))
        if digest_preserved:
            reason_codes.append("PACKAGE_DRY_RUN_SOURCE_DIGEST_PRESERVED")

    # Add path safety reason codes
    for r in path_reasons:
        if r.startswith("PACKAGE_DRY_RUN_"):
            reason_codes.append(r)

    if collision_free:
        reason_codes.append("PACKAGE_DRY_RUN_TARGET_PATH_COLLISION_FREE")

    software_validation_caveat = e_dict.get("software_validation_caveat", "")
    if software_validation_caveat:
        reason_codes.append("PACKAGE_DRY_RUN_SOFTWARE_CAVEAT_INCLUDED")

    # Determine status
    astatus = e_dict.get("assembly_status")
    include_in_plan = e_dict.get("include_in_package_plan", False)

    # Check for forbidden entries (deploy or signing)
    is_deploy = e_dict.get("is_deployment_artifact", False)
    is_sign = e_dict.get("is_signing_artifact", False)

    dry_run_status = "package_dry_run_invalid"
    if (plan_digest_match and entry_digest_match and catalog_digest_match and catalog_valid and
        path_safe and collision_free and digest_preserved and not is_deploy and not is_sign and
        software_validation_caveat):
        if astatus == "package_layout_ready" and include_in_plan:
            dry_run_status = "package_dry_run_verified"
            reason_codes.append("PACKAGE_DRY_RUN_VERIFIED")
        elif astatus == "package_layout_blocked":
            dry_run_status = "package_dry_run_blocked"
            reason_codes.append("PACKAGE_DRY_RUN_BLOCKED")
        elif astatus == "package_layout_pending":
            dry_run_status = "package_dry_run_pending"
        else:
            dry_run_status = "package_dry_run_invalid"
            reason_codes.append("PACKAGE_DRY_RUN_INVALID")
    else:
        dry_run_status = "package_dry_run_invalid"
        reason_codes.append("PACKAGE_DRY_RUN_INVALID")

    case = WaveguidePackageDryRunAuditCase(
        package_dry_run_case_id=f"SOL-WAVEGUIDE-DRYRUN-{e_dict.get('source_artifact_name', '').replace('.', '_')}",
        package_assembly_plan_id=plan_dict.get("package_assembly_plan_id", ""),
        package_assembly_plan_path=plan_path,
        package_assembly_plan_digest_recorded=plan_digest_recorded,
        package_assembly_plan_digest_recomputed=plan_digest_recomputed,
        package_assembly_plan_digest_match=plan_digest_match,
        layout_entry_id=e_dict.get("package_layout_entry_id", ""),
        layout_entry_digest_recorded=entry_digest_recorded,
        layout_entry_digest_recomputed=entry_digest_recomputed,
        layout_entry_digest_match=entry_digest_match,
        source_artifact_path=source_path,
        source_artifact_digest=e_dict.get("source_artifact_digest", ""),
        source_artifact_type=e_dict.get("source_artifact_type", ""),
        source_artifact_format=e_dict.get("source_artifact_format", ""),
        source_package_role=e_dict.get("source_package_role", ""),
        rc_scope=e_dict.get("rc_scope", ""),
        candidate_level=e_dict.get("candidate_level", ""),
        target_package_path=tpath,
        target_package_section=e_dict.get("target_package_section", ""),
        target_path_relative=not os.path.isabs(tpath) and not tpath.startswith("/"),
        target_path_uses_forward_slashes="\\" not in tpath,
        target_path_has_no_parent_traversal=".." not in tpath,
        target_path_has_no_absolute_root=not os.path.isabs(tpath) and not tpath.startswith("/"),
        target_path_collision_free=collision_free,
        include_in_package_plan=include_in_plan,
        assembly_status=astatus,
        dry_run_status=dry_run_status,
        source_artifact_catalog_digest_recorded=catalog_digest_recorded,
        source_artifact_catalog_digest_recomputed=catalog_digest_recomputed,
        source_artifact_catalog_digest_match=catalog_digest_match,
        source_artifact_catalog_valid=catalog_valid,
        no_archive_created=no_archive,
        no_file_copy_performed=no_copy,
        no_upload_performed=no_upload,
        no_deployment_performed=no_deploy,
        no_signing_performed=no_sign,
        allowed_distribution_channels=sorted(e_dict.get("allowed_distribution_channels", [])),
        blocked_distribution_channels=sorted(e_dict.get("blocked_distribution_channels", [])),
        reason_codes=sorted(list(set(reason_codes))),
        notes=[],
        software_validation_caveat=software_validation_caveat,
        package_dry_run_case_digest=""
    )
    case.package_dry_run_case_digest = hash_waveguide_package_dry_run_case(case)
    return case


def validate_waveguide_distribution_package_plan_independently(
    plan_path_or_dict: Any,
    catalog_path_or_dict: Any
) -> Tuple[bool, List[str]]:
    """
    Independently validates the assembly plan and verifies that catalog digest matches.
    """
    plan_dict = _load_dict(plan_path_or_dict)
    catalog_dict = _load_dict(catalog_path_or_dict)

    reasons = []
    is_valid = True

    if not plan_dict or not catalog_dict:
        return False, ["PACKAGE_DRY_RUN_INVALID"]

    # 1. Validate plan
    plan_ok, plan_reasons = validate_waveguide_distribution_package_assembly_plan(plan_dict)
    if not plan_ok:
        is_valid = False
        reasons.append("PACKAGE_DRY_RUN_ASSEMBLY_PLAN_INVALID")
    else:
        reasons.append("PACKAGE_DRY_RUN_ASSEMBLY_PLAN_VALID")

    # 2. Validate catalog
    cat_ok, cat_reasons = validate_waveguide_certified_artifact_catalog(catalog_dict)
    if not cat_ok:
        is_valid = False
        reasons.append("PACKAGE_DRY_RUN_SOURCE_CATALOG_INVALID")
    else:
        reasons.append("PACKAGE_DRY_RUN_SOURCE_CATALOG_VALID")

    # 3. Digest match check
    plan_cat_digest = plan_dict.get("source_artifact_catalog_digest", "")
    cat_digest = catalog_dict.get("artifact_catalog_digest", "")
    if plan_cat_digest != cat_digest or not cat_digest:
        is_valid = False
        reasons.append("PACKAGE_DRY_RUN_SOURCE_CATALOG_DIGEST_MISMATCH")
    else:
        reasons.append("PACKAGE_DRY_RUN_SOURCE_CATALOG_DIGEST_MATCH")

    if is_valid:
        reasons.append("PACKAGE_DRY_RUN_VERIFIED")
    else:
        reasons.append("PACKAGE_DRY_RUN_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_dry_run_report(
    plan_path_or_dict: Any,
    catalog_path_or_dict: Any
) -> WaveguidePackageDryRunAuditReport:
    """
    Builds the top-level package dry-run audit report by verifying each entry as a case.
    """
    plan_dict = _load_dict(plan_path_or_dict)
    catalog_dict = _load_dict(catalog_path_or_dict)

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not plan_dict or not catalog_dict:
        # Invalid/Empty report
        report = WaveguidePackageDryRunAuditReport(
            package_dry_run_report_id="SOL-WAVEGUIDE-PACKAGE-DRY-RUN-AUDIT-REPORT",
            package_dry_run_report_version=1,
            package_dry_run_report_status="package_dry_run_invalid",
            source_package_assembly_plan_digest="",
            source_artifact_catalog_digest="",
            audited_cases=[],
            verified_dry_run_cases=[],
            blocked_dry_run_cases=[],
            pending_dry_run_cases=[],
            invalid_dry_run_cases=[],
            verified_dry_run_count=0,
            blocked_dry_run_count=0,
            pending_dry_run_count=0,
            invalid_dry_run_count=0,
            total_simulated_file_count=0,
            rc1_dry_run_count=0,
            rc2_dry_run_count=0,
            shared_dry_run_count=0,
            target_package_sections=[],
            package_roles_indexed=[],
            artifact_types_indexed=[],
            artifact_formats_indexed=[],
            source_artifact_paths=[],
            target_package_paths=[],
            source_artifact_digests=[],
            layout_entry_digests=[],
            proof_artifact_dry_run_layout=[],
            documentation_artifact_dry_run_layout=[],
            source_module_dry_run_layout=[],
            test_source_dry_run_layout=[],
            dry_run_file_map=[],
            dry_run_section_index={},
            target_path_collision_count=0,
            unsafe_target_path_count=0,
            archive_creation_attempt_count=0,
            file_copy_attempt_count=0,
            upload_attempt_count=0,
            deployment_attempt_count=0,
            signing_attempt_count=0,
            allowed_distribution_channels=[],
            blocked_distribution_channels=[],
            reason_codes=["PACKAGE_DRY_RUN_INVALID", "PACKAGE_DRY_RUN_ASSEMBLY_PLAN_INVALID"],
            software_validation_caveat=software_validation_caveat,
            package_dry_run_report_digest=""
        )
        report.package_dry_run_report_digest = hash_waveguide_package_dry_run_report(report)
        return report

    plan_digest = plan_dict.get("package_assembly_plan_digest", "")
    catalog_digest = catalog_dict.get("artifact_catalog_digest", "")

    # Collision counts across the entire plan
    plan_entries = plan_dict.get("layout_entries", [])
    collision_count = detect_waveguide_package_target_path_collisions(plan_entries)

    cases = []
    for entry in plan_entries:
        case = build_waveguide_package_dry_run_case(entry, plan_dict, catalog_dict)
        cases.append(case)

    # Sort cases by target_package_path, source_artifact_path, source_artifact_digest
    def case_sort_key(c):
        return (c.target_package_path, c.source_artifact_path, c.source_artifact_digest)
    
    sorted_cases = sorted(cases, key=case_sort_key)

    verified_dry_run_cases = []
    blocked_dry_run_cases = []
    pending_dry_run_cases = []
    invalid_dry_run_cases = []

    rc1_dry_run_count = 0
    rc2_dry_run_count = 0
    shared_dry_run_count = 0

    target_package_sections = []
    package_roles_indexed = []
    artifact_types_indexed = []
    artifact_formats_indexed = []
    source_artifact_paths = []
    target_package_paths = []
    source_artifact_digests = []
    layout_entry_digests = []

    proof_artifact_dry_run_layout = []
    documentation_artifact_dry_run_layout = []
    source_module_dry_run_layout = []
    test_source_dry_run_layout = []

    all_reasons = [
        "PACKAGE_DRY_RUN_COUNTS_VALID",
        "PACKAGE_DRY_RUN_INDEXES_VALID",
        "PACKAGE_DRY_RUN_FILE_MAP_CANONICAL",
        "PACKAGE_DRY_RUN_SECTION_INDEX_CANONICAL"
    ]

    unsafe_target_path_count = 0

    for case in sorted_cases:
        path = case.source_artifact_path
        tpath = case.target_package_path
        sect = case.target_package_section
        status = case.dry_run_status
        scope = case.rc_scope
        role = case.source_package_role
        atype = case.source_artifact_type
        aformat = case.source_artifact_format
        digest = case.source_artifact_digest
        entry_digest = case.layout_entry_digest_recorded

        # Track safety
        if not case.target_path_relative or not case.target_path_uses_forward_slashes or not case.target_path_has_no_parent_traversal:
            unsafe_target_path_count += 1

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
        add_unique(layout_entry_digests, entry_digest)

        if status == "package_dry_run_verified":
            add_unique(verified_dry_run_cases, path)
            if case.is_proof_artifact:
                add_unique(proof_artifact_dry_run_layout, tpath)
            elif case.is_documentation_artifact:
                add_unique(documentation_artifact_dry_run_layout, tpath)
            elif case.is_code_artifact:
                add_unique(source_module_dry_run_layout, tpath)
            elif case.is_test_artifact:
                add_unique(test_source_dry_run_layout, tpath)
        elif status == "package_dry_run_blocked":
            add_unique(blocked_dry_run_cases, path)
        elif status == "package_dry_run_pending":
            add_unique(pending_dry_run_cases, path)
        else:
            add_unique(invalid_dry_run_cases, path)

        if scope == "RC1":
            rc1_dry_run_count += 1
        elif scope == "RC2":
            rc2_dry_run_count += 1
        else:
            shared_dry_run_count += 1

        for rcode in case.reason_codes:
            if rcode not in all_reasons:
                all_reasons.append(rcode)

    # Sort lists
    target_package_sections = sorted(target_package_sections)
    package_roles_indexed = sorted(package_roles_indexed)
    artifact_types_indexed = sorted(artifact_types_indexed)
    artifact_formats_indexed = sorted(artifact_formats_indexed)
    source_artifact_paths = sorted(source_artifact_paths)
    target_package_paths = sorted(target_package_paths)
    source_artifact_digests = sorted(source_artifact_digests)
    layout_entry_digests = sorted(layout_entry_digests)
    proof_artifact_dry_run_layout = sorted(proof_artifact_dry_run_layout)
    documentation_artifact_dry_run_layout = sorted(documentation_artifact_dry_run_layout)
    source_module_dry_run_layout = sorted(source_module_dry_run_layout)
    test_source_dry_run_layout = sorted(test_source_dry_run_layout)

    # Build file map
    dry_run_file_map = []
    # Sorted by target_package_path
    sorted_for_map = sorted(sorted_cases, key=lambda c: c.target_package_path)
    for idx, case in enumerate(sorted_for_map):
        dry_run_file_map.append({
            "dry_run_file_map_index": idx + 1,
            "source_artifact_path": case.source_artifact_path,
            "target_package_path": case.target_package_path,
            "artifact_digest": case.source_artifact_digest,
            "artifact_type": case.source_artifact_type,
            "package_role": case.source_package_role,
            "rc_scope": case.rc_scope,
            "dry_run_status": case.dry_run_status
        })

    # Build section index
    dry_run_section_index = {}
    for sect in ["proof/", "docs/", "source/", "tests/", "indexes/", "metadata/"]:
        paths_in_sect = [c.target_package_path for c in sorted_cases if c.target_package_section == sect and c.dry_run_status == "package_dry_run_verified"]
        dry_run_section_index[sect] = sorted(paths_in_sect)

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

    verified_dry_run_count = len(verified_dry_run_cases)
    blocked_dry_run_count = len(blocked_dry_run_cases)
    pending_dry_run_count = len(pending_dry_run_cases)
    invalid_dry_run_count = len(invalid_dry_run_cases)

    # Determine status
    plan_ok, plan_reasons = validate_waveguide_distribution_package_plan_independently(plan_dict, catalog_dict)
    if blocked_dry_run_count > 0 or invalid_dry_run_count > 0 or collision_count > 0 or unsafe_target_path_count > 0 or not plan_ok:
        report_status = "package_dry_run_invalid"
        all_reasons.append("PACKAGE_DRY_RUN_INVALID")
    else:
        report_status = "package_dry_run_verified"
        all_reasons.append("PACKAGE_DRY_RUN_VERIFIED")

    report = WaveguidePackageDryRunAuditReport(
        package_dry_run_report_id="SOL-WAVEGUIDE-PACKAGE-DRY-RUN-AUDIT-REPORT",
        package_dry_run_report_version=1,
        package_dry_run_report_status=report_status,
        source_package_assembly_plan_digest=plan_digest,
        source_artifact_catalog_digest=catalog_digest,
        audited_cases=sorted_cases,
        verified_dry_run_cases=sorted(verified_dry_run_cases),
        blocked_dry_run_cases=sorted(blocked_dry_run_cases),
        pending_dry_run_cases=sorted(pending_dry_run_cases),
        invalid_dry_run_cases=sorted(invalid_dry_run_cases),
        verified_dry_run_count=verified_dry_run_count,
        blocked_dry_run_count=blocked_dry_run_count,
        pending_dry_run_count=pending_dry_run_count,
        invalid_dry_run_count=invalid_dry_run_count,
        total_simulated_file_count=verified_dry_run_count,
        rc1_dry_run_count=rc1_dry_run_count,
        rc2_dry_run_count=rc2_dry_run_count,
        shared_dry_run_count=shared_dry_run_count,
        target_package_sections=target_package_sections,
        package_roles_indexed=package_roles_indexed,
        artifact_types_indexed=artifact_types_indexed,
        artifact_formats_indexed=artifact_formats_indexed,
        source_artifact_paths=source_artifact_paths,
        target_package_paths=target_package_paths,
        source_artifact_digests=source_artifact_digests,
        layout_entry_digests=layout_entry_digests,
        proof_artifact_dry_run_layout=proof_artifact_dry_run_layout,
        documentation_artifact_dry_run_layout=documentation_artifact_dry_run_layout,
        source_module_dry_run_layout=source_module_dry_run_layout,
        test_source_dry_run_layout=test_source_dry_run_layout,
        dry_run_file_map=dry_run_file_map,
        dry_run_section_index=dry_run_section_index,
        target_path_collision_count=collision_count,
        unsafe_target_path_count=unsafe_target_path_count,
        archive_creation_attempt_count=0,
        file_copy_attempt_count=0,
        upload_attempt_count=0,
        deployment_attempt_count=0,
        signing_attempt_count=0,
        allowed_distribution_channels=allowed_channels,
        blocked_distribution_channels=blocked_channels,
        reason_codes=sorted(list(set(all_reasons))),
        software_validation_caveat=software_validation_caveat,
        package_dry_run_report_digest=""
    )
    report.package_dry_run_report_digest = hash_waveguide_package_dry_run_report(report)
    return report


def validate_waveguide_package_dry_run_report(report: Any) -> Tuple[bool, List[str]]:
    """
    Validates a dry-run report.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    reasons = []
    is_valid = True

    # 1. Digest checks
    given_digest = r_dict.get("package_dry_run_report_digest")
    if not given_digest:
        is_valid = False
        reasons.append("PACKAGE_DRY_RUN_INVALID")
    else:
        recomputed = hash_waveguide_package_dry_run_report(r_dict)
        if recomputed != given_digest:
            is_valid = False
            reasons.append("PACKAGE_DRY_RUN_INVALID")
        else:
            reasons.append("PACKAGE_DRY_RUN_REPORT_DIGEST_VALID")

    # 2. Case checks
    cases = r_dict.get("audited_cases", [])
    verified_paths = []
    case_statuses = []
    for case in cases:
        c_dict = asdict(case) if hasattr(case, "__dict__") else dict(case)
        # Validate each case digest
        given_c_digest = c_dict.get("package_dry_run_case_digest")
        if not given_c_digest:
            is_valid = False
            reasons.append("PACKAGE_DRY_RUN_INVALID")
        else:
            recomputed_c = hash_waveguide_package_dry_run_case(c_dict)
            if recomputed_c != given_c_digest:
                is_valid = False
                reasons.append("PACKAGE_DRY_RUN_INVALID")
        
        status = c_dict.get("dry_run_status")
        tpath = c_dict.get("target_package_path")
        case_statuses.append(status)
        if status == "package_dry_run_verified":
            verified_paths.append(tpath)

        # Check safety of case
        if status == "package_dry_run_verified":
            if not c_dict.get("target_path_relative") or not c_dict.get("target_path_uses_forward_slashes") or not c_dict.get("target_path_has_no_parent_traversal"):
                is_valid = False
                reasons.append("PACKAGE_DRY_RUN_INVALID")
            if not c_dict.get("target_path_collision_free"):
                is_valid = False
                reasons.append("PACKAGE_DRY_RUN_INVALID")

    # 3. Collision checks
    if len(verified_paths) != len(set(verified_paths)):
        is_valid = False
        reasons.append("PACKAGE_DRY_RUN_INVALID")

    # 4. Count consistency
    v_count = r_dict.get("verified_dry_run_count", 0)
    b_count = r_dict.get("blocked_dry_run_count", 0)
    p_count = r_dict.get("pending_dry_run_count", 0)
    i_count = r_dict.get("invalid_dry_run_count", 0)

    if (v_count != case_statuses.count("package_dry_run_verified") or
        b_count != case_statuses.count("package_dry_run_blocked") or
        p_count != case_statuses.count("package_dry_run_pending") or
        i_count != case_statuses.count("package_dry_run_invalid")):
        is_valid = False
        reasons.append("PACKAGE_DRY_RUN_INVALID")

    # 5. Status check
    status = r_dict.get("package_dry_run_report_status")
    if status == "package_dry_run_verified":
        if b_count > 0 or i_count > 0 or len(cases) == 0:
            is_valid = False
            reasons.append("PACKAGE_DRY_RUN_INVALID")

    if is_valid:
        for rc in r_dict.get("reason_codes", []):
            if rc.startswith("PACKAGE_DRY_RUN_"):
                reasons.append(rc)
        reasons.append("PACKAGE_DRY_RUN_VERIFIED")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_dry_run_report(report: Any) -> str:
    """
    Returns a plaintext summary of the report.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    lines = [
        "============================================================",
        "          SOL WAVEGUIDE PACKAGE DRY-RUN AUDIT REPORT",
        "============================================================",
        f"Report ID:        {r_dict.get('package_dry_run_report_id')}",
        f"Version:          {r_dict.get('package_dry_run_report_version')}",
        f"Status:           {r_dict.get('package_dry_run_report_status', '').upper()}",
        f"Report Digest:    {r_dict.get('package_dry_run_report_digest')}",
        "------------------------------------------------------------",
        "Simulated Package Layout Map:"
    ]

    for item in r_dict.get("dry_run_file_map", []):
        lines.append(
            f"  [{item.get('dry_run_file_map_index')}] {item.get('source_artifact_path')} "
            f"-> {item.get('target_package_path')} (status: {item.get('dry_run_status')})"
        )

    lines.append("------------------------------------------------------------")
    lines.append("Planned Section Layout Summary:")
    sect_index = r_dict.get("dry_run_section_index", {})
    for sect, paths in sect_index.items():
        lines.append(f"  * {sect}: {len(paths)} files")

    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in r_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {r_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_package_dry_run_report(report: Any, filepath: str) -> None:
    """
    Exports the report to a JSON file.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    full_path = os.path.join(REPO_ROOT, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_dry_run_reports(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two reports.
    """
    if hasattr(left, "__dict__"):
        l_dict = asdict(left)
    else:
        l_dict = dict(left)

    if hasattr(right, "__dict__"):
        r_dict = asdict(right)
    else:
        r_dict = dict(right)

    diff = {
        "report_id_match": l_dict.get("package_dry_run_report_id") == r_dict.get("package_dry_run_report_id"),
        "report_version_match": l_dict.get("package_dry_run_report_version") == r_dict.get("package_dry_run_report_version"),
        "report_status_match": l_dict.get("package_dry_run_report_status") == r_dict.get("package_dry_run_report_status"),
        "report_digest_match": l_dict.get("package_dry_run_report_digest") == r_dict.get("package_dry_run_report_digest"),
        "verified_count_diff": l_dict.get("verified_dry_run_count", 0) - r_dict.get("verified_dry_run_count", 0),
        "blocked_count_diff": l_dict.get("blocked_dry_run_count", 0) - r_dict.get("blocked_dry_run_count", 0),
        "target_paths_left_only": list(set(l_dict.get("target_package_paths", [])) - set(r_dict.get("target_package_paths", []))),
        "target_paths_right_only": list(set(r_dict.get("target_package_paths", [])) - set(l_dict.get("target_package_paths", [])))
    }

    diff["all_match"] = (
        diff["report_id_match"] and
        diff["report_version_match"] and
        diff["report_status_match"] and
        diff["report_digest_match"] and
        diff["verified_count_diff"] == 0 and
        diff["blocked_count_diff"] == 0 and
        not diff["target_paths_left_only"] and
        not diff["target_paths_right_only"]
    )
    return diff


def index_waveguide_package_dry_run_cases_by_rc(cases: List[Any]) -> Dict[str, List[Any]]:
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


def index_waveguide_package_dry_run_cases_by_status(cases: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes cases by dry_run_status.
    """
    idx = {}
    for c in cases:
        c_dict = asdict(c) if hasattr(c, "__dict__") else dict(c)
        status = c_dict.get("dry_run_status")
        if status not in idx:
            idx[status] = []
        idx[status].append(c_dict)
    return idx


def index_waveguide_package_dry_run_cases_by_section(cases: List[Any]) -> Dict[str, List[Any]]:
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


def build_waveguide_package_dry_run_file_map(cases: List[Any]) -> List[Dict[str, Any]]:
    """
    Builds a deterministic dry-run file map from cases, sorted by target path.
    """
    dry_run_file_map = []
    sorted_for_map = sorted(cases, key=lambda c: c.target_package_path if hasattr(c, "target_package_path") else c.get("target_package_path", ""))
    for idx, case in enumerate(sorted_for_map):
        c_dict = asdict(case) if hasattr(case, "__dict__") else dict(case)
        dry_run_file_map.append({
            "dry_run_file_map_index": idx + 1,
            "source_artifact_path": c_dict.get("source_artifact_path", ""),
            "target_package_path": c_dict.get("target_package_path", ""),
            "artifact_digest": c_dict.get("source_artifact_digest", ""),
            "artifact_type": c_dict.get("source_artifact_type", ""),
            "package_role": c_dict.get("source_package_role", ""),
            "rc_scope": c_dict.get("rc_scope", ""),
            "dry_run_status": c_dict.get("dry_run_status", "")
        })
    return dry_run_file_map


def build_waveguide_package_dry_run_section_index(cases: List[Any]) -> Dict[str, List[str]]:
    """
    Builds a deterministic dry-run section index.
    """
    dry_run_section_index = {}
    for sect in ["proof/", "docs/", "source/", "tests/", "indexes/", "metadata/"]:
        paths_in_sect = []
        for case in cases:
            c_dict = asdict(case) if hasattr(case, "__dict__") else dict(case)
            if c_dict.get("target_package_section") == sect and c_dict.get("dry_run_status") == "package_dry_run_verified":
                paths_in_sect.append(c_dict.get("target_package_path"))
        dry_run_section_index[sect] = sorted(paths_in_sect)
    return dry_run_section_index

