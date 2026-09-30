# SOL Waveguide Compiler Pass Admission Controller

This document defines the Compiler Pass Admission Controller system, outlining how it consumes runtime capability resolution records, handles admission requests, enforces RC1 and RC2 policies, and evaluates safety constraints.

---

## 1. Purpose of the Pass Admission Controller

The Compiler Pass Admission Controller decides whether a requested compiler pass or optimization profile may be admitted for execution under the active release candidate. It consumes the read-only capability resolution records produced by the Runtime Capability Resolver:

```text
Runtime Capability Resolver
→ Compiler Pass Admission Controller
→ future Governed Pass Execution Harness
```

Future tooling queries the admission controller before executing any pass or selecting an optimization profile to ensure compliance with the governance gates.

---

## 2. Admission Request and Decision Schemas

### Admission Request Schema
*   `request_id`: Canonical request identifier (e.g. `SOL-WAVEGUIDE-PASS-ADMISSION-REQUEST-RC2`).
*   `rc_id`: Release Candidate ID (`SOL-WAVEGUIDE-RC1` or `SOL-WAVEGUIDE-RC2`).
*   `candidate_level`: Level of the candidate (`foundation` or `governed_execution_stack`).
*   `requested_pass`: Name of the pass to execute (e.g. `cost_model_evaluation`).
*   `requested_profile`: Optional optimization profile (e.g. `COST_MODEL_DEBUG`).
*   `requested_scope`: Scope of the request (`foundation_pass`, `governed_execution_pass`, `profile_selection`, or `optimization_selection`).
*   `capability_resolution_path`: Path to the capability resolution JSON.
*   `capability_resolution_digest`: Expected digest of the capability resolution record.
*   `strict_waveguide_required`: Must be set to `true`.
*   `lane_fabric_fallback_requested` / `hybrid_execution_requested` / `production_mutation_requested`: Safety indicators.
*   `software_validation_caveat_required`: Must be set to `true`.
*   `request_digest`: SHA256 digest of key-sorted request JSON (excluding `request_digest` itself).

### Admission Decision Schema
*   `decision_id`: Canonical decision identifier.
*   `request_id`: Matches the incoming request.
*   `rc_id` / `candidate_level` / `requested_pass` / `requested_profile` / `requested_scope`: Copied from request.
*   `capability_resolution_digest`: Loaded from resolution.
*   `capability_status`: Status of capability (`capability_resolved` or `capability_blocked`).
*   `admission_status`: Admission result (`pass_admitted`, `pass_blocked`, or `pass_warning`).
*   `pass_allowed` / `profile_allowed`: Boolean indicators.
*   `strict_waveguide_required`: Safety check.
*   `lane_fabric_fallback_allowed` / `hybrid_execution_allowed` / `production_mutation_allowed`: Must resolve to `false`.
*   `reason_codes`: Sorted list of evaluation reason codes.
*   `notes`: Explanatory text.
*   `software_validation_caveat`: Inherited from the capability resolution.
*   `decision_digest`: SHA256 digest of key-sorted decision JSON (excluding `decision_digest` itself).

---

## 3. RC1 Foundation vs RC2 Governed Stack Admission Policies

### RC1 Foundation Admission Policy
RC1 restricts pass admission to the Foundation-only subset:
*   **Admitted Passes/Profiles**: Must be explicitly allowed in the `SOL-WAVEGUIDE-RC1` capability resolution (e.g., `pipeline_compaction`).
*   **Blocked Passes**: Governed stack passes such as `channel_kernel_recognition`, `cost_model_evaluation`, and `deterministic_policy_selection` are strictly blocked.
*   **Blocked Profiles**: Governed stack profiles such as `COST_MODEL_DEBUG`, `AUTOTUNE_SAFE`, `AUTOTUNE_LOWEST_CYCLES`, and `KERNEL_AUTOTUNE_SAFE` are strictly blocked.

### RC2 Governed Execution Stack Admission Policy
RC2 permits governed stack features:
*   **Admitted Passes/Profiles**: All Foundation passes/profiles, as well as governed passes (`channel_kernel_recognition`, `cost_model_evaluation`, `deterministic_policy_selection`) and governed profiles (`COST_MODEL_DEBUG`, `AUTOTUNE_SAFE`, `AUTOTUNE_LOWEST_CYCLES`, `KERNEL_AUTOTUNE_SAFE`).
*   **Requirement**: The underlying `SOL-WAVEGUIDE-RC2` capability resolution must validate successfully with `capability_status = capability_resolved`.

---

## 4. Universal Safety Rules

A pass must be blocked for both RC1 and RC2 if any of the following safety rules are violated:
1.  **Strict Waveguide Required**: Only strict waveguide execution (`strict_waveguide_required: true`) is permitted.
2.  **LaneFabric Fallback Forbidden**: Any request for fallback (`lane_fabric_fallback_requested: true`) is blocked.
3.  **Hybrid Execution Forbidden**: Compilation mixing requests (`hybrid_execution_requested: true`) are blocked.
4.  **Production Mutation Forbidden**: Runtime environment modifications (`production_mutation_requested: true`) are blocked.
5.  **Software Validation Caveat Required**: A valid software validation caveat (proving shadow/sandbox model verification) must be present in the capability resolution record.

---

## 5. Deterministic Hashing Strategy

All requests and decisions are hashed deterministically to guarantee record integrity:
*   Uses **SHA256** canonical hashing.
*   The JSON serialization uses key-sorting.
*   Self-referential digest fields (`request_digest` on requests and `decision_digest` on decisions) are stripped before hashing.
*   No machine-specific absolute paths or timestamps are included.

---

## 6. Required Artifacts

The system exports standard admission decisions:
*   RC1 Admitted Decision: [docs/SOL_WAVEGUIDE_COMPILER_PASS_ADMISSION_RC1.json](file:///g:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_COMPILER_PASS_ADMISSION_RC1.json) (admitting `pipeline_compaction`).
*   RC2 Admitted Decision: [docs/SOL_WAVEGUIDE_COMPILER_PASS_ADMISSION_RC2.json](file:///g:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_COMPILER_PASS_ADMISSION_RC2.json) (admitting `cost_model_evaluation`).

---

## 7. Sandbox Caveat

> [!IMPORTANT]
> **SOFTWARE VALIDATION CAVEAT**
> The pass admission controller, requests, and decisions run entirely within a shadow/sandbox compiler verification system. This does not perform real-world hardware verification.

---

## 8. Next Recommended Step: Governed Pass Execution Harness

The next bridge in the governance roadmap is the **Governed Pass Execution Harness**. That future module will wrap the actual compiler pass compiler execution stage, consulting these admission decisions to block unadmitted passes or profiles, log validation verdicts, and enforce deterministic selection.
