# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Release Certification Validator / Independent Audit Verifier.
Reloads a certification bundle, recomputes its digest, reloads all nested
artifact references, validates every governance component, compares recorded
digests, and produces a separate deterministic external-style audit report.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide governance modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT,
    hash_file_contents,
    validate_waveguide_rc_promotion_record
)
from sol_waveguide_rc_manifest import (
    validate_waveguide_rc_manifest_consistency
)
from sol_waveguide_rc_release_gate import (
    validate_waveguide_rc_boundary
)
from sol_waveguide_rc_promotion_court import (
    hash_waveguide_rc_court_verdict
)
from sol_waveguide_rc_release_registry import (
    validate_waveguide_rc_release_registry
)
from sol_waveguide_runtime_capability_resolver import (
    validate_waveguide_runtime_capability_resolution
)
from sol_waveguide_governed_compiler_session_registry import (
    validate_waveguide_governed_compiler_session_registry
)
from sol_waveguide_release_certification_bundle import (
    validate_waveguide_release_certification_bundle,
    summarize_waveguide_release_certification_bundle,
    compare_waveguide_release_certification_bundles,
    hash_waveguide_release_certification_bundle,
    get_default_artifact_paths
)


@dataclass
class WaveguideReleaseCertificationAuditCase:
    audit_case_id: str
    certification_bundle_id: str
    certification_bundle_path: str
    certification_bundle_digest_recorded: str
    certification_bundle_digest_recomputed: str
    certification_bundle_digest_match: bool
    certification_bundle_status: str
    rc_id: str
    candidate_level: str
    manifest_digest_recorded: str
    manifest_digest_recomputed: str
    release_gate_digest_recorded: str
    release_gate_digest_recomputed: str
    promotion_record_digest_recorded: str
    promotion_record_digest_recomputed: str
    promotion_court_verdict_digest_recorded: str
    promotion_court_verdict_digest_recomputed: str
    release_registry_digest_recorded: str
    release_registry_digest_recomputed: str
    runtime_capability_resolution_digest_recorded: str
    runtime_capability_resolution_digest_recomputed: str
    compiler_session_registry_digest_recorded: str
    compiler_session_registry_digest_recomputed: str
    artifact_digest_mismatches: List[str]
    artifact_validation_failures: List[str]
    rc_approved_in_registry: bool
    nested_rc_id_consistent: bool
    session_registry_status: str
    registered_session_count: int
    registered_rejection_session_count: int
    blocked_session_count: int
    invalid_session_count: int
    compiler_profiles_indexed: List[str]
    pass_sequences_indexed: List[List[str]]
    handler_ids_indexed: List[str]
    final_output_payload_digests: List[str]
    audit_status: str
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    audit_case_digest: str = ""


@dataclass
class WaveguideReleaseCertificationAuditReport:
    audit_report_id: str
    audit_report_version: int
    audit_report_status: str
    audited_bundles: List[str]
    verified_audits: List[str]
    failed_audits: List[str]
    blocked_audits: List[str]
    verified_audit_count: int
    failed_audit_count: int
    blocked_audit_count: int
    rc1_audit_count: int
    rc2_audit_count: int
    certification_bundle_digests: List[str]
    manifest_digests: List[str]
    release_gate_digests: List[str]
    promotion_record_digests: List[str]
    promotion_court_verdict_digests: List[str]
    release_registry_digests: List[str]
    runtime_capability_resolution_digests: List[str]
    compiler_session_registry_digests: List[str]
    artifact_digest_mismatch_count: int
    artifact_validation_failure_count: int
    reason_codes: List[str]
    software_validation_caveat: str
    audit_report_digest: str = ""


def hash_waveguide_release_certification_audit_case(case: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation,
    excluding the self-referential audit_case_digest field.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    elif isinstance(case, dict):
        c_dict = dict(case)
    else:
        raise TypeError("case must be a dictionary or a dataclass instance")

    c_dict_copy = dict(c_dict)
    c_dict_copy.pop("audit_case_digest", None)
    return hash_data(c_dict_copy)


def hash_waveguide_release_certification_audit_report(report: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation,
    excluding the self-referential audit_report_digest field.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    r_dict_copy = dict(r_dict)
    r_dict_copy.pop("audit_report_digest", None)
    return hash_data(r_dict_copy)


def recompute_waveguide_release_certification_artifact_digest(path: str) -> str:
    """
    Recomputes artifact digest by hashing its file contents.
    """
    if not path:
        return ""
    norm_path = normalize_to_repo_path(path)
    full_path = os.path.join(REPO_ROOT, norm_path)
    if not os.path.exists(full_path):
        return ""
    try:
        return hash_file_contents(full_path)
    except Exception:
        return ""


def validate_waveguide_release_certification_artifact_digests(bundle: Any) -> Tuple[bool, List[str], Dict[str, str]]:
    """
    Recomputes and validates all digests in the bundle.
    Returns (all_match, mismatch_paths, recomputed_digests).
    """
    if hasattr(bundle, "__dict__"):
        b_dict = asdict(bundle)
    elif isinstance(bundle, dict):
        b_dict = dict(bundle)
    else:
        raise TypeError("bundle must be a dictionary or a dataclass instance")

    paths = b_dict.get("artifact_paths", [])
    recorded_digests = b_dict.get("artifact_digests", {})

    all_match = True
    mismatch_paths = []
    recomputed_digests = {}

    for path in paths:
        recomp = recompute_waveguide_release_certification_artifact_digest(path)
        recomputed_digests[path] = recomp

        recorded = recorded_digests.get(path, "")

        # Check both recorded in dict and the corresponding field
        p_lower = path.lower()
        field_recorded = ""
        if "manifest" in p_lower:
            field_recorded = b_dict.get("manifest_digest", "")
        elif "delta_audit" in p_lower:
            field_recorded = b_dict.get("release_gate_digest", "")
        elif "promotion_record" in p_lower:
            field_recorded = b_dict.get("promotion_record_digest", "")
        elif "court_verdict" in p_lower:
            field_recorded = b_dict.get("promotion_court_verdict_digest", "")
        elif "release_registry" in p_lower:
            field_recorded = b_dict.get("release_registry_digest", "")
        elif "capability_resolver" in p_lower or "capability_resolution" in p_lower:
            field_recorded = b_dict.get("runtime_capability_resolution_digest", "")
        elif "session_registry" in p_lower:
            field_recorded = b_dict.get("compiler_session_registry_digest", "")

        if not recomp or recomp != recorded or recomp != field_recorded:
            all_match = False
            mismatch_paths.append(path)

    return all_match, sorted(mismatch_paths), recomputed_digests


def load_waveguide_release_certification_artifact_chain(bundle: Any) -> Dict[str, Any]:
    """
    Loads all artifact files referenced in the bundle and returns them in a dict.
    """
    if hasattr(bundle, "__dict__"):
        b_dict = asdict(bundle)
    elif isinstance(bundle, dict):
        b_dict = dict(bundle)
    else:
        raise TypeError("bundle must be a dictionary or a dataclass instance")

    paths = b_dict.get("artifact_paths", [])

    chain = {}
    for path in paths:
        p_lower = path.lower()
        full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(path))
        data = None
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        if "manifest" in p_lower:
            chain["manifest"] = data
        elif "delta_audit" in p_lower:
            chain["release_gate"] = data
        elif "promotion_record" in p_lower:
            chain["promotion_record"] = data
        elif "court_verdict" in p_lower:
            chain["court_verdict"] = data
        elif "release_registry" in p_lower:
            chain["release_registry"] = data
        elif "capability_resolver" in p_lower or "capability_resolution" in p_lower:
            chain["capability_resolution"] = data
        elif "session_registry" in p_lower:
            chain["session_registry"] = data

    return chain


def build_waveguide_release_certification_audit_case(bundle_path_or_dict: Any) -> WaveguideReleaseCertificationAuditCase:
    """
    Builds a deterministic Release Certification Audit Case for a given bundle.
    """
    bundle_path = ""
    bundle_dict = None
    load_failed = False
    missing_bundle = False

    # 1. Load/Resolve Bundle
    if isinstance(bundle_path_or_dict, str):
        bundle_path = normalize_to_repo_path(bundle_path_or_dict)
        full_path = os.path.join(REPO_ROOT, bundle_path)
        if not os.path.exists(full_path):
            missing_bundle = True
            load_failed = True
        else:
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    bundle_dict = json.load(f)
            except Exception:
                load_failed = True
    elif hasattr(bundle_path_or_dict, "__dict__"):
        bundle_dict = asdict(bundle_path_or_dict)
    elif isinstance(bundle_path_or_dict, dict):
        bundle_dict = dict(bundle_path_or_dict)
    else:
        load_failed = True

    reason_codes = ["RELEASE_AUDIT_CASE_CANONICAL"]
    notes = []
    artifact_digest_mismatches = []
    artifact_validation_failures = []

    # Defaults in case of loading failure
    certification_bundle_id = ""
    certification_bundle_digest_recorded = ""
    certification_bundle_digest_recomputed = ""
    certification_bundle_digest_match = False
    certification_bundle_status = ""
    rc_id = ""
    candidate_level = ""

    manifest_digest_recorded = ""
    manifest_digest_recomputed = ""
    release_gate_digest_recorded = ""
    release_gate_digest_recomputed = ""
    promotion_record_digest_recorded = ""
    promotion_record_digest_recomputed = ""
    promotion_court_verdict_digest_recorded = ""
    promotion_court_verdict_digest_recomputed = ""
    release_registry_digest_recorded = ""
    release_registry_digest_recomputed = ""
    runtime_capability_resolution_digest_recorded = ""
    runtime_capability_resolution_digest_recomputed = ""
    compiler_session_registry_digest_recorded = ""
    compiler_session_registry_digest_recomputed = ""

    rc_approved_in_registry = False
    nested_rc_id_consistent = True
    session_registry_status = ""
    registered_session_count = 0
    registered_rejection_session_count = 0
    blocked_session_count = 0
    invalid_session_count = 0
    compiler_profiles_indexed = []
    pass_sequences_indexed = []
    handler_ids_indexed = []
    final_output_payload_digests = []
    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if load_failed:
        reason_codes.append("RELEASE_AUDIT_BUNDLE_INVALID")
        reason_codes.append("RELEASE_AUDIT_FAILED")
        if missing_bundle:
            notes.append(f"Bundle file is missing: {bundle_path}")
            audit_status = "audit_blocked"
            reason_codes.append("RELEASE_AUDIT_BLOCKED")
        else:
            notes.append("Failed to load or parse bundle.")
            audit_status = "audit_failed"

        case = WaveguideReleaseCertificationAuditCase(
            audit_case_id=f"SOL-WAVEGUIDE-RELEASE-CERTIFICATION-AUDIT-CASE-{rc_id or 'UNKNOWN'}",
            certification_bundle_id=certification_bundle_id,
            certification_bundle_path=bundle_path,
            certification_bundle_digest_recorded=certification_bundle_digest_recorded,
            certification_bundle_digest_recomputed=certification_bundle_digest_recomputed,
            certification_bundle_digest_match=certification_bundle_digest_match,
            certification_bundle_status=certification_bundle_status,
            rc_id=rc_id,
            candidate_level=candidate_level,
            manifest_digest_recorded=manifest_digest_recorded,
            manifest_digest_recomputed=manifest_digest_recomputed,
            release_gate_digest_recorded=release_gate_digest_recorded,
            release_gate_digest_recomputed=release_gate_digest_recomputed,
            promotion_record_digest_recorded=promotion_record_digest_recorded,
            promotion_record_digest_recomputed=promotion_record_digest_recomputed,
            promotion_court_verdict_digest_recorded=promotion_court_verdict_digest_recorded,
            promotion_court_verdict_digest_recomputed=promotion_court_verdict_digest_recomputed,
            release_registry_digest_recorded=release_registry_digest_recorded,
            release_registry_digest_recomputed=release_registry_digest_recomputed,
            runtime_capability_resolution_digest_recorded=runtime_capability_resolution_digest_recorded,
            runtime_capability_resolution_digest_recomputed=runtime_capability_resolution_digest_recomputed,
            compiler_session_registry_digest_recorded=compiler_session_registry_digest_recorded,
            compiler_session_registry_digest_recomputed=compiler_session_registry_digest_recomputed,
            artifact_digest_mismatches=artifact_digest_mismatches,
            artifact_validation_failures=artifact_validation_failures,
            rc_approved_in_registry=rc_approved_in_registry,
            nested_rc_id_consistent=nested_rc_id_consistent,
            session_registry_status=session_registry_status,
            registered_session_count=registered_session_count,
            registered_rejection_session_count=registered_rejection_session_count,
            blocked_session_count=blocked_session_count,
            invalid_session_count=invalid_session_count,
            compiler_profiles_indexed=compiler_profiles_indexed,
            pass_sequences_indexed=pass_sequences_indexed,
            handler_ids_indexed=handler_ids_indexed,
            final_output_payload_digests=final_output_payload_digests,
            audit_status=audit_status,
            reason_codes=sorted(list(set(reason_codes))),
            notes=notes,
            software_validation_caveat=software_validation_caveat,
            audit_case_digest=""
        )
        case.audit_case_digest = hash_waveguide_release_certification_audit_case(case)
        return case

    reason_codes.append("RELEASE_AUDIT_BUNDLE_LOADED")

    # 2. Extract basic info
    certification_bundle_id = bundle_dict.get("certification_bundle_id", "")
    certification_bundle_digest_recorded = bundle_dict.get("certification_bundle_digest", "")
    certification_bundle_status = bundle_dict.get("certification_status", "")
    rc_id = bundle_dict.get("rc_id", "")
    candidate_level = bundle_dict.get("candidate_level", "")

    # 3. Recompute and validate bundle digest
    certification_bundle_digest_recomputed = hash_waveguide_release_certification_bundle(bundle_dict)
    if certification_bundle_digest_recomputed == certification_bundle_digest_recorded:
        certification_bundle_digest_match = True
        reason_codes.append("RELEASE_AUDIT_BUNDLE_DIGEST_MATCH")
    else:
        certification_bundle_digest_match = False
        reason_codes.append("RELEASE_AUDIT_BUNDLE_DIGEST_MISMATCH")
        notes.append("Bundle digest mismatch.")

    # Check bundle status
    if certification_bundle_status == "certification_ready":
        reason_codes.append("RELEASE_AUDIT_BUNDLE_CERTIFICATION_READY")
    else:
        notes.append(f"Bundle status is not certification_ready: {certification_bundle_status}")

    # Call existing bundle validator
    ok_bundle, _ = validate_waveguide_release_certification_bundle(bundle_dict)
    if ok_bundle:
        reason_codes.append("RELEASE_AUDIT_BUNDLE_VALID")
    else:
        reason_codes.append("RELEASE_AUDIT_BUNDLE_INVALID")
        notes.append("Existing bundle validator failed.")

    # 4. Check caveat
    caveat = bundle_dict.get("software_validation_caveat", "")
    if caveat and "sandbox" in caveat.lower():
        reason_codes.append("RELEASE_AUDIT_SOFTWARE_CAVEAT_INCLUDED")
    else:
        artifact_validation_failures.append("Software validation caveat is missing or invalid.")

    # 5. Reload artifact paths referenced by bundle and recompute digests
    artifact_paths = bundle_dict.get("artifact_paths", [])
    artifact_digests = bundle_dict.get("artifact_digests", {})

    # Load chain
    chain = load_waveguide_release_certification_artifact_chain(bundle_dict)

    # Check if all 7 required components are loaded
    expected_components = ["manifest", "release_gate", "promotion_record", "court_verdict", "release_registry", "capability_resolution", "session_registry"]
    if all(chain.get(k) is not None for k in expected_components):
        reason_codes.append("RELEASE_AUDIT_ARTIFACT_CHAIN_LOADED")
    else:
        notes.append("Some artifacts in the chain failed to load.")

    # Digests validation
    all_dig_match, mismatch_paths, recomp_digests = validate_waveguide_release_certification_artifact_digests(bundle_dict)
    artifact_digest_mismatches = mismatch_paths
    if all_dig_match:
        reason_codes.append("RELEASE_AUDIT_ARTIFACT_DIGESTS_MATCH")
    else:
        reason_codes.append("RELEASE_AUDIT_ARTIFACT_DIGEST_MISMATCH")
        for path in mismatch_paths:
            notes.append(f"Artifact digest mismatch: {path}")

    # Assign the recomputed / recorded digests for separate fields
    manifest_digest_recorded = bundle_dict.get("manifest_digest", "")
    release_gate_digest_recorded = bundle_dict.get("release_gate_digest", "")
    promotion_record_digest_recorded = bundle_dict.get("promotion_record_digest", "")
    promotion_court_verdict_digest_recorded = bundle_dict.get("promotion_court_verdict_digest", "")
    release_registry_digest_recorded = bundle_dict.get("release_registry_digest", "")
    runtime_capability_resolution_digest_recorded = bundle_dict.get("runtime_capability_resolution_digest", "")
    compiler_session_registry_digest_recorded = bundle_dict.get("compiler_session_registry_digest", "")

    # Map them to recomputed ones
    for path in artifact_paths:
        p_lower = path.lower()
        recomp = recomp_digests.get(path, "")
        if "manifest" in p_lower:
            manifest_digest_recomputed = recomp
        elif "delta_audit" in p_lower:
            release_gate_digest_recomputed = recomp
        elif "promotion_record" in p_lower:
            promotion_record_digest_recomputed = recomp
        elif "court_verdict" in p_lower:
            promotion_court_verdict_digest_recomputed = recomp
        elif "release_registry" in p_lower:
            release_registry_digest_recomputed = recomp
        elif "capability_resolver" in p_lower or "capability_resolution" in p_lower:
            runtime_capability_resolution_digest_recomputed = recomp
        elif "session_registry" in p_lower:
            compiler_session_registry_digest_recomputed = recomp

    # 6. Validate the components via their validators

    # Manifest
    manifest = chain.get("manifest")
    if manifest is None:
        artifact_validation_failures.append("Manifest artifact missing.")
    else:
        try:
            if validate_waveguide_rc_manifest_consistency(manifest):
                reason_codes.append("RELEASE_AUDIT_MANIFEST_VALID")
            else:
                artifact_validation_failures.append("Manifest validation failed.")
        except Exception as e:
            artifact_validation_failures.append(f"Manifest validator threw exception: {str(e)}")

        if manifest.get("rc_id") != rc_id:
            nested_rc_id_consistent = False
            artifact_validation_failures.append("Manifest rc_id mismatch.")

    # Release Gate
    release_gate = chain.get("release_gate")
    if release_gate is None:
        artifact_validation_failures.append("Release gate artifact missing.")
    else:
        if release_gate.get("boundary_valid") is True:
            reason_codes.append("RELEASE_AUDIT_RELEASE_GATE_VALID")
        else:
            artifact_validation_failures.append("Release gate boundary validation failed.")

    # Promotion Record
    promotion_record = chain.get("promotion_record")
    if promotion_record is None:
        artifact_validation_failures.append("Promotion record artifact missing.")
    else:
        try:
            ok, _ = validate_waveguide_rc_promotion_record(promotion_record)
            if ok and promotion_record.get("promotion_status") == "promotion_ready":
                reason_codes.append("RELEASE_AUDIT_PROMOTION_RECORD_VALID")
            else:
                artifact_validation_failures.append("Promotion record validation failed or not ready.")
        except Exception as e:
            artifact_validation_failures.append(f"Promotion record validator threw exception: {str(e)}")

        if promotion_record.get("rc_id") != rc_id:
            nested_rc_id_consistent = False
            artifact_validation_failures.append("Promotion record rc_id mismatch.")

    # Court Verdict
    court_verdict = chain.get("court_verdict")
    if court_verdict is None:
        artifact_validation_failures.append("Court verdict artifact missing.")
    else:
        try:
            comp_hash = hash_waveguide_rc_court_verdict(court_verdict)
            if comp_hash != court_verdict.get("verdict_digest"):
                artifact_validation_failures.append("Court verdict internal digest validation failed.")
            elif court_verdict.get("court_verdict") != "promotion_approved":
                artifact_validation_failures.append("Court verdict status is not promotion_approved.")
            else:
                reason_codes.append("RELEASE_AUDIT_COURT_VERDICT_APPROVED")
        except Exception as e:
            artifact_validation_failures.append(f"Court verdict validation threw exception: {str(e)}")

        if court_verdict.get("rc_id") != rc_id:
            nested_rc_id_consistent = False
            artifact_validation_failures.append("Court verdict rc_id mismatch.")

    # Release Registry
    release_registry = chain.get("release_registry")
    if release_registry is None:
        artifact_validation_failures.append("Release registry artifact missing.")
    else:
        try:
            ok, _ = validate_waveguide_rc_release_registry(release_registry)
            if ok:
                reason_codes.append("RELEASE_AUDIT_RELEASE_REGISTRY_VALID")
            else:
                artifact_validation_failures.append("Release registry validation failed.")
        except Exception as e:
            artifact_validation_failures.append(f"Release registry validator threw exception: {str(e)}")

        if rc_id in release_registry.get("approved_rc_ids", []):
            rc_approved_in_registry = True
            reason_codes.append("RELEASE_AUDIT_RC_APPROVED_IN_REGISTRY")
        else:
            rc_approved_in_registry = False
            artifact_validation_failures.append("Target RC not approved in release registry.")

    # Capability Resolution
    capability_resolution = chain.get("capability_resolution")
    if capability_resolution is None:
        artifact_validation_failures.append("Capability resolution artifact missing.")
    else:
        try:
            ok, _ = validate_waveguide_runtime_capability_resolution(capability_resolution)
            if ok:
                reason_codes.append("RELEASE_AUDIT_RUNTIME_CAPABILITY_VALID")
            else:
                artifact_validation_failures.append("Runtime capability resolution validation failed.")
        except Exception as e:
            artifact_validation_failures.append(f"Runtime capability validator threw exception: {str(e)}")

        if capability_resolution.get("rc_id") != rc_id:
            nested_rc_id_consistent = False
            artifact_validation_failures.append("Capability resolution rc_id mismatch.")

    # Session Registry
    session_registry = chain.get("session_registry")
    if session_registry is None:
        artifact_validation_failures.append("Session registry artifact missing.")
    else:
        try:
            ok, _ = validate_waveguide_governed_compiler_session_registry(session_registry)
            if ok:
                reason_codes.append("RELEASE_AUDIT_SESSION_REGISTRY_VALID")
            else:
                artifact_validation_failures.append("Session registry validation failed.")
        except Exception as e:
            artifact_validation_failures.append(f"Session registry validator threw exception: {str(e)}")

        session_registry_status = session_registry.get("registry_status", "")

        # Extract fields
        registered_session_count = session_registry.get("registered_session_count", 0)
        registered_rejection_session_count = session_registry.get("registered_rejection_session_count", 0)
        blocked_session_count = session_registry.get("blocked_session_count", 0)
        invalid_session_count = session_registry.get("invalid_session_count", 0)
        compiler_profiles_indexed = session_registry.get("compiler_profiles_indexed", [])
        pass_sequences_indexed = session_registry.get("pass_sequences_indexed", [])
        handler_ids_indexed = session_registry.get("handler_ids_indexed", [])
        final_output_payload_digests = session_registry.get("final_output_payload_digests", [])

        # Compare counts and lists with bundle
        counts_match = (
            registered_session_count == bundle_dict.get("registered_session_count") and
            registered_rejection_session_count == bundle_dict.get("registered_rejection_session_count") and
            blocked_session_count == bundle_dict.get("blocked_session_count") and
            invalid_session_count == bundle_dict.get("invalid_session_count") and
            session_registry.get("rc1_session_count") == bundle_dict.get("rc1_session_count") and
            session_registry.get("rc2_session_count") == bundle_dict.get("rc2_session_count")
        )
        if counts_match:
            reason_codes.append("RELEASE_AUDIT_SESSION_COUNTS_MATCH")
        else:
            artifact_validation_failures.append("Session registry counts mismatch.")

        lists_match = (
            compiler_profiles_indexed == bundle_dict.get("compiler_profiles_indexed") and
            pass_sequences_indexed == bundle_dict.get("pass_sequences_indexed") and
            handler_ids_indexed == bundle_dict.get("handler_ids_indexed") and
            final_output_payload_digests == bundle_dict.get("final_output_payload_digests")
        )
        if lists_match:
            reason_codes.append("RELEASE_AUDIT_INDEXES_MATCH")
        else:
            artifact_validation_failures.append("Session registry indexed lists mismatch.")

    # 7. Decide final audit status
    has_missing_files = False
    for path in artifact_paths:
        full_p = os.path.join(REPO_ROOT, path)
        if not os.path.exists(full_p):
            has_missing_files = True

    is_blocked_status = has_missing_files or certification_bundle_status == "certification_blocked"

    # Collect validation status
    if len(artifact_validation_failures) > 0:
        reason_codes.append("RELEASE_AUDIT_ARTIFACT_VALIDATION_FAILED")
    else:
        reason_codes.append("RELEASE_AUDIT_ARTIFACT_VALIDATION_PASSED")

    if (len(artifact_digest_mismatches) == 0 and
            len(artifact_validation_failures) == 0 and
            certification_bundle_digest_match and
            certification_bundle_status == "certification_ready" and
            ok_bundle and
            nested_rc_id_consistent and
            rc_approved_in_registry):
        audit_status = "audit_verified"
        reason_codes.append("RELEASE_AUDIT_VERIFIED")
    elif is_blocked_status:
        audit_status = "audit_blocked"
        reason_codes.append("RELEASE_AUDIT_BLOCKED")
    else:
        audit_status = "audit_failed"
        reason_codes.append("RELEASE_AUDIT_FAILED")

    # Generate deterministic ID
    case_suffix = rc_id.split('-')[-1] if rc_id else 'UNKNOWN'
    case = WaveguideReleaseCertificationAuditCase(
        audit_case_id=f"SOL-WAVEGUIDE-RELEASE-CERTIFICATION-AUDIT-CASE-{case_suffix}",
        certification_bundle_id=certification_bundle_id,
        certification_bundle_path=bundle_path,
        certification_bundle_digest_recorded=certification_bundle_digest_recorded,
        certification_bundle_digest_recomputed=certification_bundle_digest_recomputed,
        certification_bundle_digest_match=certification_bundle_digest_match,
        certification_bundle_status=certification_bundle_status,
        rc_id=rc_id,
        candidate_level=candidate_level,
        manifest_digest_recorded=manifest_digest_recorded,
        manifest_digest_recomputed=manifest_digest_recomputed,
        release_gate_digest_recorded=release_gate_digest_recorded,
        release_gate_digest_recomputed=release_gate_digest_recomputed,
        promotion_record_digest_recorded=promotion_record_digest_recorded,
        promotion_record_digest_recomputed=promotion_record_digest_recomputed,
        promotion_court_verdict_digest_recorded=promotion_court_verdict_digest_recorded,
        promotion_court_verdict_digest_recomputed=promotion_court_verdict_digest_recomputed,
        release_registry_digest_recorded=release_registry_digest_recorded,
        release_registry_digest_recomputed=release_registry_digest_recomputed,
        runtime_capability_resolution_digest_recorded=runtime_capability_resolution_digest_recorded,
        runtime_capability_resolution_digest_recomputed=runtime_capability_resolution_digest_recomputed,
        compiler_session_registry_digest_recorded=compiler_session_registry_digest_recorded,
        compiler_session_registry_digest_recomputed=compiler_session_registry_digest_recomputed,
        artifact_digest_mismatches=sorted(artifact_digest_mismatches),
        artifact_validation_failures=sorted(artifact_validation_failures),
        rc_approved_in_registry=rc_approved_in_registry,
        nested_rc_id_consistent=nested_rc_id_consistent,
        session_registry_status=session_registry_status,
        registered_session_count=registered_session_count,
        registered_rejection_session_count=registered_rejection_session_count,
        blocked_session_count=blocked_session_count,
        invalid_session_count=invalid_session_count,
        compiler_profiles_indexed=compiler_profiles_indexed,
        pass_sequences_indexed=pass_sequences_indexed,
        handler_ids_indexed=handler_ids_indexed,
        final_output_payload_digests=final_output_payload_digests,
        audit_status=audit_status,
        reason_codes=sorted(list(set(reason_codes))),
        notes=notes,
        software_validation_caveat=software_validation_caveat,
        audit_case_digest=""
    )
    case.audit_case_digest = hash_waveguide_release_certification_audit_case(case)
    return case


def validate_waveguide_release_certification_bundle_independently(bundle: Any) -> Tuple[bool, List[str]]:
    """
    Validates a bundle independently by building its audit case and checking its status.
    """
    case = build_waveguide_release_certification_audit_case(bundle)
    is_valid = (case.audit_status == "audit_verified")
    return is_valid, case.reason_codes


def build_waveguide_release_certification_audit_report(cases: List[Any]) -> WaveguideReleaseCertificationAuditReport:
    """
    Combines one or more audit cases into a single deterministic top-level audit report.
    """
    # 1. Sort cases deterministically
    def case_sort_key(c):
        if hasattr(c, "__dict__"):
            d = asdict(c)
        else:
            d = dict(c)
        return (
            d.get("rc_id", ""),
            d.get("certification_bundle_id", ""),
            d.get("certification_bundle_digest_recorded", "")
        )

    sorted_cases = sorted(cases, key=case_sort_key)

    audited_bundles = []
    verified_audits = []
    failed_audits = []
    blocked_audits = []

    verified_audit_count = 0
    failed_audit_count = 0
    blocked_audit_count = 0
    rc1_audit_count = 0
    rc2_audit_count = 0

    certification_bundle_digests = []
    manifest_digests = []
    release_gate_digests = []
    promotion_record_digests = []
    promotion_court_verdict_digests = []
    release_registry_digests = []
    runtime_capability_resolution_digests = []
    compiler_session_registry_digests = []

    artifact_digest_mismatch_count = 0
    artifact_validation_failure_count = 0

    all_reasons = []

    for case in sorted_cases:
        if hasattr(case, "__dict__"):
            c_dict = asdict(case)
        else:
            c_dict = dict(case)

        cb_id = c_dict.get("certification_bundle_id", "")
        status = c_dict.get("audit_status", "")
        rc_id = c_dict.get("rc_id", "")

        if cb_id:
            audited_bundles.append(cb_id)

        if status == "audit_verified":
            verified_audit_count += 1
            if cb_id:
                verified_audits.append(cb_id)
        elif status == "audit_blocked":
            blocked_audit_count += 1
            if cb_id:
                blocked_audits.append(cb_id)
        elif status == "audit_failed":
            failed_audit_count += 1
            if cb_id:
                failed_audits.append(cb_id)

        if "RC1" in rc_id:
            rc1_audit_count += 1
        elif "RC2" in rc_id:
            rc2_audit_count += 1

        # Collect digests
        def add_unique(lst, val):
            if val and val not in lst:
                lst.append(val)

        add_unique(certification_bundle_digests, c_dict.get("certification_bundle_digest_recorded"))
        add_unique(manifest_digests, c_dict.get("manifest_digest_recorded"))
        add_unique(release_gate_digests, c_dict.get("release_gate_digest_recorded"))
        add_unique(promotion_record_digests, c_dict.get("promotion_record_digest_recorded"))
        add_unique(promotion_court_verdict_digests, c_dict.get("promotion_court_verdict_digest_recorded"))
        add_unique(release_registry_digests, c_dict.get("release_registry_digest_recorded"))
        add_unique(runtime_capability_resolution_digests, c_dict.get("runtime_capability_resolution_digest_recorded"))
        add_unique(compiler_session_registry_digests, c_dict.get("compiler_session_registry_digest_recorded"))

        artifact_digest_mismatch_count += len(c_dict.get("artifact_digest_mismatches", []))
        artifact_validation_failure_count += len(c_dict.get("artifact_validation_failures", []))

        for rc in c_dict.get("reason_codes", []):
            if rc not in all_reasons:
                all_reasons.append(rc)

    # Sort lists deterministically
    audited_bundles = sorted(audited_bundles)
    verified_audits = sorted(verified_audits)
    failed_audits = sorted(failed_audits)
    blocked_audits = sorted(blocked_audits)

    certification_bundle_digests = sorted(certification_bundle_digests)
    manifest_digests = sorted(manifest_digests)
    release_gate_digests = sorted(release_gate_digests)
    promotion_record_digests = sorted(promotion_record_digests)
    promotion_court_verdict_digests = sorted(promotion_court_verdict_digests)
    release_registry_digests = sorted(release_registry_digests)
    runtime_capability_resolution_digests = sorted(runtime_capability_resolution_digests)
    compiler_session_registry_digests = sorted(compiler_session_registry_digests)

    # Determine top-level report status
    report_status = "audit_report_verified"
    if failed_audit_count > 0:
        report_status = "audit_report_failed"
        all_reasons.append("RELEASE_AUDIT_REPORT_FAILED")
    elif blocked_audit_count > 0 or len(sorted_cases) == 0:
        report_status = "audit_report_blocked"
        all_reasons.append("RELEASE_AUDIT_REPORT_BLOCKED")
    else:
        all_reasons.append("RELEASE_AUDIT_REPORT_VERIFIED")

    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    report = WaveguideReleaseCertificationAuditReport(
        audit_report_id="SOL-WAVEGUIDE-RELEASE-CERTIFICATION-AUDIT-REPORT",
        audit_report_version=1,
        audit_report_status=report_status,
        audited_bundles=audited_bundles,
        verified_audits=verified_audits,
        failed_audits=failed_audits,
        blocked_audits=blocked_audits,
        verified_audit_count=verified_audit_count,
        failed_audit_count=failed_audit_count,
        blocked_audit_count=blocked_audit_count,
        rc1_audit_count=rc1_audit_count,
        rc2_audit_count=rc2_audit_count,
        certification_bundle_digests=certification_bundle_digests,
        manifest_digests=manifest_digests,
        release_gate_digests=release_gate_digests,
        promotion_record_digests=promotion_record_digests,
        promotion_court_verdict_digests=promotion_court_verdict_digests,
        release_registry_digests=release_registry_digests,
        runtime_capability_resolution_digests=runtime_capability_resolution_digests,
        compiler_session_registry_digests=compiler_session_registry_digests,
        artifact_digest_mismatch_count=artifact_digest_mismatch_count,
        artifact_validation_failure_count=artifact_validation_failure_count,
        reason_codes=sorted(list(set(all_reasons))),
        software_validation_caveat=software_validation_caveat,
        audit_report_digest=""
    )
    report.audit_report_digest = hash_waveguide_release_certification_audit_report(report)
    return report


def validate_waveguide_release_certification_audit_report(report: Any) -> Tuple[bool, List[str]]:
    """
    Validates a top-level release certification audit report.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    reasons = []
    is_valid = True

    # Check caveat
    caveat = r_dict.get("software_validation_caveat", "")
    if caveat and "sandbox" in caveat.lower():
        reasons.append("RELEASE_AUDIT_SOFTWARE_CAVEAT_INCLUDED")
    else:
        is_valid = False
        reasons.append("RELEASE_AUDIT_REPORT_FAILED")

    # Recompute and compare report digest
    given_digest = r_dict.get("audit_report_digest", "")
    if given_digest:
        recomputed = hash_waveguide_release_certification_audit_report(r_dict)
        if recomputed == given_digest:
            reasons.append("RELEASE_AUDIT_REPORT_DIGEST_VALID")
        else:
            is_valid = False
            reasons.append("RELEASE_AUDIT_REPORT_FAILED")

    # Check verification status consistency
    status = r_dict.get("audit_report_status", "")
    total_audits = r_dict.get("verified_audit_count", 0) + r_dict.get("failed_audit_count", 0) + r_dict.get("blocked_audit_count", 0)

    if total_audits == 0:
        is_valid = False
        reasons.append("RELEASE_AUDIT_REPORT_FAILED")
    elif status == "audit_report_verified":
        if r_dict.get("verified_audit_count", 0) == total_audits and r_dict.get("failed_audit_count", 0) == 0 and r_dict.get("blocked_audit_count", 0) == 0:
            reasons.append("RELEASE_AUDIT_REPORT_VERIFIED")
        else:
            is_valid = False
            reasons.append("RELEASE_AUDIT_REPORT_FAILED")
    elif status == "audit_report_failed":
        reasons.append("RELEASE_AUDIT_REPORT_FAILED")
    elif status == "audit_report_blocked":
        reasons.append("RELEASE_AUDIT_REPORT_BLOCKED")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_release_certification_audit_report(report: Any) -> str:
    """
    Generates deterministic human-readable summary.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    lines = [
        "============================================================",
        "      SOL WAVEGUIDE RELEASE CERTIFICATION AUDIT REPORT SUMMARY",
        "============================================================",
        f"Report ID:        {r_dict.get('audit_report_id')}",
        f"Version:          {r_dict.get('audit_report_version')}",
        f"Status:           {r_dict.get('audit_report_status', '').upper()}",
        f"Report Digest:    {r_dict.get('audit_report_digest')}",
        "------------------------------------------------------------",
        "Audit Breakdown:",
        f"  * Total Verified Audits: {r_dict.get('verified_audit_count')}",
        f"  * Total Failed Audits:   {r_dict.get('failed_audit_count')}",
        f"  * Total Blocked Audits:  {r_dict.get('blocked_audit_count')}",
        f"  * RC1 Audit Count:       {r_dict.get('rc1_audit_count')}",
        f"  * RC2 Audit Count:       {r_dict.get('rc2_audit_count')}",
        "------------------------------------------------------------",
        "Audited Bundles:",
    ]
    for b in r_dict.get("audited_bundles", []):
        lines.append(f"  - {b}")
    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for rc in r_dict.get("reason_codes", []):
        lines.append(f"  - {rc}")
    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {r_dict.get('software_validation_caveat')}")
    lines.append("============================================================")
    return "\n".join(lines)


def export_waveguide_release_certification_audit_report(report: Any, filepath: str) -> None:
    """
    Exports report to a key-sorted JSON filepath.
    """
    if hasattr(report, "__dict__"):
        r_dict = asdict(report)
    elif isinstance(report, dict):
        r_dict = dict(report)
    else:
        raise TypeError("report must be a dictionary or a dataclass instance")

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_release_certification_audit_reports(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two reports and returns differences.
    """
    def to_dict(r):
        if hasattr(r, "__dict__"):
            return asdict(r)
        return dict(r)

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
