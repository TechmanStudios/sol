# SOL Waveguide Governed Compiler Session Registry

This document defines the **Governed Compiler Session Registry** for the SOL Waveguide compiler sessions. The Session Registry indexes verified session cases (session proof capsules) from the verifier report into a canonical, release-level history catalog.

---

## 1. Purpose of the Session Registry

The Session Registry compiles multiple verified session records into a single release-level proving artifact:

```text
Governed Compiler Session Verifier
→ Governed Compiler Session Registry (This Step)
→ future Release Certification Bundle
```

It acts as a release-level registry, verifying that all executed and rejection-verified session verification cases validate successfully, and indexing them by compiler profiles, pass sequences, handler IDs, and Release Candidates.

---

## 2. Schemas and Specifications

### Registry Entry Schema
*   `session_registry_entry_id`: Unique identifier for the registry entry (e.g. `SOL-WAVEGUIDE-SESSION-REGISTRY-ENTRY-{rc_id}-{compiler_profile}`).
*   `rc_id`: Release Candidate ID (`SOL-WAVEGUIDE-RC1` or `SOL-WAVEGUIDE-RC2`).
*   `candidate_level`: Level of the candidate (`foundation` or `governed_execution_stack`).
*   `compiler_profile`: Compiler profile.
*   `requested_pass_sequence`: List of passes requested.
*   `session_verification_status`: Status of the verified case mapped to registry entry status (`session_registered` or `session_rejection_registered`).
*   `invocation_status`: Envelope invocation status.
*   `invocation_record_path`: Path reference to the invocation record.
*   `invocation_record_digest`: Reference record digest.
*   `session_case_digest`: Reference verifier case digest.
*   `trace_ledger_digest` / `replay_report_digest` / `final_output_payload_digest`: System-level digest links.
*   `executed_pass_count` / `rejected_pass_count`: Action counts.
*   `verified_execution_count` / `verified_rejection_count` / `failed_replay_count`: Verification metrics.
*   `handler_ids_used`: Handler IDs utilized in the session.
*   `reason_codes` / `software_validation_caveat`: Policy logs.
*   `registry_entry_digest`: Entry signature.

### Top-Level Registry Schema
*   `registry_id`: Full registry identifier (`SOL-WAVEGUIDE-GOVERNED-COMPILER-SESSION-REGISTRY`).
*   `registry_version`: Catalog version (`1`).
*   `registry_status`: Verification status (`session_registry_valid`, `session_registry_blocked`).
*   `source_session_verifier_report_digest`: Reference session verifier report digest.
*   `entries`: Key-sorted list of registry entries.
*   `registered_sessions` / `registered_rejection_sessions`: Playback entry ID lists.
*   `blocked_sessions` / `invalid_sessions`: Error entry ID lists.
*   `registered_session_count` / `registered_rejection_session_count`: Metric counts.
*   `blocked_session_count` / `invalid_session_count`: Error counts.
*   `rc1_session_count` / `rc2_session_count`: Scope counts.
*   `compiler_profiles_indexed`: Sorted unique list of compiler profiles.
*   `pass_sequences_indexed`: Sorted unique list of pass sequences.
*   `handler_ids_indexed`: Sorted unique list of handler IDs utilized across all sessions.
*   `invocation_record_digests` / `session_case_digests` / `trace_ledger_digests` / `replay_report_digests` / `final_output_payload_digests`: Key-sorted aggregate digest lists.
*   `software_validation_caveat` / `reason_codes`: Policy logs.
*   `registry_digest`: Top-level registry catalog signature.

---

## 3. Entry Mapping and Validation Rules

### Status Mapping
Verifier verification case statuses are mapped to registry entry statuses:
*   `session_verified` $\to$ `session_registered`
*   `session_rejection_verified` $\to$ `session_rejection_registered`
*   `session_blocked` $\to$ `session_blocked`
*   Other states $\to$ `session_invalid`

### Entry Validation Rules
*   **Registered entries**: Must have `session_verification_status = session_registered`, `invocation_status = invocation_verified`, `executed_pass_count >= 1`, `verified_execution_count >= 1`, and `failed_replay_count = 0`.
*   **Rejection-registered entries**: Must have `session_verification_status = session_rejection_registered`, `invocation_status = invocation_rejected_verified`, `executed_pass_count = 0`, `rejected_pass_count >= 1`, `verified_rejection_count >= 1`, and `failed_replay_count = 0`.
*   **Cavats & Signatures**: Entry must include the software validation caveat and its `registry_entry_digest` must validate.

---

## 4. Top-Level Registry Validation Rules

The top-level registry is valid only when:
*   Every included entry validates successfully.
*   All counts (sessions, rejection sessions, blocked, invalid, RC1, RC2) exactly match the entries.
*   All compiler profiles, pass sequences, and handler IDs are indexed and sorted.
*   All nested digest lists are sorted, unique, and present.
*   The registry catalog signature `registry_digest` validates.

---

## 5. Deterministic Hashing Requirements

*   Serializes all keys using canonical, sorted JSON serialization.
*   Preserves requested pass sequence order inside each entry.
*   Sorts registry entries by stable keys: `rc_id`, `compiler_profile`, `session_verification_status`, and `invocation_record_digest`.
*   Strips self-referential digest fields (`registry_entry_digest` and `registry_digest`) during hashing.
*   Uses **SHA256** digests.

---

## 6. Software Validation Caveat and Limitations

*   **Sandbox Caveat**: Validation is shadow/sandbox software validation, not quantum hardware validation.
*   **Non-Production Registry**: The registry indexes verified transaction proof capsules. It does not certify releases or package them into production release bundles.
