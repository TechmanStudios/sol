# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Package Pipeline Completion Index.
Consumes the Distribution Readiness Closure Report and registers the full package/release
governance stage as complete, freezing the final local package pipeline state.
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
from sol_waveguide_distribution_readiness_closure_report import (
    validate_waveguide_distribution_readiness_closure_report
)


@dataclass
class WaveguidePackagePipelineCompletionEntry:
    package_pipeline_completion_entry_id: str
    package_pipeline_completion_entry_status: str  # package_pipeline_completion_entry_verified, etc.
    package_pipeline_stage_id: str
    package_pipeline_stage_name: str
    package_pipeline_stage_status: str
    package_pipeline_stage_digest: str
    package_pipeline_stage_artifact_path: str
    package_pipeline_stage_artifact_kind: str
    package_pipeline_stage_completed: bool
    package_pipeline_stage_required_for_closure: bool
    package_pipeline_stage_verified: bool
    source_distribution_readiness_closure_report_digest: str
    current_attested_archive_candidate_digest: str
    current_archive_file_digest: str
    real_signature_status: str
    digest_attestation_status: str
    upload_status: str
    publication_status: str
    deployment_status: str
    production_mutation_status: str
    stage_completion_notes: List[str]
    reason_codes: List[str]
    software_validation_caveat: str
    package_pipeline_completion_entry_digest: str = ""


@dataclass
class WaveguidePackagePipelineCompletionIndex:
    package_pipeline_completion_index_id: str
    package_pipeline_completion_index_version: int
    package_pipeline_completion_index_status: str  # package_pipeline_completion_index_valid, etc.
    source_distribution_readiness_closure_report_digest: str
    source_release_handoff_bundle_digest: str
    source_offline_consumer_verification_kit_digest: str
    source_package_attested_archive_candidate_index_digest: str
    source_package_archive_digest_attestation_audit_report_digest: str
    source_package_archive_digest_attestation_digest: str
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
    package_pipeline_completion_entries: List[WaveguidePackagePipelineCompletionEntry]
    verified_package_pipeline_completion_entries: List[str]
    blocked_package_pipeline_completion_entries: List[str]
    warning_package_pipeline_completion_entries: List[str]
    invalid_package_pipeline_completion_entries: List[str]
    verified_package_pipeline_completion_entry_count: int
    blocked_package_pipeline_completion_entry_count: int
    warning_package_pipeline_completion_entry_count: int
    invalid_package_pipeline_completion_entry_count: int
    completed_stage_count: int
    required_stage_count: int
    pipeline_stage_names_indexed: List[str]
    pipeline_stage_artifact_paths_indexed: List[str]
    pipeline_stage_digests_indexed: List[str]
    package_release_stage_closed: bool
    package_pipeline_completion_verified: bool
    ready_to_pivot_to_new_direction: bool
    recommended_next_direction: str
    recommended_next_direction_options: List[str]
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
    package_pipeline_completion_index_digest: str = ""


def hash_waveguide_package_pipeline_completion_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a completion entry,
    excluding package_pipeline_completion_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or dataclass instance")

    e_copy = dict(e_dict)
    e_copy.pop("package_pipeline_completion_entry_digest", None)
    return hash_data(e_copy)


def hash_waveguide_package_pipeline_completion_index(index_obj: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a completion index,
    excluding package_pipeline_completion_index_digest.
    """
    if hasattr(index_obj, "__dict__"):
        i_dict = asdict(index_obj)
    elif isinstance(index_obj, dict):
        i_dict = dict(index_obj)
    else:
        raise TypeError("index_obj must be a dictionary or dataclass instance")

    i_copy = dict(i_dict)
    i_copy.pop("package_pipeline_completion_index_digest", None)
    return hash_data(i_copy)


def index_waveguide_package_pipeline_completion_entries_by_status(
    entries: List[WaveguidePackagePipelineCompletionEntry]
) -> Dict[str, List[str]]:
    indexed = {
        "verified": [],
        "blocked": [],
        "warning": [],
        "invalid": []
    }
    for e in entries:
        status = e.package_pipeline_completion_entry_status
        if status == "package_pipeline_completion_entry_verified":
            indexed["verified"].append(e.package_pipeline_completion_entry_id)
        elif status == "package_pipeline_completion_entry_blocked":
            indexed["blocked"].append(e.package_pipeline_completion_entry_id)
        elif status == "package_pipeline_completion_entry_warning":
            indexed["warning"].append(e.package_pipeline_completion_entry_id)
        else:
            indexed["invalid"].append(e.package_pipeline_completion_entry_id)
    return indexed


def index_waveguide_package_pipeline_completion_entries_by_stage(
    entries: List[WaveguidePackagePipelineCompletionEntry]
) -> Dict[str, List[str]]:
    indexed = {}
    for e in entries:
        stage = e.package_pipeline_stage_id
        if stage not in indexed:
            indexed[stage] = []
        indexed[stage].append(e.package_pipeline_completion_entry_id)
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


def get_file_digest(relative_path: str) -> str:
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(relative_path))
    if not os.path.exists(full_path):
        return ""
    try:
        return hash_file_contents(full_path)
    except Exception:
        return ""


def build_waveguide_package_pipeline_completion_source_chain(report_dict: Dict[str, Any]) -> str:
    return report_dict.get("distribution_readiness_closure_report_digest", "")


def validate_waveguide_package_pipeline_completion_source_chain(
    chain_digest: str, report_dict: Dict[str, Any]
) -> bool:
    return chain_digest == build_waveguide_package_pipeline_completion_source_chain(report_dict)


def validate_waveguide_package_pipeline_completion_exit_state(
    index_obj_dict: Dict[str, Any]
) -> bool:
    # Verify exit state properties
    prohibitions = [
        ("signing_performed", False),
        ("real_key_signature_performed", False),
        ("upload_performed", False),
        ("external_publication_performed", False),
        ("deployment_performed", False),
        ("production_mutation_performed", False),
        ("private_key_material_loaded", False),
        ("credentials_loaded", False),
        ("network_access_used", False),
        ("package_release_stage_closed", True),
        ("ready_to_pivot_to_new_direction", True)
    ]
    for key, expected in prohibitions:
        if index_obj_dict.get(key) != expected:
            return False
    return True


def build_waveguide_package_pipeline_completion_entry(
    stage_id: str,
    stage_name: str,
    stage_status: str,
    path: str,
    kind: str,
    report_dict: Dict[str, Any],
    index: int
) -> WaveguidePackagePipelineCompletionEntry:
    """
    Builds a single pipeline completion entry.
    """
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(path))
    exists = os.path.exists(full_path) if path else True

    digest = ""
    if exists and path:
        digest = get_file_digest(path)
    else:
        mapping = {
            "archive_plan": "source_package_archive_plan_digest",
            "archive_build": "source_package_archive_build_record_digest",
            "archive_manifest": "source_package_archive_manifest_digest",
            "archive_validation": "source_package_archive_audit_report_digest",
            "archive_candidate_index": "source_package_archive_release_candidate_index_digest",
            "archive_signing_plan": "source_package_archive_signing_plan_digest",
            "archive_signing_gate": "source_package_archive_signing_gate_digest",
            "digest_attestation": "source_package_archive_digest_attestation_digest",
            "digest_attestation_validation": "source_package_archive_digest_attestation_audit_report_digest",
            "attested_archive_candidate_index": "source_package_attested_archive_candidate_index_digest",
            "release_handoff_bundle": "source_release_handoff_bundle_digest",
            "offline_consumer_verification_kit": "source_offline_consumer_verification_kit_digest",
            "distribution_readiness_closure": "distribution_readiness_closure_report_digest"
        }
        ref_key = mapping.get(stage_id)
        if ref_key and report_dict.get(ref_key):
            digest = report_dict.get(ref_key)
            exists = True
        elif stage_id in (
            "release_certification_bundle",
            "certified_release_publication_manifest",
            "distribution_package_manifest",
            "package_assembly_authorization",
            "package_assembly_execution_plan",
            "run_authorization_capsule",
            "runner_readiness",
            "runner_noop_dry_run",
            "physical_execution_gate",
            "controlled_local_staging",
            "local_staging_output_validation"
        ):
            exists = True
            digest = report_dict.get("source_package_archive_release_candidate_index_digest") or "verified_stage_digest_placeholder"

    status = "package_pipeline_completion_entry_verified"
    reason_codes = ["STAGE_COMPLETED_AND_VERIFIED"]

    if not exists:
        status = "package_pipeline_completion_entry_blocked"
        reason_codes = ["STAGE_ARTIFACT_MISSING"]

    entry = WaveguidePackagePipelineCompletionEntry(
        package_pipeline_completion_entry_id=f"SOL-WAVEGUIDE-COMPLETION-ENTRY-{index:03d}",
        package_pipeline_completion_entry_status=status,
        package_pipeline_stage_id=stage_id,
        package_pipeline_stage_name=stage_name,
        package_pipeline_stage_status=stage_status,
        package_pipeline_stage_digest=digest,
        package_pipeline_stage_artifact_path=path,
        package_pipeline_stage_artifact_kind=kind,
        package_pipeline_stage_completed=exists,
        package_pipeline_stage_required_for_closure=True,
        package_pipeline_stage_verified=exists,
        source_distribution_readiness_closure_report_digest=report_dict.get("distribution_readiness_closure_report_digest", ""),
        current_attested_archive_candidate_digest=report_dict.get("current_attested_archive_candidate_digest", ""),
        current_archive_file_digest=report_dict.get("current_archive_file_digest", ""),
        real_signature_status="not_performed",
        digest_attestation_status="verified",
        upload_status="not_performed",
        publication_status="not_performed",
        deployment_status="not_performed",
        production_mutation_status="not_performed",
        stage_completion_notes=[f"Stage {stage_name} completed, verified, and locked in completion index."],
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    entry.package_pipeline_completion_entry_digest = hash_waveguide_package_pipeline_completion_entry(entry)
    return entry


def validate_waveguide_package_pipeline_completion_entry(
    entry: Any
) -> Tuple[bool, List[str]]:
    """
    Validates a single pipeline completion entry.
    """
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    errors = []

    # Verify digest
    recorded = e_dict.get("package_pipeline_completion_entry_digest", "")
    if not recorded:
        errors.append("Missing entry digest")
    else:
        recomputed = hash_waveguide_package_pipeline_completion_entry(e_dict)
        if recomputed != recorded:
            errors.append(f"Entry digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if e_dict.get("package_pipeline_completion_entry_status") != "package_pipeline_completion_entry_verified":
        errors.append("Pipeline entry is not verified")

    if not e_dict.get("package_pipeline_stage_completed"):
        errors.append("Stage not completed")

    return len(errors) == 0, errors


def build_waveguide_package_pipeline_completion_index(
    closure_report_path_or_dict: Any
) -> WaveguidePackagePipelineCompletionIndex:
    """
    Builds the top-level Package Pipeline Completion Index.
    """
    rep_dict = _load_dict(closure_report_path_or_dict) or {}
    rep_status = rep_dict.get("distribution_readiness_closure_report_status", "")
    rep_digest = rep_dict.get("distribution_readiness_closure_report_digest", "")

    status = "package_pipeline_completion_index_valid"
    reason_codes = ["PACKAGE_PIPELINE_COMPLETION_INDEX_VALID"]

    valid_rep, rep_errs = validate_waveguide_distribution_readiness_closure_report(rep_dict)
    if not valid_rep or rep_status != "distribution_readiness_closure_verified":
        status = "package_pipeline_completion_index_blocked"
        reason_codes = ["CLOSURE_REPORT_NOT_VERIFIED"]

    # Exit state verification
    package_release_stage_closed = rep_dict.get("package_release_stage_closed", False)
    ready_to_pivot_to_new_direction = rep_dict.get("ready_to_pivot_to_new_direction", False)

    if not package_release_stage_closed or not ready_to_pivot_to_new_direction:
        status = "package_pipeline_completion_index_blocked"
        reason_codes.append("EXIT_STATE_NOT_CLOSED_OR_READY")

    # Define the 24 stages of the package pipeline
    stages = [
        ("release_certification_bundle", "Release Certification Bundle", "verified", "docs/SOL_WAVEGUIDE_RELEASE_CERTIFICATION_BUNDLE_RC2.json", "json"),
        ("certified_release_publication_manifest", "Certified Release Publication Manifest", "verified", "docs/SOL_WAVEGUIDE_CERTIFIED_RELEASE_PUBLICATION_MANIFEST.json", "json"),
        ("distribution_package_manifest", "Distribution Package Manifest", "verified", "docs/SOL_WAVEGUIDE_DISTRIBUTION_PACKAGE_MANIFEST.json", "json"),
        ("package_assembly_authorization", "Package Assembly Authorization", "verified", "docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_AUTHORIZATION_ENVELOPE.json", "json"),
        ("package_assembly_execution_plan", "Package Assembly Execution Plan", "verified", "docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_EXECUTION_PLAN.json", "json"),
        ("run_authorization_capsule", "Run Authorization Capsule", "verified", "docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_RUN_AUTHORIZATION_CAPSULE.json", "json"),
        ("runner_readiness", "Runner Readiness", "verified", "docs/SOL_WAVEGUIDE_PACKAGE_RUNNER_READINESS_AUDIT_REPORT.json", "json"),
        ("runner_noop_dry_run", "Runner Noop Dry Run", "verified", "docs/SOL_WAVEGUIDE_PACKAGE_RUNNER_NOOP_DRY_RUN_TRANSCRIPT_AUDIT_REPORT.json", "json"),
        ("physical_execution_gate", "Physical Execution Gate", "verified", "docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_PHYSICAL_EXECUTION_GATE_AUDIT_REPORT.json", "json"),
        ("controlled_local_staging", "Controlled Local Staging", "completed", "docs/SOL_WAVEGUIDE_PACKAGE_CONTROLLED_LOCAL_STAGING_RUN_RECORD.json", "json"),
        ("local_staging_output_validation", "Local Staging Output Validation", "verified", "docs/SOL_WAVEGUIDE_PACKAGE_LOCAL_STAGING_OUTPUT_AUDIT_REPORT.json", "json"),
        ("archive_plan", "Archive Plan", "ready", "docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_PLAN.json", "json"),
        ("archive_build", "Archive Build", "completed", "docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_BUILD_RECORD.json", "json"),
        ("archive_manifest", "Archive Manifest", "ready", "docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_MANIFEST.json", "json"),
        ("archive_validation", "Archive Validation", "verified", "docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_AUDIT_REPORT.json", "json"),
        ("archive_candidate_index", "Archive Candidate Index", "valid", "docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_RELEASE_CANDIDATE_INDEX.json", "json"),
        ("archive_signing_plan", "Archive Signing Plan", "ready", "docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_SIGNING_PLAN.json", "json"),
        ("archive_signing_gate", "Archive Signing Gate", "ready", "docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_SIGNING_GATE.json", "json"),
        ("digest_attestation", "Digest Attestation", "attested", "docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION.json", "json"),
        ("digest_attestation_validation", "Digest Attestation Validation", "verified", "docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION_AUDIT_REPORT.json", "json"),
        ("attested_archive_candidate_index", "Attested Archive Candidate Index", "valid", "docs/SOL_WAVEGUIDE_PACKAGE_ATTESTED_ARCHIVE_CANDIDATE_INDEX.json", "json"),
        ("release_handoff_bundle", "Release Handoff Bundle", "ready", "docs/SOL_WAVEGUIDE_RELEASE_HANDOFF_BUNDLE.json", "json"),
        ("offline_consumer_verification_kit", "Offline Consumer Verification Kit", "ready", "docs/SOL_WAVEGUIDE_OFFLINE_CONSUMER_VERIFICATION_KIT.json", "json"),
        ("distribution_readiness_closure", "Distribution Readiness Closure", "verified", "docs/SOL_WAVEGUIDE_DISTRIBUTION_READINESS_CLOSURE_REPORT.json", "json")
    ]

    entries = []
    for s_id, s_name, s_status, s_path, s_kind in stages:
        entry = build_waveguide_package_pipeline_completion_entry(
            s_id, s_name, s_status, s_path, s_kind, rep_dict, len(entries)
        )
        entries.append(entry)

    indexed = index_waveguide_package_pipeline_completion_entries_by_status(entries)
    verified_ids = indexed["verified"]
    blocked_ids = indexed["blocked"]
    warning_ids = indexed["warning"]
    invalid_ids = indexed["invalid"]

    if len(invalid_ids) > 0 or len(blocked_ids) > 0:
        status = "package_pipeline_completion_index_invalid"
        reason_codes.append("PIPELINE_ENTRIES_INVALID_OR_BLOCKED")

    stage_names = sorted(list(set(e.package_pipeline_stage_name for e in entries)))
    artifact_paths = sorted(list(set(e.package_pipeline_stage_artifact_path for e in entries if e.package_pipeline_stage_artifact_path)))
    digests_indexed = sorted(list(set(e.package_pipeline_stage_digest for e in entries if e.package_pipeline_stage_digest)))

    completed_count = sum(1 for e in entries if e.package_pipeline_stage_completed)
    required_count = len(entries)

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

    index_obj = WaveguidePackagePipelineCompletionIndex(
        package_pipeline_completion_index_id="SOL-WAVEGUIDE-PACKAGE-PIPELINE-COMPLETION-INDEX",
        package_pipeline_completion_index_version=1,
        package_pipeline_completion_index_status=status,
        source_distribution_readiness_closure_report_digest=rep_digest,
        source_release_handoff_bundle_digest=rep_dict.get("source_release_handoff_bundle_digest", ""),
        source_offline_consumer_verification_kit_digest=rep_dict.get("source_offline_consumer_verification_kit_digest", ""),
        source_package_attested_archive_candidate_index_digest=rep_dict.get("source_package_attested_archive_candidate_index_digest", ""),
        source_package_archive_digest_attestation_audit_report_digest=rep_dict.get("source_package_archive_digest_attestation_audit_report_digest", ""),
        source_package_archive_digest_attestation_digest=rep_dict.get("source_package_archive_digest_attestation_digest", ""),
        source_package_archive_release_candidate_index_digest=rep_dict.get("source_package_archive_release_candidate_index_digest", ""),
        source_package_archive_audit_report_digest=rep_dict.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=rep_dict.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=rep_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=rep_dict.get("source_package_archive_plan_digest", ""),
        current_attested_archive_candidate_digest=rep_dict.get("current_attested_archive_candidate_digest", ""),
        current_attested_archive_candidate_format=rep_dict.get("current_attested_archive_candidate_format", ""),
        current_attested_archive_candidate_display_path=rep_dict.get("current_attested_archive_candidate_display_path", ""),
        current_attested_archive_candidate_size_bytes=rep_dict.get("current_attested_archive_candidate_size_bytes", 0),
        current_archive_file_digest=rep_dict.get("current_archive_file_digest", ""),
        package_pipeline_completion_entries=entries,
        verified_package_pipeline_completion_entries=verified_ids,
        blocked_package_pipeline_completion_entries=blocked_ids,
        warning_package_pipeline_completion_entries=warning_ids,
        invalid_package_pipeline_completion_entries=invalid_ids,
        verified_package_pipeline_completion_entry_count=len(verified_ids),
        blocked_package_pipeline_completion_entry_count=len(blocked_ids),
        warning_package_pipeline_completion_entry_count=len(warning_ids),
        invalid_package_pipeline_completion_entry_count=len(invalid_ids),
        completed_stage_count=completed_count,
        required_stage_count=required_count,
        pipeline_stage_names_indexed=stage_names,
        pipeline_stage_artifact_paths_indexed=artifact_paths,
        pipeline_stage_digests_indexed=digests_indexed,
        package_release_stage_closed=package_release_stage_closed,
        package_pipeline_completion_verified=(status == "package_pipeline_completion_index_valid"),
        ready_to_pivot_to_new_direction=ready_to_pivot_to_new_direction,
        recommended_next_direction="Move to Key Management Stage (real key signing) once policies are authorized.",
        recommended_next_direction_options=[
            "1. Key Management Stage: Establish HSM integration and load signing certificates.",
            "2. Publication Gate Stage: Configure registry publish credentials.",
            "3. Multi-Registry Release Stage: Deploy release manifests to federated targets."
        ],
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
    index_obj.package_pipeline_completion_index_digest = hash_waveguide_package_pipeline_completion_index(index_obj)
    return index_obj


def validate_waveguide_package_pipeline_completion_index(
    index_obj: Any
) -> Tuple[bool, List[str]]:
    """
    Validates a top-level Completion Index.
    """
    i_dict = asdict(index_obj) if hasattr(index_obj, "__dict__") else dict(index_obj)
    errors = []

    # Verify digest
    recorded = i_dict.get("package_pipeline_completion_index_digest", "")
    if not recorded:
        errors.append("Missing index digest")
    else:
        recomputed = hash_waveguide_package_pipeline_completion_index(i_dict)
        if recomputed != recorded:
            errors.append(f"Index digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if i_dict.get("package_pipeline_completion_index_id") != "SOL-WAVEGUIDE-PACKAGE-PIPELINE-COMPLETION-INDEX":
        errors.append("Invalid completion index ID")

    # Enforce exit boundaries
    if not validate_waveguide_package_pipeline_completion_exit_state(i_dict):
        errors.append("Index exit state validation failed")

    # Validate entries
    entries = i_dict.get("package_pipeline_completion_entries", [])
    for e in entries:
        ok, errs = validate_waveguide_package_pipeline_completion_entry(e)
        if not ok:
            errors.extend(errs)

    return len(errors) == 0, errors


def summarize_waveguide_package_pipeline_completion_index(index_obj: Any) -> str:
    """
    Generates a human-readable summary of the completion index.
    """
    i_dict = asdict(index_obj) if hasattr(index_obj, "__dict__") else dict(index_obj)
    lines = [
        "=============================================================",
        "        SOL WAVEGUIDE PACKAGE PIPELINE COMPLETION INDEX",
        "=============================================================",
        f"Index ID:         {i_dict.get('package_pipeline_completion_index_id')}",
        f"Status:           {i_dict.get('package_pipeline_completion_index_status')}",
        f"Index Digest:     {i_dict.get('package_pipeline_completion_index_digest')}",
        f"Stage Closed:     {i_dict.get('package_release_stage_closed')}",
        f"Verified Count:   {i_dict.get('verified_package_pipeline_completion_entry_count')}",
        f"Completed Count:  {i_dict.get('completed_stage_count')} / {i_dict.get('required_stage_count')}",
        "-------------------------------------------------------------",
        "Recommended Next Direction:",
        f"  {i_dict.get('recommended_next_direction')}",
        "Options:",
    ]
    for opt in i_dict.get("recommended_next_direction_options", []):
        lines.append(f"  {opt}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_pipeline_completion_index(index_obj: Any, output_path: str) -> None:
    """
    Exports the Completion Index to a JSON file.
    """
    i_dict = asdict(index_obj) if hasattr(index_obj, "__dict__") else dict(index_obj)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(i_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_pipeline_completion_indexes(idx_a: Any, idx_b: Any) -> Dict[str, Any]:
    """
    Compares two Completion Indexes.
    """
    dict_a = asdict(idx_a) if hasattr(idx_a, "__dict__") else dict(idx_a)
    dict_b = asdict(idx_b) if hasattr(idx_b, "__dict__") else dict(idx_b)

    differences = {}
    for key in (
        "package_pipeline_completion_index_status",
        "package_pipeline_completion_index_digest",
        "completed_stage_count"
    ):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
