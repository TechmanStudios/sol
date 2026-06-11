# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Sovereign Runtime
=====================
Defines the sovereign runtime environment capable of scheduling, executing, and observing
level-up sequences in shadow or sandbox mode. Production execution is rejected.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class SovereignRuntimeId:
    runtime_id: str
    created_at: float = field(default_factory=time.time)

@dataclass
class SovereignRuntimePolicy:
    allowed_modes: List[str] = field(default_factory=lambda: ["shadow", "sandbox"])
    required_invariants: List[str] = field(default_factory=list)
    max_steps_per_sequence: int = 100
    allow_production_execution: bool = False

@dataclass
class SovereignRuntimeState:
    runtime_id: SovereignRuntimeId
    policy: SovereignRuntimePolicy
    mode: str = "shadow"  # shadow, sandbox, hold, quarantine
    active_level: int = 35
    executed_commands: List[Any] = field(default_factory=list)
    events: List[Any] = field(default_factory=list)
    quarantine_flags: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SovereignRuntimeCommand:
    command_id: str
    target_level: int
    operation: str  # e.g., "levelup_step", "validate_gates"
    payload: Dict[str, Any] = field(default_factory=dict)
    mode: str = "shadow"

@dataclass
class SovereignRuntimeEvent:
    event_id: str
    runtime_id: str
    timestamp: float
    event_type: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SovereignRuntimeResult:
    success: bool
    final_level: int
    executed_steps: int
    errors: List[str] = field(default_factory=list)
    quarantined: bool = False

@dataclass
class SovereignRuntimeReport:
    report_id: str
    runtime_id: str
    policy: SovereignRuntimePolicy
    state: SovereignRuntimeState
    result: SovereignRuntimeResult
    passed_gates: bool = True


def build_sovereign_runtime(policy: SovereignRuntimePolicy) -> SovereignRuntimeState:
    """
    Builds a new sovereign runtime instance.
    """
    if policy.allow_production_execution:
        raise ValueError("Cannot build runtime: production execution is strictly prohibited.")
    
    import uuid
    r_id = SovereignRuntimeId(runtime_id=f"RUN_{uuid.uuid4().hex[:8]}")
    return SovereignRuntimeState(
        runtime_id=r_id,
        policy=policy,
        mode="shadow"
    )


def validate_sovereign_runtime(runtime: SovereignRuntimeState) -> bool:
    """
    Validates runtime policy and active state constraints.
    """
    if runtime.policy.allow_production_execution:
        raise ValueError("Runtime configuration violation: production execution is prohibited.")
    if runtime.mode not in ["shadow", "sandbox", "hold", "quarantine"]:
        raise ValueError(f"Runtime is in invalid mode: {runtime.mode}")
    return True


def submit_runtime_command(runtime: SovereignRuntimeState, command: SovereignRuntimeCommand) -> SovereignRuntimeEvent:
    """
    Submits a command to the runtime ledger and processes mode transitions.
    """
    validate_sovereign_runtime(runtime)
    
    if command.mode == "production" or runtime.mode == "production":
        runtime.mode = "hold"
        raise ValueError("Production mode execution is blocked by sovereign control rules.")

    import uuid
    event = SovereignRuntimeEvent(
        event_id=f"EV_{uuid.uuid4().hex[:8]}",
        runtime_id=runtime.runtime_id.runtime_id,
        timestamp=time.time(),
        event_type="command_submitted",
        details={
            "command_id": command.command_id,
            "target_level": command.target_level,
            "operation": command.operation,
            "mode": command.mode
        }
    )
    runtime.events.append(event)
    runtime.executed_commands.append(command)
    return event


def execute_shadow_runtime_command(runtime: SovereignRuntimeState, command: SovereignRuntimeCommand) -> SovereignRuntimeResult:
    """
    Executes a runtime command strictly in shadow mode (read-only/dry-run).
    """
    submit_runtime_command(runtime, command)
    
    # In shadow mode, we simulate and verify the execution without mutating state
    errors = []
    success = True
    
    if command.target_level > runtime.active_level + 1:
        errors.append(f"Target level {command.target_level} exceeds incremental stepping constraint.")
        success = False
        
    final_level = command.target_level if success else runtime.active_level
    
    return SovereignRuntimeResult(
        success=success,
        final_level=final_level,
        executed_steps=1 if success else 0,
        errors=errors,
        quarantined=(runtime.mode == "quarantine")
    )


def summarize_sovereign_runtime(runtime: SovereignRuntimeState) -> SovereignRuntimeReport:
    """
    Summarizes execution telemetry and gates check status.
    """
    import uuid
    passed = runtime.mode in ["shadow", "sandbox"] and not runtime.policy.allow_production_execution
    result = SovereignRuntimeResult(
        success=passed,
        final_level=runtime.active_level,
        executed_steps=len(runtime.executed_commands),
        errors=[] if passed else ["Runtime is in a non-executable hold or quarantine state."],
        quarantined=(runtime.mode == "quarantine")
    )
    
    return SovereignRuntimeReport(
        report_id=f"RPT_{uuid.uuid4().hex[:8]}",
        runtime_id=runtime.runtime_id.runtime_id,
        policy=runtime.policy,
        state=runtime,
        result=result,
        passed_gates=passed
    )


def submit_topology_relocation_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeEvent:
    """
    Submits a topology relocation command to the sovereign runtime.
    Runtime must enforce allowed modes, court tokens, and rollback references.
    """
    if command.mode == "production" or runtime.mode == "production":
        runtime.mode = "hold"
        raise ValueError("Production mode execution is blocked by sovereign control rules.")
    
    # Enforce allowed mode
    if command.mode not in runtime.policy.allowed_modes:
        raise ValueError(f"Command mode {command.mode} is not allowed by runtime policy.")

    # Enforce court token if sandbox
    if command.mode == "sandbox":
        token = command.payload.get("court_token")
        if not token or token == "INVALID_TOKEN":
            raise ValueError("Court token is required for sandbox execution.")

    # Enforce rollback snapshot reference
    rollback_snapshot = command.payload.get("rollback_snapshot")
    if not rollback_snapshot:
        raise ValueError("Rollback references are required for topology relocation command execution.")

    # Check for no production/default topology mutation
    if command.payload.get("mutate_production_topology"):
        raise ValueError("Production topology mutation is strictly prohibited.")

    return submit_runtime_command(runtime, command)


def execute_shadow_topology_relocation_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeResult:
    """
    Executes a shadow topology relocation command.
    """
    submit_topology_relocation_command(runtime, command)
    errors = []
    
    if command.payload.get("should_fail"):
        errors.append("Simulated shadow relocation command execution failure.")
        
    success = len(errors) == 0
    final_level = command.target_level if success else runtime.active_level
    
    return SovereignRuntimeResult(
        success=success,
        final_level=final_level,
        executed_steps=1 if success else 0,
        errors=errors,
        quarantined=(runtime.mode == "quarantine")
    )


def submit_autonomous_cadence_sync_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeEvent:
    """
    Submits an autonomous cadence sync command to the sovereign runtime.
    Runtime must enforce allowed modes, court tokens, and rollback references.
    """
    if command.mode == "production" or runtime.mode == "production":
        runtime.mode = "hold"
        raise ValueError("Production mode execution is blocked by sovereign control rules.")
    
    # Enforce allowed mode
    if command.mode not in runtime.policy.allowed_modes:
        raise ValueError(f"Command mode {command.mode} is not allowed by runtime policy.")

    # Enforce court token if sandbox
    if command.mode == "sandbox":
        token = command.payload.get("court_token")
        if not token or token == "INVALID_TOKEN":
            raise ValueError("Court token is required for sandbox execution.")

    # Enforce rollback snapshot reference
    rollback_snapshot = command.payload.get("rollback_snapshot")
    if not rollback_snapshot:
        raise ValueError("Rollback references are required for autonomous cadence command execution.")

    # Check for no production/default cadence mutation
    if command.payload.get("mutate_production_cadence"):
        raise ValueError("Production cadence mutation is strictly prohibited.")

    # Ensure no automatic promotion
    if command.payload.get("automatic_promotion"):
        raise ValueError("Automatic promotion is prohibited under sovereign timing rules.")

    return submit_runtime_command(runtime, command)


def execute_shadow_autonomous_cadence_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeResult:
    """
    Executes a shadow autonomous cadence sync command.
    """
    submit_autonomous_cadence_sync_command(runtime, command)
    errors = []
    
    if command.payload.get("should_fail"):
        errors.append("Simulated shadow autonomous cadence command execution failure.")
        
    success = len(errors) == 0
    final_level = command.target_level if success else runtime.active_level
    
    return SovereignRuntimeResult(
        success=success,
        final_level=final_level,
        executed_steps=1 if success else 0,
        errors=errors,
        quarantined=(runtime.mode == "quarantine")
    )


def submit_multicore_assembly_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeEvent:
    """
    Submits a multi-core assembly command. Enforces shadow/sandbox mode,
    court token for sandbox, ranger observer, rollback references, no production
    execution, and no automatic promotion.
    """
    if command.mode == "production" or runtime.mode == "production" or command.payload.get("production_execution"):
        runtime.mode = "hold"
        raise ValueError("Production mode execution is blocked by sovereign control rules.")

    if command.mode not in runtime.policy.allowed_modes:
        raise ValueError(f"Command mode {command.mode} is not allowed by runtime policy.")

    if command.mode == "sandbox":
        token = command.payload.get("court_token")
        if not token or token == "INVALID_TOKEN":
            raise ValueError("Court token is required for sandbox execution.")

    # Enforce ranger observer
    ranger = command.payload.get("ranger_observer") or command.payload.get("ranger_evidence")
    if not ranger:
        raise ValueError("Ranger observer reference is required for multi-core assembly command execution.")

    # Enforce rollback snapshot reference
    rollback_snapshot = command.payload.get("rollback_snapshot")
    if not rollback_snapshot:
        raise ValueError("Rollback references are required for multi-core assembly command execution.")

    # Check for no automatic promotion
    if command.payload.get("automatic_promotion"):
        raise ValueError("Automatic promotion is prohibited under sovereign multi-core assembly rules.")

    # Check for active profiles or tables mutation attempts
    if command.payload.get("mutate_active_profiles") or command.payload.get("overwrite_active_cadence") or command.payload.get("overwrite_active_phase_table") or command.payload.get("overwrite_active_carrier"):
        raise ValueError("Active profile/table overwrite is prohibited.")

    return submit_runtime_command(runtime, command)


def execute_shadow_multicore_assembly_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeResult:
    """
    Executes a shadow multi-core assembly command.
    """
    submit_multicore_assembly_command(runtime, command)
    errors = []
    
    if command.payload.get("should_fail"):
        errors.append("Simulated shadow multi-core assembly command execution failure.")
        
    success = len(errors) == 0
    final_level = command.target_level if success else runtime.active_level
    
    return SovereignRuntimeResult(
        success=success,
        final_level=final_level,
        executed_steps=1 if success else 0,
        errors=errors,
        quarantined=(runtime.mode == "quarantine")
    )


def submit_pipeline_balance_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeEvent:
    """
    Submits a pipeline balance command. Enforces shadow/sandbox mode,
    court token if sandbox, ranger observer, rollback references, no production
    execution, and no automatic promotion.
    """
    if command.mode == "production" or runtime.mode == "production" or command.payload.get("production_execution"):
        runtime.mode = "hold"
        raise ValueError("Production mode execution is blocked by sovereign control rules.")

    if command.mode not in runtime.policy.allowed_modes:
        raise ValueError(f"Command mode {command.mode} is not allowed by runtime policy.")

    if command.mode == "sandbox":
        token = command.payload.get("court_token")
        if not token or token == "INVALID_TOKEN":
            raise ValueError("Court token is required for sandbox execution.")

    # Enforce ranger observer
    ranger = command.payload.get("ranger_observer") or command.payload.get("ranger_evidence")
    if not ranger:
        raise ValueError("Ranger observer reference is required for pipeline balance command execution.")

    # Enforce rollback snapshot reference
    rollback_snapshot = command.payload.get("rollback_snapshot")
    if not rollback_snapshot:
        raise ValueError("Rollback references are required for pipeline balance command execution.")

    # Check for no automatic promotion
    if command.payload.get("automatic_promotion"):
        raise ValueError("Automatic promotion is prohibited under sovereign pipeline balance rules.")

    # Check for active profiles or tables mutation attempts
    if command.payload.get("mutate_active_profiles") or command.payload.get("overwrite_active_cadence") or command.payload.get("overwrite_active_phase_table") or command.payload.get("overwrite_active_carrier"):
        raise ValueError("Active profile/table overwrite is prohibited.")

    return submit_runtime_command(runtime, command)


def execute_shadow_pipeline_balance_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeResult:
    """
    Executes a shadow pipeline balance command.
    """
    submit_pipeline_balance_command(runtime, command)
    errors = []
    
    if command.payload.get("should_fail"):
        errors.append("Simulated shadow pipeline balance command execution failure.")
        
    success = len(errors) == 0
    final_level = command.target_level if success else runtime.active_level
    
    return SovereignRuntimeResult(
        success=success,
        final_level=final_level,
        executed_steps=1 if success else 0,
        errors=errors,
        quarantined=(runtime.mode == "quarantine")
    )


def submit_quantum_wavefront_calibration_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeEvent:
    """
    Submits a quantum wavefront calibration command. Enforces shadow/sandbox mode,
    court token if sandbox, ranger observer, rollback references, no production
    execution, and no automatic promotion.
    """
    if command.mode == "production" or runtime.mode == "production" or command.payload.get("production_execution"):
        runtime.mode = "hold"
        raise ValueError("Production mode execution is blocked by sovereign control rules.")

    if command.mode not in runtime.policy.allowed_modes:
        raise ValueError(f"Command mode {command.mode} is not allowed by runtime policy.")

    if command.mode == "sandbox":
        token = command.payload.get("court_token")
        if not token or token == "INVALID_TOKEN":
            raise ValueError("Court token is required for sandbox execution.")

    # Enforce ranger observer
    ranger = command.payload.get("ranger_observer") or command.payload.get("ranger_evidence")
    if not ranger:
        raise ValueError("Ranger observer reference is required for quantum wavefront calibration command execution.")

    # Enforce rollback snapshot reference
    rollback_snapshot = command.payload.get("rollback_snapshot")
    if not rollback_snapshot:
        raise ValueError("Rollback references are required for quantum wavefront calibration command execution.")

    # Check for no automatic promotion
    if command.payload.get("automatic_promotion"):
        raise ValueError("Automatic promotion is prohibited under sovereign quantum wavefront calibration rules.")

    # Check for active profiles or tables mutation attempts
    if command.payload.get("mutate_active_profiles") or command.payload.get("overwrite_active_cadence") or command.payload.get("overwrite_active_phase_table") or command.payload.get("overwrite_active_carrier"):
        raise ValueError("Active profile/table overwrite is prohibited.")

    return submit_runtime_command(runtime, command)


def execute_shadow_quantum_wavefront_calibration_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeResult:
    """
    Executes a shadow quantum wavefront calibration command.
    """
    submit_quantum_wavefront_calibration_command(runtime, command)
    errors = []
    
    if command.payload.get("should_fail"):
        errors.append("Simulated shadow quantum wavefront calibration command execution failure.")
        
    success = len(errors) == 0
    final_level = command.target_level if success else runtime.active_level
    
    return SovereignRuntimeResult(
        success=success,
        final_level=final_level,
        executed_steps=1 if success else 0,
        errors=errors,
        quarantined=(runtime.mode == "quarantine")
    )


def submit_burnin_runtime_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeEvent:
    """
    Submits a burn-in runtime command. Enforces shadow/sandbox mode,
    court token if sandbox, ranger observer, rollback references, no production
    execution, and no automatic promotion.
    """
    if command.mode == "production" or runtime.mode == "production" or command.payload.get("production_execution"):
        runtime.mode = "hold"
        raise ValueError("Production mode execution is blocked by sovereign control rules.")

    if command.mode not in runtime.policy.allowed_modes:
        raise ValueError(f"Command mode {command.mode} is not allowed by runtime policy.")

    if command.mode == "sandbox":
        token = command.payload.get("court_token")
        if not token or token == "INVALID_TOKEN":
            raise ValueError("Court token is required for sandbox execution.")

    # Enforce ranger observer
    ranger = command.payload.get("ranger_observer") or command.payload.get("ranger_evidence")
    if not ranger:
        raise ValueError("Ranger observer reference is required for burn-in runtime command execution.")

    # Enforce rollback snapshot reference
    rollback_snapshot = command.payload.get("rollback_snapshot")
    if not rollback_snapshot:
        raise ValueError("Rollback references are required for burn-in runtime command execution.")

    # Check for no automatic promotion
    if command.payload.get("automatic_promotion"):
        raise ValueError("Automatic promotion is prohibited under sovereign burn-in rules.")

    # Bounded cycle count
    max_cycles = command.payload.get("max_cycles", 10)
    if max_cycles <= 0 or max_cycles > 1000:
        raise ValueError("Unbounded cycle count is prohibited.")

    # Check for active profiles or tables mutation attempts
    if command.payload.get("mutate_active_profiles") or command.payload.get("overwrite_active_cadence") or command.payload.get("overwrite_active_phase_table") or command.payload.get("overwrite_active_carrier"):
        raise ValueError("Active profile/table overwrite is prohibited.")

    return submit_runtime_command(runtime, command)



def execute_shadow_burnin_runtime_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeResult:
    """
    Executes a shadow burn-in runtime command.
    """
    submit_burnin_runtime_command(runtime, command)
    errors = []
    
    if command.payload.get("should_fail"):
        errors.append("Simulated shadow burn-in command execution failure.")
        
    success = len(errors) == 0
    final_level = command.target_level if success else runtime.active_level
    
    return SovereignRuntimeResult(
        success=success,
        final_level=final_level,
        executed_steps=1 if success else 0,
        errors=errors,
        quarantined=(runtime.mode == "quarantine")
    )


def submit_release_candidate_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeEvent:
    """
    Submits a release candidate command. Enforces shadow/sandbox mode,
    court token if sandbox, ranger observer, no production execution,
    and no automatic promotion.
    """
    if command.mode == "production" or runtime.mode == "production" or command.payload.get("production_execution"):
        runtime.mode = "hold"
        raise ValueError("Production mode execution is blocked by sovereign control rules.")

    if command.mode not in runtime.policy.allowed_modes:
        raise ValueError(f"Command mode {command.mode} is not allowed by runtime policy.")

    if command.mode == "sandbox":
        token = command.payload.get("court_token")
        if not token or token == "INVALID_TOKEN":
            raise ValueError("Court token is required for sandbox execution.")

    # Enforce ranger observer
    ranger = command.payload.get("ranger_observer") or command.payload.get("ranger_evidence")
    if not ranger:
        raise ValueError("Ranger observer reference is required for release candidate command execution.")

    # Check for no automatic promotion
    if command.payload.get("automatic_promotion"):
        raise ValueError("Automatic promotion is prohibited under sovereign release candidate rules.")

    # Check for active profiles or tables mutation attempts
    if command.payload.get("mutate_active_profiles") or command.payload.get("overwrite_active_cadence") or command.payload.get("overwrite_active_phase_table") or command.payload.get("overwrite_active_carrier"):
        raise ValueError("Active profile/table overwrite is prohibited.")

    return submit_runtime_command(runtime, command)


def execute_shadow_release_candidate_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeResult:
    """
    Executes a shadow release candidate command.
    """
    submit_release_candidate_command(runtime, command)
    errors = []
    
    if command.payload.get("should_fail"):
        errors.append("Simulated shadow release candidate command execution failure.")
        
    success = len(errors) == 0
    final_level = command.target_level if success else runtime.active_level
    
    return SovereignRuntimeResult(
        success=success,
        final_level=final_level,
        executed_steps=1 if success else 0,
        errors=errors,
        quarantined=(runtime.mode == "quarantine")
    )


def submit_system_finalization_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeEvent:
    """
    Submits a system finalization command. Enforces shadow/sandbox mode,
    court review, ranger observer, ledger entry, and no automatic promotion.
    """
    if command.mode == "production" or runtime.mode == "production" or command.payload.get("production_execution"):
        runtime.mode = "hold"
        raise ValueError("Production mode execution is blocked by sovereign control rules.")

    if command.mode not in runtime.policy.allowed_modes:
        raise ValueError(f"Command mode {command.mode} is not allowed by runtime policy.")

    if command.mode == "sandbox":
        token = command.payload.get("court_token")
        if not token or token == "INVALID_TOKEN":
            raise ValueError("Court token is required for sandbox execution.")

    # Enforce ranger observer
    ranger = command.payload.get("ranger_observer") or command.payload.get("ranger_evidence")
    if not ranger:
        raise ValueError("Ranger observer reference is required for system finalization command execution.")

    # Check for no automatic promotion
    if command.payload.get("automatic_promotion"):
        raise ValueError("Automatic promotion is prohibited under sovereign finalization rules.")

    # Check for active profiles or tables mutation attempts
    if command.payload.get("mutate_active_profiles") or command.payload.get("overwrite_active_cadence") or command.payload.get("overwrite_active_phase_table") or command.payload.get("overwrite_active_carrier"):
        raise ValueError("Active profile/table overwrite is prohibited.")

    return submit_runtime_command(runtime, command)


def execute_shadow_system_finalization_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeResult:
    """
    Executes shadow system finalization command.
    """
    submit_system_finalization_command(runtime, command)
    errors = []
    
    if command.payload.get("should_fail"):
        errors.append("Simulated shadow system finalization failure.")
        
    success = len(errors) == 0
    final_level = command.target_level if success else runtime.active_level
    
    return SovereignRuntimeResult(
        success=success,
        final_level=final_level,
        executed_steps=1 if success else 0,
        errors=errors,
        quarantined=(runtime.mode == "quarantine")
    )


def submit_production_gateway_check_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeEvent:
    """
    Submits a production gateway check command.
    """
    # Enforces default-deny and rejects production mode
    if command.mode == "production" or runtime.mode == "production" or command.payload.get("production_execution"):
        runtime.mode = "hold"
        raise ValueError("Production mode execution is blocked by sovereign control rules.")

    return submit_runtime_command(runtime, command)


def execute_shadow_production_gateway_check_command(
    runtime: SovereignRuntimeState,
    command: SovereignRuntimeCommand
) -> SovereignRuntimeResult:
    """
    Executes shadow production gateway check.
    """
    submit_production_gateway_check_command(runtime, command)
    errors = []
    
    if command.payload.get("should_fail"):
        errors.append("Simulated gateway check failure.")
        
    success = len(errors) == 0
    final_level = command.target_level if success else runtime.active_level
    
    return SovereignRuntimeResult(
        success=success,
        final_level=final_level,
        executed_steps=1 if success else 0,
        errors=errors,
        quarantined=(runtime.mode == "quarantine")
    )






