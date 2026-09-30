# SOL Waveguide Governed Pass Replay Verifier

This document defines the **Governed Pass Replay Verifier** system for the SOL Waveguide governance stack. The verifier audits the records registered in the trace ledger, verifying that executed passes can be replayed deterministically and rejected passes are correctly handled.

---

## 1. Purpose of the Replay Verifier

The replay verifier provides a cryptographic verification layer that guarantees execution trace reproducibility:

```text
Execution Trace Registry / Rejection Ledger
→ Governed Pass Replay Verifier (This Step)
→ future Governed Compiler Invocation Envelope
```

It reloads execution and rejection records, validates their structures and digests against the ledger index, dispatches re-execution of admitted passes to registered deterministic safe handlers, and asserts that the resulting output payload digest matches the original run.

---

## 2. Replay Case and Replay Report Schemas

### Replay Case Schema
*   `replay_case_id`: Identifier of the case (e.g. `SOL-WAVEGUIDE-REPLAY-CASE-SOL-WAVEGUIDE-TRACE-ENTRY-RC1-pipeline_compaction-FULL_SAFE_OPTIMIZED`).
*   `ledger_path` / `ledger_digest` / `ledger_status`: Parent ledger metadata references.
*   `source_trace_entry_digest`: Digest of the original trace entry.
*   `execution_record_path` / `execution_record_digest`: Reference record path and signature.
*   `rc_id` / `candidate_level` / `requested_pass` / `requested_profile`: Details of requested compiler pass.
*   `execution_status`: Status of the execution record.
*   `handler_id` / `handler_version`: Details of safe handler used.
*   `input_payload_digest`: Original input payload digest.
*   `recorded_output_payload_digest`: Original output payload digest.
*   `software_validation_caveat`: Proves simulated execution context.
*   `replay_case_status`: Readiness status (`replay_case_ready`, `replay_case_rejected_record`, `replay_case_blocked`, or `replay_case_invalid`).
*   `replay_status`: Individual case verification status (`replay_verified`, `replay_rejected_record_verified`, `replay_failed`, or `replay_skipped`).
*   `reason_codes`: Trace list of verification milestones.
*   `replay_case_digest`: SHA256 digest of key-sorted case JSON (excluding `replay_case_digest`).

### Replay Report Schema
*   `replay_report_id`: Unique report ID (`SOL-WAVEGUIDE-GOVERNED-PASS-REPLAY-REPORT`).
*   `replay_report_version`: Report version string (`1`).
*   `replay_report_status`: Verification status (`replay_report_verified`, `replay_report_failed`, or `replay_report_warning`).
*   `ledger_id` / `ledger_digest` / `ledger_valid`: Parent ledger status trackers.
*   `cases`: Deterministically sorted list of all replay cases.
*   `verified_executions` / `verified_rejections` / `failed_replays` / `skipped_replays`: Case ID categories.
*   `verified_execution_count` / `verified_rejection_count` / `failed_replay_count` / `skipped_replay_count`: Metrics.
*   `handler_ids_replayed`: Unique, sorted list of replayed handler IDs.
*   `source_execution_record_digests`: Unique, sorted list of execution record digests checked.
*   `source_trace_entry_digests`: Unique, sorted list of trace entry digests checked.
*   `reason_codes`: Verification reason codes.
*   `software_validation_caveat`: Proves simulation context.
*   `replay_report_digest`: SHA256 digest of key-sorted report JSON (excluding `replay_report_digest`).

---

## 3. Replay and Verification Rules

### Executed Record Replay Rules
An executed record replay is valid only when:
1.  The parent trace ledger validates successfully.
2.  The trace entry validates successfully.
3.  The governed execution record validates successfully.
4.  The execution record digest matches the trace entry.
5.  The execution status is `pass_executed` and admission status is `pass_admitted`.
6.  The handler ID and version are registered.
7.  The requested pass matches the registered handler.
8.  The input payload digest matches the recorded input payload digest.
9.  Rerunning the safe handler produces an output payload whose digest equals the recorded output payload digest.

### Rejected Record Verification Rules
A rejected record verification is valid only when:
1.  The parent trace ledger validates successfully.
2.  The trace entry validates successfully.
3.  The governed execution record's digest is valid.
4.  The execution status is `pass_rejected`.
5.  Rejection reason codes are present in the record.
6.  No handler replay is attempted and no output payload digest is recorded.

---

## 4. Deterministic Hashing and Digest Exclusions

Uses SHA256 canonical hashing matching other Waveguide layers:
*   Serializes all keys using canonical, sorted JSON serialization.
*   Strips self-referential digest fields (`replay_case_digest` when hashing cases, `replay_report_digest` when hashing the report).
*   Avoids absolute machine-specific paths and timestamp fields.

---

## 5. Required Artifacts

The system exports verification records:
*   Full Replay Report JSON: [docs/SOL_WAVEGUIDE_GOVERNED_PASS_REPLAY_REPORT.json](file:///g:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_GOVERNED_PASS_REPLAY_REPORT.json)

---

## 6. Software Validation Caveat and Limitations

> [!IMPORTANT]
> **SOFTWARE VALIDATION CAVEAT**
> The replay verifier runs entirely within a shadow sandbox environment. It replays *deterministic stub safe handlers* rather than real optimizer algorithms or live lowering passes. It validates policy conformance and digest integrity without mutating production compiler states.

---

## 7. Next Recommended Step: Governed Compiler Invocation Envelope

The next logical bridge is the **Governed Compiler Invocation Envelope**. That layer will wrap compiler sessions, capturing invocation metadata, compiler profiles, and sequence tracking to bind pass-level registries into a single execution transaction.
