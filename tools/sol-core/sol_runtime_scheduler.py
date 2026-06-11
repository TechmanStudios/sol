# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Runtime Scheduler
=====================
Schedules and runs level-up jobs in shadow mode. Automatically blocks infinite loops
and halts execution if any critical gate check fails.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class RuntimeSchedulePolicy:
    max_loops: int = 5
    halt_on_failed_gate: bool = True
    disable_auto_promotion: bool = True

@dataclass
class ScheduledLevelUpJob:
    job_id: str
    sequence: Dict[str, Any]
    policy: RuntimeSchedulePolicy
    status: str = "pending"  # pending, running, completed, held, failed
    created_at: float = field(default_factory=time.time)
    execution_attempts: int = 0
    failure_reason: Optional[str] = None

@dataclass
class RuntimeScheduleDecision:
    decision_id: str
    action: str  # execute, hold, halt
    reason: str

@dataclass
class RuntimeScheduleReport:
    report_id: str
    job_id: str
    status: str
    executed_steps: int
    halted: bool
    errors: List[str] = field(default_factory=list)


def schedule_levelup_job(sequence: Dict[str, Any], policy: RuntimeSchedulePolicy) -> ScheduledLevelUpJob:
    """
    Schedules a level-up sequence for future execution.
    """
    import uuid
    job_id = f"JOB_{uuid.uuid4().hex[:8]}"
    return ScheduledLevelUpJob(
        job_id=job_id,
        sequence=sequence,
        policy=policy
    )


def validate_scheduled_job(job: ScheduledLevelUpJob) -> bool:
    """
    Validates job configuration and ensures no automatic promotion parameters are enabled.
    """
    if not job.sequence:
        raise ValueError("Job contains no sequence definition.")
    if job.policy.max_loops <= 0 or job.policy.max_loops > 100:
        raise ValueError("Invalid max_loops bounds configured in schedule policy.")
    if not job.policy.disable_auto_promotion:
        raise ValueError("Schedule policy configuration violation: automatic level promotion is prohibited.")
    return True


def execute_due_shadow_jobs(jobs: List[ScheduledLevelUpJob], runtime: Any) -> List[RuntimeScheduleReport]:
    """
    Executes due scheduled jobs strictly in shadow mode. Halts immediately on any gate failure or cycle.
    """
    reports = []
    
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    for job in jobs:
        validate_scheduled_job(job)
        
        if job.status in ["completed", "failed", "held"]:
            continue
            
        job.status = "running"
        job.execution_attempts += 1
        
        # Check loops limit to avoid infinite cycles
        if job.execution_attempts > job.policy.max_loops:
            job.status = "failed"
            job.failure_reason = "Infinite execution loop limit exceeded."
            reports.append(RuntimeScheduleReport(
                report_id=f"SCH_RPT_{job.job_id}",
                job_id=job.job_id,
                status="failed",
                executed_steps=0,
                halted=True,
                errors=[job.failure_reason]
            ))
            continue
            
        errors = []
        halted = False
        executed = 0
        
        # Check runtime state
        if extract(runtime, "mode") == "hold" or extract(runtime, "mode") == "quarantine":
            job.status = "held"
            job.failure_reason = f"Runtime state is in mode: {extract(runtime, 'mode')}"
            reports.append(RuntimeScheduleReport(
                report_id=f"SCH_RPT_{job.job_id}",
                job_id=job.job_id,
                status="held",
                executed_steps=0,
                halted=True,
                errors=[job.failure_reason]
            ))
            continue
            
        # Run shadow level up
        from sol_levelup_sequence import execute_shadow_levelup_sequence
        try:
            trace = execute_shadow_levelup_sequence(job.sequence, runtime)
            if trace.outcome != "success":
                halted = True
                errors.append(f"Sequence step execution trace failed with outcome: {trace.outcome}")
            else:
                executed = len(trace.executed_steps)
        except Exception as e:
            halted = True
            errors.append(f"Execution failed due to exception: {str(e)}")
            
        if halted and job.policy.halt_on_failed_gate:
            job.status = "held"
            job.failure_reason = "; ".join(errors)
        elif halted:
            job.status = "failed"
            job.failure_reason = "; ".join(errors)
        else:
            job.status = "completed"
            
        reports.append(RuntimeScheduleReport(
            report_id=f"SCH_RPT_{job.job_id}",
            job_id=job.job_id,
            status=job.status,
            executed_steps=executed,
            halted=halted,
            errors=errors
        ))
        
    return reports


def hold_scheduled_job(job: ScheduledLevelUpJob, reason: str) -> None:
    """
    Places a scheduled job on hold.
    """
    job.status = "held"
    job.failure_reason = reason
