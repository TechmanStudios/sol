# SOL Waveguide Local Staging Output Manifest

## Purpose
The Local Staging Output Manifest scans the physical output staging directory after a run. It indexes the files found on disk, recording relative paths, file sizes, and recomputed SHA256 digests. It matches these files against the run record, checking for missing or unexpected files, and verifying sizes and digests.

No files are copied or mutated by this module.

## Input Artifacts
- `docs/SOL_WAVEGUIDE_PACKAGE_CONTROLLED_LOCAL_STAGING_RUN_RECORD.json`

## Output Artifacts
- `docs/SOL_WAVEGUIDE_PACKAGE_LOCAL_STAGING_OUTPUT_MANIFEST.json`
- `docs/SOL_WAVEGUIDE_PACKAGE_LOCAL_STAGING_OUTPUT_MANIFEST.md` (this file)

## Scanning and Matching Rules
- **Missing Files**: If a file described in the copy records is missing from disk, it is flagged as `missing_file` with status `local_staging_output_missing`.
- **Unexpected Files**: Any untracked file found in the staging root that was not in the copy records is flagged as `unexpected_file` with status `local_staging_output_unexpected`.
- **Digest Verification**: Staged file digests are recomputed using standard SHA256 hashing. For self-referential files, the manifest checks if the staged file matches the actual source file's digest recorded in the copy record.
- **Boundaries**: The manifest propagates all directory creation/copy counts and blocked operation counts from the run record.

## Hashing and Exclusions
- `local_staging_output_entry_digest` is popped prior to hashing output entries.
- `local_staging_output_manifest_digest` is popped prior to hashing the top-level manifest.

> [!NOTE]
> All validation is shadow/sandbox software validation, not real quantum hardware validation.
