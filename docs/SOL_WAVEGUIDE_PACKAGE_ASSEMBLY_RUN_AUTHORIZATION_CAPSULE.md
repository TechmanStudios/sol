# SOL Waveguide Package Assembly Run Authorization Capsule

The **SOL Waveguide Package Assembly Run Authorization Capsule** is the governance layer in the waveguide release pipeline that authorizes a specific future package assembly run request. It consumes the verified Package Execution Readiness Audit Report and binds the authorized run to the exact verified execution plan and execution-readiness report digests.

This step establishes the following release pipeline bridge:

```text
Package Assembly Execution Plan Validator / Execution Readiness Auditor
→ Package Assembly Run Authorization Capsule (This Step)
→ future Package Assembly Run Authorization Validator / Run Preflight Auditor
```

---

## 1. Purpose & Integration Philosophy

This module consumes the **Package Execution Readiness Audit Report** (`docs/SOL_WAVEGUIDE_PACKAGE_EXECUTION_READINESS_AUDIT_REPORT.json`). It answers:
> *Is this specific future package assembly run request authorized against the exact verified execution-readiness report and execution plan digest, while still performing no physical package operation?*

### Distinction Between Run Authorization and Run Execution

The capsule acts as an immutable proof of intent. It authorizes a future run request in metadata, but strictly prohibits the capsule generation step from executing any physical packaging actions. 

The following boundaries are enforced:
* **No ZIP files** or tarballs are created.
* **No files** are copied to target layouts or package directories.
* **No directories** are created on disk.
* **No uploads**, external publication acts, or signing are performed.
* **No production state mutations** are triggered.

---

## 2. Run Authorization Capsule Schema

The capsule (`WaveguidePackageAssemblyRunAuthorizationCapsule`) includes:

| Field | Description |
|---|---|
| `package_assembly_run_authorization_capsule_id` | Hardcoded capsule identity (`SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUN-AUTHORIZATION-CAPSULE`). |
| `package_assembly_run_authorization_capsule_version` | hardcoded version (`1`). |
| `run_request_id` | Deterministic request ID (e.g. `SOL-WAVEGUIDE-RUN-REQUEST-<readiness_report_digest[:16]>`). |
| `run_request_kind` | Hardcoded request kind (`metadata_only_future_package_assembly_run`). |
| `run_authorization_status` | Status from capsule (`package_run_authorized` / `package_run_blocked` / `package_run_invalid`). |
| `run_authorization_decision` | Decision from capsule (`authorize_specific_future_run` / `block_specific_future_run` / `invalid_run_authorization`). |
| `run_authorization_scope` | Hardcoded scope (`metadata_only`). |
| `source_execution_readiness_report_digest` | Recorded digest of the readiness report. |
| `source_package_assembly_execution_plan_digest` | Recorded digest of the execution plan. |
| `source_preflight_authorization_report_digest` | Recorded digest of the preflight report. |
| `source_authorization_envelope_digest` | Recorded digest of the authorization envelope. |
| `source_final_package_readiness_report_digest` | Recorded digest of the final package readiness report. |
| `source_distribution_package_manifest_digest` | Recorded digest of the package manifest. |
| `source_dry_run_audit_report_digest` | Recorded digest of the dry-run report. |
| `source_package_assembly_plan_digest` | Recorded digest of the package assembly plan. |
| `source_artifact_catalog_digest` | Recorded digest of the artifact catalog. |
| `verified_execution_readiness_case_count` | Count of verified readiness cases (`31` for clean state). |
| `blocked_execution_readiness_case_count` | Count of blocked readiness cases (`0` for clean state). |
| `warning_execution_readiness_case_count` | Count of warning readiness cases (`0` for clean state). |
| `invalid_execution_readiness_case_count` | Count of invalid readiness cases (`0` for clean state). |
| `planned_execution_step_count` | Count of planned steps (`31` for clean state). |
| `blocked_execution_step_count` | Count of blocked steps (`0` for clean state). |
| `warning_execution_step_count` | Count of warning steps (`0` for clean state). |
| `invalid_execution_step_count` | Count of invalid steps (`0` for clean state). |
| `total_authorized_file_count` | Total file count instruction (`28` for clean state). |
| `rc1_authorized_file_count` | RC1 file count (`6`). |
| `rc2_authorized_file_count` | RC2 file count (`6`). |
| `shared_authorized_file_count` | Shared file count (`16`). |
| `authorized_target_package_sections` | Sorted list of target sections (e.g. `bin`, `docs`, `lib`). |
| `authorized_execution_step_types` | Sorted list of step types in plan. |
| `authorized_execution_step_phases` | Sorted list of step phases in plan. |
| `authorized_package_roles` | Sorted list of roles in plan. |
| `authorized_artifact_types` | Sorted list of artifact types. |
| `authorized_rc_scopes` | Sorted list of RC scopes. |
| `authorized_source_reference_digests` | Sorted list of all input digests. |
| `authorized_source_reference_paths` | Sorted list of all input paths. |
| `authorized_target_package_paths` | Sorted list of all output package paths. |
| `authorized_planned_output_references` | Sorted list of all output references. |
| `authorized_execution_step_digests` | Sorted list of all plan step digests. |
| `authorized_execution_readiness_case_digests` | Sorted list of all readiness case digests. |
| `run_constraints` | Explicit run restrictions. |
| `run_allowances` | Explicit run allowances. |
| `run_prohibitions` | Explicit run prohibitions. |
| `run_guard_requirements` | Guard matrix criteria that future runners must satisfy. |
| `run_noop_boundary` | Dict representing sandbox boundaries (all flags must be `False`). |
| `run_rollback_noop_policy` | Dict representing rollback configuration (must be `metadata_only`). |
| `blocked_operation_attempt_counts` | Attempt counters (all must be `0`). |
| `specific_future_run_authorized` | Authorizes future run request in principle (`True` for clean state). |
| `metadata_only_run_authorization` | Restricts run to metadata-only validation (`True` for clean state). |
| `physical_execution_authorized` | Prohibits physical execution (`False`). |
| `archive_creation_authorized` | Prohibits ZIP/tar archive creation (`False`). |
| `file_copy_authorized` | Prohibits file copying (`False`). |
| `directory_creation_authorized` | Prohibits directory creation (`False`). |
| `upload_authorized` | Prohibits artifact upload (`False`). |
| `deployment_authorized` | Prohibits run deployment (`False`). |
| `signing_authorized` | Prohibits external key signing (`False`). |
| `external_publication_authorized` | Prohibits publishing to registries (`False`). |
| `production_mutation_authorized` | Prohibits release state mutation (`False`). |
| `physical_execution_performed` | Performed flag (`False`). |
| `archive_creation_performed` | Performed flag (`False`). |
| `file_copy_performed` | Performed flag (`False`). |
| `directory_creation_performed` | Performed flag (`False`). |
| `upload_performed` | Performed flag (`False`). |
| `deployment_performed` | Performed flag (`False`). |
| `signing_performed` | Performed flag (`False`). |
| `external_publication_performed` | Performed flag (`False`). |
| `production_mutation_performed` | Performed flag (`False`). |
| `reason_codes` | Traceable outcome codes. |
| `notes` | Diagnostic notes. |
| `software_validation_caveat` | Software caveat warning. |
| `package_assembly_run_authorization_capsule_digest` | SHA256 hex digest of the capsule. |

---

## 3. Policy & Guard Semantics

### Run Constraints

The constraints verify that no mutation is allowed and that the request is bound to the exact input report:
* `metadata_only_run_authorization`
* `specific_future_run_only`
* `non_mutating_authorization`
* `requires_execution_readiness_report_digest_match`
* `requires_execution_plan_digest_match`
* `requires_preflight_authorization_digest_match`
* `requires_same_authorized_file_count`
* `requires_same_execution_step_count`
* `requires_no_archive_creation`
* `requires_no_file_copy`
* `requires_no_directory_creation`
* `requires_no_upload`
* `requires_no_deployment`
* `requires_no_signing`
* `requires_no_external_publication`
* `requires_no_production_mutation`
* `requires_separate_run_preflight_audit`

### Run Allowances

The allowances define the narrow scope of the authorized run request:
* `specific_future_package_assembly_run_may_be_requested`
* `specific_future_run_requires_run_preflight_audit`
* `specific_future_run_requires_same_execution_readiness_digest`
* `specific_future_run_requires_same_execution_plan_digest`
* `specific_future_run_requires_same_authorized_file_count`
* `specific_future_run_requires_zero_mutation_attempts`

### Run Prohibitions

Explicit bans on mutating behavior:
* `no_archive_creation_by_run_authorization_capsule`
* `no_file_copy_by_run_authorization_capsule`
* `no_directory_creation_by_run_authorization_capsule`
* `no_upload_by_run_authorization_capsule`
* `no_deployment_by_run_authorization_capsule`
* `no_signing_by_run_authorization_capsule`
* `no_external_publication_by_run_authorization_capsule`
* `no_production_mutation_by_run_authorization_capsule`

### Run Guard Requirements

Required match conditions checked by any future validator/runner:
* `source_execution_readiness_report_digest_matches`
* `source_package_assembly_execution_plan_digest_matches`
* `source_preflight_authorization_report_digest_matches`
* `source_authorization_envelope_digest_matches`
* `source_final_package_readiness_report_digest_matches`
* `source_distribution_package_manifest_digest_matches`
* `source_dry_run_audit_report_digest_matches`
* `source_package_assembly_plan_digest_matches`
* `source_artifact_catalog_digest_matches`
* `metadata_only_run_boundary_acknowledged`
* `future_runner_requires_separate_run_preflight_audit`
* `future_runner_requires_no_archive_creation_by_capsule`
* `future_runner_requires_no_file_copy_by_capsule`
* `future_runner_requires_no_directory_creation_by_capsule`
* `future_runner_requires_no_upload_by_capsule`
* `future_runner_requires_no_deployment_by_capsule`
* `future_runner_requires_no_signing_by_capsule`
* `future_runner_requires_no_external_publication_by_capsule`
* `future_runner_requires_no_production_mutation_by_capsule`

---

## 4. Hashing Strategy & Self-Reference Exclusions

To ensure hash stability:
* Keys are sorted before canonical JSON serialization.
* Self-referential digest fields are popped before hashing:
  * `package_assembly_run_authorization_capsule_digest` is popped when hashing the capsule.

---

## 5. Caveats, Limitations & Sandbox Boundaries

* **Software Caveat**: *"Validation is shadow/sandbox software validation, not quantum hardware validation."*
* **Limitations**: The run authorization capsule does not physically package the candidate, nor does it guarantee execution-readiness of the runtime platform.

---

## 6. Next Recommended Build Step

The next recommended governance bridge is the:
```text
Package Assembly Run Authorization Validator / Run Preflight Auditor
```
That future step will independently reload this capsule, recompute its digest, validate the execution-readiness report reference, and verify all run constraints, allowances, prohibitions, guard requirements, and no-op boundaries, producing a run-preflight audit report.
