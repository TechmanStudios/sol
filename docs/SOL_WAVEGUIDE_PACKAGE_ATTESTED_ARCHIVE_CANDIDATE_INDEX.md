# SOL Waveguide Attested Archive Candidate Index

## Purpose
The Attested Archive Candidate Index registers verified, digest-attested archive candidates as release-ready candidates in the local waveguide package registry.

## Inputs & Outputs
* **Input**: `docs/SOL_WAVEGUIDE_PACKAGE_ARCHIVE_DIGEST_ATTESTATION_AUDIT_REPORT.json`
* **Output**: `docs/SOL_WAVEGUIDE_PACKAGE_ATTESTED_ARCHIVE_CANDIDATE_INDEX.json`

## Safety Boundaries
* Preserves the strict separation between digest attestation and real private-key signing.
* Verifies that no real key signing, upload, publication, or deployment occurred.
* Restricts candidates to local registry scope.
* Excludes self-referential digest fields from hash inputs.

## Caveat
Validation is shadow/sandbox software validation, not quantum hardware validation.
