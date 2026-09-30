# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Package Assembly Execution Plan.
Consumes the Preflight Authorization Audit Report and defines the exact ordered execution metadata
for a future controlled package assembly operation without performing physical operations.
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
from sol_waveguide_package_assembly_authorization_validator import (
    validate_waveguide_package_preflight_authorization_audit_report
)


@dataclass
class WaveguidePackageAssemblyExecutionStep:
    package_execution_step_id: str
    step_index: int
    step_name: str
    step_type: str
    step_phase: str
    step_status: str
    source_reference_digest: str
    source_reference_path: str
    input_reference_kind: str
    planned_output_reference: str
    planned_output_kind: str
    target_package_section: str
    target_package_path: str
    artifact_digest: str
    artifact_type: str
    package_role: str
    rc_scope: str
    requires_preflight_authorization: bool
    requires_same_authorization_envelope_digest: bool
    requires_same_preflight_report_digest: bool
    requires_same_final_readiness_report_digest: bool
    requires_same_package_manifest_digest: bool
    requires_same_dry_run_report_digest: bool
    requires_same_artifact_catalog_digest: bool
    guard_conditions: List[str]
    prohibited_operations: List[str]
    no_op_boundary: bool
    physical_execution_performed: bool
    archive_created: bool
    file_copied: bool
    directory_created: bool
    upload_performed: bool
    deployment_performed: bool
    signing_performed: bool
    external_publication_performed: bool
    production_mutation_performed: bool
    reason_codes: List[str]
    notes: List[str]
    software_validation_caveat: str
    package_execution_step_digest: str = ""


@dataclass
class WaveguidePackageAssemblyExecutionPlan:
    package_assembly_execution_plan_id: str
    package_assembly_execution_plan_version: int
    package_assembly_execution_plan_status: str  # package_execution_plan_ready, etc.
    source_preflight_authorization_report_digest: str
    source_authorization_envelope_digest: str
    source_final_package_readiness_report_digest: str
    source_distribution_package_manifest_digest: str
    source_dry_run_audit_report_digest: str
    source_package_assembly_plan_digest: str
    source_artifact_catalog_digest: str
    execution_steps: List[WaveguidePackageAssemblyExecutionStep]
    planned_execution_steps: List[str]
    blocked_execution_steps: List[str]
    warning_execution_steps: List[str]
    invalid_execution_steps: List[str]
    planned_execution_step_count: int
    blocked_execution_step_count: int
    warning_execution_step_count: int
    invalid_execution_step_count: int
    total_authorized_file_count: int
    rc1_authorized_file_count: int
    rc2_authorized_file_count: int
    shared_authorized_file_count: int
    planned_input_reference_count: int
    planned_output_reference_count: int
    target_package_sections: List[str]
    execution_step_types_indexed: List[str]
    execution_step_phases_indexed: List[str]
    package_roles_indexed: List[str]
    artifact_types_indexed: List[str]
    rc_scopes_indexed: List[str]
    source_reference_digests: List[str]
    source_reference_paths: List[str]
    target_package_paths: List[str]
    planned_output_references: List[str]
    execution_guard_matrix: List[str]
    execution_input_reference_index: Dict[str, str]
    execution_output_reference_index: Dict[str, str]
    noop_sandbox_boundary: Dict[str, Any]
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
    package_assembly_execution_plan_digest: str = ""


def hash_waveguide_package_assembly_execution_step(step: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of step excluding self-digest.
    """
    if hasattr(step, "__dict__"):
        s_dict = asdict(step)
    elif isinstance(step, dict):
        s_dict = dict(step)
    else:
        raise TypeError("step must be a dictionary or a dataclass instance")

    s_dict_copy = dict(s_dict)
    s_dict_copy.pop("package_execution_step_digest", None)
    return hash_data(s_dict_copy)


def hash_waveguide_package_assembly_execution_plan(plan: Any) -> str:
    """
    Computes deterministic SHA256 hex digest of plan excluding self-digest.
    """
    if hasattr(plan, "__dict__"):
        p_dict = asdict(plan)
    elif isinstance(plan, dict):
        p_dict = dict(plan)
    else:
        raise TypeError("plan must be a dictionary or a dataclass instance")

    p_dict_copy = dict(p_dict)
    p_dict_copy.pop("package_assembly_execution_plan_digest", None)
    return hash_data(p_dict_copy)


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


def build_waveguide_package_assembly_execution_step(
    step_id: str,
    index: int,
    name: str,
    stype: str,
    phase: str,
    source_digest: str,
    source_path: str,
    input_kind: str,
    output_ref: str,
    output_kind: str,
    section: str,
    tpath: str,
    adigest: str,
    atype: str,
    role: str,
    scope: str,
    preflight_report_digest: str
) -> WaveguidePackageAssemblyExecutionStep:
    """
    Helper to construct an execution step.
    """
    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."
    guards = sorted([
        "source_preflight_authorization_report_digest_matches",
        "source_authorization_envelope_digest_matches",
        "source_final_package_readiness_report_digest_matches",
        "source_distribution_package_manifest_digest_matches",
        "source_dry_run_audit_report_digest_matches",
        "source_package_assembly_plan_digest_matches",
        "source_artifact_catalog_digest_matches",
        "metadata_only_boundary_acknowledged",
        "no_archive_creation_in_this_plan",
        "no_file_copy_in_this_plan",
        "no_directory_creation_in_this_plan",
        "no_upload_in_this_plan",
        "no_deployment_in_this_plan",
        "no_signing_in_this_plan",
        "no_external_publication_in_this_plan",
        "no_production_mutation_in_this_plan",
        "future_runner_requires_separate_execution_authorization"
    ])
    prohibited = sorted([
        "no_archive_creation_in_this_plan",
        "no_file_copy_in_this_plan",
        "no_directory_creation_in_this_plan",
        "no_upload_in_this_plan",
        "no_deployment_in_this_plan",
        "no_signing_in_this_plan",
        "no_external_publication_in_this_plan",
        "no_production_mutation_in_this_plan"
    ])

    step = WaveguidePackageAssemblyExecutionStep(
        package_execution_step_id=step_id,
        step_index=index,
        step_name=name,
        step_type=stype,
        step_phase=phase,
        step_status="execution_step_planned",
        source_reference_digest=source_digest,
        source_reference_path=source_path,
        input_reference_kind=input_kind,
        planned_output_reference=output_ref,
        planned_output_kind=output_kind,
        target_package_section=section,
        target_package_path=tpath,
        artifact_digest=adigest,
        artifact_type=atype,
        package_role=role,
        rc_scope=scope,
        requires_preflight_authorization=True,
        requires_same_authorization_envelope_digest=True,
        requires_same_preflight_report_digest=True,
        requires_same_final_readiness_report_digest=True,
        requires_same_package_manifest_digest=True,
        requires_same_dry_run_report_digest=True,
        requires_same_artifact_catalog_digest=True,
        guard_conditions=guards,
        prohibited_operations=prohibited,
        no_op_boundary=True,
        physical_execution_performed=False,
        archive_created=False,
        file_copied=False,
        directory_created=False,
        upload_performed=False,
        deployment_performed=False,
        signing_performed=False,
        external_publication_performed=False,
        production_mutation_performed=False,
        reason_codes=["PACKAGE_EXECUTION_STEP_PLANNED", "PACKAGE_EXECUTION_STEP_CANONICAL"],
        notes=[],
        software_validation_caveat=caveat
    )
    step.package_execution_step_digest = hash_waveguide_package_assembly_execution_step(step)
    return step


def validate_waveguide_package_assembly_execution_step(step: Any) -> Tuple[bool, List[str]]:
    """
    Validates a single execution step.
    """
    step_dict = _load_dict(step)
    if not step_dict:
        return False, ["PACKAGE_EXECUTION_STEP_INVALID"]

    reasons = []
    is_valid = True

    # 1. Step index must be deterministic and non-negative
    idx = step_dict.get("step_index", -1)
    if idx < 0:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_STEP_INVALID_INDEX")

    # 2. String fields presence
    for f in ["package_execution_step_id", "step_name", "step_type", "step_phase", "step_status"]:
        if not step_dict.get(f):
            is_valid = False
            reasons.append(f"PACKAGE_EXECUTION_STEP_MISSING_{f.upper()}")

    # 3. Status checks
    status = step_dict.get("step_status", "")
    expected_statuses = ["execution_step_planned", "execution_step_blocked", "execution_step_warning", "execution_step_invalid"]
    if status not in expected_statuses:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_STEP_UNRECOGNIZED_STATUS")

    # 4. Prohibited physical actions
    mutations = [
        "physical_execution_performed", "archive_created", "file_copied", "directory_created",
        "upload_performed", "deployment_performed", "signing_performed",
        "external_publication_performed", "production_mutation_performed"
    ]
    for m in mutations:
        if step_dict.get(m) is not False:
            is_valid = False
            reasons.append(f"PACKAGE_EXECUTION_STEP_MUTATION_AUTHORIZED_{m.upper()}")

    # 5. Guard conditions and Prohibitions check
    if not step_dict.get("guard_conditions"):
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_STEP_MISSING_GUARDS")
    if not step_dict.get("prohibited_operations"):
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_STEP_MISSING_PROHIBITIONS")
    if step_dict.get("no_op_boundary") is not True:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_STEP_MISSING_NOOP_BOUNDARY")
    if not step_dict.get("software_validation_caveat"):
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_STEP_MISSING_CAVEAT")

    # 6. Digest check
    recorded = step_dict.get("package_execution_step_digest", "")
    recomputed = hash_waveguide_package_assembly_execution_step(step_dict)
    if recorded != recomputed or not recorded:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_STEP_DIGEST_MISMATCH")

    if is_valid:
        reasons.append("PACKAGE_EXECUTION_STEP_DIGEST_VALID")
    else:
        reasons.append("PACKAGE_EXECUTION_STEP_INVALID")

    return is_valid, sorted(list(set(reasons)))


def build_waveguide_package_assembly_execution_plan(
    preflight_report_path_or_dict: Any,
    readiness_report_path_or_dict: Any = None
) -> WaveguidePackageAssemblyExecutionPlan:
    """
    Builds the top-level execution plan.
    """
    preflight_dict = _load_dict(preflight_report_path_or_dict)
    
    # Locate readiness report
    readiness_dict = None
    if readiness_report_path_or_dict is not None:
        readiness_dict = _load_dict(readiness_report_path_or_dict)
    else:
        default_readiness_path = os.path.join(REPO_ROOT, "docs", "SOL_WAVEGUIDE_FINAL_PACKAGE_READINESS_AUDIT_REPORT.json")
        if os.path.exists(default_readiness_path):
            readiness_dict = _load_dict(default_readiness_path)

    caveat = "Validation is shadow/sandbox software validation, not quantum hardware validation."

    if not preflight_dict or not readiness_dict:
        return WaveguidePackageAssemblyExecutionPlan(
            package_assembly_execution_plan_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-EXECUTION-PLAN",
            package_assembly_execution_plan_version=1,
            package_assembly_execution_plan_status="package_execution_plan_invalid",
            source_preflight_authorization_report_digest="",
            source_authorization_envelope_digest="",
            source_final_package_readiness_report_digest="",
            source_distribution_package_manifest_digest="",
            source_dry_run_audit_report_digest="",
            source_package_assembly_plan_digest="",
            source_artifact_catalog_digest="",
            execution_steps=[],
            planned_execution_steps=[],
            blocked_execution_steps=[],
            warning_execution_steps=[],
            invalid_execution_steps=[],
            planned_execution_step_count=0,
            blocked_execution_step_count=0,
            warning_execution_step_count=0,
            invalid_execution_step_count=0,
            total_authorized_file_count=0,
            rc1_authorized_file_count=0,
            rc2_authorized_file_count=0,
            shared_authorized_file_count=0,
            planned_input_reference_count=0,
            planned_output_reference_count=0,
            target_package_sections=[],
            execution_step_types_indexed=[],
            execution_step_phases_indexed=[],
            package_roles_indexed=[],
            artifact_types_indexed=[],
            rc_scopes_indexed=[],
            source_reference_digests=[],
            source_reference_paths=[],
            target_package_paths=[],
            planned_output_references=[],
            execution_guard_matrix=[],
            execution_input_reference_index={},
            execution_output_reference_index={},
            noop_sandbox_boundary={},
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
            reason_codes=["PACKAGE_EXECUTION_SOURCE_PREFLIGHT_INVALID", "PACKAGE_EXECUTION_PLAN_INVALID"],
            software_validation_caveat=caveat
        )

    # Validate preflight report
    is_preflight_ok, preflight_reasons = validate_waveguide_package_preflight_authorization_audit_report(preflight_dict)
    preflight_status = preflight_dict.get("preflight_authorization_report_status", "")
    
    plan_status = "package_execution_plan_ready"
    reasons = ["PACKAGE_EXECUTION_PLAN_CANONICAL"]
    
    if not is_preflight_ok or preflight_status != "package_preflight_authorization_verified":
        plan_status = "package_execution_plan_invalid"
        reasons.append("PACKAGE_EXECUTION_SOURCE_PREFLIGHT_INVALID")
    else:
        reasons.append("PACKAGE_EXECUTION_SOURCE_PREFLIGHT_VERIFIED")

    # Extract digests
    pf_digest = preflight_dict.get("preflight_authorization_report_digest", "")
    env_digest = preflight_dict.get("source_authorization_envelope_digest", "")
    fr_digest = preflight_dict.get("source_final_package_readiness_report_digest", "")
    dm_digest = preflight_dict.get("source_distribution_package_manifest_digest", "")
    dr_digest = preflight_dict.get("source_dry_run_audit_report_digest", "")
    ap_digest = preflight_dict.get("source_package_assembly_plan_digest", "")
    ac_digest = preflight_dict.get("source_artifact_catalog_digest", "")

    total_files = preflight_dict.get("total_authorized_file_count", 0)
    rc1_files = preflight_dict.get("rc1_authorized_file_count", 0)
    rc2_files = preflight_dict.get("rc2_authorized_file_count", 0)
    shared_files = preflight_dict.get("shared_authorized_file_count", 0)

    # Generate steps from readiness cases
    steps = []
    cases = readiness_dict.get("audited_cases", [])
    
    # Sort cases deterministically
    sorted_cases = sorted(cases, key=lambda x: (x.get("target_package_path", ""), x.get("source_artifact_path", "")))

    # Step 0: Verify Preflight Authorization
    step_0 = build_waveguide_package_assembly_execution_step(
        step_id="SOL-WAVEGUIDE-EXECUTION-STEP-000",
        index=0,
        name="Verify Preflight Authorization",
        stype="verify_preflight_authorization",
        phase="preflight",
        source_digest=pf_digest,
        source_path="docs/SOL_WAVEGUIDE_PACKAGE_PREFLIGHT_AUTHORIZATION_AUDIT_REPORT.json",
        input_kind="preflight_report",
        output_ref="",
        output_kind="none",
        section="",
        tpath="",
        adigest="",
        atype="preflight_report",
        role="audit_verification_proof",
        scope="Shared",
        preflight_report_digest=pf_digest
    )
    steps.append(step_0)

    # File steps (1 to 28)
    for idx, case in enumerate(sorted_cases, start=1):
        step_id = f"SOL-WAVEGUIDE-EXECUTION-STEP-{idx:03d}"
        s_path = case.get("source_artifact_path", "")
        t_path = case.get("target_package_path", "")
        s_digest = case.get("source_artifact_digest", "")
        a_type = case.get("source_artifact_type", "")
        role = case.get("source_package_role", "")
        scope = case.get("candidate_level", "Shared")
        section = case.get("target_package_section", "")

        step = build_waveguide_package_assembly_execution_step(
            step_id=step_id,
            index=idx,
            name=f"Plan metadata for {s_path} -> {t_path}",
            stype="prepare_metadata_instruction",
            phase="instruction_planning",
            source_digest=s_digest,
            source_path=s_path,
            input_kind="source_artifact",
            output_ref=t_path,
            output_kind="target_artifact",
            section=section,
            tpath=t_path,
            adigest=s_digest,
            atype=a_type,
            role=role,
            scope=scope,
            preflight_report_digest=pf_digest
        )
        steps.append(step)

    # Step 29: Prepare No-Op Boundary
    step_29 = build_waveguide_package_assembly_execution_step(
        step_id="SOL-WAVEGUIDE-EXECUTION-STEP-029",
        index=29,
        name="Prepare No-Op Boundary",
        stype="prepare_noop_boundary",
        phase="safety_boundary",
        source_digest="",
        source_path="",
        input_kind="none",
        output_ref="",
        output_kind="none",
        section="",
        tpath="",
        adigest="",
        atype="",
        role="",
        scope="Shared",
        preflight_report_digest=pf_digest
    )
    steps.append(step_29)

    # Step 30: Finalize Execution Blueprint
    step_30 = build_waveguide_package_assembly_execution_step(
        step_id="SOL-WAVEGUIDE-EXECUTION-STEP-030",
        index=30,
        name="Finalize Execution Blueprint",
        stype="finalize_execution_blueprint",
        phase="finalization",
        source_digest="",
        source_path="",
        input_kind="none",
        output_ref="",
        output_kind="none",
        section="",
        tpath="",
        adigest="",
        atype="",
        role="",
        scope="Shared",
        preflight_report_digest=pf_digest
    )
    steps.append(step_30)

    # Collect indexes
    target_package_sections = sorted(list(set(s.target_package_section for s in steps if s.target_package_section)))
    execution_step_types_indexed = sorted(list(set(s.step_type for s in steps)))
    execution_step_phases_indexed = sorted(list(set(s.step_phase for s in steps)))
    package_roles_indexed = sorted(list(set(s.package_role for s in steps if s.package_role)))
    artifact_types_indexed = sorted(list(set(s.artifact_type for s in steps if s.artifact_type)))
    rc_scopes_indexed = sorted(list(set(s.rc_scope for s in steps if s.rc_scope)))
    source_reference_digests = sorted(list(set(s.source_reference_digest for s in steps if s.source_reference_digest)))
    source_reference_paths = sorted(list(set(s.source_reference_path for s in steps if s.source_reference_path)))
    target_package_paths = sorted(list(set(s.target_package_path for s in steps if s.target_package_path)))
    planned_output_references = sorted(list(set(s.planned_output_reference for s in steps if s.planned_output_reference)))

    execution_guard_matrix = sorted([
        "source_preflight_authorization_report_digest_matches",
        "source_authorization_envelope_digest_matches",
        "source_final_package_readiness_report_digest_matches",
        "source_distribution_package_manifest_digest_matches",
        "source_dry_run_audit_report_digest_matches",
        "source_package_assembly_plan_digest_matches",
        "source_artifact_catalog_digest_matches",
        "metadata_only_boundary_acknowledged",
        "no_archive_creation_in_this_plan",
        "no_file_copy_in_this_plan",
        "no_directory_creation_in_this_plan",
        "no_upload_in_this_plan",
        "no_deployment_in_this_plan",
        "no_signing_in_this_plan",
        "no_external_publication_in_this_plan",
        "no_production_mutation_in_this_plan",
        "future_runner_requires_separate_execution_authorization"
    ])

    execution_input_reference_index = {}
    execution_output_reference_index = {}
    for s in steps:
        if s.step_type == "prepare_metadata_instruction":
            if s.source_reference_path:
                execution_input_reference_index[s.source_reference_path] = s.source_reference_digest
            if s.target_package_path:
                execution_output_reference_index[s.target_package_path] = s.artifact_digest

    noop_sandbox_boundary = {
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
        "rollback_reason": "no_physical_execution_performed",
        "rollback_scope": "metadata_only",
        "rollback_operations": []
    }

    blocked_operation_attempt_counts = {
        "archive_creation": 0, "file_copy": 0, "directory_creation": 0,
        "upload": 0, "deployment": 0, "external_signing": 0,
        "external_publication": 0, "production_mutation": 0
    }

    planned_steps_ids = [s.package_execution_step_id for s in steps]

    plan = WaveguidePackageAssemblyExecutionPlan(
        package_assembly_execution_plan_id="SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-EXECUTION-PLAN",
        package_assembly_execution_plan_version=1,
        package_assembly_execution_plan_status=plan_status,
        source_preflight_authorization_report_digest=pf_digest,
        source_authorization_envelope_digest=env_digest,
        source_final_package_readiness_report_digest=fr_digest,
        source_distribution_package_manifest_digest=dm_digest,
        source_dry_run_audit_report_digest=dr_digest,
        source_package_assembly_plan_digest=ap_digest,
        source_artifact_catalog_digest=ac_digest,
        execution_steps=steps,
        planned_execution_steps=planned_steps_ids,
        blocked_execution_steps=[],
        warning_execution_steps=[],
        invalid_execution_steps=[],
        planned_execution_step_count=len(steps),
        blocked_execution_step_count=0,
        warning_execution_step_count=0,
        invalid_execution_step_count=0,
        total_authorized_file_count=total_files,
        rc1_authorized_file_count=rc1_files,
        rc2_authorized_file_count=rc2_files,
        shared_authorized_file_count=shared_files,
        planned_input_reference_count=len(execution_input_reference_index),
        planned_output_reference_count=len(execution_output_reference_index),
        target_package_sections=target_package_sections,
        execution_step_types_indexed=execution_step_types_indexed,
        execution_step_phases_indexed=execution_step_phases_indexed,
        package_roles_indexed=package_roles_indexed,
        artifact_types_indexed=artifact_types_indexed,
        rc_scopes_indexed=rc_scopes_indexed,
        source_reference_digests=source_reference_digests,
        source_reference_paths=source_reference_paths,
        target_package_paths=target_package_paths,
        planned_output_references=planned_output_references,
        execution_guard_matrix=execution_guard_matrix,
        execution_input_reference_index=execution_input_reference_index,
        execution_output_reference_index=execution_output_reference_index,
        noop_sandbox_boundary=noop_sandbox_boundary,
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
    plan.package_assembly_execution_plan_digest = hash_waveguide_package_assembly_execution_plan(plan)
    return plan


def validate_waveguide_package_assembly_execution_plan(plan: Any) -> Tuple[bool, List[str]]:
    """
    Independently validates the top-level execution plan.
    """
    plan_dict = _load_dict(plan)
    if not plan_dict:
        return False, ["PACKAGE_EXECUTION_PLAN_INVALID"]

    reasons = []
    is_valid = True

    # 1. Basic properties
    if plan_dict.get("package_assembly_execution_plan_id") != "SOL-WAVEGUIDE-PACKAGE-ASSEMBLY-EXECUTION-PLAN":
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_PLAN_INVALID_ID")

    status = plan_dict.get("package_assembly_execution_plan_status", "")
    if status not in ["package_execution_plan_ready", "package_execution_plan_blocked", "package_execution_plan_warning", "package_execution_plan_invalid"]:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_PLAN_UNRECOGNIZED_STATUS")

    # 2. Check steps validation
    steps = plan_dict.get("execution_steps", [])
    if not steps:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_PLAN_MISSING_STEPS")
    else:
        for idx, s in enumerate(steps):
            s_ok, s_reasons = validate_waveguide_package_assembly_execution_step(s)
            if not s_ok:
                is_valid = False
                reasons.extend(s_reasons)

    # 3. Check counts
    total_files = plan_dict.get("total_authorized_file_count", 0)
    if total_files <= 0:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_PLAN_INVALID_FILE_COUNT")

    # 4. Check no mutation check flags
    mutations = [
        "physical_execution_performed", "archive_creation_performed", "file_copy_performed",
        "directory_creation_performed", "upload_performed", "deployment_performed",
        "signing_performed", "external_publication_performed", "production_mutation_performed"
    ]
    for m in mutations:
        if plan_dict.get(m) is not False:
            is_valid = False
            reasons.append(f"PACKAGE_EXECUTION_PLAN_MUTATION_PERFORMED_{m.upper()}")

    # 5. Check blocked counts are all zero
    counts = plan_dict.get("blocked_operation_attempt_counts", {})
    expected_ops = [
        "archive_creation", "file_copy", "directory_creation",
        "upload", "deployment", "external_signing",
        "external_publication", "production_mutation"
    ]
    for op in expected_ops:
        if counts.get(op, -1) != 0:
            is_valid = False
            reasons.append("PACKAGE_EXECUTION_PLAN_NONZERO_BLOCKED_OPERATION")

    # 6. Check digest
    recorded = plan_dict.get("package_assembly_execution_plan_digest", "")
    recomputed = hash_waveguide_package_assembly_execution_plan(plan_dict)
    if recorded != recomputed or not recorded:
        is_valid = False
        reasons.append("PACKAGE_EXECUTION_PLAN_DIGEST_MISMATCH")

    # Final decision
    if is_valid and status == "package_execution_plan_ready":
        reasons.append("PACKAGE_EXECUTION_PLAN_READY")
    else:
        reasons.append("PACKAGE_EXECUTION_PLAN_INVALID")

    return is_valid, sorted(list(set(reasons)))


def summarize_waveguide_package_assembly_execution_plan(plan: Any) -> str:
    """
    Returns a brief deterministic summary of the execution plan.
    """
    plan_dict = _load_dict(plan)
    if not plan_dict:
        return "Invalid Package Assembly Execution Plan"

    status = plan_dict.get("package_assembly_execution_plan_status", "unknown")
    steps = plan_dict.get("execution_steps", [])
    total_files = plan_dict.get("total_authorized_file_count", 0)
    digest = plan_dict.get("package_assembly_execution_plan_digest", "")

    return (
        f"SOL Waveguide Package Assembly Execution Plan Summary:\n"
        f"  Plan Status: {status}\n"
        f"  Execution Plan Digest: {digest}\n"
        f"  Total Planned Steps: {len(steps)}\n"
        f"  Total Authorized Files: {total_files}\n"
        f"  Physical Execution Performed: {plan_dict.get('physical_execution_performed')}\n"
        f"  No-Op Sandbox Boundary: {plan_dict.get('noop_sandbox_boundary') is not None}\n"
    )


def export_waveguide_package_assembly_execution_plan(plan: Any, filepath: str) -> None:
    """
    Serializes and exports the execution plan to JSON.
    """
    plan_dict = _load_dict(plan)
    if not plan_dict:
        raise ValueError("Cannot export invalid plan data")

    full_path = os.path.join(REPO_ROOT, normalize_to_repo_path(filepath))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(plan_dict, f, indent=4, sort_keys=True)


def compare_waveguide_package_assembly_execution_plans(left: Any, right: Any) -> Dict[str, Any]:
    """
    Compares two execution plans and highlights differences.
    """
    l_dict = _load_dict(left) or {}
    r_dict = _load_dict(right) or {}

    diffs = {}
    for key in sorted(list(set(list(l_dict.keys()) + list(r_dict.keys())))):
        if key == "execution_steps":
            # Compare step lengths or details
            l_steps = l_dict.get(key, [])
            r_steps = r_dict.get(key, [])
            if len(l_steps) != len(r_steps):
                diffs[key] = (f"len={len(l_steps)}", f"len={len(r_steps)}")
            continue
        l_val = l_dict.get(key)
        r_val = r_dict.get(key)
        if l_val != r_val:
            diffs[key] = (l_val, r_val)
    return diffs


def index_waveguide_execution_steps_by_type(steps: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes execution steps by step_type.
    """
    idx = {}
    for s in steps:
        s_dict = _load_dict(s)
        if s_dict:
            stype = s_dict.get("step_type", "unknown")
            idx.setdefault(stype, []).append(s_dict)
    return idx


def index_waveguide_execution_steps_by_status(steps: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes execution steps by step_status.
    """
    idx = {}
    for s in steps:
        s_dict = _load_dict(s)
        if s_dict:
            status = s_dict.get("step_status", "unknown")
            idx.setdefault(status, []).append(s_dict)
    return idx


def index_waveguide_execution_steps_by_phase(steps: List[Any]) -> Dict[str, List[Any]]:
    """
    Indexes execution steps by step_phase.
    """
    idx = {}
    for s in steps:
        s_dict = _load_dict(s)
        if s_dict:
            phase = s_dict.get("step_phase", "unknown")
            idx.setdefault(phase, []).append(s_dict)
    return idx
