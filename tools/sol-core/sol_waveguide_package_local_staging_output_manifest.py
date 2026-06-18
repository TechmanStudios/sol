# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Local Staging Output Manifest.
Consumes the Controlled Local Staging Run Record and scans the staging root on the local filesystem,
recording staged file paths, sizes, digests, and matching status.
"""

import os
import json
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    hash_file_contents,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_package_controlled_local_staging_runner import (
    validate_waveguide_package_controlled_local_staging_run_record,
    resolve_waveguide_package_local_staging_root,
    validate_waveguide_package_local_staging_target_path
)
from sol_waveguide_package_controlled_local_staging_plan import (
    validate_waveguide_package_local_staging_path_safety
)


@dataclass
class WaveguidePackageLocalStagingOutputEntry:
    local_staging_output_entry_id: str
    output_index: int
    output_status: str  # local_staging_output_verified, local_staging_output_missing, etc.
    source_copy_record_digest: str
    source_artifact_path: str
    source_artifact_digest_expected: str
    target_staging_relative_path: str
    target_staged_file_exists: bool
    target_staged_file_digest: str
    target_staged_file_size_bytes: int
    target_digest_matches_source: bool
    target_size_matches_source: bool
    target_path_inside_staging_root: bool
    unexpected_file: bool
    missing_file: bool
    duplicate_target_path: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    local_staging_output_entry_digest: str = ""


@dataclass
class WaveguidePackageLocalStagingOutputManifest:
    local_staging_output_manifest_id: str
    local_staging_output_manifest_version: int
    local_staging_output_manifest_status: str  # package_local_staging_manifest_ready, etc.
    source_controlled_local_staging_run_record_digest: str
    source_controlled_local_staging_plan_digest: str
    staging_root_token: str
    staging_root_display_path: str
    output_entries: List[WaveguidePackageLocalStagingOutputEntry]
    verified_output_entries: List[str]
    missing_output_entries: List[str]
    unexpected_output_entries: List[str]
    digest_mismatch_output_entries: List[str]
    invalid_output_entries: List[str]
    verified_output_count: int
    missing_output_count: int
    unexpected_output_count: int
    digest_mismatch_output_count: int
    invalid_output_count: int
    total_expected_file_count: int
    total_staged_file_count: int
    target_package_sections: List[str]
    source_artifact_paths: List[str]
    source_artifact_digests: List[str]
    target_staging_relative_paths: List[str]
    target_staged_file_digests: List[str]
    created_directory_count: int
    copied_file_count: int
    archive_created_count: int
    upload_count: int
    deployment_count: int
    signing_count: int
    external_publication_count: int
    production_mutation_count: int
    directory_creation_performed: bool
    file_copy_performed: bool
    archive_creation_performed: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    local_staging_output_manifest_digest: str = ""


def hash_waveguide_package_local_staging_output_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an output entry excluding local_staging_output_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or dataclass instance")

    e_copy = dict(e_dict)
    e_copy.pop("local_staging_output_entry_digest", None)
    return hash_data(e_copy)


def hash_waveguide_package_local_staging_output_manifest(manifest: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an output manifest excluding local_staging_output_manifest_digest.
    """
    if hasattr(manifest, "__dict__"):
        m_dict = asdict(manifest)
    elif isinstance(manifest, dict):
        m_dict = dict(manifest)
    else:
        raise TypeError("manifest must be a dictionary or dataclass instance")

    m_copy = dict(m_dict)
    m_copy.pop("local_staging_output_manifest_digest", None)
    return hash_data(m_copy)


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


def scan_waveguide_package_local_staging_directory(staging_root: str) -> List[str]:
    """
    Recursively scans the staging root directory and returns a sorted list of relative paths normalized to slash.
    """
    try:
        norm_root = resolve_waveguide_package_local_staging_root(staging_root)
    except ValueError:
        return []

    if not os.path.exists(norm_root):
        return []

    found_files = []
    for root, dirs, files in os.walk(norm_root):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, norm_root)
            normalized = rel_path.replace("\\", "/")
            found_files.append(normalized)

    return sorted(found_files)


def build_waveguide_package_local_staging_output_entry(
    output_index: int,
    output_status: str,
    source_copy_record_digest: str,
    source_artifact_path: str,
    source_artifact_digest_expected: str,
    target_staging_relative_path: str,
    target_staged_file_exists: bool,
    target_staged_file_digest: str,
    target_staged_file_size_bytes: int,
    target_digest_matches_source: bool,
    target_size_matches_source: bool,
    target_path_inside_staging_root: bool,
    unexpected_file: bool,
    missing_file: bool,
    duplicate_target_path: bool,
    reason_codes: List[str]
) -> WaveguidePackageLocalStagingOutputEntry:
    entry = WaveguidePackageLocalStagingOutputEntry(
        local_staging_output_entry_id=f"SOL-WAVEGUIDE-OUTPUT-ENTRY-{output_index:03d}",
        output_index=output_index,
        output_status=output_status,
        source_copy_record_digest=source_copy_record_digest,
        source_artifact_path=source_artifact_path,
        source_artifact_digest_expected=source_artifact_digest_expected,
        target_staging_relative_path=target_staging_relative_path,
        target_staged_file_exists=target_staged_file_exists,
        target_staged_file_digest=target_staged_file_digest,
        target_staged_file_size_bytes=target_staged_file_size_bytes,
        target_digest_matches_source=target_digest_matches_source,
        target_size_matches_source=target_size_matches_source,
        target_path_inside_staging_root=target_path_inside_staging_root,
        unexpected_file=unexpected_file,
        missing_file=missing_file,
        duplicate_target_path=duplicate_target_path,
        reason_codes=reason_codes,
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    entry.local_staging_output_entry_digest = hash_waveguide_package_local_staging_output_entry(entry)
    return entry


def validate_waveguide_package_local_staging_output_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates an output entry model.
    """
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    errors = []

    # Verify digest
    recorded_digest = e_dict.get("local_staging_output_entry_digest", "")
    if not recorded_digest:
        errors.append("Missing output entry digest")
    else:
        recomputed = hash_waveguide_package_local_staging_output_entry(e_dict)
        if recomputed != recorded_digest:
            errors.append(f"Output entry digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    # Boundary check
    rel_path = e_dict.get("target_staging_relative_path", "")
    if not validate_waveguide_package_local_staging_path_safety(rel_path):
        errors.append(f"Invalid relative target path: {rel_path}")

    return len(errors) == 0, errors


def build_waveguide_package_local_staging_output_manifest(
    run_record_path_or_dict: Any,
    staging_root: str
) -> WaveguidePackageLocalStagingOutputManifest:
    """
    Scans the staging_root directory on disk, maps against execution copy records,
    and builds the output manifest.
    """
    run_dict = _load_dict(run_record_path_or_dict) or {}
    run_digest = run_dict.get("controlled_local_staging_run_record_digest", "")
    plan_digest = run_dict.get("source_controlled_local_staging_plan_digest", "")

    # Validate run record pre-conditions
    valid_run, run_errs = validate_waveguide_package_controlled_local_staging_run_record(run_dict)

    manifest_status = "package_local_staging_manifest_ready"
    reason_codes = ["MANIFEST_BUILD_SUCCESS"]

    if run_dict.get("controlled_local_staging_run_status") != "package_local_staging_run_completed":
        manifest_status = "package_local_staging_manifest_blocked"
        reason_codes.append("RUN_STATUS_NOT_COMPLETED")

    norm_root = ""
    try:
        norm_root = resolve_waveguide_package_local_staging_root(staging_root)
    except ValueError as e:
        manifest_status = "package_local_staging_manifest_blocked"
        reason_codes.append(str(e))

    # Scan directories
    staged_files = scan_waveguide_package_local_staging_directory(staging_root)
    staged_set = set(staged_files)

    copy_records = run_dict.get("copy_records", [])
    output_entries = []
    verified_ids = []
    missing_ids = []
    unexpected_ids = []
    mismatch_ids = []
    invalid_ids = []

    seen_targets = set()
    idx = 0

    # Match expected copies
    for cr in copy_records:
        rel_path = cr.get("target_staging_relative_path")
        src_path = cr.get("source_artifact_path")
        expected_digest = cr.get("source_artifact_digest_expected")
        cr_digest = cr.get("local_staging_copy_record_digest")
        src_size = cr.get("source_artifact_size_bytes", 0)

        # Collision check
        duplicate = False
        if rel_path in seen_targets:
            duplicate = True
        seen_targets.add(rel_path)

        exists = False
        size = 0
        digest = ""
        inside = validate_waveguide_package_local_staging_target_path(staging_root, rel_path)

        if inside and norm_root:
            tgt_full = os.path.join(norm_root, rel_path)
            if os.path.exists(tgt_full) and os.path.isfile(tgt_full):
                exists = True
                size = os.path.getsize(tgt_full)
                try:
                    digest = hash_file_contents(tgt_full)
                except Exception:
                    digest = ""
                # Remove from scanned set to track unexpected files
                if rel_path in staged_set:
                    staged_set.remove(rel_path)

        is_self_referential = ("_CATALOG" in src_path or "_PLAN" in src_path or "_MANIFEST" in src_path) if src_path else False
        if is_self_referential:
            actual_src_digest = cr.get("source_artifact_digest_actual") or expected_digest
            digest_matches = (digest == actual_src_digest) if exists else False
        else:
            digest_matches = (digest == expected_digest) if exists else False
        size_matches = (size == src_size) if exists else False

        # Status rules
        status = "local_staging_output_verified"
        entry_reasons = ["ENTRY_VERIFIED"]
        missing = False

        if not exists:
            status = "local_staging_output_missing"
            entry_reasons = ["FILE_MISSING"]
            missing = True
        elif not digest_matches:
            status = "local_staging_output_digest_mismatch"
            entry_reasons = ["DIGEST_MISMATCH"]
        elif duplicate:
            status = "local_staging_output_invalid"
            entry_reasons = ["DUPLICATE_TARGET_PATH"]

        entry = build_waveguide_package_local_staging_output_entry(
            output_index=idx,
            output_status=status,
            source_copy_record_digest=cr_digest,
            source_artifact_path=src_path,
            source_artifact_digest_expected=expected_digest,
            target_staging_relative_path=rel_path,
            target_staged_file_exists=exists,
            target_staged_file_digest=digest,
            target_staged_file_size_bytes=size,
            target_digest_matches_source=digest_matches,
            target_size_matches_source=size_matches,
            target_path_inside_staging_root=inside,
            unexpected_file=False,
            missing_file=missing,
            duplicate_target_path=duplicate,
            reason_codes=entry_reasons
        )
        output_entries.append(entry)

        # Categorize
        if status == "local_staging_output_verified":
            verified_ids.append(entry.local_staging_output_entry_id)
        elif status == "local_staging_output_missing":
            missing_ids.append(entry.local_staging_output_entry_id)
        elif status == "local_staging_output_digest_mismatch":
            mismatch_ids.append(entry.local_staging_output_entry_id)
        else:
            invalid_ids.append(entry.local_staging_output_entry_id)

        idx += 1

    # Remaining unexpected files
    for unexp in sorted(list(staged_set)):
        tgt_full = os.path.join(norm_root, unexp) if norm_root else ""
        size = os.path.getsize(tgt_full) if tgt_full else 0
        try:
            digest = hash_file_contents(tgt_full) if tgt_full else ""
        except Exception:
            digest = ""

        entry = build_waveguide_package_local_staging_output_entry(
            output_index=idx,
            output_status="local_staging_output_unexpected",
            source_copy_record_digest="",
            source_artifact_path="",
            source_artifact_digest_expected="",
            target_staging_relative_path=unexp,
            target_staged_file_exists=True,
            target_staged_file_digest=digest,
            target_staged_file_size_bytes=size,
            target_digest_matches_source=False,
            target_size_matches_source=False,
            target_path_inside_staging_root=True,
            unexpected_file=True,
            missing_file=False,
            duplicate_target_path=False,
            reason_codes=["UNEXPECTED_FILE_ON_DISK"]
        )
        output_entries.append(entry)
        unexpected_ids.append(entry.local_staging_output_entry_id)
        idx += 1

    if missing_ids or unexpected_ids or mismatch_ids or invalid_ids:
        manifest_status = "package_local_staging_manifest_blocked"
        reason_codes.append("MANIFEST_CONTAINS_ERRORS")

    # Metadata lists
    target_sections = sorted(list(set(e.get("target_package_section") for e in copy_records if e.get("target_package_section"))))
    source_paths = sorted(list(set(e.source_artifact_path for e in output_entries if e.source_artifact_path)))
    source_digests = sorted(list(set(e.source_artifact_digest_expected for e in output_entries if e.source_artifact_digest_expected)))
    target_rel_paths = sorted(list(set(e.target_staging_relative_path for e in output_entries)))
    staged_digests = sorted(list(set(e.target_staged_file_digest for e in output_entries if e.target_staged_file_digest)))

    manifest = WaveguidePackageLocalStagingOutputManifest(
        local_staging_output_manifest_id="SOL-WAVEGUIDE-LOCAL-STAGING-OUTPUT-MANIFEST",
        local_staging_output_manifest_version=1,
        local_staging_output_manifest_status=manifest_status,
        source_controlled_local_staging_run_record_digest=run_digest,
        source_controlled_local_staging_plan_digest=plan_digest,
        staging_root_token="<SOL_LOCAL_STAGING_ROOT>",
        staging_root_display_path=str(staging_root).replace("\\", "/"),
        output_entries=output_entries,
        verified_output_entries=verified_ids,
        missing_output_entries=missing_ids,
        unexpected_output_entries=unexpected_ids,
        digest_mismatch_output_entries=mismatch_ids,
        invalid_output_entries=invalid_ids,
        verified_output_count=len(verified_ids),
        missing_output_count=len(missing_ids),
        unexpected_output_count=len(unexpected_ids),
        digest_mismatch_output_count=len(mismatch_ids),
        invalid_output_count=len(invalid_ids),
        total_expected_file_count=len(copy_records),
        total_staged_file_count=len(copy_records) - len(missing_ids) + len(unexpected_ids),
        target_package_sections=target_sections,
        source_artifact_paths=source_paths,
        source_artifact_digests=source_digests,
        target_staging_relative_paths=target_rel_paths,
        target_staged_file_digests=staged_digests,
        created_directory_count=run_dict.get("created_directory_count", 0),
        copied_file_count=run_dict.get("copied_file_count", 0),
        archive_created_count=0,
        upload_count=0,
        deployment_count=0,
        signing_count=0,
        external_publication_count=0,
        production_mutation_count=0,
        directory_creation_performed=run_dict.get("directory_creation_performed", False),
        file_copy_performed=run_dict.get("file_copy_performed", False),
        archive_creation_performed=False,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=run_dict.get("blocked_operation_attempt_counts", {}),
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    manifest.local_staging_output_manifest_digest = hash_waveguide_package_local_staging_output_manifest(manifest)
    return manifest


def validate_waveguide_package_local_staging_output_manifest(manifest: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates the manifest structure.
    """
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    errors = []

    # Verify digest
    recorded_digest = m_dict.get("local_staging_output_manifest_digest", "")
    if not recorded_digest:
        errors.append("Missing manifest digest")
    else:
        recomputed = hash_waveguide_package_local_staging_output_manifest(m_dict)
        if recomputed != recorded_digest:
            errors.append(f"Manifest digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    # Prohibitions
    prohibitions = [
        ("archive_creation_performed", False),
        ("upload_performed", False),
        ("deployment_performed", False),
        ("signing_performed", False),
        ("external_publication_performed", False),
        ("production_mutation_performed", False),
        ("archive_created_count", 0),
        ("upload_count", 0),
        ("deployment_count", 0),
        ("signing_count", 0),
        ("external_publication_count", 0),
        ("production_mutation_count", 0),
    ]
    for key, expected in prohibitions:
        if m_dict.get(key) is not expected:
            errors.append(f"{key} must be {expected}")

    # Verify entries
    entries = m_dict.get("output_entries", [])
    for e in entries:
        valid_entry, entry_errs = validate_waveguide_package_local_staging_output_entry(e)
        if not valid_entry:
            errors.extend(entry_errs)

    return len(errors) == 0, errors


def summarize_waveguide_package_local_staging_output_manifest(manifest: Any) -> str:
    """
    Returns a human-readable summary of the manifest.
    """
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    summary = [
        f"Manifest Status:                  {m_dict.get('local_staging_output_manifest_status', '').upper()}",
        f"Verified / Missing / Unexpected:  {m_dict.get('verified_output_count')} / {m_dict.get('missing_output_count')} / {m_dict.get('unexpected_output_count')}",
        f"Digest mismatch / Invalid count:  {m_dict.get('digest_mismatch_output_count')} / {m_dict.get('invalid_output_count')}",
        f"Expected / Staged file count:    {m_dict.get('total_expected_file_count')} / {m_dict.get('total_staged_file_count')}",
        f"Archive/Upload/Deploy performed: {m_dict.get('archive_creation_performed')} / {m_dict.get('upload_performed')} / {m_dict.get('deployment_performed')}",
        f"Manifest Digest:                 {m_dict.get('local_staging_output_manifest_digest')}"
    ]
    return "\n".join(summary)


def export_waveguide_package_local_staging_output_manifest(manifest: Any, filepath: str) -> None:
    """
    Exports the manifest to a JSON file.
    """
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(m_dict, f, sort_keys=True, indent=4)


def compare_waveguide_package_local_staging_output_manifests(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two output manifests.
    """
    l_dict = asdict(left) if hasattr(left, "__dict__") else dict(left)
    r_dict = asdict(right) if hasattr(right, "__dict__") else dict(right)
    return {
        "manifest_status_match": l_dict.get("local_staging_output_manifest_status") == r_dict.get("local_staging_output_manifest_status"),
        "total_staged_file_count_match": l_dict.get("total_staged_file_count") == r_dict.get("total_staged_file_count"),
        "manifest_digest_match": l_dict.get("local_staging_output_manifest_digest") == r_dict.get("local_staging_output_manifest_digest")
    }


def index_waveguide_package_local_staging_outputs_by_section(manifest: Any) -> Dict[str, List[Any]]:
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    entries = m_dict.get("output_entries", [])
    index = {}
    for e in entries:
        sect = e.get("target_package_section", "")
        index.setdefault(sect, []).append(e)
    return index


def index_waveguide_package_local_staging_outputs_by_digest_match(manifest: Any) -> Dict[bool, List[Any]]:
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    entries = m_dict.get("output_entries", [])
    index = {True: [], False: []}
    for e in entries:
        match = e.get("target_digest_matches_source", False)
        index[match].append(e)
    return index
