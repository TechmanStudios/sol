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
