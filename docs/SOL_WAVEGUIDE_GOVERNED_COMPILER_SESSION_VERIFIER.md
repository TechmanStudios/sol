# SOL Waveguide Governed Compiler Session Verifier

This document defines the **Governed Compiler Invocation Replay / Session Verifier** system for the SOL Waveguide compiler sessions. The session verifier consumes session transaction records (invocation envelopes), validates nested artifact digests, verifies pass plan ordering, checks execution and rejection counts, recomputes final output payload digests, and generates session verification reports.

---

## 1. Purpose of the Session Verifier

The Session Verifier completes the compiler session audit trail by validating the transaction envelope's structural integrity:

```text
Governed Compiler Invocation Envelope
→ Governed Compiler Invocation Replay / Session Verifier (This Step)
→ future Governed Compiler Session Registry
```

It ensures that a recorded compiler session was executed in strict accordance with the release candidate's governance policies, capability limits, and safety restrictions, verifying that all execution and rejection steps are fully auditable and replay-verified.

---

## 2. Schemas and Specifications

### Session Verification Case Schema
*   `session_case_id`: Unique identifier for the verification case.
*   `invocation_record_path`: Normalized repository path to the invocation record.
*   `invocation_record_digest`: Record digest read from the JSON envelope.
*   `invocation_record_valid`: Status of record signature verification.
*   `invocation_request_digest`: Reference request digest.
*   `rc_id` / `candidate_level` / `compiler_profile`: Metadata read from the record.
*   `requested_pass_sequence`: Ordered sequence of passes requested.
*   `pass_plan_valid` / `pass_plan_order_preserved`: Booleans validating pass planning order.
*   `capability_resolution_digest`: Digest validating active capability policies.
*   `admission_decision_digests` / `execution_record_digests` / `trace_entry_digests`: Reference digest lists.
*   `trace_ledger_digest` / `replay_report_digest`: System-level digest links.
*   `recorded_final_output_payload_digest`: Output payload digest stored in the record.
*   `recomputed_final_output_payload_digest`: Output payload digest recomputed by the verifier.
*   `executed_pass_count` / `rejected_pass_count`: Action counts from the record.
*   `verified_execution_count` / `verified_rejection_count` / `failed_replay_count`: Replay metrics.
*   `invocation_status`: Envelope status.
*   `session_verification_status`: Final verification status (`session_verified`, `session_rejection_verified`, `session_failed`, or `session_blocked`).
*   `reason_codes` / `notes` / `software_validation_caveat`: Logs and validations.
*   `session_case_digest`: Case signature.

### Top-Level Session Verification Report Schema
*   `session_verification_report_id`: ID of the top-level report.
*   `session_verification_report_version`: Report version.
*   `session_verification_report_status`: Overall report status (`session_verification_report_verified`, `session_verification_report_failed`).
*   `cases`: List of serialized verification cases.
*   `verified_sessions` / `verified_rejection_sessions`: Playback session IDs.
*   `failed_sessions` / `blocked_sessions`: Session failure lists.
*   `verified_session_count` / `verified_rejection_session_count`: Metrics.
*   `failed_session_count` / `blocked_session_count`: Error metrics.
*   `rc1_session_count` / `rc2_session_count`: Scope metrics.
*   `invocation_record_digests` / `trace_ledger_digests` / `replay_report_digests` / `final_output_payload_digests`: Key-sorted aggregate digest lists.
*   `reason_codes` / `software_validation_caveat`: Policy logs.
*   `session_verification_report_digest`: Top-level report signature.

---

## 3. Verification and Safety Policies

### RC1 Foundation Session Verification
*   Under `SOL-WAVEGUIDE-RC1`, sessions containing only foundation passes (e.g. `pipeline_compaction`) verify as `session_verified`.
*   Sessions attempting to execute governed execution stack passes under RC1 are rejected and verify as `session_rejection_verified`.

### RC2 Governed Stack Session Verification
*   Under `SOL-WAVEGUIDE-RC2`, sessions executing both foundation and governed passes verify as `session_verified`.

### Recompute Strategy for Output Payload Digest
The final output payload digest is recomputed using the canonical aggregate strategy:
*   Collects ordered executed pass output payload digests from execution records on disk.
*   Collects ordered rejection record digests.
*   Aggregates they with requested pass sequence, release candidate ID, and compiler profile into a single deterministic JSON structure, and hashes the structure using **SHA256**.

### Strict Safety Verification
A session is blocked or fails verification if:
*   LaneFabric fallback, hybrid execution, or production mutation is requested.
*   The software validation caveat is missing.
*   Strict waveguide requirement is disabled.
*   Any plan order corruption, count mismatch, or digest mismatch occurs.

---

## 4. Deterministic Hashing Requirements

*   Serializes all keys using canonical, sorted JSON serialization.
*   Strips self-referential digest fields (`session_case_digest` and `session_verification_report_digest`) during hashing.
*   Uses **SHA256** digests.

---

## 5. Software Validation Caveat and Limitations

*   **Sandbox Caveat**: Validation is shadow/sandbox software validation, not quantum hardware validation.
*   **Dry-Run Limitations**: The verifier reverifies transaction envelope data from mock files and in-memory trace structures. It does not load or execute real production compiler assets or optimization passes.
