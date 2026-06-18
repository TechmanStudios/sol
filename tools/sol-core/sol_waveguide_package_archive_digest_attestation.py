# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Package Archive Digest Attestation.
Consumes the Package Archive Signing Gate and creates a local digest attestation
for the current verified archive candidate.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_package_archive_builder import (
    compute_waveguide_package_archive_digest
)
from sol_waveguide_package_archive_signing_gate import (
    validate_waveguide_package_archive_signing_gate
)


@dataclass
class WaveguidePackageArchiveDigestAttestationStatement:
    archive_digest_attestation_statement_id: str
    archive_digest_attestation_statement_status: str  # archive_digest_attestation_statement_ready, etc.
    archive_candidate_digest: str
    archive_candidate_kind: str
    archive_format: str
    archive_filename: str
    archive_display_path: str
    archive_file_digest_recorded: str
    archive_file_digest_recomputed: str
    archive_file_digest_match: bool
    archive_file_size_bytes: int
    source_package_archive_signing_gate_digest: str
    source_package_archive_signing_plan_digest: str
    source_package_archive_release_candidate_index_digest: str
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    attestation_kind: str
    attestation_algorithm: str
    attestation_hash_algorithm: str
    attestation_statement_text: str
    attestation_scope: str
    real_signature_claimed: bool
    real_key_signing_used: bool
    external_signing_used: bool
    timestamp_authority_used: bool
    private_key_material_loaded: bool
    credentials_loaded: bool
    network_access_used: bool
    upload_performed: bool
    deployment_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    archive_digest_attestation_statement_digest: str = ""


@dataclass
class WaveguidePackageArchiveDigestAttestation:
    package_archive_digest_attestation_id: str
    package_archive_digest_attestation_version: int
    package_archive_digest_attestation_status: str  # package_archive_digest_attested, etc.
    source_package_archive_signing_gate_digest: str
    source_package_archive_signing_plan_digest: str
    source_package_archive_release_candidate_index_digest: str
    source_package_archive_audit_report_digest: str
    source_package_archive_manifest_digest: str
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_digest_attestation_statements: List[WaveguidePackageArchiveDigestAttestationStatement]
    ready_archive_digest_attestation_statements: List[str]
    blocked_archive_digest_attestation_statements: List[str]
    warning_archive_digest_attestation_statements: List[str]
    invalid_archive_digest_attestation_statements: List[str]
    ready_archive_digest_attestation_statement_count: int
    blocked_archive_digest_attestation_statement_count: int
    warning_archive_digest_attestation_statement_count: int
    invalid_archive_digest_attestation_statement_count: int
    archive_candidate_digest: str
    archive_candidate_kind: str
    archive_format: str
    archive_filename: str
    archive_display_path: str
    archive_file_digest_recorded: str
    archive_file_digest_recomputed: str
    archive_file_digest_match: bool
    archive_file_size_bytes: int
    attestation_kind: str
    attestation_algorithm: str
    attestation_hash_algorithm: str
    real_signature_status: str
    digest_attestation_status: str
    signing_status: str
    upload_status: str
    publication_status: str
    deployment_status: str
    production_mutation_status: str
    real_signature_claimed: bool
    real_key_signing_used: bool
    external_signing_used: bool
    timestamp_authority_used: bool
    private_key_material_loaded: bool
    credentials_loaded: bool
    network_access_used: bool
    signing_performed: bool
    real_key_signature_performed: bool
    digest_attestation_performed: bool
    external_signing_performed: bool
    timestamp_authority_performed: bool
    upload_performed: bool
    deployment_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    package_archive_digest_attestation_digest: str = ""


def hash_waveguide_package_archive_digest_attestation_statement(statement: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an attestation statement,
    excluding archive_digest_attestation_statement_digest.
    """
    if hasattr(statement, "__dict__"):
        s_dict = asdict(statement)
    elif isinstance(statement, dict):
        s_dict = dict(statement)
    else:
        raise TypeError("statement must be a dictionary or dataclass instance")

    s_copy = dict(s_dict)
    s_copy.pop("archive_digest_attestation_statement_digest", None)
    return hash_data(s_copy)


def hash_waveguide_package_archive_digest_attestation(attestation: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a top-level attestation,
    excluding package_archive_digest_attestation_digest.
    """
    if hasattr(attestation, "__dict__"):
        a_dict = asdict(attestation)
    elif isinstance(attestation, dict):
        a_dict = dict(attestation)
    else:
        raise TypeError("attestation must be a dictionary or dataclass instance")

    a_copy = dict(a_dict)
    a_copy.pop("package_archive_digest_attestation_digest", None)
    return hash_data(a_copy)


def recompute_waveguide_package_archive_digest_for_attestation(archive_filepath: str) -> str:
    """
    Computes the SHA256 digest of the actual archive file.
    """
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(archive_filepath))
    if not os.path.exists(full_path):
        return ""
    return compute_waveguide_package_archive_digest(full_path)


def validate_waveguide_package_archive_digest_attestation_scope(scope: str) -> bool:
    return scope == "controlled_local_archive_attestation_scope"


def validate_waveguide_package_archive_digest_attestation_boolean_matrix(
    stmt_dict: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    errors = []
    # Real signature/signing-key/credentials/external operations must be false/absent
    prohibitions = [
        "real_signature_claimed",
        "real_key_signing_used",
        "external_signing_used",
        "timestamp_authority_used",
        "private_key_material_loaded",
        "credentials_loaded",
        "network_access_used",
        "upload_performed",
        "deployment_performed",
        "external_publication_performed",
        "production_mutation_performed",
    ]
    for key in prohibitions:
        if stmt_dict.get(key) is not False:
            errors.append(f"Statement {key} must be False")
    return len(errors) == 0, errors


def validate_waveguide_package_archive_digest_attestation_source_chain(
    gate_digest: str,
    stmt_dict: Dict[str, Any]
) -> bool:
    return stmt_dict.get("source_package_archive_signing_gate_digest") == gate_digest


def index_waveguide_package_archive_digest_attestation_statements_by_status(
    statements: List[WaveguidePackageArchiveDigestAttestationStatement]
) -> Dict[str, List[str]]:
    indexed = {
        "ready": [],
        "blocked": [],
        "warning": [],
        "invalid": []
    }
    for s in statements:
        status = s.archive_digest_attestation_statement_status
        if status == "archive_digest_attestation_statement_ready":
            indexed["ready"].append(s.archive_digest_attestation_statement_id)
        elif status == "archive_digest_attestation_statement_blocked":
            indexed["blocked"].append(s.archive_digest_attestation_statement_id)
        elif status == "archive_digest_attestation_statement_warning":
            indexed["warning"].append(s.archive_digest_attestation_statement_id)
        else:
            indexed["invalid"].append(s.archive_digest_attestation_statement_id)
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


def build_waveguide_package_archive_digest_attestation_statement(
    gate_dict: Dict[str, Any],
    index: int,
    archive_filepath: str,
    archive_override_digest: Optional[str] = None
) -> WaveguidePackageArchiveDigestAttestationStatement:
    """
    Builds a single digest attestation statement.
    """
    recorded_digest = gate_dict.get("current_archive_candidate_digest", "")
    
    # Recompute digest from actual file, unless overridden for test/sandboxing
    if archive_override_digest is not None:
        recomputed_digest = archive_override_digest
    else:
        recomputed_digest = recompute_waveguide_package_archive_digest_for_attestation(archive_filepath)

    digest_match = (recorded_digest == recomputed_digest) and (recorded_digest != "")

    status = "archive_digest_attestation_statement_ready"
    reason_codes = ["ATTESTATION_STATEMENT_READY"]

    if not digest_match:
        status = "archive_digest_attestation_statement_invalid"
        reason_codes = ["ARCHIVE_DIGEST_MISMATCH"]

    statement_text = (
        f"SOL Waveguide Local Digest Attestation Statement - Binds archive file digest {recomputed_digest} "
        f"to signing gate {gate_dict.get('package_archive_signing_gate_digest')} under local attestation rules."
    )

    statement = WaveguidePackageArchiveDigestAttestationStatement(
        archive_digest_attestation_statement_id=f"SOL-WAVEGUIDE-ATTESTATION-STATEMENT-{index:03d}",
        archive_digest_attestation_statement_status=status,
        archive_candidate_digest=recorded_digest,
        archive_candidate_kind="local_verified_zip_archive_candidate",
        archive_format=gate_dict.get("current_archive_candidate_format", ""),
        archive_filename=gate_dict.get("archive_filename", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip"),
        archive_display_path=gate_dict.get("current_archive_candidate_display_path", ""),
        archive_file_digest_recorded=recorded_digest,
        archive_file_digest_recomputed=recomputed_digest,
        archive_file_digest_match=digest_match,
        archive_file_size_bytes=gate_dict.get("current_archive_candidate_size_bytes", 0),
        source_package_archive_signing_gate_digest=gate_dict.get("package_archive_signing_gate_digest", ""),
        source_package_archive_signing_plan_digest=gate_dict.get("source_package_archive_signing_plan_digest", ""),
        source_package_archive_release_candidate_index_digest=gate_dict.get("source_package_archive_release_candidate_index_digest", ""),
        source_package_archive_audit_report_digest=gate_dict.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=gate_dict.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=gate_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=gate_dict.get("source_package_archive_plan_digest", ""),
        attestation_kind="local_digest_attestation",
        attestation_algorithm="sha256_digest_binding_statement",
        attestation_hash_algorithm="sha256",
        attestation_statement_text=statement_text,
        attestation_scope="controlled_local_archive_attestation_scope",
        real_signature_claimed=False,
        real_key_signing_used=False,
        external_signing_used=False,
        timestamp_authority_used=False,
        private_key_material_loaded=False,
        credentials_loaded=False,
        network_access_used=False,
        upload_performed=False,
        deployment_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    statement.archive_digest_attestation_statement_digest = hash_waveguide_package_archive_digest_attestation_statement(statement)
    return statement


def validate_waveguide_package_archive_digest_attestation_statement(
    statement: Any
) -> Tuple[bool, List[str]]:
    """
    Independently validates a single attestation statement.
    """
    s_dict = asdict(statement) if hasattr(statement, "__dict__") else dict(statement)
    errors = []

    # Verify digest
    recorded = s_dict.get("archive_digest_attestation_statement_digest", "")
    if not recorded:
        errors.append("Missing statement digest")
    else:
        recomputed = hash_waveguide_package_archive_digest_attestation_statement(s_dict)
        if recomputed != recorded:
            errors.append(f"Statement digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    # Validate boolean matrix
    ok_matrix, matrix_errs = validate_waveguide_package_archive_digest_attestation_boolean_matrix(s_dict)
    if not ok_matrix:
        errors.extend(matrix_errs)

    # Validate digest match
    if not s_dict.get("archive_file_digest_match"):
        errors.append("Archive file digest match must be True")

    # Validate scope
    scope = s_dict.get("attestation_scope", "")
    if not validate_waveguide_package_archive_digest_attestation_scope(scope):
        errors.append("Invalid attestation scope")

    return len(errors) == 0, errors


def build_waveguide_package_archive_digest_attestation(
    gate_path_or_dict: Any,
    archive_filepath_override: Optional[str] = None,
    archive_override_digest: Optional[str] = None
) -> WaveguidePackageArchiveDigestAttestation:
    """
    Builds the top-level Package Archive Digest Attestation.
    """
    gate_dict = _load_dict(gate_path_or_dict) or {}
    gate_digest = gate_dict.get("package_archive_signing_gate_digest", "")
    gate_status = gate_dict.get("package_archive_signing_gate_status", "")

    status = "package_archive_digest_attested"
    reason_codes = ["PACKAGE_ARCHIVE_DIGEST_ATTESTED"]

    valid_gate, gate_errs = validate_waveguide_package_archive_signing_gate(gate_dict)
    if not valid_gate or gate_status != "package_archive_signing_gate_ready":
        status = "package_archive_digest_attestation_blocked"
        reason_codes = ["SIGNING_GATE_NOT_READY"]

    # Enforce performed flag checks (prohibitions)
    signing_performed = gate_dict.get("signing_performed", False)
    upload_performed = gate_dict.get("upload_performed", False)
    publication_performed = gate_dict.get("external_publication_performed", False)
    deployment_performed = gate_dict.get("deployment_performed", False)
    production_mutation_performed = gate_dict.get("production_mutation_performed", False)

    if signing_performed or upload_performed or publication_performed or deployment_performed or production_mutation_performed:
        status = "package_archive_digest_attestation_invalid"
        reason_codes.append("SIGNING_GATE_MUTATION_VIOLATION")

    archive_filepath = archive_filepath_override or gate_dict.get("current_archive_candidate_display_path", "")
    if not archive_filepath:
        archive_filepath = "docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip"
    
    statements = []
    # Currently we assume 1 candidate entry, as defined in our index and gate
    if status != "package_archive_digest_attestation_invalid" and status != "package_archive_digest_attestation_blocked":
        stmt = build_waveguide_package_archive_digest_attestation_statement(
            gate_dict, 0, archive_filepath, archive_override_digest=archive_override_digest
        )
        statements.append(stmt)

    indexed = index_waveguide_package_archive_digest_attestation_statements_by_status(statements)
    
    ready_ids = indexed["ready"]
    blocked_ids = indexed["blocked"]
    warning_ids = indexed["warning"]
    invalid_ids = indexed["invalid"]

    if len(invalid_ids) > 0 or len(blocked_ids) > 0:
        status = "package_archive_digest_attestation_invalid"
        reason_codes.append("ATTESTATION_STATEMENTS_INVALID_OR_BLOCKED")

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

    # Extract info from first statement if available
    stmt_dict = asdict(statements[0]) if len(statements) > 0 else {}

    att = WaveguidePackageArchiveDigestAttestation(
        package_archive_digest_attestation_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-DIGEST-ATTESTATION",
        package_archive_digest_attestation_version=1,
        package_archive_digest_attestation_status=status,
        source_package_archive_signing_gate_digest=gate_digest,
        source_package_archive_signing_plan_digest=gate_dict.get("source_package_archive_signing_plan_digest", ""),
        source_package_archive_release_candidate_index_digest=gate_dict.get("source_package_archive_release_candidate_index_digest", ""),
        source_package_archive_audit_report_digest=gate_dict.get("source_package_archive_audit_report_digest", ""),
        source_package_archive_manifest_digest=gate_dict.get("source_package_archive_manifest_digest", ""),
        source_package_archive_build_record_digest=gate_dict.get("source_package_archive_build_record_digest", ""),
        source_package_archive_plan_digest=gate_dict.get("source_package_archive_plan_digest", ""),
        archive_digest_attestation_statements=statements,
        ready_archive_digest_attestation_statements=ready_ids,
        blocked_archive_digest_attestation_statements=blocked_ids,
        warning_archive_digest_attestation_statements=warning_ids,
        invalid_archive_digest_attestation_statements=invalid_ids,
        ready_archive_digest_attestation_statement_count=len(ready_ids),
        blocked_archive_digest_attestation_statement_count=len(blocked_ids),
        warning_archive_digest_attestation_statement_count=len(warning_ids),
        invalid_archive_digest_attestation_statement_count=len(invalid_ids),
        archive_candidate_digest=gate_dict.get("current_archive_candidate_digest", ""),
        archive_candidate_kind="local_verified_zip_archive_candidate",
        archive_format=gate_dict.get("current_archive_candidate_format", ""),
        archive_filename=gate_dict.get("archive_filename", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip"),
        archive_display_path=gate_dict.get("current_archive_candidate_display_path", ""),
        archive_file_digest_recorded=gate_dict.get("current_archive_candidate_digest", ""),
        archive_file_digest_recomputed=stmt_dict.get("archive_file_digest_recomputed", ""),
        archive_file_digest_match=stmt_dict.get("archive_file_digest_match", False),
        archive_file_size_bytes=gate_dict.get("current_archive_candidate_size_bytes", 0),
        attestation_kind="local_digest_attestation",
        attestation_algorithm="sha256_digest_binding_statement",
        attestation_hash_algorithm="sha256",
        real_signature_status="not_performed",
        digest_attestation_status="verified" if status == "package_archive_digest_attested" else "failed",
        signing_status="not_performed",
        upload_status="not_performed",
        publication_status="not_performed",
        deployment_status="not_performed",
        production_mutation_status="not_performed",
        real_signature_claimed=False,
        real_key_signing_used=False,
        external_signing_used=False,
        timestamp_authority_used=False,
        private_key_material_loaded=False,
        credentials_loaded=False,
        network_access_used=False,
        signing_performed=False,
        real_key_signature_performed=False,
        digest_attestation_performed=(status == "package_archive_digest_attested"),
        external_signing_performed=False,
        timestamp_authority_performed=False,
        upload_performed=False,
        deployment_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    att.package_archive_digest_attestation_digest = hash_waveguide_package_archive_digest_attestation(att)
    return att


def validate_waveguide_package_archive_digest_attestation(
    attestation: Any
) -> Tuple[bool, List[str]]:
    """
    Independently validates a top-level Package Archive Digest Attestation.
    """
    a_dict = asdict(attestation) if hasattr(attestation, "__dict__") else dict(attestation)
    errors = []

    # Verify digest
    recorded = a_dict.get("package_archive_digest_attestation_digest", "")
    if not recorded:
        errors.append("Missing attestation digest")
    else:
        recomputed = hash_waveguide_package_archive_digest_attestation(a_dict)
        if recomputed != recorded:
            errors.append(f"Attestation digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if a_dict.get("package_archive_digest_attestation_id") != "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-DIGEST-ATTESTATION":
        errors.append("Invalid attestation ID")

    # Enforce prohibitions
    prohibitions = [
        ("real_signature_claimed", False),
        ("real_key_signing_used", False),
        ("external_signing_used", False),
        ("timestamp_authority_used", False),
        ("private_key_material_loaded", False),
        ("credentials_loaded", False),
        ("network_access_used", False),
        ("signing_performed", False),
        ("real_key_signature_performed", False),
        ("external_signing_performed", False),
        ("timestamp_authority_performed", False),
        ("upload_performed", False),
        ("deployment_performed", False),
        ("external_publication_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if a_dict.get(key) is not expected:
            errors.append(f"Top-level {key} must be {expected}")

    # Validate statements
    statements = a_dict.get("archive_digest_attestation_statements", [])
    for s in statements:
        ok, errs = validate_waveguide_package_archive_digest_attestation_statement(s)
        if not ok:
            errors.extend(errs)

    return len(errors) == 0, errors


def summarize_waveguide_package_archive_digest_attestation(attestation: Any) -> str:
    """
    Generates a human-readable summary of the Digest Attestation.
    """
    a_dict = asdict(attestation) if hasattr(attestation, "__dict__") else dict(attestation)
    lines = [
        "=============================================================",
        "            SOL WAVEGUIDE PACKAGE DIGEST ATTESTATION",
        "=============================================================",
        f"Attestation ID:   {a_dict.get('package_archive_digest_attestation_id')}",
        f"Status:           {a_dict.get('package_archive_digest_attestation_status')}",
        f"Attest Digest:    {a_dict.get('package_archive_digest_attestation_digest')}",
        f"Candidate Digest: {a_dict.get('archive_candidate_digest')}",
        f"File Digest Match: {a_dict.get('archive_file_digest_match')}",
        f"Attest Performed: {a_dict.get('digest_attestation_performed')}",
        f"Real Sign Claim:  {a_dict.get('real_signature_claimed')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in a_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_archive_digest_attestation(attestation: Any, output_path: str) -> None:
    """
    Exports the Digest Attestation to a JSON file.
    """
    a_dict = asdict(attestation) if hasattr(attestation, "__dict__") else dict(attestation)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(a_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_archive_digest_attestations(att_a: Any, att_b: Any) -> Dict[str, Any]:
    """
    Compares two Digest Attestations.
    """
    dict_a = asdict(att_a) if hasattr(att_a, "__dict__") else dict(att_a)
    dict_b = asdict(att_b) if hasattr(att_b, "__dict__") else dict(att_b)

    differences = {}
    for key in (
        "package_archive_digest_attestation_status",
        "archive_file_digest_match",
        "package_archive_digest_attestation_digest"
    ):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
