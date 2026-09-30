# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL System Lockdown
===================
Captures and enforces lockdown snapshots of all registries and parameter stores.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class SystemLockdownPolicy:
    lock_all_registries: bool = True

@dataclass
class SystemLockdownSnapshot:
    snapshot_id: str
    settings: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class SystemLockdownViolation:
    invariant_name: str
    expected: Any
    actual: Any
    description: str

@dataclass
class SystemLockdownReport:
    report_id: str
    snapshot: SystemLockdownSnapshot
    violations: List[SystemLockdownViolation] = field(default_factory=list)
    locked: bool = True
    timestamp: float = field(default_factory=time.time)


def capture_system_lockdown_snapshot(runtime: Any, registries: Any) -> SystemLockdownSnapshot:
    """
    Captures configuration parameters from runtime and registries.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    snapshot_id = f"LCK_SNP_{uuid.uuid4().hex[:8]}"
    
    settings = {
        "auto_promote_enabled": extract(runtime, "allow_automatic_promotion", False),
        "production_execution_enabled": extract(runtime, "allow_production_execution", False),
        "default_mutation_enabled": extract(runtime, "allow_default_mutation", False) or extract(runtime, "production_execution_attempted", False),
        "live_mutation_gateway_enabled": extract(runtime, "live_gateway_enabled", False),
        
        "active_phase_tables_protected": not extract(registries, "active_phase_tables_overwritten", False),
        "active_cadence_profiles_protected": not extract(registries, "active_cadence_profiles_overwritten", False),
        "active_carrier_registry_protected": not extract(registries, "active_carrier_registry_overwritten", False),
        
        "ranger_registry_intact": not extract(registries, "ranger_registry_corrupted", False),
        "court_registry_intact": not extract(registries, "court_registry_corrupted", False),
        "rollback_registry_intact": not extract(registries, "rollback_registry_corrupted", False),
        "ledger_registry_intact": not extract(registries, "ledger_registry_corrupted", False),
        "quarantine_flags_intact": not extract(runtime, "quarantine_corrupted", False)
    }
    
    return SystemLockdownSnapshot(snapshot_id=snapshot_id, settings=settings)


def validate_system_lockdown(
    snapshot: SystemLockdownSnapshot,
    policy: SystemLockdownPolicy
) -> SystemLockdownReport:
    """
    Validates snapshot settings against expected lockdown defaults.
    """
    violations = []
    
    expected_settings = {
        "auto_promote_enabled": False,
        "production_execution_enabled": False,
        "default_mutation_enabled": False,
        "live_mutation_gateway_enabled": False,
        "active_phase_tables_protected": True,
        "active_cadence_profiles_protected": True,
        "active_carrier_registry_protected": True,
        "ranger_registry_intact": True,
        "court_registry_intact": True,
        "rollback_registry_intact": True,
        "ledger_registry_intact": True,
        "quarantine_flags_intact": True
    }
    
    for k, expected_val in expected_settings.items():
        actual_val = snapshot.settings.get(k)
        if actual_val != expected_val:
            violations.append(SystemLockdownViolation(
                invariant_name=k,
                expected=expected_val,
                actual=actual_val,
                description=f"System lockdown invariant {k} violated: expected {expected_val}, actual {actual_val}."
            ))
            
    locked = len(violations) == 0
    return SystemLockdownReport(
        report_id=f"LCK_RPT_{uuid.uuid4().hex[:8]}",
        snapshot=snapshot,
        violations=violations,
        locked=locked
    )


def detect_system_lockdown_violation(
    before: SystemLockdownSnapshot,
    after: SystemLockdownSnapshot
) -> List[SystemLockdownViolation]:
    """
    Detects any settings drift between two snapshots.
    """
    violations = []
    for k, expected_val in before.settings.items():
        actual_val = after.settings.get(k)
        if actual_val != expected_val:
            violations.append(SystemLockdownViolation(
                invariant_name=k,
                expected=expected_val,
                actual=actual_val,
                description=f"Drift detected in locked parameter {k}: changed from {expected_val} to {actual_val}."
            ))
    return violations


def summarize_system_lockdown(report: SystemLockdownReport) -> Dict[str, Any]:
    """
    Summarizes the lockdown report.
    """
    return {
        "report_id": report.report_id,
        "locked": report.locked,
        "violations_count": len(report.violations),
        "violations": [v.invariant_name for v in report.violations]
    }
