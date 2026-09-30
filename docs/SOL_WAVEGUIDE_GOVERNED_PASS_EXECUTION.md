# SOL Waveguide Governed Pass Execution Harness

This document defines the Governed Pass Execution Harness system, detailing schemas, registered safe pass handlers, execution/rejection policies for RC1 and RC2, and safety constraints.

---

## 1. Purpose of the Governed Pass Execution Harness

The Governed Pass Execution Harness acts as a deterministic wrapper around compiler pass invocation. It validates pass admission decisions and dispatches execution only to registered deterministic safe handlers, producing detailed audit records and preventing execution violations:

```text
Compiler Pass Admission Controller
→ Governed Pass Execution Harness
→ future Execution Trace Registry / Rejection Ledger
```

All pass executions and blocks are recorded deterministically as signed/hashed trace structures for post-compilation verification.

---

## 2. Request and Record Schemas

### Execution Request Schema
*   `execution_request_id`: Canonical request identifier (e.g. `SOL-WAVEGUIDE-PASS-EXECUTION-REQUEST-RC2`).
*   `rc_id`: Release Candidate ID (`SOL-WAVEGUIDE-RC1` or `SOL-WAVEGUIDE-RC2`).
*   `candidate_level`: Level of candidate (`foundation` or `governed_execution_stack`).
*   `requested_pass`: Name of compiler pass (e.g. `cost_model_evaluation`).
*   `requested_profile`: Optional profile name (e.g. `COST_MODEL_DEBUG`).
*   `admission_decision_path`: Path to the pass admission decision JSON file.
*   `admission_decision_digest`: Digest value of the admission decision.
*   `admission_status`: Admission status (`pass_admitted` or `pass_blocked`).
*   `execution_scope`: Scope of execution (e.g., `foundation_pass_execution`, `governed_pass_execution`).
*   `input_payload_digest`: Digest value of the input payload.
*   `strict_waveguide_required`: Must be set to `true`.
*   `lane_fabric_fallback_allowed` / `hybrid_execution_allowed` / `production_mutation_allowed`: Safety indicator configurations.
*   `software_validation_caveat_required`: Must be set to `true`.
*   `execution_request_digest`: SHA256 digest of key-sorted request JSON (excluding `execution_request_digest` itself).

### Execution Record Schema
*   `execution_record_id`: Canonical record identifier.
*   `execution_request_id`: Matches request.
*   `rc_id` / `candidate_level` / `requested_pass` / `requested_profile`: Copied from request.
*   `admission_decision_digest`: Copied from request.
*   `admission_status`: Admission status copied from decision.
*   `execution_status`: Output status (`pass_executed`, `pass_rejected`, `pass_execution_warning`, or `pass_execution_error`).
*   `handler_id`: Registered handler ID (e.g., `SOL-PASS-HANDLER-COST-MODEL-EVALUATION-V1`).
*   `handler_version`: Version of the safe handler (`1.0.0`).
*   `handler_registered`: Boolean flag indicator.
*   `pass_executed` / `pass_rejected`: Boolean indicator states.
*   `input_payload_digest` / `output_payload_digest`: Digests of input and output data.
*   `trace`: Step-by-step list of verification and execution logs.
*   `reason_codes`: Sorted list of evaluation reason codes.
*   `notes`: Explanatory details.
*   `strict_waveguide_required`: safety check.
*   `lane_fabric_fallback_allowed` / `hybrid_execution_allowed` / `production_mutation_allowed`: safety check results.
*   `software_validation_caveat`: Caveat proving sandbox simulation context.
*   `execution_record_digest`: SHA256 digest of key-sorted record JSON (excluding `execution_record_digest` itself).

---

## 3. Safe Handler Registry

To prevent executing untrusted arbitrary compiler logic, the harness limits execution to a closed set of registered safe handlers.

*   `pipeline_compaction`:
    *   **Handler ID**: `SOL-PASS-HANDLER-PIPELINE-COMPACTION-V1`
    *   **Logic**: Compacts pipeline stages and returns compaction ratio metrics.
*   `channel_kernel_recognition`:
    *   **Handler ID**: `SOL-PASS-HANDLER-CHANNEL-KERNEL-RECOGNITION-V1`
    *   **Logic**: Recognizes micro-ISA patterns and counts matched kernels.
*   `cost_model_evaluation`:
    *   **Handler ID**: `SOL-PASS-HANDLER-COST-MODEL-EVALUATION-V1`
    *   **Logic**: Calculates cost scores based on input clock cycle count.
*   `deterministic_policy_selection`:
    *   **Handler ID**: `SOL-PASS-HANDLER-DETERMINISTIC-POLICY-SELECTION-V1`
    *   **Logic**: Returns deterministic selection indices for autotuning.

---

## 4. Execution Policies

### RC1 Foundation execution Policy
*   Foundation-admitted passes (e.g., `pipeline_compaction`) execute successfully through registered handlers.
*   Governed execution stack passes (e.g., `cost_model_evaluation`) are rejected, producing `pass_rejected` records without execution.

### RC2 Governed Execution Stack Policy
*   Both Foundation and Governed Execution Stack passes (if registered and admitted) can be executed.
*   Blocked RC2 decisions (or missing handlers) generate `pass_rejected` records.

---

## 5. Universal Safety Constraints

The harness strictly rejects pass execution if:
1.  **Strict Waveguide Missing**: Only strict waveguide mode is allowed.
2.  **Fallback Requested**: LaneFabric fallback is forbidden.
3.  **Hybrid compilation Requested**: Hybrid execution mixes are forbidden.
4.  **Mutation Requested**: Production mutations are forbidden.
5.  **Software validation Caveat Missing**: A sandbox validation caveat must be present.

---

## 6. Deterministic Hashing Strategy

All records, requests, and payloads are digested using **SHA256**:
*   All dictionaries are sorted by keys.
*   Self-referential digests (`execution_request_digest` on request and `execution_record_digest` on record) are omitted from hash calculations.

---

## 7. Required Artifacts

The harness generates and exports standard execution logs under `docs/`:
*   RC1 Admitted Execution Record: [docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json](file:///g:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC1.json)
*   RC2 Admitted Execution Record: [docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC2.json](file:///g:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_RC2.json)
*   Rejection Example Record: [docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json](file:///g:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_GOVERNED_PASS_EXECUTION_REJECTION_EXAMPLE.json)

---

## 8. Next Recommended Step: Execution Trace Registry / Rejection Ledger

The recommended next roadmap step is the **Execution Trace Registry / Rejection Ledger**. That future module will collect all execution/rejection records, cataloging them for downstream audit logs, compliance checks, and optimization re-runs.
