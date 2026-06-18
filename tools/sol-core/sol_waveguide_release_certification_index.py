# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Release Certification Index / RC Audit Registry.
Collects verified audit reports for release candidates and indexes them
into a canonical historic audit registry.
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
from sol_waveguide_release_certification_validator import (
    build_waveguide_release_certification_audit_case,
    validate_waveguide_release_certification_audit_report,
    WaveguideReleaseCertificationAuditReport,
    WaveguideReleaseCertificationAuditCase
)


@dataclass
class WaveguideReleaseCertificationIndexEntry:
    audit_registry_entry_id: str
    rc_id: str
    candidate_level: str
    certification_bundle_id: str
    certification_bundle_digest: str
    certification_bundle_path: str
    audit_report_path: str
    audit_report_digest: str
    audit_report_status: str
    audit_case_digest: str
    audit_case_status: str
    audit_status: str
    artifact_digest_mismatch_count: int
    artifact_validation_failure_count: int
    verified_audit_count: int
    failed_audit_count: int
    blocked_audit_count: int
    target_rc_approved: bool
    runtime_capability_valid: bool
    compiler_session_registry_valid: bool
    registered_session_count: int
    registered_rejection_session_count: int
    blocked_session_count: int
    invalid_session_count: int
    compiler_profiles_indexed: List[str]
    pass_sequences_indexed: List[List[str]]
    handler_ids_indexed: List[str]
    final_output_payload_digests: List[str]
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    registry_entry_digest: str = ""


@dataclass
class WaveguideReleaseCertificationIndex:
    audit_registry_id: str
    audit_registry_version: int
    audit_registry_status: str
    entries: List[WaveguideReleaseCertificationIndexEntry]
    audit_timeline: List[Dict[str, Any]]
    registered_audits: List[str]
    failed_audits: List[str]
    blocked_audits: List[str]
    invalid_audits: List[str]
    registered_audit_count: int
    failed_audit_count: int
    blocked_audit_count: int
    invalid_audit_count: int
    rc1_audit_count: int
    rc2_audit_count: int
    verified_rcs: List[str]
    failed_rcs: List[str]
    blocked_rcs: List[str]
    pending_rcs: List[str]
    candidate_levels_indexed: List[str]
    certification_bundle_ids: List[str]
    certification_bundle_digests: List[str]
    audit_report_digests: List[str]
    audit_case_digests: List[str]
    compiler_session_registry_digests: List[str]
    final_output_payload_digests: List[str]
    reason_codes: List[str]
    software_validation_caveat: str
    audit_registry_digest: str = ""


def hash_waveguide_release_certification_index_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation
    excluding the self-referential registry_entry_digest field.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or a dataclass instance")

    e_dict_copy = dict(e_dict)
    e_dict_copy.pop("registry_entry_digest", None)
    return hash_data(e_dict_copy)


def hash_waveguide_release_certification_index(index: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation
    excluding the self-referential audit_registry_digest field.
    """
    if hasattr(index, "__dict__"):
        i_dict = asdict(index)
    elif isinstance(index, dict):
        i_dict = dict(index)
    else:
        raise TypeError("index must be a dictionary or a dataclass instance")

    i_dict_copy = dict(i_dict)
    i_dict_copy.pop("audit_registry_digest", None)
    return hash_data(i_dict_copy)


def build_waveguide_release_certification_index_entry(
    report_path_or_dict: Any,
    case_path_or_dict: Optional[Any] = None
) -> WaveguideReleaseCertificationIndexEntry:
    """
    Builds a deterministic release certification index entry from an audit report and case.
    If the case is not provided, it resolves the bundle path and rebuilds it.
    """
    report_path = ""
    report_dict = None
    load_failed = False

    # 1. Load/Resolve Report
    if isinstance(report_path_or_dict, str):
        report_path = normalize_to_repo_path(report_path_or_dict)
        full_path = os.path.join(REPO_ROOT, report_path)
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
        # Build invalid/failed entry
        entry = WaveguideReleaseCertificationIndexEntry(
            audit_registry_entry_id="SOL-WAVEGUIDE-AUDIT-REGISTRY-ENTRY-UNKNOWN",
            rc_id="UNKNOWN",
            candidate_level="Unknown",
            certification_bundle_id="",
            certification_bundle_digest="",
            certification_bundle_path="",
            audit_report_path=report_path,
            audit_report_digest="",
            audit_report_status="audit_report_invalid",
            audit_case_digest="",
            audit_case_status="audit_invalid",
            audit_status="audit_invalid",
            artifact_digest_mismatch_count=0,
            artifact_validation_failure_count=0,
            verified_audit_count=0,
            failed_audit_count=0,
            blocked_audit_count=0,
            target_rc_approved=False,
            runtime_capability_valid=False,
            compiler_session_registry_valid=False,
            registered_session_count=0,
            registered_rejection_session_count=0,
            blocked_session_count=0,
            invalid_session_count=0,
            compiler_profiles_indexed=[],
            pass_sequences_indexed=[],
            handler_ids_indexed=[],
            final_output_payload_digests=[],
            reason_codes=["RELEASE_CERT_INDEX_ENTRY_CANONICAL", "RELEASE_CERT_INDEX_SOURCE_AUDIT_REPORT_INVALID"],
            notes=["Failed to load or parse audit report."],
            software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation.",
            registry_entry_digest=""
        )
        entry.registry_entry_digest = hash_waveguide_release_certification_index_entry(entry)
        return entry

    # 2. Load/Resolve Case
    case_dict = None
    case_load_failed = False
    
    if case_path_or_dict is not None:
        if isinstance(case_path_or_dict, str):
            c_path = normalize_to_repo_path(case_path_or_dict)
            full_c_path = os.path.join(REPO_ROOT, c_path)
            if os.path.exists(full_c_path):
                try:
                    with open(full_c_path, "r", encoding="utf-8") as f:
                        case_dict = json.load(f)
                except Exception:
                    case_load_failed = True
            else:
                case_load_failed = True
        elif hasattr(case_path_or_dict, "__dict__"):
            case_dict = asdict(case_path_or_dict)
        elif isinstance(case_path_or_dict, dict):
            case_dict = dict(case_path_or_dict)
    else:
        # Rebuild case from bundle
        audited_bundles = report_dict.get("audited_bundles", [])
        if audited_bundles:
            bundle_id = audited_bundles[0]
            bundle_path = f"docs/{bundle_id.replace('-', '_')}.json"
            full_b_path = os.path.join(REPO_ROOT, bundle_path)
            if os.path.exists(full_b_path):
                try:
                    # build_waveguide_release_certification_audit_case handles loading/building
                    case_obj = build_waveguide_release_certification_audit_case(full_b_path)
                    case_dict = asdict(case_obj)
                except Exception:
                    case_load_failed = True
            else:
                case_load_failed = True
        else:
            case_load_failed = True

    if case_load_failed or not case_dict:
        # Build failed entry
        entry = WaveguideReleaseCertificationIndexEntry(
            audit_registry_entry_id="SOL-WAVEGUIDE-AUDIT-REGISTRY-ENTRY-UNKNOWN",
            rc_id="UNKNOWN",
            candidate_level="Unknown",
            certification_bundle_id="",
            certification_bundle_digest="",
            certification_bundle_path="",
            audit_report_path=report_path,
            audit_report_digest=report_dict.get("audit_report_digest", ""),
            audit_report_status=report_dict.get("audit_report_status", "audit_report_invalid"),
            audit_case_digest="",
            audit_case_status="audit_invalid",
            audit_status="audit_invalid",
            artifact_digest_mismatch_count=0,
            artifact_validation_failure_count=0,
            verified_audit_count=report_dict.get("verified_audit_count", 0),
            failed_audit_count=report_dict.get("failed_audit_count", 0),
            blocked_audit_count=report_dict.get("blocked_audit_count", 0),
            target_rc_approved=False,
            runtime_capability_valid=False,
            compiler_session_registry_valid=False,
            registered_session_count=0,
            registered_rejection_session_count=0,
            blocked_session_count=0,
            invalid_session_count=0,
            compiler_profiles_indexed=[],
            pass_sequences_indexed=[],
            handler_ids_indexed=[],
            final_output_payload_digests=[],
            reason_codes=["RELEASE_CERT_INDEX_ENTRY_CANONICAL", "RELEASE_CERT_INDEX_SOURCE_AUDIT_REPORT_VALID"],
            notes=["Failed to load or rebuild corresponding audit case."],
            software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation.",
            registry_entry_digest=""
        )
        entry.registry_entry_digest = hash_waveguide_release_certification_index_entry(entry)
        return entry

    # 3. Construct Index Entry
    rc_id = case_dict.get("rc_id", "UNKNOWN")
    candidate_level = case_dict.get("candidate_level", "Unknown")
    certification_bundle_id = case_dict.get("certification_bundle_id", "")
    certification_bundle_digest = case_dict.get("certification_bundle_digest_recorded", "")
    certification_bundle_path = case_dict.get("certification_bundle_path", "")
    
    # Normalize paths
    if certification_bundle_path:
        certification_bundle_path = normalize_to_repo_path(certification_bundle_path)
    if report_path:
        report_path = normalize_to_repo_path(report_path)

    audit_report_digest = report_dict.get("audit_report_digest", "")
    audit_report_status = report_dict.get("audit_report_status", "")
    audit_case_digest = case_dict.get("audit_case_digest", "")
    audit_case_status = case_dict.get("audit_status", "")

    # Status mapping
    if audit_case_status == "audit_verified" and audit_report_status == "audit_report_verified":
        audit_status = "audit_registered"
        status_reason = "RELEASE_CERT_INDEX_AUDIT_REGISTERED"
    elif audit_case_status == "audit_failed" or audit_report_status == "audit_report_failed":
        audit_status = "audit_failed_registered"
        status_reason = "RELEASE_CERT_INDEX_AUDIT_FAILED_REGISTERED"
    elif audit_case_status == "audit_blocked" or audit_report_status == "audit_report_blocked":
        audit_status = "audit_blocked_registered"
        status_reason = "RELEASE_CERT_INDEX_AUDIT_BLOCKED_REGISTERED"
    else:
        audit_status = "audit_invalid"
        status_reason = ""

    artifact_digest_mismatch_count = case_dict.get("artifact_digest_mismatch_count", len(case_dict.get("artifact_digest_mismatches", [])))
    artifact_validation_failure_count = case_dict.get("artifact_validation_failure_count", len(case_dict.get("artifact_validation_failures", [])))
    
    verified_audit_count = report_dict.get("verified_audit_count", 0)
    failed_audit_count = report_dict.get("failed_audit_count", 0)
    blocked_audit_count = report_dict.get("blocked_audit_count", 0)

    # Validate sub-components
    case_reasons = case_dict.get("reason_codes", [])
    target_rc_approved = case_dict.get("rc_approved_in_registry", False) or "RELEASE_AUDIT_RC_APPROVED_IN_REGISTRY" in case_reasons
    runtime_capability_valid = "RELEASE_AUDIT_RUNTIME_CAPABILITY_VALID" in case_reasons
    compiler_session_registry_valid = "RELEASE_AUDIT_SESSION_REGISTRY_VALID" in case_reasons

    registered_session_count = case_dict.get("registered_session_count", 0)
    registered_rejection_session_count = case_dict.get("registered_rejection_session_count", 0)
    blocked_session_count = case_dict.get("blocked_session_count", 0)
    invalid_session_count = case_dict.get("invalid_session_count", 0)

    # Lists
    compiler_profiles_indexed = sorted(case_dict.get("compiler_profiles_indexed", []))
    
    # Preserve semantic order of pass sequences
    pass_sequences_indexed = case_dict.get("pass_sequences_indexed", [])
    
    handler_ids_indexed = sorted(case_dict.get("handler_ids_indexed", []))
    final_output_payload_digests = sorted(case_dict.get("final_output_payload_digests", []))

    # Reason codes
    reasons = [
        "RELEASE_CERT_INDEX_ENTRY_CANONICAL",
        "RELEASE_CERT_INDEX_SOURCE_AUDIT_REPORT_VALID"
    ]
    if status_reason:
        reasons.append(status_reason)
    if rc_id != "UNKNOWN":
        reasons.append("RELEASE_CERT_INDEX_RC_INDEXED")
    if candidate_level != "Unknown":
        reasons.append("RELEASE_CERT_INDEX_CANDIDATE_LEVEL_INDEXED")
    if certification_bundle_digest:
        reasons.append("RELEASE_CERT_INDEX_BUNDLE_DIGEST_REFERENCED")
    if audit_report_digest:
        reasons.append("RELEASE_CERT_INDEX_AUDIT_REPORT_DIGEST_REFERENCED")
    if audit_case_digest:
        reasons.append("RELEASE_CERT_INDEX_AUDIT_CASE_DIGEST_REFERENCED")
    if case_dict.get("compiler_session_registry_digest_recorded"):
        reasons.append("RELEASE_CERT_INDEX_SESSION_REGISTRY_DIGEST_REFERENCED")
    if final_output_payload_digests:
        reasons.append("RELEASE_CERT_INDEX_FINAL_OUTPUT_DIGESTS_REFERENCED")
    
    software_validation_caveat = case_dict.get("software_validation_caveat", "Validation is shadow/sandbox software validation, not quantum hardware validation.")
    if software_validation_caveat and "sandbox" in software_validation_caveat.lower():
        reasons.append("RELEASE_CERT_INDEX_SOFTWARE_CAVEAT_INCLUDED")

    entry = WaveguideReleaseCertificationIndexEntry(
        audit_registry_entry_id=f"SOL-WAVEGUIDE-AUDIT-REGISTRY-ENTRY-{rc_id}",
        rc_id=rc_id,
        candidate_level=candidate_level,
        certification_bundle_id=certification_bundle_id,
        certification_bundle_digest=certification_bundle_digest,
        certification_bundle_path=certification_bundle_path,
        audit_report_path=report_path,
        audit_report_digest=audit_report_digest,
        audit_report_status=audit_report_status,
        audit_case_digest=audit_case_digest,
        audit_case_status=audit_case_status,
        audit_status=audit_status,
        artifact_digest_mismatch_count=artifact_digest_mismatch_count,
        artifact_validation_failure_count=artifact_validation_failure_count,
        verified_audit_count=verified_audit_count,
        failed_audit_count=failed_audit_count,
        blocked_audit_count=blocked_audit_count,
        target_rc_approved=target_rc_approved,
        runtime_capability_valid=runtime_capability_valid,
        compiler_session_registry_valid=compiler_session_registry_valid,
        registered_session_count=registered_session_count,
        registered_rejection_session_count=registered_rejection_session_count,
        blocked_session_count=blocked_session_count,
        invalid_session_count=invalid_session_count,
        compiler_profiles_indexed=compiler_profiles_indexed,
        pass_sequences_indexed=pass_sequences_indexed,
        handler_ids_indexed=handler_ids_indexed,
        final_output_payload_digests=final_output_payload_digests,
        reason_codes=sorted(list(set(reasons))),
        notes=case_dict.get("notes", []),
        software_validation_caveat=software_validation_caveat,
        registry_entry_digest=""
    )
    entry.registry_entry_digest = hash_waveguide_release_certification_index_entry(entry)
    return entry


def validate_waveguide_release_certification_index_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Validates a release certification index entry.
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
    software_validation_caveat = e_dict.get("software_validation_caveat")

    if not rc_id or rc_id == "UNKNOWN":
        is_valid = False
        reasons.append("RELEASE_CERT_INDEX_INVALID")
    if not candidate_level or candidate_level == "Unknown":
        is_valid = False
        reasons.append("RELEASE_CERT_INDEX_INVALID")
    if not certification_bundle_id or not certification_bundle_digest:
        is_valid = False
        reasons.append("RELEASE_CERT_INDEX_INVALID")
    if not audit_report_digest or not audit_case_digest:
        is_valid = False
        reasons.append("RELEASE_CERT_INDEX_INVALID")
    if not software_validation_caveat or "sandbox" not in software_validation_caveat.lower():
        is_valid = False
        reasons.append("RELEASE_CERT_INDEX_INVALID")

    # 2. Check digest validates
    given_digest = e_dict.get("registry_entry_digest")
    if given_digest:
        recomputed = hash_waveguide_release_certification_index_entry(e_dict)
        if recomputed == given_digest:
            reasons.append("RELEASE_CERT_INDEX_ENTRY_DIGEST_VALID")
        else:
            is_valid = False
            reasons.append("RELEASE_CERT_INDEX_INVALID")
    else:
        is_valid = False
        reasons.append("RELEASE_CERT_INDEX_INVALID")

    # 3. Check status consistency for verified entry
    audit_status = e_dict.get("audit_status")
    if audit_status in ("audit_registered", "audit_verified"):
        # Strict validation checks
        mismatch_c = e_dict.get("artifact_digest_mismatch_count", 0)
        failure_c = e_dict.get("artifact_validation_failure_count", 0)
        verified_c = e_dict.get("verified_audit_count", 0)
        failed_c = e_dict.get("failed_audit_count", 0)
        blocked_c = e_dict.get("blocked_audit_count", 0)
        
        target_approved = e_dict.get("target_rc_approved", False)
        capability_valid = e_dict.get("runtime_capability_valid", False)
        session_registry_valid = e_dict.get("compiler_session_registry_valid", False)

        if (mismatch_c != 0 or failure_c != 0 or verified_c < 1 or failed_c != 0 or blocked_c != 0 or
                not target_approved or not capability_valid or not session_registry_valid):
            is_valid = False
            reasons.append("RELEASE_CERT_INDEX_INVALID")

    # Add canonical reasons from entry if valid
    if is_valid:
        for rc in e_dict.get("reason_codes", []):
            if rc.startswith("RELEASE_CERT_INDEX_"):
                reasons.append(rc)
        reasons.append("RELEASE_CERT_INDEX_ENTRY_CANONICAL")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_release_certification_index(
    reports: List[Any],
    cases: Optional[List[Any]] = None
) -> WaveguideReleaseCertificationIndex:
    """
    Builds a deterministic Release Certification Index / RC Audit Registry.
    """
    entries = []
    
    # Build entries
    for idx, report in enumerate(reports):
        corresponding_case = None
        if cases and idx < len(cases):
            corresponding_case = cases[idx]
        entry = build_waveguide_release_certification_index_entry(report, corresponding_case)
        entries.append(entry)

    # Sort entries deterministically
    def entry_sort_key(e):
        return (
            e.rc_id,
            e.candidate_level,
            e.audit_status,
            e.audit_report_digest
        )
    sorted_entries = sorted(entries, key=entry_sort_key)

    # Sort timeline deterministically by lexical rc_id
    timeline_entries = []
    timeline_sorted = sorted(sorted_entries, key=lambda e: e.rc_id)
    for index_1, entry in enumerate(timeline_sorted):
        timeline_entries.append({
            "timeline_index": index_1 + 1,
            "rc_id": entry.rc_id,
            "candidate_level": entry.candidate_level,
            "audit_status": entry.audit_status,
            "certification_bundle_id": entry.certification_bundle_id,
            "certification_bundle_digest": entry.certification_bundle_digest,
            "audit_report_digest": entry.audit_report_digest,
            "audit_case_digest": entry.audit_case_digest
        })

    registered_audits = []
    failed_audits = []
    blocked_audits = []
    invalid_audits = []

    registered_audit_count = 0
    failed_audit_count = 0
    blocked_audit_count = 0
    invalid_audit_count = 0
    rc1_audit_count = 0
    rc2_audit_count = 0

    verified_rcs = []
    failed_rcs = []
    blocked_rcs = []

    candidate_levels_indexed = []
    certification_bundle_ids = []
    certification_bundle_digests = []
    audit_report_digests = []
    audit_case_digests = []
    compiler_session_registry_digests = []
    final_output_payload_digests = []
    all_reasons = ["RELEASE_CERT_INDEX_TIMELINE_CANONICAL", "RELEASE_CERT_INDEX_COUNTS_VALID"]

    for entry in sorted_entries:
        cb_id = entry.certification_bundle_id
        rc_id = entry.rc_id
        status = entry.audit_status
        level = entry.candidate_level

        # Category mapping
        if status in ("audit_registered", "audit_verified"):
            registered_audit_count += 1
            if cb_id and cb_id not in registered_audits:
                registered_audits.append(cb_id)
            if rc_id and rc_id not in verified_rcs:
                verified_rcs.append(rc_id)
        elif status == "audit_failed_registered":
            failed_audit_count += 1
            if cb_id and cb_id not in failed_audits:
                failed_audits.append(cb_id)
            if rc_id and rc_id not in failed_rcs:
                failed_rcs.append(rc_id)
        elif status == "audit_blocked_registered":
            blocked_audit_count += 1
            if cb_id and cb_id not in blocked_audits:
                blocked_audits.append(cb_id)
            if rc_id and rc_id not in blocked_rcs:
                blocked_rcs.append(rc_id)
        else:
            invalid_audit_count += 1
            if cb_id and cb_id not in invalid_audits:
                invalid_audits.append(cb_id)

        if "RC1" in rc_id:
            rc1_audit_count += 1
        elif "RC2" in rc_id:
            rc2_audit_count += 1

        # Unique lists
        def add_unique(lst, val):
            if val and val not in lst:
                lst.append(val)

        add_unique(candidate_levels_indexed, level)
        add_unique(certification_bundle_ids, cb_id)
        add_unique(certification_bundle_digests, entry.certification_bundle_digest)
        add_unique(audit_report_digests, entry.audit_report_digest)
        add_unique(audit_case_digests, entry.audit_case_digest)
        
        # Extract session registry digest if present in entry reason codes or we can get it from timeline
        # Since we don't have it directly as a field, let's look at it from reports/cases
        # In a real run, we can also extract session registry digests if they are referenced
        # For simplicity, we can inspect case if it's there
        # Let's see: we can parse it from case_dict if we passed case
        # Wait, since compiler_session_registry_digests is a top-level indexing field:
        # we can pass it or resolve it. If corresponding_case has it:
        # we can store it in registry
        # Let's inspect the report's compiler_session_registry_digests list!
        # The report dict contains "compiler_session_registry_digests" (List[str]).
        # So we can extract it from the report!
        # Let's check report_dict:
        # report_dict has a list "compiler_session_registry_digests"
        # We can extract it from report_dict:
        # Let's map it from reports!
        
        for digest in entry.final_output_payload_digests:
            add_unique(final_output_payload_digests, digest)

        for code in entry.reason_codes:
            if code not in all_reasons:
                all_reasons.append(code)

    # Extract compiler session registry digests from reports
    for rep in reports:
        if hasattr(rep, "__dict__"):
            rep_dict = asdict(rep)
        elif isinstance(rep, dict):
            rep_dict = dict(rep)
        else:
            rep_dict = {}
        for sd in rep_dict.get("compiler_session_registry_digests", []):
            add_unique(compiler_session_registry_digests, sd)

    # Sort all lists
    registered_audits = sorted(registered_audits)
    failed_audits = sorted(failed_audits)
    blocked_audits = sorted(blocked_audits)
    invalid_audits = sorted(invalid_audits)
    verified_rcs = sorted(verified_rcs)
    failed_rcs = sorted(failed_rcs)
    blocked_rcs = sorted(blocked_rcs)

    candidate_levels_indexed = sorted(candidate_levels_indexed)
    certification_bundle_ids = sorted(certification_bundle_ids)
    certification_bundle_digests = sorted(certification_bundle_digests)
    audit_report_digests = sorted(audit_report_digests)
    audit_case_digests = sorted(audit_case_digests)
    compiler_session_registry_digests = sorted(compiler_session_registry_digests)
    final_output_payload_digests = sorted(final_output_payload_digests)

    # Read pending RCs
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
    
    pending_rcs = sorted(list(set(approved_rcs) - set(verified_rcs)))

    # Determine status
    if failed_audit_count > 0 or invalid_audit_count > 0 or len(sorted_entries) == 0:
        registry_status = "audit_registry_invalid"
        all_reasons.append("RELEASE_CERT_INDEX_INVALID")
    elif blocked_audit_count > 0:
        registry_status = "audit_registry_blocked"
        all_reasons.append("RELEASE_CERT_INDEX_BLOCKED")
    else:
        registry_status = "audit_registry_valid"
        all_reasons.append("RELEASE_CERT_INDEX_VALID")

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    index = WaveguideReleaseCertificationIndex(
        audit_registry_id="SOL-WAVEGUIDE-RELEASE-CERTIFICATION-INDEX",
        audit_registry_version=1,
        audit_registry_status=registry_status,
        entries=sorted_entries,
        audit_timeline=timeline_entries,
        registered_audits=registered_audits,
        failed_audits=failed_audits,
        blocked_audits=blocked_audits,
        invalid_audits=invalid_audits,
        registered_audit_count=registered_audit_count,
        failed_audit_count=failed_audit_count,
        blocked_audit_count=blocked_audit_count,
        invalid_audit_count=invalid_audit_count,
        rc1_audit_count=rc1_audit_count,
        rc2_audit_count=rc2_audit_count,
        verified_rcs=verified_rcs,
        failed_rcs=failed_rcs,
        blocked_rcs=blocked_rcs,
        pending_rcs=pending_rcs,
        candidate_levels_indexed=candidate_levels_indexed,
        certification_bundle_ids=certification_bundle_ids,
        certification_bundle_digests=certification_bundle_digests,
        audit_report_digests=audit_report_digests,
        audit_case_digests=audit_case_digests,
        compiler_session_registry_digests=compiler_session_registry_digests,
        final_output_payload_digests=final_output_payload_digests,
        reason_codes=sorted(list(set(all_reasons))),
        software_validation_caveat=software_validation_caveat,
        audit_registry_digest=""
    )
    index.audit_registry_digest = hash_waveguide_release_certification_index(index)
    return index


def validate_waveguide_release_certification_index(index: Any) -> Tuple[bool, List[str]]:
    """
    Validates a top-level Release Certification Index / RC Audit Registry.
    """
    if hasattr(index, "__dict__"):
        i_dict = asdict(index)
    elif isinstance(index, dict):
        i_dict = dict(index)
    else:
        raise TypeError("index must be a dictionary or a dataclass instance")

    reasons = []
    is_valid = True

    # 1. Recompute index digest and compare
    given_digest = i_dict.get("audit_registry_digest")
    if given_digest:
        recomputed = hash_waveguide_release_certification_index(i_dict)
        if recomputed == given_digest:
            reasons.append("RELEASE_CERT_INDEX_REGISTRY_DIGEST_VALID")
        else:
            is_valid = False
            reasons.append("RELEASE_CERT_INDEX_INVALID")
    else:
        is_valid = False
        reasons.append("RELEASE_CERT_INDEX_INVALID")

    # 2. Check caveat
    caveat = i_dict.get("software_validation_caveat", "")
    if not caveat or "sandbox" not in caveat.lower():
        is_valid = False
        reasons.append("RELEASE_CERT_INDEX_INVALID")

    # 3. Validate entries and check counts match
    entries = i_dict.get("entries", [])
    if len(entries) == 0:
        is_valid = False
        reasons.append("RELEASE_CERT_INDEX_INVALID")

    registered_c = 0
    failed_c = 0
    blocked_c = 0
    invalid_c = 0
    rc1_c = 0
    rc2_c = 0

    for e in entries:
        ok_entry, entry_reasons = validate_waveguide_release_certification_index_entry(e)
        if not ok_entry:
            is_valid = False
            reasons.append("RELEASE_CERT_INDEX_INVALID")
        
        status = e.get("audit_status")
        if status in ("audit_registered", "audit_verified"):
            registered_c += 1
        elif status == "audit_failed_registered":
            failed_c += 1
        elif status == "audit_blocked_registered":
            blocked_c += 1
        else:
            invalid_c += 1

        rc_id = e.get("rc_id", "")
        if "RC1" in rc_id:
            rc1_c += 1
        elif "RC2" in rc_id:
            rc2_c += 1

    # Compare counts
    if (registered_c != i_dict.get("registered_audit_count", 0) or
            failed_c != i_dict.get("failed_audit_count", 0) or
            blocked_c != i_dict.get("blocked_audit_count", 0) or
            invalid_c != i_dict.get("invalid_audit_count", 0) or
            rc1_c != i_dict.get("rc1_audit_count", 0) or
            rc2_c != i_dict.get("rc2_audit_count", 0)):
        is_valid = False
        reasons.append("RELEASE_CERT_INDEX_INVALID")

    # Verify lists are sorted
    for lst_name in ("verified_rcs", "failed_rcs", "blocked_rcs", "pending_rcs",
                     "candidate_levels_indexed", "certification_bundle_ids",
                     "certification_bundle_digests", "audit_report_digests",
                     "audit_case_digests", "compiler_session_registry_digests",
                     "final_output_payload_digests"):
        lst = i_dict.get(lst_name, [])
        if lst != sorted(lst):
            is_valid = False
            reasons.append("RELEASE_CERT_INDEX_INVALID")

    # Check status matches
    status = i_dict.get("audit_registry_status")
    if status == "audit_registry_valid":
        if failed_c > 0 or invalid_c > 0 or blocked_c > 0:
            is_valid = False
            reasons.append("RELEASE_CERT_INDEX_INVALID")
        else:
            reasons.append("RELEASE_CERT_INDEX_VALID")
    elif status == "audit_registry_blocked":
        if blocked_c == 0:
            is_valid = False
            reasons.append("RELEASE_CERT_INDEX_INVALID")
        else:
            reasons.append("RELEASE_CERT_INDEX_BLOCKED")
    elif status == "audit_registry_invalid":
        reasons.append("RELEASE_CERT_INDEX_INVALID")

    return is_valid, sorted(list(set(reasons)))


def index_waveguide_release_certification_entries_by_rc(entries: List[Any]) -> Dict[str, Any]:
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


def index_waveguide_release_certification_entries_by_status(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes entries mapping audit_status to a list of entries.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        status = e_dict.get("audit_status")
        if status not in idx:
            idx[status] = []
        idx[status].append(e_dict)
    return idx


def index_waveguide_release_certification_entries_by_candidate_level(entries: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes entries mapping candidate_level to a list of entries.
    """
    idx = {}
    for e in entries:
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        level = e_dict.get("candidate_level")
        if level not in idx:
            idx[level] = []
        idx[level].append(e_dict)
    return idx


def build_waveguide_release_certification_audit_timeline(entries: List[Any]) -> List[Dict[str, Any]]:
    """
    Builds a sorted deterministic audit timeline without timestamps.
    """
    sorted_entries = sorted(entries, key=lambda e: e.rc_id if hasattr(e, "rc_id") else e.get("rc_id", ""))
    timeline = []
    for idx, e in enumerate(sorted_entries):
        if hasattr(e, "__dict__"):
            e_dict = asdict(e)
        else:
            e_dict = dict(e)
        timeline.append({
            "timeline_index": idx + 1,
            "rc_id": e_dict.get("rc_id"),
            "candidate_level": e_dict.get("candidate_level"),
            "audit_status": e_dict.get("audit_status"),
            "certification_bundle_id": e_dict.get("certification_bundle_id"),
            "certification_bundle_digest": e_dict.get("certification_bundle_digest"),
            "audit_report_digest": e_dict.get("audit_report_digest"),
            "audit_case_digest": e_dict.get("audit_case_digest")
        })
    return timeline


def summarize_waveguide_release_certification_index(index: Any) -> str:
    """
    Generates a deterministic plaintext summary of the index/registry.
    """
    if hasattr(index, "__dict__"):
        i_dict = asdict(index)
    elif isinstance(index, dict):
        i_dict = dict(index)
    else:
        raise TypeError("index must be a dictionary or a dataclass instance")

    lines = [
        "============================================================",
        "      SOL WAVEGUIDE RELEASE CERTIFICATION INDEX SUMMARY",
        "============================================================",
        f"Registry ID:      {i_dict.get('audit_registry_id')}",
        f"Version:          {i_dict.get('audit_registry_version')}",
        f"Status:           {i_dict.get('audit_registry_status', '').upper()}",
        f"Registry Digest:  {i_dict.get('audit_registry_digest')}",
        "------------------------------------------------------------",
        "Registered Audits:",
    ]
    for b in i_dict.get("registered_audits", []):
        lines.append(f"  - {b}")
    lines.append("------------------------------------------------------------")
    lines.append("Timeline Entries:")
    for t in i_dict.get("audit_timeline", []):
        lines.append(f"  [{t.get('timeline_index')}] {t.get('rc_id')} ({t.get('candidate_level')}) - Status: {t.get('audit_status')}")
    lines.append("------------------------------------------------------------")
    lines.append("Pending Release Candidates:")
    for pr in i_dict.get("pending_rcs", []):
        lines.append(f"  - {pr}")
    lines.append("------------------------------------------------------------")
    lines.append("Indexed Levels:")
    for l in i_dict.get("candidate_levels_indexed", []):
        lines.append(f"  * {l}")
    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in i_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")
    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {i_dict.get('software_validation_caveat')}")
    lines.append("============================================================")
    return "\n".join(lines)


def export_waveguide_release_certification_index(index: Any, filepath: str) -> None:
    """
    Exports the release certification index to a key-sorted JSON file.
    """
    if hasattr(index, "__dict__"):
        i_dict = asdict(index)
    elif isinstance(index, dict):
        i_dict = dict(index)
    else:
        raise TypeError("index must be a dictionary or a dataclass instance")

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(i_dict, f, indent=4, sort_keys=True)


def compare_waveguide_release_certification_indexes(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two indexes and returns differences.
    """
    def to_dict(ind):
        if hasattr(ind, "__dict__"):
            return asdict(ind)
        return dict(ind)

    left_dict = to_dict(left)
    right_dict = to_dict(right)

    diffs = {}
    for key in set(left_dict.keys()) | set(right_dict.keys()):
        val_l = left_dict.get(key)
        val_r = right_dict.get(key)
        if val_l != val_r:
            diffs[key] = {
                "left": val_l,
                "right": val_r
            }
    return diffs
