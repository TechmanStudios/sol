# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Certified Artifact Catalog / Distribution Package Index.
Consumes the Distribution Readiness Audit Report and catalogues repository files
safe for inclusion in a distribution package.
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
from sol_waveguide_publication_manifest_validator import (
    validate_waveguide_distribution_readiness_audit_report,
    WaveguideDistributionReadinessAuditReport,
    WaveguideDistributionReadinessAuditCase
)


@dataclass
class WaveguideCertifiedArtifactCatalogEntry:
    artifact_catalog_entry_id: str
    artifact_path: str
    artifact_name: str
    artifact_type: str  # json_proof_capsule, markdown_documentation, python_module, pytest_suite, release_manifest, audit_report, certification_bundle, registry_index, documentation_index
    artifact_format: str  # json, markdown, python, text
    rc_scope: str  # RC1, RC2, Shared
    candidate_level: str  # Foundation, Governed Execution Stack, Shared
    package_role: str  # release_governance_proof, compiler_governance_proof, audit_verification_proof, publication_readiness_proof, distribution_readiness_proof, implementation_source, test_source, documentation
    distribution_status: str  # artifact_distribution_ready, artifact_distribution_blocked, etc.
    artifact_digest: str
    artifact_size_bytes: int
    source_distribution_audit_report_digest: str
    source_publication_manifest_digest: str
    source_audit_registry_digest: str
    related_rc_ids: List[str]
    related_bundle_digests: List[str]
    related_audit_report_digests: List[str]
    related_audit_case_digests: List[str]
    allowed_distribution_channels: List[str]
    blocked_distribution_channels: List[str]
    is_required_for_distribution_package: bool
    is_proof_artifact: bool
    is_documentation_artifact: bool
    is_code_artifact: bool
    is_deployment_artifact: bool
    is_signing_artifact: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    artifact_catalog_entry_digest: str = ""


@dataclass
class WaveguideCertifiedArtifactCatalog:
    artifact_catalog_id: str
    artifact_catalog_version: int
    artifact_catalog_status: str  # artifact_catalog_valid, etc.
    source_distribution_audit_report_digest: str
    source_publication_manifest_digest: str
    source_audit_registry_digest: str
    entries: List[WaveguideCertifiedArtifactCatalogEntry]
    distribution_ready_artifacts: List[str]
    blocked_artifacts: List[str]
    pending_artifacts: List[str]
    invalid_artifacts: List[str]
    distribution_ready_artifact_count: int
    blocked_artifact_count: int
    pending_artifact_count: int
    invalid_artifact_count: int
    rc1_artifact_count: int
    rc2_artifact_count: int
    shared_artifact_count: int
    artifact_types_indexed: List[str]
    artifact_formats_indexed: List[str]
    package_roles_indexed: List[str]
    rc_scopes_indexed: List[str]
    artifact_paths_indexed: List[str]
    artifact_digests_indexed: List[str]
    documentation_artifact_paths: List[str]
    proof_artifact_paths: List[str]
    code_artifact_paths: List[str]
    test_artifact_paths: List[str]
    distribution_package_inventory: List[Dict[str, Any]]
    allowed_distribution_channels: List[str]
    blocked_distribution_channels: List[str]
    reason_codes: List[str]
    software_validation_caveat: str
    artifact_catalog_digest: str = ""


def hash_waveguide_certified_artifact_catalog_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation
    excluding the self-referential artifact_catalog_entry_digest field.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or a dataclass instance")

    e_dict_copy = dict(e_dict)
    e_dict_copy.pop("artifact_catalog_entry_digest", None)
    return hash_data(e_dict_copy)


def hash_waveguide_certified_artifact_catalog(catalog: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation
    excluding the self-referential artifact_catalog_digest field.
    """
    if hasattr(catalog, "__dict__"):
        c_dict = asdict(catalog)
    elif isinstance(catalog, dict):
        c_dict = dict(catalog)
    else:
        raise TypeError("catalog must be a dictionary or a dataclass instance")

    c_dict_copy = dict(c_dict)
    c_dict_copy.pop("artifact_catalog_digest", None)
    return hash_data(c_dict_copy)


def compute_waveguide_catalog_artifact_digest(artifact_path: str) -> str:
    """
    Recomputes the file digest of a local repository file using standard hash_file_contents.
    """
    normalized = normalize_to_repo_path(artifact_path)
    full_path = os.path.join(REPO_ROOT, normalized)
    if normalized and os.path.isfile(full_path):
        return hash_file_contents(full_path)
    return ""


def build_waveguide_certified_artifact_catalog_entry(
    artifact_path: str,
    report_path_or_dict: Any,
    rc_scope: str = "Shared"
) -> WaveguideCertifiedArtifactCatalogEntry:
    """
    Builds a deterministic artifact catalog entry for a file in the repository.
    """
    # 1. Resolve source report digests
    report_dict = None
    if isinstance(report_path_or_dict, str):
        path = normalize_to_repo_path(report_path_or_dict)
        full_path = os.path.join(REPO_ROOT, path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    report_dict = json.load(f)
            except Exception:
                pass
    elif hasattr(report_path_or_dict, "__dict__"):
        report_dict = asdict(report_path_or_dict)
    elif isinstance(report_path_or_dict, dict):
        report_dict = dict(report_path_or_dict)

    if not report_dict:
        report_dict = {}

    report_digest = report_dict.get("distribution_audit_report_digest", "")
    manifest_digest = report_dict.get("source_publication_manifest_digest", "")
    registry_digest = report_dict.get("source_audit_registry_digest", "")

    # 2. Extract nested case info if matching scope
    related_rc_ids = []
    related_bundle_digests = []
    related_audit_report_digests = []
    related_audit_case_digests = []

    cases = report_dict.get("audited_cases", [])
    for case in cases:
        c_rc = case.get("rc_id", "")
        if c_rc:
            if rc_scope == "Shared" or rc_scope in c_rc:
                related_rc_ids.append(c_rc)
                related_bundle_digests.append(case.get("certification_bundle_digest", ""))
                related_audit_report_digests.append(case.get("audit_report_digest", ""))
                related_audit_case_digests.append(case.get("audit_case_digest", ""))

    related_rc_ids = sorted(list(set(related_rc_ids)))
    related_bundle_digests = sorted(list(set(filter(None, related_bundle_digests))))
    related_audit_report_digests = sorted(list(set(filter(None, related_audit_report_digests))))
    related_audit_case_digests = sorted(list(set(filter(None, related_audit_case_digests))))

    # 3. Determine properties from file path/name
    norm_path = normalize_to_repo_path(artifact_path)
    full_artifact_path = os.path.join(REPO_ROOT, norm_path)
    name = os.path.basename(norm_path)

    # Type & Format classifications
    is_proof = False
    is_documentation = False
    is_code = False
    is_deployment = False
    is_signing = False

    reason_codes = ["ARTIFACT_CATALOG_ENTRY_CANONICAL"]

    # Blocked channel definitions
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

    if norm_path.endswith(".json"):
        artifact_format = "json"
        is_proof = True
        reason_codes.append("ARTIFACT_CATALOG_JSON_PROOF_INCLUDED")
        if "_MANIFEST" in name or "_manifest" in name:
            artifact_type = "release_manifest"
            package_role = "release_governance_proof"
        elif "_RECORD" in name:
            artifact_type = "json_proof_capsule"
            package_role = "release_governance_proof"
        elif "_COURT" in name or "_VERDICT" in name:
            artifact_type = "json_proof_capsule"
            package_role = "release_governance_proof"
        elif "_REGISTRY" in name:
            artifact_type = "release_manifest"
            package_role = "release_governance_proof"
        elif "_RESOLVER" in name:
            artifact_type = "release_manifest"
            package_role = "compiler_governance_proof"
        elif "_BUNDLE" in name:
            artifact_type = "certification_bundle"
            package_role = "release_governance_proof"
        elif "_AUDIT_REPORT" in name:
            artifact_type = "audit_report"
            if "DISTRIBUTION" in name:
                package_role = "distribution_readiness_proof"
            else:
                package_role = "audit_verification_proof"
        elif "_INDEX" in name:
            artifact_type = "registry_index"
            package_role = "publication_readiness_proof"
        elif "_CATALOG" in name:
            artifact_type = "documentation_index"
            package_role = "distribution_readiness_proof"
            is_proof = False
            is_documentation = True
        else:
            artifact_type = "json_proof_capsule"
            package_role = "release_governance_proof"

    elif norm_path.endswith(".md"):
        artifact_format = "markdown"
        artifact_type = "markdown_documentation"
        package_role = "documentation"
        is_documentation = True
        reason_codes.append("ARTIFACT_CATALOG_MARKDOWN_DOC_INCLUDED")

    elif norm_path.endswith(".py"):
        artifact_format = "python"
        is_code = True
        if "tools/" in norm_path:
            artifact_type = "python_module"
            package_role = "implementation_source"
            reason_codes.append("ARTIFACT_CATALOG_SOURCE_MODULE_INCLUDED")
        else:
            artifact_type = "pytest_suite"
            package_role = "test_source"
            reason_codes.append("ARTIFACT_CATALOG_TEST_SOURCE_INCLUDED")

    else:
        artifact_format = "text"
        artifact_type = "documentation_index"
        package_role = "documentation"
        is_documentation = True

    # 4. Check deployment or signing classifications to block them
    # Ensure no deployment-related files (like key files, upload scripts, scheduler configs) slip through
    if "deploy" in name.lower() or "upload" in name.lower() or "signing" in name.lower() or "key" in name.lower():
        is_deployment = True
        is_signing = True
        reason_codes.append("ARTIFACT_CATALOG_DEPLOYMENT_BLOCKED")
        reason_codes.append("ARTIFACT_CATALOG_EXTERNAL_SIGNING_BLOCKED")

    # Scope mapping
    if "RC1" in name or "rc1" in name:
        rc_scope = "RC1"
        candidate_level = "Foundation"
    elif "RC2" in name or "rc2" in name:
        rc_scope = "RC2"
        candidate_level = "Governed Execution Stack"
    else:
        rc_scope = rc_scope
        if rc_scope == "RC1":
            candidate_level = "Foundation"
        elif rc_scope == "RC2":
            candidate_level = "Governed Execution Stack"
        else:
            candidate_level = "Shared"

    # 5. Load and calculate digest / status
    artifact_digest = ""
    artifact_size_bytes = 0
    distribution_status = "artifact_distribution_invalid"

    # Self-referential artifacts are treated as pending if not yet written
    is_self_referential = ("_ARTIFACT_CATALOG" in name)

    if os.path.exists(full_artifact_path):
        reason_codes.append("ARTIFACT_CATALOG_ARTIFACT_EXISTS")
        artifact_digest = hash_file_contents(full_artifact_path)
        if artifact_digest:
            reason_codes.append("ARTIFACT_CATALOG_ARTIFACT_DIGEST_MATCH")
        artifact_size_bytes = os.path.getsize(full_artifact_path)

        if is_deployment or is_signing:
            distribution_status = "artifact_distribution_blocked"
        else:
            distribution_status = "artifact_distribution_ready"
            reason_codes.append("ARTIFACT_CATALOG_DISTRIBUTION_READY")
    else:
        reason_codes.append("ARTIFACT_CATALOG_ARTIFACT_MISSING")
        if is_self_referential:
            distribution_status = "artifact_distribution_pending"
        else:
            distribution_status = "artifact_distribution_blocked"

    if "production_deployment" in blocked_channels:
        reason_codes.append("ARTIFACT_CATALOG_DEPLOYMENT_BLOCKED")
    if "external_key_signing" in blocked_channels:
        reason_codes.append("ARTIFACT_CATALOG_EXTERNAL_SIGNING_BLOCKED")
    if "production_deployment" in blocked_channels and "external_key_signing" in blocked_channels:
        reason_codes.append("ARTIFACT_CATALOG_FORBIDDEN_CHANNELS_BLOCKED")

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reason_codes.append("ARTIFACT_CATALOG_SOFTWARE_CAVEAT_INCLUDED")

    entry = WaveguideCertifiedArtifactCatalogEntry(
        artifact_catalog_entry_id=f"SOL-WAVEGUIDE-ARTIFACT-{name.replace('.', '_')}",
        artifact_path=norm_path,
        artifact_name=name,
        artifact_type=artifact_type,
        artifact_format=artifact_format,
        rc_scope=rc_scope,
        candidate_level=candidate_level,
        package_role=package_role,
        distribution_status=distribution_status,
        artifact_digest=artifact_digest,
        artifact_size_bytes=artifact_size_bytes,
        source_distribution_audit_report_digest=report_digest,
        source_publication_manifest_digest=manifest_digest,
        source_audit_registry_digest=registry_digest,
        related_rc_ids=related_rc_ids,
        related_bundle_digests=related_bundle_digests,
        related_audit_report_digests=related_audit_report_digests,
        related_audit_case_digests=related_audit_case_digests,
        allowed_distribution_channels=sorted(allowed_channels),
        blocked_distribution_channels=sorted(blocked_channels),
        is_required_for_distribution_package=(not is_self_referential and not is_deployment and not is_signing),
        is_proof_artifact=is_proof,
        is_documentation_artifact=is_documentation,
        is_code_artifact=is_code,
        is_deployment_artifact=is_deployment,
        is_signing_artifact=is_signing,
        reason_codes=sorted(list(set(reason_codes))),
        notes=[],
        software_validation_caveat=software_validation_caveat,
        artifact_catalog_entry_digest=""
    )
    entry.artifact_catalog_entry_digest = hash_waveguide_certified_artifact_catalog_entry(entry)
    return entry


def validate_waveguide_certified_artifact_catalog_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Validates a single artifact catalog entry.
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
    path = e_dict.get("artifact_path")
    name = e_dict.get("artifact_name")
    atype = e_dict.get("artifact_type")
    aformat = e_dict.get("artifact_format")
    role = e_dict.get("package_role")
    status = e_dict.get("distribution_status")
    report_digest = e_dict.get("source_distribution_audit_report_digest")
    caveat = e_dict.get("software_validation_caveat")

    if not path or not name or not atype or not aformat or not role or not status:
        is_valid = False
        reasons.append("ARTIFACT_CATALOG_INVALID")
    if not report_digest:
        is_valid = False
        reasons.append("ARTIFACT_CATALOG_INVALID")
    if not caveat or "sandbox" not in caveat.lower():
        is_valid = False
        reasons.append("ARTIFACT_CATALOG_INVALID")

    # 2. Check digest validates if file exists
    given_digest = e_dict.get("artifact_catalog_entry_digest")
    if given_digest:
        recomputed = hash_waveguide_certified_artifact_catalog_entry(e_dict)
        if recomputed == given_digest:
            reasons.append("ARTIFACT_CATALOG_ENTRY_DIGEST_VALID")
        else:
            is_valid = False
            reasons.append("ARTIFACT_CATALOG_INVALID")
    else:
        is_valid = False
        reasons.append("ARTIFACT_CATALOG_INVALID")

    # 3. Check status consistency
    if status == "artifact_distribution_ready":
        # Check file exists and digest matches
        full_p = os.path.join(REPO_ROOT, path)
        if not path or not os.path.isfile(full_p):
            is_valid = False
            reasons.append("ARTIFACT_CATALOG_INVALID")
        else:
            recomputed_file_digest = hash_file_contents(full_p)
            is_self_referential = ("_ARTIFACT_CATALOG" in name)
            if not is_self_referential and recomputed_file_digest != e_dict.get("artifact_digest"):
                is_valid = False
                reasons.append("ARTIFACT_CATALOG_INVALID")

        # Must not be a deployment or signing unit
        if e_dict.get("is_deployment_artifact") or e_dict.get("is_signing_artifact"):
            is_valid = False
            reasons.append("ARTIFACT_CATALOG_INVALID")

        # Allowed channels should match policy
        allowed = e_dict.get("allowed_distribution_channels", [])
        if "production_deployment" in allowed or "external_key_signing" in allowed:
            is_valid = False
            reasons.append("ARTIFACT_CATALOG_INVALID")

    # Add codes if valid
    if is_valid:
        for rc in e_dict.get("reason_codes", []):
            if rc.startswith("ARTIFACT_CATALOG_"):
                reasons.append(rc)
        reasons.append("ARTIFACT_CATALOG_ENTRY_CANONICAL")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_certified_artifact_catalog(
    report_path_or_dict: Any
) -> WaveguideCertifiedArtifactCatalog:
    """
    Builds a deterministic Certified Artifact Catalog from a Distribution Readiness report.
    """
    report_dict = None
    load_failed = False

    # 1. Load readiness report
    if isinstance(report_path_or_dict, str):
        path = normalize_to_repo_path(report_path_or_dict)
        full_path = os.path.join(REPO_ROOT, path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    report_dict = json.load(f)
            except Exception:
                load_failed = True
        else:
            load_failed = True
    elif hasattr(report_path_or_dict, "__dict__"):
        report_dict = asdict(report_path_or_dict)
    elif isinstance(report_path_or_dict, dict):
        report_dict = dict(report_path_or_dict)
    else:
        load_failed = True

    if load_failed or not report_dict:
        # Build empty/invalid catalog
        software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
        catalog = WaveguideCertifiedArtifactCatalog(
            artifact_catalog_id="SOL-WAVEGUIDE-CERTIFIED-ARTIFACT-CATALOG",
            artifact_catalog_version=1,
            artifact_catalog_status="artifact_catalog_invalid",
            source_distribution_audit_report_digest="",
            source_publication_manifest_digest="",
            source_audit_registry_digest="",
            entries=[],
            distribution_ready_artifacts=[],
            blocked_artifacts=[],
            pending_artifacts=[],
            invalid_artifacts=[],
            distribution_ready_artifact_count=0,
            blocked_artifact_count=0,
            pending_artifact_count=0,
            invalid_artifact_count=0,
            rc1_artifact_count=0,
            rc2_artifact_count=0,
            shared_artifact_count=0,
            artifact_types_indexed=[],
            artifact_formats_indexed=[],
            package_roles_indexed=[],
            rc_scopes_indexed=[],
            artifact_paths_indexed=[],
            artifact_digests_indexed=[],
            documentation_artifact_paths=[],
            proof_artifact_paths=[],
            code_artifact_paths=[],
            test_artifact_paths=[],
            distribution_package_inventory=[],
            allowed_distribution_channels=[],
            blocked_distribution_channels=[],
            reason_codes=["ARTIFACT_CATALOG_INVALID", "ARTIFACT_CATALOG_SOURCE_DISTRIBUTION_AUDIT_INVALID"],
            software_validation_caveat=software_validation_caveat,
            artifact_catalog_digest=""
        )
        catalog.artifact_catalog_digest = hash_waveguide_certified_artifact_catalog(catalog)
        return catalog

    report_digest = report_dict.get("distribution_audit_report_digest", "")
    manifest_digest = report_dict.get("source_publication_manifest_digest", "")
    registry_digest = report_dict.get("source_audit_registry_digest", "")

    # Structural check of source report
    val_ok, val_reasons = validate_waveguide_distribution_readiness_audit_report(report_dict)

    # Defined list of required files to inventory
    required_files = [
        # JSON proof capsules
        ("docs/SOL_WAVEGUIDE_RC1_MANIFEST.json", "RC1"),
        ("docs/SOL_WAVEGUIDE_RC2_MANIFEST.json", "RC2"),
        ("docs/SOL_WAVEGUIDE_RC_DELTA_AUDIT.json", "Shared"),
        ("docs/SOL_WAVEGUIDE_RC_PROMOTION_RECORD_RC1.json", "RC1"),
        ("docs/SOL_WAVEGUIDE_RC_PROMOTION_RECORD_RC2.json", "RC2"),
        ("docs/SOL_WAVEGUIDE_RC_COURT_VERDICT_RC1.json", "RC1"),
        ("docs/SOL_WAVEGUIDE_RC_COURT_VERDICT_RC2.json", "RC2"),
        ("docs/SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json", "Shared"),
        ("docs/SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC1.json", "RC1"),
        ("docs/SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_RC2.json", "RC2"),
        ("docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_REGISTRY.json", "Shared"),
        ("docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC1.json", "RC1"),
        ("docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC2.json", "RC2"),
        ("docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC1.json", "RC1"),
        ("docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT_RC2.json", "RC2"),
        ("docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_AUDIT_REPORT.json", "Shared"),
        ("docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.json", "Shared"),
        ("docs/SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json", "Shared"),
        ("docs/SOL_WAVEGUIDE_DISTRIBUTION_READINESS_AUDIT_REPORT.json", "Shared"),
        # Markdown docs
        ("docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE.md", "Shared"),
        ("docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_VALIDATOR.md", "Shared"),
        ("docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_INDEX.md", "Shared"),
        ("docs/SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.md", "Shared"),
        ("docs/SOL_WAVEGUIDE_PUBLICATION_MANIFEST_VALIDATOR.md", "Shared"),
        # Self-referential catalog doc/JSON (exist only after script generation, so handled gracefully)
        ("docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json", "Shared"),
        ("docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.md", "Shared"),
        # Source/Test modules
        ("tools/sol-core/sol_waveguide_certified_artifact_catalog.py", "Shared"),
        ("tests/test_waveguide_certified_artifact_catalog.py", "Shared")
    ]

    entries = []
    for path_str, scope in required_files:
        # Gracefully handle paths that might not exist or be generated later
        entry = build_waveguide_certified_artifact_catalog_entry(path_str, report_dict, scope)
        entries.append(entry)

    # Sort entries deterministically by artifact_path, artifact_type, package_role
    def entry_sort_key(e):
        return (
            e.artifact_path,
            e.artifact_type,
            e.package_role
        )
    sorted_entries = sorted(entries, key=entry_sort_key)

    distribution_ready_artifacts = []
    blocked_artifacts = []
    pending_artifacts = []
    invalid_artifacts = []

    distribution_ready_artifact_count = 0
    blocked_artifact_count = 0
    pending_artifact_count = 0
    invalid_artifact_count = 0
    rc1_artifact_count = 0
    rc2_artifact_count = 0
    shared_artifact_count = 0

    artifact_types_indexed = []
    artifact_formats_indexed = []
    package_roles_indexed = []
    rc_scopes_indexed = []
    artifact_paths_indexed = []
    artifact_digests_indexed = []
    documentation_artifact_paths = []
    proof_artifact_paths = []
    code_artifact_paths = []
    test_artifact_paths = []

    all_reasons = [
        "ARTIFACT_CATALOG_COUNTS_VALID",
        "ARTIFACT_CATALOG_INDEXES_VALID",
        "ARTIFACT_CATALOG_PACKAGE_INVENTORY_CANONICAL"
    ]

    if val_ok:
        all_reasons.append("ARTIFACT_CATALOG_SOURCE_DISTRIBUTION_AUDIT_VALID")
    else:
        all_reasons.append("ARTIFACT_CATALOG_SOURCE_DISTRIBUTION_AUDIT_INVALID")

    for entry in sorted_entries:
        path = entry.artifact_path
        status = entry.distribution_status
        scope = entry.rc_scope
        atype = entry.artifact_type
        aformat = entry.artifact_format
        role = entry.package_role
        digest = entry.artifact_digest

        # Unique index aggregations
        def add_unique(lst, val):
            if val and val not in lst:
                lst.append(val)

        add_unique(artifact_types_indexed, atype)
        add_unique(artifact_formats_indexed, aformat)
        add_unique(package_roles_indexed, role)
        add_unique(rc_scopes_indexed, scope)
        add_unique(artifact_paths_indexed, path)
        add_unique(artifact_digests_indexed, digest)

        if entry.is_proof_artifact:
            add_unique(proof_artifact_paths, path)
        if entry.is_documentation_artifact:
            add_unique(documentation_artifact_paths, path)
        if entry.is_code_artifact:
            if "test_" in entry.artifact_name:
                add_unique(test_artifact_paths, path)
            else:
                add_unique(code_artifact_paths, path)

        if status == "artifact_distribution_ready":
            distribution_ready_artifact_count += 1
            add_unique(distribution_ready_artifacts, path)
        elif status == "artifact_distribution_blocked":
            blocked_artifact_count += 1
            add_unique(blocked_artifacts, path)
        elif status == "artifact_distribution_pending":
            pending_artifact_count += 1
            add_unique(pending_artifacts, path)
        else:
            invalid_artifact_count += 1
            add_unique(invalid_artifacts, path)

        if scope == "RC1":
            rc1_artifact_count += 1
        elif scope == "RC2":
            rc2_artifact_count += 1
        else:
            shared_artifact_count += 1

        for code in entry.reason_codes:
            if code not in all_reasons:
                all_reasons.append(code)

    # Sort all index lists
    distribution_ready_artifacts = sorted(distribution_ready_artifacts)
    blocked_artifacts = sorted(blocked_artifacts)
    pending_artifacts = sorted(pending_artifacts)
    invalid_artifacts = sorted(invalid_artifacts)
    artifact_types_indexed = sorted(artifact_types_indexed)
    artifact_formats_indexed = sorted(artifact_formats_indexed)
    package_roles_indexed = sorted(package_roles_indexed)
    rc_scopes_indexed = sorted(rc_scopes_indexed)
    artifact_paths_indexed = sorted(artifact_paths_indexed)
    artifact_digests_indexed = sorted(artifact_digests_indexed)
    documentation_artifact_paths = sorted(documentation_artifact_paths)
    proof_artifact_paths = sorted(proof_artifact_paths)
    code_artifact_paths = sorted(code_artifact_paths)
    test_artifact_paths = sorted(test_artifact_paths)

    # Build readiness catalog sorted by path
    distribution_package_inventory = []
    inventory_sorted = sorted(sorted_entries, key=lambda e: e.artifact_path)
    for index_1, entry in enumerate(inventory_sorted):
        distribution_package_inventory.append({
            "inventory_index": index_1 + 1,
            "artifact_path": entry.artifact_path,
            "artifact_type": entry.artifact_type,
            "artifact_format": entry.artifact_format,
            "package_role": entry.package_role,
            "distribution_status": entry.distribution_status,
            "artifact_digest": entry.artifact_digest,
            "rc_scope": entry.rc_scope
        })

    # Allowed and blocked channels policy mappings
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

    # Overall catalog status
    # A catalog is valid if all entries validate and the source report is verified
    # Note: pending self-referential entries do not make the catalog invalid.
    if blocked_artifact_count > 0 or invalid_artifact_count > 0 or not val_ok:
        catalog_status = "artifact_catalog_invalid"
        all_reasons.append("ARTIFACT_CATALOG_INVALID")
    else:
        catalog_status = "artifact_catalog_valid"
        all_reasons.append("ARTIFACT_CATALOG_VALID")

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    catalog = WaveguideCertifiedArtifactCatalog(
        artifact_catalog_id="SOL-WAVEGUIDE-CERTIFIED-ARTIFACT-CATALOG",
        artifact_catalog_version=1,
        artifact_catalog_status=catalog_status,
        source_distribution_audit_report_digest=report_digest,
        source_publication_manifest_digest=manifest_digest,
        source_audit_registry_digest=registry_digest,
        entries=sorted_entries,
        distribution_ready_artifacts=distribution_ready_artifacts,
        blocked_artifacts=blocked_artifacts,
        pending_artifacts=pending_artifacts,
        invalid_artifacts=invalid_artifacts,
        distribution_ready_artifact_count=distribution_ready_artifact_count,
        blocked_artifact_count=blocked_artifact_count,
        pending_artifact_count=pending_artifact_count,
        invalid_artifact_count=invalid_artifact_count,
        rc1_artifact_count=rc1_artifact_count,
        rc2_artifact_count=rc2_artifact_count,
        shared_artifact_count=shared_artifact_count,
        artifact_types_indexed=artifact_types_indexed,
        artifact_formats_indexed=artifact_formats_indexed,
        package_roles_indexed=package_roles_indexed,
        rc_scopes_indexed=rc_scopes_indexed,
        artifact_paths_indexed=artifact_paths_indexed,
        artifact_digests_indexed=artifact_digests_indexed,
        documentation_artifact_paths=documentation_artifact_paths,
        proof_artifact_paths=proof_artifact_paths,
        code_artifact_paths=code_artifact_paths,
        test_artifact_paths=test_artifact_paths,
        distribution_package_inventory=distribution_package_inventory,
        allowed_distribution_channels=allowed_distribution_channels,
        blocked_distribution_channels=blocked_distribution_channels,
        reason_codes=sorted(list(set(all_reasons))),
        software_validation_caveat=software_validation_caveat,
        artifact_catalog_digest=""
    )
    catalog.artifact_catalog_digest = hash_waveguide_certified_artifact_catalog(catalog)
    return catalog


def validate_waveguide_certified_artifact_catalog(catalog: Any) -> Tuple[bool, List[str]]:
    """
    Validates the top-level artifact catalog.
    """
    if hasattr(catalog, "__dict__"):
        c_dict = asdict(catalog)
    elif isinstance(catalog, dict):
        c_dict = dict(catalog)
    else:
        raise TypeError("catalog must be a dictionary or a dataclass instance")

    reasons = []
    is_valid = True

    # 1. Digest checks
    given_digest = c_dict.get("artifact_catalog_digest")
    if not given_digest:
        is_valid = False
        reasons.append("ARTIFACT_CATALOG_INVALID")
    else:
        recomputed = hash_waveguide_certified_artifact_catalog(c_dict)
        if recomputed == given_digest:
            reasons.append("ARTIFACT_CATALOG_DIGEST_VALID")
        else:
            is_valid = False
            reasons.append("ARTIFACT_CATALOG_INVALID")

    # 2. Check entries validation
    entries = c_dict.get("entries", [])
    entry_statuses = []
    for entry in entries:
        # Validate each entry
        ok, ent_reasons = validate_waveguide_certified_artifact_catalog_entry(entry)
        if not ok:
            is_valid = False
            reasons.append("ARTIFACT_CATALOG_INVALID")
        entry_statuses.append(entry.get("distribution_status") if isinstance(entry, dict) else entry.distribution_status)

    # 3. Check counts consistency
    ready_count = c_dict.get("distribution_ready_artifact_count", 0)
    blocked_count = c_dict.get("blocked_artifact_count", 0)
    pending_count = c_dict.get("pending_artifact_count", 0)
    invalid_count = c_dict.get("invalid_artifact_count", 0)

    if (ready_count != entry_statuses.count("artifact_distribution_ready") or
        blocked_count != entry_statuses.count("artifact_distribution_blocked") or
        pending_count != entry_statuses.count("artifact_distribution_pending") or
        invalid_count != entry_statuses.count("artifact_distribution_invalid")):
        is_valid = False
        reasons.append("ARTIFACT_CATALOG_INVALID")

    # 4. Check status consistency
    catalog_status = c_dict.get("artifact_catalog_status")
    if catalog_status == "artifact_catalog_valid":
        if blocked_count > 0 or invalid_count > 0 or len(entries) == 0:
            is_valid = False
            reasons.append("ARTIFACT_CATALOG_INVALID")

    if is_valid:
        for rc in c_dict.get("reason_codes", []):
            if rc.startswith("ARTIFACT_CATALOG_"):
                reasons.append(rc)
        reasons.append("ARTIFACT_CATALOG_VALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_certified_artifact_catalog(catalog: Any) -> str:
    """
    Returns a plaintext summary of the artifact catalog.
    """
    if hasattr(catalog, "__dict__"):
        c_dict = asdict(catalog)
    elif isinstance(catalog, dict):
        c_dict = dict(catalog)
    else:
        raise TypeError("catalog must be a dictionary or a dataclass instance")

    lines = [
        "============================================================",
        "          SOL WAVEGUIDE CERTIFIED ARTIFACT CATALOG",
        "============================================================",
        f"Catalog ID:       {c_dict.get('artifact_catalog_id')}",
        f"Version:          {c_dict.get('artifact_catalog_version')}",
        f"Status:           {c_dict.get('artifact_catalog_status', '').upper()}",
        f"Catalog Digest:   {c_dict.get('artifact_catalog_digest')}",
        "------------------------------------------------------------",
        "Distribution Ready Artifacts:"
    ]

    for path in c_dict.get("distribution_ready_artifacts", []):
        lines.append(f"  * {path}")

    lines.append("------------------------------------------------------------")
    lines.append("Blocked / Missing Artifacts:")
    for path in c_dict.get("blocked_artifacts", []):
        lines.append(f"  * {path}")

    lines.append("------------------------------------------------------------")
    lines.append("Pending Self-Referential Artifacts:")
    for path in c_dict.get("pending_artifacts", []):
        lines.append(f"  * {path}")

    lines.append("------------------------------------------------------------")
    lines.append("Package Inventory Details:")
    for item in c_dict.get("distribution_package_inventory", []):
        lines.append(
            f"  [{item.get('inventory_index')}] {item.get('artifact_path')} ({item.get('rc_scope')}) "
            f"-> status: {item.get('distribution_status')}"
        )

    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in c_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {c_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_certified_artifact_catalog(catalog: Any, filepath: str) -> None:
    """
    Exports the catalog to a JSON file.
    """
    if hasattr(catalog, "__dict__"):
        c_dict = asdict(catalog)
    elif isinstance(catalog, dict):
        c_dict = dict(catalog)
    else:
        raise TypeError("catalog must be a dictionary or a dataclass instance")

    full_path = os.path.join(REPO_ROOT, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(c_dict, f, indent=4, sort_keys=True)


def compare_waveguide_certified_artifact_catalogs(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two catalogs and returns differences.
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
        "catalog_id_match": l_dict.get("artifact_catalog_id") == r_dict.get("artifact_catalog_id"),
        "catalog_version_match": l_dict.get("artifact_catalog_version") == r_dict.get("artifact_catalog_version"),
        "catalog_status_match": l_dict.get("artifact_catalog_status") == r_dict.get("artifact_catalog_status"),
        "catalog_digest_match": l_dict.get("artifact_catalog_digest") == r_dict.get("artifact_catalog_digest"),
        "ready_count_diff": l_dict.get("distribution_ready_artifact_count", 0) - r_dict.get("distribution_ready_artifact_count", 0),
        "blocked_count_diff": l_dict.get("blocked_artifact_count", 0) - r_dict.get("blocked_artifact_count", 0),
        "ready_paths_left_only": list(set(l_dict.get("distribution_ready_artifacts", [])) - set(r_dict.get("distribution_ready_artifacts", []))),
        "ready_paths_right_only": list(set(r_dict.get("distribution_ready_artifacts", [])) - set(l_dict.get("distribution_ready_artifacts", []))),
        "blocked_paths_left_only": list(set(l_dict.get("blocked_artifacts", [])) - set(r_dict.get("blocked_artifacts", []))),
        "blocked_paths_right_only": list(set(r_dict.get("blocked_artifacts", [])) - set(l_dict.get("blocked_artifacts", [])))
    }
    
    diff["all_match"] = (
        diff["catalog_id_match"] and
        diff["catalog_version_match"] and
        diff["catalog_status_match"] and
        diff["catalog_digest_match"] and
        diff["ready_count_diff"] == 0 and
        diff["blocked_count_diff"] == 0 and
        not diff["ready_paths_left_only"] and
        not diff["ready_paths_right_only"] and
        not diff["blocked_paths_left_only"] and
        not diff["blocked_paths_right_only"]
    )
    return diff


def index_waveguide_catalog_entries_by_rc(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes entries mapping rc_scope to list of entries.
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


def index_waveguide_catalog_entries_by_artifact_type(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes entries mapping artifact_type to list of entries.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        atype = e_dict.get("artifact_type")
        if atype not in idx:
            idx[atype] = []
        idx[atype].append(e_dict)
    return idx


def index_waveguide_catalog_entries_by_package_role(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes entries mapping package_role to list of entries.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        role = e_dict.get("package_role")
        if role not in idx:
            idx[role] = []
        idx[role].append(e_dict)
    return idx


def index_waveguide_catalog_entries_by_distribution_status(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes entries mapping distribution_status to list of entries.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        status = e_dict.get("distribution_status")
        if status not in idx:
            idx[status] = []
        idx[status].append(e_dict)
    return idx


def build_waveguide_distribution_package_inventory(entries: List[Any]) -> List[Dict[str, Any]]:
    """
    Builds a deterministic package inventory sorted strictly by path.
    """
    sorted_entries = sorted(entries, key=lambda e: e.artifact_path if hasattr(e, "artifact_path") else e.get("artifact_path", ""))
    catalog = []
    for idx, e in enumerate(sorted_entries):
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        catalog.append({
            "inventory_index": idx + 1,
            "artifact_path": e_dict.get("artifact_path"),
            "artifact_type": e_dict.get("artifact_type"),
            "artifact_format": e_dict.get("artifact_format"),
            "package_role": e_dict.get("package_role"),
            "distribution_status": e_dict.get("distribution_status"),
            "artifact_digest": e_dict.get("artifact_digest"),
            "rc_scope": e_dict.get("rc_scope")
        })
    return catalog
