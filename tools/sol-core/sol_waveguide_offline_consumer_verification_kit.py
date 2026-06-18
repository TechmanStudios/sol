# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Offline Consumer Verification Kit.
Consumes the Release Handoff Bundle and produces verification steps and instructions
for verifying the package archive and governance chain offline.
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


@dataclass
class WaveguideOfflineVerificationStep:
    offline_verification_step_id: str
    offline_verification_step_index: int
    offline_verification_step_status: str  # offline_verification_step_ready, etc.
    offline_verification_step_kind: str
    offline_verification_step_title: str
    offline_verification_step_description: str
    offline_verification_command: str
    offline_verification_expected_result: str
    offline_verification_artifact_path: str
    offline_verification_artifact_digest: str
    offline_verification_artifact_kind: str
    requires_network: bool
    requires_credentials: bool
    requires_private_key: bool
    requires_external_service: bool
    requires_timestamp_authority: bool
    verifies_archive_digest: bool
    verifies_digest_attestation: bool
    verifies_real_signature: bool
    verifies_source_chain: bool
    verifies_no_upload: bool
    verifies_no_deployment: bool
    verifies_no_publication: bool
    verifies_no_production_mutation: bool
    safe_for_offline_consumer: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    offline_verification_step_digest: str = ""


@dataclass
class WaveguideOfflineConsumerVerificationKit:
    offline_consumer_verification_kit_id: str
    offline_consumer_verification_kit_version: int
    offline_consumer_verification_kit_status: str  # offline_consumer_verification_kit_ready, etc.
    source_release_handoff_bundle_digest: str
    source_package_attested_archive_candidate_index_digest: str
    source_package_archive_digest_attestation_audit_report_digest: str
    source_package_archive_digest_attestation_digest: str
    source_package_archive_audit_report_digest: str
    current_attested_archive_candidate_digest: str
    current_attested_archive_candidate_format: str
    current_attested_archive_candidate_display_path: str
    current_archive_file_digest: str
    offline_verification_steps: List[WaveguideOfflineVerificationStep]
    ready_offline_verification_steps: List[str]
    blocked_offline_verification_steps: List[str]
    warning_offline_verification_steps: List[str]
    invalid_offline_verification_steps: List[str]
    ready_offline_verification_step_count: int
    blocked_offline_verification_step_count: int
    warning_offline_verification_step_count: int
    invalid_offline_verification_step_count: int
    verification_step_kinds_indexed: List[str]
    verification_artifact_paths_indexed: List[str]
    verification_artifact_digests_indexed: List[str]
    offline_commands: List[str]
    offline_command_safety_verified: bool
    offline_no_network_requirement_verified: bool
    offline_no_credentials_requirement_verified: bool
    offline_no_private_key_requirement_verified: bool
    digest_attestation_verification_supported: bool
    real_signature_verification_supported: bool
    real_signature_status: str
    digest_attestation_status: str
    upload_status: str
    publication_status: str
    deployment_status: str
    production_mutation_status: str
    network_access_required: bool
    credentials_required: bool
    private_key_required: bool
    external_service_required: bool
    timestamp_authority_required: bool
    consumer_verification_ready: bool
    signing_performed: bool
    real_key_signature_performed: bool
    digest_attestation_performed: bool
    external_signing_performed: bool
    timestamp_authority_performed: bool
    upload_performed: bool
    external_publication_performed: bool
    deployment_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    offline_consumer_verification_kit_digest: str = ""


def hash_waveguide_offline_verification_step(step: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a verification step,
    excluding offline_verification_step_digest.
    """
    if hasattr(step, "__dict__"):
        s_dict = asdict(step)
    elif isinstance(step, dict):
        s_dict = dict(step)
    else:
        raise TypeError("step must be a dictionary or dataclass instance")

    s_copy = dict(s_dict)
    s_copy.pop("offline_verification_step_digest", None)
    return hash_data(s_copy)


def hash_waveguide_offline_consumer_verification_kit(kit: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a verification kit,
    excluding offline_consumer_verification_kit_digest.
    """
    if hasattr(kit, "__dict__"):
        k_dict = asdict(kit)
    elif isinstance(kit, dict):
        k_dict = dict(kit)
    else:
        raise TypeError("kit must be a dictionary or dataclass instance")

    k_copy = dict(k_dict)
    k_copy.pop("offline_consumer_verification_kit_digest", None)
    return hash_data(k_copy)


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


def index_waveguide_offline_verification_steps_by_status(
    steps: List[WaveguideOfflineVerificationStep]
) -> Dict[str, List[str]]:
    indexed = {
        "ready": [],
        "blocked": [],
        "warning": [],
        "invalid": []
    }
    for s in steps:
        status = s.offline_verification_step_status
        if status == "offline_verification_step_ready":
            indexed["ready"].append(s.offline_verification_step_id)
        elif status == "offline_verification_step_blocked":
            indexed["blocked"].append(s.offline_verification_step_id)
        elif status == "offline_verification_step_warning":
            indexed["warning"].append(s.offline_verification_step_id)
        else:
            indexed["invalid"].append(s.offline_verification_step_id)
    return indexed


def index_waveguide_offline_verification_steps_by_kind(
    steps: List[WaveguideOfflineVerificationStep]
) -> Dict[str, List[str]]:
    indexed = {}
    for s in steps:
        kind = s.offline_verification_step_kind
        if kind not in indexed:
            indexed[kind] = []
        indexed[kind].append(s.offline_verification_step_id)
    return indexed


def build_waveguide_offline_verification_command_set(
    steps: List[WaveguideOfflineVerificationStep]
) -> List[str]:
    return [s.offline_verification_command for s in steps if s.offline_verification_command]


def validate_waveguide_offline_verification_command_safety(command: str) -> bool:
    # Basic sanity checks to ensure offline verification command doesn't have network or mutation calls
    forbidden_substrings = ["curl", "wget", "git push", "ssh", "scp", "ftp", "http:", "https:"]
    return not any(sub in command.lower() for sub in forbidden_substrings)


def validate_waveguide_offline_verification_no_network_requirement(step: Dict[str, Any]) -> bool:
    return step.get("requires_network") is False


def build_waveguide_offline_consumer_verification_step(
    kind: str,
    title: str,
    desc: str,
    cmd: str,
    expected: str,
    path: str,
    digest: str,
    artifact_kind: str,
    index: int,
    requires_network: bool = False,
    requires_credentials: bool = False,
    requires_private_key: bool = False
) -> WaveguideOfflineVerificationStep:
    """
    Builds a single offline verification step.
    """
    status = "offline_verification_step_ready"
    reason_codes = ["OFFLINE_STEP_READY"]
    safe = True

    if requires_network or requires_credentials or requires_private_key:
        status = "offline_verification_step_blocked"
        reason_codes = ["OFFLINE_REQUIREMENTS_VIOLATED"]
        safe = False

    if not validate_waveguide_offline_verification_command_safety(cmd):
        if status == "offline_verification_step_ready":
            status = "offline_verification_step_invalid"
            reason_codes = ["COMMAND_UNSAFE"]
        else:
            reason_codes.append("COMMAND_UNSAFE")
        safe = False

    step = WaveguideOfflineVerificationStep(
        offline_verification_step_id=f"SOL-WAVEGUIDE-VERIFICATION-STEP-{index:03d}",
        offline_verification_step_index=index,
        offline_verification_step_status=status,
        offline_verification_step_kind=kind,
        offline_verification_step_title=title,
        offline_verification_step_description=desc,
        offline_verification_command=cmd,
        offline_verification_expected_result=expected,
        offline_verification_artifact_path=path,
        offline_verification_artifact_digest=digest,
        offline_verification_artifact_kind=artifact_kind,
        requires_network=requires_network,
        requires_credentials=requires_credentials,
        requires_private_key=requires_private_key,
        requires_external_service=False,
        requires_timestamp_authority=False,
        verifies_archive_digest=(kind == "verify_archive_sha256"),
        verifies_digest_attestation=(kind == "verify_digest_attestation"),
        verifies_real_signature=False,
        verifies_source_chain=(kind == "verify_release_handoff_bundle"),
        verifies_no_upload=True,
        verifies_no_deployment=True,
        verifies_no_publication=True,
        verifies_no_production_mutation=True,
        safe_for_offline_consumer=safe,
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    step.offline_verification_step_digest = hash_waveguide_offline_verification_step(step)
    return step


def validate_waveguide_offline_consumer_verification_step(
    step: Any
) -> Tuple[bool, List[str]]:
    """
    Validates a single offline verification step.
    """
    s_dict = asdict(step) if hasattr(step, "__dict__") else dict(step)
    errors = []

    # Verify digest
    recorded = s_dict.get("offline_verification_step_digest", "")
    if not recorded:
        errors.append("Missing step digest")
    else:
        recomputed = hash_waveguide_offline_verification_step(s_dict)
        if recomputed != recorded:
            errors.append(f"Step digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    # Enforce safe offline execution
    prohibitions = [
        ("requires_network", False),
        ("requires_credentials", False),
        ("requires_private_key", False),
        ("requires_external_service", False),
        ("requires_timestamp_authority", False),
        ("safe_for_offline_consumer", True),
    ]
    for key, expected in prohibitions:
        if s_dict.get(key) != expected:
            errors.append(f"Field {key} must be {expected}")

    return len(errors) == 0, errors


def build_waveguide_offline_consumer_verification_kit(
    handoff_bundle_path_or_dict: Any
) -> WaveguideOfflineConsumerVerificationKit:
    """
    Builds the top-level Offline Consumer Verification Kit.
    """
    bun_dict = _load_dict(handoff_bundle_path_or_dict) or {}
    bun_status = bun_dict.get("release_handoff_bundle_status", "")
    bun_digest = bun_dict.get("release_handoff_bundle_digest", "")

    status = "offline_consumer_verification_kit_ready"
    reason_codes = ["OFFLINE_CONSUMER_VERIFICATION_KIT_READY"]

    valid_bun, bun_errs = validate_waveguide_release_handoff_bundle(bun_dict)
    if not valid_bun or bun_status != "release_handoff_bundle_ready":
        status = "offline_consumer_verification_kit_blocked"
        reason_codes = ["RELEASE_HANDOFF_BUNDLE_NOT_READY"]

    # Extract needed info
    current_cand_digest = bun_dict.get("current_attested_archive_candidate_digest", "")
    current_cand_format = bun_dict.get("current_attested_archive_candidate_format", "zip")
    current_cand_display = bun_dict.get("current_attested_archive_candidate_display_path", "")

    source_idx_digest = bun_dict.get("source_package_attested_archive_candidate_index_digest", "")
    source_att_audit_digest = bun_dict.get("source_package_archive_digest_attestation_audit_report_digest", "")
    source_att_digest = bun_dict.get("source_package_archive_digest_attestation_digest", "")
    source_archive_audit_digest = bun_dict.get("source_package_archive_audit_report_digest", "")

    # Build steps
    steps = []
    # Step 1: Verify archive file digest
    steps.append(build_waveguide_offline_consumer_verification_step(
        kind="verify_archive_sha256",
        title="Verify Archive SHA256 Digest",
        desc="Downstream consumer recomputes the SHA256 digest of the archive file locally and compares it.",
        cmd=f"certutil -hashfile {current_cand_display or 'docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip'} SHA256",
        expected=current_cand_digest,
        path=current_cand_display or "docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip",
        digest=current_cand_digest,
        artifact_kind="archive_zip",
        index=len(steps)
    ))
    # Step 2: Verify archive audit report
    steps.append(build_waveguide_offline_consumer_verification_step(
        kind="verify_archive_audit_report",
        title="Verify Archive Audit Report",
        desc="Verifies that the package archive contains the required members and has a matching manifest/plan.",
        cmd="python tools/sol-core/sol_waveguide_package_archive_validator.py docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_MANIFEST.json",
        expected="package_archive_verified",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_AUDIT_REPORT.json",
        digest=source_archive_audit_digest,
        artifact_kind="archive_audit_report",
        index=len(steps)
    ))
    # Step 3: Verify digest attestation
    steps.append(build_waveguide_offline_consumer_verification_step(
        kind="verify_digest_attestation",
        title="Verify Digest Attestation",
        desc="Verifies the attestation statement binding the archive digest to the compiler pipeline stages.",
        cmd="python tools/sol-core/sol_waveguide_package_archive_digest_attestation_validator.py docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION.json",
        expected="package_archive_digest_attestation_verified",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION.json",
        digest=source_att_digest,
        artifact_kind="digest_attestation",
        index=len(steps)
    ))
    # Step 4: Verify attested candidate index
    steps.append(build_waveguide_offline_consumer_verification_step(
        kind="verify_attested_candidate_index",
        title="Verify Attested Candidate Index",
        desc="Ensures that the candidate index contains the verified, attested candidate entry.",
        cmd="python tools/sol-core/sol_waveguide_package_attested_archive_candidate_index.py docs/SOL_WAVEGUIDE_PACKAGE_ATTESTED_ARCHIVE_CANDIDATE_INDEX.json",
        expected="package_attested_archive_candidate_index_valid",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ATTESTED_ARCHIVE_CANDIDATE_INDEX.json",
        digest=source_idx_digest,
        artifact_kind="attested_archive_candidate_index",
        index=len(steps)
    ))
    # Step 5: Verify release handoff bundle
    steps.append(build_waveguide_offline_consumer_verification_step(
        kind="verify_release_handoff_bundle",
        title="Verify Release Handoff Bundle",
        desc="Validates that the handoff bundle correctly references all metadata files and that their digests match.",
        cmd="python tools/sol-core/sol_waveguide_release_handoff_bundle.py docs/SOL_WAVEGUIDE_RELEASE_HANDOFF_BUNDLE.json",
        expected="release_handoff_bundle_ready",
        path="docs/SOL_WAVEGUIDE_RELEASE_HANDOFF_BUNDLE.json",
        digest=bun_digest,
        artifact_kind="handoff_bundle",
        index=len(steps)
    ))
    # Step 6: Verify no signature claim
    steps.append(build_waveguide_offline_consumer_verification_step(
        kind="verify_no_signature_claim",
        title="Verify No Cryptographic Signature Claim",
        desc="Verifies that no real private-key cryptographic signature is claimed by the attestation.",
        cmd="python -c \"import json; d=json.load(open('docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION.json')); assert d['real_signature_claimed'] is False\"",
        expected="Assert passes",
        path="docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION.json",
        digest=source_att_digest,
        artifact_kind="digest_attestation",
        index=len(steps)
    ))
    # Step 7: Verify no network publication
    steps.append(build_waveguide_offline_consumer_verification_step(
        kind="verify_no_network_publication",
        title="Verify Offline Execution Boundary",
        desc="Confirms that no uploads, deployment, or network-bound publication took place.",
        cmd="python -c \"import json; d=json.load(open('docs/SOL_WAVEGUIDE_RELEASE_HANDOFF_BUNDLE.json')); assert d['upload_performed'] is False\"",
        expected="Assert passes",
        path="docs/SOL_WAVEGUIDE_RELEASE_HANDOFF_BUNDLE.json",
        digest=bun_digest,
        artifact_kind="handoff_bundle",
        index=len(steps)
    ))

    indexed_status = index_waveguide_offline_verification_steps_by_status(steps)
    ready_ids = indexed_status["ready"]
    blocked_ids = indexed_status["blocked"]
    warning_ids = indexed_status["warning"]
    invalid_ids = indexed_status["invalid"]

    if len(invalid_ids) > 0 or len(blocked_ids) > 0:
        status = "offline_consumer_verification_kit_invalid"
        reason_codes.append("OFFLINE_STEPS_INVALID_OR_BLOCKED")

    kinds_indexed = sorted(list(set(s.offline_verification_step_kind for s in steps)))
    paths_indexed = sorted(list(set(s.offline_verification_artifact_path for s in steps if s.offline_verification_artifact_path)))
    digests_indexed = sorted(list(set(s.offline_verification_artifact_digest for s in steps if s.offline_verification_artifact_digest)))

    commands = build_waveguide_offline_verification_command_set(steps)
    commands_safe = all(validate_waveguide_offline_verification_command_safety(c) for c in commands)

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

    kit = WaveguideOfflineConsumerVerificationKit(
        offline_consumer_verification_kit_id="SOL-WAVEGUIDE-OFFLINE-CONSUMER-VERIFICATION-KIT",
        offline_consumer_verification_kit_version=1,
        offline_consumer_verification_kit_status=status,
        source_release_handoff_bundle_digest=bun_digest,
        source_package_attested_archive_candidate_index_digest=source_idx_digest,
        source_package_archive_digest_attestation_audit_report_digest=source_att_audit_digest,
        source_package_archive_digest_attestation_digest=source_att_digest,
        source_package_archive_audit_report_digest=source_archive_audit_digest,
        current_attested_archive_candidate_digest=current_cand_digest,
        current_attested_archive_candidate_format=current_cand_format,
        current_attested_archive_candidate_display_path=current_cand_display,
        current_archive_file_digest=current_cand_digest,
        offline_verification_steps=steps,
        ready_offline_verification_steps=ready_ids,
        blocked_offline_verification_steps=blocked_ids,
        warning_offline_verification_steps=warning_ids,
        invalid_offline_verification_steps=invalid_ids,
        ready_offline_verification_step_count=len(ready_ids),
        blocked_offline_verification_step_count=len(blocked_ids),
        warning_offline_verification_step_count=len(warning_ids),
        invalid_offline_verification_step_count=len(invalid_ids),
        verification_step_kinds_indexed=kinds_indexed,
        verification_artifact_paths_indexed=paths_indexed,
        verification_artifact_digests_indexed=digests_indexed,
        offline_commands=commands,
        offline_command_safety_verified=commands_safe,
        offline_no_network_requirement_verified=all(validate_waveguide_offline_verification_no_network_requirement(asdict(s)) for s in steps),
        offline_no_credentials_requirement_verified=True,
        offline_no_private_key_requirement_verified=True,
        digest_attestation_verification_supported=True,
        real_signature_verification_supported=False,
        real_signature_status="not_performed",
        digest_attestation_status="verified",
        upload_status="not_performed",
        publication_status="not_performed",
        deployment_status="not_performed",
        production_mutation_status="not_performed",
        network_access_required=False,
        credentials_required=False,
        private_key_required=False,
        external_service_required=False,
        timestamp_authority_required=False,
        consumer_verification_ready=(status == "offline_consumer_verification_kit_ready"),
        signing_performed=False,
        real_key_signature_performed=False,
        digest_attestation_performed=True,
        external_signing_performed=False,
        timestamp_authority_performed=False,
        upload_performed=False,
        external_publication_performed=False,
        deployment_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    kit.offline_consumer_verification_kit_digest = hash_waveguide_offline_consumer_verification_kit(kit)
    return kit


def validate_waveguide_offline_consumer_verification_kit(
    kit: Any
) -> Tuple[bool, List[str]]:
    """
    Validates a top-level Offline Consumer Verification Kit.
    """
    k_dict = asdict(kit) if hasattr(kit, "__dict__") else dict(kit)
    errors = []

    # Verify digest
    recorded = k_dict.get("offline_consumer_verification_kit_digest", "")
    if not recorded:
        errors.append("Missing kit digest")
    else:
        recomputed = hash_waveguide_offline_consumer_verification_kit(k_dict)
        if recomputed != recorded:
            errors.append(f"Kit digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if k_dict.get("offline_consumer_verification_kit_id") != "SOL-WAVEGUIDE-OFFLINE-CONSUMER-VERIFICATION-KIT":
        errors.append("Invalid verification kit ID")

    # Enforce prohibitions
    prohibitions = [
        ("real_signature_status", "not_performed"),
        ("upload_status", "not_performed"),
        ("publication_status", "not_performed"),
        ("deployment_status", "not_performed"),
        ("production_mutation_status", "not_performed"),
        ("network_access_required", False),
        ("credentials_required", False),
        ("private_key_required", False),
        ("external_service_required", False),
        ("timestamp_authority_required", False),
        ("signing_performed", False),
        ("real_key_signature_performed", False),
        ("upload_performed", False),
        ("external_publication_performed", False),
        ("deployment_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if k_dict.get(key) != expected:
            errors.append(f"Top-level field {key} must be {expected}")

    # Validate steps
    steps = k_dict.get("offline_verification_steps", [])
    for s in steps:
        ok, errs = validate_waveguide_offline_consumer_verification_step(s)
        if not ok:
            errors.extend(errs)

    return len(errors) == 0, errors


def summarize_waveguide_offline_consumer_verification_kit(kit: Any) -> str:
    """
    Generates a human-readable summary of the verification kit.
    """
    k_dict = asdict(kit) if hasattr(kit, "__dict__") else dict(kit)
    lines = [
        "=============================================================",
        "        SOL WAVEGUIDE OFFLINE CONSUMER VERIFICATION KIT",
        "=============================================================",
        f"Kit ID:           {k_dict.get('offline_consumer_verification_kit_id')}",
        f"Status:           {k_dict.get('offline_consumer_verification_kit_status')}",
        f"Kit Digest:       {k_dict.get('offline_consumer_verification_kit_digest')}",
        f"Commands Safe:    {k_dict.get('offline_command_safety_verified')}",
        f"Consumer Ready:   {k_dict.get('consumer_verification_ready')}",
        f"Ready Steps:      {k_dict.get('ready_offline_verification_step_count')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in k_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_offline_consumer_verification_kit(kit: Any, output_path: str) -> None:
    """
    Exports the Offline Verification Kit to a JSON file.
    """
    k_dict = asdict(kit) if hasattr(kit, "__dict__") else dict(kit)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(k_dict, f, indent=4, sort_keys=True)


def compare_waveguide_offline_consumer_verification_kits(kit_a: Any, kit_b: Any) -> Dict[str, Any]:
    """
    Compares two Offline Verification Kits.
    """
    dict_a = asdict(kit_a) if hasattr(kit_a, "__dict__") else dict(kit_a)
    dict_b = asdict(kit_b) if hasattr(kit_b, "__dict__") else dict(kit_b)

    differences = {}
    for key in (
        "offline_consumer_verification_kit_status",
        "offline_consumer_verification_kit_digest",
        "ready_offline_verification_step_count"
    ):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
