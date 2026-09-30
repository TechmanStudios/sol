# SOL Waveguide Release Candidate Release Gate & Delta Audit

This document defines the release validation, boundary checks, and auditing rules for release candidates of the SOL waveguide engine optimization framework.

---

## 1. Purpose of the Release Gate

The RC Release Gate and Delta Audit Harness provides machine-verifiable verification of the separation between release candidates:
- **RC1 (Foundation)**: Core strict waveguide backend and v1/channel foundation. It must not leak any optimization, cost model, or autotuning features.
- **RC2 (Governed Execution Stack)**: Governed execution stack containing cost estimation, autotuning, and trace validation.
- **Delta Analysis**: Tracks and verifies all RC2-only additions, validating that only authorized governed features are introduced and no unexpected profiles, passes, or parameters are leaked.

---

## 2. RC1 vs RC2 Boundary

To ensure strict engineering governance, the compiler release boundaries are defined as follows:

### Allowed RC2-only Governed Features
The following features are designated as RC2-only additions and must be absent from RC1:
- **Profiles**:
  - `COST_MODEL_DEBUG`
  - `AUTOTUNE_SAFE`
  - `AUTOTUNE_LOWEST_CYCLES`
  - `KERNEL_AUTOTUNE_SAFE`
- **Canonical Passes**:
  - `channel_kernel_recognition`
  - `cost_model_evaluation`
  - `deterministic_policy_selection`
- **Configuration Fields**:
  - `cost_model_and_autotuning`

---

## 3. Release Verdict Rules

The release gate dynamically evaluates a candidate manifest and assigns one of three verdicts:

| Verdict | Meaning | Reason Codes / Criteria |
| :--- | :--- | :--- |
| **`release_ready`** | The manifest is clean and matches its release candidate requirements. | `RC_RELEASE_READY`, `RC_MANIFEST_SCHEMA_VALID`, `RC_DELTA_MATCHES_EXPECTATION` |
| **`warning`** | The manifest is safe to run but contains unexpected additions or modifications. | `RC2_UNEXPECTED_FEATURE` |
| **`blocked`** | The manifest violates release candidate rules or fails consistency checks. | `RC1_GOVERNED_FEATURE_LEAK`, `RC1_FOUNDATION_FEATURE_MISSING`, `RC2_GOVERNED_FEATURE_MISSING`, `RC_RELEASE_BLOCKED` |

---

## 4. Audit Artifact Format

The release gate exports a deterministic delta audit file to [docs/SOL_WAVEGUIDE_RC_DELTA_AUDIT.json](file:///g:/docs/TechmanStudios/sol/docs/SOL_WAVEGUIDE_RC_DELTA_AUDIT.json). This JSON artifact logs:
- Manifest IDs for RC1 and RC2.
- Shared profiles, passes, and fields.
- RC2-only additions.
- Boundary check verdicts and failure reasons (e.g. `RC1_GOVERNED_FEATURE_LEAK`).
- Software-simulation scope caveat.

---

## 5. Next Recommended Bridge: Signed RC Promotion Ledger

The next bridge in the compiler roadmap is the **Signed RC Promotion Ledger**.
This future step will:
- Freeze manifest hashes and validation outcomes into a signed ledger.
- Prevent manual or unverified release promotions.
- Require dual-agent sign-offs for final release promotions.

---

## 6. Scope and Sandbox Caveat

> [!IMPORTANT]
> **SANDBOX CAVEAT & SCOPE LIMITATION**
> All release gate checks, manifest validations, and delta audits are software-simulated checks within a shadow/sandbox compiler model.
> - There is no physical quantum-hardware verification.
> - Execution remains strictly a software model for compiler verification and research.
