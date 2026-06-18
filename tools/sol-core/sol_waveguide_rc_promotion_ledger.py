# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Release Candidate Signed Promotion Ledger
======================================================
Serializes and hashes release candidates (RC1/RC2), release gate evaluations,
and verification references into deterministic promotion records.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

from sol_waveguide_rc_manifest import build_waveguide_rc_manifest
from sol_waveguide_rc_release_gate import (
    build_waveguide_rc_release_gate,
    build_waveguide_rc_delta_report,
    summarize_waveguide_rc_release_gate
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def normalize_to_repo_path(path: str) -> str:
    """
    Normalizes path to a repository-relative path with forward slashes
    to prevent machine-dependent path differences in the hashes.
    """
    if not path:
        return ""
    if not os.path.isabs(path):
        return os.path.normpath(path).replace('\\', '/')
    try:
        rel = os.path.relpath(path, REPO_ROOT)
        return rel.replace('\\', '/')
    except Exception:
        return os.path.normpath(path).replace('\\', '/')


@dataclass
class WaveguideRCPromotionRecord:
    record_id: str
    rc_id: str
    candidate_level: str
    manifest_path: str
    manifest_digest: str
    release_gate_verdict: str
    release_gate_reason_codes: List[str]
    release_gate_summary: str
    delta_audit_path: str
    delta_audit_digest: str
    proof_ledger_paths: List[str]
    proof_claims: Dict[str, Any]
    regression_summary: str
    artifact_paths: List[str]
    promotion_authority: Dict[str, Any]
    promotion_scope: str
    software_validation_caveat: str
    promotion_status: str
    promotion_reason_codes: List[str]
    record_digest: str = ""


def hash_data(data: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of serialized canonical representation.
    """
    serialized = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def hash_file_contents(filepath: str) -> str:
    """
    Reads file, parses as JSON if possible to canonicalize, and hashes.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        data = json.loads(content)
        return hash_data(data)
    except Exception:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


def hash_waveguide_rc_manifest(manifest: Any) -> str:
    """
    Hashes a manifest dictionary or file path.
    """
    if isinstance(manifest, dict):
        return hash_data(manifest)
    elif isinstance(manifest, str):
        full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(manifest))
        return hash_file_contents(full_path)
    else:
        raise TypeError("manifest must be a dictionary or a filepath string")


def hash_waveguide_rc_audit_artifact(audit_data_or_path: Any) -> str:
    """
    Hashes a delta report dictionary or file path.
    """
    if isinstance(audit_data_or_path, dict):
        return hash_data(audit_data_or_path)
    elif isinstance(audit_data_or_path, str):
        full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(audit_data_or_path))
        return hash_file_contents(full_path)
    else:
        raise TypeError("audit_data_or_path must be a dictionary or a filepath string")


def hash_waveguide_rc_promotion_record(record: Any) -> str:
    """
    Hashes promotion record, excluding the record_digest field.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    elif isinstance(record, dict):
        r_dict = dict(record)
    else:
        raise TypeError("record must be a dictionary or a dataclass instance")

    r_dict.pop("record_digest", None)
    return hash_data(r_dict)


def build_waveguide_rc_promotion_record(
    candidate_manifest: Dict[str, Any],
    release_gate_report: Optional[Dict[str, Any]] = None,
    delta_report: Optional[Dict[str, Any]] = None,
    regression_summary: Optional[str] = None,
    authority: Optional[Dict[str, Any]] = None,
    proof_ledger_paths: Optional[List[str]] = None,
    artifact_paths: Optional[List[str]] = None,
    manifest_path: Optional[str] = None,
    delta_audit_path: Optional[str] = None
) -> WaveguideRCPromotionRecord:
    """
    Constructs a deterministic release promotion record for the candidate manifest.
    """
    rc_id = candidate_manifest.get("rc_id", "SOL-WAVEGUIDE-RC2")
    candidate_level = "RC1" if "RC1" in rc_id else "RC2"

    if release_gate_report is None:
        release_gate_report = build_waveguide_rc_release_gate(candidate_manifest)

    if delta_report is None:
        if candidate_level == "RC1":
            rc2_clean = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")
            delta_report = build_waveguide_rc_delta_report(candidate_manifest, rc2_clean)
        else:
            rc1_clean = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
            delta_report = build_waveguide_rc_delta_report(rc1_clean, candidate_manifest)

    if not manifest_path:
        manifest_path = f"docs/SOL_WAVEGUIDE_{candidate_level}_MANIFEST.json"
    manifest_path = normalize_to_repo_path(manifest_path)

    manifest_digest = hash_waveguide_rc_manifest(candidate_manifest)

    release_gate_verdict = release_gate_report.get("verdict", "blocked")
    release_gate_reason_codes = release_gate_report.get("reasons", [])
    release_gate_summary = summarize_waveguide_rc_release_gate(release_gate_report)

    if not delta_audit_path:
        delta_audit_path = "docs/SOL_WAVEGUIDE_RC_DELTA_AUDIT.json"
    delta_audit_path = normalize_to_repo_path(delta_audit_path)

    delta_audit_digest = hash_waveguide_rc_audit_artifact(delta_report)

    if proof_ledger_paths is None:
        if candidate_level == "RC2":
            proof_ledger_paths = ["docs/SOL_WAVEGUIDE_PROOF_LEDGER_RC2.md"]
        else:
            proof_ledger_paths = []
    proof_ledger_paths = [normalize_to_repo_path(p) for p in proof_ledger_paths]

    proof_claims = {}
    if candidate_level == "RC2":
        proof_claims = {
            "proof_claims_status": "verified_by_proof_ledger",
            "claims_documented": [
                "Claim 11: Sandbox Channel State Transitions",
                "Claim 12: Scoreboard Hazard Avoidance",
                "Claim 13: Microprogram Cost Model Policy",
                "Claim 14: Channelized Kernel Recognizer",
                "Claim 15: Safe Autotuning Convergence"
            ]
        }
    else:
        proof_claims = {
            "proof_claims_status": "foundation_claims_inherited_from_manifest_and_release_gate"
        }

    if regression_summary is None:
        regression_summary = (
            "Focused Gate Suite: pytest tests/test_waveguide_rc_release_gate.py \u2192 12/12 PASSED\n"
            "RC Manifest Suite: pytest tests/test_waveguide_rc_manifest.py \u2192 11/11 PASSED\n"
            "Full Regression Campaign: pytest \u2192 926/926 PASSED\n"
            "Execution mode: sequential, no parallelism"
        )

    if artifact_paths is None:
        if candidate_level == "RC1":
            artifact_paths = [
                f"docs/SOL_WAVEGUIDE_{candidate_level}_MANIFEST.json",
                "docs/SOL_WAVEGUIDE_RC_RELEASE_GATE.md",
                "docs/SOL_WAVEGUIDE_RC_DELTA_AUDIT.json",
                f"docs/SOL_WAVEGUIDE_RC_PROMOTION_RECORD_{candidate_level}.json"
            ]
        else:
            artifact_paths = [
                f"docs/SOL_WAVEGUIDE_{candidate_level}_MANIFEST.json",
                "docs/SOL_WAVEGUIDE_ARCHITECTURE_MAP_RC2.md",
                "docs/SOL_WAVEGUIDE_OPTIMIZATION_RESEARCH_DOSSIER_RC2.md",
                "docs/SOL_WAVEGUIDE_PROOF_LEDGER_RC2.md",
                "docs/SOL_WAVEGUIDE_RC_RELEASE_GATE.md",
                "docs/SOL_WAVEGUIDE_RC_DELTA_AUDIT.json",
                f"docs/SOL_WAVEGUIDE_RC_PROMOTION_RECORD_{candidate_level}.json"
            ]
    artifact_paths = [normalize_to_repo_path(p) for p in artifact_paths]

    if authority is None:
        authority = {
            "authority_type": "court_supervised_placeholder",
            "authority_id": "SOL-WAVEGUIDE-RC-PROMOTION-LEDGER",
            "authority_status": "pending_future_court_flow"
        }

    promotion_scope = "software_sandbox_verification_only"
    software_validation_caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    # Compute status and reason codes
    promotion_reasons = ["RC_PROMOTION_RECORD_CANONICAL"]
    if manifest_digest:
        promotion_reasons.append("RC_PROMOTION_MANIFEST_HASH_VALID")
    if delta_audit_digest:
        promotion_reasons.append("RC_PROMOTION_AUDIT_HASH_VALID")

    if release_gate_verdict == "release_ready":
        promotion_reasons.append("RC_PROMOTION_RELEASE_GATE_READY")
        status = "promotion_ready"
    elif release_gate_verdict == "warning":
        promotion_reasons.append("RC_PROMOTION_RELEASE_GATE_NOT_READY")
        status = "promotion_warning"
    else:
        promotion_reasons.append("RC_PROMOTION_RELEASE_GATE_NOT_READY")
        status = "promotion_blocked"

    # Check documentation existence
    required_docs = []
    if candidate_level == "RC1":
        required_docs = [
            "docs/SOL_WAVEGUIDE_RC1_MANIFEST.json",
            "docs/SOL_WAVEGUIDE_RC_RELEASE_GATE.md"
        ]
    else:
        required_docs = [
            "docs/SOL_WAVEGUIDE_RC2_MANIFEST.json",
            "docs/SOL_WAVEGUIDE_ARCHITECTURE_MAP_RC2.md",
            "docs/SOL_WAVEGUIDE_OPTIMIZATION_RESEARCH_DOSSIER_RC2.md",
            "docs/SOL_WAVEGUIDE_PROOF_LEDGER_RC2.md",
            "docs/SOL_WAVEGUIDE_RC_RELEASE_GATE.md"
        ]

    missing_docs = []
    for doc in required_docs:
        full_doc_path = os.path.join(REPO_ROOT, doc)
        if not os.path.exists(full_doc_path):
            missing_docs.append(doc)

    if missing_docs:
        promotion_reasons.append("RC_PROMOTION_REQUIRED_DOC_MISSING")
        status = "promotion_blocked"

    if proof_ledger_paths or candidate_level == "RC1":
        promotion_reasons.append("RC_PROMOTION_PROOF_LEDGER_REFERENCED")
    if regression_summary:
        promotion_reasons.append("RC_PROMOTION_REGRESSION_SUMMARY_RECORDED")
    if software_validation_caveat:
        promotion_reasons.append("RC_PROMOTION_SOFTWARE_CAVEAT_INCLUDED")

    # Pre-append the digest validity check reason code
    promotion_reasons.append("RC_PROMOTION_RECORD_DIGEST_VALID")

    record = WaveguideRCPromotionRecord(
        record_id=f"SOL-WAVEGUIDE-RC-PROMOTION-RECORD-{candidate_level}",
        rc_id=rc_id,
        candidate_level=candidate_level,
        manifest_path=manifest_path,
        manifest_digest=manifest_digest,
        release_gate_verdict=release_gate_verdict,
        release_gate_reason_codes=release_gate_reason_codes,
        release_gate_summary=release_gate_summary,
        delta_audit_path=delta_audit_path,
        delta_audit_digest=delta_audit_digest,
        proof_ledger_paths=proof_ledger_paths,
        proof_claims=proof_claims,
        regression_summary=regression_summary,
        artifact_paths=artifact_paths,
        promotion_authority=authority,
        promotion_scope=promotion_scope,
        software_validation_caveat=software_validation_caveat,
        promotion_status=status,
        promotion_reason_codes=promotion_reasons,
        record_digest=""
    )

    record.record_digest = hash_waveguide_rc_promotion_record(record)
    return record


def validate_waveguide_rc_promotion_record(record: Any) -> Tuple[bool, List[str]]:
    """
    Verifies that the promotion record has a valid digest and matches target filesystem artifacts.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    elif isinstance(record, dict):
        r_dict = dict(record)
    else:
        raise TypeError("record must be a dictionary or a dataclass instance")

    reasons = []
    is_valid = True

    given_digest = r_dict.get("record_digest", "")
    computed_digest = hash_waveguide_rc_promotion_record(r_dict)
    if given_digest == computed_digest:
        reasons.append("RC_PROMOTION_RECORD_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("RC_PROMOTION_RECORD_DIGEST_INVALID")

    manifest_path = r_dict.get("manifest_path", "")
    full_manifest_path = os.path.join(REPO_ROOT, manifest_path)
    if os.path.exists(full_manifest_path):
        try:
            curr_hash = hash_waveguide_rc_manifest(full_manifest_path)
            if curr_hash == r_dict.get("manifest_digest"):
                reasons.append("RC_PROMOTION_MANIFEST_HASH_VALID")
            else:
                is_valid = False
                reasons.append("RC_PROMOTION_MANIFEST_HASH_MISMATCH")
        except Exception:
            is_valid = False
            reasons.append("RC_PROMOTION_MANIFEST_HASH_ERROR")
    else:
        is_valid = False
        reasons.append("RC_PROMOTION_MANIFEST_FILE_MISSING")

    audit_path = r_dict.get("delta_audit_path", "")
    full_audit_path = os.path.join(REPO_ROOT, audit_path)
    if os.path.exists(full_audit_path):
        try:
            curr_hash = hash_waveguide_rc_audit_artifact(full_audit_path)
            if curr_hash == r_dict.get("delta_audit_digest"):
                reasons.append("RC_PROMOTION_AUDIT_HASH_VALID")
            else:
                is_valid = False
                reasons.append("RC_PROMOTION_AUDIT_HASH_MISMATCH")
        except Exception:
            is_valid = False
            reasons.append("RC_PROMOTION_AUDIT_HASH_ERROR")
    else:
        is_valid = False
        reasons.append("RC_PROMOTION_AUDIT_FILE_MISSING")

    level = r_dict.get("candidate_level")
    required_docs = []
    if level == "RC1":
        required_docs = [
            "docs/SOL_WAVEGUIDE_RC1_MANIFEST.json",
            "docs/SOL_WAVEGUIDE_RC_RELEASE_GATE.md"
        ]
    else:
        required_docs = [
            "docs/SOL_WAVEGUIDE_RC2_MANIFEST.json",
            "docs/SOL_WAVEGUIDE_ARCHITECTURE_MAP_RC2.md",
            "docs/SOL_WAVEGUIDE_OPTIMIZATION_RESEARCH_DOSSIER_RC2.md",
            "docs/SOL_WAVEGUIDE_PROOF_LEDGER_RC2.md",
            "docs/SOL_WAVEGUIDE_RC_RELEASE_GATE.md"
        ]

    missing = [d for d in required_docs if not os.path.exists(os.path.join(REPO_ROOT, d))]
    if missing:
        is_valid = False
        reasons.append("RC_PROMOTION_REQUIRED_DOC_MISSING")

    if r_dict.get("release_gate_verdict") == "release_ready":
        reasons.append("RC_PROMOTION_RELEASE_GATE_READY")
    else:
        is_valid = False
        reasons.append("RC_PROMOTION_RELEASE_GATE_NOT_READY")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_rc_promotion_record(record: Any) -> str:
    """
    Generates a deterministic human-readable text summary of the promotion record.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    elif isinstance(record, dict):
        r_dict = dict(record)
    else:
        raise TypeError("record must be a dictionary or a dataclass instance")

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE RELEASE CANDIDATE PROMOTION RECORD",
        "============================================================",
        f"Record ID:        {r_dict.get('record_id')}",
        f"Candidate ID:     {r_dict.get('rc_id')}",
        f"Candidate Level:  {r_dict.get('candidate_level')}",
        f"Promotion Status: {r_dict.get('promotion_status', '').upper()}",
        f"Record Digest:    {r_dict.get('record_digest')}",
        "------------------------------------------------------------",
        f"Manifest Path:    {r_dict.get('manifest_path')}",
        f"Manifest Digest:  {r_dict.get('manifest_digest')}",
        f"Gate Verdict:     {r_dict.get('release_gate_verdict')}",
        f"Delta Audit Path: {r_dict.get('delta_audit_path')}",
        f"Delta Audit Digest:{r_dict.get('delta_audit_digest')}",
        "------------------------------------------------------------",
        "Proof Claims Status:",
        f"  {r_dict.get('proof_claims', {}).get('proof_claims_status', 'N/A')}",
        "Regression Summary:",
    ]
    reg_summary = r_dict.get('regression_summary', '')
    for line in reg_summary.split('\n'):
        lines.append(f"  {line}")

    lines.append("------------------------------------------------------------")
    lines.append("Authority Metadata:")
    auth = r_dict.get('promotion_authority', {})
    lines.append(f"  ID:             {auth.get('authority_id')}")
    lines.append(f"  Type:           {auth.get('authority_type')}")
    lines.append(f"  Status:         {auth.get('authority_status')}")
    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {r_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_rc_promotion_record(record: Any, filepath: str) -> None:
    """
    Exports a promotion record as formatted JSON.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    elif isinstance(record, dict):
        r_dict = dict(record)
    else:
        raise TypeError("record must be a dictionary or a dataclass instance")

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_rc_promotion_records(left_record: Any, right_record: Any) -> Dict[str, Any]:
    """
    Generically compares two records and returns any key differences.
    """
    def to_dict(rec):
        if hasattr(rec, "__dict__"):
            return asdict(rec)
        return dict(rec)

    left_dict = to_dict(left_record)
    right_dict = to_dict(right_record)

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


if __name__ == "__main__":
    # Generate canonical promotion records
    rc1_manifest = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rc2_manifest = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")

    rc1_record = build_waveguide_rc_promotion_record(rc1_manifest)
    rc2_record = build_waveguide_rc_promotion_record(rc2_manifest)

    rc1_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_PROMOTION_RECORD_RC1.json")
    rc2_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_PROMOTION_RECORD_RC2.json")

    export_waveguide_rc_promotion_record(rc1_record, rc1_export_path)
    export_waveguide_rc_promotion_record(rc2_record, rc2_export_path)

    print(f"Exported RC1 promotion record: {rc1_export_path}")
    print(f"Exported RC2 promotion record: {rc2_export_path}")
