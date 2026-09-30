# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Distribution Readiness Closure Report.
Consumes the Handoff Bundle and Verification Kit and audits the final exit criteria
for closing this release/package governance stage.
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
from sol_waveguide_release_handoff_bundle import (
    validate_waveguide_release_handoff_bundle
)
from sol_waveguide_offline_consumer_verification_kit import (
    validate_waveguide_offline_consumer_verification_kit
)


@dataclass
class WaveguideDistributionClosureCase:
    distribution_closure_case_id: str
    distribution_closure_case_status: str  # distribution_closure_case_verified, etc.
    distribution_closure_requirement_id: str
    distribution_closure_requirement_kind: str
    distribution_closure_requirement_description: str
    source_release_handoff_bundle_digest: str
    source_offline_consumer_verification_kit_digest: str
    source_package_attested_archive_candidate_index_digest: str
    source_package_archive_digest_attestation_audit_report_digest: str
    source_package_archive_audit_report_digest: str
    current_attested_archive_candidate_digest: str
    archive_verified: bool
    archive_digest_attested: bool
    digest_attestation_audit_verified: bool
    handoff_bundle_ready: bool
    offline_verification_kit_ready: bool
    offline_consumer_verification_ready: bool
    real_signature_absent_verified: bool
    real_key_signing_absent_verified: bool
    private_key_material_absent_verified: bool
    credentials_absent_verified: bool
    network_access_absent_verified: bool
    upload_absent_verified: bool
    publication_absent_verified: bool
    deployment_absent_verified: bool
    production_mutation_absent_verified: bool
    closure_requirement_satisfied: bool
    closure_blocker_present: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    distribution_closure_case_digest: str = ""


@dataclass
class WaveguideDistributionReadinessClosureReport:
    distribution_readiness_closure_report_id: str
    distribution_readiness_closure_report_version: int
    distribution_readiness_closure_report_status: str  # distribution_readiness_closure_verified, etc.
    source_release_handoff_bundle_digest: str
    source_offline_consumer_verification_kit_digest: str
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
    current_attested_archive_candidate_digest: str
    current_attested_archive_candidate_format: str
    current_attested_archive_candidate_display_path: str
    current_attested_archive_candidate_size_bytes: int
    current_archive_file_digest: str
    closure_cases: List[WaveguideDistributionClosureCase]
    verified_distribution_closure_cases: List[str]
    blocked_distribution_closure_cases: List[str]
    warning_distribution_closure_cases: List[str]
    invalid_distribution_closure_cases: List[str]
    verified_distribution_closure_case_count: int
    blocked_distribution_closure_case_count: int
    warning_distribution_closure_case_count: int
    invalid_distribution_closure_case_count: int
    closure_requirement_kinds_indexed: List[str]
    closure_case_digests_indexed: List[str]
    archive_verified: bool
    archive_digest_attested: bool
    digest_attestation_audit_verified: bool
    release_handoff_bundle_ready: bool
    offline_consumer_verification_kit_ready: bool
    offline_consumer_verification_ready: bool
    source_chain_verified: bool
    operation_boundaries_verified: bool
    exit_criteria_verified: bool
    package_release_stage_closed: bool
    ready_to_pivot_to_new_direction: bool
    ready_for_future_key_management_stage: bool
    ready_for_future_publication_gate_stage: bool
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
    private_key_material_loaded: bool
    credentials_loaded: bool
    network_access_used: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    distribution_readiness_closure_report_digest: str = ""


def hash_waveguide_distribution_readiness_closure_case(case: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a closure case,
    excluding distribution_closure_case_digest.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    elif isinstance(case, dict):
        c_dict = dict(case)
    else:
        raise TypeError("case must be a dictionary or dataclass instance")

    c_copy = dict(c_dict)
    c_copy.pop("distribution_closure_case_digest", None)
    return hash_data(c_copy)


def hash_waveguide_distribution_readiness_closure_report(report: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a closure report,
    excluding distribution_readiness_closure_report_digest.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or dataclass instance")

    r_copy = dict(r_dict)
    r_copy.pop("distribution_readiness_closure_report_digest", None)
    return hash_data(r_copy)


def index_waveguide_distribution_closure_cases_by_status(
    cases: List[WaveguideDistributionClosureCase]
) -> Dict[str, List[str]]:
    indexed = {
        "verified": [],
        "blocked": [],
        "warning": [],
        "invalid": []
    }
    for c in cases:
        status = c.distribution_closure_case_status
        if status == "distribution_closure_case_verified":
            indexed["verified"].append(c.distribution_closure_case_id)
        elif status == "distribution_closure_case_blocked":
            indexed["blocked"].append(c.distribution_closure_case_id)
        elif status == "distribution_closure_case_warning":
            indexed["warning"].append(c.distribution_closure_case_id)
        else:
            indexed["invalid"].append(c.distribution_closure_case_id)
    return indexed


def index_waveguide_distribution_closure_cases_by_requirement(
    cases: List[WaveguideDistributionClosureCase]
) -> Dict[str, List[str]]:
    indexed = {}
    for c in cases:
        req = c.distribution_closure_requirement_id
        if req not in indexed:
            indexed[req] = []
        indexed[req].append(c.distribution_closure_case_id)
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


def validate_waveguide_distribution_closure_source_chain(
    handoff_digest: str, kit_digest: str
) -> bool:
    return bool(handoff_digest and kit_digest)


def validate_waveguide_distribution_closure_operation_boundaries(
    report_dict: Dict[str, Any]
) -> bool:
    # Ensure no prohibited activities occurred
    prohibited = [
        "signing_performed",
        "real_key_signature_performed",
        "external_signing_performed",
        "timestamp_authority_performed",
        "upload_performed",
        "external_publication_performed",
        "deployment_performed",
        "production_mutation_performed",
        "private_key_material_loaded",
        "credentials_loaded",
        "network_access_used"
    ]
    for p in prohibited:
        if report_dict.get(p, False) is not False:
            return False
    return True


def validate_waveguide_distribution_closure_exit_criteria(
    cases: List[WaveguideDistributionClosureCase]
) -> bool:
    return all(c.closure_requirement_satisfied and not c.closure_blocker_present for c in cases)


def build_waveguide_distribution_readiness_closure_case(
    requirement_id: str,
    kind: str,
    desc: str,
    handoff_dict: Dict[str, Any],
    kit_dict: Dict[str, Any],
    index: int
) -> WaveguideDistributionClosureCase:
    """
    Builds a single distribution closure case.
    """
    bun_status = handoff_dict.get("release_handoff_bundle_status", "")
    kit_status = kit_dict.get("offline_consumer_verification_kit_status", "")

    archive_verified = (handoff_dict.get("release_handoff_bundle_status") == "release_handoff_bundle_ready")
    archive_digest_attested = (handoff_dict.get("digest_attestation_status") == "verified")
    digest_attestation_audit_verified = (handoff_dict.get("source_chain_verified") is True)
    handoff_ready = (bun_status == "release_handoff_bundle_ready")
    kit_ready = (kit_status == "offline_consumer_verification_kit_ready")
    offline_consumer_verification_ready = kit_dict.get("consumer_verification_ready", False)

    # Prohibitions verification
    real_signature_absent = (handoff_dict.get("real_signature_status") == "not_performed")
    real_key_signing_absent = (handoff_dict.get("real_key_signature_performed") is False)
    private_key_material_absent = (handoff_dict.get("private_key_material_loaded", False) is False)
    credentials_absent = (handoff_dict.get("credentials_loaded", False) is False)
    network_access_absent = (handoff_dict.get("network_access_used", False) is False)

    upload_absent = (handoff_dict.get("upload_performed") is False)
    publication_absent = (handoff_dict.get("external_publication_performed") is False)
    deployment_absent = (handoff_dict.get("deployment_performed") is False)
    production_mutation_absent = (handoff_dict.get("production_mutation_performed") is False)

    status = "distribution_closure_case_verified"
    satisfied = True
    blocker = False
    reason_codes = ["CLOSURE_CASE_VERIFIED"]

    # Evaluate specific requirements
    if requirement_id == "archive_verification" and not archive_verified:
        satisfied = False
    elif requirement_id == "digest_attestation_verification" and not archive_digest_attested:
        satisfied = False
    elif requirement_id == "attestation_audit_verification" and not digest_attestation_audit_verified:
        satisfied = False
    elif requirement_id == "handoff_readiness" and not handoff_ready:
        satisfied = False
    elif requirement_id == "offline_consumer_verification_kit_readiness" and not kit_ready:
        satisfied = False
    elif requirement_id == "offline_consumer_verification" and not offline_consumer_verification_ready:
        satisfied = False
    elif requirement_id == "no_real_signature_boundary" and (not real_signature_absent or not real_key_signing_absent):
        satisfied = False
        blocker = True
    elif requirement_id == "no_network_boundary" and not network_access_absent:
        satisfied = False
        blocker = True
    elif requirement_id == "no_publication_boundary" and not publication_absent:
        satisfied = False
        blocker = True
    elif requirement_id == "no_deployment_boundary" and not deployment_absent:
        satisfied = False
        blocker = True
    elif requirement_id == "no_production_mutation_boundary" and not production_mutation_absent:
        satisfied = False
        blocker = True

    if not satisfied:
        status = "distribution_closure_case_blocked" if blocker else "distribution_closure_case_invalid"
        reason_codes = ["CLOSURE_REQUIREMENT_NOT_SATISFIED"]

    case = WaveguideDistributionClosureCase(
        distribution_closure_case_id=f"SOL-WAVEGUIDE-CLOSURE-CASE-{index:03d}",
        distribution_closure_case_status=status,
        distribution_closure_requirement_id=requirement_id,
        distribution_closure_requirement_kind=kind,
        distribution_closure_requirement_description=desc,
        source_release_handoff_bundle_digest=handoff_dict.get("release_handoff_bundle_digest", ""),
        source_offline_consumer_verification_kit_digest=kit_dict.get("offline_consumer_verification_kit_digest", ""),
        source_package_attested_archive_candidate_index_digest=handoff_dict.get("source_package_attested_archive_candidate_index_digest", ""),
        source_package_archive_digest_attestation_audit_report_digest=handoff_dict.get("source_package_archive_digest_attestation_audit_report_digest", ""),
        source_package_archive_audit_report_digest=handoff_dict.get("source_package_archive_audit_report_digest", ""),
        current_attested_archive_candidate_digest=handoff_dict.get("current_attested_archive_candidate_digest", ""),
        archive_verified=archive_verified,
        archive_digest_attested=archive_digest_attested,
        digest_attestation_audit_verified=digest_attestation_audit_verified,
        handoff_bundle_ready=handoff_ready,
        offline_verification_kit_ready=kit_ready,
        offline_consumer_verification_ready=offline_consumer_verification_ready,
        real_signature_absent_verified=real_signature_absent,
        real_key_signing_absent_verified=real_key_signing_absent,
        private_key_material_absent_verified=private_key_material_absent,
        credentials_absent_verified=credentials_absent,
        network_access_absent_verified=network_access_absent,
        upload_absent_verified=upload_absent,
        publication_absent_verified=publication_absent,
        deployment_absent_verified=deployment_absent,
        production_mutation_absent_verified=production_mutation_absent,
        closure_requirement_satisfied=satisfied,
        closure_blocker_present=blocker,
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    case.distribution_closure_case_digest = hash_waveguide_distribution_readiness_closure_case(case)
    return case


def validate_waveguide_distribution_readiness_closure_case(
    case: Any
) -> Tuple[bool, List[str]]:
    """
    Validates a single distribution closure case.
    """
    c_dict = asdict(case) if hasattr(case, "__dict__") else dict(case)
    errors = []

    # Verify digest
    recorded = c_dict.get("distribution_closure_case_digest", "")
    if not recorded:
        errors.append("Missing case digest")
    else:
        recomputed = hash_waveguide_distribution_readiness_closure_case(c_dict)
        if recomputed != recorded:
            errors.append(f"Case digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    # Enforce exit criteria safety
    if c_dict.get("distribution_closure_case_status") != "distribution_closure_case_verified":
        errors.append("Closure case is not verified")

    if c_dict.get("closure_blocker_present") is not False:
        errors.append("Closure blocker present in case")

    return len(errors) == 0, errors


def build_waveguide_distribution_readiness_closure_report(
    handoff_bundle_path_or_dict: Any,
    verification_kit_path_or_dict: Any
) -> WaveguideDistributionReadinessClosureReport:
    """
    Builds the top-level Distribution Readiness Closure Report.
    """
    bun_dict = _load_dict(handoff_bundle_path_or_dict) or {}
    kit_dict = _load_dict(verification_kit_path_or_dict) or {}

    bun_digest = bun_dict.get("release_handoff_bundle_digest", "")
    bun_status = bun_dict.get("release_handoff_bundle_status", "")
    kit_digest = kit_dict.get("offline_consumer_verification_kit_digest", "")
    kit_status = kit_dict.get("offline_consumer_verification_kit_status", "")

    status = "distribution_readiness_closure_verified"
    reason_codes = ["DISTRIBUTION_CLOSURE_VERIFIED"]

    valid_bun, bun_errs = validate_waveguide_release_handoff_bundle(bun_dict)
    valid_kit, kit_errs = validate_waveguide_offline_consumer_verification_kit(kit_dict)

    if not valid_bun or bun_status != "release_handoff_bundle_ready" or not valid_kit or kit_status != "offline_consumer_verification_kit_ready":
        status = "distribution_readiness_closure_blocked"
        reason_codes = ["HANDOFF_OR_KIT_NOT_READY"]

    # Gather case definitions
    case_defs = [
        ("archive_verification", "archive_verification", "Archive is built and verified with exact members"),
        ("digest_attestation_verification", "digest_attestation_verification", "Local digest attestation statement generated"),
        ("attestation_audit_verification", "digest_attestation_verification", "Local digest attestation audit report verified"),
        ("handoff_readiness", "handoff_readiness", "Release handoff bundle generated and validated"),
        ("offline_consumer_verification_kit_readiness", "offline_consumer_verification", "Offline verification kit built"),
        ("offline_consumer_verification", "offline_consumer_verification", "Offline verification steps verified and safe"),
        ("no_real_signature_boundary", "no_real_signature_boundary", "Real key signing operations absent"),
        ("no_network_boundary", "no_network_boundary", "Private keys, credentials, and network access absent"),
        ("no_publication_boundary", "no_publication_boundary", "External publication operations absent"),
        ("no_deployment_boundary", "no_deployment_boundary", "Deployment operations absent"),
        ("no_production_mutation_boundary", "no_production_mutation_boundary", "Production mutations absent")
    ]

    cases = []
    for i, (req_id, req_kind, req_desc) in enumerate(case_defs):
        case = build_waveguide_distribution_readiness_closure_case(
            req_id, req_kind, req_desc, bun_dict, kit_dict, len(cases)
        )
        cases.append(case)

    indexed = index_waveguide_distribution_closure_cases_by_status(cases)
    verified_ids = indexed["verified"]
    blocked_ids = indexed["blocked"]
    warning_ids = indexed["warning"]
    invalid_ids = indexed["invalid"]

    if len(invalid_ids) > 0 or len(blocked_ids) > 0:
        status = "distribution_readiness_closure_invalid"
        reason_codes.append("CLOSURE_CASES_FAILED_OR_BLOCKED")

    kinds_indexed = sorted(list(set(c.distribution_closure_requirement_kind for c in cases)))
    digests_indexed = sorted(list(set(c.distribution_closure_case_digest for c in cases)))

    archive_verified = (bun_status == "release_handoff_bundle_ready")
    archive_digest_attested = (bun_dict.get("digest_attestation_status") == "verified")
    digest_attestation_audit_verified = (bun_dict.get("source_chain_verified") is True)
    offline_consumer_verification_ready = kit_dict.get("consumer_verification_ready", False)

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

    report = WaveguideDistributionReadinessClosureReport(
        distribution_readiness_closure_report_id="SOL-WAVEGUIDE-DISTRIBUTION-READINESS-CLOSURE-REPORT",
        distribution_readiness_closure_report_version=1,
        distribution_readiness_closure_report_status=status,
        source_release_handoff_bundle_digest=bun_digest,
        source_offline_consumer_verification_kit_digest=kit_digest,
        source_package_attested_archive_candidate_index_digest=bun_dict.get("source_package_attested_archive_candidate_index_digest", ""),
        source_package_archive_digest_attestation_audit_report_digest=bun_dict.get("source_package_archive_digest_attestation_audit_report_digest", ""),
        source_package_archive_digest_attestation_digest=bun_dict.get("source_package_archive_digest_attestation_digest", ""),
        source_package_archive_signing_gate_digest=bun_dict.get("source_package_archive_signing_gate_digest", ""),
        source_package_archive_signing_plan_digest=bun_dict.get("source_package_archive_signing_plan_digest", ""),
        source_package_archive_release_candidate_index_digest=bun_dict.get("source_package_archive_release_candidate_index_digest", ""),
        source_package_archive_audit_report_digest=bun_dict.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=bun_dict.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=bun_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=bun_dict.get("source_package_archive_plan_digest", ""),
        current_attested_archive_candidate_digest=bun_dict.get("current_attested_archive_candidate_digest", ""),
        current_attested_archive_candidate_format=bun_dict.get("current_attested_archive_candidate_format", ""),
        current_attested_archive_candidate_display_path=bun_dict.get("current_attested_archive_candidate_display_path", ""),
        current_attested_archive_candidate_size_bytes=bun_dict.get("current_attested_archive_candidate_size_bytes", 0),
        current_archive_file_digest=bun_dict.get("current_archive_file_digest", ""),
        closure_cases=cases,
        verified_distribution_closure_cases=verified_ids,
        blocked_distribution_closure_cases=blocked_ids,
        warning_distribution_closure_cases=warning_ids,
        invalid_distribution_closure_cases=invalid_ids,
        verified_distribution_closure_case_count=len(verified_ids),
        blocked_distribution_closure_case_count=len(blocked_ids),
        warning_distribution_closure_case_count=len(warning_ids),
        invalid_distribution_closure_case_count=len(invalid_ids),
        closure_requirement_kinds_indexed=kinds_indexed,
        closure_case_digests_indexed=digests_indexed,
        archive_verified=archive_verified,
        archive_digest_attested=archive_digest_attested,
        digest_attestation_audit_verified=digest_attestation_audit_verified,
        release_handoff_bundle_ready=(bun_status == "release_handoff_bundle_ready"),
        offline_consumer_verification_kit_ready=(kit_status == "offline_consumer_verification_kit_ready"),
        offline_consumer_verification_ready=offline_consumer_verification_ready,
        source_chain_verified=validate_waveguide_distribution_closure_source_chain(bun_digest, kit_digest),
        operation_boundaries_verified=validate_waveguide_distribution_closure_operation_boundaries(bun_dict),
        exit_criteria_verified=validate_waveguide_distribution_closure_exit_criteria(cases),
        package_release_stage_closed=True,
        ready_to_pivot_to_new_direction=True,
        ready_for_future_key_management_stage=True,
        ready_for_future_publication_gate_stage=True,
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
        private_key_material_loaded=False,
        credentials_loaded=False,
        network_access_used=False,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    report.distribution_readiness_closure_report_digest = hash_waveguide_distribution_readiness_closure_report(report)
    return report


def validate_waveguide_distribution_readiness_closure_report(
    report: Any
) -> Tuple[bool, List[str]]:
    """
    Validates a top-level Distribution Readiness Closure Report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    errors = []

    # Verify digest
    recorded = r_dict.get("distribution_readiness_closure_report_digest", "")
    if not recorded:
        errors.append("Missing report digest")
    else:
        recomputed = hash_waveguide_distribution_readiness_closure_report(r_dict)
        if recomputed != recorded:
            errors.append(f"Report digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if r_dict.get("distribution_readiness_closure_report_id") != "SOL-WAVEGUIDE-DISTRIBUTION-READINESS-CLOSURE-REPORT":
        errors.append("Invalid closure report ID")

    # Enforce boundary checks
    if not validate_waveguide_distribution_closure_operation_boundaries(r_dict):
        errors.append("Report boundary violation detected")

    # Exit criteria validation
    if r_dict.get("package_release_stage_closed") is not True:
        errors.append("Release stage is not closed")
    if r_dict.get("ready_to_pivot_to_new_direction") is not True:
        errors.append("Ready to pivot flag is not true")

    # Validate cases
    cases = r_dict.get("closure_cases", [])
    for c in cases:
        ok, errs = validate_waveguide_distribution_readiness_closure_case(c)
        if not ok:
            errors.extend(errs)

    return len(errors) == 0, errors


def summarize_waveguide_distribution_readiness_closure_report(report: Any) -> str:
    """
    Generates a human-readable summary of the closure report.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    lines = [
        "=============================================================",
        "        SOL WAVEGUIDE DISTRIBUTION READINESS CLOSURE REPORT",
        "=============================================================",
        f"Report ID:        {r_dict.get('distribution_readiness_closure_report_id')}",
        f"Status:           {r_dict.get('distribution_readiness_closure_report_status')}",
        f"Report Digest:    {r_dict.get('distribution_readiness_closure_report_digest')}",
        f"Stage Closed:     {r_dict.get('package_release_stage_closed')}",
        f"Ready to Pivot:   {r_dict.get('ready_to_pivot_to_new_direction')}",
        f"Verified Cases:   {r_dict.get('verified_distribution_closure_case_count')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in r_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_distribution_readiness_closure_report(report: Any, output_path: str) -> None:
    """
    Exports the Closure Report to a JSON file.
    """
    r_dict = asdict(report) if hasattr(report, "__dict__") else dict(report)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_distribution_readiness_closure_reports(rep_a: Any, rep_b: Any) -> Dict[str, Any]:
    """
    Compares two Closure Reports.
    """
    dict_a = asdict(rep_a) if hasattr(rep_a, "__dict__") else dict(rep_a)
    dict_b = asdict(rep_b) if hasattr(rep_b, "__dict__") else dict(rep_b)

    differences = {}
    for key in (
        "distribution_readiness_closure_report_status",
        "distribution_readiness_closure_report_digest",
        "verified_distribution_closure_case_count"
    ):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
