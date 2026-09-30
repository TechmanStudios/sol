# SOL Waveguide Governed Compiler Invocation Envelope

This document defines the **Governed Compiler Invocation Envelope** system for the SOL Waveguide compiler sessions. The invocation envelope binds pass-level capability resolution, admission decisions, pass execution records, trace indexing, and replay verification reports into a single, deterministic compiler session transaction record.

---

## 1. Purpose of the Invocation Envelope

The Governed Compiler Invocation Envelope consolidates individual pass-level governance records into a single compiler session transaction:

```text
Governed Pass Replay Verifier
→ Governed Compiler Invocation Envelope (This Step)
→ future Governed Compiler Invocation Replay / Session Verifier
```

It acts as a session transaction wrapper, ensuring that a compiler session runs under strict governance, admitting only policy-compliant passes, executing safe handlers, indexing all operations, and verifying the entire session via the replay verifier.

---

## 2. Schemas and Specifications

### Invocation Request Schema
*   `invocation_request_id`: Unique session request ID.
*   `rc_id`: Release Candidate ID (`SOL-WAVEGUIDE-RC1` or `SOL-WAVEGUIDE-RC2`).
*   `candidate_level`: Level of the candidate (`foundation` or `governed_execution_stack`).
*   `compiler_profile`: Compiler profile associated with the session.
*   `requested_pass_sequence`: List of passes to execute in sequence.
*   `requested_scope`: Scope of the request (`foundation_compiler_invocation`, `governed_compiler_invocation`, or `dry_run_compiler_invocation`).
*   `capability_resolution_path` / `capability_resolution_digest`: Resolution policy details.
*   `registry_digest`: Release registry digest.
*   `strict_waveguide_required`: Must be `true`.
*   `lane_fabric_fallback_requested` / `hybrid_execution_requested` / `production_mutation_requested`: Must be `false`.
*   `software_validation_caveat_required`: Must be `true`.
*   `input_payload_digest`: Digest of the input payload.
*   `invocation_request_digest`: SHA256 signature of sorted request (excluding `invocation_request_digest`).

### Pass Plan Schema
*   `pass_index`: Sequence position index (0, 1, 2, ...).
*   `requested_pass`: Name of the pass.
*   `requested_profile`: Requested profile.
*   `requested_scope`: Scope of the admission request.
*   `expected_admission_status`: expected admission status.
*   `expected_execution_status`: expected execution outcome.
*   `required_handler_id`: Handler ID mapped from registry.
*   `strict_waveguide_required`: Safety enforcement.
*   `lane_fabric_fallback_allowed` / `hybrid_execution_allowed` / `production_mutation_allowed`: Must be `false`.

### Invocation Record Schema
*   `invocation_record_id`: Session record ID.
*   `invocation_request_id`: Request ID reference.
*   `rc_id` / `candidate_level` / `compiler_profile`: Session parameters.
*   `requested_pass_sequence`: Requested passes.
*   `pass_plan`: Serialized pass plan.
*   `invocation_status`: Overall outcome status (`invocation_verified`, `invocation_blocked`, `invocation_rejected_verified`, `invocation_failed`, or `invocation_warning`).
*   `capability_resolution_digest`: Resolved capability policy check.
*   `admission_decision_digests` / `execution_record_digests` / `trace_entry_digests`: Reference lists.
*   `trace_ledger_digest`: Reference to session trace ledger.
*   `replay_report_digest`: Reference to session replay verification report.
*   `executed_pass_count` / `rejected_pass_count`: Action metrics.
*   `verified_execution_count` / `verified_rejection_count` / `failed_replay_count`: Verification metrics.
*   `handler_ids_used`: Handler IDs utilized.
*   `input_payload_digest`: input payload digest.
*   `final_output_payload_digest`: Output payload digest after pass sequence execution.
*   `reason_codes` / `notes` / `software_validation_caveat`: Evaluation logs.
*   `invocation_record_digest`: SHA256 signature of sorted record (excluding `invocation_record_digest`).

---

## 3. Invocation Policies and Safety Constraints

### RC1 Foundation Invocation Policy
Under `SOL-WAVEGUIDE-RC1`, only foundation compiler passes (e.g. `pipeline_compaction`) are permitted. Governed features (cost models, autotuning, kernel recognition) are blocked, and requests attempting to run them are rejected.

### RC2 Governed Stack Invocation Policy
Under `SOL-WAVEGUIDE-RC2`, both foundation passes and governed features (e.g. `cost_model_evaluation`, `deterministic_policy_selection`) are permitted.

### Rejection-Only Invocation Behavior
If all passes requested in the session are blocked by capability policy, no handlers are executed, and the session status resolves to `invocation_rejected_verified` once all rejections are trace-indexed and replay-verified.

### Strict Safety Requirements
*   `strict_waveguide_required`: Must be active.
*   `lane_fabric_fallback_requested`: Prohibited.
*   `hybrid_execution_requested`: Prohibited.
*   `production_mutation_requested`: Prohibited.
*   `software_validation_caveat_required`: Proves sandbox execution context.

---

## 4. Deterministic Hashing Requirements

Matches Waveguide core layer hashing:
*   Serializes all keys using canonical, sorted JSON serialization.
*   Strips self-referential digest fields (`invocation_request_digest` and `invocation_record_digest`) during hashing.
*   Uses **SHA256** digests.

---

## 5. Software Validation Caveat and Limitations

> [!IMPORTANT]
> **SOFTWARE VALIDATION CAVEAT**
> The invocation envelope is a non-production validation wrapper running in a shadow sandbox. It wraps mock/simulated safe handlers and indexes dry-run compiler sessions without mutating production pipeline states.

---

## 6. Next Recommended Step: Governed Compiler Invocation Replay / Session Verifier

The next logical bridge is the **Governed Compiler Invocation Replay / Session Verifier**. That future step will replay and verify full invocation envelopes as a complete governed compiler session, rather than only validating individual pass traces.
