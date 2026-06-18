# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Publication Manifest Validator / Distribution Readiness Auditor.
Independently reloads the publication manifest, recomputes digests, validates
against the source audit registry, and emits distribution-readiness reports.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT,
    hash_file_contents
)
from sol_waveguide_release_certification_index import (
    validate_waveguide_release_certification_index,
    WaveguideReleaseCertificationIndex,
    WaveguideReleaseCertificationIndexEntry
)
from sol_waveguide_certified_release_publication_manifest import (
    hash_waveguide_certified_release_publication_entry,
    hash_waveguide_certified_release_publication_manifest,
    validate_waveguide_certified_release_publication_manifest,
    WaveguideCertifiedReleasePublicationEntry,
    WaveguideCertifiedReleasePublicationManifest
)


@dataclass
class WaveguideDistributionReadinessAuditCase:
    distribution_audit_case_id: str
    publication_manifest_id: str
    publication_manifest_path: str
    publication_manifest_digest_recorded: str
    publication_manifest_digest_recomputed: str
    publication_manifest_digest_match: bool
    publication_entry_id: str
    publication_entry_digest_recorded: str
    publication_entry_digest_recomputed: str
    publication_entry_digest_match: bool
    rc_id: str
    candidate_level: str
    publication_status: str
    distribution_readiness_status: str  # distribution_ready, distribution_blocked, distribution_pending, distribution_invalid
    source_audit_registry_digest_recorded: str
    source_audit_registry_digest_recomputed: str
    source_audit_registry_digest_match: bool
    source_audit_registry_valid: bool
    source_audit_registry_entry_digest: str
    certification_bundle_id: str
    certification_bundle_digest: str
    audit_report_digest: str
    audit_case_digest: str
    audit_status: str
    audit_report_status: str
    target_rc_approved: bool
    runtime_capability_valid: bool
    compiler_session_registry_valid: bool
    artifact_digest_mismatch_count: int
    artifact_validation_failure_count: int
    registered_session_count: int
    registered_rejection_session_count: int
    final_output_payload_digests: List[str]
    allowed_channels: List[str]
    blocked_channels: List[str]
    metadata_only_channels_verified: bool
    forbidden_channels_blocked: bool
    publication_gate_reasons: List[str]
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    distribution_audit_case_digest: str = ""


@dataclass
class WaveguideDistributionReadinessAuditReport:
    distribution_audit_report_id: str
    distribution_audit_report_version: int
    distribution_audit_report_status: str  # distribution_readiness_verified, etc.
    source_publication_manifest_digest: str
    source_audit_registry_digest: str
    audited_cases: List[WaveguideDistributionReadinessAuditCase]
    distribution_ready_rcs: List[str]
    distribution_blocked_rcs: List[str]
    distribution_pending_rcs: List[str]
    distribution_invalid_rcs: List[str]
    distribution_ready_count: int
    distribution_blocked_count: int
    distribution_pending_count: int
    distribution_invalid_count: int
    rc1_distribution_count: int
    rc2_distribution_count: int
    candidate_levels_indexed: List[str]
    certification_bundle_ids: List[str]
    certification_bundle_digests: List[str]
    audit_report_digests: List[str]
    audit_case_digests: List[str]
    audit_registry_entry_digests: List[str]
    publication_entry_digests: List[str]
    final_output_payload_digests: List[str]
    allowed_channels_indexed: List[str]
    blocked_channels_indexed: List[str]
    metadata_only_channels_verified: bool
    forbidden_channels_blocked: bool
    reason_codes: List[str]
    software_validation_caveat: str
    distribution_audit_report_digest: str = ""


def hash_waveguide_distribution_readiness_audit_case(case: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation
    excluding the self-referential distribution_audit_case_digest field.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    elif isinstance(case, dict):
        c_dict = dict(case)
    else:
        raise TypeError("case must be a dictionary or a dataclass instance")

    c_dict_copy = dict(c_dict)
    c_dict_copy.pop("distribution_audit_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_distribution_readiness_audit_report(report: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation
    excluding the self-referential distribution_audit_report_digest field.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    r_dict_copy = dict(r_dict)
    r_dict_copy.pop("distribution_audit_report_digest", None)
    return hash_data(r_dict_copy)


def recompute_waveguide_publication_manifest_digest(pub_manifest_or_dict: Any) -> str:
    """
    Recomputes the top-level publication manifest digest.
    """
    return hash_waveguide_certified_release_publication_manifest(pub_manifest_or_dict)


def recompute_waveguide_publication_entry_digest(pub_entry_or_dict: Any) -> str:
    """
    Recomputes a publication entry digest.
    """
    return hash_waveguide_certified_release_publication_entry(pub_entry_or_dict)


def validate_waveguide_distribution_channel_policy(allowed: List[str], blocked: List[str]) -> Tuple[bool, List[str]]:
    """
    Verifies that allowed channels are metadata-only and forbidden channels remain blocked.
    """
    reasons = []
    is_valid = True

    forbidden = [
        "production_deployment",
        "external_key_signing",
        "legal_certification_claim",
        "quantum_hardware_certification"
    ]

    # Check allowed channels
    for ch in allowed:
        if ch in forbidden:
            is_valid = False
            reasons.append("DISTRIBUTION_READINESS_INVALID")
        if ch == "internal_distribution":
            reasons.append("DISTRIBUTION_INTERNAL_DISTRIBUTION_METADATA_ONLY")
        if ch == "documentation_publication":
            reasons.append("DISTRIBUTION_DOCUMENTATION_PUBLICATION_METADATA_ONLY")
        if ch == "artifact_catalog_publication":
            reasons.append("DISTRIBUTION_ARTIFACT_CATALOG_METADATA_ONLY")

    # Check blocked channels
    for ch in forbidden:
        if ch not in blocked:
            is_valid = False
            reasons.append("DISTRIBUTION_READINESS_INVALID")

    if "production_deployment" in blocked:
        reasons.append("DISTRIBUTION_PRODUCTION_DEPLOYMENT_BLOCKED")
    if "external_key_signing" in blocked:
        reasons.append("DISTRIBUTION_EXTERNAL_SIGNING_BLOCKED")
    if "legal_certification_claim" in blocked:
        reasons.append("DISTRIBUTION_LEGAL_CLAIM_BLOCKED")
    if "quantum_hardware_certification" in blocked:
        reasons.append("DISTRIBUTION_QUANTUM_HARDWARE_CLAIM_BLOCKED")

    if is_valid:
        reasons.append("DISTRIBUTION_FORBIDDEN_CHANNELS_BLOCKED")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_distribution_readiness_audit_case(
    pub_entry_or_dict: Any,
    pub_manifest_path_or_dict: Any,
    registry_path_or_dict: Any
) -> WaveguideDistributionReadinessAuditCase:
    """
    Builds a deterministic distribution readiness audit case.
    """
    # 1. Resolve publication entry
    if hasattr(pub_entry_or_dict, "__dict__"):
        ent_dict = asdict(pub_entry_or_dict)
    elif isinstance(pub_entry_or_dict, dict):
        ent_dict = dict(pub_entry_or_dict)
    else:
        ent_dict = {}

    rc_id = ent_dict.get("rc_id", "UNKNOWN")
    candidate_level = ent_dict.get("candidate_level", "Unknown")
    pub_status = ent_dict.get("publication_status", "publication_invalid")

    # 2. Resolve publication manifest
    manifest_dict = None
    manifest_path = ""
    manifest_load_failed = False
    
    if isinstance(pub_manifest_path_or_dict, str):
        manifest_path = normalize_to_repo_path(pub_manifest_path_or_dict)
        full_manifest_path = os.path.join(REPO_ROOT, manifest_path)
        if os.path.exists(full_manifest_path):
            try:
                with open(full_manifest_path, "r", encoding="utf-8") as f:
                    manifest_dict = json.load(f)
            except Exception:
                manifest_load_failed = True
        else:
            manifest_load_failed = True
    elif hasattr(pub_manifest_path_or_dict, "__dict__"):
        manifest_dict = asdict(pub_manifest_path_or_dict)
    elif isinstance(pub_manifest_path_or_dict, dict):
        manifest_dict = dict(pub_manifest_path_or_dict)
    else:
        manifest_load_failed = True

    # 3. Resolve source registry index
    registry_dict = None
    registry_path = ""
    registry_load_failed = False

    if isinstance(registry_path_or_dict, str):
        registry_path = normalize_to_repo_path(registry_path_or_dict)
        full_registry_path = os.path.join(REPO_ROOT, registry_path)
        if os.path.exists(full_registry_path):
            try:
                with open(full_registry_path, "r", encoding="utf-8") as f:
                    registry_dict = json.load(f)
            except Exception:
                registry_load_failed = True
        else:
            registry_load_failed = True
    elif hasattr(registry_path_or_dict, "__dict__"):
        registry_dict = asdict(registry_path_or_dict)
    elif isinstance(registry_path_or_dict, dict):
        registry_dict = dict(registry_path_or_dict)
    else:
        registry_load_failed = True

    # Default check values
    pub_manifest_digest_recorded = ""
    pub_manifest_digest_recomputed = ""
    pub_manifest_digest_match = False
    pub_entry_digest_recorded = ent_dict.get("publication_entry_digest", "")
    pub_entry_digest_recomputed = ""
    pub_entry_digest_match = False
    
    source_audit_registry_digest_recorded = ""
    source_audit_registry_digest_recomputed = ""
    source_audit_registry_digest_match = False
    source_audit_registry_valid = False

    reason_codes = ["DISTRIBUTION_AUDIT_CASE_CANONICAL"]
    publication_gate_reasons = []

    if manifest_dict:
        reason_codes.append("DISTRIBUTION_PUBLICATION_MANIFEST_LOADED")
        # Validate manifest structure using validator logic
        val_ok, val_reasons = validate_waveguide_certified_release_publication_manifest(manifest_dict)
        if val_ok:
            reason_codes.append("DISTRIBUTION_PUBLICATION_MANIFEST_VALID")
        else:
            reason_codes.append("DISTRIBUTION_PUBLICATION_MANIFEST_INVALID")
            publication_gate_reasons.append("Publication manifest fails structural validation.")

        pub_manifest_digest_recorded = manifest_dict.get("publication_manifest_digest", "")
        pub_manifest_digest_recomputed = recompute_waveguide_publication_manifest_digest(manifest_dict)
        pub_manifest_digest_match = (pub_manifest_digest_recorded == pub_manifest_digest_recomputed)
        if pub_manifest_digest_match:
            reason_codes.append("DISTRIBUTION_PUBLICATION_MANIFEST_DIGEST_MATCH")
        else:
            reason_codes.append("DISTRIBUTION_PUBLICATION_MANIFEST_DIGEST_MISMATCH")
            publication_gate_reasons.append("Publication manifest digest mismatch.")
    else:
        reason_codes.append("DISTRIBUTION_PUBLICATION_MANIFEST_INVALID")
        publication_gate_reasons.append("Failed to load publication manifest.")

    if ent_dict:
        pub_entry_digest_recomputed = recompute_waveguide_publication_entry_digest(ent_dict)
        pub_entry_digest_match = (pub_entry_digest_recorded == pub_entry_digest_recomputed)
        if pub_entry_digest_match:
            reason_codes.append("DISTRIBUTION_PUBLICATION_ENTRY_DIGEST_MATCH")
            reason_codes.append("DISTRIBUTION_PUBLICATION_ENTRY_DIGEST_REFERENCED")
        else:
            reason_codes.append("DISTRIBUTION_PUBLICATION_ENTRY_DIGEST_MISMATCH")
            publication_gate_reasons.append(f"Publication entry digest mismatch for entry '{ent_dict.get('publication_entry_id')}'.")
    else:
        publication_gate_reasons.append("Failed to resolve publication entry.")

    if registry_dict:
        # Validate registry using validator logic
        val_ok, val_reasons = validate_waveguide_release_certification_index(registry_dict)
        source_audit_registry_valid = val_ok
        if val_ok:
            reason_codes.append("DISTRIBUTION_SOURCE_AUDIT_REGISTRY_VALID")
        else:
            reason_codes.append("DISTRIBUTION_SOURCE_AUDIT_REGISTRY_INVALID")
            publication_gate_reasons.append("Source audit registry index fails structural validation.")

        source_audit_registry_digest_recorded = manifest_dict.get("source_audit_registry_digest", "") if manifest_dict else ""
        source_audit_registry_digest_recomputed = registry_dict.get("audit_registry_digest", "")
        source_audit_registry_digest_match = (source_audit_registry_digest_recorded == source_audit_registry_digest_recomputed)
        if source_audit_registry_digest_match:
            reason_codes.append("DISTRIBUTION_SOURCE_AUDIT_REGISTRY_DIGEST_MATCH")
        else:
            reason_codes.append("DISTRIBUTION_SOURCE_AUDIT_REGISTRY_DIGEST_MISMATCH")
            publication_gate_reasons.append("Source audit registry digest mismatch.")
    else:
        reason_codes.append("DISTRIBUTION_SOURCE_AUDIT_REGISTRY_INVALID")
        publication_gate_reasons.append("Failed to load source audit registry index.")

    # 4. Verify channel policy
    allowed_channels = ent_dict.get("publication_channels_allowed", [])
    blocked_channels = ent_dict.get("publication_channels_blocked", [])
    
    policy_ok, policy_reasons = validate_waveguide_distribution_channel_policy(allowed_channels, blocked_channels)
    for rc in policy_reasons:
        reason_codes.append(rc)
    
    metadata_only_channels_verified = policy_ok
    forbidden_channels_blocked = policy_ok
    if not policy_ok:
        publication_gate_reasons.append("Channel policy violation (forbidden channel allowed or required blocked channel missing).")

    # 5. Look up matching registry entry to verify audit state
    matching_reg_entry = None
    if registry_dict:
        reg_entries = registry_dict.get("entries", [])
        for re in reg_entries:
            if re.get("rc_id") == rc_id:
                matching_reg_entry = re
                break

    if matching_reg_entry:
        reason_codes.append("DISTRIBUTION_SOURCE_AUDIT_ENTRY_REFERENCED")
        audit_status = matching_reg_entry.get("audit_status", "")
        if audit_status in ("audit_registered", "audit_verified"):
            reason_codes.append("DISTRIBUTION_RC_AUDIT_VERIFIED")
        else:
            publication_gate_reasons.append(f"Source registry entry status is '{audit_status}', not audit_registered.")
    else:
        publication_gate_reasons.append(f"No corresponding registry entry found for RC ID '{rc_id}'.")

    # Final readiness status mapping
    if pub_status == "publication_ready":
        reason_codes.append("DISTRIBUTION_RC_PUBLICATION_READY")
        if not publication_gate_reasons:
            distribution_readiness_status = "distribution_ready"
            reason_codes.append("DISTRIBUTION_RC_READY")
            reason_codes.append("DISTRIBUTION_READINESS_VERIFIED")
        else:
            distribution_readiness_status = "distribution_blocked"
            reason_codes.append("DISTRIBUTION_RC_BLOCKED")
            reason_codes.append("DISTRIBUTION_READINESS_BLOCKED")
    elif pub_status == "publication_blocked":
        distribution_readiness_status = "distribution_blocked"
        reason_codes.append("DISTRIBUTION_RC_BLOCKED")
        reason_codes.append("DISTRIBUTION_READINESS_BLOCKED")
    elif pub_status == "publication_pending":
        distribution_readiness_status = "distribution_pending"
        reason_codes.append("DISTRIBUTION_READINESS_BLOCKED")
    else:
        distribution_readiness_status = "distribution_invalid"
        reason_codes.append("DISTRIBUTION_READINESS_INVALID")

    # Preserved digests
    if ent_dict.get("certification_bundle_digest"):
        reason_codes.append("DISTRIBUTION_BUNDLE_DIGEST_REFERENCED")
    if ent_dict.get("audit_report_digest"):
        reason_codes.append("DISTRIBUTION_AUDIT_REPORT_DIGEST_REFERENCED")
    if ent_dict.get("audit_case_digest"):
        reason_codes.append("DISTRIBUTION_AUDIT_CASE_DIGEST_REFERENCED")
    if ent_dict.get("final_output_payload_digests"):
        reason_codes.append("DISTRIBUTION_FINAL_OUTPUT_DIGESTS_REFERENCED")

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reason_codes.append("DISTRIBUTION_SOFTWARE_CAVEAT_INCLUDED")

    case = WaveguideDistributionReadinessAuditCase(
        distribution_audit_case_id=f"SOL-WAVEGUIDE-DISTRIBUTION-AUDIT-CASE-{rc_id}",
        publication_manifest_id=ent_dict.get("publication_manifest_id", "SOL-WAVEGUIDE-CERTIFIED-RELEASE-PUBLICATION-MANIFEST"),
        publication_manifest_path=manifest_path,
        publication_manifest_digest_recorded=pub_manifest_digest_recorded,
        publication_manifest_digest_recomputed=pub_manifest_digest_recomputed,
        publication_manifest_digest_match=pub_manifest_digest_match,
        publication_entry_id=ent_dict.get("publication_entry_id", ""),
        publication_entry_digest_recorded=pub_entry_digest_recorded,
        publication_entry_digest_recomputed=pub_entry_digest_recomputed,
        publication_entry_digest_match=pub_entry_digest_match,
        rc_id=rc_id,
        candidate_level=candidate_level,
        publication_status=pub_status,
        distribution_readiness_status=distribution_readiness_status,
        source_audit_registry_digest_recorded=source_audit_registry_digest_recorded,
        source_audit_registry_digest_recomputed=source_audit_registry_digest_recomputed,
        source_audit_registry_digest_match=source_audit_registry_digest_match,
        source_audit_registry_valid=source_audit_registry_valid,
        source_audit_registry_entry_digest=ent_dict.get("source_audit_registry_entry_digest", ""),
        certification_bundle_id=ent_dict.get("certification_bundle_id", ""),
        certification_bundle_digest=ent_dict.get("certification_bundle_digest", ""),
        audit_report_digest=ent_dict.get("audit_report_digest", ""),
        audit_case_digest=ent_dict.get("audit_case_digest", ""),
        audit_status=ent_dict.get("audit_status", ""),
        audit_report_status=ent_dict.get("audit_report_status", ""),
        target_rc_approved=ent_dict.get("target_rc_approved", False),
        runtime_capability_valid=ent_dict.get("runtime_capability_valid", False),
        compiler_session_registry_valid=ent_dict.get("compiler_session_registry_valid", False),
        artifact_digest_mismatch_count=ent_dict.get("artifact_digest_mismatch_count", 0),
        artifact_validation_failure_count=ent_dict.get("artifact_validation_failure_count", 0),
        registered_session_count=ent_dict.get("registered_session_count", 0),
        registered_rejection_session_count=ent_dict.get("registered_rejection_session_count", 0),
        final_output_payload_digests=sorted(ent_dict.get("final_output_payload_digests", [])),
        allowed_channels=sorted(allowed_channels),
        blocked_channels=sorted(blocked_channels),
        metadata_only_channels_verified=metadata_only_channels_verified,
        forbidden_channels_blocked=forbidden_channels_blocked,
        publication_gate_reasons=sorted(publication_gate_reasons),
        reason_codes=sorted(list(set(reason_codes))),
        notes=sorted(ent_dict.get("notes", [])),
        software_validation_caveat=software_validation_caveat,
        distribution_audit_case_digest=""
    )
    case.distribution_audit_case_digest = hash_waveguide_distribution_readiness_audit_case(case)
    return case


def validate_waveguide_publication_manifest_independently(
    pub_manifest_path_or_dict: Any,
    registry_path_or_dict: Any
) -> Tuple[bool, List[str]]:
    """
    Independently reloads the manifest and re-verifies its digests and contents.
    """
    reasons = []
    is_valid = True

    # 1. Resolve manifest
    manifest_dict = None
    if isinstance(pub_manifest_path_or_dict, str):
        path = normalize_to_repo_path(pub_manifest_path_or_dict)
        full_path = os.path.join(REPO_ROOT, path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    manifest_dict = json.load(f)
            except Exception:
                is_valid = False
        else:
            is_valid = False
    elif hasattr(pub_manifest_path_or_dict, "__dict__"):
        manifest_dict = asdict(pub_manifest_path_or_dict)
    elif isinstance(pub_manifest_path_or_dict, dict):
        manifest_dict = dict(pub_manifest_path_or_dict)
    else:
        is_valid = False

    if not is_valid or not manifest_dict:
        reasons.append("DISTRIBUTION_PUBLICATION_MANIFEST_INVALID")
        return False, reasons

    # Structural check
    ok, val_reasons = validate_waveguide_certified_release_publication_manifest(manifest_dict)
    for r in val_reasons:
        reasons.append(r.replace("PUBLICATION_MANIFEST_", "DISTRIBUTION_PUBLICATION_MANIFEST_"))

    # Digest verification
    rec_digest = recompute_waveguide_publication_manifest_digest(manifest_dict)
    given_digest = manifest_dict.get("publication_manifest_digest", "")
    if rec_digest == given_digest:
        reasons.append("DISTRIBUTION_PUBLICATION_MANIFEST_DIGEST_MATCH")
    else:
        is_valid = False
        reasons.append("DISTRIBUTION_PUBLICATION_MANIFEST_DIGEST_MISMATCH")

    # Entries digest check
    entries = manifest_dict.get("publication_entries", [])
    for e in entries:
        rec_e_digest = recompute_waveguide_publication_entry_digest(e)
        given_e_digest = e.get("publication_entry_digest", "")
        if rec_e_digest != given_e_digest:
            is_valid = False
            reasons.append("DISTRIBUTION_PUBLICATION_ENTRY_DIGEST_MISMATCH")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_distribution_readiness_audit_report(
    pub_manifest_path_or_dict: Any,
    registry_path_or_dict: Any
) -> WaveguideDistributionReadinessAuditReport:
    """
    Builds a deterministic top-level distribution-readiness audit report.
    """
    manifest_dict = None
    load_failed = False

    # 1. Load manifest
    if isinstance(pub_manifest_path_or_dict, str):
        path = normalize_to_repo_path(pub_manifest_path_or_dict)
        full_path = os.path.join(REPO_ROOT, path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    manifest_dict = json.load(f)
            except Exception:
                load_failed = True
        else:
            load_failed = True
    elif hasattr(pub_manifest_path_or_dict, "__dict__"):
        manifest_dict = asdict(pub_manifest_path_or_dict)
    elif isinstance(pub_manifest_path_or_dict, dict):
        manifest_dict = dict(pub_manifest_path_or_dict)
    else:
        load_failed = True

    if load_failed or not manifest_dict:
        # Build invalid report
        software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
        report = WaveguideDistributionReadinessAuditReport(
            distribution_audit_report_id="SOL-WAVEGUIDE-DISTRIBUTION-READINESS-AUDIT-REPORT",
            distribution_audit_report_version=1,
            distribution_audit_report_status="distribution_readiness_invalid",
            source_publication_manifest_digest="",
            source_audit_registry_digest="",
            audited_cases=[],
            distribution_ready_rcs=[],
            distribution_blocked_rcs=[],
            distribution_pending_rcs=[],
            distribution_invalid_rcs=[],
            distribution_ready_count=0,
            distribution_blocked_count=0,
            distribution_pending_count=0,
            distribution_invalid_count=0,
            rc1_distribution_count=0,
            rc2_distribution_count=0,
            candidate_levels_indexed=[],
            certification_bundle_ids=[],
            certification_bundle_digests=[],
            audit_report_digests=[],
            audit_case_digests=[],
            audit_registry_entry_digests=[],
            publication_entry_digests=[],
            final_output_payload_digests=[],
            allowed_channels_indexed=[],
            blocked_channels_indexed=[],
            metadata_only_channels_verified=False,
            forbidden_channels_blocked=False,
            reason_codes=["DISTRIBUTION_READINESS_INVALID", "DISTRIBUTION_PUBLICATION_MANIFEST_INVALID"],
            software_validation_caveat=software_validation_caveat,
            distribution_audit_report_digest=""
        )
        report.distribution_audit_report_digest = hash_waveguide_distribution_readiness_audit_report(report)
        return report

    source_manifest_digest = manifest_dict.get("publication_manifest_digest", "")
    source_registry_digest = manifest_dict.get("source_audit_registry_digest", "")

    # Build cases
    cases = []
    raw_entries = manifest_dict.get("publication_entries", [])
    for ent in raw_entries:
        case = build_waveguide_distribution_readiness_audit_case(ent, manifest_dict, registry_path_or_dict)
        cases.append(case)

    # Sort cases deterministically
    def case_sort_key(c):
        return (
            c.rc_id,
            c.candidate_level,
            c.distribution_readiness_status,
            c.publication_entry_digest_recorded
        )
    sorted_cases = sorted(cases, key=case_sort_key)

    distribution_ready_rcs = []
    distribution_blocked_rcs = []
    distribution_pending_rcs = []
    distribution_invalid_rcs = []

    distribution_ready_count = 0
    distribution_blocked_count = 0
    distribution_pending_count = 0
    distribution_invalid_count = 0
    rc1_distribution_count = 0
    rc2_distribution_count = 0

    candidate_levels_indexed = []
    certification_bundle_ids = []
    certification_bundle_digests = []
    audit_report_digests = []
    audit_case_digests = []
    audit_registry_entry_digests = []
    publication_entry_digests = []
    final_output_payload_digests = []
    allowed_channels_indexed = []
    blocked_channels_indexed = []

    metadata_only_channels_verified = True
    forbidden_channels_blocked = True

    all_reasons = ["DISTRIBUTION_COUNTS_VALID", "DISTRIBUTION_FORBIDDEN_CHANNELS_BLOCKED"]

    for case in sorted_cases:
        rc_id = case.rc_id
        status = case.distribution_readiness_status
        cb_id = case.certification_bundle_id
        level = case.candidate_level

        # Category mapping
        if status == "distribution_ready":
            distribution_ready_count += 1
            if rc_id and rc_id not in distribution_ready_rcs:
                distribution_ready_rcs.append(rc_id)
        elif status == "distribution_blocked":
            distribution_blocked_count += 1
            if rc_id and rc_id not in distribution_blocked_rcs:
                distribution_blocked_rcs.append(rc_id)
        elif status == "distribution_pending":
            distribution_pending_count += 1
            if rc_id and rc_id not in distribution_pending_rcs:
                distribution_pending_rcs.append(rc_id)
        else:
            distribution_invalid_count += 1
            if rc_id and rc_id not in distribution_invalid_rcs:
                distribution_invalid_rcs.append(rc_id)

        if "RC1" in rc_id:
            rc1_distribution_count += 1
        elif "RC2" in rc_id:
            rc2_distribution_count += 1

        if not case.metadata_only_channels_verified:
            metadata_only_channels_verified = False
        if not case.forbidden_channels_blocked:
            forbidden_channels_blocked = False

        # Unique lists
        def add_unique(lst, val):
            if val and val not in lst:
                lst.append(val)

        add_unique(candidate_levels_indexed, level)
        add_unique(certification_bundle_ids, cb_id)
        add_unique(certification_bundle_digests, case.certification_bundle_digest)
        add_unique(audit_report_digests, case.audit_report_digest)
        add_unique(audit_case_digests, case.audit_case_digest)
        add_unique(audit_registry_entry_digests, case.source_audit_registry_entry_digest)
        add_unique(publication_entry_digests, case.publication_entry_digest_recorded)
        
        for digest in case.final_output_payload_digests:
            add_unique(final_output_payload_digests, digest)
            
        for ch in case.allowed_channels:
            add_unique(allowed_channels_indexed, ch)
            
        for ch in case.blocked_channels:
            add_unique(blocked_channels_indexed, ch)

        for code in case.reason_codes:
            if code not in all_reasons:
                all_reasons.append(code)

    # Sort all lists
    distribution_ready_rcs = sorted(distribution_ready_rcs)
    distribution_blocked_rcs = sorted(distribution_blocked_rcs)
    distribution_pending_rcs = sorted(distribution_pending_rcs)
    distribution_invalid_rcs = sorted(distribution_invalid_rcs)

    candidate_levels_indexed = sorted(candidate_levels_indexed)
    certification_bundle_ids = sorted(certification_bundle_ids)
    certification_bundle_digests = sorted(certification_bundle_digests)
    audit_report_digests = sorted(audit_report_digests)
    audit_case_digests = sorted(audit_case_digests)
    audit_registry_entry_digests = sorted(audit_registry_entry_digests)
    publication_entry_digests = sorted(publication_entry_digests)
    final_output_payload_digests = sorted(final_output_payload_digests)
    allowed_channels_indexed = sorted(allowed_channels_indexed)
    blocked_channels_indexed = sorted(blocked_channels_indexed)

    # Look up pending RCs in registry
    approved_rcs = []
    registry_path_file = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json")
    if os.path.exists(registry_path_file):
        try:
            with open(registry_path_file, "r", encoding="utf-8") as f:
                reg_data = json.load(f)
            approved_rcs = reg_data.get("approved_rc_ids", [])
        except Exception:
            pass
    if not approved_rcs:
        approved_rcs = ["SOL-WAVEGUIDE-RC1", "SOL-WAVEGUIDE-RC2"]
    
    catalog_rcs = distribution_ready_rcs + distribution_blocked_rcs
    distribution_pending_rcs = sorted(list(set(approved_rcs) - set(catalog_rcs)))
    distribution_pending_count = len(distribution_pending_rcs)

    # Determine status
    if distribution_blocked_count > 0 or distribution_invalid_count > 0 or len(sorted_cases) == 0:
        report_status = "distribution_readiness_blocked"
        all_reasons.append("DISTRIBUTION_READINESS_BLOCKED")
    else:
        report_status = "distribution_readiness_verified"
        all_reasons.append("DISTRIBUTION_READINESS_VERIFIED")

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    report = WaveguideDistributionReadinessAuditReport(
        distribution_audit_report_id="SOL-WAVEGUIDE-DISTRIBUTION-READINESS-AUDIT-REPORT",
        distribution_audit_report_version=1,
        distribution_audit_report_status=report_status,
        source_publication_manifest_digest=source_manifest_digest,
        source_audit_registry_digest=source_registry_digest,
        audited_cases=sorted_cases,
        distribution_ready_rcs=distribution_ready_rcs,
        distribution_blocked_rcs=distribution_blocked_rcs,
        distribution_pending_rcs=distribution_pending_rcs,
        distribution_invalid_rcs=distribution_invalid_rcs,
        distribution_ready_count=distribution_ready_count,
        distribution_blocked_count=distribution_blocked_count,
        distribution_pending_count=distribution_pending_count,
        distribution_invalid_count=distribution_invalid_count,
        rc1_distribution_count=rc1_distribution_count,
        rc2_distribution_count=rc2_distribution_count,
        candidate_levels_indexed=candidate_levels_indexed,
        certification_bundle_ids=certification_bundle_ids,
        certification_bundle_digests=certification_bundle_digests,
        audit_report_digests=audit_report_digests,
        audit_case_digests=audit_case_digests,
        audit_registry_entry_digests=audit_registry_entry_digests,
        publication_entry_digests=publication_entry_digests,
        final_output_payload_digests=final_output_payload_digests,
        allowed_channels_indexed=allowed_channels_indexed,
        blocked_channels_indexed=blocked_channels_indexed,
        metadata_only_channels_verified=metadata_only_channels_verified,
        forbidden_channels_blocked=forbidden_channels_blocked,
        reason_codes=sorted(list(set(all_reasons))),
        software_validation_caveat=software_validation_caveat,
        distribution_audit_report_digest=""
    )
    report.distribution_audit_report_digest = hash_waveguide_distribution_readiness_audit_report(report)
    return report


def validate_waveguide_distribution_readiness_audit_report(report: Any) -> Tuple[bool, List[str]]:
    """
    Validates a distribution readiness audit report.
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
    given_digest = r_dict.get("distribution_audit_report_digest")
    if not given_digest:
        is_valid = False
        reasons.append("DISTRIBUTION_READINESS_INVALID")
    else:
        recomputed = hash_waveguide_distribution_readiness_audit_report(r_dict)
        if recomputed == given_digest:
            reasons.append("DISTRIBUTION_AUDIT_REPORT_DIGEST_VALID")
        else:
            is_valid = False
            reasons.append("DISTRIBUTION_READINESS_INVALID")

    # 2. Check cases validation
    cases = r_dict.get("audited_cases", [])
    case_statuses = []
    for case in cases:
        # Validate each case using digest check
        c_digest = case.get("distribution_audit_case_digest") if isinstance(case, dict) else case.distribution_audit_case_digest
        if not c_digest:
            is_valid = False
        else:
            recomputed_case_digest = hash_waveguide_distribution_readiness_audit_case(case)
            if recomputed_case_digest != c_digest:
                is_valid = False
        
        status = case.get("distribution_readiness_status") if isinstance(case, dict) else case.distribution_readiness_status
        case_statuses.append(status)

    # 3. Check counts consistency
    ready_count = r_dict.get("distribution_ready_count", 0)
    blocked_count = r_dict.get("distribution_blocked_count", 0)
    invalid_count = r_dict.get("distribution_invalid_count", 0)
    
    if (ready_count != case_statuses.count("distribution_ready") or
        blocked_count != case_statuses.count("distribution_blocked") or
        invalid_count != case_statuses.count("distribution_invalid")):
        is_valid = False
        reasons.append("DISTRIBUTION_READINESS_INVALID")

    # 4. Check status readiness consistency
    report_status = r_dict.get("distribution_audit_report_status")
    if report_status == "distribution_readiness_verified":
        if blocked_count > 0 or invalid_count > 0 or len(cases) == 0:
            is_valid = False
            reasons.append("DISTRIBUTION_READINESS_INVALID")

    # Add codes if valid
    if is_valid:
        for rc in r_dict.get("reason_codes", []):
            if rc.startswith("DISTRIBUTION_"):
                reasons.append(rc)
        reasons.append("DISTRIBUTION_READINESS_VERIFIED")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_distribution_readiness_audit_report(report: Any) -> str:
    """
    Returns a plaintext summary of the distribution readiness report.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE DISTRIBUTION READINESS AUDIT REPORT",
        "============================================================",
        f"Report ID:        {r_dict.get('distribution_audit_report_id')}",
        f"Version:          {r_dict.get('distribution_audit_report_version')}",
        f"Status:           {r_dict.get('distribution_audit_report_status', '').upper()}",
        f"Report Digest:    {r_dict.get('distribution_audit_report_digest')}",
        "------------------------------------------------------------",
        "Distribution Ready Release Candidates:"
    ]

    for rc in r_dict.get("distribution_ready_rcs", []):
        lines.append(f"  * {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Blocked Release Candidates:")
    for rc in r_dict.get("distribution_blocked_rcs", []):
        lines.append(f"  * {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Audited Cases Details:")
    for case in r_dict.get("audited_cases", []):
        lines.append(
            f"  - RC: {case.get('rc_id')} ({case.get('candidate_level')}) "
            f"-> status: {case.get('distribution_readiness_status')}"
        )

    lines.append("------------------------------------------------------------")
    lines.append("Allowed Channels Indexed:")
    for ch in r_dict.get("allowed_channels_indexed", []):
        lines.append(f"  - {ch}")

    lines.append("------------------------------------------------------------")
    lines.append("Blocked Channels Indexed:")
    for ch in r_dict.get("blocked_channels_indexed", []):
        lines.append(f"  - {ch}")

    lines.append("------------------------------------------------------------")
    lines.append("Forbidden Channels Blocked: " + str(r_dict.get("forbidden_channels_blocked")))
    lines.append("Metadata-only Channels Verified: " + str(r_dict.get("metadata_only_channels_verified")))
    
    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in r_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {r_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_distribution_readiness_audit_report(report: Any, filepath: str) -> None:
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


def compare_waveguide_distribution_readiness_audit_reports(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two readiness reports and returns differences.
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
        "report_id_match": l_dict.get("distribution_audit_report_id") == r_dict.get("distribution_audit_report_id"),
        "report_version_match": l_dict.get("distribution_audit_report_version") == r_dict.get("distribution_audit_report_version"),
        "report_status_match": l_dict.get("distribution_audit_report_status") == r_dict.get("distribution_audit_report_status"),
        "report_digest_match": l_dict.get("distribution_audit_report_digest") == r_dict.get("distribution_audit_report_digest"),
        "ready_rc_count_diff": l_dict.get("distribution_ready_count", 0) - r_dict.get("distribution_ready_count", 0),
        "blocked_rc_count_diff": l_dict.get("distribution_blocked_count", 0) - r_dict.get("distribution_blocked_count", 0),
        "ready_rcs_left_only": list(set(l_dict.get("distribution_ready_rcs", [])) - set(r_dict.get("distribution_ready_rcs", []))),
        "ready_rcs_right_only": list(set(r_dict.get("distribution_ready_rcs", [])) - set(l_dict.get("distribution_ready_rcs", []))),
        "blocked_rcs_left_only": list(set(l_dict.get("distribution_blocked_rcs", [])) - set(r_dict.get("distribution_blocked_rcs", []))),
        "blocked_rcs_right_only": list(set(r_dict.get("distribution_blocked_rcs", [])) - set(l_dict.get("distribution_blocked_rcs", [])))
    }
    
    diff["all_match"] = (
        diff["report_id_match"] and
        diff["report_version_match"] and
        diff["report_status_match"] and
        diff["report_digest_match"] and
        diff["ready_rc_count_diff"] == 0 and
        diff["blocked_rc_count_diff"] == 0 and
        not diff["ready_rcs_left_only"] and
        not diff["ready_rcs_right_only"] and
        not diff["blocked_rcs_left_only"] and
        not diff["blocked_rcs_right_only"]
    )
    return diff


def index_waveguide_distribution_readiness_cases_by_rc(cases: List[Any]) -> Dict[str, Any]:
    """
    Indexes cases mapping rc_id to case dictionary.
    """
    idx = {}
    for c in cases:
        if hasattr(c, "__dict__"):
            c_dict = asdict(c)
        else:
            c_dict = dict(c)
        idx[c_dict.get("rc_id")] = c_dict
    return idx


def index_waveguide_distribution_readiness_cases_by_status(cases: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes cases mapping distribution_readiness_status to lists of cases.
    """
    idx = {}
    for c in cases:
        if hasattr(c, "__dict__"):
            c_dict = asdict(c)
        else:
            c_dict = dict(c)
        status = c_dict.get("distribution_readiness_status")
        if status not in idx:
            idx[status] = []
        idx[status].append(c_dict)
    return idx


def index_waveguide_distribution_readiness_cases_by_channel(cases: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes cases mapping allowed distribution channels to lists of cases.
    """
    idx = {}
    for c in cases:
        if hasattr(c, "__dict__"):
            c_dict = asdict(c)
        else:
            c_dict = dict(c)
        allowed = c_dict.get("allowed_channels", [])
        for channel in allowed:
            if channel not in idx:
                idx[channel] = []
            idx[channel].append(c_dict)
    return idx
