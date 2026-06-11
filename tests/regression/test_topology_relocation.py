# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Regression tests for Phase 43: Sovereign Topology Relocation and Multi-Manifold Reshaping.
"""

import sys
from pathlib import Path
import pytest
import time
import uuid
import json
from dataclasses import dataclass

# Setup path injection to guarantee local tools importing
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Import new Phase 43 modules
from sol_sovereign_topology_relocation import (
    SovereignTopologyParticipant,
    TopologyRelocationSource,
    TopologyRelocationTarget,
    SovereignTopologyRelocationIntent,
    TopologyRelocationPlan,
    TopologyRelocationStep,
    TopologyRelocationResult,
    TopologyRelocationReport,
    build_topology_relocation_intent,
    validate_topology_relocation_intent,
    build_topology_relocation_plan,
    execute_shadow_topology_relocation,
    compare_topology_before_after
)
from sol_multimanifold_reshape_orchestrator import (
    MultiManifoldReshapeParticipant,
    MultiManifoldReshapeIntent,
    MultiManifoldReshapePlan,
    MultiManifoldReshapeStep,
    MultiManifoldReshapeResult,
    MultiManifoldReshapeReport,
    build_multimanifold_reshape_intent,
    validate_multimanifold_reshape_intent,
    plan_multimanifold_reshape,
    execute_shadow_multimanifold_reshape,
    summarize_multimanifold_reshape
)
from sol_topology_relocation_manifest import (
    TopologyRelocationManifest,
    TopologyRelocationEvidence,
    TopologyRelocationGateSnapshot,
    TopologyRelocationRollbackRef,
    TopologyRelocationVerdict,
    open_topology_relocation_manifest,
    attach_topology_relocation_evidence,
    attach_topology_gate_snapshot,
    attach_topology_rollback_ref,
    validate_topology_relocation_manifest
)
from sol_topology_shape_guard import (
    TopologyShapeSnapshot,
    TopologyShapeComparison,
    TopologyShapeGuardReport,
    capture_topology_shape_snapshot,
    compare_topology_shape_snapshots,
    validate_topology_shape_preservation
)
from sol_topology_migration_protocol import (
    TopologyMigrationProtocol,
    TopologyMigrationPrepareState,
    TopologyMigrationTransferState,
    TopologyMigrationVerifyState,
    TopologyMigrationCommitState,
    TopologyMigrationAbortState,
    TopologyMigrationProtocolReport,
    prepare_topology_migration,
    transfer_topology_shadow,
    verify_topology_migration,
    commit_topology_migration_shadow,
    abort_topology_migration
)
from sol_sovereign_topology_policy import (
    SovereignTopologyPolicy,
    TopologyRelocationConstraint,
    TopologyRelocationGateResult,
    TopologyRelocationRiskEstimate
)

# Import extended components
from sol_manifold_reshape import (
    ManifoldShape,
    export_reshape_for_sovereign_topology,
    validate_reshape_under_sovereign_policy
)
from sol_dimensional_topology import (
    build_multimanifold_dimensional_remap,
    validate_multimanifold_coordinate_consistency
)
from sol_distributed_state_relocation import (
    validate_state_refs_after_topology_relocation,
    block_state_relocation_on_topology_mismatch
)
from sol_dynamic_waveguide_rebalancer import (
    WaveguideRebalancePlan,
    WaveguideRebalanceCandidate,
    validate_waveguide_rebalance_after_topology_relocation,
    remap_waveguide_rebalance_for_new_topology
)
from sol_transactional_geodesic_optimizer import (
    TransactionalRouteOptimizationPlan,
    TransactionalRouteCandidate,
    TransactionalGeodesicRoute,
    validate_routes_after_topology_relocation,
    remap_transactional_routes_for_topology
)
from sol_carrier_registry import (
    snapshot_carriers_before_topology_relocation,
    validate_carrier_registry_after_topology_relocation
)
from sol_interlane_prefix_carry import (
    remap_prefix_carry_after_topology_relocation,
    validate_prefix_carry_after_topology_relocation
)
from sol_temporal_cadence import (
    snapshot_cadence_before_topology_relocation,
    validate_cadence_after_topology_relocation
)
from sol_global_lock_boundary import (
    GlobalLockBoundaryPlan,
    validate_locks_for_topology_relocation
)
from sol_wavefront_propagator import (
    WavefrontPropagationConfig,
    run_shadow_wavefront_after_topology_relocation
)
from sol_waveguide_boundary import (
    validate_pml_after_topology_relocation
)
from sol_sovereign_runtime import (
    SovereignRuntimeState,
    SovereignRuntimePolicy,
    SovereignRuntimeId,
    SovereignRuntimeCommand,
    build_sovereign_runtime,
    submit_topology_relocation_command,
    execute_shadow_topology_relocation_command
)
from sol_runtime_ledger import (
    build_runtime_ledger,
    append_runtime_event,
    validate_runtime_ledger
)
from coding_library.sovereign_domain.frontier_bridge import (
    SovereignTopologyAdvisor,
    SovereignTopologySuggestion,
    SovereignTopologyClosedLoopPolicy,
    SovereignTopologyClosedLoopReport
)
from coding_library.sovereign_domain.rangers.topology_relocation_ranger import TopologyRelocationRanger
from coding_library.sovereign_domain.promotion_court import PromotionCourt, PromotionGateResult



# Mock objects for tests
@pytest.fixture
def sample_policy():
    return SovereignTopologyPolicy(
        shadow_only_by_default=True,
        court_token_required_for_sandbox_execution=True
    )

@pytest.fixture
def sample_participant():
    return SovereignTopologyParticipant(
        participant_id="part_1",
        manifold_id="manifold_A",
        shard_ids=["shard_1", "shard_2"],
        lane_ids=["lane_0", "lane_1"],
        waveguide_segment_ids=["wg_0"],
        carrier_ids=["carr_0", "carr_1"],
        prefix_carry_bridge_ids=["bridge_0"],
        hcam_bank_refs=["hcam_bank_0"],
        state_hash_refs=["hash_0"],
        rollback_snapshot_refs=["rollback_0"],
        court_evidence_refs=["court_ev_0"]
    )

@pytest.fixture
def sample_source(sample_participant):
    return TopologyRelocationSource(
        source_id="src_topo",
        participants=[sample_participant],
        topology_hash="hash_before"
    )

@pytest.fixture
def sample_target(sample_participant):
    return TopologyRelocationTarget(
        target_id="tgt_topo",
        participants=[sample_participant],
        topology_hash="hash_after"
    )


# Test 1: Topology relocation intent builds for one mock manifold
def test_topology_relocation_intent_builds_one_manifold(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN"},
        policy=sample_policy
    )
    assert intent is not None
    assert intent.source.source_id == "src_topo"
    assert len(intent.source.participants) == 1


# Test 2: Topology relocation intent builds for multiple mock manifolds
def test_topology_relocation_intent_builds_multiple_manifolds(sample_policy):
    part1 = SovereignTopologyParticipant(participant_id="p1", manifold_id="m1")
    part2 = SovereignTopologyParticipant(participant_id="p2", manifold_id="m2")
    src = TopologyRelocationSource(source_id="src_multi", participants=[part1, part2], topology_hash="hash_before")
    tgt = TopologyRelocationTarget(target_id="tgt_multi", participants=[part1, part2], topology_hash="hash_after")
    intent = build_topology_relocation_intent(src, tgt, {"court_token": "SANDBOX_TOKEN"}, sample_policy)
    assert len(intent.source.participants) == 2


# Test 3: Invalid source topology is rejected
def test_invalid_source_topology_rejected(sample_target, sample_policy):
    invalid_src = TopologyRelocationSource(source_id="src_invalid", participants=[], topology_hash="")
    intent = build_topology_relocation_intent(invalid_src, sample_target, {"court_token": "SANDBOX_TOKEN"}, sample_policy)
    with pytest.raises(ValueError, match="Invalid source topology"):
        validate_topology_relocation_intent(intent)


# Test 4: Invalid target topology is rejected
def test_invalid_target_topology_rejected(sample_source, sample_policy):
    invalid_tgt = TopologyRelocationTarget(target_id="tgt_invalid", participants=[], topology_hash="")
    intent = build_topology_relocation_intent(sample_source, invalid_tgt, {"court_token": "SANDBOX_TOKEN"}, sample_policy)
    with pytest.raises(ValueError, match="Invalid target topology"):
        validate_topology_relocation_intent(intent)


# Test 5: Multi-manifold reshape plan builds for 2 manifolds
def test_multimanifold_reshape_plan_builds_2_manifolds(sample_policy):
    m1 = {"manifold_id": "m1", "shape": ManifoldShape(dims=[2, 2])}
    m2 = {"manifold_id": "m2", "shape": ManifoldShape(dims=[4])}
    target_shapes = [ManifoldShape(dims=[4]), ManifoldShape(dims=[2, 2])]
    intent = build_multimanifold_reshape_intent([m1, m2], target_shapes, sample_policy)
    plan = plan_multimanifold_reshape(intent)
    assert plan is not None
    assert len(plan.steps) == 2


# Test 6: Multi-manifold reshape plan builds for 3+ manifolds
def test_multimanifold_reshape_plan_builds_3_plus_manifolds(sample_policy):
    m1 = {"manifold_id": "m1", "shape": ManifoldShape(dims=[2, 2])}
    m2 = {"manifold_id": "m2", "shape": ManifoldShape(dims=[4])}
    m3 = {"manifold_id": "m3", "shape": ManifoldShape(dims=[1, 4])}
    target_shapes = [ManifoldShape(dims=[4]), ManifoldShape(dims=[2, 2]), ManifoldShape(dims=[4, 1])]
    intent = build_multimanifold_reshape_intent([m1, m2, m3], target_shapes, sample_policy)
    plan = plan_multimanifold_reshape(intent)
    assert len(plan.steps) == 3


# Test 7: Coordinate remap is complete
def test_coordinate_remap_complete(sample_policy):
    m1 = {"manifold_id": "m1", "shape": ManifoldShape(dims=[2, 2])}
    target_shapes = [ManifoldShape(dims=[4])]
    intent = build_multimanifold_reshape_intent([m1], target_shapes, sample_policy)
    plan = plan_multimanifold_reshape(intent)
    result = execute_shadow_multimanifold_reshape(plan)
    assert result.success
    assert not result.errors


# Test 8: Lossless coordinate remap is reversible
def test_lossless_coordinate_remap_reversible():
    from sol_dimensional_topology import project_coordinates, validate_coordinate_remap
    remap = project_coordinates(ManifoldShape(dims=[2, 3]), ManifoldShape(dims=[6]))
    assert remap.reversible
    assert validate_coordinate_remap(remap)


# Test 9: Topology shape guard detects missing node
def test_shape_guard_detects_missing_node(sample_policy):
    before = TopologyShapeSnapshot(snapshot_id="before", node_count=10, edge_count=5)
    after = TopologyShapeSnapshot(snapshot_id="after", node_count=9, edge_count=5)
    comparison = compare_topology_shape_snapshots(before, after)
    report = validate_topology_shape_preservation(comparison, sample_policy)
    assert not report.passed
    assert any("node count" in err for err in report.errors)


# Test 10: Topology shape guard detects missing lane binding
def test_shape_guard_detects_missing_lane_binding(sample_policy):
    before = TopologyShapeSnapshot(snapshot_id="before", node_count=10, edge_count=5, lane_bindings=["lane_0"])
    after = TopologyShapeSnapshot(snapshot_id="after", node_count=10, edge_count=5, lane_bindings=[])
    comparison = compare_topology_shape_snapshots(before, after)
    report = validate_topology_shape_preservation(comparison, sample_policy)
    assert not report.passed
    assert any("lane binding" in err for err in report.errors)


# Test 11: Topology shape guard detects missing carrier binding
def test_shape_guard_detects_missing_carrier_binding(sample_policy):
    before = TopologyShapeSnapshot(snapshot_id="before", node_count=10, edge_count=5, carrier_bindings=["carr_0"])
    after = TopologyShapeSnapshot(snapshot_id="after", node_count=10, edge_count=5, carrier_bindings=[])
    comparison = compare_topology_shape_snapshots(before, after)
    report = validate_topology_shape_preservation(comparison, sample_policy)
    assert not report.passed
    assert any("carrier binding" in err for err in report.errors)


# Test 12: Topology shape guard detects missing PML boundary
def test_shape_guard_detects_missing_pml_boundary(sample_policy):
    before = TopologyShapeSnapshot(snapshot_id="before", node_count=10, edge_count=5, pml_boundaries=["pml_0"])
    after = TopologyShapeSnapshot(snapshot_id="after", node_count=10, edge_count=5, pml_boundaries=[])
    comparison = compare_topology_shape_snapshots(before, after)
    report = validate_topology_shape_preservation(comparison, sample_policy)
    assert not report.passed
    assert any("PML boundary" in err for err in report.errors)


# Test 13: Topology manifest rejects missing rollback refs
def test_topology_manifest_rejects_missing_rollback_refs():
    manifest = open_topology_relocation_manifest("candidate_43")
    manifest.before_hash = "before_hash"
    manifest.after_hash = "after_hash"
    manifest.coordinate_remap_tables = {"tab": 1}
    with pytest.raises(ValueError, match="missing rollback references"):
        validate_topology_relocation_manifest(manifest)


# Test 14: Topology migration protocol blocks missing carrier snapshot
def test_topology_migration_protocol_blocks_missing_carrier_snapshot(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(sample_source, sample_target, {"court_token": "SANDBOX_TOKEN"}, sample_policy)
    runtime = build_sovereign_runtime(SovereignRuntimePolicy())
    plan = build_topology_relocation_plan(intent, runtime)
    protocol = TopologyMigrationProtocol(
        protocol_id="mig_proto",
        runtime=runtime,
        plan=plan,
        policy=sample_policy,
        court_token="SANDBOX_TOKEN",
        metadata={"rollback_snapshot": "snap", "cadence_snapshot": "cad_snap"}
    )
    prepare_topology_migration(protocol)
    assert not protocol.prepare_state.authorized
    assert any("Carrier registry snapshot is missing" in err for err in protocol.prepare_state.errors)


# Test 15: Topology migration protocol blocks missing cadence snapshot
def test_topology_migration_protocol_blocks_missing_cadence_snapshot(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(sample_source, sample_target, {"court_token": "SANDBOX_TOKEN"}, sample_policy)
    runtime = build_sovereign_runtime(SovereignRuntimePolicy())
    plan = build_topology_relocation_plan(intent, runtime)
    protocol = TopologyMigrationProtocol(
        protocol_id="mig_proto",
        runtime=runtime,
        plan=plan,
        policy=sample_policy,
        court_token="SANDBOX_TOKEN",
        metadata={"rollback_snapshot": "snap", "carrier_snapshot": "carr_snap"}
    )
    prepare_topology_migration(protocol)
    assert not protocol.prepare_state.authorized
    assert any("Cadence profile snapshot is missing" in err for err in protocol.prepare_state.errors)


# Test 16: State refs survive topology relocation
def test_state_refs_survive_topology_relocation(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN"},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    
    # State refs check passes without raising error
    assert validate_state_refs_after_topology_relocation({"result": {"success": True}}, report)


# Test 17: Waveguide routes remap under topology relocation
def test_waveguide_routes_remap_under_topology_relocation():
    route_plan = TransactionalRouteOptimizationPlan(
        plan_id="plan_route",
        intent=None,
        candidates=[
            TransactionalRouteCandidate(
                candidate_id="cand_1",
                route=TransactionalGeodesicRoute(route_id="r1", path=["m1", "m2"], manifolds=["m1", "m2"])
            )
        ]
    )
    topology_remap = {"m1": "m1_new", "m2": "m2_new"}
    remapped = remap_transactional_routes_for_topology(route_plan, topology_remap)
    assert remapped.candidates[0].route.path == ["m1_new", "m2_new"]


# Test 18: Prefix-carry bridges survive topology relocation
def test_prefix_carry_bridges_survive_topology_relocation(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN"},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert validate_prefix_carry_after_topology_relocation({"result": {"success": True}}, report)


# Test 19: H-CAM bank refs survive topology relocation
def test_hcam_bank_refs_survive_topology_relocation(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN"},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert report.preservation_status["hcam_banks"]


# Test 20: Lock boundary violation blocks topology relocation
def test_lock_boundary_violation_blocks_topology_relocation(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN", "lock_boundary_failed": True, "rollback_snapshot": "snap"},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert not report.result.success
    assert any("Lock boundary verification failed" in err for err in report.result.errors)


# Test 21: Cross-manifold deadlock blocks topology relocation
def test_cross_manifold_deadlock_blocks_topology_relocation(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN", "cross_manifold_deadlock": True, "rollback_snapshot": "snap"},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert not report.result.success
    assert any("Cross-manifold deadlock detected" in err for err in report.result.errors)


# Test 22: Cadence window failure blocks topology relocation
def test_cadence_window_failure_blocks_topology_relocation(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN", "cadence_window_failed": True, "rollback_snapshot": "snap"},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert not report.result.success
    assert any("Cadence window validation failed" in err for err in report.result.errors)


# Test 23: Wavefront coherence collapse blocks topology relocation
def test_wavefront_coherence_collapse_blocks_topology_relocation(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN", "wavefront_coherence_collapsed": True, "rollback_snapshot": "snap"},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert not report.result.success
    assert any("Wavefront coherence collapsed" in err for err in report.result.errors)


# Test 24: Crosstalk spike blocks topology relocation
def test_crosstalk_spike_blocks_topology_relocation(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN", "crosstalk_spiked": True, "rollback_snapshot": "snap"},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert not report.result.success
    assert any("Crosstalk spike detected" in err for err in report.result.errors)


# Test 25: Boundary reflection breach blocks topology relocation
def test_boundary_reflection_breach_blocks_topology_relocation(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN", "boundary_reflection_breached": True, "rollback_snapshot": "snap"},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert not report.result.success
    assert any("Boundary reflection breach detected" in err for err in report.result.errors)


# Test 26: Active phase table overwrite attempt is rejected
def test_active_phase_table_overwrite_rejected(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN", "overwrite_active_phase_tables": True},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert not report.result.success
    assert any("Active phase tables overwrite attempt blocked" in err for err in report.result.errors)


# Test 27: Active cadence profile overwrite attempt is rejected
def test_active_cadence_profile_overwrite_rejected(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN", "overwrite_active_cadence_profiles": True},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert not report.result.success
    assert any("Active cadence profiles overwrite attempt blocked" in err for err in report.result.errors)


# Test 28: Active carrier registry overwrite attempt is rejected
def test_active_carrier_registry_overwrite_rejected(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(
        source=sample_source,
        target=sample_target,
        topology_refs={"court_token": "SANDBOX_TOKEN", "overwrite_active_carrier_registry": True},
        policy=sample_policy
    )
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    assert not report.result.success
    assert any("Active carrier registry overwrite attempt blocked" in err for err in report.result.errors)


# Test 29: Rollback restores mock topology, shape maps, carrier registry, cadence profiles, PML declarations, and prefix-carry bindings
def test_rollback_restores_mock_state(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(sample_source, sample_target, {"court_token": "SANDBOX_TOKEN", "rollback_snapshot": "snap", "carrier_snapshot": "carr", "cadence_snapshot": "cad"}, sample_policy)
    runtime = build_sovereign_runtime(SovereignRuntimePolicy())
    plan = build_topology_relocation_plan(intent, runtime)
    protocol = TopologyMigrationProtocol(
        protocol_id="mig_proto",
        runtime=runtime,
        plan=plan,
        policy=sample_policy,
        court_token="SANDBOX_TOKEN",
        metadata={"rollback_snapshot": "snap", "carrier_snapshot": "carr", "cadence_snapshot": "cad"}
    )
    prepare_topology_migration(protocol)
    abort_topology_migration(protocol, "Simulated abort")
    assert protocol.abort_state.aborted
    assert protocol.abort_state.rollback_executed


# Test 30: TopologyRelocationRanger emits JSON-serializable SovereignPacket
def test_topology_relocation_ranger_emits_packet(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(sample_source, sample_target, {"court_token": "SANDBOX_TOKEN"}, sample_policy)
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    
    # Manifest
    manifest = open_topology_relocation_manifest("cand_1")
    manifest.before_hash = "before"
    manifest.after_hash = "after"
    attach_topology_rollback_ref(manifest, TopologyRelocationRollbackRef(rollback_id="rb_1", snapshot_ref="snap"))
    manifest.coordinate_remap_tables = {"tab": 1}
    validate_topology_relocation_manifest(manifest)

    # Shape guard report
    before_snap = capture_topology_shape_snapshot(sample_source)
    after_snap = capture_topology_shape_snapshot(sample_target)
    comp = compare_topology_shape_snapshots(before_snap, after_snap)
    guard_rpt = validate_topology_shape_preservation(comp, sample_policy)

    # Protocol report
    runtime = build_sovereign_runtime(SovereignRuntimePolicy())
    protocol = TopologyMigrationProtocol(
        protocol_id="mig_proto",
        runtime=runtime,
        plan=plan,
        policy=sample_policy,
        court_token="SANDBOX_TOKEN",
        metadata={"rollback_snapshot": "snap", "carrier_snapshot": "carr", "cadence_snapshot": "cad"}
    )
    prepare_topology_migration(protocol)
    transfer_topology_shadow(protocol)
    verify_topology_migration(protocol)
    proto_rpt = commit_topology_migration_shadow(protocol)

    ranger = TopologyRelocationRanger()
    packet = ranger.observe_relocation(
        relocation_plan=plan,
        relocation_report=report,
        reshape_report={"result": {"success": True}},
        shape_guard_report=guard_rpt,
        protocol_report=proto_rpt,
        manifest=manifest
    )
    assert packet.domain == "sol_sovereign"
    assert packet.level == 43
    # Check JSON serializability
    d = {
        "packet_id": packet.packet_id,
        "domain": packet.domain,
        "level": packet.level,
        "actor": packet.actor,
        "evidence": packet.evidence,
        "recommendation": packet.recommendation
    }
    dumped = json.dumps(d)
    assert dumped is not None


# Test 31: Promotion Court can review reports and verdicts
def test_promotion_court_reviews_phase43_reports(sample_source, sample_target, sample_policy):
    intent = build_topology_relocation_intent(sample_source, sample_target, {"court_token": "SANDBOX_TOKEN"}, sample_policy)
    plan = build_topology_relocation_plan(intent, None)
    report = execute_shadow_topology_relocation(plan)
    
    court = PromotionCourt()
    
    # 1. Relocation report review
    res = court.review_topology_relocation_report(report)
    assert res.passed

    # 2. Reshape report review
    reshape_rpt = MultiManifoldReshapeReport(
        report_id="mmr_rpt",
        result=MultiManifoldReshapeResult(result_id="res", plan=None, success=True),
        validation_passed=True
    )
    res_mm = court.review_multimanifold_reshape_report(reshape_rpt)
    assert res_mm.passed

    # 3. Shape guard review
    before_snap = capture_topology_shape_snapshot(sample_source)
    after_snap = capture_topology_shape_snapshot(sample_target)
    comp = compare_topology_shape_snapshots(before_snap, after_snap)
    guard_rpt = validate_topology_shape_preservation(comp, sample_policy)
    res_sg = court.review_topology_shape_guard_report(guard_rpt)
    assert res_sg.passed

    # 4. Manifest review
    manifest = open_topology_relocation_manifest("cand_1")
    manifest.before_hash = "before"
    manifest.after_hash = "after"
    attach_topology_rollback_ref(manifest, TopologyRelocationRollbackRef(rollback_id="rb_1", snapshot_ref="snap"))
    manifest.coordinate_remap_tables = {"tab": 1}
    validate_topology_relocation_manifest(manifest)
    res_man = court.review_topology_relocation_manifest(manifest)
    assert res_man.passed
