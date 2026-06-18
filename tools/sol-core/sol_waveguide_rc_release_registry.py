# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Release Candidate Release Registry and Promotion Index
==================================================================
Manages the deterministic cataloging of all court-approved release candidates,
verifying ledger/verdict signatures and artifact paths in a software-supervised index.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

from sol_waveguide_rc_manifest import build_waveguide_rc_manifest
from sol_waveguide_rc_promotion_ledger import (
    validate_waveguide_rc_promotion_record,
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_rc_promotion_court import (
    hash_waveguide_rc_court_verdict,
    validate_waveguide_rc_promotion_case
)


@dataclass
class WaveguideRCRegistryEntry:
    entry_id: str
    rc_id: str
    candidate_level: str
    release_status: str             # release_registered, release_blocked, release_warning
    manifest_path: str
    manifest_digest: str
    delta_audit_digest: str
    promotion_record_path: str
    promotion_record_digest: str
    court_verdict_path: str
    court_verdict_digest: str
    court_verdict: str
    quorum_status: str
    approved_rangers: List[str]
    artifact_paths: List[str]
    software_validation_caveat: str
    registry_entry_digest: str = ""


@dataclass
class WaveguideRCReleaseRegistry:
    registry_id: str
    registry_version: int
    registry_status: str               # registry_valid, registry_blocked, registry_warning
    entries: Dict[str, Any]            # Map of rc_id -> dict/dataclass
    approved_rc_ids: List[str]
    latest_foundation_rc: Optional[str]
    latest_governed_stack_rc: Optional[str]
    artifact_paths: List[str]
    software_validation_caveat: str
    registry_digest: str = ""


def hash_waveguide_rc_registry_entry(entry: Any) -> str:
    """
    Computes digest for a registry entry, excluding registry_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or a dataclass instance")

    e_dict.pop("registry_entry_digest", None)
    return hash_data(e_dict)


def hash_waveguide_rc_release_registry(registry: Any) -> str:
    """
    Computes digest for the full registry, excluding registry_digest.
    """
    if hasattr(registry, "__dict__"):
        r_dict = asdict(registry)
    elif isinstance(registry, dict):
        r_dict = dict(registry)
    else:
        raise TypeError("registry must be a dictionary or a dataclass instance")

    r_dict.pop("registry_digest", None)
    return hash_data(r_dict)


def build_waveguide_rc_registry_entry(
    verdict: Any,
    record: Any,
    verdict_path: Optional[str] = None,
    record_path: Optional[str] = None
) -> WaveguideRCRegistryEntry:
    """
    Constructs a registry entry from a court verdict and its underlying promotion record.
    """
    if hasattr(verdict, "__dict__"):
        v_dict = asdict(verdict)
    else:
        v_dict = dict(verdict)

    if hasattr(record, "__dict__"):
        r_dict = asdict(record)
    else:
        r_dict = dict(record)

    rc_id = v_dict.get("rc_id")
    level = v_dict.get("candidate_level")

    if not verdict_path:
        verdict_path = f"docs/SOL_WAVEGUIDE_RC_COURT_VERDICT_{level}.json"
    verdict_path = normalize_to_repo_path(verdict_path)

    if not record_path:
        record_path = f"docs/SOL_WAVEGUIDE_RC_PROMOTION_RECORD_{level}.json"
    record_path = normalize_to_repo_path(record_path)

    court_verdict_val = v_dict.get("court_verdict")
    quorum_status_val = v_dict.get("quorum_status")
    caveat = v_dict.get("software_validation_caveat", "")
    artifacts = r_dict.get("artifact_paths", [])

    # Validation criteria checks
    court_approved = court_verdict_val == "promotion_approved"
    quorum_satisfied = quorum_status_val == "quorum_satisfied"
    digest_match = r_dict.get("record_digest") == v_dict.get("promotion_record_digest")
    caveat_ok = caveat and "sandbox" in caveat.lower()
    artifacts_present = len(artifacts) > 0

    if court_approved and quorum_satisfied and digest_match and caveat_ok and artifacts_present:
        release_status = "release_registered"
    else:
        release_status = "release_blocked"

    entry = WaveguideRCRegistryEntry(
        entry_id=f"SOL-WAVEGUIDE-RC-REGISTRY-ENTRY-{level}",
        rc_id=rc_id,
        candidate_level=level,
        release_status=release_status,
        manifest_path=r_dict.get("manifest_path", ""),
        manifest_digest=r_dict.get("manifest_digest", ""),
        delta_audit_digest=r_dict.get("delta_audit_digest", ""),
        promotion_record_path=record_path,
        promotion_record_digest=r_dict.get("record_digest", ""),
        court_verdict_path=verdict_path,
        court_verdict_digest=v_dict.get("verdict_digest", ""),
        court_verdict=court_verdict_val,
        quorum_status=quorum_status_val,
        approved_rangers=v_dict.get("approved_attestations", []),
        artifact_paths=artifacts,
        software_validation_caveat=caveat,
        registry_entry_digest=""
    )

    entry.registry_entry_digest = hash_waveguide_rc_registry_entry(entry)
    return entry


def validate_waveguide_rc_registry_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Performs full validation on a registry entry, checking digests and filesystem references.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    else:
        e_dict = dict(entry)

    reasons = []
    is_valid = True

    # 1. Digest check
    given_digest = e_dict.get("registry_entry_digest", "")
    computed_digest = hash_waveguide_rc_registry_entry(e_dict)
    if given_digest == computed_digest:
        reasons.append("RC_REGISTRY_ENTRY_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("RC_REGISTRY_ENTRY_DIGEST_INVALID")

    # 2. Manifest check
    manifest_path = e_dict.get("manifest_path", "")
    full_manifest_path = os.path.join(REPO_ROOT, manifest_path)
    if os.path.exists(full_manifest_path):
        from sol_waveguide_rc_promotion_ledger import hash_waveguide_rc_manifest
        if hash_waveguide_rc_manifest(full_manifest_path) == e_dict.get("manifest_digest"):
            reasons.append("RC_REGISTRY_MANIFEST_HASH_VALID")
        else:
            is_valid = False
            reasons.append("RC_REGISTRY_MANIFEST_HASH_MISMATCH")
    else:
        is_valid = False
        reasons.append("RC_REGISTRY_MANIFEST_FILE_MISSING")

    # 3. Promotion record check
    record_path = e_dict.get("promotion_record_path", "")
    full_record_path = os.path.join(REPO_ROOT, record_path)
    if os.path.exists(full_record_path):
        with open(full_record_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        curr_hash = data.get("record_digest", "")
        if curr_hash == e_dict.get("promotion_record_digest"):
            reasons.append("RC_REGISTRY_PROMOTION_RECORD_DIGEST_VALID")
        else:
            is_valid = False
            reasons.append("RC_REGISTRY_PROMOTION_RECORD_DIGEST_INVALID")
    else:
        is_valid = False
        reasons.append("RC_REGISTRY_PROMOTION_RECORD_FILE_MISSING")

    # 4. Court verdict check
    verdict_path = e_dict.get("court_verdict_path", "")
    full_verdict_path = os.path.join(REPO_ROOT, verdict_path)
    if os.path.exists(full_verdict_path):
        with open(full_verdict_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        curr_hash = data.get("verdict_digest", "")
        if curr_hash == e_dict.get("court_verdict_digest"):
            reasons.append("RC_REGISTRY_COURT_VERDICT_DIGEST_VALID")
        else:
            is_valid = False
            reasons.append("RC_REGISTRY_COURT_VERDICT_DIGEST_INVALID")
    else:
        is_valid = False
        reasons.append("RC_REGISTRY_COURT_VERDICT_FILE_MISSING")

    # 5. Business logic rules
    if e_dict.get("court_verdict") == "promotion_approved":
        reasons.append("RC_REGISTRY_COURT_VERDICT_APPROVED")
    else:
        is_valid = False
        reasons.append("RC_REGISTRY_COURT_VERDICT_NOT_APPROVED")

    if e_dict.get("quorum_status") == "quorum_satisfied":
        reasons.append("RC_REGISTRY_QUORUM_SATISFIED")
    else:
        is_valid = False
        reasons.append("RC_REGISTRY_QUORUM_FAILED")

    caveat = e_dict.get("software_validation_caveat", "")
    if caveat and "sandbox" in caveat.lower():
        reasons.append("RC_REGISTRY_SOFTWARE_CAVEAT_INCLUDED")
    else:
        is_valid = False

    artifacts = e_dict.get("artifact_paths", [])
    if artifacts:
        missing_art = False
        for art in artifacts:
            if not os.path.exists(os.path.join(REPO_ROOT, art)):
                missing_art = True
                break
        if not missing_art:
            reasons.append("RC_REGISTRY_REQUIRED_ARTIFACTS_PRESENT")
        else:
            is_valid = False
    else:
        is_valid = False

    if is_valid:
        reasons.append("RC_REGISTRY_ENTRY_CANONICAL")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_rc_release_registry(entries: List[Any]) -> WaveguideRCReleaseRegistry:
    """
    Assembles registry entries into the top-level Release Registry container.
    """
    entries_map = {}
    approved_ids = []
    latest_foundation = None
    latest_governed = None
    registry_status = "registry_valid"

    all_artifacts = [
        "docs/SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json",
        "docs/SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.md"
    ]

    for entry in entries:
        if hasattr(entry, "__dict__"):
            e_dict = asdict(entry)
        else:
            e_dict = dict(entry)

        rc_id = e_dict.get("rc_id")
        level = e_dict.get("candidate_level")
        status = e_dict.get("release_status")

        entries_map[rc_id] = e_dict

        # Collect artifacts
        for art in e_dict.get("artifact_paths", []):
            if art not in all_artifacts:
                all_artifacts.append(art)

        # Handle lookup statuses
        if status == "release_registered":
            approved_ids.append(rc_id)
            if level == "RC1":
                latest_foundation = rc_id
            elif level == "RC2":
                latest_governed = rc_id
        else:
            registry_status = "registry_blocked"

    approved_ids = sorted(approved_ids)

    registry = WaveguideRCReleaseRegistry(
        registry_id="SOL-WAVEGUIDE-RC-RELEASE-REGISTRY",
        registry_version=1,
        registry_status=registry_status,
        entries=entries_map,
        approved_rc_ids=approved_ids,
        latest_foundation_rc=latest_foundation,
        latest_governed_stack_rc=latest_governed,
        artifact_paths=sorted(all_artifacts),
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )

    registry.registry_digest = hash_waveguide_rc_release_registry(registry)
    return registry


def validate_waveguide_rc_release_registry(registry: Any) -> Tuple[bool, List[str]]:
    """
    Performs full validation on the release registry.
    """
    if hasattr(registry, "__dict__"):
        r_dict = asdict(registry)
    else:
        r_dict = dict(registry)

    reasons = []
    is_valid = True

    # 1. Registry digest
    given_digest = r_dict.get("registry_digest", "")
    computed_digest = hash_waveguide_rc_release_registry(r_dict)
    if given_digest == computed_digest:
        reasons.append("RC_REGISTRY_DIGEST_VALID")
    else:
        is_valid = False
        reasons.append("RC_REGISTRY_DIGEST_INVALID")

    # 2. Validate all entries
    entries_map = r_dict.get("entries", {})
    entry_checks_ok = True
    for rc_id, e_dict in entries_map.items():
        ok, entry_reasons = validate_waveguide_rc_registry_entry(e_dict)
        if not ok:
            entry_checks_ok = False

    if entry_checks_ok:
        reasons.append("RC_REGISTRY_APPROVED_RC_INDEXED")
    else:
        is_valid = False

    # 3. Status checks
    if r_dict.get("registry_status") == "registry_valid":
        reasons.append("RC_REGISTRY_VALID")
    else:
        is_valid = False
        reasons.append("RC_REGISTRY_BLOCKED")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_rc_release_registry(registry: Any) -> str:
    """
    Generates formatted plaintext summary of the release registry.
    """
    if hasattr(registry, "__dict__"):
        r_dict = asdict(registry)
    else:
        r_dict = dict(registry)

    lines = [
        "============================================================",
        "     SOL WAVEGUIDE RELEASE CANDIDATE RELEASE REGISTRY",
        "============================================================",
        f"Registry ID:      {r_dict.get('registry_id')}",
        f"Version:          {r_dict.get('registry_version')}",
        f"Status:           {r_dict.get('registry_status', '').upper()}",
        f"Registry Digest:  {r_dict.get('registry_digest')}",
        "------------------------------------------------------------",
        f"Latest Foundation RC:     {r_dict.get('latest_foundation_rc')}",
        f"Latest Governed Stack RC: {r_dict.get('latest_governed_stack_rc')}",
        "Approved Release Candidates:",
    ]
    for rc in r_dict.get("approved_rc_ids", []):
        entry = r_dict.get("entries", {}).get(rc, {})
        lines.append(f"  * {rc} (Digest: {entry.get('registry_entry_digest')[:12]}...)")

    lines.append("------------------------------------------------------------")
    lines.append("Caveat:")
    lines.append(f"  {r_dict.get('software_validation_caveat')}")
    lines.append("============================================================")

    return "\n".join(lines)


def export_waveguide_rc_release_registry(registry: Any, filepath: str) -> None:
    """
    Exports release registry to key-sorted JSON catalog.
    """
    if hasattr(registry, "__dict__"):
        r_dict = asdict(registry)
    else:
        r_dict = dict(registry)

    target_dir = os.path.dirname(filepath)
    if target_dir and not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(r_dict, f, indent=4, sort_keys=True)


def compare_waveguide_rc_release_registries(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two release registries for differences.
    """
    def to_dict(reg):
        if hasattr(reg, "__dict__"):
            return asdict(reg)
        return dict(reg)

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


if __name__ == "__main__":
    from sol_waveguide_rc_promotion_ledger import build_waveguide_rc_promotion_record
    from sol_waveguide_rc_promotion_court import (
        build_waveguide_rc_promotion_case,
        build_waveguide_rc_court_panel,
        build_waveguide_rc_court_verdict
    )
    # 1. Load verdicts and promotion records
    rc1_manifest = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC1")
    rc2_manifest = build_waveguide_rc_manifest("SOL-WAVEGUIDE-RC2")

    rc1_rec = build_waveguide_rc_promotion_record(rc1_manifest)
    rc2_rec = build_waveguide_rc_promotion_record(rc2_manifest)

    rc1_case = build_waveguide_rc_promotion_case(rc1_rec)
    rc2_case = build_waveguide_rc_promotion_case(rc2_rec)

    rc1_panel = build_waveguide_rc_court_panel(rc1_rec)
    rc2_panel = build_waveguide_rc_court_panel(rc2_rec)

    rc1_verdict = build_waveguide_rc_court_verdict(rc1_case, rc1_panel)
    rc2_verdict = build_waveguide_rc_court_verdict(rc2_case, rc2_panel)

    # 2. Build registry entries
    entry1 = build_waveguide_rc_registry_entry(rc1_verdict, rc1_rec)
    entry2 = build_waveguide_rc_registry_entry(rc2_verdict, rc2_rec)

    # 3. Assemble full registry catalog
    registry = build_waveguide_rc_release_registry([entry1, entry2])

    registry_export_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json")
    export_waveguide_rc_release_registry(registry, registry_export_path)

    print(f"Exported RC Release Registry index: {registry_export_path}")
