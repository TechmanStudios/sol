# SOL Waveguide Release Candidate Court-Supervised Promotion Flow

This document defines the court-supervised promotion verification flow, detailing case records, required ranger panel attestations, quorum rules, verdict criteria, and output schemas.

---

## 1. Purpose of the Court Flow

The Court-Supervised RC Promotion Flow introduces a deterministic verification step before release candidate promotion. It consumes sealed promotion records from the Signed RC Promotion Ledger, constructs a promotion case, routes that case through a panel of five specialized "rangers" for independent verification, calculates quorum, and seals the result into a court verdict record.

```text
Signed RC Promotion Ledger
\u2192 Court-Supervised RC Promotion Flow
\u2192 future RC Release Registry / Promotion Index
```

---

## 2. Ranger Panel and Quorum Rule

### Ranger Panel
The court panel is composed of five required rangers, each representing a separate verification domain:
1.  **`ManifestBoundaryRanger`**: Validates manifest candidate level, manifest paths, and ensures manifest digests match build files.
2.  **`ReleaseGateRanger`**: Checks that the release gate verdict evaluates to `release_ready`.
3.  **`PromotionLedgerRanger`**: Checks that the promotion record status evaluates to `promotion_ready` and that the promotion record's digest is valid.
4.  **`ProofLedgerRanger`**: Validates that all proof claims are present and conservative, and that sandbox caveats exist.
5.  **`RegressionAuditRanger`**: Checks regression campaign records to ensure full sequential regression campaigns ran successfully.

### Quorum Rule
Quorum is strictly deterministic:
*   **Rule**: `all_required_rangers_must_approve`
*   All required rangers must be present (`quorum_satisfied`).
*   All required rangers must return `approved`. Any rejection or missing ranger results in promotion failure.

---

## 3. Verdict Status Rules

| Court Verdict | Quorum Status | Attestation Statuses | Criteria |
| :--- | :--- | :--- | :--- |
| **`promotion_approved`** | `quorum_satisfied` | All required rangers return `approved` | Promotion record is ready, all rangers approve, and caveats are included. |
| **`promotion_warning`** | `quorum_satisfied` | No ranger rejects, but warning emitted | Warnings are present on non-blocking checks. |
| **`promotion_rejected`** | `quorum_failed` or `quorum_satisfied` | Any ranger rejects, or quorum fails | Mismatched digests, missing files, or validation failures. |

---

## 4. Case and Verdict Schemas

### Case Model Fields
*   `case_id`: Canonical case identifier (e.g. `SOL-WAVEGUIDE-RC-PROMOTION-CASE-RC2`).
*   `rc_id`: Candidate Release Candidate ID (e.g. `SOL-WAVEGUIDE-RC2`).
*   `candidate_level`: Level identifier (`RC1` or `RC2`).
*   `promotion_record_path`: Repository-relative path to the signed promotion record JSON.
*   `promotion_record_digest`: SHA256 content digest of the promotion record.
*   `promotion_record_status`: Ledger status (`promotion_ready`, etc.).
*   `court_id`: Court identifier (`SOL-WAVEGUIDE-RC-PROMOTION-COURT`).
*   `required_rangers`: List of required ranger IDs.
*   `quorum_rule`: Quorum rule identifier.
*   `software_validation_caveat`: Software validation caveat string.
*   `case_digest`: SHA256 digest of the canonical key-sorted case content (excluding `case_digest` itself).

### Verdict Model Fields
*   `verdict_id`: Canonical verdict identifier (e.g. `SOL-WAVEGUIDE-RC-COURT-VERDICT-RC2`).
*   `case_id`: Referenced case identifier.
*   `court_verdict`: Final decision (`promotion_approved`, `promotion_rejected`, `promotion_warning`).
*   `quorum_status`: Quorum status (`quorum_satisfied`, `quorum_failed`).
*   `attestations`: List of serialized ranger attestation records.
*   `verdict_digest`: SHA256 digest of the canonical key-sorted verdict content (excluding `verdict_digest` itself).

---

## 5. Next Recommended Step: RC Release Registry / Promotion Index

The next bridge in the release roadmap is the **RC Release Registry / Promotion Index**.
A future index module will maintain a deterministic registry of all court-approved release candidates, manifest digests, signed promotion ledger records, and court verdicts, establishing a central source-of-truth lookup for verified compiler builds.

---

## 6. Scope and Sandbox Caveat

> [!IMPORTANT]
> **SANDBOX CAVEAT & SCOPE LIMITATION**
> All cases, ranger panel attestations, and court verdicts are software-simulated checks within a shadow/sandbox compiler model.
> - There is no physical quantum-hardware verification.
> - Execution remains strictly a software model for compiler verification and research.
