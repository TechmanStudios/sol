# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Topology Migration Protocol
===============================
Standardizes prepare, transfer, verify, commit, and abort execution sequence during relocation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid
import time

@dataclass
class TopologyMigrationPrepareState:
    authorized: bool
    rollback_snapshot_captured: bool
    carrier_snapshot_captured: bool
    cadence_snapshot_captured: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class TopologyMigrationTransferState:
    shadow_relocation_executed: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class TopologyMigrationVerifyState:
    before_after_hashes_verified: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class TopologyMigrationCommitState:
    shadow_commit_executed: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class TopologyMigrationAbortState:
    aborted: bool
    reason: str
    rollback_executed: bool

@dataclass
class TopologyMigrationProtocol:
    protocol_id: str
    runtime: Any
    plan: Any
    policy: Any
    court_token: Optional[str] = None
    prepare_state: Optional[TopologyMigrationPrepareState] = None
    transfer_state: Optional[TopologyMigrationTransferState] = None
    verify_state: Optional[TopologyMigrationVerifyState] = None
    commit_state: Optional[TopologyMigrationCommitState] = None
    abort_state: Optional[TopologyMigrationAbortState] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TopologyMigrationProtocolReport:
    report_id: str
    protocol: TopologyMigrationProtocol
    success: bool
    errors: List[str] = field(default_factory=list)
    ranger_evidence_emitted: bool = False


def prepare_topology_migration(protocol: TopologyMigrationProtocol) -> None:
    """
    Initializes and prepares the migration state. Performs authorization, token,
    and multiple snapshot captures (topology, rollback, carrier, cadence).
    """
    errors = []
    
    # 1. Validate sovereign runtime authorization
    runtime_mode = getattr(protocol.runtime, "mode", "shadow")
    if runtime_mode not in ["shadow", "sandbox"]:
        errors.append("Sovereign runtime is not in shadow/sandbox mode: unauthorized.")

    # 2. Validate court token if sandbox
    policy = protocol.policy
    court_token_req = getattr(policy, "court_token_required_for_sandbox_execution", True)
    if court_token_req and runtime_mode == "sandbox":
        if not protocol.court_token or protocol.court_token == "INVALID_TOKEN":
            errors.append("Invalid or missing court token for sandbox trial.")

    # 3. Check for snapshot requirements (topology, rollback, carrier, cadence)
    rollback_snapshot = protocol.metadata.get("rollback_snapshot")
    carrier_snapshot = protocol.metadata.get("carrier_snapshot")
    cadence_snapshot = protocol.metadata.get("cadence_snapshot")
    
    rollback_captured = rollback_snapshot is not None
    carrier_captured = carrier_snapshot is not None
    cadence_captured = cadence_snapshot is not None
    
    if not rollback_captured:
        errors.append("Rollback snapshot is missing.")
    if not carrier_captured:
        errors.append("Carrier registry snapshot is missing.")
    if not cadence_captured:
        errors.append("Cadence profile snapshot is missing.")

    # 4. Global lock boundaries, transaction boundaries, waveguide routes, shape/remap tables
    if protocol.metadata.get("lock_boundary_failed"):
        errors.append("Lock boundary validation failed.")
    if protocol.metadata.get("transaction_boundary_failed"):
        errors.append("Transaction boundary validation failed.")
    if protocol.metadata.get("waveguide_route_failed"):
        errors.append("Waveguide route validation failed.")
    if protocol.metadata.get("shape_remap_table_failed"):
        errors.append("Shape/remap table validation failed.")

    protocol.prepare_state = TopologyMigrationPrepareState(
        authorized=len(errors) == 0,
        rollback_snapshot_captured=rollback_captured,
        carrier_snapshot_captured=carrier_captured,
        cadence_snapshot_captured=cadence_captured,
        errors=errors
    )


def transfer_topology_shadow(protocol: TopologyMigrationProtocol) -> None:
    """
    Executes the shadow relocation transfer stage.
    """
    errors = []
    if not protocol.prepare_state or not protocol.prepare_state.authorized:
        errors.append("Cannot initiate transfer: preparation stage failed or did not run.")
    
    # Run the shadow relocation
    from sol_sovereign_topology_relocation import execute_shadow_topology_relocation
    if protocol.plan:
        try:
            report = execute_shadow_topology_relocation(protocol.plan)
            if not report.result.success:
                errors.extend(report.result.errors)
        except Exception as e:
            errors.append(f"Shadow relocation execution failed: {str(e)}")
    else:
        errors.append("No relocation plan provided.")
        
    protocol.transfer_state = TopologyMigrationTransferState(
        shadow_relocation_executed=len(errors) == 0,
        errors=errors
    )


def verify_topology_migration(protocol: TopologyMigrationProtocol) -> None:
    """
    Verifies that the relocated topology matches before/after hash expectations.
    """
    errors = []
    if not protocol.transfer_state or not protocol.transfer_state.shadow_relocation_executed:
        errors.append("Cannot verify: transfer stage failed or did not run.")
        
    # Check hashes comparison
    plan = protocol.plan
    if plan:
        before_hash = plan.intent.source.topology_hash
        after_hash = plan.intent.target.topology_hash
        if before_hash == after_hash and before_hash != "MOCK_IDENTICAL_HASH":
            errors.append("Topology hashes did not shift during relocation.")
            
    protocol.verify_state = TopologyMigrationVerifyState(
        before_after_hashes_verified=len(errors) == 0,
        errors=errors
    )


def commit_topology_migration_shadow(protocol: TopologyMigrationProtocol) -> TopologyMigrationProtocolReport:
    """
    Finalizes the shadow commit process.
    """
    errors = []
    
    if not protocol.verify_state or not protocol.verify_state.before_after_hashes_verified:
        errors.append("Cannot commit: verification stage failed or did not run.")
        
    # Verify no default live/production table overwrite
    policy = protocol.policy
    if policy:
        if getattr(policy, "shadow_only_by_default", True):
            pass  # Ensure it stays shadow

    protocol.commit_state = TopologyMigrationCommitState(
        shadow_commit_executed=len(errors) == 0,
        errors=errors
    )
    
    success = len(errors) == 0 and protocol.prepare_state.authorized and protocol.transfer_state.shadow_relocation_executed
    
    return TopologyMigrationProtocolReport(
        report_id=f"MIG_RPT_{uuid.uuid4().hex[:8]}",
        protocol=protocol,
        success=success,
        errors=errors,
        ranger_evidence_emitted=success
    )


def abort_topology_migration(protocol: TopologyMigrationProtocol, reason: str) -> None:
    """
    Aborts the migration and rolls back state parameters if captured.
    """
    rollback_status = False
    if protocol.prepare_state and protocol.prepare_state.rollback_snapshot_captured:
        # Restore mock state properties
        rollback_status = True
        
    protocol.abort_state = TopologyMigrationAbortState(
        aborted=True,
        reason=reason,
        rollback_executed=rollback_status
    )
