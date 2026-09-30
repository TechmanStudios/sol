# SOL Waveguide Runtime Capability Resolver

This document defines the runtime capability resolver system, detailing schemas, policy mapping for RC1 and RC2, execution limitations, and hashing rules.

---

## 1. Purpose of the Capability Resolver

The Runtime Capability Resolver translates approved release candidates inside the Release Registry into read-only policy constraints and capability mapping lists. It serves as the bridge between the release registry and compiler execution:

```text
RC Release Registry / Promotion Index
\u2192 Runtime Capability Resolver
\u2192 future Compiler Pass Admission Controller
```

Future tooling queries the resolver to verify whether specific passes, autotuning, or profiles are authorized for execution under the active release candidate level.

---

## 2. Capability Request and Resolution Schemas

### Request Schema
*   `request_id`: Canonical request identifier (e.g. `SOL-WAVEGUIDE-RC-CAPABILITY-REQUEST-RC2`).
*   `rc_id`: Target Release Candidate ID (e.g. `SOL-WAVEGUIDE-RC2`).
*   `requested_scope`: Scope requested (`foundation_runtime` or `governed_execution_runtime`).
*   `registry_path`: Repository-relative path to the release registry JSON.
*   `registry_digest`: Registry digest value.
*   `require_court_approved_release`: Boolean flag requiring verified court approval.
*   `software_validation_caveat_required`: Boolean flag requiring software caveats.
*   `request_digest`: SHA256 digest of key-sorted request JSON (excluding `request_digest` itself).

### Resolution Schema
*   `resolution_id`: Canonical resolution identifier.
*   `capability_status`: Status of resolution (`capability_resolved`, `capability_blocked`, `capability_warning`).
*   `allowed_backend`: Expected backend compiler string (`pdm_waveguide_microcoded_strict`).
*   `allowed_profiles` / `allowed_passes`: Dynamic lists derived from the approved RC manifest.
*   `disallowed_profiles` / `disallowed_passes`: Blocked feature sets.
*   `governed_stack_enabled`: Boolean flag.
*   `cost_model_enabled` / `autotuning_enabled` / `kernel_recognition_enabled` / `deterministic_policy_selection_enabled`: Boolean feature flags.
*   `strict_waveguide_required`: Strict backend compliance flag.
*   `lane_fabric_fallback_allowed` / `hybrid_execution_allowed` / `production_mutation_allowed`: Policy prohibition flags.
*   `resolution_digest`: SHA256 digest of key-sorted resolution JSON (excluding `resolution_digest` itself).

---

## 3. RC1 Foundation vs RC2 Governed Stack Policies

### RC1 Foundation Policy
RC1 is locked to Foundation-only capabilities:
- **Governed Stack Features**: Disabled (`governed_stack_enabled: false`, autotune/cost model disabled).
- **Disallowed Profiles**: `COST_MODEL_DEBUG`, `AUTOTUNE_SAFE`, `AUTOTUNE_LOWEST_CYCLES`, `KERNEL_AUTOTUNE_SAFE`
- **Disallowed Passes**: `channel_kernel_recognition`, `cost_model_evaluation`, `deterministic_policy_selection`
- **Allowed Profiles/Passes**: Derived from the approved `SOL-WAVEGUIDE-RC1` manifest.

### RC2 Governed Execution Stack Policy
RC2 authorizes both Foundation and Governed Stack capabilities:
- **Governed Stack Features**: Enabled (`governed_stack_enabled: true`, autotune/cost model enabled).
- **Allowed Governed Profiles**: `COST_MODEL_DEBUG`, `AUTOTUNE_SAFE`, `AUTOTUNE_LOWEST_CYCLES`, `KERNEL_AUTOTUNE_SAFE`
- **Allowed Governed Passes**: `channel_kernel_recognition`, `cost_model_evaluation`, `deterministic_policy_selection`
- **Allowed Profiles/Passes**: Derived from the approved `SOL-WAVEGUIDE-RC2` manifest.

---

## 4. Execution Restrictions (Both RC1 and RC2)

To preserve compiler execution safety:
1.  **Strict Waveguide Required**: Only the strict backend `pdm_waveguide_microcoded_strict` is authorized.
2.  **LaneFabric Fallback Prohibition**: `lane_fabric_fallback_allowed: false` prevents falling back to unverified fabrics.
3.  **Hybrid Execution Prohibition**: `hybrid_execution_allowed: false` prevents executing unapproved compilation mixes.
4.  **Production Mutation Prohibition**: `production_mutation_allowed: false` protects runtime environment integrity.

---

## 5. Next Recommended Step: Compiler Pass Admission Controller

The next bridge in the roadmap is the **Compiler Pass Admission Controller**.
A future controller module will query these runtime capability resolution records and enforce pass admission at execution time, blocking unallowed passes from running.

---

## 6. Scope and Sandbox Caveat

> [!IMPORTANT]
> **SANDBOX CAVEAT & SCOPE LIMITATION**
> The capability resolver, requests, and resolutions run entirely as software policy checks inside a shadow/sandbox compiler model.
> - There is no physical quantum-hardware verification.
> - Execution remains strictly a software model for compiler verification and research.
