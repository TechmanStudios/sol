# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Cross-Manifold Geodesic Routing
===================================
Scaffolds geodesic routing paths and shadow transfer execution between multiple
separated manifold domains.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib
import json

from sol_shard_topology import ShardId, ShardTopology, assign_manifold_to_shard

@dataclass
class ManifoldDomain:
    manifold_id: str
    domain_name: str
    lanes: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GeodesicRouteHop:
    hop_index: int
    source_node_id: str
    target_node_id: str
    delay_ms: float = 0.05
    attenuation: float = 0.01

@dataclass
class CrossManifoldRoute:
    route_id: str
    source_manifold_id: str
    target_manifold_id: str
    hops: List[GeodesicRouteHop] = field(default_factory=list)
    route_depth: int = 0
    participating_lanes: List[int] = field(default_factory=list)
    boundary_crossings: List[str] = field(default_factory=list)
    expected_output_width: int = 64
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GeodesicRoutePlan:
    source_domain: ManifoldDomain
    target_domain: ManifoldDomain
    route: CrossManifoldRoute
    value_width: int
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrossManifoldTransferRequest:
    request_id: str
    source_domain_id: str
    target_domain_id: str
    value: int
    value_width: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrossManifoldTransferResult:
    request: CrossManifoldTransferRequest
    transferred_value: int
    passed_gates: bool
    evidence: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrossManifoldRoutingReport:
    report_id: str
    request_id: str
    source_manifold_id: str
    target_manifold_id: str
    route_depth: int
    boundary_crossings: List[str]
    value_width: int
    passed_gates: bool
    oracle_match: bool
    gate_report: Any  # InstructionGateReport
    transfer_result: CrossManifoldTransferResult
    reproducibility_hash: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


def build_geodesic_route(
    source_domain: ManifoldDomain,
    target_domain: ManifoldDomain,
    value_width: int
) -> CrossManifoldRoute:
    """
    Constructs a geodesic route between two manifold domains.
    """
    route_id = f"ROUTE_{source_domain.manifold_id}_TO_{target_domain.manifold_id}"
    
    # Mocking hops for deterministic scaffold execution
    hops = [
        GeodesicRouteHop(
            hop_index=0,
            source_node_id=f"{source_domain.manifold_id}_egress",
            target_node_id="Geodesic_Gateway_Alpha"
        ),
        GeodesicRouteHop(
            hop_index=1,
            source_node_id="Geodesic_Gateway_Alpha",
            target_node_id="Geodesic_Gateway_Beta"
        ),
        GeodesicRouteHop(
            hop_index=2,
            source_node_id="Geodesic_Gateway_Beta",
            target_node_id=f"{target_domain.manifold_id}_ingress"
        )
    ]
    
    # Boundary crossings include the gateway crossings
    boundary_crossings = ["EgressGate", "CoreGatewayAlpha", "CoreGatewayBeta", "IngressGate"]
    
    # Participating lanes default to all lanes in the source domain
    participating_lanes = list(source_domain.lanes)
    
    return CrossManifoldRoute(
        route_id=route_id,
        source_manifold_id=source_domain.manifold_id,
        target_manifold_id=target_domain.manifold_id,
        hops=hops,
        route_depth=len(hops),
        participating_lanes=participating_lanes,
        boundary_crossings=boundary_crossings,
        expected_output_width=value_width,
        metadata={"routing_algorithm": "hierarchical_shortest_path"}
    )


def validate_geodesic_route(route: CrossManifoldRoute) -> bool:
    """
    Validates the geodesic route against safety and correctness rules.
    """
    # 1. Reject missing source or target domains
    if not route.source_manifold_id or not route.target_manifold_id:
        return False
        
    # 2. Reject route with no hops
    if not route.hops:
        return False
        
    # 3. Reject unbounded route depth (depth must be <= 4)
    if route.route_depth > 4 or len(route.hops) > 4:
        return False
        
    return True


def plan_cross_manifold_transfer(
    request: CrossManifoldTransferRequest
) -> GeodesicRoutePlan:
    """
    Creates a geodesic route plan from a transfer request.
    """
    # Mock domains based on the request IDs
    source_domain = ManifoldDomain(
        manifold_id=request.source_domain_id,
        domain_name=f"Domain_{request.source_domain_id}",
        lanes=list(range(request.value_width // 8))
    )
    target_domain = ManifoldDomain(
        manifold_id=request.target_domain_id,
        domain_name=f"Domain_{request.target_domain_id}",
        lanes=list(range(request.value_width // 8))
    )
    
    route = build_geodesic_route(source_domain, target_domain, request.value_width)
    
    evidence = {
        "planned_at": time.time(),
        "total_hops": len(route.hops),
        "requested_width": request.value_width,
        "request": request
    }
    
    return GeodesicRoutePlan(
        source_domain=source_domain,
        target_domain=target_domain,
        route=route,
        value_width=request.value_width,
        evidence=evidence
    )


def execute_shadow_transfer(
    plan: GeodesicRoutePlan
) -> CrossManifoldTransferResult:
    """
    Simulates a shadow transfer of the request value along the planned route.
    """
    # Simply preserve the value masked to the expected width
    mask = (1 << plan.value_width) - 1
    
    # Retrieve request mock or default
    request = plan.evidence.get("request")
    if request is None:
        request = CrossManifoldTransferRequest(
            request_id=f"REQ_{plan.route.route_id}",
            source_domain_id=plan.source_domain.manifold_id,
            target_domain_id=plan.target_domain.manifold_id,
            value=0xDEADBEEF & mask,
            value_width=plan.value_width
        )
    
    # Ensure validation check
    passed_validation = validate_geodesic_route(plan.route)
    
    evidence = {
        "validation_passed": passed_validation,
        "attenuation_loss": 0.03,
        "accumulated_delay_ms": sum(hop.delay_ms for hop in plan.route.hops)
    }
    
    return CrossManifoldTransferResult(
        request=request,
        transferred_value=request.value & mask,
        passed_gates=passed_validation,
        evidence=evidence
    )


def plan_consensus_routed_transfer(
    request: CrossManifoldTransferRequest,
    consensus_group: Any
) -> GeodesicRoutePlan:
    """
    Plans a cross-manifold transfer requiring group consensus.
    """
    plan = plan_cross_manifold_transfer(request)
    plan.evidence["consensus_group"] = consensus_group
    return plan


def execute_shadow_consensus_transfer(
    plan: GeodesicRoutePlan
) -> CrossManifoldTransferResult:
    """
    Shadow executes a cross-manifold transfer gated by route validation,
    entanglement stability, and consensus quorum.
    """
    # 1. Route validity
    passed_validation = validate_geodesic_route(plan.route)
    
    # 2. Entanglement stability
    stability_passed = plan.target_domain.metadata.get("stability_passed", True)
    
    # 3. Consensus quorum
    consensus_group = plan.evidence.get("consensus_group")
    quorum_reached = True
    if consensus_group is not None:
        quorum_reached = getattr(consensus_group, "metadata", {}).get("quorum_reached", True)
        if isinstance(consensus_group, dict):
            quorum_reached = consensus_group.get("metadata", {}).get("quorum_reached", True)
        
    # 4. Oracle match
    request = plan.evidence.get("request")
    oracle_match = True
    if request is not None:
        oracle_val = request.metadata.get("oracle_value")
        if oracle_val is not None:
            oracle_match = (request.value == oracle_val)
            
    passed_gates = passed_validation and stability_passed and quorum_reached and oracle_match
    
    mask = (1 << plan.value_width) - 1
    val = request.value & mask if request else 0
    
    evidence = {
        "validation_passed": passed_validation,
        "stability_passed": stability_passed,
        "quorum_reached": quorum_reached,
        "oracle_match": oracle_match,
        "passed_gates": passed_gates
    }
    
    if request is None:
        request = CrossManifoldTransferRequest(
            request_id=f"REQ_CONSENSUS_{plan.route.route_id}",
            source_domain_id=plan.source_domain.manifold_id,
            target_domain_id=plan.target_domain.manifold_id,
            value=val,
            value_width=plan.value_width
        )
        
    return CrossManifoldTransferResult(
        request=request,
        transferred_value=val,
        passed_gates=passed_gates,
        evidence=evidence
    )


@dataclass
class AtomicGeodesicRoutePlan:
    requests: List[CrossManifoldTransferRequest]
    consensus_group: Any
    route_plans: List[GeodesicRoutePlan]
    evidence: Dict[str, Any] = field(default_factory=dict)


def plan_atomic_cross_manifold_commit(
    requests: List[CrossManifoldTransferRequest],
    consensus_group: Any
) -> AtomicGeodesicRoutePlan:
    """
    Plans atomic cross-manifold routing commitments.
    """
    route_plans = []
    for req in requests:
        plan = plan_cross_manifold_transfer(req)
        # Link consensus group
        plan.evidence["consensus_group"] = consensus_group
        route_plans.append(plan)
        
    evidence = {
        "planned_at": time.time(),
        "total_requests": len(requests),
        "consensus_group": consensus_group
    }
    return AtomicGeodesicRoutePlan(
        requests=requests,
        consensus_group=consensus_group,
        route_plans=route_plans,
        evidence=evidence
    )


def execute_shadow_atomic_route_commit(
    plan: AtomicGeodesicRoutePlan
) -> CrossManifoldTransferResult:
    """
    Shadow executes atomic cross-manifold transfers and checks stability gates.
    """
    results = []
    all_passed = True
    
    source_domains = []
    target_domains = []
    route_ids = []
    boundary_crossings = []
    route_stability = True
    oracle_match = True
    
    for r_plan in plan.route_plans:
        # Check target stability
        stability_passed = r_plan.target_domain.metadata.get("stability_passed", True)
        if not stability_passed:
            route_stability = False
            
        # Check validation
        route_ok = validate_geodesic_route(r_plan.route)
        
        # Check oracle match
        req = r_plan.evidence.get("request")
        if req is not None:
            oracle_val = req.metadata.get("oracle_value")
            if oracle_val is not None:
                if req.value != oracle_val:
                    oracle_match = False
                    
        passed = route_ok and stability_passed and oracle_match
        if not passed:
            all_passed = False
            
        # Execute individual shadow consensus transfer
        res = execute_shadow_consensus_transfer(r_plan)
        results.append(res)
        
        # Collect reporting data
        source_domains.append(r_plan.source_domain.manifold_id)
        target_domains.append(r_plan.target_domain.manifold_id)
        route_ids.append(r_plan.route.route_id)
        boundary_crossings.extend(r_plan.route.boundary_crossings)
        
    evidence = {
        "source_domains": source_domains,
        "target_domains": target_domains,
        "route_ids": route_ids,
        "boundary_crossings": list(set(boundary_crossings)),
        "route_stability": route_stability,
        "oracle_match": oracle_match,
        "all_passed": all_passed,
        "individual_results": results
    }
    
    # Return a combined result
    first_req = plan.requests[0] if plan.requests else None
    req = CrossManifoldTransferRequest(
        request_id=f"ATOMIC_REQ_{int(time.time())}",
        source_domain_id=str(source_domains),
        target_domain_id=str(target_domains),
        value=first_req.value if first_req else 0,
        value_width=first_req.value_width if first_req else 64
    )
    
    return CrossManifoldTransferResult(
        request=req,
        transferred_value=first_req.value if (first_req and all_passed) else 0,
        passed_gates=all_passed,
        evidence=evidence
    )


@dataclass
class ShardedRoutePlan:
    request: CrossManifoldTransferRequest
    source_shard: ShardId
    target_shard: ShardId
    route: CrossManifoldRoute
    shard_topology: ShardTopology
    rollback_available: bool = True
    evidence: Dict[str, Any] = field(default_factory=dict)


def plan_sharded_cross_manifold_transfer(
    request: CrossManifoldTransferRequest,
    shard_topology: ShardTopology
) -> ShardedRoutePlan:
    """
    Plans a cross-manifold routing path across shard domains.
    """
    src_shard = assign_manifold_to_shard(request.source_domain_id, shard_topology)
    tgt_shard = assign_manifold_to_shard(request.target_domain_id, shard_topology)
    
    # Convert domain IDs to mock domains
    src_domain = ManifoldDomain(
        manifold_id=request.source_domain_id,
        domain_name=f"Domain_{request.source_domain_id}",
        lanes=list(range(request.value_width // 8))
    )
    tgt_domain = ManifoldDomain(
        manifold_id=request.target_domain_id,
        domain_name=f"Domain_{request.target_domain_id}",
        lanes=list(range(request.value_width // 8))
    )
    
    route = build_geodesic_route(src_domain, tgt_domain, request.value_width)
    
    # Calculate boundary crossings between src_shard and tgt_shard
    crossings = []
    if src_shard != tgt_shard:
        crossings.append(f"{src_shard.shard_id}_to_{tgt_shard.shard_id}")
        
    route.boundary_crossings = list(set(route.boundary_crossings + crossings))
    
    evidence = {
        "planned_at": time.time(),
        "source_shard": src_shard.shard_id,
        "target_shard": tgt_shard.shard_id,
        "boundary_crossings": crossings
    }
    
    return ShardedRoutePlan(
        request=request,
        source_shard=src_shard,
        target_shard=tgt_shard,
        route=route,
        shard_topology=shard_topology,
        rollback_available=True,
        evidence=evidence
    )


def validate_sharded_route(plan: ShardedRoutePlan) -> bool:
    """
    Validates sharded route boundaries and limits.
    """
    boundary_crossings = plan.evidence.get("boundary_crossings", [])
    if len(boundary_crossings) > 4:
        return False
        
    if plan.source_shard.shard_id not in plan.shard_topology.shards:
        return False
    if plan.target_shard.shard_id not in plan.shard_topology.shards:
        return False
        
    return validate_geodesic_route(plan.route)


