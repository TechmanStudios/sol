# SOL Waveguide Package Assembly Plan Validator / Dry-Run Packager Auditor

The **SOL Waveguide Package Assembly Plan Validator** (also termed the **Dry-Run Packager Auditor**) is an independent validation layer designed to verify that the proposed distribution package layout is safe, deterministic, and fully compliant with distribution safety boundaries.

This layer validates the proposed package layout strictly as metadata. It verifies the pipeline structure before any archiving or packaging occurs:

```text
Distribution Package Assembly Plan
→ Package Assembly Plan Validator / Dry-Run Packager Auditor (This Step)
→ future Distribution Package Manifest
```

---

## 1. Purpose & Design Philosophy

The main purpose of the Dry-Run Packager Auditor is to verify the safety and integrity of the proposed package layout map. It answers:
> *Can the distribution package assembly plan be independently reloaded, verified, and dry-run simulated without mutating release state or performing physical operations?*

To guarantee clean, secure packaging boundaries, the validator enforces a strict sandbox boundary. It simulates package layout assembly solely through deterministic metadata:
- **No ZIP or tarball creation** is performed.
- **No file copying** or filesystem directory structure creation is done.
- **No artifact upload**, external publishing, or deployment occurs.
- **No external key signing** is executed.

---

## 2. Input Consumption & Integration

The auditor accepts and validates two primary inputs:
1. **Distribution Package Assembly Plan** (`docs/SOL_WAVEGUIDE_DISTRIBUTION_PACKAGE_ASSEMBLY_PLAN.json`): Loaded, recomputed, and validated to ensure the layout plan itself has not been tampered with.
2. **Certified Artifact Catalog** (`docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json`): Independently loaded and validated using the `sol_waveguide_certified_artifact_catalog` validation suite.

The validator matches the source catalog digest recorded in the assembly plan against the recomputed digest of the loaded catalog to ensure absolute alignment.

---

## 3. Target Path Safety Rules

To prevent traversal vulnerabilities and preserve safety under simulated environments, every target path must satisfy these strict constraints:
- **Relative Path**: Paths must be relative. Absolute roots (e.g. `/`, `C:/`) are blocked.
- **Forward Slashes Only**: Paths must use `/` as the separator character. Windows backslashes (`\`) are forbidden.
- **No Parent Traversals**: Paths containing `..` or leading/trailing parent components are blocked.
- **No Empty Segments**: Multiple consecutive slashes (`//`) are rejected.
- **Path Collision Detection**: No two verified package layout entries may share the same `target_package_path`.

Unsafe target paths cause the corresponding dry-run audit case to fail and block report certification.

---

## 4. Dry-Run Audit Case Schema

For each package layout entry, a case is evaluated. The case includes the following attributes:

| Field | Description |
|---|---|
| `package_dry_run_case_id` | Deterministic unique case identifier. |
| `package_assembly_plan_id` | Associated assembly plan ID. |
| `package_assembly_plan_path` | Source path of the plan file. |
| `package_assembly_plan_digest_recorded` | Recorded plan digest. |
| `package_assembly_plan_digest_recomputed` | Recomputed plan digest. |
| `package_assembly_plan_digest_match` | Boolean flag indicating a match. |
| `layout_entry_id` | Associated layout entry ID. |
| `layout_entry_digest_recorded` | Recorded layout entry digest. |
| `layout_entry_digest_recomputed` | Recomputed layout entry digest. |
| `layout_entry_digest_match` | Boolean flag indicating a match. |
| `source_artifact_path` | Source path of the repository file. |
| `source_artifact_digest` | SHA256 digest of the source file. |
| `source_artifact_type` | Type classification of the artifact (e.g., `proof_capsule`, `markdown_documentation`). |
| `source_artifact_format` | Format (e.g., `json`, `markdown`, `python`). |
| `source_package_role` | Associated role (e.g., `proof_capsule`, `documentation`, `implementation_source`). |
| `rc_scope` | Scope of the release candidate (`RC1`, `RC2`, `Shared`). |
| `candidate_level` | Level associated (e.g., `candidate_level_1`, `candidate_level_2`). |
| `target_package_path` | Simulated package destination path. |
| `target_package_section` | Destination section (`proof/`, `docs/`, `source/`, `tests/`). |
| `target_path_relative` | Safety flag for relative path check. |
| `target_path_uses_forward_slashes` | Safety flag for separator check. |
| `target_path_has_no_parent_traversal` | Safety flag for parent traversal check. |
| `target_path_has_no_absolute_root` | Safety flag for absolute path check. |
| `target_path_collision_free` | Collision safety check. |
| `include_in_package_plan` | Boolean indicating inclusion flag. |
| `assembly_status` | Plan-level assembly status (`package_layout_ready`). |
| `dry_run_status` | Status code (`package_dry_run_verified`, `package_dry_run_blocked`, `package_dry_run_invalid`). |
| `source_artifact_catalog_digest_recorded` | Catalog digest from plan. |
| `source_artifact_catalog_digest_recomputed` | Recomputed catalog digest. |
| `source_artifact_catalog_digest_match` | Boolean flag indicating a match. |
| `source_artifact_catalog_valid` | Boolean indicating catalog validity. |
| `no_archive_created` | Boundary safety verification flag (true). |
| `no_file_copy_performed` | Boundary safety verification flag (true). |
| `no_upload_performed` | Boundary safety verification flag (true). |
| `no_deployment_performed` | Boundary safety verification flag (true). |
| `no_signing_performed` | Boundary safety verification flag (true). |
| `allowed_distribution_channels` | Lists of verified target distribution channels. |
| `blocked_distribution_channels` | Lists of explicitly blocked distribution channels. |
| `reason_codes` | List of reason code string tokens. |
| `notes` | Optional notes. |
| `software_validation_caveat` | Required validation caveat text. |
| `package_dry_run_case_digest` | SHA256 case digest (self-referential field). |

---

## 5. Top-Level Dry-Run Audit Report Schema

The validator compiles all individual cases into a certified top-level audit report (`SOL_WAVEGUIDE_PACKAGE_DRY_RUN_AUDIT_REPORT`):

- **Report Status**: `package_dry_run_verified` only when every layout entry verifies successfully, all target paths are collision-free and safe, and no deployment or signing files are included.
- **Dry-Run File Map**: Deterministic mapping of source repository paths to package target paths, sorted by `target_package_path` with sequence indexes starting from 1.
- **Dry-Run Section Index**: Sorted lists of target paths categorized under planned sections (`proof/`, `docs/`, `source/`, `tests/`).
- **Forbidden Attempt Counts**: Ensures zero counters for archive creation, file copy, upload, deployment, and signing attempts.

---

## 6. Deterministic Hashing & Self-Reference Exclusions

Deterministic hashing utilizes standard SHA256 canonical JSON serialization (sorted keys):
- For case digests, the `package_dry_run_case_digest` field is popped from the dictionary before computing the digest.
- For report digests, the `package_dry_run_report_digest` field is popped from the dictionary before computing the digest.

This prevents circular self-reference loops and produces stable, reproducible validation signatures.

---

## 7. Sandbox Caveats & Limitations

- **Software Validation Caveat**: *"Validation is shadow/sandbox software validation, not quantum hardware validation."*
- **Limitations**: The dry-run validation checks metadata properties and does not guarantee that files exist on the host filesystem or possess matching filesystem permissions during actual package build. It certifies the logical layout claims, not execution-level media packaging.

---

## 8. Next Recommended Build Step

The next governance bridge is the **Distribution Package Manifest**. That step will produce the final deterministic package manifest describing the package contents, layout, digest map, and verified dry-run report reference, still without actually creating an archive, copying files, uploading, signing, publishing, or deploying anything.
