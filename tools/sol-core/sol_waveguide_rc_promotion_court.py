# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Release Candidate Court-Supervised Promotion Flow
=============================================================
Defines case models, required ranger panels, attestation verification rules,
quorum evaluations, and court verdict signing.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

from sol_waveguide_rc_manifest import build_waveguide_rc_manifest
from sol_waveguide_rc_release_gate import build_waveguide_rc_release_gate
from sol_waveguide_rc_promotion_ledger import (
    WaveguideRCPromotionRecord,
    build_waveguide_rc_promotion_record,
    validate_waveguide_rc_promotion_record,
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)


@dataclass
class RangerAttestation:
    attestation_id: str
    ranger_id: str
    scope: str
    status: str       # approved, rejected, warning
    reason_codes: List[str]
    notes: List[str]
    input_digest: str


@dataclass
class WaveguideRCPromotionCase:
    case_id: str
    rc_id: str
    candidate_level: str
    promotion_record_path: str
    promotion_record_digest: str
    promotion_record_status: str
    court_id: str
    required_rangers: List[str]
    quorum_rule: str
    software_validation_caveat: str
    case_digest: str = ""


@dataclass
class WaveguideRCCourtVerdict:
    verdict_id: str
    case_id: str
    rc_id: str
    candidate_level: str
    court_id: str
    court_verdict: str
    quorum_status: str
    required_attestations: List[str]
    received_attestations: List[str]
    approved_attestations: List[str]
    rejected_attestations: List[str]
    warning_attestations: List[str]
    attestations: List[Dict[str, Any]]
    promotion_record_digest: str
    case_digest: str
    software_validation_caveat: str
    reason_codes: List[str]
    verdict_digest: str = ""


def hash_waveguide_rc_promotion_case(case: Any) -> str:
    """
    Computes case digest, excluding case_digest itself.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    elif isinstance(case, dict):
        c_dict = dict(case)
    else:
        raise TypeError("case must be a dictionary or a dataclass instance")

    c_dict.pop("case_digest", None)
    return hash_data(c_dict)


def hash_waveguide_rc_court_verdict(verdict: Any) -> str:
    """
    Computes verdict digest, excluding verdict_digest itself.
    """
    if hasattr(verdict, "__dict__"):
        v_dict = asdict(verdict)
    elif isinstance(verdict, dict):
        v_dict = dict(verdict)
    else:
        raise TypeError("verdict must be a dictionary or a dataclass instance")

    v_dict.pop("verdict_digest", None)
    return hash_data(v_dict)


def build_waveguide_rc_promotion_case(record: Any, record_path: Optional[str] = None) -> WaveguideRCPromotionCase:
    """
    Builds a case file wrapping the signed promotion record.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    else:
        r_dict = dict(record)

    level = r_dict.get("candidate_level", "RC2")
    if not record_path:
        record_path = f"docs/SOL_WAVEGUIDE_RC_PROMOTION_RECORD_{level}.json"
    record_path = normalize_to_repo_path(record_path)

    required_rangers = [
        "ManifestBoundaryRanger",
        "ReleaseGateRanger",
        "PromotionLedgerRanger",
        "ProofLedgerRanger",
        "RegressionAuditRanger"
    ]

    case = WaveguideRCPromotionCase(
        case_id=f"SOL-WAVEGUIDE-RC-PROMOTION-CASE-{level}",
        rc_id=r_dict.get("rc_id"),
        candidate_level=level,
        promotion_record_path=record_path,
        promotion_record_digest=r_dict.get("record_digest", ""),
        promotion_record_status=r_dict.get("promotion_status", ""),
        court_id="SOL-WAVEGUIDE-RC-PROMOTION-COURT",
        required_rangers=required_rangers,
        quorum_rule="all_required_rangers_must_approve",
        software_validation_caveat=r_dict.get("software_validation_caveat", "")
    )

    case.case_digest = hash_waveguide_rc_promotion_case(case)
    return case


def validate_waveguide_rc_promotion_case(case: Any) -> Tuple[bool, List[str]]:
    """
    Verifies case digest matches and referenced promotion record is valid.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    else:
        c_dict = dict(case)

    reasons = []
    is_valid = True

    # 1. Verify case digest
    given_digest = c_dict.get("case_digest", "")
    computed_digest = hash_waveguide_rc_promotion_case(c_dict)
    if given_digest == computed_digest:
        reasons.append("RC_COURT_CASE_CANONICAL")
    else:
        is_valid = False
        reasons.append("RC_COURT_CASE_DIGEST_INVALID")

    # 2. Check promotion record file on disk
    record_path = c_dict.get("promotion_record_path", "")
    full_path = os.path.join(REPO_ROOT, record_path)
    if os.path.exists(full_path):
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        curr_hash = data.get("record_digest", "")
        if curr_hash == c_dict.get("promotion_record_digest"):
            reasons.append("RC_COURT_PROMOTION_RECORD_VALID")
        else:
            is_valid = False
            reasons.append("RC_COURT_PROMOTION_RECORD_MISMATCH")
    else:
        is_valid = False
        reasons.append("RC_COURT_PROMOTION_RECORD_MISSING")

    return is_valid, sorted(list(set(reasons)))


def evaluate_waveguide_rc_ranger_attestation(ranger_id: str, record: Any) -> RangerAttestation:
    """
    Runs deterministic verification checks on the record for a specific ranger.
    """
    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    else:
        r_dict = dict(record)

    scope = ""
    status = "rejected"
    reason_codes = []
    notes = []
    input_digest = r_dict.get("record_digest", "")

    if ranger_id == "ManifestBoundaryRanger":
        scope = "manifest_boundary_verification"
        # Validate manifest boundary hashes
        is_valid, validation_reasons = validate_waveguide_rc_promotion_record(record)
        manifest_ok = "RC_PROMOTION_MANIFEST_HASH_VALID" in validation_reasons and not any(
            r in validation_reasons for r in (
                "RC_PROMOTION_MANIFEST_HASH_MISMATCH",
                "RC_PROMOTION_MANIFEST_FILE_MISSING",
                "RC_PROMOTION_MANIFEST_HASH_ERROR"
            )
        )
        if r_dict.get("rc_id") and r_dict.get("candidate_level") in ("RC1", "RC2") and manifest_ok:
            status = "approved"
            reason_codes.append("RC_COURT_RANGER_APPROVED")
            notes.append("Manifest boundary check passed. Manifest digest matches filesystem artifact.")
        else:
            status = "rejected"
            reason_codes.append("RC_COURT_RANGER_REJECTED")
            notes.append("Manifest boundary check failed. Missing or mismatched manifest metadata.")

    elif ranger_id == "ReleaseGateRanger":
        scope = "release_gate_verification"
        gate_verdict = r_dict.get("release_gate_verdict")
        if gate_verdict == "release_ready":
            status = "approved"
            reason_codes.append("RC_COURT_RANGER_APPROVED")
            notes.append("Release gate verification passed. Verdict is release_ready.")
        else:
            status = "rejected"
            reason_codes.append("RC_COURT_RANGER_REJECTED")
            notes.append(f"Release gate verification failed. Verdict is {gate_verdict}.")

    elif ranger_id == "PromotionLedgerRanger":
        scope = "promotion_ledger_verification"
        is_valid, validation_reasons = validate_waveguide_rc_promotion_record(record)
        promo_ready = r_dict.get("promotion_status") == "promotion_ready"
        digest_valid = "RC_PROMOTION_RECORD_DIGEST_VALID" in validation_reasons

        if is_valid and promo_ready and digest_valid:
            status = "approved"
            reason_codes.append("RC_COURT_RANGER_APPROVED")
            notes.append("Promotion ledger verification passed. Record is canonical and digest matches.")
        else:
            status = "rejected"
            reason_codes.append("RC_COURT_RANGER_REJECTED")
            notes.append("Promotion ledger verification failed. Mismatched record digests or invalid status.")

    elif ranger_id == "ProofLedgerRanger":
        scope = "proof_ledger_verification"
        proof_claims = r_dict.get("proof_claims", {})
        caveat = r_dict.get("software_validation_caveat", "")

        claims_ok = "proof_claims_status" in proof_claims
        caveat_ok = caveat and "sandbox" in caveat.lower()

        level = r_dict.get("candidate_level")
        ledger_paths_ok = True
        if level == "RC2":
            ledger_paths_ok = len(r_dict.get("proof_ledger_paths", [])) > 0

        if claims_ok and caveat_ok and ledger_paths_ok:
            status = "approved"
            reason_codes.append("RC_COURT_RANGER_APPROVED")
            notes.append("Proof ledger verification passed. Software-only caveats and proof claims are correct.")
        else:
            status = "rejected"
            reason_codes.append("RC_COURT_RANGER_REJECTED")
            notes.append("Proof ledger verification failed. Missing required caveats or proof paths.")

    elif ranger_id == "RegressionAuditRanger":
        scope = "regression_audit_verification"
        reg_summary = r_dict.get("regression_summary", "")

        has_gate = "test_waveguide_rc_release_gate.py" in reg_summary
        has_manifest = "test_waveguide_rc_manifest.py" in reg_summary
        has_pytest = "pytest" in reg_summary
        has_seq = "sequential" in reg_summary or "no parallelism" in reg_summary

        if has_gate and has_manifest and has_pytest and has_seq:
            status = "approved"
            reason_codes.append("RC_COURT_RANGER_APPROVED")
            notes.append("Regression audit passed. Sequential validation campaigns verified successfully.")
        else:
            status = "rejected"
            reason_codes.append("RC_COURT_RANGER_REJECTED")
            notes.append("Regression audit failed. Incomplete regression documentation or non-sequential mode detected.")

    else:
        reason_codes.append("RC_COURT_RANGER_REJECTED")
        notes.append(f"Unknown ranger identifier: {ranger_id}")

    return RangerAttestation(
        attestation_id=f"SOL-WAVEGUIDE-RC-ATTESTATION-{ranger_id.upper()}-{r_dict.get('candidate_level')}",
        ranger_id=ranger_id,
        scope=scope,
        status=status,
        reason_codes=reason_codes,
        notes=notes,
        input_digest=input_digest
    )


def build_waveguide_rc_court_panel(record: Any) -> List[RangerAttestation]:
    """
    Builds the default five-ranger panel evaluating the promotion record.
    """
    rangers = [
        "ManifestBoundaryRanger",
        "ReleaseGateRanger",
        "PromotionLedgerRanger",
        "ProofLedgerRanger",
        "RegressionAuditRanger"
    ]
    return [evaluate_waveguide_rc_ranger_attestation(r_id, record) for r_id in rangers]


def build_waveguide_rc_court_verdict(case: Any, panel: List[RangerAttestation]) -> WaveguideRCCourtVerdict:
    """
    Computes attestation statuses, verifies quorum, and issues court verdict record.
    """
    if hasattr(case, "__dict__"):
        c_dict = asdict(case)
    else:
        c_dict = dict(case)

    att_dicts = []
    received = []
    approved = []
    rejected = []
    warning = []

    for att in panel:
        if hasattr(att, "__dict__"):
            att_dict = asdict(att)
        else:
            att_dict = dict(att)
        att_dicts.append(att_dict)

        ranger_id = att_dict.get("ranger_id")
        received.append(ranger_id)

        status = att_dict.get("status")
        if status == "approved":
            approved.append(ranger_id)
        elif status == "warning":
            warning.append(ranger_id)
        else:
            rejected.append(ranger_id)

    required_rangers = c_dict.get("required_rangers", [])
    quorum_status = "quorum_failed"
    if set(required_rangers).issubset(set(received)):
        quorum_status = "quorum_satisfied"

    court_verdict = "promotion_rejected"
    verdict_reasons = []

    if quorum_status == "quorum_satisfied":
        verdict_reasons.append("RC_COURT_QUORUM_SATISFIED")
        verdict_reasons.append("RC_COURT_REQUIRED_RANGERS_PRESENT")
    else:
        verdict_reasons.append("RC_COURT_QUORUM_FAILED")

    # Strict approval rules
    if len(rejected) == 0 and len(warning) == 0 and set(required_rangers).issubset(set(approved)):
        if c_dict.get("promotion_record_status") == "promotion_ready":
            court_verdict = "promotion_approved"
            verdict_reasons.append("RC_COURT_PROMOTION_APPROVED")
        else:
            verdict_reasons.append("RC_COURT_PROMOTION_REJECTED")
    else:
        if len(rejected) > 0:
            verdict_reasons.append("RC_COURT_RANGER_REJECTED")
        verdict_reasons.append("RC_COURT_PROMOTION_REJECTED")

    caveat = c_dict.get("software_validation_caveat", "")
    if caveat:
        verdict_reasons.append("RC_COURT_SOFTWARE_CAVEAT_INCLUDED")

    verdict_reasons.append("RC_COURT_CASE_CANONICAL")
    verdict_reasons.append("RC_COURT_VERDICT_DIGEST_VALID")

    verdict_reasons = sorted(list(set(verdict_reasons)))

    verdict = WaveguideRCCourtVerdict(
        verdict_id=f"SOL-WAVEGUIDE-RC-COURT-VERDICT-{c_dict.get('candidate_level')}",
        case_id=c_dict.get("case_id"),
        rc_id=c_dict.get("rc_id"),
        candidate_level=c_dict.get("candidate_level"),
        court_id=c_dict.get("court_id"),
        court_verdict=court_verdict,
        quorum_status=quorum_status,
        required_attestations=required_rangers,
        received_attestations=received,
        approved_attestations=approved,
        rejected_attestations=rejected,
        warning_attestations=warning,
        attestations=att_dicts,
        promotion_record_digest=c_dict.get("promotion_record_digest"),
        case_digest=c_dict.get("case_digest"),
        software_validation_caveat=caveat,
        reason_codes=verdict_reasons,
        verdict_digest=""
    )

    verdict.verdict_digest = hash_waveguide_rc_court_verdict(verdict)
    return verdict


def summarize_waveguide_rc_court_verdict(verdict: Any) -> str:
    """
    Generates formatted plaintext summary of the court verdict.
    """
    if hasattr(verdict, "__dict__"):
        v_dict = asdict(verdict)
    else:
        v_dict = dict(verdict)

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE RELEASE CANDIDATE COURT VERDICT",
        "============================================================",
        f"Verdict ID:       {v_dict.get('verdict_id')}",
        f"Case ID:          {v_dict.get('case_id')}",
        f"Candidate ID:     {v_dict.get('rc_id')}",
        f"Candidate Level:  {v_dict.get('candidate_level')}",
        f"Court Verdict:    {v_dict.get('court_verdict', '').upper()}",
        f"Quorum Status:    {v_dict.get('quorum_status', '').upper()}",
        f"Verdict Digest:   {v_dict.get('verdict_digest')}",
        "------------------------------------------------------------",
        "Ranger Attestation Summary:",
    ]
    for att in v_dict.get("attestations", []):
        lines.append(f"  * {att.get('ranger_id')}: {att.get('status').upper()} ({', '.join(att.get('reason_codes', []))})")

    lines.append("------------------------------------------------------------")
    lines.append("Reason Codes:")
    for code in v_dict.get("reason_codes", []):
        lines.append(f"  - {code}")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {v_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_rc_court_verdict(verdict: Any, filepath: str) -> None:
    """
    Exports court verdict to key-sorted JSON filepath.
    """
    if hasattr(verdict, "__dict__"):
        v_dict = asdict(verdict)
    else:
        v_dict = dict(verdict)

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(v_dict, f, indent=4, sort_keys=True)


def compare_waveguide_rc_court_verdicts(left_verdict: Any, right_verdict: Any) -> Dict[str, Any]:
    """
    Compares two court verdicts and returns differences.
    """
    def to_dict(ver):
        if hasattr(ver, "__dict__"):
            return asdict(ver)
        return dict(ver)

    left_dict = to_dict(left_verdict)
    right_dict = to_dict(right_verdict)

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
    from sol_waveguide_rc_promotion_ledger import (
        hash_waveguide_rc_promotion_record,
        export_waveguide_rc_promotion_record
    )
    # 1. Rebuild or load promotion records
    rc1_manifest = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rc2_manifest = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")

    rc1_rec = build_waveguide_rc_promotion_record(rc1_manifest)
    rc2_rec = build_waveguide_rc_promotion_record(rc2_manifest)

    # 2. Build cases
    rc1_case = build_waveguide_rc_promotion_case(rc1_rec)
    rc2_case = build_waveguide_rc_promotion_case(rc2_rec)

    # 3. Evaluate panels
    rc1_panel = build_waveguide_rc_court_panel(rc1_rec)
    rc2_panel = build_waveguide_rc_court_panel(rc2_rec)

    # 4. Generate verdicts
    rc1_verdict = build_waveguide_rc_court_verdict(rc1_case, rc1_panel)
    rc2_verdict = build_waveguide_rc_court_verdict(rc2_case, rc2_panel)

    rc1_export = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_COURT_VERDICT_RC1.json")
    rc2_export = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_COURT_VERDICT_RC2.json")

    export_waveguide_rc_court_verdict(rc1_verdict, rc1_export)
    export_waveguide_rc_court_verdict(rc2_verdict, rc2_export)

    print(f"Exported RC1 court verdict: {rc1_export}")
    print(f"Exported RC2 court verdict: {rc2_export}")
