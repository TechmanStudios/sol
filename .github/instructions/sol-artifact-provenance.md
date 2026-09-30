# SOL Artifact Provenance and External Archive Policy

## Truth is a graph of artifacts
A claim is only as real as its references.

## Canonical in-repo artifacts
- dashboard HTML (single-file)
- math foundation
- master research log
- external artifacts manifest
- README / run instructions
- agents/instructions/prompts/skills (this kit)

## External archive rule
If an artifact is not in repo, it must be:
- stored externally, and
- referenced in sol_external_artifacts_manifest_v2.md (or matching patterns), and
- mentioned in the run bundle’s “Exports” section.

## No orphan references
If a writeup references:
- a CSV not present,
- a part file without a manifest,
- a historical dashboard build,

then update the external manifest or mark the reference [UNKNOWN] and do not promote claims.

## Artifact inventory section (required in RN/RD)
Every research note must list:
- Local artifacts (present in repo)
- External artifacts (stored elsewhere + manifest reference)
