# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Sovereign Multi-Core Assembly
=================================
Manages assembly of multi-core execution clusters in shadow/sandbox mode.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import uuid

@dataclass
class SovereignCoreAssemblyId:
    assembly_id: str
    epoch_id: str

@dataclass
class SovereignCoreAssemblyPolicy:
    allow_sandbox: bool = True
    court_token_required: bool = True
    rollback_required: bool = True

@dataclass
class SovereignCoreUnit:
    core_id: str
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SovereignCoreCluster:
    cluster_id: str
    cores: List[SovereignCoreUnit]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SovereignCoreAssemblyPlan:
    plan_id: str
    policy: SovereignCoreAssemblyPolicy
    core_group: Any
    fabric_map: Any
    clusters: List[SovereignCoreCluster]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SovereignCoreAssemblyResult:
    success: bool
    errors: List[str] = field(default_factory=list)
    assembled_cores: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SovereignCoreAssemblyReport:
    report_id: str
    plan: SovereignCoreAssemblyPlan
    result: SovereignCoreAssemblyResult
    timestamp: float = field(default_factory=time.time)


def build_sovereign_core_assembly(
    core_group: Any,
    fabric_map: Any,
    policy: SovereignCoreAssemblyPolicy
) -> SovereignCoreAssemblyPlan:
    """
    Constructs a multi-core assembly plan. Core group count must be 2, 4, or 8.
    """
    if not core_group:
        raise ValueError("Invalid core group: core group is empty.")

    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    cores = extract(core_group, "cores", {})
    # Core group might be a list or dictionary
    if isinstance(cores, dict):
        core_ids = list(cores.keys())
    elif isinstance(cores, list):
        core_ids = cores
    else:
        # Check if core_group has core_count attribute
        count = extract(core_group, "core_count", 0)
        core_ids = [f"core_{i}" for i in range(count)] if count else []

    core_count = len(core_ids)
    if core_count not in (2, 4, 8):
        raise ValueError(f"Invalid core group: assembly count must be 2, 4, or 8. Found: {core_count}")

    # Build sovereign core units
    units = [SovereignCoreUnit(core_id=cid) for cid in core_ids]
    
    # Create clusters
    clusters = []
    # partition into clusters of 2 cores
    for idx in range(0, core_count, 2):
        clusters.append(SovereignCoreCluster(
            cluster_id=f"CLUSTER_{idx // 2}",
            cores=units[idx:idx+2]
        ))

    import uuid
    plan_id = f"ASSEMBLY_PLAN_{uuid.uuid4().hex[:8]}"
    
    # Extract metadata to check for references
    metadata = {}
    if isinstance(core_group, dict):
        metadata.update(core_group.get("metadata", {}))
    else:
        metadata.update(getattr(core_group, "metadata", {}) or {})

    # Reference rollback and cadence
    metadata["rollback_snapshot"] = extract(core_group, "rollback_snapshot") or metadata.get("rollback_snapshot")
    metadata["cadence_profile"] = extract(core_group, "cadence_profile") or metadata.get("cadence_profile")
    metadata["simd_bindings"] = extract(core_group, "simd_bindings") or metadata.get("simd_bindings")
    metadata["tensor_shards"] = extract(core_group, "tensor_shards") or metadata.get("tensor_shards")
    metadata["waveguide_lanes"] = extract(core_group, "waveguide_lanes") or metadata.get("waveguide_lanes")
    metadata["prefix_carry_bridge"] = extract(core_group, "prefix_carry_bridge") or metadata.get("prefix_carry_bridge")

    return SovereignCoreAssemblyPlan(
        plan_id=plan_id,
        policy=policy,
        core_group=core_group,
        fabric_map=fabric_map,
        clusters=clusters,
        metadata=metadata
    )


def validate_sovereign_core_assembly(plan: SovereignCoreAssemblyPlan) -> bool:
    """
    Validates assembly plan constraints, references, and mappings.
    """
    # Enforce rollback snapshot reference presence
    if not plan.metadata.get("rollback_snapshot"):
        raise ValueError("Missing rollback snapshot reference in assembly plan.")
        
    # Enforce cadence profile reference presence
    if not plan.metadata.get("cadence_profile"):
        raise ValueError("Missing cadence profile reference in assembly plan.")

    # Core count check
    cores_count = sum(len(c.cores) for c in plan.clusters)
    if cores_count not in (2, 4, 8):
        raise ValueError("Core group validation failed: assembly must be 2, 4, or 8 cores.")

    return True


def execute_shadow_core_assembly(
    plan: SovereignCoreAssemblyPlan
) -> SovereignCoreAssemblyReport:
    """
    Simulates assembling core clusters in shadow mode.
    """
    errors = []
    
    # Run validation
    try:
        validate_sovereign_core_assembly(plan)
    except ValueError as e:
        errors.append(str(e))
        
    # Check for simulate failure or unstable cadence
    if plan.metadata.get("unstable_cadence") or plan.metadata.get("cadence_instability"):
        errors.append("Core assembly blocked: unstable autonomous cadence.")
        
    success = len(errors) == 0
    assembled_cores = []
    if success:
        for c in plan.clusters:
            for u in c.cores:
                assembled_cores.append(u.core_id)
                
    result = SovereignCoreAssemblyResult(
        success=success,
        errors=errors,
        assembled_cores=assembled_cores,
        metadata={"timestamp": time.time()}
    )
    
    import uuid
    return SovereignCoreAssemblyReport(
        report_id=f"ASSEMBLY_REP_{uuid.uuid4().hex[:8]}",
        plan=plan,
        result=result
    )


def summarize_sovereign_core_assembly(result: SovereignCoreAssemblyResult) -> Dict[str, Any]:
    """
    Summarizes assembly result outcomes.
    """
    return {
        "success": result.success,
        "errors": list(result.errors),
        "assembled_core_count": len(result.assembled_cores)
    }
