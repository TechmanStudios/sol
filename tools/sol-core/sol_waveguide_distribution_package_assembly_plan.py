# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Distribution Package Assembly Plan.
Consumes the Certified Artifact Catalog and maps source artifacts into package layouts.
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
    REPO_ROOT,
    hash_file_contents
)
from sol_waveguide_certified_artifact_catalog import (
    validate_waveguide_certified_artifact_catalog,
    WaveguideCertifiedArtifactCatalog
)


@dataclass
class WaveguideDistributionPackageLayoutEntry:
    package_layout_entry_id: str
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
    include_in_package_plan: bool
    assembly_status: str  # package_layout_ready, package_layout_blocked, package_layout_pending, package_layout_invalid
    artifact_size_bytes: int
    allowed_distribution_channels: List[str]
    blocked_distribution_channels: List[str]
    is_required_for_distribution_package: bool
    is_proof_artifact: bool
    is_documentation_artifact: bool
    is_code_artifact: bool
    is_test_artifact: bool
    is_deployment_artifact: bool
    is_signing_artifact: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    package_layout_entry_digest: str = ""


@dataclass
class WaveguideDistributionPackageAssemblyPlan:
    package_assembly_plan_id: str
    package_assembly_plan_version: int
    package_assembly_plan_status: str  # package_plan_ready, package_plan_blocked, etc.
    source_artifact_catalog_digest: str
    planned_package_root: str
    layout_entries: List[WaveguideDistributionPackageLayoutEntry]
    ready_layout_entries: List[str]
    blocked_layout_entries: List[str]
    pending_layout_entries: List[str]
    invalid_layout_entries: List[str]
    ready_layout_count: int
    blocked_layout_count: int
    pending_layout_count: int
    invalid_layout_count: int
    total_planned_file_count: int
    rc1_layout_count: int
    rc2_layout_count: int
    shared_layout_count: int
    target_package_sections: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    artifact_formats_indexed: List[str]
    source_artifact_paths: List[str]
    target_package_paths: List[str]
    source_artifact_digests: List[str]
    proof_artifact_layout: List[str]
    documentation_artifact_layout: List[str]
    source_module_layout: List[str]
    test_source_layout: List[str]
    package_file_map: List[Dict[str, Any]]
    package_section_index: Dict[str, List[str]]
    allowed_distribution_channels: List[str]
    blocked_distribution_channels: List[str]
    reason_codes: List[str]
    software_validation_caveat: str
    package_assembly_plan_digest: str = ""


def hash_waveguide_distribution_package_layout_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized layout entry excluding the self-referential digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or a dataclass instance")

    e_dict_copy = dict(e_dict)
    e_dict_copy.pop("package_layout_entry_digest", None)
    return hash_data(e_dict_copy)


def hash_waveguide_distribution_package_assembly_plan(plan: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized package plan excluding the self-referential digest.
    """
    if hasattr(plan, "__dict__"):
        p_dict = asdict(plan)
    elif isinstance(plan, dict):
        p_dict = dict(plan)
    else:
        raise TypeError("plan must be a dictionary or a dataclass instance")

    p_dict_copy = dict(p_dict)
    p_dict_copy.pop("package_assembly_plan_digest", None)
    return hash_data(p_dict_copy)


def map_waveguide_artifact_to_package_path(source_path: str) -> Tuple[str, str]:
    """
    Maps a source artifact path to (target_package_path, target_package_section).
    e.g. docs/*.json -> proof/json/<filename>
         docs/*.md -> docs/<filename>
         tools/sol-core/*.py -> source/tools/sol-core/<filename>
         tests/*.py -> tests/<filename>
    """
    norm = normalize_to_repo_path(source_path)
    filename = os.path.basename(norm)
    if norm.startswith("docs/"):
        if norm.endswith(".json"):
            return f"proof/json/{filename}", "proof/"
        elif norm.endswith(".md"):
            return f"docs/{filename}", "docs/"
    elif norm.startswith("tools/sol-core/"):
        if norm.endswith(".py"):
            return f"source/tools/sol-core/{filename}", "source/"
    elif norm.startswith("tests/"):
        if norm.endswith(".py"):
            return f"tests/{filename}", "tests/"

    # Fallback rules
    if norm.endswith(".json"):
        return f"proof/json/{filename}", "proof/"
    elif norm.endswith(".md"):
        return f"docs/{filename}", "docs/"
    elif norm.endswith(".py"):
        return f"source/{filename}", "source/"

    return f"metadata/{filename}", "metadata/"


def build_waveguide_distribution_package_layout_entry(
    catalog_entry: Any,
    catalog_digest: str
) -> WaveguideDistributionPackageLayoutEntry:
    """
    Builds a package layout entry from a catalog entry.
    """
    if hasattr(catalog_entry, "__dict__"):
        c_dict = asdict(catalog_entry)
    elif isinstance(catalog_entry, dict):
        c_dict = dict(catalog_entry)
    else:
        raise TypeError("catalog_entry must be a dictionary or a dataclass instance")

    source_path = c_dict.get("artifact_path", "")
    target_path, target_section = map_waveguide_artifact_to_package_path(source_path)

    is_proof = c_dict.get("is_proof_artifact", False)
    is_docs = c_dict.get("is_documentation_artifact", False)
    
    # Differentiate code vs test in layout
    is_test = c_dict.get("package_role") == "test_source" or c_dict.get("artifact_type") == "pytest_suite"
    is_code = c_dict.get("package_role") == "implementation_source" or (c_dict.get("is_code_artifact", False) and not is_test)

    is_deploy = c_dict.get("is_deployment_artifact", False)
    is_sign = c_dict.get("is_signing_artifact", False)

    # Determine assembly status
    c_status = c_dict.get("distribution_status")
    if c_status == "artifact_distribution_blocked" or is_deploy or is_sign:
        assembly_status = "package_layout_blocked"
    elif c_status == "artifact_distribution_ready":
        assembly_status = "package_layout_ready"
    elif c_status == "artifact_distribution_pending":
        assembly_status = "package_layout_pending"
    else:
        assembly_status = "package_layout_invalid"

    include_in_plan = (assembly_status == "package_layout_ready")

    # Populate reason codes
    reason_codes = [
        "PACKAGE_PLAN_LAYOUT_ENTRY_CANONICAL",
        "PACKAGE_PLAN_SOURCE_ARTIFACT_REFERENCED",
        "PACKAGE_PLAN_DIGEST_PRESERVED",
        "PACKAGE_PLAN_TARGET_PATH_MAPPED",
        "PACKAGE_PLAN_TARGET_PATH_RELATIVE",
        "PACKAGE_PLAN_TARGET_PATH_SAFE",
        "PACKAGE_PLAN_NO_ARCHIVE_CREATED",
        "PACKAGE_PLAN_NO_UPLOAD_PERFORMED",
        "PACKAGE_PLAN_NO_DEPLOYMENT_PERFORMED",
        "PACKAGE_PLAN_NO_SIGNING_PERFORMED"
    ]

    if is_deploy:
        reason_codes.append("PACKAGE_PLAN_DEPLOYMENT_BLOCKED")
    if is_sign:
        reason_codes.append("PACKAGE_PLAN_EXTERNAL_SIGNING_BLOCKED")

    if is_proof:
        reason_codes.append("PACKAGE_PLAN_PROOF_LAYOUT_INCLUDED")
    if is_docs:
        reason_codes.append("PACKAGE_PLAN_DOCS_LAYOUT_INCLUDED")
    if is_code:
        reason_codes.append("PACKAGE_PLAN_SOURCE_LAYOUT_INCLUDED")
    if is_test:
        reason_codes.append("PACKAGE_PLAN_TEST_LAYOUT_INCLUDED")

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reason_codes.append("PACKAGE_PLAN_SOFTWARE_CAVEAT_INCLUDED")

    entry = WaveguideDistributionPackageLayoutEntry(
        package_layout_entry_id=f"SOL-WAVEGUIDE-LAYOUT-{c_dict.get('artifact_name', '').replace('.', '_')}",
        source_artifact_path=source_path,
        source_artifact_name=c_dict.get("artifact_name", ""),
        source_artifact_digest=c_dict.get("artifact_digest", ""),
        source_artifact_type=c_dict.get("artifact_type", ""),
        source_artifact_format=c_dict.get("artifact_format", ""),
        source_package_role=c_dict.get("package_role", ""),
        rc_scope=c_dict.get("rc_scope", ""),
        candidate_level=c_dict.get("candidate_level", ""),
        target_package_path=target_path,
        target_package_section=target_section,
        include_in_package_plan=include_in_plan,
        assembly_status=assembly_status,
        artifact_size_bytes=c_dict.get("artifact_size_bytes", 0),
        allowed_distribution_channels=sorted(c_dict.get("allowed_distribution_channels", [])),
        blocked_distribution_channels=sorted(c_dict.get("blocked_distribution_channels", [])),
        is_required_for_distribution_package=c_dict.get("is_required_for_distribution_package", False),
        is_proof_artifact=is_proof,
        is_documentation_artifact=is_docs,
        is_code_artifact=is_code,
        is_test_artifact=is_test,
        is_deployment_artifact=is_deploy,
        is_signing_artifact=is_sign,
        reason_codes=sorted(list(set(reason_codes))),
        notes=[],
        software_validation_caveat=software_validation_caveat,
        package_layout_entry_digest=""
    )
    entry.package_layout_entry_digest = hash_waveguide_distribution_package_layout_entry(entry)
    return entry


def validate_waveguide_distribution_package_layout_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Validates a layout entry.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or a dataclass instance")

    reasons = []
    is_valid = True

    # 1. Presence checks
    spath = e_dict.get("source_artifact_path")
    sdigest = e_dict.get("source_artifact_digest")
    stype = e_dict.get("source_artifact_type")
    sformat = e_dict.get("source_artifact_format")
    srole = e_dict.get("source_package_role")
    scope = e_dict.get("rc_scope")
    tpath = e_dict.get("target_package_path")
    tsection = e_dict.get("target_package_section")
    astatus = e_dict.get("assembly_status")
    caveat = e_dict.get("software_validation_caveat")

    if (not spath or not stype or not sformat or not srole or not scope or 
        not tpath or not tsection or not astatus or not caveat):
        is_valid = False
        reasons.append("PACKAGE_PLAN_INVALID")

    # Catalog digest check - digest is required for ready artifacts
    if astatus == "package_layout_ready" and not sdigest:
        is_valid = False
        reasons.append("PACKAGE_PLAN_INVALID")

    # 2. Path safety rules
    if tpath:
        # Must be relative, use /, not start with /, not contain ..
        if (os.path.isabs(tpath) or tpath.startswith("/") or ".." in tpath or "\\" in tpath):
            is_valid = False
            reasons.append("PACKAGE_PLAN_INVALID")

    # 3. Digest check
    given_digest = e_dict.get("package_layout_entry_digest")
    if given_digest:
        recomputed = hash_waveguide_distribution_package_layout_entry(e_dict)
        if recomputed != given_digest:
            is_valid = False
            reasons.append("PACKAGE_PLAN_INVALID")
        else:
            reasons.append("PACKAGE_PLAN_LAYOUT_ENTRY_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("PACKAGE_PLAN_INVALID")

    # 4. Ready rules
    if astatus == "package_layout_ready":
        if not e_dict.get("include_in_package_plan"):
            is_valid = False
            reasons.append("PACKAGE_PLAN_INVALID")
        if e_dict.get("is_deployment_artifact") or e_dict.get("is_signing_artifact"):
            is_valid = False
            reasons.append("PACKAGE_PLAN_INVALID")
        
        # Verify no upload/deployment channels are allowed
        allowed = e_dict.get("allowed_distribution_channels", [])
        if "production_deployment" in allowed or "external_key_signing" in allowed:
            is_valid = False
            reasons.append("PACKAGE_PLAN_INVALID")

    if is_valid:
        for rc in e_dict.get("reason_codes", []):
            if rc.startswith("PACKAGE_PLAN_"):
                reasons.append(rc)
        reasons.append("PACKAGE_PLAN_LAYOUT_ENTRY_CANONICAL")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_distribution_package_assembly_plan(
    catalog_path_or_dict: Any
) -> WaveguideDistributionPackageAssemblyPlan:
    """
    Builds a deterministic assembly plan from a Certified Artifact Catalog.
    """
    catalog_dict = None
    load_failed = False

    if isinstance(catalog_path_or_dict, str):
        path = normalize_to_repo_path(catalog_path_or_dict)
        full_path = os.path.join(REPO_ROOT, path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    catalog_dict = json.load(f)
            except Exception:
                load_failed = True
        else:
            load_failed = True
    elif hasattr(catalog_path_or_dict, "__dict__"):
        catalog_dict = asdict(catalog_path_or_dict)
    elif isinstance(catalog_path_or_dict, dict):
        catalog_dict = dict(catalog_path_or_dict)
    else:
        load_failed = True

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if load_failed or not catalog_dict:
        # Build empty/invalid plan
        plan = WaveguideDistributionPackageAssemblyPlan(
            package_assembly_plan_id="SOL-WAVEGUIDE-DISTRIBUTION-PACKAGE-ASSEMBLY-PLAN",
            package_assembly_plan_version=1,
            package_assembly_plan_status="package_plan_invalid",
            source_artifact_catalog_digest="",
            planned_package_root="package/",
            layout_entries=[],
            ready_layout_entries=[],
            blocked_layout_entries=[],
            pending_layout_entries=[],
            invalid_layout_entries=[],
            ready_layout_count=0,
            blocked_layout_count=0,
            pending_layout_count=0,
            invalid_layout_count=0,
            total_planned_file_count=0,
            rc1_layout_count=0,
            rc2_layout_count=0,
            shared_layout_count=0,
            target_package_sections=[],
            package_roles_indexed=[],
            artifact_types_indexed=[],
            artifact_formats_indexed=[],
            source_artifact_paths=[],
            target_package_paths=[],
            source_artifact_digests=[],
            proof_artifact_layout=[],
            documentation_artifact_layout=[],
            source_module_layout=[],
            test_source_layout=[],
            package_file_map=[],
            package_section_index={},
            allowed_distribution_channels=[],
            blocked_distribution_channels=[],
            reason_codes=["PACKAGE_PLAN_INVALID", "PACKAGE_PLAN_SOURCE_CATALOG_INVALID"],
            software_validation_caveat=software_validation_caveat,
            package_assembly_plan_digest=""
        )
        plan.package_assembly_plan_digest = hash_waveguide_distribution_package_assembly_plan(plan)
        return plan

    catalog_digest = catalog_dict.get("artifact_catalog_digest", "")

    # Validate catalog using existing validator
    cat_ok, cat_reasons = validate_waveguide_certified_artifact_catalog(catalog_dict)

    # Convert inventory entries into layout entries
    entries_list = catalog_dict.get("entries", [])
    layout_entries = []
    for cent in entries_list:
        entry = build_waveguide_distribution_package_layout_entry(cent, catalog_digest)
        layout_entries.append(entry)

    # Sort layout entries deterministically by target_package_path, source_artifact_path, source_artifact_digest
    def layout_sort_key(e):
        return (e.target_package_path, e.source_artifact_path, e.source_artifact_digest)
    
    sorted_entries = sorted(layout_entries, key=layout_sort_key)

    ready_layout_entries = []
    blocked_layout_entries = []
    pending_layout_entries = []
    invalid_layout_entries = []

    rc1_layout_count = 0
    rc2_layout_count = 0
    shared_layout_count = 0

    target_package_sections = []
    package_roles_indexed = []
    artifact_types_indexed = []
    artifact_formats_indexed = []
    source_artifact_paths = []
    target_package_paths = []
    source_artifact_digests = []

    proof_artifact_layout = []
    documentation_artifact_layout = []
    source_module_layout = []
    test_source_layout = []

    all_reasons = [
        "PACKAGE_PLAN_COUNTS_VALID",
        "PACKAGE_PLAN_INDEXES_VALID",
        "PACKAGE_PLAN_FILE_MAP_CANONICAL",
        "PACKAGE_PLAN_SECTION_INDEX_CANONICAL"
    ]

    if cat_ok:
        all_reasons.append("PACKAGE_PLAN_SOURCE_CATALOG_VALID")
    else:
        all_reasons.append("PACKAGE_PLAN_SOURCE_CATALOG_INVALID")

    def add_unique(lst, val):
        if val and val not in lst:
            lst.append(val)

    # Group and count layout entries
    for entry in sorted_entries:
        path = entry.source_artifact_path
        tpath = entry.target_package_path
        section = entry.target_package_section
        status = entry.assembly_status
        scope = entry.rc_scope
        role = entry.source_package_role
        atype = entry.source_artifact_type
        aformat = entry.source_artifact_format
        digest = entry.source_artifact_digest

        add_unique(target_package_sections, section)
        add_unique(package_roles_indexed, role)
        add_unique(artifact_types_indexed, atype)
        add_unique(artifact_formats_indexed, aformat)
        add_unique(source_artifact_paths, path)
        add_unique(target_package_paths, tpath)
        add_unique(source_artifact_digests, digest)

        if status == "package_layout_ready":
            add_unique(ready_layout_entries, path)
            if entry.is_proof_artifact:
                add_unique(proof_artifact_layout, tpath)
            elif entry.is_documentation_artifact:
                add_unique(documentation_artifact_layout, tpath)
            elif entry.is_code_artifact:
                add_unique(source_module_layout, tpath)
            elif entry.is_test_artifact:
                add_unique(test_source_layout, tpath)
        elif status == "package_layout_blocked":
            add_unique(blocked_layout_entries, path)
        elif status == "package_layout_pending":
            add_unique(pending_layout_entries, path)
        else:
            add_unique(invalid_layout_entries, path)

        if scope == "RC1":
            rc1_layout_count += 1
        elif scope == "RC2":
            rc2_layout_count += 1
        else:
            shared_layout_count += 1

        for code in entry.reason_codes:
            if code not in all_reasons:
                all_reasons.append(code)

    # Sorting all index lists
    target_package_sections = sorted(target_package_sections)
    package_roles_indexed = sorted(package_roles_indexed)
    artifact_types_indexed = sorted(artifact_types_indexed)
    artifact_formats_indexed = sorted(artifact_formats_indexed)
    source_artifact_paths = sorted(source_artifact_paths)
    target_package_paths = sorted(target_package_paths)
    source_artifact_digests = sorted(source_artifact_digests)
    proof_artifact_layout = sorted(proof_artifact_layout)
    documentation_artifact_layout = sorted(documentation_artifact_layout)
    source_module_layout = sorted(source_module_layout)
    test_source_layout = sorted(test_source_layout)

    # Build package file map
    package_file_map = []
    # File map sorted by target_package_path
    sorted_for_map = sorted(sorted_entries, key=lambda e: e.target_package_path)
    for idx, entry in enumerate(sorted_for_map):
        package_file_map.append({
            "file_map_index": idx + 1,
            "source_artifact_path": entry.source_artifact_path,
            "target_package_path": entry.target_package_path,
            "artifact_digest": entry.source_artifact_digest,
            "artifact_type": entry.source_artifact_type,
            "package_role": entry.source_package_role,
            "rc_scope": entry.rc_scope
        })

    # Build section index
    package_section_index = {}
    for sect in ["proof/", "docs/", "source/", "tests/", "indexes/", "metadata/"]:
        # Find all target paths in this section
        paths_in_sect = [e.target_package_path for e in sorted_entries if e.target_package_section == sect]
        package_section_index[sect] = sorted(paths_in_sect)

    # Allowed / blocked channels
    allowed_distribution_channels = [
        "artifact_catalog_publication",
        "documentation_publication",
        "internal_distribution"
    ]
    blocked_distribution_channels = [
        "external_key_signing",
        "legal_certification_claim",
        "production_deployment",
        "quantum_hardware_certification"
    ]

    ready_layout_count = len(ready_layout_entries)
    blocked_layout_count = len(blocked_layout_entries)
    pending_layout_count = len(pending_layout_entries)
    invalid_layout_count = len(invalid_layout_entries)

    # Determine plan status
    # A plan is ready if catalog is valid, all entries are ready, and no blocked or invalid entries exist
    # (Pending entries are acceptable for catalogs that are pending, but for a final plan they should ideally be ready).
    if blocked_layout_count > 0 or invalid_layout_count > 0 or not cat_ok:
        plan_status = "package_plan_invalid"
        all_reasons.append("PACKAGE_PLAN_INVALID")
    else:
        plan_status = "package_plan_ready"
        all_reasons.append("PACKAGE_PLAN_READY")

    plan = WaveguideDistributionPackageAssemblyPlan(
        package_assembly_plan_id="SOL-WAVEGUIDE-DISTRIBUTION-PACKAGE-ASSEMBLY-PLAN",
        package_assembly_plan_version=1,
        package_assembly_plan_status=plan_status,
        source_artifact_catalog_digest=catalog_digest,
        planned_package_root="package/",
        layout_entries=sorted_entries,
        ready_layout_entries=sorted(ready_layout_entries),
        blocked_layout_entries=sorted(blocked_layout_entries),
        pending_layout_entries=sorted(pending_layout_entries),
        invalid_layout_entries=sorted(invalid_layout_entries),
        ready_layout_count=ready_layout_count,
        blocked_layout_count=blocked_layout_count,
        pending_layout_count=pending_layout_count,
        invalid_layout_count=invalid_layout_count,
        total_planned_file_count=ready_layout_count,
        rc1_layout_count=rc1_layout_count,
        rc2_layout_count=rc2_layout_count,
        shared_layout_count=shared_layout_count,
        target_package_sections=target_package_sections,
        package_roles_indexed=package_roles_indexed,
        artifact_types_indexed=artifact_types_indexed,
        artifact_formats_indexed=artifact_formats_indexed,
        source_artifact_paths=source_artifact_paths,
        target_package_paths=target_package_paths,
        source_artifact_digests=source_artifact_digests,
        proof_artifact_layout=proof_artifact_layout,
        documentation_artifact_layout=documentation_artifact_layout,
        source_module_layout=source_module_layout,
        test_source_layout=test_source_layout,
        package_file_map=package_file_map,
        package_section_index=package_section_index,
        allowed_distribution_channels=allowed_distribution_channels,
        blocked_distribution_channels=blocked_distribution_channels,
        reason_codes=sorted(list(set(all_reasons))),
        software_validation_caveat=software_validation_caveat,
        package_assembly_plan_digest=""
    )
    plan.package_assembly_plan_digest = hash_waveguide_distribution_package_assembly_plan(plan)
    return plan


def validate_waveguide_distribution_package_assembly_plan(plan: Any) -> Tuple[bool, List[str]]:
    """
    Validates a package assembly plan.
    """
    if hasattr(plan, "__dict__"):
        p_dict = asdict(plan)
    elif isinstance(plan, dict):
        p_dict = dict(plan)
    else:
        raise TypeError("plan must be a dictionary or a dataclass instance")

    reasons = []
    is_valid = True

    # 1. Digest checks
    given_digest = p_dict.get("package_assembly_plan_digest")
    if not given_digest:
        is_valid = False
        reasons.append("PACKAGE_PLAN_INVALID")
    else:
        recomputed = hash_waveguide_distribution_package_assembly_plan(p_dict)
        if recomputed != given_digest:
            is_valid = False
            reasons.append("PACKAGE_PLAN_INVALID")
        else:
            reasons.append("PACKAGE_PLAN_DIGEST_VALID")

    # 2. Entries validation
    entries = p_dict.get("layout_entries", [])
    entry_statuses = []
    target_paths = []
    for entry in entries:
        ok, ent_reasons = validate_waveguide_distribution_package_layout_entry(entry)
        if not ok:
            is_valid = False
            reasons.append("PACKAGE_PLAN_INVALID")

        # Track targets and statuses
        if isinstance(entry, dict):
            status = entry.get("assembly_status")
            tpath = entry.get("target_package_path")
        else:
            status = entry.assembly_status
            tpath = entry.target_package_path

        entry_statuses.append(status)
        if status == "package_layout_ready":
            target_paths.append(tpath)

    # 3. Path collision checks
    if len(target_paths) != len(set(target_paths)):
        is_valid = False
        reasons.append("PACKAGE_PLAN_INVALID")

    # 4. Check count consistency
    ready_count = p_dict.get("ready_layout_count", 0)
    blocked_count = p_dict.get("blocked_layout_count", 0)
    pending_count = p_dict.get("pending_layout_count", 0)
    invalid_count = p_dict.get("invalid_layout_count", 0)

    if (ready_count != entry_statuses.count("package_layout_ready") or
        blocked_count != entry_statuses.count("package_layout_blocked") or
        pending_count != entry_statuses.count("package_layout_pending") or
        invalid_count != entry_statuses.count("package_layout_invalid")):
        is_valid = False
        reasons.append("PACKAGE_PLAN_INVALID")

    # 5. Status rules
    plan_status = p_dict.get("package_assembly_plan_status")
    if plan_status == "package_plan_ready":
        if blocked_count > 0 or invalid_count > 0 or len(entries) == 0:
            is_valid = False
            reasons.append("PACKAGE_PLAN_INVALID")

    if is_valid:
        for rc in p_dict.get("reason_codes", []):
            if rc.startswith("PACKAGE_PLAN_"):
                reasons.append(rc)
        reasons.append("PACKAGE_PLAN_READY")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_distribution_package_assembly_plan(plan: Any) -> str:
    """
    Returns a plaintext summary of the assembly plan.
    """
    if hasattr(plan, "__dict__"):
        p_dict = asdict(plan)
    elif isinstance(plan, dict):
        p_dict = dict(plan)
    else:
        raise TypeError("plan must be a dictionary or a dataclass instance")

    lines = [
        "============================================================",
        "        SOL WAVEGUIDE DISTRIBUTION PACKAGE ASSEMBLY PLAN",
        "============================================================",
        f"Plan ID:          {p_dict.get('package_assembly_plan_id')}",
        f"Version:          {p_dict.get('package_assembly_plan_version')}",
        f"Status:           {p_dict.get('package_assembly_plan_status', '').upper()}",
        f"Plan Digest:      {p_dict.get('package_assembly_plan_digest')}",
        "------------------------------------------------------------",
        "Layout Path Mapping Summary:"
    ]

    for item in p_dict.get("package_file_map", []):
        lines.append(
            f"  [{item.get('file_map_index')}] {item.get('source_artifact_path')} "
            f"-> {item.get('target_package_path')} ({item.get('rc_scope')})"
        )

    lines.append("------------------------------------------------------------")
    lines.append("Planned Section Layout Summary:")
    sect_index = p_dict.get("package_section_index", {})
    for sect, paths in sect_index.items():
        lines.append(f"  * {sect}: {len(paths)} files")

    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in p_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {p_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_distribution_package_assembly_plan(plan: Any, filepath: str) -> None:
    """
    Exports the plan to a JSON file.
    """
    if hasattr(plan, "__dict__"):
        p_dict = asdict(plan)
    elif isinstance(plan, dict):
        p_dict = dict(plan)
    else:
        raise TypeError("plan must be a dictionary or a dataclass instance")

    full_path = os.path.join(REPO_ROOT, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(p_dict, f, indent=4, sort_keys=True)


def compare_waveguide_distribution_package_assembly_plans(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two plans and returns differences.
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
        "plan_id_match": l_dict.get("package_assembly_plan_id") == r_dict.get("package_assembly_plan_id"),
        "plan_version_match": l_dict.get("package_assembly_plan_version") == r_dict.get("package_assembly_plan_version"),
        "plan_status_match": l_dict.get("package_assembly_plan_status") == r_dict.get("package_assembly_plan_status"),
        "plan_digest_match": l_dict.get("package_assembly_plan_digest") == r_dict.get("package_assembly_plan_digest"),
        "ready_count_diff": l_dict.get("ready_layout_count", 0) - r_dict.get("ready_layout_count", 0),
        "blocked_count_diff": l_dict.get("blocked_layout_count", 0) - r_dict.get("blocked_layout_count", 0),
        "target_paths_left_only": list(set(l_dict.get("target_package_paths", [])) - set(r_dict.get("target_package_paths", []))),
        "target_paths_right_only": list(set(r_dict.get("target_package_paths", [])) - set(l_dict.get("target_package_paths", [])))
    }

    diff["all_match"] = (
        diff["plan_id_match"] and
        diff["plan_version_match"] and
        diff["plan_status_match"] and
        diff["plan_digest_match"] and
        diff["ready_count_diff"] == 0 and
        diff["blocked_count_diff"] == 0 and
        not diff["target_paths_left_only"] and
        not diff["target_paths_right_only"]
    )
    return diff


def index_waveguide_package_layout_entries_by_rc(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes layout entries by rc_scope.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        scope = e_dict.get("rc_scope", "Shared")
        if scope not in idx:
            idx[scope] = []
        idx[scope].append(e_dict)
    return idx


def index_waveguide_package_layout_entries_by_section(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes layout entries by target_package_section.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        sect = e_dict.get("target_package_section")
        if sect not in idx:
            idx[sect] = []
        idx[sect].append(e_dict)
    return idx


def index_waveguide_package_layout_entries_by_role(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes layout entries by source_package_role.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        role = e_dict.get("source_package_role")
        if role not in idx:
            idx[role] = []
        idx[role].append(e_dict)
    return idx


def build_waveguide_package_file_map(entries: List[Any]) -> List[Dict[str, Any]]:
    """
    Builds a sorted package file map list.
    """
    sorted_entries = sorted(entries, key=lambda e: e.target_package_path if hasattr(e, "target_package_path") else e.get("target_package_path", ""))
    file_map = []
    for idx, e in enumerate(sorted_entries):
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        file_map.append({
            "file_map_index": idx + 1,
            "source_artifact_path": e_dict.get("source_artifact_path"),
            "target_package_path": e_dict.get("target_package_path"),
            "artifact_digest": e_dict.get("source_artifact_digest"),
            "artifact_type": e_dict.get("source_artifact_type"),
            "package_role": e_dict.get("source_package_role"),
            "rc_scope": e_dict.get("rc_scope")
        })
    return file_map


def build_waveguide_package_section_index(entries: List[Any]) -> Dict[str, List[str]]:
    """
    Builds a section index structure.
    """
    sorted_entries = sorted(entries, key=lambda e: e.target_package_path if hasattr(e, "target_package_path") else e.get("target_package_path", ""))
    sect_index = {sect: [] for sect in ["proof/", "docs/", "source/", "tests/", "indexes/", "metadata/"]}
    for e in sorted_entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        sect = e_dict.get("target_package_section")
        tpath = e_dict.get("target_package_path")
        if sect in sect_index:
            sect_index[sect].append(tpath)
    return sect_index
