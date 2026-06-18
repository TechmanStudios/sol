# SOL Waveguide Distribution Package Manifest

The **SOL Waveguide Distribution Package Manifest** is the final package-description layer in the waveguide release governance pipeline. It describes the intended package contents, target layout, digest map, section indices, and proof chain references.

This layer represents the complete and verified package description prior to final manifest audits:

```text
Package Assembly Plan Validator / Dry-Run Packager Auditor
→ Distribution Package Manifest (This Step)
→ future Distribution Package Manifest Validator / Final Package Readiness Auditor
```

---

## 1. Purpose & Core Philosophy

The Package Manifest answers:
> *What would the complete SOL Waveguide distribution package contain, where would every file live, and which dry-run audit proves the package layout is safe?*

Like the layers before it, the Package Manifest operates under a strict sandboxed metadata-only boundary:
- **No archives** (ZIPs/tarballs) are created.
- **No files** are copied to simulated package folders.
- **No directories** are created on disk.
- **No uploads** or publication acts are triggered.
- **No signing** or production state mutations are made.

---

## 2. Input Integration & Flow

The manifest consumes the **Package Dry-Run Audit Report** (`docs/SOL_WAVEGUIDE_PACKAGE_DRY_RUN_AUDIT_REPORT.json`). It verifies:
- The dry-run report validates successfully.
- The dry-run report status is verified (`PACKAGE_DRY_RUN_VERIFIED`).
- The source catalog digest and assembly plan digests are preserved to maintain the cryptographic proof chain.

---

## 3. Package Content Entry Schema

Each simulated file maps to a **Package Content Entry** (`WaveguideDistributionPackageContentEntry`):

| Field | Description |
|---|---|
| `package_content_entry_id` | Deterministic content entry ID. |
| `source_artifact_path` | Source repository path. |
| `source_artifact_name` | Filename (basename). |
| `source_artifact_digest` | SHA256 file contents digest. |
| `source_artifact_type` | Type (e.g. `release_manifest`, `pytest_suite`). |
| `source_artifact_format` | File format (e.g. `json`, `markdown`, `python`). |
| `source_package_role` | Associated package role. |
| `rc_scope` | Release candidate scope (`RC1`, `RC2`, `Shared`). |
| `candidate_level` | Level associated with entry. |
| `target_package_path` | Simulated package destination path. |
| `target_package_section` | Section (`docs/`, `proof/`, `source/`, `tests/`). |
| `dry_run_case_digest` | Digest of the dry-run case verifying this mapping. |
| `layout_entry_digest` | Digest of the matching layout plan entry. |
| `include_in_package_manifest` | Flag indicating inclusion in manifest. |
| `manifest_entry_status` | Status code (`package_content_ready`). |
| `artifact_size_bytes` | File size in bytes from the Certified Catalog. |
| `is_proof_artifact` | Section check for `proof/`. |
| `is_documentation_artifact` | Section check for `docs/`. |
| `is_code_artifact` | Section check for `source/`. |
| `is_test_artifact` | Section check for `tests/`. |
| `is_deployment_artifact` | Rejection safety flag. |
| `is_signing_artifact` | Rejection safety flag. |
| `allowed_distribution_channels` | Channels allowed for publication. |
| `blocked_distribution_channels` | Channels blocked. |
| `reason_codes` | List of reason code string tokens. |
| `notes` | Optional notes. |
| `software_validation_caveat` | Shadow/sandbox caveat statement. |
| `package_content_entry_digest` | SHA256 digest of this entry. |

---

## 4. Top-Level Package Manifest Schema

The top-level manifest structure (`WaveguideDistributionPackageManifest`) catalogs:
- **Digest Map**: List mapping target paths to source paths and digests, sorted by `target_package_path`.
- **Layout Map**: Dict mapping sections to sorted lists of target paths.
- **Section Manifests**: Detailed metadata (entry count, paths, file digests, case digests) sorted by sections:
  - `proof_artifact_manifest` (`proof/`)
  - `documentation_artifact_manifest` (`docs/`)
  - `source_artifact_manifest` (`source/`)
  - `test_artifact_manifest` (`tests/`)
- **Blocked Operations**: Counter mapping showing that zero violations of archiving, copying, uploading, signing, and deploying occurred.

---

## 5. Deterministic Hashing & Self-Reference Exclusions

Stable SHA256 hashing is achieved by canonical JSON sorting (keys sorted):
- `package_content_entry_digest` is popped from a content entry before hashing.
- `distribution_package_manifest_digest` is popped from the manifest before hashing.

---

## 6. Caveats & Limitations

- **Software Validation Caveat**: *"Validation is shadow/sandbox software validation, not quantum hardware validation."*
- **Limitations**: The manifest describes a future package layout structure but does not verify actual file contents on the filesystem at runtime, nor does it guarantee the target paths are writeable.

---

## 7. Next Recommended Build Step

The next recommended governance bridge is the:
```text
Distribution Package Manifest Validator / Final Package Readiness Auditor
```
That step will independently reload the `SOL_WAVEGUIDE_DISTRIBUTION_PACKAGE_MANIFEST.json`, recompute all content entry digests, verify the dry-run audit report reference, validate blocked operation counts, and produce a final package-readiness audit report.
