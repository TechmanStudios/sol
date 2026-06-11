# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Topology Relocation Manifest
================================
Maintains and validates the official manifest registry containing relocation proof and court decisions.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

@dataclass
class TopologyRelocationEvidence:
    evidence_id: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TopologyRelocationGateSnapshot:
    snapshot_id: str
    gate_results: Dict[str, bool] = field(default_factory=dict)

@dataclass
class TopologyRelocationRollbackRef:
    rollback_id: str
    snapshot_ref: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TopologyRelocationVerdict:
    verdict_id: str
    decision: str  # e.g., "accept_shadow_topology_relocation"
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TopologyRelocationManifest:
    manifest_id: str
    candidate_id: str
    before_hash: str = ""
    after_hash: str = ""
    shape_maps: Dict[str, Any] = field(default_factory=dict)
    coordinate_remap_tables: Dict[str, Any] = field(default_factory=dict)
    carrier_remap_tables: Dict[str, Any] = field(default_factory=dict)
    lane_remap_tables: Dict[str, Any] = field(default_factory=dict)
    waveguide_remap_tables: Dict[str, Any] = field(default_factory=dict)
    rollback_refs: List[TopologyRelocationRollbackRef] = field(default_factory=list)
    ranger_packets: List[Any] = field(default_factory=list)
    court_decisions: List[TopologyRelocationVerdict] = field(default_factory=list)
    evidence: List[TopologyRelocationEvidence] = field(default_factory=list)
    gate_snapshots: List[TopologyRelocationGateSnapshot] = field(default_factory=list)
    is_valid: bool = False


def open_topology_relocation_manifest(candidate_id: str) -> TopologyRelocationManifest:
    """
    Initializes a new topology relocation manifest.
    """
    return TopologyRelocationManifest(
        manifest_id=f"MANIFEST_{uuid.uuid4().hex[:8]}",
        candidate_id=candidate_id
    )


def attach_topology_relocation_evidence(
    manifest: TopologyRelocationManifest,
    evidence: TopologyRelocationEvidence
) -> None:
    """
    Attaches a relocation evidence packet to the manifest.
    """
    manifest.evidence.append(evidence)


def attach_topology_gate_snapshot(
    manifest: TopologyRelocationManifest,
    gate_snapshot: TopologyRelocationGateSnapshot
) -> None:
    """
    Attaches a gate status check snapshot to the manifest.
    """
    manifest.gate_snapshots.append(gate_snapshot)


def attach_topology_rollback_ref(
    manifest: TopologyRelocationManifest,
    rollback_ref: TopologyRelocationRollbackRef
) -> None:
    """
    Attaches a rollback snapshot reference to the manifest.
    """
    manifest.rollback_refs.append(rollback_ref)


def validate_topology_relocation_manifest(manifest: TopologyRelocationManifest) -> bool:
    """
    Validates that the manifest contains all necessary relocation elements.
    If rollback references or other critical fields are missing, it raises a ValueError.
    """
    if not manifest.rollback_refs:
        manifest.is_valid = False
        raise ValueError("Manifest validation failed: missing rollback references.")
        
    if not manifest.before_hash or not manifest.after_hash:
        manifest.is_valid = False
        raise ValueError("Manifest validation failed: missing before/after topology hashes.")
        
    if not manifest.coordinate_remap_tables:
        manifest.is_valid = False
        raise ValueError("Manifest validation failed: missing coordinate remap tables.")
        
    manifest.is_valid = True
    return True
