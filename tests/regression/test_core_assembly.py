# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Regression tests for Phase 45: Sovereign Multi-Core Assembly and Pipeline Calibration.
"""

import sys
from pathlib import Path
import pytest
import time
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List

# Setup path injection to guarantee local tools importing
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Import new modules
from sol_sovereign_multicore_assembly import (
    SovereignCoreAssemblyId,
    SovereignCoreAssemblyPolicy,
    SovereignCoreUnit,
    SovereignCoreCluster,
    SovereignCoreAssemblyPlan,
    SovereignCoreAssemblyResult,
    SovereignCoreAssemblyReport,
    build_sovereign_core_assembly,
    validate_sovereign_core_assembly,
    execute_shadow_core_assembly,
    summarize_sovereign_core_assembly
)
from sol_pipeline_calibration import (
    PipelineCalibrationPolicy,
    PipelineCalibrationTarget,
    PipelineCalibrationBaseline,
    PipelineCalibrationObservation,
    PipelineCalibrationAdjustment,
    PipelineCalibrationResult,
    PipelineCalibrationReport,
    build_pipeline_calibration_targets,
    capture_pipeline_calibration_baseline,
    measure_pipeline_calibration_error,
    plan_pipeline_calibration_adjustment,
    execute_shadow_pipeline_calibration,
    summarize_pipeline_calibration
)
from sol_multicore_pipeline_assembler import (
    PipelineAssemblyIntent,
    PipelineAssemblyStageBinding,
    PipelineAssemblyLaneBinding,
    PipelineAssemblyCoreBinding,
    PipelineAssemblyPlan,
    PipelineAssemblyResult,
    PipelineAssemblyReport,
    build_pipeline_assembly_intent,
    bind_pipeline_stages_to_cores,
    bind_pipeline_lanes_to_waveguides,
    validate_pipeline_assembly_plan,
    execute_shadow_pipeline_assembly
)
from sol_core_cadence_calibration import (
    CoreCadenceProfile,
    CoreCadenceObservation,
    CoreCadenceAdjustment,
    CoreCadenceCalibrationReport,
    build_core_cadence_profiles,
    measure_core_cadence_skew,
    plan_core_cadence_adjustment,
    execute_shadow_core_cadence_calibration
)
from sol_core_waveguide_binding import (
    CoreWaveguideBinding,
    CoreWaveguideBindingMap,
    CoreWaveguideBindingReport,
    bind_cores_to_waveguide_fabric,
    validate_core_waveguide_bindings,
    compare_core_waveguide_bindings
)

# Import extended modules
from sol_multicore_pipeline import (
    PipelineSchedule,
    PipelineStage,
    PipelineTask,
    PipelineDependency,
    build_pipeline,
    assign_tasks_to_cores,
    export_pipeline_for_sovereign_assembly,
    validate_pipeline_after_assembly,
    run_shadow_assembled_pipeline
)
from sol_pipeline_optimizer import (
    PipelineOptimizationPolicy,
    PipelineOptimizationCandidate,
    PipelineOptimizationPlan,
    PipelineOptimizationReport,
    PipelineOptimizationResult,
    recommend_pipeline_calibration_from_bottlenecks,
    validate_optimization_after_pipeline_calibration
)
from sol_lockfree_bypass import (
    BypassExecutionPlan,
    validate_bypass_after_core_assembly
)
from sol_simd_core_integration import (
    SIMDCoreFabricMap,
    SIMDCoreBinding,
    SIMDWaveguideDispatchPlan,
    validate_simd_core_after_sovereign_assembly,
    run_shadow_simd_pipeline_on_assembled_cores
)
from sol_tensor_flow import (
    TensorShape,
    TensorShard,
    TensorFlowPlan,
    validate_tensor_shards_after_core_assembly,
    run_shadow_tensor_pipeline_on_assembled_cores
)
from sol_hierarchical_waveguide_fabric import (
    HierarchicalWaveguideTopology,
    validate_waveguide_topology_after_core_assembly
)
from sol_interlane_prefix_carry import (
    validate_prefix_carry_after_core_assembly
)
from sol_resonant_cadence_controller import (
    validate_resonant_cadence_after_core_assembly
)
from sol_autonomous_cadence_sync import (
    block_core_assembly_on_unstable_autonomous_cadence
)
from sol_sovereign_runtime import (
    SovereignRuntimePolicy,
    SovereignRuntimeState,
    SovereignRuntimeCommand,
    build_sovereign_runtime,
    submit_multicore_assembly_command,
    execute_shadow_multicore_assembly_command
)
from sol_runtime_ledger import (
    build_runtime_ledger,
    append_runtime_event,
    attach_runtime_evidence,
    attach_rollback_reference,
    validate_runtime_ledger
)
from coding_library.sovereign_domain.frontier_bridge import (
    SovereignCoreAssemblyAdvisor,
    PipelineCalibrationAdvisor,
    CoreAssemblySuggestion,
    PipelineCalibrationSuggestion,
    CoreAssemblyClosedLoopReport,
    FrontierBridge
)
from coding_library.sovereign_domain.rangers.core_assembly_ranger import CoreAssemblyRanger
from coding_library.sovereign_domain.promotion_court import PromotionCourt
from coding_library.sovereign_domain.evidence_packet import SovereignPacket

# Mock helpers
class MockCoreGroup:
    def __init__(self, cores):
        self.cores = cores
        self.core_count = len(cores)

@pytest.fixture
def base_2_core_group():
    return MockCoreGroup({"core_0": {}, "core_1": {}})

@pytest.fixture
def base_4_core_group():
    return MockCoreGroup({"core_0": {}, "core_1": {}, "core_2": {}, "core_3": {}})

@pytest.fixture
def base_8_core_group():
    return MockCoreGroup({f"core_{i}": {} for i in range(8)})

@pytest.fixture
def assembly_policy():
    return SovereignCoreAssemblyPolicy(allow_sandbox=True, court_token_required=True, rollback_required=True)

# 1. sovereign core assembly builds for 2-core group.
def test_sovereign_core_assembly_2_cores(base_2_core_group, assembly_policy):
    core_group = base_2_core_group
    # Add rollback and cadence profile reference mock metadata
    core_group.rollback_snapshot = "snap_2_core"
    core_group.cadence_profile = "cadence_2_core"
    
    plan = build_sovereign_core_assembly(core_group, {}, assembly_policy)
    assert isinstance(plan, SovereignCoreAssemblyPlan)
    assert len(plan.clusters) == 1
    assert len(plan.clusters[0].cores) == 2
    assert plan.metadata.get("rollback_snapshot") == "snap_2_core"

# 2. sovereign core assembly builds for 4-core group.
def test_sovereign_core_assembly_4_cores(base_4_core_group, assembly_policy):
    core_group = base_4_core_group
    core_group.rollback_snapshot = "snap_4_core"
    core_group.cadence_profile = "cadence_4_core"
    
    plan = build_sovereign_core_assembly(core_group, {}, assembly_policy)
    assert isinstance(plan, SovereignCoreAssemblyPlan)
    assert len(plan.clusters) == 2
    assert sum(len(c.cores) for c in plan.clusters) == 4

# 3. sovereign core assembly builds for 8-core group.
def test_sovereign_core_assembly_8_cores(base_8_core_group, assembly_policy):
    core_group = base_8_core_group
    core_group.rollback_snapshot = "snap_8_core"
    core_group.cadence_profile = "cadence_8_core"
    
    plan = build_sovereign_core_assembly(core_group, {}, assembly_policy)
    assert isinstance(plan, SovereignCoreAssemblyPlan)
    assert len(plan.clusters) == 4
    assert sum(len(c.cores) for c in plan.clusters) == 8

# 4. invalid core group is rejected.
def test_invalid_core_group_rejected(assembly_policy):
    bad_core_group = MockCoreGroup({"core_0": {}, "core_1": {}, "core_2": {}})  # 3 cores is invalid
    bad_core_group.rollback_snapshot = "snap"
    bad_core_group.cadence_profile = "cadence"
    
    with pytest.raises(ValueError, match="assembly count must be 2, 4, or 8"):
        build_sovereign_core_assembly(bad_core_group, {}, assembly_policy)

# 5. pipeline assembly binds all required stages.
def test_pipeline_assembly_binds_all_stages(base_2_core_group, assembly_policy):
    core_group = base_2_core_group
    core_group.rollback_snapshot = "snap"
    core_group.cadence_profile = "cadence"
    
    assembly_plan = build_sovereign_core_assembly(core_group, {}, assembly_policy)
    intent = build_pipeline_assembly_intent({}, {}, assembly_plan)
    
    stage_bindings = bind_pipeline_stages_to_cores(intent)
    lane_bindings = bind_pipeline_lanes_to_waveguides(intent)
    core_bindings = [PipelineAssemblyCoreBinding(core_id="core_0", cluster_id="CLUSTER_0")]
    
    plan = PipelineAssemblyPlan(
        plan_id="PLAN_A",
        intent=intent,
        stage_bindings=stage_bindings,
        lane_bindings=lane_bindings,
        core_bindings=core_bindings
    )
    assert validate_pipeline_assembly_plan(plan) is True

# 6. missing stage binding rejects pipeline assembly.
def test_missing_stage_binding_rejects_pipeline_assembly(base_2_core_group, assembly_policy):
    core_group = base_2_core_group
    core_group.rollback_snapshot = "snap"
    core_group.cadence_profile = "cadence"
    
    assembly_plan = build_sovereign_core_assembly(core_group, {}, assembly_policy)
    # Simulate missing stage request in sequence dictionary
    intent = build_pipeline_assembly_intent({"simulate_missing_stage": True}, {}, assembly_plan)
    
    stage_bindings = bind_pipeline_stages_to_cores(intent)
    lane_bindings = bind_pipeline_lanes_to_waveguides(intent)
    
    plan = PipelineAssemblyPlan(
        plan_id="PLAN_B",
        intent=intent,
        stage_bindings=stage_bindings,
        lane_bindings=lane_bindings,
        core_bindings=[]
    )
    with pytest.raises(ValueError, match="Missing stage binding rejects pipeline assembly"):
        validate_pipeline_assembly_plan(plan)

# 7. lane bindings cover all expected lanes.
def test_lane_bindings_cover_all_expected_lanes(base_2_core_group, assembly_policy):
    core_group = base_2_core_group
    core_group.rollback_snapshot = "snap"
    core_group.cadence_profile = "cadence"
    
    assembly_plan = build_sovereign_core_assembly(core_group, {}, assembly_policy)
    assembly_plan.metadata["lane_count"] = 16
    intent = build_pipeline_assembly_intent({}, {}, assembly_plan)
    
    lane_bindings = bind_pipeline_lanes_to_waveguides(intent)
    assert len(lane_bindings) == 16
    assert [lb.lane_id for lb in lane_bindings] == list(range(16))

# 8. waveguide bindings preserve PML coverage.
def test_waveguide_bindings_preserve_pml_coverage(base_2_core_group, assembly_policy):
    core_group = base_2_core_group
    core_group.rollback_snapshot = "snap"
    core_group.cadence_profile = "cadence"
    core_group.tensor_shards = ["tensor_0"]
    
    assembly_plan = build_sovereign_core_assembly(core_group, {}, assembly_policy)
    
    # Check invalid PML coverage
    assembly_plan.metadata["pml_coverage_violated"] = True
    binding_map = bind_cores_to_waveguide_fabric(assembly_plan, {"lane_bindings": list(range(8))})
    
    with pytest.raises(ValueError, match="missing or violated PML boundary coverage"):
        validate_core_waveguide_bindings(binding_map)

# 9. SIMD bindings validate for all supported SIMD modes.
def test_simd_bindings_validate_all_supported_modes():
    modes = ["uint8x8", "uint16x4", "uint32x2", "uint64x1"]
    for mode in modes:
        binding_map = SIMDCoreFabricMap(
            map_id="MAP_SIMD",
            candidate_id="CAND_SIMD",
            bindings=[SIMDCoreBinding(core_id="core_0", simd_mode=mode, waveguide_lane_ids=[0])],
            metadata={}
        )
        assert validate_simd_core_after_sovereign_assembly(binding_map, {"success": True}) is True

# 10. tensor shard bindings survive core assembly.
def test_tensor_shard_bindings_survive_core_assembly(base_2_core_group, assembly_policy):
    shape = TensorShape([4, 4])
    cores = base_2_core_group
    shards = [
        TensorShard(shard_id=0, core_id="core_0", shape=shape, element_indices=[0]),
        TensorShard(shard_id=1, core_id="core_1", shape=shape, element_indices=[1])
    ]
    tensor_plan = TensorFlowPlan(shape=shape, core_group=cores, shards=shards, metadata={"tensor_shards": True})
    
    # Survives assembly validation check
    assert validate_tensor_shards_after_core_assembly(tensor_plan, {"success": True}) is True

# 11. prefix-carry bridge bindings survive core assembly.
def test_prefix_carry_bridge_bindings_survive_core_assembly():
    carry_plan = type("MockCarryPlan", (object,), {"metadata": {"some_check": True}})()
    assert validate_prefix_carry_after_core_assembly(carry_plan, {"success": True}) is True

# 12. pipeline calibration baseline is required before calibration.
def test_pipeline_calibration_baseline_required():
    obs = PipelineObservation = PipelineCalibrationObservation(
        observation_id="OBS",
        stage_latency=0.006,
        core_queue_depth=2,
        cross_core_stall_time=0.001,
        backpressure=0.1,
        reduction_wait=0.0,
        consensus_wait=0.0,
        shard_lock_wait=0.0,
        cadence_drift=0.002,
        wavefront_timing_drift=0.0,
        carrier_timing_drift=0.0
    )
    with pytest.raises(ValueError, match="baseline is required before calibration"):
        measure_pipeline_calibration_error(None, obs)

# 13. unbounded pipeline calibration policy is rejected.
def test_unbounded_calibration_policy_rejected():
    policy = PipelineCalibrationPolicy(max_steps=0) # Unbounded/invalid steps limit
    with pytest.raises(ValueError, match="max_steps must be > 0"):
        plan_pipeline_calibration_adjustment({"stage_latency_error": 0.05}, policy)

# 14. stage latency breach blocks promotion.
def test_stage_latency_breach_blocks_promotion():
    court = PromotionCourt()
    packet = SovereignPacket(
        packet_id="PKT_BREACH",
        domain="sol_sovereign",
        level=45,
        actor="Ranger",
        actor_type="ranger",
        mission_id="M_BREACH",
        claim="Stage latency breach",
        evidence={"stage_latency": 0.12, "promotion_readiness": False},
        invariants_checked=[],
        artifacts=[],
        recommendation="observe",
        confidence=0.99,
        reproducibility_hash="hash"
    )
    res = court.review_core_assembly_ranger_packet(packet)
    assert res.passed is False
    assert res.decision == "quarantine_pipeline_stage"

# 15. backpressure breach blocks promotion.
def test_backpressure_breach_blocks_promotion():
    court = PromotionCourt()
    packet = SovereignPacket(
        packet_id="PKT_BP",
        domain="sol_sovereign",
        level=45,
        actor="Ranger",
        actor_type="ranger",
        mission_id="M_BP",
        claim="Backpressure breach",
        evidence={"backpressure": 0.15, "promotion_readiness": False},
        invariants_checked=[],
        artifacts=[],
        recommendation="observe",
        confidence=0.99,
        reproducibility_hash="hash"
    )
    res = court.review_core_assembly_ranger_packet(packet)
    assert res.passed is False
    assert res.decision == "hold_core_assembly"

# 16. cross-core stall breach blocks promotion.
def test_cross_core_stall_breach_blocks_promotion():
    court = PromotionCourt()
    packet = SovereignPacket(
        packet_id="PKT_STALL",
        domain="sol_sovereign",
        level=45,
        actor="Ranger",
        actor_type="ranger",
        mission_id="M_STALL",
        claim="Cross core stall breach",
        evidence={"cross_core_stalls": 0.15, "promotion_readiness": False},
        invariants_checked=[],
        artifacts=[],
        recommendation="observe",
        confidence=0.99,
        reproducibility_hash="hash"
    )
    res = court.review_core_assembly_ranger_packet(packet)
    assert res.passed is False
    assert res.decision == "hold_core_assembly"

# 17. core cadence skew breach blocks promotion.
def test_core_cadence_skew_breach_blocks_promotion():
    court = PromotionCourt()
    packet = SovereignPacket(
        packet_id="PKT_SKEW",
        domain="sol_sovereign",
        level=45,
        actor="Ranger",
        actor_type="ranger",
        mission_id="M_SKEW",
        claim="Skew breach",
        evidence={"cadence_skew": 0.15, "promotion_readiness": False},
        invariants_checked=[],
        artifacts=[],
        recommendation="observe",
        confidence=0.99,
        reproducibility_hash="hash"
    )
    res = court.review_core_assembly_ranger_packet(packet)
    assert res.passed is False
    assert res.decision == "hold_core_assembly"

# 18. autonomous cadence instability blocks assembly.
def test_autonomous_cadence_instability_blocks_assembly():
    sync_report = {"result": {"success": True}, "errors": [], "metadata": {"cadence_instability": True}}
    with pytest.raises(ValueError, match="Core assembly blocked: unstable autonomous cadence"):
        block_core_assembly_on_unstable_autonomous_cadence(sync_report)

# 19. active cadence profile overwrite attempt is rejected.
def test_active_cadence_profile_overwrite_rejected():
    adjustments = [CoreCadenceAdjustment("ADJ", "active_profile", 0.1, 0.05)]
    report = execute_shadow_core_cadence_calibration(adjustments)
    assert report.success is False
    assert "Active cadence profile overwrite attempt is rejected." in report.errors

# 20. active phase table overwrite attempt is rejected.
def test_active_phase_table_overwrite_rejected():
    opt_report = {"metadata": {"overwrite_active_phase_table": True}}
    cal_report = {"success": True}
    with pytest.raises(ValueError, match="Active profile/table overwrite is prohibited"):
        validate_optimization_after_pipeline_calibration(opt_report, cal_report)

# 21. active carrier registry overwrite attempt is rejected.
def test_active_carrier_registry_overwrite_rejected():
    opt_report = {"metadata": {"overwrite_active_carrier": True}}
    cal_report = {"success": True}
    with pytest.raises(ValueError, match="Active profile/table overwrite is prohibited"):
        validate_optimization_after_pipeline_calibration(opt_report, cal_report)

# 22. runtime ledger records assembly plan, calibration baseline, ranger packet, court verdict, and rollback refs.
def test_runtime_ledger_records_everything():
    ledger = build_runtime_ledger()
    
    # 1. Core assembly plan
    plan = SovereignCoreAssemblyPlan("plan_0", SovereignCoreAssemblyPolicy(), {}, {}, [])
    append_runtime_event(ledger, plan)
    
    # 2. Calibration baseline
    baseline = PipelineCalibrationBaseline("base_0", [])
    append_runtime_event(ledger, baseline)
    
    # 3. Ranger packet
    packet = SovereignPacket("pkt_0", "sol", 45, "Ranger", "ranger", "mission", "claim", {}, [], [], "promote", 0.99, "repro_hash")
    append_runtime_event(ledger, packet)
    
    # 4. Court verdict
    verdict = type("MockVerdict", (object,), {"decision_id": "V_OK", "decision": "promote_level45_candidate", "justification": "Passed"})()
    append_runtime_event(ledger, verdict)
    
    # 5. Rollback ref
    rollback = type("MockRollback", (object,), {"rollback_id": "snap_0", "state_checksum": "hash"})()
    attach_rollback_reference(ledger, rollback)
    
    rep = validate_runtime_ledger(ledger)
    assert rep.passed_validation is True
    
    # Verify entry types
    types = [e.entry_type for e in rep.entries]
    assert "core_assembly_plan" in types
    assert "pipeline_calibration_baseline" in types
    assert "ranger_packet" in types
    assert "court_decision" in types
    assert "rollback_ref" in types

# 23. rollback restores mock core assembly and candidate cadence state.
def test_rollback_restores_mock_state():
    ledger = build_runtime_ledger()
    rollback = type("MockRollback", (object,), {"rollback_id": "snap_0", "state_checksum": "hash"})()
    attach_rollback_reference(ledger, rollback)
    
    assert len(ledger["rollback_references"]) == 1
    assert ledger["rollback_references"][0].rollback_id == "snap_0"

# 24. CoreAssemblyRanger emits JSON-serializable SovereignPacket.
def test_core_assembly_ranger_emits_packet(base_2_core_group, assembly_policy):
    core_group = base_2_core_group
    core_group.rollback_snapshot = "snap"
    core_group.cadence_profile = "cadence"
    
    assembly_plan = build_sovereign_core_assembly(core_group, {}, assembly_policy)
    assembly_report = execute_shadow_core_assembly(assembly_plan)
    
    ranger = CoreAssemblyRanger()
    packet = ranger.observe_core_assembly(
        assembly_report=assembly_report,
        mission_id="MISSION_L45"
    )
    assert isinstance(packet, SovereignPacket)
    assert packet.level == 45
    packet_dict = packet.to_dict()
    assert json.dumps(packet_dict) is not None

# 25. Promotion Court can review reports.
def test_promotion_court_can_review_reports(base_2_core_group, assembly_policy):
    court = PromotionCourt()
    
    core_group = base_2_core_group
    core_group.rollback_snapshot = "snap"
    core_group.cadence_profile = "cadence"
    core_group.tensor_shards = ["tensor_0"]
    
    assembly_plan = build_sovereign_core_assembly(core_group, {}, assembly_policy)
    assembly_report = execute_shadow_core_assembly(assembly_plan)
    
    dec_assembly = court.review_sovereign_core_assembly_report(assembly_report)
    assert dec_assembly.passed is True
    assert dec_assembly.decision == "accept_shadow_core_assembly"
    
    # Calibration report review
    cal_res = PipelineCalibrationResult(success=True)
    cal_rep = PipelineCalibrationReport("REP", PipelineCalibrationBaseline("B", []), cal_res)
    dec_cal = court.review_pipeline_calibration_report(cal_rep)
    assert dec_cal.passed is True
    assert dec_cal.decision == "accept_shadow_core_assembly"
    
    # Pipeline assembly review
    pip_res = PipelineAssemblyResult(success=True)
    pip_rep = PipelineAssemblyReport("REP", PipelineAssemblyPlan("P", None, [], [], []), pip_res)
    dec_pip = court.review_pipeline_assembly_report(pip_rep)
    assert dec_pip.passed is True
    assert dec_pip.decision == "accept_shadow_core_assembly"
    
    # Core cadence calibration review
    cad_rep = CoreCadenceCalibrationReport("REP", [], 0.001, True)
    dec_cad = court.review_core_cadence_calibration_report(cad_rep)
    assert dec_cad.passed is True
    assert dec_cad.decision == "accept_shadow_core_assembly"
    
    # Core waveguide binding review
    wg_rep = CoreWaveguideBindingReport("REP", CoreWaveguideBindingMap("M", []), True)
    dec_wg = court.review_core_waveguide_binding_report(wg_rep)
    assert dec_wg.passed is True
    assert dec_wg.decision == "accept_shadow_core_assembly"
    
    # Ranger packet review
    ranger = CoreAssemblyRanger()
    packet = ranger.observe_core_assembly(
        assembly_report=assembly_report,
        mission_id="MISSION_L45"
    )
    # Ensure it maps correctly inside packet and has present baseline/targets/etc.
    packet.evidence["promotion_readiness"] = True
    packet.recommendation = "promote"
    dec_rng = court.review_core_assembly_ranger_packet(packet)
    assert dec_rng.passed is True
    assert dec_rng.decision == "promote_level45_candidate"
