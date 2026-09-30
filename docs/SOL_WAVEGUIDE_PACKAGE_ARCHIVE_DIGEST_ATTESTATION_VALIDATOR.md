# SOL Waveguide Package Archive Digest Attestation Validator

## Purpose
The Digest Attestation Validator independently audits the Digest Attestation, recomputing all digests, verifying the signing gate, and producing a formal attestation audit report.

## Inputs & Outputs
* **Input**: `docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION.json`
* **Output**: `docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION_AUDIT_REPORT.json`

## Safety Boundaries
* Recomputes all statement digests independently.
* Audits the governance source chain references to ensure they are unbroken.
* Asserts that no real private-key signing or credential access was used.
* Excludes self-referential digest fields from hash inputs.

## Caveat
Validation is shadow/sandbox software validation, not quantum hardware validation.
