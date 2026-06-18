# SOL Waveguide Package Archive Builder

## Purpose
The Package Archive Builder handles the physical compilation of the local ZIP archive candidate containing the approved staged files.

## Inputs & Outputs
* **Input**: `docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_PLAN.json`
* **Output**: `docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_BUILD_RECORD.json`

## Archive Safety Rules
* Requires `operator_approved: true`.
* Requires `local_archive_scope_confirmed: true`.
* Rejects root directories (repository root, filesystem root, home directory) as output path target.
* Writes ZIP with fixed DOS timestamp `(1980, 1, 1, 0, 0, 0)` for determinism.

## Caveat
Validation is shadow/sandbox software validation, not quantum hardware validation.
