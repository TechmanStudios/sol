# SOL Waveguide Package Assembly Execution Plan

The **SOL Waveguide Package Assembly Execution Plan** is a deterministic planning layer in the waveguide release pipeline that maps a verified preflight authorization audit into a sequence of ordered steps for a future controlled package assembly.

This step establishes the following release pipeline bridge:

```text
Package Assembly Authorization Validator / Preflight Authorization Auditor
→ Package Assembly Execution Plan (This Step)
→ future Package Assembly Execution Plan Validator / Execution Readiness Auditor
```

---

## 1. Purpose & Integration Philosophy

This module consumes the **Preflight Authorization Audit Report** (`docs/SOL_WAVEGUIDE_PACKAGE_PREFLIGHT_AUTHORIZATION_AUDIT_REPORT.json`) and creates an ordered set of step blueprints. It answers:
> *If package assembly is later performed by a controlled runner, what exact ordered steps, inputs, outputs, guards, source references, target layout references, and prohibited-operation boundaries must be followed?*

### Distinction Between Planning and Execution

To guarantee that planning remains side-effect-free, this layer is strictly confined to generating descriptive software metadata. It enforces the following boundaries:
* **No ZIP files** or tarballs are created.
* **No files** are copied to target package directories.
* **No directories** are created on disk.
* **No uploads**, external publication acts, or signing are performed.
* **No production state mutations** are triggered.

---

## 2. Input Integration & Flow

The execution planner:
1. Loads the Preflight Authorization Audit Report.
2. Validates it via `validate_waveguide_package_preflight_authorization_audit_report`.
3. Confirms the report status is `package_preflight_authorization_verified`.
4. Loads the Final Package Readiness Audit Report to extract the file metadata mappings.
5. Deterministically sorts cases by `target_package_path` and `source_artifact_path`.
6. Generates step sequence definitions and hashes them.

---

## 3. Execution Step Schema

Each step represented by `WaveguidePackageAssemblyExecutionStep` includes:

| Field | Description |
|---|---|
| `package_execution_step_id` | Unique identifier (e.g. `SOL-WAVEGUIDE-EXECUTION-STEP-001`). |
| `step_index` | Non-negative integer index. |
| `step_name` | Human-readable description. |
| `step_type` | `verify_preflight_authorization`, `prepare_metadata_instruction`, `prepare_noop_boundary`, or `finalize_execution_blueprint`. |
| `step_phase` | `preflight`, `instruction_planning`, `safety_boundary`, or `finalization`. |
| `step_status` | `execution_step_planned`. |
| `source_reference_digest` | Recorded digest of the input source. |
| `source_reference_path` | Repository relative path to the source. |
| `input_reference_kind` | `preflight_report`, `source_artifact`, or `none`. |
| `planned_output_reference` | Planned target package path. |
| `planned_output_kind` | `target_artifact` or `none`. |
| `target_package_section` | Target layout section (e.g. `docs/`, `proof/`). |
| `target_package_path` | Target layout path. |
| `artifact_digest` | SHA256 digest of the artifact. |
| `artifact_type` | Specific waveguide role type. |
| `package_role` | Role type from final readiness report. |
| `rc_scope` | Scope of the candidate (`Shared`, `RC1`, `RC2`). |
| `requires_preflight_authorization` | Boolean flag (always `True`). |
| `requires_same_authorization_envelope_digest` | Boolean flag (always `True`). |
| `requires_same_preflight_report_digest` | Boolean flag (always `True`). |
| `requires_same_final_readiness_report_digest` | Boolean flag (always `True`). |
| `requires_same_package_manifest_digest` | Boolean flag (always `True`). |
| `requires_same_dry_run_report_digest` | Boolean flag (always `True`). |
| `requires_same_artifact_catalog_digest` | Boolean flag (always `True`). |
| `guard_conditions` | List of guard conditions that must pass. |
| `prohibited_operations` | List of prohibited operations. |
| `no_op_boundary` | Boolean flag (always `True`). |
| `physical_execution_performed` | Boolean flag (always `False`). |
| `archive_created` | Boolean flag (always `False`). |
| `file_copied` | Boolean flag (always `False`). |
| `directory_created` | Boolean flag (always `False`). |
| `upload_performed` | Boolean flag (always `False`). |
| `deployment_performed` | Boolean flag (always `False`). |
| `signing_performed` | Boolean flag (always `False`). |
| `external_publication_performed` | Boolean flag (always `False`). |
| `production_mutation_performed` | Boolean flag (always `False`). |
| `reason_codes` | Status/reason tokens. |
| `notes` | Optional list of notes. |
| `software_validation_caveat` | Caveat string. |
| `package_execution_step_digest` | Deterministic digest. |

---

## 4. Top-Level Execution Plan Schema

The top-level plan represented by `WaveguidePackageAssemblyExecutionPlan` includes:
* **Identification & Digests**: Preserved digests of the source preflight report, envelope, manifest, dry-run report, plan, and catalog.
* **Execution Step Sequence**: List of step dataclasses.
* **Indexes & Mappings**:
  * Sorted indexes for Sections, Roles, Types, and Formats.
  * `execution_input_reference_index`: maps `source_reference_path` -> `source_reference_digest`.
  * `execution_output_reference_index`: maps `target_package_path` -> `artifact_digest`.
* **Execution Guard Matrix**: Checks that any future execution runner must satisfy before acting.
* **No-Op Sandbox Boundary**: Maps physical creation/mutations to `False`.
* **Rollback/No-Op Policy**: Specifies the rollback scope is metadata-only.
* **Blocked Operations**: Attempt counters for prohibited operations (all zero).

---

## 5. Hashing Strategy & Self-Reference Exclusions

To ensure hash stability:
* Keys are sorted before canonical JSON serialization.
* Self-referential digest fields are popped before hashing:
  * `package_execution_step_digest` is popped when hashing execution steps.
  * `package_assembly_execution_plan_digest` is popped when hashing the top-level plan.

---

## 6. Caveats, Limitations & Sandbox Boundaries

* **Software Caveat**: *"Validation is shadow/sandbox software validation, not quantum hardware validation."*
* **Limitations**: The plan describes execution metadata; it does not physically copy or verify the presence of files at run-time.

---

## 7. Next Recommended Build Step

The next recommended governance bridge is:
```text
Package Assembly Execution Plan Validator / Execution Readiness Auditor
```
That future step will independently reload the execution plan, recompute digests, validate the guard matrix, verify preflight report references, and produce an execution-readiness audit report without performing any physical packaging operations.
