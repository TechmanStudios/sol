# SOL Waveguide Controlled Local Staging Runner

## Purpose
The Controlled Local Staging Runner executes the first real filesystem operation in the package pipeline. Consuming the staging plan, it creates target directories and copies exactly the 28 approved source files to the designated target paths within a verified local staging root.

## Input Artifacts
- `docs/SOL_WAVEGUIDE_PACKAGE_CONTROLLED_LOCAL_STAGING_PLAN.json`

## Output Artifacts
- `docs/SOL_WAVEGUIDE_PACKAGE_CONTROLLED_LOCAL_STAGING_RUN_RECORD.json`
- `docs/SOL_WAVEGUIDE_PACKAGE_CONTROLLED_LOCAL_STAGING_RUNNER.md` (this file)

## Filesystem Safety Model
Staging directory creation and file copies are permitted **only** when all of the following gates are satisfied:
1. `operator_approved` is explicitly passed as `True`.
2. `local_filesystem_scope_confirmed` is explicitly passed as `True`.
3. The staging root path is explicitly provided and validated as safe:
   - Must not equal the repository root directory (`REPO_ROOT`).
   - Must not equal the user home directory (`~`).
   - Must not equal any filesystem drive/partition root (e.g. `C:/` or `/`).
   - Must be normalized to forward slashes `/`.
4. Target paths must resolve strictly inside the staging root (no parent traversal `../` escape).
5. Only the 28 planned and approved files can be copied.

If any check fails, the runner returns a blocked run record and performs no file mutations.

## Self-Referential Digest Handling
- Staging entry copying calculates actual source digests and compares them with expected digests.
- For self-referential files (such as `docs/SOL_WAVEGUIDE_CERTIFIED_ARTIFACT_CATALOG.json`), the expected digest recorded in the plan represents the base hash (excluding its own entry digest), whereas the actual file on disk contains the written entry digest. To resolve this circular dependency, the runner verifies that the staged file matches the actual source file in the repository.

## Hashing and Exclusions
- `local_staging_copy_record_digest` is popped prior to hashing copy records.
- `controlled_local_staging_run_record_digest` is popped prior to hashing the top-level run record.

## Governance Boundaries
The runner does not:
- Perform compression or archive creation of any kind (no ZIP/tarball).
- Upload, sign, deploy, or publish artifacts.
- Mutate files in the repository.
- Mutate production state.

> [!NOTE]
> All validation is shadow/sandbox software validation, not real quantum hardware validation.
