# SOL Waveguide Package Archive Validator

## Purpose
The Package Archive Validator reloads the manifest, recomputes digests of ZIP archive and its members, enforces boundaries, and compiles the audit report.

## Inputs & Outputs
* **Input**: `docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_MANIFEST.json`
* **Output**: `docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_AUDIT_REPORT.json`

## Audit Verification Rules
* Checks for missing/unexpected members.
* Confirms member digests match staging file digests.
* Confirms operation boundary counts (upload/deployment/signing/production mutation counts are 0).

## Caveat
Validation is shadow/sandbox software validation, not quantum hardware validation.
