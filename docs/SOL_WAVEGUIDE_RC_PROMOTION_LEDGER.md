# SOL Waveguide Release Candidate Signed Promotion Ledger

This document defines the release candidate promotion ledger system, detailing the deterministic hashing strategy, promotion record format, verification status rules, and required artifacts.

---

## 1. Purpose of the Promotion Ledger

The Signed RC Promotion Ledger seals the results of the Release Candidate Release Gate into stable, replayable, and machine-verifiable records. By generating a canonical promotion record and hashing it, the promotion ledger establishes a tamper-proof receipt proving that:
1. The candidate manifest was correctly built and validated.
2. The release gate evaluated the candidate as ready for promotion.
3. All required documentation and proof claims are present.
4. Regression test campaigns executed sequentially and successfully.

This module provides the transition layer between the release-gate evaluation and the future court-supervised promotion flow.

```text
RC Release Gate and Delta Audit Harness
\u2192 Signed RC Promotion Ledger
\u2192 future Court-Supervised RC Promotion Flow
```

---

## 2. Hashing Strategy

To ensure deterministic verification independent of the running host or local directory structure:
- **Canonical JSON Serialization**: Dictionaries and objects are serialized using key-sorted, compact JSON (no extraneous whitespace).
- **Separator Normalization**: File paths are stored as repository-relative paths (e.g. `docs/SOL_WAVEGUIDE_RC1_MANIFEST.json`) with forward slashes (`/`), preventing absolute path variations from affecting hashes.
- **Timestamp Exclusions**: Verification is based on static content state rather than ephemeral execution times.
- **Digest Self-Reference Exclusion**: The `record_digest` property itself is popped/ignored during computation to avoid cyclic references.
- **Algorithm**: Standard `sha256` hashing is used.

---

## 3. Promotion Status Rules

A candidate is assigned one of three promotion statuses:

| Status | Verdict | Criteria |
| :--- | :--- | :--- |
| **`promotion_ready`** | `release_ready` | Release gate verification passes, required documentation exists, and Digests match. |
| **`promotion_warning`** | `warning` | Release gate issues warnings (unexpected features), but other checks pass. |
| **`promotion_blocked`** | `blocked` | Release gate blocks the candidate, required documentation is missing, or digests mismatch. |

---

## 4. Promotion Record Model Fields

Each promotion record contains the following properties:

| Field | Type | Description |
| :--- | :--- | :--- |
| `record_id` | `str` | Canonical record identifier (e.g. `SOL-WAVEGUIDE-RC-PROMOTION-RECORD-RC1`). |
| `rc_id` | `str` | Candidate Release Candidate ID (e.g. `SOL-WAVEGUIDE-RC1`). |
| `candidate_level` | `str` | Level identifier (`RC1` or `RC2`). |
| `manifest_path` | `str` | Repository-relative path to the candidate manifest JSON. |
| `manifest_digest` | `str` | Deterministic SHA256 hash of the candidate manifest. |
| `release_gate_verdict` | `str` | Release gate evaluation verdict (`release_ready`, `warning`, `blocked`). |
| `release_gate_reason_codes` | `List[str]` | Reason codes returned by the release gate evaluation. |
| `release_gate_summary` | `str` | Full plaintext release gate audit summary. |
| `delta_audit_path` | `str` | Repository-relative path to the delta audit JSON. |
| `delta_audit_digest` | `str` | Deterministic SHA256 hash of the delta audit report. |
| `proof_ledger_paths` | `List[str]` | Paths to documented mathematical proofs. |
| `proof_claims` | `Dict` | Structured representation of the claims covered (claims 11-15 for RC2, inherited for RC1). |
| `regression_summary` | `str` | Human-readable text report of the latest sequential regression test results. |
| `artifact_paths` | `List[str]` | List of all verification/documentation artifacts associated with the release. |
| `promotion_authority` | `Dict` | Promotion authority metadata (defaults to pending supervised authority). |
| `promotion_scope` | `str` | Scope of the release (e.g., `"software_sandbox_verification_only"`). |
| `software_validation_caveat` | `str` | Explicit caveat stating validation is software-simulation only. |
| `promotion_status` | `str` | Computed promotion status (`promotion_ready`, `promotion_warning`, `promotion_blocked`). |
| `promotion_reason_codes` | `List[str]` | Verification codes generated during promotion processing. |
| `record_digest` | `str` | SHA256 digest of the canonicalized record. |

---

## 5. Next Recommended Step: Court-Supervised RC Promotion Flow

The next bridge in the release roadmap is the **Court-Supervised RC Promotion Flow**.
A future court-supervised engine will ingest these signed promotion records and route them through multi-ranger consensus sign-offs, verifying that the record's signatures match physical/software ledger audits before promoting candidates.

---

## 6. Scope and Sandbox Caveat

> [!IMPORTANT]
> **SANDBOX CAVEAT & SCOPE LIMITATION**
> All release promotion records, digests, and validation logic are software-simulated checks within a shadow/sandbox compiler model.
> - There is no physical quantum-hardware verification.
> - Execution remains strictly a software model for compiler verification and research.
