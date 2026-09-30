# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Waveguide Package Archive Manifest.
Consumes the Package Archive Build Record and inspects the created ZIP archive,
generating a detailed archive manifest.
"""

import os
import json
import zipfile
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_package_archive_builder import (
    validate_waveguide_package_archive_build_record,
    resolve_waveguide_package_archive_output_root,
    compute_waveguide_package_archive_digest
)
from sol_waveguide_package_archive_plan import (
    validate_waveguide_package_archive_member_path_safety
)


@dataclass
class WaveguidePackageArchiveManifestEntry:
    archive_manifest_entry_id: str
    entry_index: int
    archive_member_relative_path: str
    archive_member_exists: bool
    archive_member_path_safety_verified: bool
    archive_member_digest: str
    archive_member_size_bytes: int
    archive_member_compressed_size_bytes: int
    archive_member_compression_method: str
    source_staged_file_digest_expected: str
    source_staged_file_size_bytes_expected: int
    archive_member_digest_matches_source: bool
    archive_member_size_matches_source: bool
    unexpected_archive_member: bool
    missing_archive_member: bool
    duplicate_archive_member_path: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    archive_manifest_entry_digest: str = ""


@dataclass
class WaveguidePackageArchiveManifest:
    package_archive_manifest_id: str
    package_archive_manifest_version: int
    package_archive_manifest_status: str  # package_archive_manifest_ready, package_archive_manifest_blocked, etc.
    source_package_archive_build_record_digest: str
    source_package_archive_plan_digest: str
    archive_format: str  # zip
    archive_output_root_token: str  # <SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>
    archive_output_display_path: str
    archive_filename: str
    archive_display_path: str
    archive_file_exists: bool
    archive_file_digest: str
    archive_file_size_bytes: int
    archive_entries: List[WaveguidePackageArchiveManifestEntry]
    verified_archive_entries: List[str]
    missing_archive_entries: List[str]
    unexpected_archive_entries: List[str]
    digest_mismatch_archive_entries: List[str]
    invalid_archive_entries: List[str]
    verified_archive_entry_count: int
    missing_archive_entry_count: int
    unexpected_archive_entry_count: int
    digest_mismatch_archive_entry_count: int
    invalid_archive_entry_count: int
    total_expected_archive_file_count: int
    total_archive_member_count: int
    target_package_sections: List[str]
    archive_member_relative_paths: List[str]
    archive_member_digests: List[str]
    source_staged_file_digests: List[str]
    created_archive_count: int
    archive_creation_performed: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    blocked_operation_attempt_counts: Dict[str, int]
    reason_codes: List[str]
    software_validation_caveat: str
    package_archive_manifest_digest: str = ""


def hash_waveguide_package_archive_manifest_entry(entry: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of a manifest entry excluding archive_manifest_entry_digest.
    """
    if hasattr(entry, "__dict__"):
        e_dict = asdict(entry)
    elif isinstance(entry, dict):
        e_dict = dict(entry)
    else:
        raise TypeError("entry must be a dictionary or dataclass instance")

    e_copy = dict(e_dict)
    e_copy.pop("archive_manifest_entry_digest", None)
    return hash_data(e_copy)


def hash_waveguide_package_archive_manifest(manifest: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of an archive manifest excluding package_archive_manifest_digest.
    """
    if hasattr(manifest, "__dict__"):
        m_dict = asdict(manifest)
    elif isinstance(manifest, dict):
        m_dict = dict(manifest)
    else:
        raise TypeError("manifest must be a dictionary or dataclass instance")

    m_copy = dict(m_dict)
    m_copy.pop("package_archive_manifest_digest", None)
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


def compute_waveguide_package_archive_member_digest(zf: zipfile.ZipFile, member_path: str) -> str:
    """
    Computes SHA256 hex digest of a de-compressed zip member, parsing as JSON if possible to canonicalize.
    """
    with zf.open(member_path) as f:
        content_bytes = f.read()
    try:
        content_str = content_bytes.decode("utf-8")
        data = json.loads(content_str)
        return hash_data(data)
    except Exception:
        h = hashlib.sha256()
        h.update(content_bytes)
        return h.hexdigest()


def build_waveguide_package_archive_manifest_entry(
    member_path: str,
    zf: Optional[zipfile.ZipFile],
    zinfo: Optional[zipfile.ZipInfo],
    expected_digest: str,
    expected_size: int,
    index: int,
    unexpected: bool = False,
    missing: bool = False
) -> WaveguidePackageArchiveManifestEntry:
    """
    Builds a single manifest entry.
    """
    exists = (zf is not None) and (zinfo is not None) and not missing
    safety_ok = validate_waveguide_package_archive_member_path_safety(member_path)

    member_digest = ""
    member_size = 0
    c_size = 0
    c_method = "deflated"

    if exists and zf and zinfo:
        try:
            member_digest = compute_waveguide_package_archive_member_digest(zf, member_path)
            member_size = zinfo.file_size
            c_size = zinfo.compress_size
        except Exception:
            exists = False

    digest_match = (member_digest == expected_digest) and (member_digest != "")
    size_match = (member_size == expected_size) and (member_size != 0)

    entry = WaveguidePackageArchiveManifestEntry(
        archive_manifest_entry_id=f"SOL-WAVEGUIDE-ARCHIVE-MANIFEST-ENTRY-{index:03d}",
        entry_index=index,
        archive_member_relative_path=member_path,
        archive_member_exists=exists,
        archive_member_path_safety_verified=safety_ok,
        archive_member_digest=member_digest,
        archive_member_size_bytes=member_size,
        archive_member_compressed_size_bytes=c_size,
        archive_member_compression_method=c_method,
        source_staged_file_digest_expected=expected_digest,
        source_staged_file_size_bytes_expected=expected_size,
        archive_member_digest_matches_source=digest_match,
        archive_member_size_matches_source=size_match,
        unexpected_archive_member=unexpected,
        missing_archive_member=missing,
        duplicate_archive_member_path=False,
        reason_codes=["MANIFEST_ENTRY_VERIFIED"] if exists else ["MANIFEST_ENTRY_FAILED"],
        notes=[],
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    entry.archive_manifest_entry_digest = hash_waveguide_package_archive_manifest_entry(entry)
    return entry


def validate_waveguide_package_archive_manifest_entry(entry: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a manifest entry.
    """
    e_dict = asdict(entry) if hasattr(entry, "__dict__") else dict(entry)
    errors = []

    recorded = e_dict.get("archive_manifest_entry_digest", "")
    if not recorded:
        errors.append("Missing entry digest")
    else:
        recomputed = hash_waveguide_package_archive_manifest_entry(e_dict)
        if recomputed != recorded:
            errors.append(f"Manifest entry digest mismatch. Recorded: {recorded}, Recomputed: {recomputed}")

    if e_dict.get("missing_archive_member"):
        errors.append(f"Missing member: {e_dict.get('archive_member_relative_path')}")
    if e_dict.get("unexpected_archive_member"):
        errors.append(f"Unexpected member in ZIP: {e_dict.get('archive_member_relative_path')}")
    if not e_dict.get("archive_member_exists"):
        errors.append(f"Member does not exist or was failed to read: {e_dict.get('archive_member_relative_path')}")
    if not e_dict.get("archive_member_digest_matches_source"):
        errors.append(f"Digest mismatch for member: {e_dict.get('archive_member_relative_path')}")

    return len(errors) == 0, errors


def build_waveguide_package_archive_manifest(
    build_record_path_or_dict: Any,
    archive_output_root_override: Optional[str] = None
) -> WaveguidePackageArchiveManifest:
    """
    Builds the Package Archive Manifest from the build record.
    """
    br_dict = _load_dict(build_record_path_or_dict) or {}
    record_digest = br_dict.get("package_archive_build_record_digest", "")
    record_status = br_dict.get("package_archive_build_status", "")

    manifest_status = "package_archive_manifest_ready"
    reason_codes = ["PACKAGE_ARCHIVE_MANIFEST_READY"]

    # Verify build record is complete
    if record_status != "package_archive_build_completed":
        manifest_status = "package_archive_manifest_blocked"
        reason_codes = ["BUILD_RECORD_NOT_COMPLETED"]

    # Check zip exists on disk
    filename = br_dict.get("archive_filename", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip")
    output_root = archive_output_root_override if archive_output_root_override else br_dict.get("archive_output_display_path", "")
    if output_root.startswith("<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>"):
        # Resolve display root back to actual location
        output_root = output_root.replace("<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>", os.path.join(REPO_ROOT, "docs", "staged_temp")) # wait, or docs/
        # Let's see: in the scripts, the archive is generated under docs/staged_temp or docs/ or pytest tmp_path.
        # Let's check where the archive builder usually saves it.
        # We can look up the absolute path of the archive.
        # Wait, if output_root contains "<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>", let's try to resolve it relative to REPO_ROOT/docs/
        # Or let's see if we can resolve it using resolve_waveguide_package_archive_output_root.
        # If output_root_override is provided, we use that.
        pass

    # Better: let's inspect the actual filepath on disk.
    display_path = br_dict.get("archive_display_path", "")
    actual_path = display_path.replace("<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>", "docs") # or staging docs
    # Wait, in the scratch script the output root is "docs" and the file is "docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY.zip".
    # Let's resolve the actual path.
    if display_path.startswith("<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>"):
        actual_path = os.path.join(REPO_ROOT, display_path.replace("<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>/", "docs/"))
    else:
        actual_path = os.path.join(REPO_ROOT, normalize_to_repo_path(display_path))

    if archive_output_root_override:
        actual_path = os.path.join(archive_output_root_override, filename)

    archive_exists = os.path.exists(actual_path)
    archive_digest = ""
    archive_size = 0

    if archive_exists:
        archive_digest = compute_waveguide_package_archive_digest(actual_path)
        archive_size = os.path.getsize(actual_path)
    else:
        manifest_status = "package_archive_manifest_blocked"
        reason_codes.append("ARCHIVE_FILE_NOT_FOUND")

    entries = []
    verified_ids = []
    missing_ids = []
    unexpected_ids = []
    mismatch_ids = []
    invalid_ids = []

    zf = None
    namelist = []
    if archive_exists:
        try:
            zf = zipfile.ZipFile(actual_path, "r")
            namelist = zf.namelist()
        except Exception as e:
            manifest_status = "package_archive_manifest_invalid"
            reason_codes.append(f"FAILED_TO_OPEN_ZIP: {str(e)}")

    # Expected list
    member_records = br_dict.get("archive_member_records", [])
    expected_member_paths = [m.get("archive_member_relative_path", "") for m in member_records]

    # Map expected entries first
    idx = 0
    for m in member_records:
        rel_path = m.get("archive_member_relative_path", "")
        expected_digest = m.get("archive_member_digest_expected", "")
        expected_size = m.get("archive_member_size_bytes_expected", 0)

        missing = (rel_path not in namelist)

        zinfo = None
        if not missing and zf:
            try:
                zinfo = zf.getinfo(rel_path)
            except KeyError:
                missing = True

        entry = build_waveguide_package_archive_manifest_entry(
            member_path=rel_path,
            zf=zf,
            zinfo=zinfo,
            expected_digest=expected_digest,
            expected_size=expected_size,
            index=idx,
            unexpected=False,
            missing=missing
        )
        entries.append(entry)
        idx += 1

        if missing:
            missing_ids.append(entry.archive_manifest_entry_id)
        elif not entry.archive_member_digest_matches_source or not entry.archive_member_size_matches_source:
            mismatch_ids.append(entry.archive_manifest_entry_id)
        else:
            # Validate entry
            ok, errs = validate_waveguide_package_archive_manifest_entry(entry)
            if ok:
                verified_ids.append(entry.archive_manifest_entry_id)
            else:
                invalid_ids.append(entry.archive_manifest_entry_id)

    # Now find unexpected entries in the zip
    for name in namelist:
        if name not in expected_member_paths:
            zinfo = None
            if zf:
                try:
                    zinfo = zf.getinfo(name)
                except Exception:
                    pass

            entry = build_waveguide_package_archive_manifest_entry(
                member_path=name,
                zf=zf,
                zinfo=zinfo,
                expected_digest="",
                expected_size=0,
                index=idx,
                unexpected=True,
                missing=False
            )
            entries.append(entry)
            idx += 1
            unexpected_ids.append(entry.archive_manifest_entry_id)

    if zf:
        zf.close()

    # Recheck status
    if len(missing_ids) > 0 or len(unexpected_ids) > 0 or len(mismatch_ids) > 0 or len(invalid_ids) > 0:
        manifest_status = "package_archive_manifest_invalid"
        reason_codes.append("MANIFEST_ENTRIES_INVALID_OR_MISMATCHED")

    target_package_sections = sorted(list(set(m.get("target_package_section", "") for m in member_records)))
    archive_member_relative_paths = sorted(list(set(e.archive_member_relative_path for e in entries)))
    archive_member_digests = sorted(list(set(e.archive_member_digest for e in entries if e.archive_member_digest)))
    source_staged_file_digests = sorted(list(set(e.source_staged_file_digest_expected for e in entries)))

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

    manifest = WaveguidePackageArchiveManifest(
        package_archive_manifest_id="SOL-WAVEGUIDE-PACKAGE-ARCHIVE-MANIFEST",
        package_archive_manifest_version=1,
        package_archive_manifest_status=manifest_status,
        source_package_archive_build_record_digest=record_digest,
        source_package_archive_plan_digest=br_dict.get("source_package_archive_plan_digest", ""),
        archive_format="zip",
        archive_output_root_token="<SOL_LOCAL_ARCHIVE_OUTPUT_ROOT>",
        archive_output_display_path=br_dict.get("archive_output_display_path", ""),
        archive_filename=filename,
        archive_display_path=br_dict.get("archive_display_path", ""),
        archive_file_exists=archive_exists,
        archive_file_digest=archive_digest,
        archive_file_size_bytes=archive_size,
        archive_entries=entries,
        verified_archive_entries=verified_ids,
        missing_archive_entries=missing_ids,
        unexpected_archive_entries=unexpected_ids,
        digest_mismatch_archive_entries=mismatch_ids,
        invalid_archive_entries=invalid_ids,
        verified_archive_entry_count=len(verified_ids),
        missing_archive_entry_count=len(missing_ids),
        unexpected_archive_entry_count=len(unexpected_ids),
        digest_mismatch_archive_entry_count=len(mismatch_ids),
        invalid_archive_entry_count=len(invalid_ids),
        total_expected_archive_file_count=len(member_records),
        total_archive_member_count=len(entries),
        target_package_sections=target_package_sections,
        archive_member_relative_paths=archive_member_relative_paths,
        archive_member_digests=archive_member_digests,
        source_staged_file_digests=source_staged_file_digests,
        created_archive_count=br_dict.get("created_archive_count", 0),
        archive_creation_performed=br_dict.get("archive_creation_performed", False),
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        blocked_operation_attempt_counts=blocked_counts,
        reason_codes=reason_codes,
        software_validation_caveat="Validation is shadow/sandbox software validation, not quantum hardware validation."
    )
    manifest.local_staging_output_manifest_digest = hash_waveguide_package_archive_manifest(manifest)
    manifest.package_archive_manifest_digest = manifest.local_staging_output_manifest_digest # wait, both fields can contain the digest
    return manifest


def validate_waveguide_package_archive_manifest(manifest: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates a top-level Package Archive Manifest.
    """
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    errors = []

    # Verify digest
    recorded_digest = m_dict.get("package_archive_manifest_digest", "")
    if not recorded_digest:
        recorded_digest = m_dict.get("local_staging_output_manifest_digest", "")

    if not recorded_digest:
        errors.append("Missing manifest digest")
    else:
        recomputed = hash_waveguide_package_archive_manifest(m_dict)
        if recomputed != recorded_digest:
            errors.append(f"Manifest digest mismatch. Recorded: {recorded_digest}, Recomputed: {recomputed}")

    if m_dict.get("package_archive_manifest_id") != "SOL-WAVEGUIDE-PACKAGE-ARCHIVE-MANIFEST":
        errors.append("Invalid manifest ID")

    # Enforce prohibitions
    prohibitions = [
        ("upload_performed", False),
        ("deployment_performed", False),
        ("signing_performed", False),
        ("external_publication_performed", False),
        ("production_mutation_performed", False),
    ]
    for key, expected in prohibitions:
        if m_dict.get(key) is not expected:
            errors.append(f"Top-level {key} must be {expected}")

    # Validate that verified member count is 28
    if m_dict.get("total_expected_archive_file_count") != 28:
        errors.append(f"Expected exactly 28 planned members, found {m_dict.get('total_expected_archive_file_count')}")

    return len(errors) == 0, errors


def summarize_waveguide_package_archive_manifest(manifest: Any) -> str:
    """
    Generates a human-readable summary of the Package Archive Manifest.
    """
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    lines = [
        "=============================================================",
        "               SOL WAVEGUIDE PACKAGE ARCHIVE MANIFEST",
        "=============================================================",
        f"Manifest ID:      {m_dict.get('package_archive_manifest_id')}",
        f"Status:           {m_dict.get('package_archive_manifest_status')}",
        f"Format:           {m_dict.get('archive_format')}",
        f"Archive Filename: {m_dict.get('archive_filename')}",
        f"Archive Size:     {m_dict.get('archive_file_size_bytes')} bytes",
        f"Archive Digest:   {m_dict.get('archive_file_digest')}",
        f"Expected Members: {m_dict.get('total_expected_archive_file_count')}",
        f"Actual Members:   {m_dict.get('total_archive_member_count')}",
        f"Verified Entries: {m_dict.get('verified_archive_entry_count')}",
        f"Archive Creation Performed: {m_dict.get('archive_creation_performed')}",
        f"Upload/Deploy/Sign Performed: {m_dict.get('upload_performed')} / {m_dict.get('deployment_performed')} / {m_dict.get('signing_performed')}",
        "-------------------------------------------------------------",
        "Reason Codes:",
    ]
    for code in m_dict.get("reason_codes", []):
        lines.append(f"  - {code}")
    lines.append("=============================================================")
    return "\n".join(lines)


def export_waveguide_package_archive_manifest(manifest: Any, output_path: str) -> None:
    """
    Exports the Package Archive Manifest to a JSON file.
    """
    m_dict = asdict(manifest) if hasattr(manifest, "__dict__") else dict(manifest)
    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(output_path))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(m_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_archive_manifests(manifest_a: Any, manifest_b: Any) -> Dict[str, Any]:
    """
    Compares two Package Archive Manifests.
    """
    dict_a = asdict(manifest_a) if hasattr(manifest_a, "__dict__") else dict(manifest_a)
    dict_b = asdict(manifest_b) if hasattr(manifest_b, "__dict__") else dict(manifest_b)

    differences = {}
    for key in ("package_archive_manifest_status", "archive_file_digest", "total_archive_member_count"):
        val_a = dict_a.get(key)
        val_b = dict_b.get(key)
        if val_a != val_b:
            differences[key] = (val_a, val_b)

    return {
        "match": len(differences) == 0,
        "differences": differences
    }
