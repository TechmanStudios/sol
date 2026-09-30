# SOL Waveguide Controlled Local Staging Plan

## Purpose
The Controlled Local Staging Plan module defines a deterministic layout mapping for staging the 28 approved package artifacts into an explicitly approved local staging root. It maps source artifacts from the workspace into their relative target locations inside a symbolic staging root placeholder `<SOL_LOCAL_STAGING_ROOT>`. 

This is a **metadata-only planning phase**. No physical file operations, directory creations, or copies are performed by this module.

## Input Artifacts
- `docs/SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_PHYSICAL_EXECUTION_GATE_AUDIT_REPORT.json` (Canonical preflight report)
- `docs/SOL_WAVEGUIDE_DISTRIBUTION_PACKAGE_ASSEMBLY_PLAN.json` (Package layout plan containing the 28 layout entries)

## Output Artifacts
- `docs/SOL_WAVEGUIDE_PACKAGE_CONTROLLED_LOCAL_STAGING_PLAN.json`
- `docs/SOL_WAVEGUIDE_PACKAGE_CONTROLLED_LOCAL_STAGING_PLAN.md` (this file)

## Schema & Hashing
The staging plan contains:
- `controlled_local_staging_plan_id`: `"SOL-WAVEGUIDE-PACKAGE-CONTROLLED-LOCAL-STAGING-PLAN"`
- `controlled_local_staging_plan_version`: `1`
- `controlled_local_staging_plan_status`: Status of the plan (`package_local_staging_plan_ready` or `package_local_staging_plan_blocked`)
- `local_staging_entries`: An array of individual staging entry mappings.
- Aggregate counts, sorted sections, scopes, and paths.

Deterministic hashing uses the standard `hash_data` function. Self-referential digest fields are popped prior to hashing:
- `local_staging_entry_digest` is popped from entry hashes.
- `controlled_local_staging_plan_digest` is popped from the top-level plan hash.

## Governance Guards & Prohibitions
To preserve governance boundaries, the plan verifies:
- Target paths remain strictly inside the staging root (no absolute targets, no empty paths).
- No parent directory traversal (`../`) is allowed.
- No duplicate target path mappings (collision check).
- Operator approval and local filesystem scope confirmation flags are set to required.
- Staging allowance flags are restricted:
  - `directory_creation_allowed` = `True`
  - `file_copy_allowed` = `True`
  - `archive_creation_allowed` = `False`
  - `upload_allowed` = `False`
  - `deployment_allowed` = `False`
  - `signing_allowed` = `False`
  - `external_publication_allowed` = `False`
  - `production_mutation_allowed` = `False`

> [!NOTE]
> All validation is shadow/sandbox software validation, not real quantum hardware validation.
