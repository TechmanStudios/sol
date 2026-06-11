# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Level-Up Sequence
=====================
Models, schedules, and executes multi-level level-up sequences, ensuring dependency correctness
and court/ranger validation gating.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class LevelUpSequenceId:
    sequence_id: str
    created_at: float = field(default_factory=time.time)

@dataclass
class LevelUpStep:
    step_id: str
    level: int
    name: str
    required_docket_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LevelUpDependency:
    dependent_level: int
    prerequisite_level: int

@dataclass
class LevelUpSchedule:
    schedule_id: str
    steps: List[LevelUpStep]
    scheduled_at: float = field(default_factory=time.time)

@dataclass
class LevelUpExecutionTrace:
    trace_id: str
    sequence_id: str
    executed_steps: List[LevelUpStep] = field(default_factory=list)
    failed_steps: List[LevelUpStep] = field(default_factory=list)
    runtime_mode: str = "shadow"
    outcome: str = "success"  # success, hold, rollback, quarantine
    logs: List[str] = field(default_factory=list)

@dataclass
class LevelUpSequenceReport:
    report_id: str
    sequence_id: str
    trace: LevelUpExecutionTrace
    success: bool
    errors: List[str] = field(default_factory=list)


def build_levelup_sequence(levels: List[LevelUpStep], dependencies: List[LevelUpDependency]) -> Dict[str, Any]:
    """
    Builds a level-up sequence structure.
    """
    import uuid
    seq_id = f"SEQ_{uuid.uuid4().hex[:8]}"
    return {
        "sequence_id": seq_id,
        "steps": levels,
        "dependencies": dependencies
    }


def validate_levelup_sequence(sequence: Dict[str, Any]) -> bool:
    """
    Validates sequence steps and dependency structures.
    """
    if not sequence.get("sequence_id"):
        raise ValueError("Sequence is missing sequence_id.")
    if not sequence.get("steps"):
        raise ValueError("Sequence contains no level-up steps.")
    
    # Check for duplicate steps
    levels = [step.level for step in sequence["steps"]]
    if len(levels) != len(set(levels)):
        raise ValueError("Duplicate levels are not allowed in the same sequence.")
        
    # Check if dependencies reference valid levels
    all_levels = set(levels)
    for dep in sequence.get("dependencies", []):
        if dep.dependent_level not in all_levels or dep.prerequisite_level not in all_levels:
            raise ValueError(f"Dependency reference {dep.prerequisite_level} -> {dep.dependent_level} contains unregistered levels.")
            
    # Perform topological sort to detect cycle
    topological_sort_levelup_steps(sequence)
    return True


def topological_sort_levelup_steps(sequence: Dict[str, Any]) -> List[LevelUpStep]:
    """
    Sorts steps topologically based on prerequisite dependencies. Raises ValueError if cycles are present.
    """
    steps = sequence["steps"]
    dependencies = sequence.get("dependencies", [])
    
    # Build adjacency list
    adj = {step.level: [] for step in steps}
    in_degree = {step.level: 0 for step in steps}
    level_to_step = {step.level: step for step in steps}
    
    for dep in dependencies:
        adj[dep.prerequisite_level].append(dep.dependent_level)
        in_degree[dep.dependent_level] += 1
        
    # Kahn's algorithm
    queue = [lvl for lvl, deg in in_degree.items() if deg == 0]
    sorted_levels = []
    
    while queue:
        # Sort queue to ensure deterministic ordering (e.g. lower level first)
        queue.sort()
        curr = queue.pop(0)
        sorted_levels.append(curr)
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                
    if len(sorted_levels) != len(steps):
        raise ValueError("Dependency cycle detected in level-up sequence.")
        
    return [level_to_step[lvl] for lvl in sorted_levels]


def execute_shadow_levelup_sequence(sequence: Dict[str, Any], runtime: Any) -> LevelUpExecutionTrace:
    """
    Simulates execution of a topologically sorted level-up sequence.
    """
    validate_levelup_sequence(sequence)
    sorted_steps = topological_sort_levelup_steps(sequence)
    
    import uuid
    trace = LevelUpExecutionTrace(
        trace_id=f"TR_{uuid.uuid4().hex[:8]}",
        sequence_id=sequence["sequence_id"],
        runtime_mode=getattr(runtime, "mode", "shadow")
    )
    
    trace.logs.append(f"Starting level-up sequence trace {trace.trace_id} in mode {trace.runtime_mode}")
    
    outcome = "success"
    
    for step in sorted_steps:
        # Gating checks simulation
        if getattr(runtime, "mode", "shadow") == "quarantine":
            outcome = "quarantine"
            trace.failed_steps.append(step)
            trace.logs.append(f"Quarantine condition active: blocking step Level {step.level}")
            break
            
        if getattr(runtime, "mode", "shadow") == "hold":
            outcome = "hold"
            trace.failed_steps.append(step)
            trace.logs.append(f"Hold condition active: halting sequence at Level {step.level}")
            break

        # Simulate execution
        trace.executed_steps.append(step)
        trace.logs.append(f"Successfully simulated Level {step.level} step: {step.name}")
        
    trace.outcome = outcome
    return trace


def summarize_levelup_sequence(trace: LevelUpExecutionTrace) -> LevelUpSequenceReport:
    """
    Summarizes sequence execution trace outcome.
    """
    import uuid
    success = trace.outcome == "success"
    errors = []
    if not success:
        errors.append(f"Level-up sequence failed due to state outcome: {trace.outcome}")
        
    return LevelUpSequenceReport(
        report_id=f"SEQ_RPT_{uuid.uuid4().hex[:8]}",
        sequence_id=trace.sequence_id,
        trace=trace,
        success=success,
        errors=errors
    )
