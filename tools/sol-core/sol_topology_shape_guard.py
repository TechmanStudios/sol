# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Topology Shape Guard
========================
Protects and validates structural shape properties, PML boundaries, H-CAM banks, and other layout bounds.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

@dataclass
class TopologyShapeSnapshot:
    snapshot_id: str
    node_count: int
    edge_count: int
    lane_bindings: List[str] = field(default_factory=list)
    carrier_bindings: List[str] = field(default_factory=list)
    pml_boundaries: List[str] = field(default_factory=list)
    hcam_banks: List[str] = field(default_factory=list)
    prefix_carry_bridges: List[str] = field(default_factory=list)
    transaction_boundaries: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TopologyShapeComparison:
    before: TopologyShapeSnapshot
    after: TopologyShapeSnapshot
    node_count_preserved: bool
    edge_count_preserved: bool
    lane_bindings_preserved: bool
    carrier_bindings_preserved: bool
    pml_boundaries_preserved: bool
    hcam_banks_preserved: bool
    prefix_carry_bridges_preserved: bool
    transaction_boundaries_preserved: bool
    is_lossless: bool = True

@dataclass
class TopologyShapeGuardReport:
    report_id: str
    comparison: TopologyShapeComparison
    passed: bool
    errors: List[str] = field(default_factory=list)


def capture_topology_shape_snapshot(topology: Any) -> TopologyShapeSnapshot:
    """
    Captures properties from the topology object into a snapshot.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    node_count = extract(topology, "node_count", 0) or len(extract(topology, "nodes", []))
    edge_count = extract(topology, "edge_count", 0) or len(extract(topology, "edges", []))
    
    return TopologyShapeSnapshot(
        snapshot_id=f"SHAPE_SNAP_{uuid.uuid4().hex[:8]}",
        node_count=node_count,
        edge_count=edge_count,
        lane_bindings=list(extract(topology, "lane_bindings", [])),
        carrier_bindings=list(extract(topology, "carrier_bindings", [])),
        pml_boundaries=list(extract(topology, "pml_boundaries", [])),
        hcam_banks=list(extract(topology, "hcam_banks", [])),
        prefix_carry_bridges=list(extract(topology, "prefix_carry_bridges", [])),
        transaction_boundaries=list(extract(topology, "transaction_boundaries", []))
    )


def compare_topology_shape_snapshots(
    before: TopologyShapeSnapshot,
    after: TopologyShapeSnapshot
) -> TopologyShapeComparison:
    """
    Compares two shape snapshots to check what was preserved.
    """
    node_preserved = before.node_count == after.node_count
    edge_preserved = before.edge_count == after.edge_count
    
    lane_preserved = set(before.lane_bindings) == set(after.lane_bindings)
    carrier_preserved = set(before.carrier_bindings) == set(after.carrier_bindings)
    pml_preserved = set(before.pml_boundaries) == set(after.pml_boundaries)
    hcam_preserved = set(before.hcam_banks) == set(after.hcam_banks)
    prefix_preserved = set(before.prefix_carry_bridges) == set(after.prefix_carry_bridges)
    tx_preserved = set(before.transaction_boundaries) == set(after.transaction_boundaries)
    
    # We default lossless to whether nodes count match
    is_lossless = node_preserved
    
    return TopologyShapeComparison(
        before=before,
        after=after,
        node_count_preserved=node_preserved,
        edge_count_preserved=edge_preserved,
        lane_bindings_preserved=lane_preserved,
        carrier_bindings_preserved=carrier_preserved,
        pml_boundaries_preserved=pml_preserved,
        hcam_banks_preserved=hcam_preserved,
        prefix_carry_bridges_preserved=prefix_preserved,
        transaction_boundaries_preserved=tx_preserved,
        is_lossless=is_lossless
    )


def validate_topology_shape_preservation(
    comparison: TopologyShapeComparison,
    policy: Any
) -> TopologyShapeGuardReport:
    """
    Validates the structural comparison against policy rules.
    If lossless is declared, node count must be preserved. Edge, lane, carrier, etc. must be checked.
    """
    errors = []
    
    # Policy checks
    if comparison.is_lossless and not comparison.node_count_preserved:
        errors.append("Topology shape guard violation: node count mismatch in lossless reshape.")
        
    preserve_lanes = getattr(policy, "preserve_active_phase_tables", True) # policy fields map
    # Or check direct fields
    if not comparison.lane_bindings_preserved:
        errors.append("Topology shape guard violation: missing lane binding preservation.")
    if not comparison.carrier_bindings_preserved:
        errors.append("Topology shape guard violation: missing carrier binding preservation.")
    if not comparison.pml_boundaries_preserved:
        errors.append("Topology shape guard violation: missing PML boundary preservation.")
    if not comparison.hcam_banks_preserved:
        errors.append("Topology shape guard violation: missing H-CAM bank preservation.")
    if not comparison.prefix_carry_bridges_preserved:
        errors.append("Topology shape guard violation: missing prefix-carry bridge preservation.")
    if not comparison.transaction_boundaries_preserved:
        errors.append("Topology shape guard violation: missing transaction boundary preservation.")

    # Check node count explicitly to allow testing missing nodes
    if not comparison.node_count_preserved:
        errors.append("Topology shape guard violation: node count not preserved.")

    passed = len(errors) == 0
    return TopologyShapeGuardReport(
        report_id=f"GUARD_RPT_{uuid.uuid4().hex[:8]}",
        comparison=comparison,
        passed=passed,
        errors=errors
    )
