# SOL Waveguide Package Archive Manifest

## Purpose
The Package Archive Manifest scans the compiled ZIP file and catalogs member metadata (names, compression types, actual sizes, and digests).

## Inputs & Outputs
* **Input**: `docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_BUILD_RECORD.json`
* **Output**: `docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_MANIFEST.json`

## Manifest Hashing & Verification
* Excludes self-referential `package_archive_manifest_digest` from its own hash input.
* Scans ZIP members independently, recomputing SHA256 hashes of de-compressed bytes.

## Caveat
Validation is shadow/sandbox software validation, not quantum hardware validation.
