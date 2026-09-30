# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Run Execution Blueprint.
Consumes the verified run-preflight audit report and defines runner-facing blueprint metadata.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Tuple, Optional

# Adjacent waveguide modules
from sol_waveguide_rc_promotion_ledger import (
    hash_data,
    normalize_to_repo_path,
    REPO_ROOT
)
from sol_waveguide_package_assembly_run_authorization_validator import (
    validate_waveguide_package_run_preflight_audit_report,
    validate_waveguide_package_run_noop_boundary,
    validate_waveguide_package_run_rollback_noop_policy
)


@dataclass
class WaveguidePackageRunBlueprintPhase:
    run_blueprint_phase_id: str
    phase_index: int
    phase_name: str
    phase_type: str  # run_preflight_validation, source_reference_verification, target_layout_verification, artifact_instruction_planning, noop_boundary_verification, abort_condition_planning, final_runner_blueprint
    phase_status: str  # run_blueprint_phase_ready, etc.
    source_run_preflight_report_digest: str
    source_run_authorization_capsule_digest: str
    source_execution_readiness_report_digest: str
    expected_input_reference: str
    expected_input_kind: str
    expected_output_reference: str
    expected_output_kind: str
    target_package_section: str
    target_package_path: str
    artifact_digest: str
    artifact_type: str
    package_role: str
    rc_scope: str
    required_guard_conditions: List[str]
    abort_conditions: List[str]
    safety_gates: List[str]
    prohibited_operations: List[str]
    noop_boundary: Dict[str, bool]
    run_rollback_noop_policy: Dict[str, Any]
    physical_execution_performed: bool
    archive_creation_performed: bool
    file_copy_performed: bool
    directory_creation_performed: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    run_blueprint_phase_digest: str = ""


@dataclass
class WaveguidePackageAssemblyRunExecutionBlueprint:
    package_assembly_run_execution_blueprint_id: str
    package_assembly_run_execution_blueprint_version: int
    run_blueprint_status: str  # package_run_blueprint_ready, etc.
    source_run_preflight_report_digest: str
    source_run_authorization_capsule_digest: str
    source_execution_readiness_report_digest: str
    source_package_assembly_execution_plan_digest: str
    source_preflight_authorization_report_digest: str
    source_authorization_envelope_digest: str
    source_final_package_readiness_report_digest: str
    source_distribution_package_manifest_digest: str
    source_dry_run_audit_report_digest: str
    source_package_assembly_plan_digest: str
    source_artifact_catalog_digest: str
    run_request_id: str
    run_request_kind: str
    run_authorization_status: str
    run_authorization_decision: str
    blueprint_phases: List[WaveguidePackageRunBlueprintPhase]
    ready_blueprint_phases: List[str]
    blocked_blueprint_phases: List[str]
    warning_blueprint_phases: List[str]
    invalid_blueprint_phases: List[str]
    ready_blueprint_phase_count: int
    blocked_blueprint_phase_count: int
    warning_blueprint_phase_count: int
    invalid_blueprint_phase_count: int
    planned_execution_step_count: int
    total_authorized_file_count: int
    rc1_authorized_file_count: int
    rc2_authorized_file_count: int
    shared_authorized_file_count: int
    expected_input_count: int
    expected_output_count: int
    target_package_sections: List[str]
    phase_types_indexed: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    rc_scopes_indexed: List[str]
    expected_input_references: List[str]
    expected_output_references: List[str]
    target_package_paths: List[str]
    artifact_digests: List[str]
    phase_digests: List[str]
    abort_condition_matrix: List[str]
    safety_gate_matrix: List[str]
    expected_input_index: Dict[str, str]
    expected_output_index: Dict[str, str]
    noop_boundary: Dict[str, bool]
    rollback_noop_policy: Dict[str, Any]
    blocked_operation_attempt_counts: Dict[str, int]
    physical_execution_performed: bool
    archive_creation_performed: bool
    file_copy_performed: bool
    directory_creation_performed: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    software_validation_caveat: str
    package_assembly_run_execution_blueprint_digest: str = ""


def hash_waveguide_package_run_blueprint_phase(phase: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of phase excluding phase digest.
    """
    if hasattr(phase, "__dict__"):
        p_dict = asdict(phase)
    elif isinstance(phase, dict):
        p_dict = dict(phase)
    else:
        raise TypeError("phase must be a dictionary or a dataclass instance")

    p_dict_copy = dict(p_dict)
    p_dict_copy.pop("run_blueprint_phase_digest", None)
    return hash_data(p_dict_copy)


def hash_waveguide_package_assembly_run_execution_blueprint(blueprint: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of blueprint excluding blueprint digest.
    """
    if hasattr(blueprint, "__dict__"):
        b_dict = asdict(blueprint)
    elif isinstance(blueprint, dict):
        b_dict = dict(blueprint)
    else:
        raise TypeError("blueprint must be a dictionary or a dataclass instance")

    b_dict_copy = dict(b_dict)
    b_dict_copy.pop("package_assembly_run_execution_blueprint_digest", None)
    return hash_data(b_dict_copy)


def _load_dict(path_or_dict: Any) -> Optional[Dict[str, Any]]:
    if isinstance(path_or_dict, str):
        path = normalize_to_repo_path(path_or_dict)
        full_path = os.path.join(REPO_ROOT, path)
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    elif hasattr(path_or_dict, "__dict__"):
        return asdict(path_or_dict)
    elif isinstance(path_or_dict, dict):
        return dict(path_or_dict)
    return None


def build_waveguide_package_run_abort_condition_matrix() -> List[str]:
    return [
        "execution_readiness_digest_mismatch",
        "preflight_report_digest_mismatch",
        "authorization_capsule_digest_mismatch",
        "plan_digest_mismatch",
        "step_digest_mismatch",
        "physical_execution_authorized_is_true",
        "mutation_flag_is_true",
        "blocked_operation_attempt_count_nonzero",
        "non_contiguous_phase_index",
        "file_count_mismatch"
    ]


def build_waveguide_package_run_safety_gate_matrix() -> List[str]:
    return [
        "preflight_audit_report_verified",
        "run_authorization_capsule_verified",
        "execution_readiness_report_verified",
        "execution_plan_verified",
        "metadata_only_boundary_active",
        "zero_blocked_operation_attempts",
        "all_phases_valid"
    ]


def build_waveguide_package_run_expected_input_index(phases: List[Any]) -> Dict[str, str]:
    res = {}
    for p in phases:
        p_dict = _load_dict(p)
        if p_dict and p_dict.get("phase_type") == "artifact_instruction_planning":
            ref = p_dict.get("expected_input_reference")
            digest = p_dict.get("artifact_digest")
            if ref and digest:
                res[ref] = digest
    return res


def build_waveguide_package_run_expected_output_index(phases: List[Any]) -> Dict[str, str]:
    res = {}
    for p in phases:
        p_dict = _load_dict(p)
        if p_dict and p_dict.get("phase_type") == "artifact_instruction_planning":
            ref = p_dict.get("expected_output_reference")
            digest = p_dict.get("artifact_digest")
            if ref and digest:
                res[ref] = digest
    return res


def build_waveguide_package_run_blueprint_phase(
    phase_index: int,
    phase_name: str,
    phase_type: str,
    preflight_dict: Dict[str, Any],
    step_dict: Optional[Dict[str, Any]] = None
) -> WaveguidePackageRunBlueprintPhase:
    """
    Builds a single execution blueprint phase.
    """
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    reasons = ["RUN_BLUEPRINT_PHASE_CANONICAL"]

    noop_boundary = {
        "physical_execution_authorized": False,
        "archive_creation_authorized": False,
        "file_copy_authorized": False,
        "directory_creation_authorized": False,
        "upload_authorized": False,
        "deployment_authorized": False,
        "signing_authorized": False,
        "external_publication_authorized": False,
        "production_mutation_authorized": False,
        "physical_execution_performed": False,
        "archive_creation_performed": False,
        "file_copy_performed": False,
        "directory_creation_performed": False,
        "upload_performed": False,
        "deployment_performed": False,
        "signing_performed": False,
        "external_publication_performed": False,
        "production_mutation_performed": False
    }

    rollback_noop_policy = {
        "rollback_required": False,
        "rollback_reason": "no_physical_run_performed",
        "rollback_scope": "metadata_only",
        "rollback_operations": []
    }

    prohibited_ops = [
        "no_archive_creation_by_run_authorization_capsule",
        "no_file_copy_by_run_authorization_capsule",
        "no_directory_creation_by_run_authorization_capsule",
        "no_upload_by_run_authorization_capsule",
        "no_deployment_by_run_authorization_capsule",
        "no_signing_by_run_authorization_capsule",
        "no_external_publication_by_run_authorization_capsule",
        "no_production_mutation_by_run_authorization_capsule"
    ]

    guards = preflight_dict.get("run_guard_requirements", [])
    abort_conds = build_waveguide_package_run_abort_condition_matrix()
    gates = build_waveguide_package_run_safety_gate_matrix()

    # Extract digests from preflight
    preflight_digest = preflight_dict.get("run_preflight_report_digest", "")
    capsule_digest = preflight_dict.get("source_run_authorization_capsule_digest", "")
    readiness_digest = preflight_dict.get("source_execution_readiness_report_digest", "")

    # Default metadata fields
    expected_input_ref = ""
    expected_input_k = "none"
    expected_output_ref = ""
    expected_output_k = "none"
    section = ""
    path = ""
    digest = ""
    art_type = ""
    role = ""
    scope = ""

    if step_dict and phase_type == "artifact_instruction_planning":
        expected_input_ref = step_dict.get("source_reference_path", "")
        expected_input_k = step_dict.get("input_reference_kind", "none")
        expected_output_ref = step_dict.get("target_package_path", "")
        expected_output_k = step_dict.get("planned_output_kind", "none")
        section = step_dict.get("target_package_section", "")
        path = step_dict.get("target_package_path", "")
        digest = step_dict.get("artifact_digest", "")
        art_type = step_dict.get("artifact_type", "")
        role = step_dict.get("package_role", "")
        scope = step_dict.get("rc_scope", "")

    phase = WaveguidePackageRunBlueprintPhase(
        run_blueprint_phase_id=f"SOL-WAVEGUIDE-RUN-PHASE-{phase_index:03d}",
        phase_index=phase_index,
        phase_name=phase_name,
        phase_type=phase_type,
        phase_status="run_blueprint_phase_ready",
        source_run_preflight_report_digest=preflight_digest,
        source_run_authorization_capsule_digest=capsule_digest,
        source_execution_readiness_report_digest=readiness_digest,
        expected_input_reference=expected_input_ref,
        expected_input_kind=expected_input_k,
        expected_output_reference=expected_output_ref,
        expected_output_kind=expected_output_k,
        target_package_section=section,
        target_package_path=path,
        artifact_digest=digest,
        artifact_type=art_type,
        package_role=role,
        rc_scope=scope,
        required_guard_conditions=sorted(guards),
        abort_conditions=sorted(abort_conds),
        safety_gates=sorted(gates),
        prohibited_operations=sorted(prohibited_ops),
        noop_boundary=noop_boundary,
        run_rollback_noop_policy=rollback_noop_policy,
        physical_execution_performed=False,
        archive_creation_performed=False,
        file_copy_performed=False,
        directory_creation_performed=False,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        reason_codes=sorted(list(set(reasons))),
        notes=[],
        software_validation_caveat=caveat
    )
    phase.run_blueprint_phase_digest = hash_waveguide_package_run_blueprint_phase(phase)
    return phase


def validate_waveguide_package_run_blueprint_phase(phase: Any) -> Tuple[bool, List[str]]:
    phase_dict = _load_dict(phase)
    if not phase_dict:
        return False, ["RUN_BLUEPRINT_PHASE_INVALID"]

    reasons = []
    is_valid = True

    # Validate digest
    recorded = phase_dict.get("run_blueprint_phase_digest", "")
    recomputed = hash_waveguide_package_run_blueprint_phase(phase_dict)
    if recorded != recomputed or not recorded:
        is_valid = False
        reasons.append("RUN_BLUEPRINT_PHASE_DIGEST_MISMATCH")

    # Required lists present
    required_lists = ["required_guard_conditions", "abort_conditions", "safety_gates", "prohibited_operations"]
    for lst in required_lists:
        if not phase_dict.get(lst):
            is_valid = False
            reasons.append(f"RUN_BLUEPRINT_PHASE_MISSING_{lst.upper()}")

    if not phase_dict.get("noop_boundary") or not phase_dict.get("run_rollback_noop_policy"):
        is_valid = False

    # Performed mutation check
    performed_flags = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in performed_flags:
        if phase_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"RUN_BLUEPRINT_PHASE_MUTATION_PERFORMED_{flag.upper()}")

    status = "run_blueprint_phase_ready" if is_valid else "run_blueprint_phase_invalid"
    phase_dict["phase_status"] = status

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_assembly_run_execution_blueprint(
    run_preflight_report_path_or_dict: Any
) -> WaveguidePackageAssemblyRunExecutionBlueprint:
    """
    Builds the top-level run execution blueprint.
    """
    preflight_dict = _load_dict(run_preflight_report_path_or_dict)
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not preflight_dict:
        return WaveguidePackageAssemblyRunExecutionBlueprint(
            package_assembly_run_execution_blueprint_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUN-EXECUTION-BLUEPRINT",
            package_assembly_run_execution_blueprint_version=1,
            run_blueprint_status="package_run_blueprint_invalid",
            source_run_preflight_report_digest="",
            source_run_authorization_capsule_digest="",
            source_execution_readiness_report_digest="",
            source_package_assembly_execution_plan_digest="",
            source_preflight_authorization_report_digest="",
            source_authorization_envelope_digest="",
            source_final_package_readiness_report_digest="",
            source_distribution_package_manifest_digest="",
            source_dry_run_audit_report_digest="",
            source_package_assembly_plan_digest="",
            source_artifact_catalog_digest="",
            run_request_id="SOL-WAVEGUIDE-RUN-REQUEST-UNKNOWN",
            run_request_kind="metadata_only_future_package_assembly_run",
            run_authorization_status="package_run_invalid",
            run_authorization_decision="invalid_run_authorization",
            blueprint_phases=[],
            ready_blueprint_phases=[],
            blocked_blueprint_phases=[],
            warning_blueprint_phases=[],
            invalid_blueprint_phases=[],
            ready_blueprint_phase_count=0,
            blocked_blueprint_phase_count=0,
            warning_blueprint_phase_count=0,
            invalid_blueprint_phase_count=0,
            planned_execution_step_count=0,
            total_authorized_file_count=0,
            rc1_authorized_file_count=0,
            rc2_authorized_file_count=0,
            shared_authorized_file_count=0,
            expected_input_count=0,
            expected_output_count=0,
            target_package_sections=[],
            phase_types_indexed=[],
            package_roles_indexed=[],
            artifact_types_indexed=[],
            rc_scopes_indexed=[],
            expected_input_references=[],
            expected_output_references=[],
            target_package_paths=[],
            artifact_digests=[],
            phase_digests=[],
            abort_condition_matrix=[],
            safety_gate_matrix=[],
            expected_input_index={},
            expected_output_index={},
            noop_boundary={},
            rollback_noop_policy={},
            blocked_operation_attempt_counts={},
            physical_execution_performed=False,
            archive_creation_performed=False,
            file_copy_performed=False,
            directory_creation_performed=False,
            upload_performed=False,
            deployment_performed=False,
            signing_performed=False,
            external_publication_performed=False,
            production_mutation_performed=False,
            reason_codes=["RUN_AUTH_SOURCE_EXECUTION_READINESS_REPORT_INVALID", "PACKAGE_RUN_BLUEPRINT_INVALID"],
            software_validation_caveat=caveat
        )

    # Validate the source preflight report
    is_preflight_ok, _ = validate_waveguide_package_run_preflight_audit_report(preflight_dict)
    preflight_status = preflight_dict.get("run_preflight_report_status", "")

    reasons = ["RUN_BLUEPRINT_CANONICAL"]
    is_valid = True

    if not is_preflight_ok or preflight_status != "package_run_preflight_verified":
        is_valid = False
        reasons.append("RUN_BLUEPRINT_PREFLIGHT_REPORT_INVALID")
    else:
        reasons.append("RUN_BLUEPRINT_PREFLIGHT_REPORT_VALID")

    # Load execution plan or readiness report to map file instructions
    plan_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_PACKAGE_ASSEMBLY_EXECUTION_PLAN.json")
    plan_dict = _load_dict(plan_path)

    phases = []
    if plan_dict and is_valid:
        # Phase 0: run_preflight_validation
        phases.append(build_waveguide_package_run_blueprint_phase(
            0, "Run Preflight Validation", "run_preflight_validation", preflight_dict
        ))
        # Phase 1: source_reference_verification
        phases.append(build_waveguide_package_run_blueprint_phase(
            1, "Source Reference Verification", "source_reference_verification", preflight_dict
        ))
        # Phase 2: target_layout_verification
        phases.append(build_waveguide_package_run_blueprint_phase(
            2, "Target Layout Verification", "target_layout_verification", preflight_dict
        ))

        # Phases 3-30: 28 file instruction steps
        steps = plan_dict.get("execution_steps", [])
        file_steps = [s for s in steps if s.get("step_type") == "prepare_metadata_instruction"]
        for idx, step in enumerate(file_steps):
            phase_idx = idx + 3
            phases.append(build_waveguide_package_run_blueprint_phase(
                phase_idx, f"Artifact Instruction Planning - Step {idx:02d}", "artifact_instruction_planning", preflight_dict, step
            ))

        # Phase 31: noop_boundary_verification
        phases.append(build_waveguide_package_run_blueprint_phase(
            31, "No-Op Boundary Verification", "noop_boundary_verification", preflight_dict
        ))
        # Phase 32: abort_condition_planning
        phases.append(build_waveguide_package_run_blueprint_phase(
            32, "Abort Condition Planning", "abort_condition_planning", preflight_dict
        ))
        # Phase 33: final_runner_blueprint
        phases.append(build_waveguide_package_run_blueprint_phase(
            33, "Final Runner Blueprint", "final_runner_blueprint", preflight_dict
        ))

    # Validate all phases
    ready_phases = []
    blocked_phases = []
    warning_phases = []
    invalid_phases = []

    for p in phases:
        p_ok, _ = validate_waveguide_package_run_blueprint_phase(p)
        if not p_ok:
            is_valid = False
            invalid_phases.append(p.run_blueprint_phase_id)
        else:
            ready_phases.append(p.run_blueprint_phase_id)

    if len(phases) != 34:
        is_valid = False

    status = "package_run_blueprint_ready" if is_valid else "package_run_blueprint_invalid"
    if is_valid:
        reasons.append("PACKAGE_RUN_BLUEPRINT_READY")
    else:
        reasons.append("PACKAGE_RUN_BLUEPRINT_INVALID")

    # Matrices and indices
    abort_matrix = build_waveguide_package_run_abort_condition_matrix()
    gate_matrix = build_waveguide_package_run_safety_gate_matrix()
    input_idx = build_waveguide_package_run_expected_input_index(phases)
    output_idx = build_waveguide_package_run_expected_output_index(phases)

    target_package_sections = sorted(preflight_dict.get("authorized_target_package_sections", []))
    phase_types_indexed = sorted(list(set(p.phase_type for p in phases)))
    package_roles_indexed = sorted(preflight_dict.get("authorized_package_roles", []))
    artifact_types_indexed = sorted(preflight_dict.get("authorized_artifact_types", []))
    rc_scopes_indexed = sorted(preflight_dict.get("authorized_rc_scopes", []))
    expected_input_references = sorted(list(input_idx.keys()))
    expected_output_references = sorted(list(output_idx.keys()))
    target_package_paths = sorted(preflight_dict.get("authorized_target_package_paths", []))
    artifact_digests = sorted(preflight_dict.get("authorized_source_reference_digests", []))
    phase_digests = sorted([p.run_blueprint_phase_digest for p in phases])

    noop_boundary = {
        "physical_execution_authorized": False,
        "archive_creation_authorized": False,
        "file_copy_authorized": False,
        "directory_creation_authorized": False,
        "upload_authorized": False,
        "deployment_authorized": False,
        "signing_authorized": False,
        "external_publication_authorized": False,
        "production_mutation_authorized": False,
        "physical_execution_performed": False,
        "archive_creation_performed": False,
        "file_copy_performed": False,
        "directory_creation_performed": False,
        "upload_performed": False,
        "deployment_performed": False,
        "signing_performed": False,
        "external_publication_performed": False,
        "production_mutation_performed": False
    }

    rollback_noop_policy = {
        "rollback_required": False,
        "rollback_reason": "no_physical_run_performed",
        "rollback_scope": "metadata_only",
        "rollback_operations": []
    }

    blocked_operation_attempt_counts = {
        "archive_creation": 0,
        "deployment": 0,
        "directory_creation": 0,
        "external_publication": 0,
        "external_signing": 0,
        "file_copy": 0,
        "production_mutation": 0,
        "upload": 0
    }

    blueprint = WaveguidePackageAssemblyRunExecutionBlueprint(
        package_assembly_run_execution_blueprint_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUN-EXECUTION-BLUEPRINT",
        package_assembly_run_execution_blueprint_version=1,
        run_blueprint_status=status,
        source_run_preflight_report_digest=preflight_dict.get("run_preflight_report_digest", ""),
        source_run_authorization_capsule_digest=preflight_dict.get("source_run_authorization_capsule_digest", ""),
        source_execution_readiness_report_digest=preflight_dict.get("source_execution_readiness_report_digest", ""),
        source_package_assembly_execution_plan_digest=preflight_dict.get("source_package_assembly_execution_plan_digest", ""),
        source_preflight_authorization_report_digest=preflight_dict.get("source_preflight_authorization_report_digest", ""),
        source_authorization_envelope_digest=preflight_dict.get("source_authorization_envelope_digest", ""),
        source_final_package_readiness_report_digest=preflight_dict.get("source_final_package_readiness_report_digest", ""),
        source_distribution_package_manifest_digest=preflight_dict.get("source_distribution_package_manifest_digest", ""),
        source_dry_run_audit_report_digest=preflight_dict.get("source_dry_run_audit_report_digest", ""),
        source_package_assembly_plan_digest=preflight_dict.get("source_package_assembly_plan_digest", ""),
        source_artifact_catalog_digest=preflight_dict.get("source_artifact_catalog_digest", ""),
        run_request_id=preflight_dict.get("run_request_id", ""),
        run_request_kind=preflight_dict.get("run_request_kind", ""),
        run_authorization_status=preflight_dict.get("run_authorization_status", ""),
        run_authorization_decision=preflight_dict.get("run_authorization_decision", ""),
        blueprint_phases=phases,
        ready_blueprint_phases=ready_phases,
        blocked_blueprint_phases=blocked_phases,
        warning_blueprint_phases=warning_phases,
        invalid_blueprint_phases=invalid_phases,
        ready_blueprint_phase_count=len(ready_phases),
        blocked_blueprint_phase_count=len(blocked_phases),
        warning_blueprint_phase_count=len(warning_phases),
        invalid_blueprint_phase_count=len(invalid_phases),
        planned_execution_step_count=preflight_dict.get("planned_execution_step_count", 0),
        total_authorized_file_count=preflight_dict.get("total_authorized_file_count", 0),
        rc1_authorized_file_count=preflight_dict.get("rc1_authorized_file_count", 0),
        rc2_authorized_file_count=preflight_dict.get("rc2_authorized_file_count", 0),
        shared_authorized_file_count=preflight_dict.get("shared_authorized_file_count", 0),
        expected_input_count=len(input_idx),
        expected_output_count=len(output_idx),
        target_package_sections=target_package_sections,
        phase_types_indexed=phase_types_indexed,
        package_roles_indexed=package_roles_indexed,
        artifact_types_indexed=artifact_types_indexed,
        rc_scopes_indexed=rc_scopes_indexed,
        expected_input_references=expected_input_references,
        expected_output_references=expected_output_references,
        target_package_paths=target_package_paths,
        artifact_digests=artifact_digests,
        phase_digests=phase_digests,
        abort_condition_matrix=sorted(abort_matrix),
        safety_gate_matrix=sorted(gate_matrix),
        expected_input_index=input_idx,
        expected_output_index=output_idx,
        noop_boundary=noop_boundary,
        rollback_noop_policy=rollback_noop_policy,
        blocked_operation_attempt_counts=blocked_operation_attempt_counts,
        physical_execution_performed=False,
        archive_creation_performed=False,
        file_copy_performed=False,
        directory_creation_performed=False,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        reason_codes=sorted(list(set(reasons))),
        software_validation_caveat=caveat
    )

    blueprint.package_assembly_run_execution_blueprint_digest = hash_waveguide_package_assembly_run_execution_blueprint(blueprint)
    return blueprint


def validate_waveguide_package_assembly_run_execution_blueprint(blueprint: Any) -> Tuple[bool, List[str]]:
    """
    Validates a run execution blueprint structure and logic.
    """
    blueprint_dict = _load_dict(blueprint)
    if not blueprint_dict:
        return False, ["PACKAGE_RUN_BLUEPRINT_INVALID"]

    reasons = []
    is_valid = True

    if blueprint_dict.get("package_assembly_run_execution_blueprint_id") != "SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-RUN-EXECUTION-BLUEPRINT":
        is_valid = False
        reasons.append("RUN_BLUEPRINT_INVALID_ID")

    if blueprint_dict.get("package_assembly_run_execution_blueprint_version") != 1:
        is_valid = False
        reasons.append("RUN_BLUEPRINT_INVALID_VERSION")

    # Validate phases
    phases = blueprint_dict.get("blueprint_phases", [])
    if not phases or len(phases) != 34:
        is_valid = False
        reasons.append("RUN_BLUEPRINT_PHASE_COUNT_MISMATCH")
    else:
        for p in phases:
            recorded = p.get("run_blueprint_phase_digest", "")
            recomputed = hash_waveguide_package_run_blueprint_phase(p)
            if recorded != recomputed or not recorded:
                is_valid = False
                reasons.append("RUN_BLUEPRINT_PHASE_DIGEST_MISMATCH")

    # Verify no-op boundary and rollback policy
    if not validate_waveguide_package_run_noop_boundary(blueprint_dict.get("noop_boundary", {})):
        is_valid = False
    if not validate_waveguide_package_run_rollback_noop_policy(blueprint_dict.get("rollback_noop_policy", {})):
        is_valid = False

    # Check that performed flags in report are false
    flag_fields = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for flag in flag_fields:
        if blueprint_dict.get(flag) is not False:
            is_valid = False
            reasons.append(f"RUN_BLUEPRINT_MUTATION_PERFORMED_{flag.upper()}")

    # Check blueprint digest
    recorded_digest = blueprint_dict.get("package_assembly_run_execution_blueprint_digest", "")
    recomputed_digest = hash_waveguide_package_assembly_run_execution_blueprint(blueprint_dict)
    if recorded_digest != recomputed_digest or not recorded_digest:
        is_valid = False
        reasons.append("RUN_BLUEPRINT_DIGEST_MISMATCH")

    status = blueprint_dict.get("run_blueprint_status", "")
    if is_valid and status == "package_run_blueprint_ready":
        reasons.append("PACKAGE_RUN_BLUEPRINT_READY")
    else:
        is_valid = False
        reasons.append("PACKAGE_RUN_BLUEPRINT_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_assembly_run_execution_blueprint(blueprint: Any) -> str:
    blueprint_dict = _load_dict(blueprint)
    if not blueprint_dict:
        return "Invalid Run Execution Blueprint"

    status = blueprint_dict.get("run_blueprint_status", "unknown")
    digest = blueprint_dict.get("package_assembly_run_execution_blueprint_digest", "")
    run_id = blueprint_dict.get("run_request_id", "")

    return (
        f"SOL Waveguide Run Execution Blueprint Summary:\n"
        f"  Blueprint Status: {status}\n"
        f"  Run Request ID: {run_id}\n"
        f"  Blueprint Digest: {digest}\n"
        f"  Total Blueprint Phases: {len(blueprint_dict.get('blueprint_phases', []))}\n"
    )


def export_waveguide_package_assembly_run_execution_blueprint(blueprint: Any, filepath: str) -> None:
    blueprint_dict = _load_dict(blueprint)
    if not blueprint_dict:
        raise ValueError("Cannot export invalid run execution blueprint data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(blueprint_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_assembly_run_execution_blueprints(left: Any, right: Any) -> Dict[str, Any]:
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs


def index_waveguide_package_run_blueprint_phases_by_type(phases: List[Any]) -> Dict[str, List[Any]]:
    idx = {}
    for p in phases:
        p_dict = _load_dict(p)
        if p_dict:
            ptype = p_dict.get("phase_type", "unknown")
            idx.setdefault(ptype, []).append(p_dict)
    return idx


def index_waveguide_package_run_blueprint_phases_by_status(phases: List[Any]) -> Dict[str, List[Any]]:
    idx = {}
    for p in phases:
        p_dict = _load_dict(p)
        if p_dict:
            status = p_dict.get("phase_status", "unknown")
            idx.setdefault(status, []).append(p_dict)
    return idx
