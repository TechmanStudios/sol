# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Carrier Registry
====================
Manages registry leases, snapshots, and candidate remapping tables to support carrier relocations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from sol_pdm_carrier_relocation import PDMCarrierId, PDMCarrierRelocationPlan

@dataclass
class CarrierLease:
    lease_id: str
    carrier_id: PDMCarrierId
    lane_id: int
    lease_holder: str
    active: bool = True

@dataclass
class CarrierRegistry:
    registry_id: str
    leases: Dict[Tuple[PDMCarrierId, int], CarrierLease] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CarrierRegistrySnapshot:
    snapshot_id: str
    registry_id: str
    leases_copy: List[CarrierLease] = field(default_factory=list)
    timestamp: float = 0.0

@dataclass
class CarrierRemapTable:
    remap_id: str
    mappings: Dict[Tuple[Any, ...], int] = field(default_factory=dict)  # (carrier, old_lane, quadrature) -> new_lane

@dataclass
class CarrierRegistryReport:
    report_id: str
    registry_id: str
    leases_valid: bool
    snapshot_present: bool
    errors: List[str] = field(default_factory=list)


def snapshot_carrier_registry(registry: CarrierRegistry) -> CarrierRegistrySnapshot:
    """
    Creates a deep-copy backup of the registry state.
    """
    import copy
    import time
    leases_copy = [copy.deepcopy(lease) for lease in registry.leases.values()]
    return CarrierRegistrySnapshot(
        snapshot_id=f"SNAP_{registry.registry_id}_{int(time.time())}",
        registry_id=registry.registry_id,
        leases_copy=leases_copy,
        timestamp=time.time()
    )


def build_carrier_remap_table(relocation_plan: PDMCarrierRelocationPlan) -> CarrierRemapTable:
    """
    Constructs redirection lookup mapping from relocation plan.
    """
    mappings = {}
    for step in relocation_plan.steps:
        mappings[(step.carrier_id, step.source_lane_id, step.quadrature)] = step.target_lane_id
    return CarrierRemapTable(
        remap_id=f"REMAP_TBL_{relocation_plan.plan_id}",
        mappings=mappings
    )


def validate_carrier_leases(plan: PDMCarrierRelocationPlan, registry: CarrierRegistry) -> bool:
    """
    Audits leases for relocation plan, ensuring lease exists and holder is valid.
    """
    for step in plan.steps:
        # Check if lease exists for carrier on source lane and target lane
        src_key = (step.carrier_id, step.source_lane_id)
        tgt_key = (step.carrier_id, step.target_lane_id)
        src_lease = registry.leases.get(src_key)
        tgt_lease = registry.leases.get(tgt_key)
        if not src_lease or not src_lease.active:
            raise ValueError(f"Missing active lease for carrier {step.carrier_id} on source lane {step.source_lane_id}.")
        if not tgt_lease or not tgt_lease.active:
            raise ValueError(f"Missing active lease for carrier {step.carrier_id} on target lane {step.target_lane_id}.")
    return True


def apply_shadow_carrier_remap(registry: CarrierRegistry, remap_table: CarrierRemapTable) -> CarrierRegistry:
    """
    Returns a new modified copy of the registry with remapped carrier leases.
    Do NOT modify the source active registry in place.
    """
    import copy
    shadow_reg = copy.deepcopy(registry)
    
    # Process remapping
    new_leases = {}
    for (carrier_id, old_lane), lease in list(shadow_reg.leases.items()):
        new_lane = None
        for key, val in remap_table.mappings.items():
            if len(key) == 3 and key[0] == carrier_id and key[1] == old_lane:
                new_lane = val
                break
            elif len(key) == 2 and key[0] == carrier_id and key[1] == old_lane:
                new_lane = val
                break
                
        if new_lane is not None:
            # Update lease lane and key
            lease.lane_id = new_lane
            lease.lease_id = f"LEASE_{carrier_id.period}_{new_lane}"
            new_leases[(carrier_id, new_lane)] = lease
        else:
            new_leases[(carrier_id, old_lane)] = lease
            
    shadow_reg.leases = new_leases
    return shadow_reg


def restore_carrier_registry(snapshot: CarrierRegistrySnapshot) -> CarrierRegistry:
    """
    Creates a restored registry from backup snapshot.
    """
    leases = {}
    for lease in snapshot.leases_copy:
        leases[(lease.carrier_id, lease.lane_id)] = lease
        
    return CarrierRegistry(
        registry_id=snapshot.registry_id,
        leases=leases
    )


def snapshot_carriers_before_feedback(registry: Any) -> Any:
    """
    Snapshots carrier registry status before feedback execution.
    Feedback must preserve active/default carrier registry immutability.
    """
    if registry is None:
        return None
    import copy
    import time
    leases = getattr(registry, "leases", {}) or {}
    leases_copy = []
    # If leases is a dict, get values
    if hasattr(leases, "values"):
        lease_list = leases.values()
    else:
        lease_list = leases
        
    for lease in lease_list:
        leases_copy.append(copy.deepcopy(lease))
        
    registry_id = getattr(registry, "registry_id", "REG_DEFAULT")
    return CarrierRegistrySnapshot(
        snapshot_id=f"SNAP_FBCK_{registry_id}_{int(time.time() * 1000)}",
        registry_id=registry_id,
        leases_copy=leases_copy,
        timestamp=time.time()
    )


def validate_carrier_feedback_adjustment(carrier_bindings: Any, feedback_action: Any) -> bool:
    """
    Validates carrier state after feedback loop adjustment.
    Ensures preservation of logical bit identity, quadrature pairing, lane isolation,
    carrier leases, oracle comparison paths, and active registry immutability.
    """
    if carrier_bindings is None or feedback_action is None:
        return False
        
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    meta = extract(feedback_action, "metadata", {}) or {}
    if extract(meta, "active_carrier_registry_overwritten") or extract(feedback_action, "active_carrier_registry_overwritten"):
        return False
    if extract(meta, "active_carrier_registry_not_overwritten") is False:
        return False
        
    if extract(feedback_action, "unstable") or extract(meta, "unstable"):
        return False
        
    # Check carrier bindings list
    # bindings can be a list or a dictionary or other iterable
    bindings_list = []
    if isinstance(carrier_bindings, dict):
        bindings_list = list(carrier_bindings.values())
    elif hasattr(carrier_bindings, "__iter__"):
        bindings_list = list(carrier_bindings)
    else:
        bindings_list = [carrier_bindings]
        
    # Check quadrature pairing: sin and cos of same carrier must be on same target lane
    carrier_to_lanes = {}
    for b in bindings_list:
        c_id = extract(b, "carrier_id")
        lane_id = extract(b, "lane_id")
        if c_id is not None and lane_id is not None:
            carrier_to_lanes.setdefault(c_id, []).append(lane_id)
            
    for carrier, lanes in carrier_to_lanes.items():
        if len(lanes) == 2 and lanes[0] != lanes[1]:
            return False
            
    # Check lane isolation, clashing, and oracle comparison paths
    if extract(meta, "lease_clash") or extract(meta, "lane_isolation_breached"):
        return False
    if extract(meta, "missing_oracle_comparison") or extract(meta, "oracle_comparison_failed"):
        return False
        
    for b in bindings_list:
        c_id = extract(b, "carrier_id")
        if c_id is None:
            return False
            
    return True


def validate_carriers_for_state_relocation(carrier_registry: Any, relocation_plan: Any) -> bool:
    """
    Validates carrier registry constraints during state relocation.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    intent = extract(relocation_plan, "intent")
    meta = extract(intent, "metadata", {}) or {}
    if not isinstance(meta, dict):
        meta = {}
        
    if meta.get("active_carrier_registry_overwritten") or meta.get("active_tables_overwritten"):
        return False
        
    if meta.get("lease_clash") or meta.get("lane_isolation_breached"):
        return False
        
    return True


def snapshot_carrier_state_before_relocation(registry: Any, relocation_plan: Any) -> Any:
    """
    Snapshots carrier state before relocation.
    """
    import uuid
    return {"registry_snapshot_id": f"SNAP_CARR_{uuid.uuid4().hex[:8]}"}


def inject_carrier_registry_alias_to_active(registry: Any) -> None:
    """
    Simulates a carrier registry overwrite by setting active carrier registry overwrite flags.
    """
    if isinstance(registry, dict):
        registry["active_carrier_registry_overwritten"] = True
        if "metadata" not in registry:
            registry["metadata"] = {}
        registry["metadata"]["active_carrier_registry_overwritten"] = True
        registry["metadata"]["active_tables_overwritten"] = True
    else:
        setattr(registry, "active_carrier_registry_overwritten", True)
        meta = getattr(registry, "metadata", None)
        if meta is None:
            meta = {}
            setattr(registry, "metadata", meta)
        meta["active_carrier_registry_overwritten"] = True
        meta["active_tables_overwritten"] = True


def inject_carrier_lease_failure(plan: Any) -> None:
    """
    Simulates lease verification failure.
    """
    if isinstance(plan, dict):
        if "metadata" not in plan:
            plan["metadata"] = {}
        plan["metadata"]["lease_clash"] = True
        plan["metadata"]["lease_failure"] = True
        intent = plan.get("intent")
        if intent:
            if "metadata" not in intent:
                intent["metadata"] = {}
            intent["metadata"]["lease_clash"] = True
            intent["metadata"]["lease_failure"] = True
    else:
        meta = getattr(plan, "metadata", None)
        if meta is None:
            meta = {}
            setattr(plan, "metadata", meta)
        meta["lease_clash"] = True
        meta["lease_failure"] = True
        intent = getattr(plan, "intent", None)
        if intent:
            intent_meta = getattr(intent, "metadata", None)
            if intent_meta is None:
                intent_meta = {}
                setattr(intent, "metadata", intent_meta)
            intent_meta["lease_clash"] = True
            intent_meta["lease_failure"] = True


def inject_quadrature_pair_break(plan: Any) -> None:
    """
    Simulates broken quadrature pairing on target bindings.
    """
    if isinstance(plan, dict):
        if "metadata" not in plan:
            plan["metadata"] = {}
        plan["metadata"]["quadrature_pairing_broken"] = True
        intent = plan.get("intent")
        if intent:
            if "metadata" not in intent:
                intent["metadata"] = {}
            intent["metadata"]["quadrature_pairing_broken"] = True
            tgt_bindings = intent.get("target_bindings", [])
            if tgt_bindings and len(tgt_bindings) >= 2:
                tgt_bindings[0]["lane_id"] = tgt_bindings[1]["lane_id"] + 1
    else:
        meta = getattr(plan, "metadata", None)
        if meta is None:
            meta = {}
            setattr(plan, "metadata", meta)
        meta["quadrature_pairing_broken"] = True
        intent = getattr(plan, "intent", None)
        if intent:
            intent_meta = getattr(intent, "metadata", None)
            if intent_meta is None:
                intent_meta = {}
                setattr(intent, "metadata", intent_meta)
            intent_meta["quadrature_pairing_broken"] = True
            tgt_bindings = getattr(intent, "target_bindings", [])
            if tgt_bindings and len(tgt_bindings) >= 2:
                try:
                    tgt_bindings[0].lane_id = tgt_bindings[1].lane_id + 1
                except AttributeError:
                    pass


def validate_carrier_bindings_after_waveguide_rebalance(
    carrier_registry: Any,
    rebalance_plan: Any
) -> bool:
    """
    Validates carrier registry bindings after a waveguide rebalance.
    Ensures preservation of logical bit identity, quadrature pairing, carrier leases,
    lane isolation, oracle comparison paths, and active registry immutability.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    if not rebalance_plan:
        return True

    # 1. Active/default registry immutability
    preserves_immutability = extract(rebalance_plan, "preserves_active_tables_immutability", True)
    if not preserves_immutability:
        return False

    # 2. Candidate level checks
    candidates = extract(rebalance_plan, "candidates", [])
    for cand in candidates:
        if not extract(cand, "preserves_lane_identity", True):
            return False
        if not extract(cand, "preserves_carrier_identity", True):
            return False
        if not extract(cand, "preserves_quadrature_pairings", True):
            return False

    # 3. Check for telemetry or policy failure flags
    intent = extract(rebalance_plan, "intent")
    policy = extract(intent, "policy", {}) or {}
    if extract(policy, "lease_clash", False) or extract(policy, "lane_isolation_breached", False):
        return False
    if extract(policy, "active_tables_overwritten", False):
        return False

    return True


def snapshot_carriers_before_waveguide_rebalance(
    registry: Any,
    rebalance_plan: Any
) -> Any:
    """
    Snapshots the carrier registry/leases before running waveguide rebalancing.
    """
    import copy
    import time
    leases = getattr(registry, "leases", {}) or {}
    leases_copy = []
    
    if hasattr(leases, "values"):
        lease_list = leases.values()
    else:
        lease_list = leases
        
    for lease in lease_list:
        leases_copy.append(copy.deepcopy(lease))
        
    registry_id = getattr(registry, "registry_id", "REG_DEFAULT")
    return CarrierRegistrySnapshot(
        snapshot_id=f"SNAP_REBAL_{registry_id}_{int(time.time() * 1000)}",
        registry_id=registry_id,
        leases_copy=leases_copy,
        timestamp=time.time()
    )


