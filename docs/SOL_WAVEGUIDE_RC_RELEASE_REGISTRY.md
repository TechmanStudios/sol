# SOL Waveguide Release Candidate Release Registry

This document defines the release candidate release registry index, detailing the lookup semantics, entry format, approval rules, and deterministic hashing strategies.

---

## 1. Purpose of the Release Registry

The RC Release Registry and Promotion Index serves as the canonical central directory of verified compiler builds. By cataloging court-approved release candidate verdicts, manifest properties, signed ledger digests, and verification receipts, the registry proves the entire chain-of-trust for the compiler roadmap:

```text
RC Release Gate and Delta Audit Harness
\u2192 Signed RC Promotion Ledger
\u2192 Court-Supervised RC Promotion Flow
\u2192 RC Release Registry / Promotion Index
\u2192 future Runtime Capability Resolver
```

The registry is the machine-verifiable lookup table consumed by downstream capability contracts and loaders.

---

## 2. Hashing Strategy and Self-Reference Exclusion

To ensure digest integrity across machines and platforms:
- **Sorted Keys**: Serialized objects are represented using key-sorted JSON fields.
- **Paths Normalization**: Paths are converted to repository-relative format (e.g. `docs/SOL_WAVEGUIDE_RC_RELEASE_REGISTRY.json`) with forward slashes (`/`).
- **Self-Reference Exclusion**:
  - `registry_entry_digest` is excluded when hashing an individual entry.
  - `registry_digest` is excluded when hashing the top-level registry index.
- **Algorithm**: Standard `sha256` hashing is utilized.

---

## 3. Approval Rules

A release candidate is cataloged as `release_registered` in the index only when:
1. The promotion court verdict is `promotion_approved`.
2. The ranger quorum is `quorum_satisfied`.
3. The court verdict digest matches and validates.
4. The promotion record digest matches and validates.
5. All required documentation and verification artifacts are present on the filesystem.
6. The software-only simulation caveat is present.

If a candidate is rejected or warning at court level, it is assigned `release_blocked` or omitted entirely.

---

## 4. Registry lookup Semantics

Downstream tooling queries this index to retrieve:
- **Approved release lists**: `approved_rc_ids` lists all fully verified and registered candidates.
- **Foundation capabilities lookup**: `latest_foundation_rc` points to the latest stable RC1 release candidate.
- **Governed stack capabilities lookup**: `latest_governed_stack_rc` points to the latest RC2 release candidate.
- **Verifiable digests**: Checks and compares manifest digests (`manifest_digest`) and signature chains.

### Default Lookups
*   **Latest Foundation RC**: `SOL-WAVEGUIDE-RC1`
*   **Latest Governed Execution Stack RC**: `SOL-WAVEGUIDE-RC2`

---

## 5. Next Recommended Step: Runtime Capability Resolver

The next bridge in the release roadmap is the **Runtime Capability Resolver**.
A future resolver module will consume the release registry catalog and translate approved release candidate levels into active runtime compiler constraints, mapping allowed optimization passes and backend execution policies dynamically.

---

## 6. Scope and Sandbox Caveat

> [!IMPORTANT]
> **SANDBOX CAVEAT & SCOPE LIMITATION**
> The release registry, entry digests, and indexing validations run entirely as software checks inside a shadow/sandbox compiler model.
> - There is no physical quantum-hardware verification.
> - Execution remains strictly a software model for compiler verification and research.
