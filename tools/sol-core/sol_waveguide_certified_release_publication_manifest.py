# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Certified Release Publication Manifest.
Consumes the verified Release Certification Index / RC Audit Registry
and produces a deterministic publication-readiness catalog of release candidates.
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
    validate_waveguide_release_certification_index_entry,
    WaveguideReleaseCertificationIndexEntry,
    WaveguideReleaseCertificationIndex
)


@dataclass
class WaveguideCertifiedReleasePublicationEntry:
    publication_entry_id: str
    rc_id: str
    candidate_level: str
    publication_status: str  # publication_ready, publication_blocked, publication_pending, publication_invalid
    source_audit_registry_entry_digest: str
    certification_bundle_id: str
    certification_bundle_digest: str
    audit_report_digest: str
    audit_case_digest: str
    audit_status: str
    audit_report_status: str
    artifact_digest_mismatch_count: int
    artifact_validation_failure_count: int
    target_rc_approved: bool
    runtime_capability_valid: bool
    compiler_session_registry_valid: bool
    registered_session_count: int
    registered_rejection_session_count: int
    final_output_payload_digests: List[str]
    publication_channels_allowed: List[str]
    publication_channels_blocked: List[str]
    publication_gate_reasons: List[str]
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    publication_entry_digest: str = ""


@dataclass
class WaveguideCertifiedReleasePublicationManifest:
    publication_manifest_id: str
    publication_manifest_version: int
    publication_manifest_status: str  # publication_manifest_ready, publication_manifest_blocked, etc.
    source_audit_registry_digest: str
    publication_entries: List[WaveguideCertifiedReleasePublicationEntry]
    publishable_rcs: List[str]
    blocked_rcs: List[str]
    pending_rcs: List[str]
    invalid_rcs: List[str]
    publishable_rc_count: int
    blocked_rc_count: int
    pending_rc_count: int
    invalid_rc_count: int
    rc1_publication_count: int
    rc2_publication_count: int
    candidate_levels_indexed: List[str]
    certification_bundle_ids: List[str]
    certification_bundle_digests: List[str]
    audit_report_digests: List[str]
    audit_case_digests: List[str]
    audit_registry_entry_digests: List[str]
    final_output_payload_digests: List[str]
    publication_channel_policy: Dict[str, List[str]]
    publication_readiness_catalog: List[Dict[str, Any]]
    reason_codes: List[str]
    software_validation_caveat: str
    publication_manifest_digest: str = ""


def hash_waveguide_certified_release_publication_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation
    excluding the self-referential publication_entry_digest field.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or a dataclass instance")

    e_dict_copy = dict(e_dict)
    e_dict_copy.pop("publication_entry_digest", None)
    return hash_data(e_dict_copy)


def hash_waveguide_certified_release_publication_manifest(manifest: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation
    excluding the self-referential publication_manifest_digest field.
    """
    if hasattr(manifest, "__dict__"):
        m_dict = asdict(manifest)
    elif isinstance(manifest, dict):
        m_dict = dict(manifest)
    else:
        raise TypeError("manifest must be a dictionary or a dataclass instance")

    m_dict_copy = dict(m_dict)
    m_dict_copy.pop("publication_manifest_digest", None)
    return hash_data(m_dict_copy)


def build_waveguide_certified_release_publication_entry(
    registry_entry_or_dict: Any,
    registry_digest: Optional[str] = None
) -> WaveguideCertifiedReleasePublicationEntry:
    """
    Builds a deterministic publication entry from a Release Certification Index entry.
    """
    if hasattr(registry_entry_or_dict, "__dict__"):
        reg_dict = asdict(registry_entry_or_dict)
    elif isinstance(registry_entry_or_dict, dict):
        reg_dict = dict(registry_entry_or_dict)
    else:
        reg_dict = {}

    rc_id = reg_dict.get("rc_id", "UNKNOWN")
    candidate_level = reg_dict.get("candidate_level", "Unknown")
    
    # 1. Determine status and metadata
    audit_status = reg_dict.get("audit_status", "audit_invalid")
    audit_report_status = reg_dict.get("audit_report_status", "audit_report_invalid")
    
    source_digest = reg_dict.get("registry_entry_digest", "")
    
    # Default disallowed/blocked channels for this version
    blocked_channels = [
        "external_key_signing",
        "legal_certification_claim",
        "production_deployment",
        "quantum_hardware_certification"
    ]
    
    # Check validity of source entry
    # A source entry is valid if it passes index validator logic
    # We can perform checks directly for cleaner code.
    mismatch_c = reg_dict.get("artifact_digest_mismatch_count", 0)
    failure_c = reg_dict.get("artifact_validation_failure_count", 0)
    target_approved = reg_dict.get("target_rc_approved", False)
    capability_valid = reg_dict.get("runtime_capability_valid", False)
    session_registry_valid = reg_dict.get("compiler_session_registry_valid", False)
    
    publication_gate_reasons = []
    reason_codes = ["PUBLICATION_ENTRY_CANONICAL"]
    
    if rc_id == "UNKNOWN":
        publication_status = "publication_invalid"
        publication_channels_allowed = []
        publication_gate_reasons.append("Unknown release candidate identifier.")
        reason_codes.append("PUBLICATION_RC_BLOCKED")
    elif audit_status not in ("audit_registered", "audit_verified"):
        publication_status = "publication_blocked"
        publication_channels_allowed = []
        publication_gate_reasons.append(f"Audit status is '{audit_status}', not audit_registered.")
        reason_codes.append("PUBLICATION_RC_BLOCKED")
    elif (mismatch_c != 0 or failure_c != 0 or not target_approved or 
          not capability_valid or not session_registry_valid):
        publication_status = "publication_blocked"
        publication_channels_allowed = []
        if mismatch_c != 0:
            publication_gate_reasons.append(f"Artifact digest mismatch count is non-zero ({mismatch_c}).")
        if failure_c != 0:
            publication_gate_reasons.append(f"Artifact validation failure count is non-zero ({failure_c}).")
        if not target_approved:
            publication_gate_reasons.append("Target release candidate is not approved in release registry.")
        if not capability_valid:
            publication_gate_reasons.append("Runtime capability resolution is invalid.")
        if not session_registry_valid:
            publication_gate_reasons.append("Governed compiler session registry is invalid.")
        reason_codes.append("PUBLICATION_RC_BLOCKED")
    else:
        publication_status = "publication_ready"
        publication_channels_allowed = [
            "artifact_catalog_publication",
            "documentation_publication",
            "internal_distribution"
        ]
        reason_codes.append("PUBLICATION_RC_READY")
        reason_codes.append("PUBLICATION_RC_AUDIT_VERIFIED")

    # Add other metadata references
    if reg_dict.get("certification_bundle_digest"):
        reason_codes.append("PUBLICATION_BUNDLE_DIGEST_REFERENCED")
    if reg_dict.get("audit_report_digest"):
        reason_codes.append("PUBLICATION_AUDIT_REPORT_DIGEST_REFERENCED")
    if reg_dict.get("audit_case_digest"):
        reason_codes.append("PUBLICATION_AUDIT_CASE_DIGEST_REFERENCED")
    if reg_dict.get("final_output_payload_digests"):
        reason_codes.append("PUBLICATION_FINAL_OUTPUT_DIGESTS_REFERENCED")
    if source_digest:
        reason_codes.append("PUBLICATION_SOURCE_AUDIT_ENTRY_REFERENCED")

    # Allowed channels policies
    if "internal_distribution" in publication_channels_allowed:
        reason_codes.append("PUBLICATION_INTERNAL_DISTRIBUTION_ALLOWED")
    if "documentation_publication" in publication_channels_allowed:
        reason_codes.append("PUBLICATION_DOCUMENTATION_ALLOWED")
    if "artifact_catalog_publication" in publication_channels_allowed:
        reason_codes.append("PUBLICATION_ARTIFACT_CATALOG_ALLOWED")

    # Blocked channels policies
    if "production_deployment" in blocked_channels:
        reason_codes.append("PUBLICATION_PRODUCTION_DEPLOYMENT_BLOCKED")
    if "external_key_signing" in blocked_channels:
        reason_codes.append("PUBLICATION_EXTERNAL_SIGNING_BLOCKED")
    if "legal_certification_claim" in blocked_channels:
        reason_codes.append("PUBLICATION_LEGAL_CLAIM_BLOCKED")
    if "quantum_hardware_certification" in blocked_channels:
        reason_codes.append("PUBLICATION_QUANTUM_HARDWARE_CLAIM_BLOCKED")

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reason_codes.append("PUBLICATION_SOFTWARE_CAVEAT_INCLUDED")

    entry = WaveguideCertifiedReleasePublicationEntry(
        publication_entry_id=f"SOL-WAVEGUIDE-PUBLICATION-ENTRY-{rc_id}",
        rc_id=rc_id,
        candidate_level=candidate_level,
        publication_status=publication_status,
        source_audit_registry_entry_digest=source_digest,
        certification_bundle_id=reg_dict.get("certification_bundle_id", ""),
        certification_bundle_digest=reg_dict.get("certification_bundle_digest", ""),
        audit_report_digest=reg_dict.get("audit_report_digest", ""),
        audit_case_digest=reg_dict.get("audit_case_digest", ""),
        audit_status=audit_status,
        audit_report_status=audit_report_status,
        artifact_digest_mismatch_count=mismatch_c,
        artifact_validation_failure_count=failure_c,
        target_rc_approved=target_approved,
        runtime_capability_valid=capability_valid,
        compiler_session_registry_valid=session_registry_valid,
        registered_session_count=reg_dict.get("registered_session_count", 0),
        registered_rejection_session_count=reg_dict.get("registered_rejection_session_count", 0),
        final_output_payload_digests=sorted(reg_dict.get("final_output_payload_digests", [])),
        publication_channels_allowed=sorted(publication_channels_allowed),
        publication_channels_blocked=sorted(blocked_channels),
        publication_gate_reasons=sorted(publication_gate_reasons),
        reason_codes=sorted(list(set(reason_codes))),
        notes=sorted(reg_dict.get("notes", [])),
        software_validation_caveat=software_validation_caveat,
        publication_entry_digest=""
    )
    entry.publication_entry_digest = hash_waveguide_certified_release_publication_entry(entry)
    return entry


def validate_waveguide_certified_release_publication_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Validates a publication manifest entry.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or a dataclass instance")

    reasons = []
    is_valid = True

    # 1. Basic presence checks
    rc_id = e_dict.get("rc_id")
    candidate_level = e_dict.get("candidate_level")
    certification_bundle_id = e_dict.get("certification_bundle_id")
    certification_bundle_digest = e_dict.get("certification_bundle_digest")
    audit_report_digest = e_dict.get("audit_report_digest")
    audit_case_digest = e_dict.get("audit_case_digest")
    source_digest = e_dict.get("source_audit_registry_entry_digest")
    software_validation_caveat = e_dict.get("software_validation_caveat")

    if not rc_id or rc_id == "UNKNOWN":
        is_valid = False
        reasons.append("PUBLICATION_RC_BLOCKED")
    if not candidate_level or candidate_level == "Unknown":
        is_valid = False
        reasons.append("PUBLICATION_RC_BLOCKED")
    if not certification_bundle_id or not certification_bundle_digest:
        is_valid = False
        reasons.append("PUBLICATION_RC_BLOCKED")
    if not audit_report_digest or not audit_case_digest or not source_digest:
        is_valid = False
        reasons.append("PUBLICATION_RC_BLOCKED")
    if not software_validation_caveat or "sandbox" not in software_validation_caveat.lower():
        is_valid = False
        reasons.append("PUBLICATION_RC_BLOCKED")

    # 2. Check digest validates
    given_digest = e_dict.get("publication_entry_digest")
    if given_digest:
        recomputed = hash_waveguide_certified_release_publication_entry(e_dict)
        if recomputed == given_digest:
            reasons.append("PUBLICATION_ENTRY_DIGEST_VALID")
        else:
            is_valid = False
            reasons.append("PUBLICATION_MANIFEST_INVALID")
    else:
        is_valid = False
        reasons.append("PUBLICATION_MANIFEST_INVALID")

    # 3. Check status consistency for ready entry
    publication_status = e_dict.get("publication_status")
    if publication_status == "publication_ready":
        # Strict validation checks
        mismatch_c = e_dict.get("artifact_digest_mismatch_count", 0)
        failure_c = e_dict.get("artifact_validation_failure_count", 0)
        target_approved = e_dict.get("target_rc_approved", False)
        capability_valid = e_dict.get("runtime_capability_valid", False)
        session_registry_valid = e_dict.get("compiler_session_registry_valid", False)

        if (mismatch_c != 0 or failure_c != 0 or not target_approved or 
            not capability_valid or not session_registry_valid):
            is_valid = False
            reasons.append("PUBLICATION_MANIFEST_INVALID")

        # Allowed channels should match default policy
        allowed = e_dict.get("publication_channels_allowed", [])
        if "production_deployment" in allowed or "external_key_signing" in allowed:
            is_valid = False
            reasons.append("PUBLICATION_MANIFEST_INVALID")

    # Add reasons from entry if valid
    if is_valid:
        for rc in e_dict.get("reason_codes", []):
            if rc.startswith("PUBLICATION_"):
                reasons.append(rc)
        reasons.append("PUBLICATION_ENTRY_CANONICAL")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_certified_release_publication_manifest(
    registry_path_or_dict: Any
) -> WaveguideCertifiedReleasePublicationManifest:
    """
    Builds a deterministic Certified Release Publication Manifest.
    """
    registry_dict = None
    load_failed = False

    # 1. Load/Resolve Registry
    if isinstance(registry_path_or_dict, str):
        path = normalize_to_repo_path(registry_path_or_dict)
        full_path = os.path.join(REPO_ROOT, path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    registry_dict = json.load(f)
            except Exception:
                load_failed = True
        else:
            load_failed = True
    elif hasattr(registry_path_or_dict, "__dict__"):
        registry_dict = asdict(registry_path_or_dict)
    elif isinstance(registry_path_or_dict, dict):
        registry_dict = dict(registry_path_or_dict)
    else:
        load_failed = True

    if load_failed or not registry_dict:
        # Build empty/invalid manifest
        software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
        manifest = WaveguideCertifiedReleasePublicationManifest(
            publication_manifest_id="SOL-WAVEGUIDE-CERTIFIED-RELEASE-PUBLICATION-MANIFEST",
            publication_manifest_version=1,
            publication_manifest_status="publication_manifest_invalid",
            source_audit_registry_digest="",
            publication_entries=[],
            publishable_rcs=[],
            blocked_rcs=[],
            pending_rcs=[],
            invalid_rcs=[],
            publishable_rc_count=0,
            blocked_rc_count=0,
            pending_rc_count=0,
            invalid_rc_count=0,
            rc1_publication_count=0,
            rc2_publication_count=0,
            candidate_levels_indexed=[],
            certification_bundle_ids=[],
            certification_bundle_digests=[],
            audit_report_digests=[],
            audit_case_digests=[],
            audit_registry_entry_digests=[],
            final_output_payload_digests=[],
            publication_channel_policy={
                "allowed": [],
                "blocked": []
            },
            publication_readiness_catalog=[],
            reason_codes=["PUBLICATION_MANIFEST_INVALID", "PUBLICATION_SOURCE_AUDIT_REGISTRY_INVALID"],
            software_validation_caveat=software_validation_caveat,
            publication_manifest_digest=""
        )
        manifest.publication_manifest_digest = hash_waveguide_certified_release_publication_manifest(manifest)
        return manifest

    source_registry_digest = registry_dict.get("audit_registry_digest", "")

    # Build entries from registry
    entries = []
    raw_entries = registry_dict.get("entries", [])
    for entry_dict in raw_entries:
        entry = build_waveguide_certified_release_publication_entry(entry_dict, source_registry_digest)
        entries.append(entry)

    # Sort entries deterministically
    def entry_sort_key(e):
        return (
            e.rc_id,
            e.candidate_level,
            e.publication_status,
            e.audit_report_digest
        )
    sorted_entries = sorted(entries, key=entry_sort_key)

    # Sort readiness catalog deterministically by lexical rc_id
    publication_readiness_catalog = []
    catalog_sorted = sorted(sorted_entries, key=lambda e: e.rc_id)
    for index_1, entry in enumerate(catalog_sorted):
        publication_readiness_catalog.append({
            "catalog_index": index_1 + 1,
            "rc_id": entry.rc_id,
            "candidate_level": entry.candidate_level,
            "publication_status": entry.publication_status,
            "certification_bundle_id": entry.certification_bundle_id,
            "certification_bundle_digest": entry.certification_bundle_digest,
            "audit_report_digest": entry.audit_report_digest,
            "audit_case_digest": entry.audit_case_digest,
            "allowed_channels": entry.publication_channels_allowed,
            "blocked_channels": entry.publication_channels_blocked
        })

    publishable_rcs = []
    blocked_rcs = []
    pending_rcs = []
    invalid_rcs = []

    publishable_rc_count = 0
    blocked_rc_count = 0
    pending_rc_count = 0
    invalid_rc_count = 0
    rc1_publication_count = 0
    rc2_publication_count = 0

    candidate_levels_indexed = []
    certification_bundle_ids = []
    certification_bundle_digests = []
    audit_report_digests = []
    audit_case_digests = []
    audit_registry_entry_digests = []
    final_output_payload_digests = []

    all_reasons = [
        "PUBLICATION_READINESS_CATALOG_CANONICAL",
        "PUBLICATION_COUNTS_VALID",
        "PUBLICATION_SOURCE_AUDIT_REGISTRY_VALID"
    ]

    for entry in sorted_entries:
        rc_id = entry.rc_id
        status = entry.publication_status
        cb_id = entry.certification_bundle_id
        level = entry.candidate_level

        # Category mapping
        if status == "publication_ready":
            publishable_rc_count += 1
            if rc_id and rc_id not in publishable_rcs:
                publishable_rcs.append(rc_id)
        elif status == "publication_blocked":
            blocked_rc_count += 1
            if rc_id and rc_id not in blocked_rcs:
                blocked_rcs.append(rc_id)
        elif status == "publication_pending":
            pending_rc_count += 1
            if rc_id and rc_id not in pending_rcs:
                pending_rcs.append(rc_id)
        else:
            invalid_rc_count += 1
            if rc_id and rc_id not in invalid_rcs:
                invalid_rcs.append(rc_id)

        if "RC1" in rc_id:
            rc1_publication_count += 1
        elif "RC2" in rc_id:
            rc2_publication_count += 1

        # Unique lists
        def add_unique(lst, val):
            if val and val not in lst:
                lst.append(val)

        add_unique(candidate_levels_indexed, level)
        add_unique(certification_bundle_ids, cb_id)
        add_unique(certification_bundle_digests, entry.certification_bundle_digest)
        add_unique(audit_report_digests, entry.audit_report_digest)
        add_unique(audit_case_digests, entry.audit_case_digest)
        add_unique(audit_registry_entry_digests, entry.source_audit_registry_entry_digest)
        
        for digest in entry.final_output_payload_digests:
            add_unique(final_output_payload_digests, digest)

        for code in entry.reason_codes:
            if code not in all_reasons:
                all_reasons.append(code)

    # Sort all lists
    publishable_rcs = sorted(publishable_rcs)
    blocked_rcs = sorted(blocked_rcs)
    pending_rcs = sorted(pending_rcs)
    invalid_rcs = sorted(invalid_rcs)

    candidate_levels_indexed = sorted(candidate_levels_indexed)
    certification_bundle_ids = sorted(certification_bundle_ids)
    certification_bundle_digests = sorted(certification_bundle_digests)
    audit_report_digests = sorted(audit_report_digests)
    audit_case_digests = sorted(audit_case_digests)
    audit_registry_entry_digests = sorted(audit_registry_entry_digests)
    final_output_payload_digests = sorted(final_output_payload_digests)

    # Read pending RCs from registry
    approved_rcs = []
    registry_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json")
    if os.path.exists(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                reg_data = json.load(f)
            approved_rcs = reg_data.get("approved_rc_ids", [])
        except Exception:
            pass
    if not approved_rcs:
        approved_rcs = ["SOL-WAVEGUIDE-RC1", "SOL-WAVEGUIDE-RC2"]
    
    # RCs that are approved in the registry but not in the catalog
    catalog_rcs = publishable_rcs + blocked_rcs
    pending_rcs = sorted(list(set(approved_rcs) - set(catalog_rcs)))
    pending_rc_count = len(pending_rcs)

    # Determine status
    if blocked_rc_count > 0 or invalid_rc_count > 0 or len(sorted_entries) == 0:
        manifest_status = "publication_manifest_blocked"
        all_reasons.append("PUBLICATION_MANIFEST_BLOCKED")
    else:
        manifest_status = "publication_manifest_ready"
        all_reasons.append("PUBLICATION_MANIFEST_READY")

    # Define channel policy metadata
    publication_channel_policy = {
        "allowed": [
            "artifact_catalog_publication",
            "documentation_publication",
            "internal_distribution"
        ],
        "blocked": [
            "external_key_signing",
            "legal_certification_claim",
            "production_deployment",
            "quantum_hardware_certification"
        ]
    }

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    manifest = WaveguideCertifiedReleasePublicationManifest(
        publication_manifest_id="SOL-WAVEGUIDE-CERTIFIED-RELEASE-PUBLICATION-MANIFEST",
        publication_manifest_version=1,
        publication_manifest_status=manifest_status,
        source_audit_registry_digest=source_registry_digest,
        publication_entries=sorted_entries,
        publishable_rcs=publishable_rcs,
        blocked_rcs=blocked_rcs,
        pending_rcs=pending_rcs,
        invalid_rcs=invalid_rcs,
        publishable_rc_count=publishable_rc_count,
        blocked_rc_count=blocked_rc_count,
        pending_rc_count=pending_rc_count,
        invalid_rc_count=invalid_rc_count,
        rc1_publication_count=rc1_publication_count,
        rc2_publication_count=rc2_publication_count,
        candidate_levels_indexed=candidate_levels_indexed,
        certification_bundle_ids=certification_bundle_ids,
        certification_bundle_digests=certification_bundle_digests,
        audit_report_digests=audit_report_digests,
        audit_case_digests=audit_case_digests,
        audit_registry_entry_digests=audit_registry_entry_digests,
        final_output_payload_digests=final_output_payload_digests,
        publication_channel_policy=publication_channel_policy,
        publication_readiness_catalog=publication_readiness_catalog,
        reason_codes=sorted(list(set(all_reasons))),
        software_validation_caveat=software_validation_caveat,
        publication_manifest_digest=""
    )
    manifest.publication_manifest_digest = hash_waveguide_certified_release_publication_manifest(manifest)
    return manifest


def validate_waveguide_certified_release_publication_manifest(manifest: Any) -> Tuple[bool, List[str]]:
    """
    Validates a publication manifest.
    """
    if hasattr(manifest, "__dict__"):
        m_dict = asdict(manifest)
    elif isinstance(manifest, dict):
        m_dict = dict(manifest)
    else:
        raise TypeError("manifest must be a dictionary or a dataclass instance")

    reasons = []
    is_valid = True

    # 1. Digest checks
    given_digest = m_dict.get("publication_manifest_digest")
    if not given_digest:
        is_valid = False
        reasons.append("PUBLICATION_MANIFEST_INVALID")
    else:
        recomputed = hash_waveguide_certified_release_publication_manifest(m_dict)
        if recomputed == given_digest:
            reasons.append("PUBLICATION_MANIFEST_DIGEST_VALID")
        else:
            is_valid = False
            reasons.append("PUBLICATION_MANIFEST_INVALID")

    # 2. Check entries validation
    entries = m_dict.get("publication_entries", [])
    entry_statuses = []
    for entry in entries:
        ok, ent_reasons = validate_waveguide_certified_release_publication_entry(entry)
        if not ok:
            is_valid = False
            reasons.append("PUBLICATION_MANIFEST_INVALID")
        entry_statuses.append(entry.get("publication_status") if isinstance(entry, dict) else entry.publication_status)

    # 3. Check counts consistency
    publishable_rc_count = m_dict.get("publishable_rc_count", 0)
    blocked_rc_count = m_dict.get("blocked_rc_count", 0)
    invalid_rc_count = m_dict.get("invalid_rc_count", 0)
    
    if (publishable_rc_count != entry_statuses.count("publication_ready") or
        blocked_rc_count != entry_statuses.count("publication_blocked") or
        invalid_rc_count != entry_statuses.count("publication_invalid")):
        is_valid = False
        reasons.append("PUBLICATION_MANIFEST_INVALID")

    # 4. Check status readiness consistency
    manifest_status = m_dict.get("publication_manifest_status")
    if manifest_status == "publication_manifest_ready":
        if blocked_rc_count > 0 or invalid_rc_count > 0 or len(entries) == 0:
            is_valid = False
            reasons.append("PUBLICATION_MANIFEST_INVALID")

    # Add codes if valid
    if is_valid:
        for rc in m_dict.get("reason_codes", []):
            if rc.startswith("PUBLICATION_"):
                reasons.append(rc)
        reasons.append("PUBLICATION_MANIFEST_READY")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_certified_release_publication_manifest(manifest: Any) -> str:
    """
    Returns a deterministic plain-text summary of a Certified Release Publication Manifest.
    """
    if hasattr(manifest, "__dict__"):
        m_dict = asdict(manifest)
    elif isinstance(manifest, dict):
        m_dict = dict(manifest)
    else:
        raise TypeError("manifest must be a dictionary or a dataclass instance")

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE CERTIFIED RELEASE PUBLICATION MANIFEST",
        "============================================================",
        f"Manifest ID:      {m_dict.get('publication_manifest_id')}",
        f"Version:          {m_dict.get('publication_manifest_version')}",
        f"Status:           {m_dict.get('publication_manifest_status', '').upper()}",
        f"Manifest Digest:  {m_dict.get('publication_manifest_digest')}",
        "------------------------------------------------------------",
        "Publishable Release Candidates:"
    ]

    for rc in m_dict.get("publishable_rcs", []):
        lines.append(f"  * {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Blocked Release Candidates:")
    for rc in m_dict.get("blocked_rcs", []):
        lines.append(f"  * {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Publication Readiness Catalog:")
    for entry in m_dict.get("publication_readiness_catalog", []):
        lines.append(
            f"  [{entry.get('catalog_index')}] {entry.get('rc_id')} ({entry.get('candidate_level')}) "
            f"- Status: {entry.get('publication_status')}"
        )

    lines.append("------------------------------------------------------------")
    lines.append("Allowed Channels:")
    policy = m_dict.get("publication_channel_policy", {})
    for ch in policy.get("allowed", []):
        lines.append(f"  - {ch}")

    lines.append("------------------------------------------------------------")
    lines.append("Blocked Channels:")
    for ch in policy.get("blocked", []):
        lines.append(f"  - {ch}")

    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in m_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {m_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_certified_release_publication_manifest(manifest: Any, filepath: str) -> None:
    """
    Exports the manifest to a JSON file.
    """
    if hasattr(manifest, "__dict__"):
        m_dict = asdict(manifest)
    elif isinstance(manifest, dict):
        m_dict = dict(manifest)
    else:
        raise TypeError("manifest must be a dictionary or a dataclass instance")

    full_path = os.path.join(REPO_ROOT, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(m_dict, f, indent=4, sort_keys=True)


def compare_waveguide_certified_release_publication_manifests(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two publication manifests and returns differences.
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
        "manifest_id_match": l_dict.get("publication_manifest_id") == r_dict.get("publication_manifest_id"),
        "manifest_version_match": l_dict.get("publication_manifest_version") == r_dict.get("publication_manifest_version"),
        "manifest_status_match": l_dict.get("publication_manifest_status") == r_dict.get("publication_manifest_status"),
        "manifest_digest_match": l_dict.get("publication_manifest_digest") == r_dict.get("publication_manifest_digest"),
        "publishable_rc_count_diff": l_dict.get("publishable_rc_count", 0) - r_dict.get("publishable_rc_count", 0),
        "blocked_rc_count_diff": l_dict.get("blocked_rc_count", 0) - r_dict.get("blocked_rc_count", 0),
        "publishable_rcs_left_only": list(set(l_dict.get("publishable_rcs", [])) - set(r_dict.get("publishable_rcs", []))),
        "publishable_rcs_right_only": list(set(r_dict.get("publishable_rcs", [])) - set(l_dict.get("publishable_rcs", []))),
        "blocked_rcs_left_only": list(set(l_dict.get("blocked_rcs", [])) - set(r_dict.get("blocked_rcs", []))),
        "blocked_rcs_right_only": list(set(r_dict.get("blocked_rcs", [])) - set(l_dict.get("blocked_rcs", [])))
    }
    
    diff["all_match"] = (
        diff["manifest_id_match"] and
        diff["manifest_version_match"] and
        diff["manifest_status_match"] and
        diff["manifest_digest_match"] and
        diff["publishable_rc_count_diff"] == 0 and
        diff["blocked_rc_count_diff"] == 0 and
        not diff["publishable_rcs_left_only"] and
        not diff["publishable_rcs_right_only"] and
        not diff["blocked_rcs_left_only"] and
        not diff["blocked_rcs_right_only"]
    )
    return diff


def index_waveguide_publication_entries_by_rc(entries: List[Any]) -> Dict[str, Any]:
    """
    Indexes entries mapping rc_id to the entry dictionary.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        idx[e_dict.get("rc_id")] = e_dict
    return idx


def index_waveguide_publication_entries_by_status(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes entries mapping publication_status to a list of entries.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        status = e_dict.get("publication_status")
        if status not in idx:
            idx[status] = []
        idx[status].append(e_dict)
    return idx


def index_waveguide_publication_entries_by_channel(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes entries mapping allowed publication channels to a list of entries that permit them.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        allowed = e_dict.get("publication_channels_allowed", [])
        for channel in allowed:
            if channel not in idx:
                idx[channel] = []
            idx[channel].append(e_dict)
    return idx


def build_waveguide_publication_readiness_catalog(entries: List[Any]) -> List[Dict[str, Any]]:
    """
    Builds a sorted deterministic publication readiness catalog without timestamps.
    """
    sorted_entries = sorted(entries, key=lambda e: e.rc_id if hasattr(e, "rc_id") else e.get("rc_id", ""))
    catalog = []
    for idx, e in enumerate(sorted_entries):
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        catalog.append({
            "catalog_index": idx + 1,
            "rc_id": e_dict.get("rc_id"),
            "candidate_level": e_dict.get("candidate_level"),
            "publication_status": e_dict.get("publication_status"),
            "certification_bundle_id": e_dict.get("certification_bundle_id"),
            "certification_bundle_digest": e_dict.get("certification_bundle_digest"),
            "audit_report_digest": e_dict.get("audit_report_digest"),
            "audit_case_digest": e_dict.get("audit_case_digest"),
            "allowed_channels": e_dict.get("publication_channels_allowed", []),
            "blocked_channels": e_dict.get("publication_channels_blocked", [])
        })
    return catalog
