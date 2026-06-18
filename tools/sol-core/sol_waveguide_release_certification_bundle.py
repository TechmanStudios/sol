# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Release Certification Bundle.
Packages the entire release governance chain, approved release candidate data,
runtime capability policy, and governed compiler session registry into one
deterministic release-level proof capsule (bundle artifact).
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent governance modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT,
    hash_file_contents,
    validate_waveguide_rc_promotion_record
)
from sol_waveguide_rc_manifest import (
    validate_waveguide_rc_manifest_consistency,
    build_waveguide_rc_manifest
)
from sol_waveguide_rc_release_gate import (
    build_waveguide_rc_release_gate,
    validate_waveguide_rc_boundary,
    GOVERNED_PROFILES,
    GOVERNED_PASSES
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


@dataclass
class WaveguideReleaseCertificationBundle:
    certification_bundle_id: str
    certification_bundle_version: int
    certification_status: str
    rc_id: str
    candidate_level: str
    release_track: str
    manifest_digest: str
    release_gate_digest: str
    promotion_record_digest: str
    promotion_court_verdict_digest: str
    release_registry_digest: str
    runtime_capability_resolution_digest: str
    compiler_session_registry_digest: str
    artifact_paths: List[str]
    artifact_digests: Dict[str, str]
    approved_rcs: List[str]
    governed_profiles: List[str]
    governed_passes: List[str]
    registered_session_count: int
    registered_rejection_session_count: int
    blocked_session_count: int
    invalid_session_count: int
    rc1_session_count: int
    rc2_session_count: int
    compiler_profiles_indexed: List[str]
    pass_sequences_indexed: List[List[str]]
    handler_ids_indexed: List[str]
    final_output_payload_digests: List[str]
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    certification_bundle_digest: str = ""


def get_default_artifact_paths(rc_id: str) -> Dict[str, str]:
    """
    Returns the default paths of the required artifacts for a given rc_id.
    """
    norm_rc = rc_id.upper()
    if "RC1" in norm_rc:
        rc_suffix = "RC1"
    elif "RC2" in norm_rc:
        rc_suffix = "RC2"
    else:
        rc_suffix = norm_rc

    return {
        "manifest": f"docs/SOL_WAVEGUIDE_{rc_suffix}_MANIFEST.json",
        "release_gate": "docs/SOL_WAVEGUIDE_RC_DELTA_AUDIT.json",
        "promotion_record": f"docs/SOL_WAVEGUIDE_RC_PROMOTION_RECORD_{rc_suffix}.json",
        "court_verdict": f"docs/SOL_WAVEGUIDE_RC_COURT_VERDICT_{rc_suffix}.json",
        "release_registry": "docs/SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json",
        "capability_resolution": f"docs/SOL_WAVEGUIDE_RUNTIME_CAPABILITY_RESOLVER_{rc_suffix}.json",
        "session_registry": "docs/SOL_WAVEGUIDE_GOVERNED_COMPILER_SESSION_REGISTRY.json"
    }


def _load_and_digest(path: str) -> Tuple[Optional[Dict[str, Any]], str]:
    if not path:
        return None, ""
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(path))
    if os.path.exists(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            digest = hash_file_contents(full_path)
            return data, digest
        except Exception:
            return None, ""
    return None, ""


def hash_waveguide_release_certification_bundle(bundle: Any) -> str:
    """
    Computes digest for a certification bundle, excluding certification_bundle_digest.
    """
    if hasattr(bundle, "__dict__"):
        b_dict = asdict(bundle)
    elif isinstance(bundle, dict):
        b_dict = dict(bundle)
    else:
        raise TypeError("bundle must be a dictionary or a dataclass instance")

    b_dict_copy = dict(b_dict)
    b_dict_copy.pop("certification_bundle_digest", None)
    return hash_data(b_dict_copy)


def build_waveguide_release_certification_bundle(
    rc_id: str,
    manifest_path: Optional[str] = None,
    release_gate_path: Optional[str] = None,
    promotion_record_path: Optional[str] = None,
    court_verdict_path: Optional[str] = None,
    release_registry_path: Optional[str] = None,
    capability_resolution_path: Optional[str] = None,
    session_registry_path: Optional[str] = None
) -> WaveguideReleaseCertificationBundle:
    """
    Builds a deterministic Release Certification Bundle for a release candidate.
    """
    norm_rc = rc_id.upper()
    if "RC1" in norm_rc:
        target_rc = "SOL-WAVEGUIDE-RC1"
        candidate_level = "Foundation"
        release_track = "Foundation"
    elif "RC2" in norm_rc:
        target_rc = "SOL-WAVEGUIDE-RC2"
        candidate_level = "Governed Execution Stack"
        release_track = "Governed Execution Stack"
    else:
        target_rc = rc_id
        candidate_level = "Unknown"
        release_track = "Unknown"

    defaults = get_default_artifact_paths(target_rc)

    # Use provided paths or defaults, normalized to repo paths
    m_path = normalize_to_repo_path(manifest_path or defaults["manifest"])
    rg_path = normalize_to_repo_path(release_gate_path or defaults["release_gate"])
    pr_path = normalize_to_repo_path(promotion_record_path or defaults["promotion_record"])
    cv_path = normalize_to_repo_path(court_verdict_path or defaults["court_verdict"])
    rr_path = normalize_to_repo_path(release_registry_path or defaults["release_registry"])
    cr_path = normalize_to_repo_path(capability_resolution_path or defaults["capability_resolution"])
    sr_path = normalize_to_repo_path(session_registry_path or defaults["session_registry"])

    # Load and hash artifacts
    manifest, manifest_digest = _load_and_digest(m_path)
    release_gate, release_gate_digest = _load_and_digest(rg_path)
    promotion_record, promotion_record_digest = _load_and_digest(pr_path)
    court_verdict, court_verdict_digest = _load_and_digest(cv_path)
    release_registry, release_registry_digest = _load_and_digest(rr_path)
    capability_resolution, runtime_capability_resolution_digest = _load_and_digest(cr_path)
    session_registry, compiler_session_registry_digest = _load_and_digest(sr_path)

    # Collect artifact paths and digests
    artifact_paths = sorted([m_path, rg_path, pr_path, cv_path, rr_path, cr_path, sr_path])
    artifact_digests = {}
    if manifest_digest:
        artifact_digests[m_path] = manifest_digest
    if release_gate_digest:
        artifact_digests[rg_path] = release_gate_digest
    if promotion_record_digest:
        artifact_digests[pr_path] = promotion_record_digest
    if court_verdict_digest:
        artifact_digests[cv_path] = court_verdict_digest
    if release_registry_digest:
        artifact_digests[rr_path] = release_registry_digest
    if runtime_capability_resolution_digest:
        artifact_digests[cr_path] = runtime_capability_resolution_digest
    if compiler_session_registry_digest:
        artifact_digests[sr_path] = compiler_session_registry_digest

    # Extract info
    approved_rcs = []
    if release_registry:
        approved_rcs = release_registry.get("approved_rc_ids", [])

    governed_profiles = sorted(list(GOVERNED_PROFILES))
    governed_passes = sorted(list(GOVERNED_PASSES))

    registered_session_count = 0
    registered_rejection_session_count = 0
    blocked_session_count = 0
    invalid_session_count = 0
    rc1_session_count = 0
    rc2_session_count = 0
    compiler_profiles_indexed = []
    pass_sequences_indexed = []
    handler_ids_indexed = []
    final_output_payload_digests = []

    if session_registry:
        registered_session_count = session_registry.get("registered_session_count", 0)
        registered_rejection_session_count = session_registry.get("registered_rejection_session_count", 0)
        blocked_session_count = session_registry.get("blocked_session_count", 0)
        invalid_session_count = session_registry.get("invalid_session_count", 0)
        rc1_session_count = session_registry.get("rc1_session_count", 0)
        rc2_session_count = session_registry.get("rc2_session_count", 0)
        compiler_profiles_indexed = session_registry.get("compiler_profiles_indexed", [])
        pass_sequences_indexed = session_registry.get("pass_sequences_indexed", [])
        handler_ids_indexed = session_registry.get("handler_ids_indexed", [])
        final_output_payload_digests = session_registry.get("final_output_payload_digests", [])

    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    
    # Construct initial bundle object (without digest)
    bundle = WaveguideReleaseCertificationBundle(
        certification_bundle_id=f"SOL-WAVEGUIDE-RELEASE-CERTIFICATION-BUNDLE-{target_rc.split('-')[-1]}",
        certification_bundle_version=1,
        certification_status="certification_invalid",
        rc_id=target_rc,
        candidate_level=candidate_level,
        release_track=release_track,
        manifest_digest=manifest_digest,
        release_gate_digest=release_gate_digest,
        promotion_record_digest=promotion_record_digest,
        promotion_court_verdict_digest=court_verdict_digest,
        release_registry_digest=release_registry_digest,
        runtime_capability_resolution_digest=runtime_capability_resolution_digest,
        compiler_session_registry_digest=compiler_session_registry_digest,
        artifact_paths=artifact_paths,
        artifact_digests=artifact_digests,
        approved_rcs=approved_rcs,
        governed_profiles=governed_profiles,
        governed_passes=governed_passes,
        registered_session_count=registered_session_count,
        registered_rejection_session_count=registered_rejection_session_count,
        blocked_session_count=blocked_session_count,
        invalid_session_count=invalid_session_count,
        rc1_session_count=rc1_session_count,
        rc2_session_count=rc2_session_count,
        compiler_profiles_indexed=compiler_profiles_indexed,
        pass_sequences_indexed=pass_sequences_indexed,
        handler_ids_indexed=handler_ids_indexed,
        final_output_payload_digests=final_output_payload_digests,
        reason_codes=[],
        notes=[],
        software_validation_caveat=caveat,
        certification_bundle_digest=""
    )

    # Validate the bundle to populate status and reasons
    is_valid, reasons = validate_waveguide_release_certification_bundle(bundle)
    bundle.reason_codes = reasons
    if is_valid:
        bundle.certification_status = "certification_ready"
    else:
        # Check if missing files cause blockage, or validation failed
        has_missing = len(artifact_digests) < len(artifact_paths)
        if has_missing or "RELEASE_CERTIFICATION_BLOCKED" in reasons:
            bundle.certification_status = "certification_blocked"
        else:
            bundle.certification_status = "certification_invalid"

    # Now compute and set the bundle digest
    bundle.certification_bundle_digest = hash_waveguide_release_certification_bundle(bundle)
    return bundle


def validate_waveguide_release_certification_bundle(bundle: Any) -> Tuple[bool, List[str]]:
    """
    Validates a release certification bundle record, its nested artifacts on disk, and digests.
    """
    if hasattr(bundle, "__dict__"):
        b_dict = asdict(bundle)
    elif isinstance(bundle, dict):
        b_dict = dict(bundle)
    else:
        raise TypeError("bundle must be a dictionary or a dataclass instance")

    reasons = []
    notes = []
    is_valid = True
    is_blocked = False

    # Extract fields from bundle
    rc_id = b_dict.get("rc_id")
    paths = b_dict.get("artifact_paths", [])
    digests = b_dict.get("artifact_digests", {})
    caveat = b_dict.get("software_validation_caveat", "")

    # 1. Check caveat
    if caveat and "sandbox" in caveat.lower():
        reasons.append("RELEASE_CERT_SOFTWARE_CAVEAT_INCLUDED")
    else:
        is_valid = False
        notes.append("Software validation caveat is missing or invalid.")

    # 2. Check counts are present
    counts_keys = [
        "registered_session_count",
        "registered_rejection_session_count",
        "blocked_session_count",
        "invalid_session_count",
        "rc1_session_count",
        "rc2_session_count"
    ]
    if all(b_dict.get(k) is not None for k in counts_keys):
        reasons.append("RELEASE_CERT_COUNTS_VALID")
    else:
        is_valid = False
        notes.append("Required session counts are missing.")

    # 3. Check artifact digests are referenced
    if len(digests) > 0:
        reasons.append("RELEASE_CERT_ARTIFACT_DIGESTS_REFERENCED")
    else:
        is_valid = False
        notes.append("No artifact digests are referenced.")

    # 4. Resolve paths
    manifest_path = None
    release_gate_path = None
    promotion_record_path = None
    court_verdict_path = None
    release_registry_path = None
    capability_resolution_path = None
    session_registry_path = None

    for p in paths:
        p_lower = p.lower()
        if "manifest" in p_lower:
            manifest_path = p
        elif "delta_audit" in p_lower:
            release_gate_path = p
        elif "promotion_record" in p_lower:
            promotion_record_path = p
        elif "court_verdict" in p_lower:
            court_verdict_path = p
        elif "release_registry" in p_lower:
            release_registry_path = p
        elif "capability_resolver" in p_lower or "capability_resolution" in p_lower:
            capability_resolution_path = p
        elif "session_registry" in p_lower:
            session_registry_path = p

    # Load and validate manifest
    rc1_manifest = None
    rc2_manifest = None
    
    if manifest_path:
        manifest, m_digest = _load_and_digest(manifest_path)
        if not manifest:
            is_valid = False
            is_blocked = True
            reasons.append("RELEASE_CERT_MANIFEST_INVALID")
            notes.append("Manifest file is missing or unreadable.")
        else:
            if rc_id == "SOL-WAVEGUIDE-RC1":
                rc1_manifest = manifest
            elif rc_id == "SOL-WAVEGUIDE-RC2":
                rc2_manifest = manifest
            
            # Check digest matches
            expected_m_digest = b_dict.get("manifest_digest")
            if m_digest != expected_m_digest:
                is_valid = False
                reasons.append("RELEASE_CERT_MANIFEST_INVALID")
                notes.append("Manifest digest mismatch.")
            elif manifest.get("rc_id") != rc_id:
                is_valid = False
                reasons.append("RELEASE_CERT_MANIFEST_INVALID")
                notes.append("Manifest rc_id mismatch.")
            else:
                try:
                    if validate_waveguide_rc_manifest_consistency(manifest):
                        reasons.append("RELEASE_CERT_MANIFEST_VALID")
                    else:
                        is_valid = False
                        reasons.append("RELEASE_CERT_MANIFEST_INVALID")
                except Exception:
                    is_valid = False
                    reasons.append("RELEASE_CERT_MANIFEST_INVALID")
    else:
        is_valid = False
        is_blocked = True
        reasons.append("RELEASE_CERT_MANIFEST_INVALID")

    # Load and validate release gate (delta report)
    if release_gate_path:
        release_gate, rg_digest = _load_and_digest(release_gate_path)
        if not release_gate:
            is_valid = False
            is_blocked = True
            reasons.append("RELEASE_CERT_RELEASE_GATE_BLOCKED")
            notes.append("Release gate file is missing or unreadable.")
        else:
            expected_rg_digest = b_dict.get("release_gate_digest")
            if rg_digest != expected_rg_digest:
                is_valid = False
                reasons.append("RELEASE_CERT_RELEASE_GATE_BLOCKED")
                notes.append("Release gate digest mismatch.")
            elif not release_gate.get("boundary_valid", False):
                is_valid = False
                is_blocked = True
                reasons.append("RELEASE_CERT_RELEASE_GATE_BLOCKED")
                notes.append("Release gate boundary validation failed.")
            else:
                reasons.append("RELEASE_CERT_RELEASE_GATE_VALID")
    else:
        is_valid = False
        is_blocked = True
        reasons.append("RELEASE_CERT_RELEASE_GATE_BLOCKED")

    # Load and validate promotion record
    if promotion_record_path:
        promotion_record, pr_digest = _load_and_digest(promotion_record_path)
        if not promotion_record:
            is_valid = False
            is_blocked = True
            reasons.append("RELEASE_CERT_PROMOTION_RECORD_INVALID")
            notes.append("Promotion record file is missing or unreadable.")
        else:
            expected_pr_digest = b_dict.get("promotion_record_digest")
            if pr_digest != expected_pr_digest:
                is_valid = False
                reasons.append("RELEASE_CERT_PROMOTION_RECORD_INVALID")
                notes.append("Promotion record digest mismatch.")
            elif promotion_record.get("rc_id") != rc_id:
                is_valid = False
                reasons.append("RELEASE_CERT_PROMOTION_RECORD_INVALID")
                notes.append("Promotion record rc_id mismatch.")
            else:
                try:
                    ok, _ = validate_waveguide_rc_promotion_record(promotion_record)
                    if ok and promotion_record.get("promotion_status") == "promotion_ready":
                        reasons.append("RELEASE_CERT_PROMOTION_RECORD_VALID")
                    else:
                        is_valid = False
                        reasons.append("RELEASE_CERT_PROMOTION_RECORD_INVALID")
                except Exception:
                    is_valid = False
                    reasons.append("RELEASE_CERT_PROMOTION_RECORD_INVALID")
    else:
        is_valid = False
        is_blocked = True
        reasons.append("RELEASE_CERT_PROMOTION_RECORD_INVALID")

    # Load and validate court verdict
    if court_verdict_path:
        court_verdict, cv_digest = _load_and_digest(court_verdict_path)
        if not court_verdict:
            is_valid = False
            is_blocked = True
            reasons.append("RELEASE_CERT_COURT_VERDICT_REJECTED")
            notes.append("Court verdict file is missing or unreadable.")
        else:
            expected_cv_digest = b_dict.get("promotion_court_verdict_digest")
            if cv_digest != expected_cv_digest:
                is_valid = False
                reasons.append("RELEASE_CERT_COURT_VERDICT_REJECTED")
                notes.append("Court verdict digest mismatch.")
            elif court_verdict.get("rc_id") != rc_id:
                is_valid = False
                reasons.append("RELEASE_CERT_COURT_VERDICT_REJECTED")
                notes.append("Court verdict rc_id mismatch.")
            elif court_verdict.get("court_verdict") != "promotion_approved":
                is_valid = False
                is_blocked = True
                reasons.append("RELEASE_CERT_COURT_VERDICT_REJECTED")
                notes.append(f"Court verdict status is: {court_verdict.get('court_verdict')}")
            else:
                computed_cv_hash = hash_waveguide_rc_court_verdict(court_verdict)
                if computed_cv_hash != court_verdict.get("verdict_digest"):
                    is_valid = False
                    reasons.append("RELEASE_CERT_COURT_VERDICT_REJECTED")
                    notes.append("Court verdict internal digest validation failed.")
                else:
                    reasons.append("RELEASE_CERT_COURT_VERDICT_APPROVED")
    else:
        is_valid = False
        is_blocked = True
        reasons.append("RELEASE_CERT_COURT_VERDICT_REJECTED")

    # Load and validate release registry
    if release_registry_path:
        release_registry, rr_digest = _load_and_digest(release_registry_path)
        if not release_registry:
            is_valid = False
            is_blocked = True
            reasons.append("RELEASE_CERT_RC_MISSING_FROM_REGISTRY")
            notes.append("Release registry file is missing or unreadable.")
        else:
            expected_rr_digest = b_dict.get("release_registry_digest")
            if rr_digest != expected_rr_digest:
                is_valid = False
                reasons.append("RELEASE_CERT_RC_MISSING_FROM_REGISTRY")
                notes.append("Release registry digest mismatch.")
            else:
                try:
                    ok, _ = validate_waveguide_rc_release_registry(release_registry)
                    if ok:
                        reasons.append("RELEASE_CERT_RELEASE_REGISTRY_VALID")
                    else:
                        is_valid = False
                except Exception:
                    is_valid = False

                if rc_id in release_registry.get("approved_rc_ids", []):
                    reasons.append("RELEASE_CERT_RC_APPROVED_IN_REGISTRY")
                else:
                    is_valid = False
                    reasons.append("RELEASE_CERT_RC_MISSING_FROM_REGISTRY")
    else:
        is_valid = False
        is_blocked = True
        reasons.append("RELEASE_CERT_RC_MISSING_FROM_REGISTRY")

    # Load and validate runtime capability resolution
    if capability_resolution_path:
        capability_resolution, cr_digest = _load_and_digest(capability_resolution_path)
        if not capability_resolution:
            is_valid = False
            is_blocked = True
            reasons.append("RELEASE_CERT_RUNTIME_CAPABILITY_INVALID")
            notes.append("Runtime capability resolution file is missing or unreadable.")
        else:
            expected_cr_digest = b_dict.get("runtime_capability_resolution_digest")
            if cr_digest != expected_cr_digest:
                is_valid = False
                reasons.append("RELEASE_CERT_RUNTIME_CAPABILITY_INVALID")
                notes.append("Capability resolution digest mismatch.")
            elif capability_resolution.get("rc_id") != rc_id:
                is_valid = False
                reasons.append("RELEASE_CERT_RUNTIME_CAPABILITY_INVALID")
                notes.append("Capability resolution rc_id mismatch.")
            else:
                try:
                    ok, _ = validate_waveguide_runtime_capability_resolution(capability_resolution)
                    if ok:
                        reasons.append("RELEASE_CERT_RUNTIME_CAPABILITY_VALID")
                    else:
                        is_valid = False
                        reasons.append("RELEASE_CERT_RUNTIME_CAPABILITY_INVALID")
                except Exception:
                    is_valid = False
                    reasons.append("RELEASE_CERT_RUNTIME_CAPABILITY_INVALID")
    else:
        is_valid = False
        is_blocked = True
        reasons.append("RELEASE_CERT_RUNTIME_CAPABILITY_INVALID")

    # Load and validate session registry
    if session_registry_path:
        session_registry, sr_digest = _load_and_digest(session_registry_path)
        if not session_registry:
            is_valid = False
            is_blocked = True
            reasons.append("RELEASE_CERT_SESSION_REGISTRY_INVALID")
            notes.append("Session registry file is missing or unreadable.")
        else:
            expected_sr_digest = b_dict.get("compiler_session_registry_digest")
            if sr_digest != expected_sr_digest:
                is_valid = False
                reasons.append("RELEASE_CERT_SESSION_REGISTRY_INVALID")
                notes.append("Session registry digest mismatch.")
            elif session_registry.get("registry_status") != "session_registry_valid":
                is_valid = False
                is_blocked = True
                reasons.append("RELEASE_CERT_SESSION_REGISTRY_INVALID")
                notes.append(f"Session registry status is: {session_registry.get('registry_status')}")
            else:
                try:
                    ok, _ = validate_waveguide_governed_compiler_session_registry(session_registry)
                    if ok:
                        reasons.append("RELEASE_CERT_SESSION_REGISTRY_VALID")
                    else:
                        is_valid = False
                        reasons.append("RELEASE_CERT_SESSION_REGISTRY_INVALID")
                except Exception:
                    is_valid = False
                    reasons.append("RELEASE_CERT_SESSION_REGISTRY_INVALID")

                # Check session counts and blocked/invalid
                blocked_sc = session_registry.get("blocked_session_count", 0)
                invalid_sc = session_registry.get("invalid_session_count", 0)
                if blocked_sc > 0 or invalid_sc > 0:
                    is_valid = False
                    notes.append(f"Blocked sessions: {blocked_sc}, Invalid sessions: {invalid_sc}")
    else:
        is_valid = False
        is_blocked = True
        reasons.append("RELEASE_CERT_SESSION_REGISTRY_INVALID")

    # 5. Check if bundle digest validates
    given_bundle_digest = b_dict.get("certification_bundle_digest")
    if given_bundle_digest:
        computed_bundle_digest = hash_waveguide_release_certification_bundle(b_dict)
        if computed_bundle_digest == given_bundle_digest:
            reasons.append("RELEASE_CERT_BUNDLE_DIGEST_VALID")
        else:
            is_valid = False
            notes.append("Bundle digest verification failed.")
    
    if is_valid:
        reasons.append("RELEASE_CERTIFICATION_READY")
    elif is_blocked:
        reasons.append("RELEASE_CERTIFICATION_BLOCKED")
    else:
        reasons.append("RELEASE_CERTIFICATION_INVALID")

    # Sort reason codes deterministically
    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_release_certification_bundle(bundle: Any) -> str:
    """
    Generates a deterministic human-readable text summary of the Release Certification Bundle.
    """
    if hasattr(bundle, "__dict__"):
        b_dict = asdict(bundle)
    elif isinstance(bundle, dict):
        b_dict = dict(bundle)
    else:
        raise TypeError("bundle must be a dictionary or a dataclass instance")

    lines = [
        "============================================================",
        "      SOL WAVEGUIDE RELEASE CERTIFICATION BUNDLE SUMMARY",
        "============================================================",
        f"Bundle ID:        {b_dict.get('certification_bundle_id')}",
        f"Bundle Version:   {b_dict.get('certification_bundle_version')}",
        f"Status:           {b_dict.get('certification_status', '').upper()}",
        f"Target RC ID:     {b_dict.get('rc_id')}",
        f"Candidate Level:  {b_dict.get('candidate_level')}",
        f"Release Track:    {b_dict.get('release_track')}",
        f"Bundle Digest:    {b_dict.get('certification_bundle_digest')}",
        "------------------------------------------------------------",
        "Artifact Digests Included:",
        f"  * Manifest:             {b_dict.get('manifest_digest')}",
        f"  * Release Gate:         {b_dict.get('release_gate_digest')}",
        f"  * Promotion Record:     {b_dict.get('promotion_record_digest')}",
        f"  * Court Verdict:        {b_dict.get('promotion_court_verdict_digest')}",
        f"  * Release Registry:     {b_dict.get('release_registry_digest')}",
        f"  * Runtime Capability:   {b_dict.get('runtime_capability_resolution_digest')}",
        f"  * Session Registry:     {b_dict.get('compiler_session_registry_digest')}",
        "------------------------------------------------------------",
        "Session Registry Statistics:",
        f"  * Registered Sessions:  {b_dict.get('registered_session_count')}",
        f"  * Registered Rejections:{b_dict.get('registered_rejection_session_count')}",
        f"  * Blocked Sessions:     {b_dict.get('blocked_session_count')}",
        f"  * Invalid Sessions:     {b_dict.get('invalid_session_count')}",
        "------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in b_dict.get("reason_codes", []):
        lines.append(f"  - {code}")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {b_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_release_certification_bundle(bundle: Any, filepath: str) -> None:
    """
    Exports certification bundle to a key-sorted JSON filepath.
    """
    if hasattr(bundle, "__dict__"):
        b_dict = asdict(bundle)
    elif isinstance(bundle, dict):
        b_dict = dict(bundle)
    else:
        raise TypeError("bundle must be a dictionary or a dataclass instance")

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(b_dict, f, indent=4, sort_keys=True)


def compare_waveguide_release_certification_bundles(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two certification bundles and returns differences.
    """
    def to_dict(b):
        if hasattr(b, "__dict__"):
            return asdict(b)
        return dict(b)

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


def collect_waveguide_release_certification_artifact_digests(rc_id: str, paths: Dict[str, str]) -> Dict[str, str]:
    """
    Collects digests for all provided artifact paths.
    """
    digests = {}
    for key, p in paths.items():
        if p:
            norm_p = normalize_to_repo_path(p)
            full_p = os.path.join(REPO_ROOT, norm_p)
            if os.path.exists(full_p):
                digests[norm_p] = hash_file_contents(full_p)
    return digests


def validate_waveguide_release_certification_artifact_chain(
    rc_id: str,
    paths: Dict[str, str],
    digests: Dict[str, str]
) -> Tuple[bool, List[str]]:
    """
    Validates a custom set of paths and digests for an RC candidate.
    """
    # Create a temporary dummy bundle with these paths/digests to run the validator
    manifest_rel = normalize_to_repo_path(paths.get("manifest", ""))
    release_gate_rel = normalize_to_repo_path(paths.get("release_gate", ""))
    promotion_record_rel = normalize_to_repo_path(paths.get("promotion_record", ""))
    court_verdict_rel = normalize_to_repo_path(paths.get("court_verdict", ""))
    release_registry_rel = normalize_to_repo_path(paths.get("release_registry", ""))
    capability_resolution_rel = normalize_to_repo_path(paths.get("capability_resolution", ""))
    session_registry_rel = normalize_to_repo_path(paths.get("session_registry", ""))

    dummy_digests = {}
    for k, v in paths.items():
        if v:
            norm_k = normalize_to_repo_path(v)
            if norm_k in digests:
                dummy_digests[norm_k] = digests[norm_k]

    dummy = WaveguideReleaseCertificationBundle(
        certification_bundle_id="DUMMY",
        certification_bundle_version=1,
        certification_status="certification_invalid",
        rc_id=rc_id,
        candidate_level="Unknown",
        release_track="Unknown",
        manifest_digest=digests.get(manifest_rel, ""),
        release_gate_digest=digests.get(release_gate_rel, ""),
        promotion_record_digest=digests.get(promotion_record_rel, ""),
        promotion_court_verdict_digest=digests.get(court_verdict_rel, ""),
        release_registry_digest=digests.get(release_registry_rel, ""),
        runtime_capability_resolution_digest=digests.get(capability_resolution_rel, ""),
        compiler_session_registry_digest=digests.get(session_registry_rel, ""),
        artifact_paths=sorted([
            manifest_rel,
            release_gate_rel,
            promotion_record_rel,
            court_verdict_rel,
            release_registry_rel,
            capability_resolution_rel,
            session_registry_rel
        ]),
        artifact_digests=dummy_digests,
        approved_rcs=[],
        governed_profiles=[],
        governed_passes=[],
        registered_session_count=0,
        registered_rejection_session_count=0,
        blocked_session_count=0,
        invalid_session_count=0,
        rc1_session_count=0,
        rc2_session_count=0,
        compiler_profiles_indexed=[],
        pass_sequences_indexed=[],
        handler_ids_indexed=[],
        final_output_payload_digests=[],
        reason_codes=[],
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation.",
        certification_bundle_digest=""
    )

    # Populate counts to avoid count validation failure
    session_registry_full = os.path.join(REPO_ROOT, session_registry_rel)
    if os.path.exists(session_registry_full):
        try:
            with open(session_registry_full, "r", encoding="utf-8") as f:
                sr_data = json.load(f)
            dummy.registered_session_count = sr_data.get("registered_session_count", 0)
            dummy.registered_rejection_session_count = sr_data.get("registered_rejection_session_count", 0)
            dummy.blocked_session_count = sr_data.get("blocked_session_count", 0)
            dummy.invalid_session_count = sr_data.get("invalid_session_count", 0)
            dummy.rc1_session_count = sr_data.get("rc1_session_count", 0)
            dummy.rc2_session_count = sr_data.get("rc2_session_count", 0)
        except Exception:
            pass

    return validate_waveguide_release_certification_bundle(dummy)


def build_waveguide_release_certification_bundle_index(bundles: List[Any]) -> Dict[str, Any]:
    """
    Builds an index registry mapping rc_id to certification details.
    """
    index = {}
    for b in bundles:
        if hasattr(b, "__dict__"):
            b_dict = asdict(b)
        else:
            b_dict = dict(b)
        
        rc = b_dict.get("rc_id")
        index[rc] = {
            "certification_bundle_id": b_dict.get("certification_bundle_id"),
            "certification_status": b_dict.get("certification_status"),
            "bundle_digest": b_dict.get("certification_bundle_digest"),
            "candidate_level": b_dict.get("candidate_level")
        }
    return index
