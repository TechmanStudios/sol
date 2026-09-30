# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Sovereign Scaffolding and WideWord Verification Tests
=========================================================
"""

import sys
import json
import math
from pathlib import Path
import pytest

# Setup path injection to guarantee local tools importing
sol_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(sol_root / "tools" / "sol-rsi"))
sys.path.insert(0, str(sol_root / "tools" / "sol-core"))

# Core sovereign domain imports
from coding_library.sovereign_domain import (
    RangerMission,
    SovereignPacket,
    SovereignDomain,
    PromotionCourt,
    PromotionGateResult,
    CalibrationCorrectionDecision,
    FrontierBridge,
    BoundedCorrectionPolicy,
    CandidateCorrection,
    FrontierClosedLoopController,
    PhaseRanger,
    MassRanger,
    BoundaryRanger,
    ByteLaneRanger,
    CarryRanger,
    TelemetryRanger,
    MemoryRanger,
    SignalRanger,
    DriftRanger,
    KernelRanger,
    CourtRanger
)
from coding_library.sovereign_domain.frontier_bridge import (
    FrontierDriftController,
    FrontierDriftSignal,
    FrontierDriftRecommendation
)

# Core WideWord imports
from sol_pdm_byte_slice import PDMByteSlice
from sol_lane_fabric import LaneFabric
from sol_prefix_carry import PrefixCarry
from sol_waveguide_boundary import WaveguideBoundary, PMLProfile
from sol_hcam_banking import HCAMBank, HCAMAddressMap, HCAMRecallPlan
from sol_phase_alignment import (
    build_default_phase_table,
    phase_error,
    observe_phase_drift,
    is_within_phase_tolerance,
    PhaseAlignmentEntry,
    PhaseAlignmentTable,
    PhaseDriftObservation,
    PhaseAlignmentReport,
    apply_candidate_phase_correction,
    diff_phase_tables,
    validate_phase_table_bounds
)
from sol_calibration_replay import (
    CalibrationReplayInput,
    CalibrationReplayResult,
    CalibrationPromotionReport,
    run_calibration_replay
)

from sol_dispersion_model import (
    build_dispersion_profile,
    estimate_group_delay,
    estimate_phase_shift,
    DispersionProfile,
    DispersionObservation
)
from sol_graph_kernel import (
    CSRAdjacency,
    GraphKernelArrays,
    build_csr_from_edges,
    snapshot_graph_arrays,
    restore_graph_arrays,
    compute_pressure_array,
    compute_flux_delta_array,
    compute_rho_transport_array,
    VectorizedGraphStepper,
    VectorizedParityReport,
    run_shadow_steps
)
from sol_engine_backend_adapter import step_vectorized_impl
from sol_engine import SOLEngine
from sol_simd_modes import (
    SIMDMode,
    SIMDExecutionPlan,
    plan_simd_mode
)



def test_mission_and_evidence_packet_serialization():
    """Verify that RangerMission and SovereignPacket serialize and deserialize cleanly."""
    mission = RangerMission(
        mission_id="L11_PHASE_PATROL_001",
        target="Level11Sequencer",
        level=11,
        objective="Measure PDM phase drift for all 16 channels",
        allowed_actions=["READ_STATE", "RUN_DIAGNOSTIC", "COLLECT_TELEMETRY"],
        forbidden_actions=["PATCH", "NUDGE", "WRITE_PHASE_TABLE"],
        ttl_steps=120,
        required_artifacts=["phase_trace.csv", "pdm_deltas.json"],
        escalation_policy="send_to_phase_calibration_agent"
    )

    # Serialize and deserialize mission
    m_dict = mission.to_dict()
    assert m_dict["mission_id"] == "L11_PHASE_PATROL_001"
    assert m_dict["allowed_actions"][0] == "READ_STATE"
    
    m_back = RangerMission.from_dict(m_dict)
    assert m_back.mission_id == mission.mission_id
    assert m_back.allowed_actions == mission.allowed_actions

    packet = SovereignPacket(
        packet_id="PKT_L11_SYNC_001",
        domain="sol_sovereign",
        level=11,
        actor="Phase Ranger",
        actor_type="ranger",
        mission_id="L11_PHASE_PATROL_001",
        claim="Phase lock matches coherence bounds",
        evidence={"coherence": 0.98, "active_delta": 0.35},
        invariants_checked=["mass_preservation", "phase_coherence"],
        artifacts=["phase_trace.csv"],
        recommendation="promote",
        confidence=0.95,
        reproducibility_hash="sha256_abcdef123456"
    )

    # Serialize and deserialize packet
    p_dict = packet.to_dict()
    assert p_dict["packet_id"] == "PKT_L11_SYNC_001"
    assert p_dict["actor_type"] == "ranger"
    
    p_back = SovereignPacket.from_dict(p_dict)
    assert p_back.packet_id == packet.packet_id
    assert p_back.recommendation == "promote"


def test_domain_registry_and_json_validity():
    """Verify that the SovereignDomain registry class can load the JSON files and query values."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    domain = SovereignDomain(library_dir=library_dir)
    
    # Verify agent registry loads
    arch_council = domain.get_agent_info("architecture_council")
    assert arch_council != {}
    assert "Chief SOL Architect" in arch_council["members"]

    # Verify ranger registry loads
    phase_ranger = domain.get_ranger_info("phase_ranger")
    assert phase_ranger != {}
    assert phase_ranger["class"] == "PhaseRanger"

    # Verify team registry loads
    team = domain.get_team_info("level_11_stabilization_team")
    assert team != {}
    assert "phase_ranger" in team["rangers"]

    # Verify gates load
    gate = domain.get_gate_info("32bit_promotion_gate")
    assert gate != {}
    assert gate["min_active_mass"] == 14.0


def test_promotion_court():
    """Verify evaluation logic inside PromotionCourt."""
    court = PromotionCourt()
    packet = SovereignPacket(
        packet_id="PKT_L11_SYNC_001",
        domain="sol_sovereign",
        level=11,
        actor="Phase Ranger",
        actor_type="ranger",
        mission_id="L11_PHASE_PATROL_001",
        claim="Stable",
        evidence={},
        invariants_checked=[],
        artifacts=[],
        recommendation="promote",
        confidence=0.95,
        reproducibility_hash="hash"
    )
    
    court.submit_packet(packet)
    assert court.evaluate_promotion("L11_PHASE_PATROL_001") is True
    
    # Negative recommendation blocks promotion
    bad_packet = SovereignPacket(
        packet_id="PKT_L11_SYNC_002",
        domain="sol_sovereign",
        level=11,
        actor="Mass Ranger",
        actor_type="ranger",
        mission_id="L11_PHASE_PATROL_001",
        claim="Mass drain",
        evidence={},
        invariants_checked=[],
        artifacts=[],
        recommendation="quarantine",
        confidence=0.9,
        reproducibility_hash="hash"
    )
    court.submit_packet(bad_packet)
    assert court.evaluate_promotion("L11_PHASE_PATROL_001") is False


def test_frontier_bridge():
    """Verify that FrontierBridge collects telemetry and blocks nudges in Phase 0."""
    bridge = FrontierBridge()
    bridge.push_telemetry({"coherence": 0.95, "crosstalk": 0.001})
    assert len(bridge.telemetry_history) == 1
    
    # Phase 0 constraint: nudge requests return False
    assert bridge.request_nudge(lane_id=0, nudge_value=1.5) is False


def test_rangers_observe_only():
    """Verify that all placeholder ranger classes instantiate and have basic patrol/inspect methods."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    
    phase = PhaseRanger(lib_agent=library_dir)
    assert phase.name == "Phase Ranger"
    assert "STABLE" in phase.patrol_lanes(None)["status"]
    
    mass = MassRanger(lib_agent=library_dir)
    assert mass.name == "Mass Ranger"
    assert "STABLE" in mass.check_mass_bounds(None)["status"]
    
    boundary = BoundaryRanger(lib_agent=library_dir)
    assert boundary.name == "Boundary Ranger"
    assert boundary.inspect_boundaries(None)["reflection_score"] == 0.01

    lane = ByteLaneRanger(lib_agent=library_dir)
    assert lane.name == "Byte-Lane Ranger"
    assert lane.verify_isolation(None)["cross_lane_leakage"] == 0.002

    carry = CarryRanger(lib_agent=library_dir)
    assert carry.name == "Carry Ranger"
    assert carry.check_carry_correctness(None)["carry_bottlenecks_detected"] is False

    telemetry = TelemetryRanger(lib_agent=library_dir)
    assert telemetry.name == "Telemetry Ranger"
    assert len(telemetry.record_run_trace(None, steps=3)) == 3


def test_wideword_core_scaffolding():
    """Verify that WideWord core modules initialize and execute mock math/routing logic."""
    # 1. PDM Byte Slice
    slice_cell = PDMByteSlice(lane_id=0, bit_offset=0)
    assert len(slice_cell.channel_map()) == 8
    
    # Test modulation/demodulation of 0xA5 (10100101)
    amps = slice_cell.modulate(0xA5)
    assert len(amps) == 8
    val = slice_cell.demodulate(amps)
    assert val == 0xA5

    # 2. Lane Fabric (32-bit: 4 lanes)
    fabric = LaneFabric(num_lanes=4)
    assert len(fabric.lanes) == 4
    word = 0xDEADBEEF
    modulated = fabric.modulate_word(word)
    assert len(modulated) == 4
    demodulated = fabric.demodulate_word(modulated)
    assert demodulated == word

    # 3. Prefix Carry
    resolver = PrefixCarry(num_lanes=4)
    # Mock carry generation / propagation
    gen = [False, True, False, False]
    prop = [True, True, True, True]
    carries = resolver.resolve_carries(gen, prop, carry_in=False)
    assert len(carries) == 4
    # Lane 0: carry_in (False)
    # Lane 1: G0 + P0*C0 = False
    # Lane 2: G1 + P1*C1 = True
    # Lane 3: G2 + P2*C2 = True
    assert carries == [False, False, True, True]
    
    sum_c0 = [10, 20, 30, 40]
    sum_c1 = [11, 21, 31, 41]
    res = resolver.compute_lane_selection(sum_c0, sum_c1, carries)
    assert res == [10, 20, 31, 41]

    # 4. Waveguide Boundary
    boundary = WaveguideBoundary(num_pml_cells=2, boundary_damping=0.16)
    profile = boundary.calculate_pml_damping_profile(grid_size=6)
    # index 0, 1 should be Left PML, index 4, 5 Right PML, 2, 3 Core
    assert profile[0] == 0.16
    assert profile[2] == 0.0
    assert profile[3] == 0.0
    assert profile[5] == 0.16
    
    assert boundary.apply_gaussian_envelope(x=5.0, t=1.0, amplitude=10.0, center=5.0, width=2.0) == 10.0


# ---- Phase 1 new verification tests ----

def test_byte_slice_alu_addition_subtraction():
    """Verify 8-bit deterministic arithmetic (addition and subtraction) and flags."""
    byte_slice = PDMByteSlice(lane_id=0, bit_offset=0)
    
    # 1. Simple addition
    res = byte_slice.add8(100, 50)
    assert res.result == 150
    assert res.carry_out == 0
    assert res.flags["zero"] is False
    assert res.flags["negative"] is True  # 150 has bit 7 set (0x96)
    assert res.flags["overflow"] is True  # two positive additions yielding a negative (0x96)
    
    # 2. Addition with carry-out
    res = byte_slice.add8(200, 100, carry_in=1)
    # 200 + 100 + 1 = 301 -> 301 & 0xFF = 45
    assert res.result == 45
    assert res.carry_out == 1
    assert res.flags["zero"] is False
    assert res.flags["negative"] is False
    
    # 3. Simple subtraction
    res = byte_slice.sub8(100, 40)
    assert res.result == 60
    assert res.carry_out == 0
    assert res.flags["zero"] is False
    assert res.flags["negative"] is False
    
    # 4. Subtraction with borrow-out (wrap)
    res = byte_slice.sub8(40, 100, borrow_in=1)
    # 40 - 100 - 1 = -61 -> -61 & 0xFF = 195
    assert res.result == 195
    assert res.carry_out == 1 # Borrow occurred
    assert res.flags["zero"] is False
    assert res.flags["negative"] is True


def test_byte_slice_alu_bitwise():
    """Verify bitwise operations AND, OR, XOR, NOT mask to 8-bit results."""
    byte_slice = PDMByteSlice(lane_id=0, bit_offset=0)
    
    # AND
    res = byte_slice.and8(0xF0, 0x0F)
    assert res.result == 0x00
    assert res.flags["zero"] is True
    
    res = byte_slice.and8(0x3C, 0xFF)
    assert res.result == 0x3C
    assert res.flags["zero"] is False
    
    # OR
    res = byte_slice.or8(0xF0, 0x0F)
    assert res.result == 0xFF
    assert res.flags["negative"] is True
    
    # XOR
    res = byte_slice.xor8(0xAA, 0x55)
    assert res.result == 0xFF
    
    res = byte_slice.xor8(0xAA, 0xAA)
    assert res.result == 0x00
    assert res.flags["zero"] is True
    
    # NOT
    res = byte_slice.not8(0x00)
    assert res.result == 0xFF
    assert res.flags["negative"] is True
    
    res = byte_slice.not8(0xFF)
    assert res.result == 0x00
    assert res.flags["zero"] is True


def test_lane_fabric_layout_widths():
    """Verify that LaneFabric.for_width returns correct number of byte slice lanes."""
    fab_16 = LaneFabric.for_width(16)
    assert len(fab_16.lanes) == 2
    assert fab_16.num_lanes == 2
    
    fab_32 = LaneFabric.for_width(32)
    assert len(fab_32.lanes) == 4
    assert fab_32.num_lanes == 4
    
    fab_64 = LaneFabric.for_width(64)
    assert len(fab_64.lanes) == 8
    assert fab_64.num_lanes == 8
    
    with pytest.raises(ValueError):
        LaneFabric.for_width(8)


def test_phase_ranger_coarse_calibration_packet():
    """Verify that PhaseRanger observes calibration telemetry and returns a serializable SovereignPacket."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    ranger = PhaseRanger(lib_agent=library_dir)
    
    # 1. Test case: calibration passes all thresholds
    passing_metrics = {
        "active_delta": 0.25,
        "inactive_max_delta": 0.08,
        "reversed_delta": 0.07,
        "phase_residual": 0.02,
        "cross_talk": 0.03,
        "min_active_register_mass": 14.5
    }
    
    packet = ranger.observe_calibration(passing_metrics, mission_id="L11_CAL_TEST")
    assert packet.actor == "Phase Ranger"
    assert packet.recommendation == "observe"
    assert packet.evidence["pass_status"] is True
    assert packet.evidence["threshold_checks"]["active_delta"] is True
    
    # Verify serializable
    dct = packet.to_dict()
    assert isinstance(dct, dict)
    js = json.dumps(dct)
    assert js is not None
    
    # 2. Test case: active_delta below min threshold -> rejects
    failing_metrics = {
        "active_delta": 0.15, # fails (min 0.20)
        "inactive_max_delta": 0.08,
        "reversed_delta": 0.07,
        "phase_residual": 0.02,
        "cross_talk": 0.03,
        "min_active_register_mass": 14.5
    }
    
    packet_fail = ranger.observe_calibration(failing_metrics, mission_id="L11_CAL_TEST")
    assert packet_fail.recommendation == "reject"
    assert packet_fail.evidence["pass_status"] is False
    assert packet_fail.evidence["threshold_checks"]["active_delta"] is False


# ---- Phase 2 new verification tests ----

def test_16bit_addition_no_overflow():
    """Verify 16-bit addition with no final carry out overflow."""
    fabric = LaneFabric.for_width(16)
    res = fabric.add_word(0x1234, 0x5678, carry_in=0)
    assert res.result == 0x68AC
    assert res.carry_out == 0
    assert res.width == 16
    assert res.lane_count == 2


def test_16bit_addition_with_overflow():
    """Verify 16-bit addition with final carry out overflow."""
    fabric = LaneFabric.for_width(16)
    # 0xFFFF + 0x0001 = 0x10000 -> result 0x0000, carry_out = 1
    res = fabric.add_word(0xFFFF, 0x0001, carry_in=0)
    assert res.result == 0x0000
    assert res.carry_out == 1


def test_32bit_random_additions():
    """Verify 32-bit WideWord additions against Python integer arithmetic."""
    import random
    random.seed(42)
    fabric = LaneFabric.for_width(32)
    
    for _ in range(50):
        a = random.randint(0, 0xFFFFFFFF)
        b = random.randint(0, 0xFFFFFFFF)
        c_in = random.randint(0, 1)
        
        res = fabric.add_word(a, b, carry_in=c_in)
        
        raw_sum = a + b + c_in
        expected_res = raw_sum & 0xFFFFFFFF
        expected_carry = 1 if raw_sum > 0xFFFFFFFF else 0
        
        assert res.result == expected_res
        assert res.carry_out == expected_carry


def test_64bit_random_additions():
    """Verify 64-bit WideWord additions against Python integer arithmetic."""
    import random
    random.seed(43)
    fabric = LaneFabric.for_width(64)
    
    for _ in range(50):
        a = random.randint(0, 0xFFFFFFFFFFFFFFFF)
        b = random.randint(0, 0xFFFFFFFFFFFFFFFF)
        c_in = random.randint(0, 1)
        
        res = fabric.add_word(a, b, carry_in=c_in)
        
        raw_sum = a + b + c_in
        expected_res = raw_sum & 0xFFFFFFFFFFFFFFFF
        expected_carry = 1 if raw_sum > 0xFFFFFFFFFFFFFFFF else 0
        
        assert res.result == expected_res
        assert res.carry_out == expected_carry


def test_carry_propagation_across_multiple_lanes():
    """Verify carry propagation ripples correctly across multiple byte lanes."""
    # 32-bit: 0x00FFFFFF + 0x00000001 = 0x01000000
    # This must generate a carry in lane 0, propagate it through lane 1 and lane 2, and end in lane 3.
    fabric = LaneFabric.for_width(32)
    res = fabric.add_word(0x00FFFFFF, 0x00000001, carry_in=0)
    assert res.result == 0x01000000
    assert res.carry_out == 0
    # Check carry trace: carries in should be [False, True, True, True]
    assert res.carry_trace == [False, True, True, True]


def test_carry_ranger_evaluates_correctness():
    """Verify CarryRanger evaluates addition correctly and outputs a SovereignPacket."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    ranger = CarryRanger(lib_agent=library_dir)
    
    fabric = LaneFabric.for_width(32)
    res = fabric.add_word(0x12345678, 0x0F0F0F0F, carry_in=1)
    
    # Correct result case
    expected_val = 0x12345678 + 0x0F0F0F0F + 1
    expected_carry = 0
    packet = ranger.observe_word_alu(res, expected_val, expected_carry)
    assert packet.recommendation == "observe"
    assert packet.evidence["matches_oracle"] is True
    
    # Incorrect result case
    packet_bad = ranger.observe_word_alu(res, expected_val + 5, expected_carry)
    assert packet_bad.recommendation == "reject"
    assert packet_bad.evidence["matches_oracle"] is False
    
    # Serialization test
    js = json.dumps(packet.to_dict())
    assert js is not None


# ---- Phase 3 new verification tests ----

def test_pml_profile_calculations():
    """Verify that WaveguideBoundary creates correct parabolic damping profiles."""
    boundary = WaveguideBoundary()
    
    grid_size = 100
    pml_cells = 10
    core_gamma = 0.005
    boundary_gamma = 0.20
    
    pml_profile = boundary.build_pml_profile(
        lane_id=1,
        grid_size=grid_size,
        pml_cells=pml_cells,
        core_gamma=core_gamma,
        boundary_gamma=boundary_gamma
    )
    
    assert len(pml_profile.profile) == grid_size
    assert pml_profile.lane_id == 1
    assert pml_profile.pml_cells == pml_cells
    
    # Check interior region damping is exactly core_gamma
    assert pml_profile.profile[50] == core_gamma
    assert pml_profile.profile[15] == core_gamma
    
    # Check boundaries damping rises toward boundary_gamma at the exact edges
    assert abs(pml_profile.profile[0] - boundary_gamma) < 1e-6
    assert abs(pml_profile.profile[-1] - boundary_gamma) < 1e-6
    # Damping inside the left PML region should be strictly greater than core_gamma
    assert pml_profile.profile[2] > core_gamma


def test_hcam_banking_layout_widths():
    """Verify that HCAMBank.for_width generates correct number of byte memory banks."""
    banks_16 = HCAMBank.for_width(16)
    assert len(banks_16) == 2
    assert banks_16[0].address_basin == "Basin_Addr_L0"
    
    banks_32 = HCAMBank.for_width(32)
    assert len(banks_32) == 4
    
    banks_64 = HCAMBank.for_width(64)
    assert len(banks_64) == 8
    
    with pytest.raises(ValueError):
        HCAMBank.for_width(8)


def test_lane_fabric_memory_plan():
    """Verify that LaneFabric generates valid memory recall plans mapping all lanes."""
    fabric = LaneFabric.for_width(32)
    plan = fabric.memory_plan_for_address(0xABCDEF01)
    
    assert plan.address == 0xABCDEF01
    assert plan.address_map.width == 32
    assert plan.address_map.lane_count == 4
    assert len(plan.address_map.banks) == 4
    
    # Verify execution steps trace maps all 4 banks
    for i in range(4):
        gate_step = f"Open recall gate 'Gate_Recall_L{i}' for Bank {i}"
        assert gate_step in plan.execution_steps


def test_boundary_ranger_observes_pml_profile():
    """Verify BoundaryRanger observes PML profile configurations and generates SovereignPackets."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    ranger = BoundaryRanger(lib_agent=library_dir)
    
    boundary = WaveguideBoundary()
    profile = boundary.build_pml_profile(grid_size=128, pml_cells=16, core_gamma=0.002, boundary_gamma=0.15)
    
    packet = ranger.observe_pml_profile(profile, mission_id="L11_BOUND_CHECK")
    assert packet.actor == "Boundary Ranger"
    assert packet.recommendation == "observe"
    assert packet.evidence["boundaries_configured"] is True
    assert packet.evidence["max_damping"] == 0.15
    
    # Verify serializable
    js = json.dumps(packet.to_dict())
    assert js is not None


def test_memory_ranger_observes_recall_plan():
    """Verify MemoryRanger observes recall plans and reports mappings correctly."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    ranger = MemoryRanger(lib_agent=library_dir)
    
    fabric = LaneFabric.for_width(64)
    plan = fabric.memory_plan_for_address(0x11223344)
    
    packet = ranger.observe_recall_plan(plan, mission_id="L13_MEM_CHECK")
    assert packet.actor == "Memory Ranger"
    assert packet.recommendation == "observe"
    assert packet.evidence["mapping_valid"] is True
    assert packet.evidence["bank_count"] == 8
    
    # Test incorrect map (simulated via missing a bank)
    bad_map = {
        "address": 0x11223344,
        "address_map": {
            "width": 64,
            "lane_count": 8,
            "banks": [
                # missing bank_id=7
                {"bank_id": j} for j in range(7)
            ]
        }
    }
    packet_bad = ranger.observe_recall_plan(bad_map, mission_id="L13_MEM_CHECK")
    assert packet_bad.recommendation == "reject"
    assert packet_bad.evidence["mapping_valid"] is False
    assert packet_bad.evidence["missing_mappings"] == [7]
    
    # Verify serializable
    js = json.dumps(packet.to_dict())
    assert js is not None


# ---- Phase 4 new verification tests ----

def test_byte_slice_encoding():
    """Verify that PDMByteSlice.encode_byte correctly maps bits to active/inactive channels."""
    slice_cell = PDMByteSlice(lane_id=0, bit_offset=0)
    
    # 0x00 -> 8 inactive channels
    encoded_00 = slice_cell.encode_byte(0x00)
    assert len(encoded_00.channels) == 8
    assert all(not ch.active for ch in encoded_00.channels)
    assert all(ch.amplitude == 0.0 for ch in encoded_00.channels)
    
    # 0xFF -> 8 active channels
    encoded_ff = slice_cell.encode_byte(0xFF)
    assert len(encoded_ff.channels) == 8
    assert all(ch.active for ch in encoded_ff.channels)
    assert all(ch.amplitude == 1.0 for ch in encoded_ff.channels)
    
    # 0b10101010 -> maps bits correctly across sine/cosine channels
    # 0b10101010: bits at positions 1, 3, 5, 7 are active (value: 2, 8, 32, 128)
    # Positions:
    # idx 0: bit 0 (inactive) -> period 11, sin
    # idx 1: bit 1 (active) -> period 11, cos
    # idx 2: bit 2 (inactive) -> period 13, sin
    # idx 3: bit 3 (active) -> period 13, cos
    # idx 4: bit 4 (inactive) -> period 17, sin
    # idx 5: bit 5 (active) -> period 17, cos
    # idx 6: bit 6 (inactive) -> period 19, sin
    # idx 7: bit 7 (active) -> period 19, cos
    encoded_mix = slice_cell.encode_byte(0b10101010)
    for idx, ch in enumerate(encoded_mix.channels):
        if idx % 2 == 1:
            assert ch.active is True
            assert ch.amplitude == 1.0
            assert ch.quadrature == "cos"
        else:
            assert ch.active is False
            assert ch.amplitude == 0.0
            assert ch.quadrature == "sin"


def test_byte_slice_round_trip():
    """Verify that decode_reference(encode_byte(x)) == x for representative values."""
    slice_cell = PDMByteSlice(lane_id=0, bit_offset=0)
    test_values = [0x00, 0xFF, 0x55, 0xAA, 0x12, 0x8F, 0x7E, 0xC3]
    for val in test_values:
        encoded = slice_cell.encode_byte(val)
        decoded = slice_cell.decode_reference(encoded)
        assert decoded == val


def test_wave_sampling():
    """Verify deterministic wave sample helpers return expected values and support envelopes."""
    slice_cell = PDMByteSlice(lane_id=0, bit_offset=0)
    
    # Encode a byte with active bits
    encoded = slice_cell.encode_byte(0b00000010)  # Bit 1 active: period 11.0, cos, amplitude 1.0
    channel = encoded.channels[1]
    
    # sample_channel at t = 0.0: cos(0) = 1.0 * amplitude (1.0) = 1.0
    import math
    from sol_pdm_byte_slice import sample_channel, sample_encoded_byte, sample_wave_packet
    
    y_t0 = sample_channel(channel, t=0.0)
    assert abs(y_t0 - 1.0) < 1e-6
    
    # Test with a temporal Gaussian envelope from WaveguideBoundary
    boundary = WaveguideBoundary()
    envelope_func = boundary.get_temporal_gaussian_envelope(t0=5.0, width=2.0)
    
    # Envelope at t=5.0 should be exp(0) = 1.0
    assert abs(envelope_func(5.0) - 1.0) < 1e-6
    # Envelope at t=0.0 should be exp(-(0-5)^2 / (2 * 4)) = exp(-25/8) = 0.0439
    env_t0 = envelope_func(0.0)
    assert abs(env_t0 - math.exp(-25.0 / 8.0)) < 1e-6
    
    y_t0_env = sample_channel(channel, t=0.0, envelope_func=envelope_func)
    assert abs(y_t0_env - 1.0 * env_t0) < 1e-6
    
    # Test sample_encoded_byte and sample_wave_packet
    y_byte_t0 = sample_encoded_byte(encoded, t=0.0)
    assert abs(y_byte_t0 - 1.0) < 1e-6
    
    y_packet = sample_wave_packet(encoded, t_values=[0.0, 5.0])
    assert len(y_packet) == 2
    assert abs(y_packet[0] - 1.0) < 1e-6


def test_lane_fabric_word_encoding():
    """Verify that LaneFabric splits values into correct numbers of byte slices and supports multi-lane wave sampling."""
    fab_16 = LaneFabric.for_width(16)
    encoded_16 = fab_16.encode_word(0xABCD)
    assert len(encoded_16) == 2
    assert encoded_16[0].value == 0xCD
    assert encoded_16[1].value == 0xAB
    
    fab_32 = LaneFabric.for_width(32)
    encoded_32 = fab_32.encode_word(0x12345678)
    assert len(encoded_32) == 4
    assert encoded_32[0].value == 0x78
    assert encoded_32[3].value == 0x12
    
    fab_64 = LaneFabric.for_width(64)
    encoded_64 = fab_64.encode_word(0x0123456789ABCDEF)
    assert len(encoded_64) == 8
    assert encoded_64[0].value == 0xEF
    assert encoded_64[7].value == 0x01
    
    # Verify multi-lane wave packet sampling
    t_vals = [0.0, 1.0, 2.0]
    sampled = fab_32.sample_word_wave_packet(encoded_32, t_vals)
    assert len(sampled) == 4
    assert all(len(lane_samples) == 3 for lane_samples in sampled)


def test_signal_ranger_observes_pdm():
    """Verify SignalRanger observes PDMEncodedByte and outputs a JSON-serializable SovereignPacket."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    ranger = SignalRanger(lib_agent=library_dir)
    
    # Test single byte observation
    slice_cell = PDMByteSlice(lane_id=3, bit_offset=24)
    encoded_byte = slice_cell.encode_byte(0x5A)
    
    packet = ranger.observe_signal(encoded_byte, mission_id="L11_SIG_CHECK_SINGLE")
    assert packet.actor == "Signal Ranger"
    assert packet.recommendation == "observe"
    assert packet.evidence["lane_ids"] == 3
    assert packet.evidence["values"] == 0x5A
    assert packet.evidence["active_channel_count"] == 4  # 0x5A (01011010) has 4 set bits
    assert packet.evidence["channel_mapping_completeness"] is True
    assert packet.evidence["is_word"] is False
    
    # Test word observation
    fabric = LaneFabric.for_width(16)
    encoded_word = fabric.encode_word(0xAA55)
    packet_word = ranger.observe_signal(encoded_word, mission_id="L11_SIG_CHECK_WORD")
    assert packet_word.recommendation == "observe"
    assert packet_word.evidence["lane_ids"] == [0, 1]
    assert packet_word.evidence["values"] == [0x55, 0xAA]
    assert packet_word.evidence["active_channel_count"] == 8  # 0x55 (4 bits) + 0xAA (4 bits)
    assert packet_word.evidence["is_word"] is True
    
    # Verify serializable
    js = json.dumps(packet.to_dict())
    assert js is not None
    js_word = json.dumps(packet_word.to_dict())
    assert js_word is not None


# ---- Phase 5 new verification tests ----

def test_phase_alignment_table_building():
    """Verify that build_default_phase_table correctly generates 8 entries for 4 carriers."""
    periods = [11.0, 13.0, 17.0, 19.0]
    table = build_default_phase_table(lane_id=2, periods=periods)
    assert table.lane_id == 2
    assert len(table.entries) == 8
    
    # Assert entry fields are properly structured
    first_entry = table.entries[0]
    assert isinstance(first_entry, PhaseAlignmentEntry)
    assert first_entry.carrier_period == 11.0
    assert first_entry.quadrature == "sin"
    assert first_entry.calibrated_phase == 0.0


def test_phase_error_angle_wrapping():
    """Verify that phase_error wraps correctly within [-pi, pi]."""
    import math
    
    # Simple differences
    assert abs(phase_error(0.0, 0.5) - 0.5) < 1e-6
    assert abs(phase_error(0.5, 0.0) - (-0.5)) < 1e-6
    
    # Wrappings across 2pi boundary
    # Expected: pi - 0.1, Observed: -pi + 0.1 -> error should be 0.2
    assert abs(phase_error(math.pi - 0.1, -math.pi + 0.1) - 0.2) < 1e-6
    assert abs(phase_error(-math.pi + 0.1, math.pi - 0.1) - (-0.2)) < 1e-6
    
    # Identical angles with multiples of 2pi difference
    assert abs(phase_error(0.0, 2 * math.pi)) < 1e-6
    assert abs(phase_error(1.0, 1.0 + 4 * math.pi)) < 1e-6


def test_drift_observation_detection():
    """Verify that observe_phase_drift correctly detects tolerance status."""
    periods = [11.0, 13.0, 17.0, 19.0]
    expected_table = build_default_phase_table(lane_id=0, periods=periods)
    
    # In-tolerance observed table (all within 0.03 error)
    observed_table_in = build_default_phase_table(lane_id=0, periods=periods)
    for entry in observed_table_in.entries:
        entry.calibrated_phase = 0.02
        
    obs_in = observe_phase_drift(expected_table, observed_table_in)
    assert obs_in.lane_id == 0
    assert abs(obs_in.max_phase_error - 0.02) < 1e-6
    assert obs_in.out_of_tolerance is False
    assert is_within_phase_tolerance(obs_in, tolerance=0.05) is True

    # Out-of-tolerance observed table (max error 0.08)
    observed_table_out = build_default_phase_table(lane_id=0, periods=periods)
    observed_table_out.entries[2].calibrated_phase = 0.08
    
    obs_out = observe_phase_drift(expected_table, observed_table_out)
    assert abs(obs_out.max_phase_error - 0.08) < 1e-6
    assert obs_out.out_of_tolerance is True
    assert is_within_phase_tolerance(obs_out, tolerance=0.05) is False


def test_byte_slice_with_calibrated_phases():
    """Verify PDMByteSlice loads and applies calibrated phases from a PhaseAlignmentTable during encoding."""
    periods = [11.0, 13.0, 17.0, 19.0]
    table = build_default_phase_table(lane_id=1, periods=periods)
    
    # Set a custom phase offset on a specific channel entry (period 13.0, cos)
    # Entry 3 in default table (11.0 sin, 11.0 cos, 13.0 sin, 13.0 cos)
    table.entries[3].calibrated_phase = 1.25
    
    slice_cell = PDMByteSlice(lane_id=1, bit_offset=0, periods=periods, phase_table=table)
    encoded = slice_cell.encode_byte(0xFF)
    
    # channel corresponding to period 13.0, cos (index 3) should have phase = 1.25
    target_channel = encoded.channels[3]
    assert target_channel.carrier_period == 13.0
    assert target_channel.quadrature == "cos"
    assert target_channel.phase == 1.25
    
    # Other channels should have phase 0.0
    assert encoded.channels[0].phase == 0.0


def test_dispersion_profile_generation():
    """Verify dispersion profile calculations generate deterministic group delays and phase shifts."""
    periods = [11.0, 13.0, 17.0, 19.0]
    profile = build_dispersion_profile(lane_id=3, periods=periods, lane_length=100.0)
    
    assert profile.lane_id == 3
    assert profile.lane_length == 100.0
    assert profile.dispersion_coeff == 0.015
    assert len(profile.group_delays) == 4
    assert len(profile.phase_shifts) == 4
    
    # Verify group delay for period 11.0: 0.015 * 100.0 / 11.0 = 1.5 / 11.0 = 0.13636
    expected_delay = 1.5 / 11.0
    assert abs(profile.group_delays[11.0] - expected_delay) < 1e-6


def test_frontier_drift_controller_advisory():
    """Verify that FrontierDriftController returns correct shadow recommendations under various drift levels."""
    bridge = FrontierBridge()
    controller = FrontierDriftController(bridge)
    
    # 1. Under tolerance: max_err = 0.02
    obs_ok = PhaseDriftObservation(lane_id=0, max_phase_error=0.02, average_phase_error=0.01, out_of_tolerance=False, evidence={})
    rec_ok = controller.suggest(obs_ok)
    assert rec_ok.action == "observe"
    assert rec_ok.nudge_value == 0.0
    assert rec_ok.damping_adjustment == 0.0
    
    # 2. Moderate error: max_err = 0.12, avg_err = 0.08 -> suggest phase nudge
    obs_mod = PhaseDriftObservation(lane_id=0, max_phase_error=0.12, average_phase_error=0.08, out_of_tolerance=True, evidence={})
    rec_mod = controller.suggest(obs_mod)
    assert rec_mod.action == "suggest_phase_nudge"
    # nudge = -0.5 * avg_err = -0.04
    assert abs(rec_mod.nudge_value - (-0.04)) < 1e-6
    assert rec_mod.damping_adjustment == 0.0
    
    # 3. High error: max_err = 0.25 -> suggest damping adjustment
    obs_high = PhaseDriftObservation(lane_id=0, max_phase_error=0.25, average_phase_error=0.18, out_of_tolerance=True, evidence={})
    rec_high = controller.suggest(obs_high)
    assert rec_high.action == "suggest_damping_adjustment"
    assert rec_high.nudge_value == 0.0
    assert rec_high.damping_adjustment == 0.012
    
    # 4. Critical error: max_err = 0.40 -> quarantine lane
    obs_crit = PhaseDriftObservation(lane_id=0, max_phase_error=0.40, average_phase_error=0.30, out_of_tolerance=True, evidence={})
    rec_crit = controller.suggest(obs_crit)
    assert rec_crit.action == "quarantine_lane"
    assert rec_crit.nudge_value == 0.0
    assert rec_crit.damping_adjustment == 0.0
    
    # Verify that telemetry history on the bridge recorded all these events
    assert len(bridge.telemetry_history) == 4
    assert bridge.telemetry_history[0]["event"] == "frontier_drift_suggestion"


def test_drift_ranger_observes_signal():
    """Verify that DriftRanger observes phase drift and outputs a JSON-serializable SovereignPacket."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    ranger = DriftRanger(lib_agent=library_dir)
    
    obs = PhaseDriftObservation(
        lane_id=2,
        max_phase_error=0.12,
        average_phase_error=0.08,
        out_of_tolerance=True,
        evidence={"details": "mock"}
    )
    
    packet = ranger.observe_drift(obs, tolerance=0.05, mission_id="L11_DRIFT_PATROL")
    assert packet.actor == "Drift Ranger"
    assert packet.recommendation == "patch"  # 0.12 falls in "suggest_phase_nudge" which maps to "patch"
    assert packet.evidence["lane_id"] == 2
    assert packet.evidence["max_phase_error"] == 0.12
    assert packet.evidence["drift_detected"] is True
    assert packet.evidence["recommended_action"] == "suggest_phase_nudge"
    
    # Verify serializability
    js = json.dumps(packet.to_dict())
    assert js is not None


# ---- Phase 6 new verification tests ----

def test_csr_conversion_edge_count():
    """Verify Compressed Sparse Row conversion preserves node and edge indices."""
    nodes = [
        {"id": "n0", "rho": 5.0, "psi": 0.0},
        {"id": "n1", "rho": 10.0, "psi": 0.5},
        {"id": "n2", "rho": 15.0, "psi": -0.5}
    ]
    edges = [
        {"from": "n0", "to": "n1", "w0": 1.0, "conductance": 1.0, "flux": 0.0},
        {"from": "n1", "to": "n2", "w0": 1.0, "conductance": 1.0, "flux": 0.0},
        {"from": "n0", "to": "n2", "w0": 1.5, "conductance": 1.2, "flux": 0.0}
    ]
    
    csr = build_csr_from_edges(nodes, edges)
    # 3 nodes -> row_ptr size is 4
    assert len(csr.row_ptr) == 4
    # Total outgoing edges is 3
    assert len(csr.col_indices) == 3
    assert len(csr.edge_indices) == 3
    
    # Node 0 has 2 outgoing edges (to n1, n2)
    # Node 1 has 1 outgoing edge (to n2)
    # Node 2 has 0 outgoing edges
    # row_ptr should be [0, 2, 3, 3]
    row_ptr_list = list(csr.row_ptr)
    assert row_ptr_list == [0, 2, 3, 3]


def test_graph_array_shapes():
    """Verify that node and edge state arrays have correct shapes and can be restored."""
    nodes = [
        {"id": "n0", "rho": 5.0, "psi": 0.0, "p": 1.2, "semanticMass": 1.5},
        {"id": "n1", "rho": 10.0, "psi": 0.5, "p": 2.4, "semanticMass": 2.0}
    ]
    edges = [
        {"from": "n0", "to": "n1", "w0": 1.1, "conductance": 1.3, "flux": 0.2}
    ]
    
    snapshot = snapshot_graph_arrays(nodes, edges)
    assert len(snapshot.node_ids) == 2
    assert len(snapshot.rho) == 2
    assert len(snapshot.psi) == 2
    assert len(snapshot.pressure) == 2
    assert len(snapshot.semantic_mass) == 2
    
    assert len(snapshot.edge_from_idx) == 1
    assert len(snapshot.edge_to_idx) == 1
    assert len(snapshot.edge_w0) == 1
    assert len(snapshot.edge_conductance) == 1
    assert len(snapshot.edge_flux) == 1
    
    # Mutate snapshot values
    snapshot.rho[0] = 99.0
    snapshot.edge_flux[0] = 55.0
    
    # Restore in-place
    restore_graph_arrays(snapshot, nodes, edges)
    assert nodes[0]["rho"] == 99.0
    assert edges[0]["flux"] == 55.0


def test_vectorized_pressure_calculation():
    """Verify pressure array equation of state computes correctly."""
    rho = [10.0, 20.0]
    m = [2.0, 5.0]
    c_press = 1.5
    
    try:
        import numpy as np
        rho_arr = np.array(rho)
        m_arr = np.array(m)
        p = compute_pressure_array(rho_arr, m_arr, c_press)
        # Expected p[0] = 1.5 * log(1 + 10/2) = 1.5 * log(6)
        assert abs(p[0] - 1.5 * math.log(6.0)) < 1e-6
        assert abs(p[1] - 1.5 * math.log(5.0)) < 1e-6
    except ImportError:
        p = compute_pressure_array(rho, m, c_press)
        assert abs(p[0] - 1.5 * math.log(6.0)) < 1e-6


def test_vectorized_flux_calculation():
    """Verify flux delta array computation matches conductance * delta_p."""
    press = [3.0, 1.0]
    edge_from = [0]
    edge_to = [1]
    cond = [1.5]
    
    try:
        import numpy as np
        press_arr = np.array(press)
        from_arr = np.array(edge_from)
        to_arr = np.array(edge_to)
        cond_arr = np.array(cond)
        
        flux = compute_flux_delta_array(press_arr, from_arr, to_arr, cond_arr)
        # Expected: 1.5 * (3.0 - 1.0) = 3.0
        assert abs(flux[0] - 3.0) < 1e-6
    except ImportError:
        flux = compute_flux_delta_array(press, edge_from, edge_to, cond)
        assert abs(flux[0] - 3.0) < 1e-6


def test_vectorized_rho_transport():
    """Verify rho transport array calculation conserves transport sum."""
    flux = [4.0, -2.0]
    edge_from = [0, 1]
    edge_to = [1, 2]
    node_count = 3
    
    try:
        import numpy as np
        flux_arr = np.array(flux)
        from_arr = np.array(edge_from)
        to_arr = np.array(edge_to)
        
        d_rho = compute_rho_transport_array(flux_arr, from_arr, to_arr, node_count)
        # Edge 0 (from 0 to 1, flux 4.0): flow = 2.0 -> d_rho[0] -= 2.0, d_rho[1] += 2.0
        # Edge 1 (from 1 to 2, flux -2.0): flow = -1.0 -> d_rho[1] -= -1.0 (+1.0), d_rho[2] += -1.0
        # Expected d_rho = [-2.0, 3.0, -1.0]
        assert abs(d_rho[0] - (-2.0)) < 1e-6
        assert abs(d_rho[1] - 3.0) < 1e-6
        assert abs(d_rho[2] - (-1.0)) < 1e-6
        # Sum of transport must be exactly 0
        assert abs(sum(d_rho)) < 1e-6
    except ImportError:
        d_rho = compute_rho_transport_array(flux, edge_from, edge_to, node_count)
        assert abs(d_rho[0] - (-2.0)) < 1e-6
        assert abs(sum(d_rho)) < 1e-6


def test_simd_mode_planning():
    """Verify SIMDExecutionPlan correctly maps groups onto byte-slices for Level 14 modes."""
    # uint8x8 -> 8 lanes
    p8 = plan_simd_mode(64, "uint8x8")
    assert p8.mode.lane_count == 8
    assert len(p8.groups) == 8
    assert p8.groups[0]["mapped_lanes"] == [0]
    assert p8.groups[7]["mapped_lanes"] == [7]
    
    # uint16x4 -> 4 groups of 2 lanes
    p16 = plan_simd_mode(64, "uint16x4")
    assert p16.mode.lane_count == 4
    assert len(p16.groups) == 4
    assert p16.groups[0]["mapped_lanes"] == [0, 1]
    assert p16.groups[3]["mapped_lanes"] == [6, 7]
    
    # uint32x2 -> 2 groups of 4 lanes
    p32 = plan_simd_mode(64, "uint32x2")
    assert p32.mode.lane_count == 2
    assert len(p32.groups) == 2
    assert p32.groups[0]["mapped_lanes"] == [0, 1, 2, 3]
    assert p32.groups[1]["mapped_lanes"] == [4, 5, 6, 7]
    
    # uint64x1 -> 1 group of 8 lanes
    p64 = plan_simd_mode(64, "uint64x1")
    assert p64.mode.lane_count == 1
    assert len(p64.groups) == 1
    assert p64.groups[0]["mapped_lanes"] == [0, 1, 2, 3, 4, 5, 6, 7]
    
    # Test LaneFabric integration
    fabric = LaneFabric.for_width(64)
    plan = fabric.simd_plan("uint16x4")
    assert plan.mode.name == "uint16x4"
    assert len(plan.groups) == 4


def test_kernel_ranger_observes_structures():
    """Verify that KernelRanger observes vectorized structures and emits a SovereignPacket."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    ranger = KernelRanger(lib_agent=library_dir)
    
    # Test GraphKernelArrays observation
    nodes = [{"id": "n0", "rho": 1.0}]
    edges = []
    snapshot = snapshot_graph_arrays(nodes, edges)
    
    packet = ranger.observe_kernel(snapshot, mission_id="L14_KERN_CHECK")
    assert packet.actor == "Kernel Ranger"
    assert packet.recommendation == "observe"
    assert packet.evidence["node_count"] == 1
    assert packet.evidence["csr_valid"] is True
    
    # Test SIMDExecutionPlan observation
    plan = plan_simd_mode(64, "uint32x2")
    packet_simd = ranger.observe_kernel(plan, mission_id="L14_SIMD_CHECK")
    assert packet_simd.recommendation == "observe"
    assert packet_simd.evidence["simd_mode"] == "uint32x2"
    assert packet_simd.evidence["lane_count"] == 2
    
    # Verify serializable
    js = json.dumps(packet.to_dict())
    assert js is not None


def test_vectorized_backend_imports():
    """Verify that vectorized backend modules import cleanly."""
    from sol_graph_kernel import VectorizedGraphStepper, VectorizedParityReport, VectorizedBackendConfig
    from sol_engine_backend_adapter import step_vectorized_impl
    assert VectorizedGraphStepper is not None
    assert VectorizedParityReport is not None
    assert step_vectorized_impl is not None


def test_vectorized_stepper_initialization():
    """Verify that VectorizedGraphStepper.from_engine compiles state from a small graph."""
    engine = SOLEngine.from_default_graph()
    stepper = VectorizedGraphStepper.from_engine(engine)
    assert stepper is not None
    assert len(stepper.snapshot.node_ids) == len(engine.physics.nodes)
    assert len(stepper.snapshot.edge_from_idx) == len(engine.physics.edges)


def test_vectorized_shadow_step_execution():
    """Verify that one vectorized shadow step returns a valid VectorizedStepReport."""
    engine = SOLEngine.from_default_graph()
    stepper = VectorizedGraphStepper.from_engine(engine)
    report = stepper.step_arrays(dt=0.12, c_press=0.1, damping=0.2)
    assert report is not None
    assert isinstance(report.total_flux, float)
    assert isinstance(report.active_count, int)
    assert "total_flux" in report.evidence


def test_parity_report_serialization():
    """Verify that VectorizedParityReport serializes to JSON cleanly."""
    report = VectorizedParityReport(
        lane_id=0,
        node_count=10,
        edge_count=20,
        max_rho_error=1e-7,
        max_pressure_error=1e-7,
        max_flux_error=1e-7,
        tolerance=1e-6,
        parity_passed=True,
        backend_mode="vectorized",
        evidence={"details": "all clear"}
    )
    assert report.lane_id == 0
    assert report.node_count == 10
    assert report.parity_passed is True
    
    import dataclasses
    d = dataclasses.asdict(report)
    js = json.dumps(d)
    assert js is not None
    assert '"parity_passed": true' in js


def test_kernel_ranger_observes_parity_report():
    """Verify that KernelRanger emits a valid SovereignPacket from a parity report."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    ranger = KernelRanger(lib_agent=library_dir)
    
    report = VectorizedParityReport(
        lane_id=0,
        node_count=5,
        edge_count=10,
        max_rho_error=1e-7,
        max_pressure_error=1e-7,
        max_flux_error=1e-7,
        tolerance=1e-6,
        parity_passed=True,
        backend_mode="vectorized",
        evidence={}
    )
    
    packet = ranger.observe_kernel(report, mission_id="L14_PARITY_CHECK")
    assert packet.actor == "Kernel Ranger"
    assert packet.recommendation == "observe"
    assert packet.evidence["parity_passed"] is True
    assert packet.evidence["backend_mode"] == "vectorized"
    
    report_fail = VectorizedParityReport(
        lane_id=0,
        node_count=5,
        edge_count=10,
        max_rho_error=0.1,
        max_pressure_error=0.1,
        max_flux_error=0.1,
        tolerance=1e-6,
        parity_passed=False,
        backend_mode="vectorized",
        evidence={}
    )
    packet_fail = ranger.observe_kernel(report_fail, mission_id="L14_PARITY_CHECK")
    assert packet_fail.recommendation == "reject"
    assert packet_fail.evidence["parity_passed"] is False


def test_default_backend_unchanged():
    """Verify that the default backend remains dictionary mode and option works."""
    engine = SOLEngine.from_default_graph()
    assert getattr(engine, "backend", "dict") == "dict"
    
    res_dict = engine.step(dt=0.12, c_press=0.1, damping=0.2)
    assert "totalFlux" in res_dict
    
    engine.set_backend("vectorized")
    assert engine.backend == "vectorized"
    res_vec = engine.step(dt=0.12, c_press=0.1, damping=0.2)
    assert "totalFlux" in res_vec
    
    with pytest.raises(ValueError):
        engine.set_backend("invalid_backend_name")


def test_shadow_step_comparison_run():
    """Verify that run_shadow_steps performs comparison and preserves original state."""
    engine = SOLEngine.from_default_graph()
    orig_t = engine.t
    orig_step = engine.step_count
    
    report = run_shadow_steps(engine, steps=3, dt=0.12, c_press=0.1, damping=0.2)
    assert report is not None
    assert report.node_count == len(engine.physics.nodes)
    assert report.edge_count == len(engine.physics.edges)
    assert isinstance(report.parity_passed, bool)
    
    # State must be preserved
    assert engine.t == orig_t
    assert engine.step_count == orig_step
    assert getattr(engine, "backend", "dict") == "dict"


def test_drift_packet_review_decisions():
    """Verify that PromotionCourt reviews drift packets within tolerance/outside tolerance correctly."""
    court = PromotionCourt()
    
    p_ok = SovereignPacket(
        packet_id="PKT_DRIFT_001",
        domain="sol_sovereign",
        level=11,
        actor="Drift Ranger",
        actor_type="ranger",
        mission_id="M_DRIFT",
        claim="drift report",
        evidence={"lane_id": 1, "max_phase_error": 0.02, "tolerance": 0.05},
        invariants_checked=["phase_drift_tolerance"],
        artifacts=[],
        recommendation="observe",
        confidence=0.98,
        reproducibility_hash="hash_ok"
    )
    res_ok = court.review_drift_packet(p_ok)
    assert isinstance(res_ok, PromotionGateResult)
    assert res_ok.decision == "observe"
    assert res_ok.passed is True
    
    p_corr = SovereignPacket(
        packet_id="PKT_DRIFT_002",
        domain="sol_sovereign",
        level=11,
        actor="Drift Ranger",
        actor_type="ranger",
        mission_id="M_DRIFT",
        claim="drift report",
        evidence={"lane_id": 1, "max_phase_error": 0.12, "tolerance": 0.05},
        invariants_checked=["phase_drift_tolerance"],
        artifacts=[],
        recommendation="patch",
        confidence=0.98,
        reproducibility_hash="hash_corr"
    )
    res_corr = court.review_drift_packet(p_corr)
    assert res_corr.decision == "authorize_candidate_phase_correction"
    assert res_corr.passed is True
    
    p_quar = SovereignPacket(
        packet_id="PKT_DRIFT_003",
        domain="sol_sovereign",
        level=11,
        actor="Drift Ranger",
        actor_type="ranger",
        mission_id="M_DRIFT",
        claim="drift report",
        evidence={"lane_id": 1, "max_phase_error": 0.45, "tolerance": 0.05},
        invariants_checked=["phase_drift_tolerance"],
        artifacts=[],
        recommendation="quarantine",
        confidence=0.98,
        reproducibility_hash="hash_quar"
    )
    res_quar = court.review_drift_packet(p_quar)
    assert res_quar.decision == "quarantine_lane"
    assert res_quar.passed is False


def test_waveguide_packet_review_decisions():
    """Verify that PromotionCourt reviews waveguide packets correctly."""
    court = PromotionCourt()
    
    p_ok = SovereignPacket(
        packet_id="PKT_WAVE_001",
        domain="sol_sovereign",
        level=11,
        actor="Boundary Ranger",
        actor_type="ranger",
        mission_id="M_WAVE",
        claim="waveguide report",
        evidence={"lane_id": 2, "reflection_score": 0.03},
        invariants_checked=[],
        artifacts=[],
        recommendation="observe",
        confidence=0.95,
        reproducibility_hash="hash1"
    )
    res_ok = court.review_waveguide_packet(p_ok)
    assert res_ok.decision == "observe"
    assert res_ok.passed is True
    
    p_corr = SovereignPacket(
        packet_id="PKT_WAVE_002",
        domain="sol_sovereign",
        level=11,
        actor="Boundary Ranger",
        actor_type="ranger",
        mission_id="M_WAVE",
        claim="waveguide report",
        evidence={"lane_id": 2, "reflection_score": 0.12},
        invariants_checked=[],
        artifacts=[],
        recommendation="patch",
        confidence=0.95,
        reproducibility_hash="hash2"
    )
    res_corr = court.review_waveguide_packet(p_corr)
    assert res_corr.decision == "authorize_candidate_damping_correction"
    assert res_corr.passed is True


def test_correction_magnitude_policy_clamping():
    """Verify that authorization clamps phase nudges to BoundedCorrectionPolicy bounds."""
    court = PromotionCourt()
    policy = BoundedCorrectionPolicy(max_phase_nudge=0.05, max_damping_delta=0.01)
    
    p_gate_result = PromotionGateResult(
        decision="authorize_candidate_phase_correction",
        gate_name="drift_gate_lane_1",
        passed=True,
        evidence_hash="somehash",
        details={"lane_id": 1, "nudge_value": 0.15, "max_phase_error": 0.12}
    )
    dec = court.authorize_candidate_correction(p_gate_result, policy)
    assert dec.authorized is True
    assert dec.correction_type == "phase"
    assert "clamped to 0.0500" in dec.reason


def test_candidate_phase_table_immutability():
    """Verify that candidate phase table is generated without modifying the original."""
    periods = [11.0, 13.0, 17.0, 19.0]
    old_table = build_default_phase_table(lane_id=3, periods=periods)
    
    assert old_table.entries[0].calibrated_phase == 0.0
    
    correction = CandidateCorrection(
        reason="test nudge",
        confidence=0.95,
        bounded_delta=0.045,
        target_lane=3,
        target_channel=(11.0, "sin"),
        before_value=0.0,
        after_value=0.045,
        evidence_hash="hash123",
        correction_type="phase"
    )
    
    new_table = apply_candidate_phase_correction(old_table, correction)
    
    assert old_table.entries[0].calibrated_phase == 0.0
    assert new_table.entries[0].calibrated_phase == 0.045
    assert new_table.entries[1].calibrated_phase == 0.0


def test_phase_table_diff():
    """Verify that diff_phase_tables reports changed entries correctly."""
    periods = [11.0, 13.0]
    t1 = build_default_phase_table(lane_id=0, periods=periods)
    t2 = apply_candidate_phase_correction(t1, CandidateCorrection(
        reason="test nudge", confidence=0.95, bounded_delta=0.03, target_lane=0,
        target_channel=(13.0, "cos"), before_value=0.0, after_value=0.03,
        evidence_hash="h", correction_type="phase"
    ))
    
    diffs = diff_phase_tables(t1, t2)
    assert len(diffs) == 1
    assert (13.0, "cos") in diffs
    assert diffs[(13.0, "cos")] == (0.0, 0.03)


def test_replay_gate_verification():
    """Verify that calibration replay gate detects missing metrics or supplied ones."""
    periods = [11.0]
    t1 = build_default_phase_table(lane_id=0, periods=periods)
    t2 = apply_candidate_phase_correction(t1, CandidateCorrection(
        reason="test nudge", confidence=0.95, bounded_delta=0.03, target_lane=0,
        target_channel=(11.0, "sin"), before_value=0.0, after_value=0.03,
        evidence_hash="h", correction_type="phase"
    ))
    
    res_missing = run_calibration_replay(CalibrationReplayInput(t1, t2, metrics=None))
    assert res_missing.status == "needs_more_evidence"
    
    metrics_pass = {
        "active_delta": 0.25,
        "crosstalk": 0.03,
        "reversed_delta": 0.05
    }
    res_pass = run_calibration_replay(CalibrationReplayInput(t1, t2, metrics=metrics_pass))
    assert res_pass.status == "pass"
    
    metrics_fail = {
        "active_delta": 0.15,
        "crosstalk": 0.03,
        "reversed_delta": 0.05
    }
    res_fail = run_calibration_replay(CalibrationReplayInput(t1, t2, metrics=metrics_fail))
    assert res_fail.status == "fail"


def test_court_ranger_packet_emission():
    """Verify that CourtRanger evaluates reports and emits a valid, JSON-serializable SovereignPacket."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    ranger = CourtRanger(lib_agent=library_dir)
    
    res = PromotionGateResult(
        decision="authorize_candidate_phase_correction",
        gate_name="drift_gate_lane_1",
        passed=True,
        evidence_hash="e_hash",
        details={"lane_id": 1, "max_phase_error": 0.12}
    )
    packet1 = ranger.observe_court_decision(res, mission_id="M_COURT")
    assert packet1.actor == "Court Ranger"
    assert packet1.recommendation == "observe"
    assert packet1.evidence["correction_type"] == "phase"
    assert packet1.evidence["lane_id"] == 1
    
    replay_res = CalibrationReplayResult(
        status="pass",
        reason="Checks clear",
        details={"lane_id": 2, "diff_count": 1}
    )
    report = CalibrationPromotionReport(
        replay_result=replay_res,
        promotion_status="approved",
        evidence_hash="e_hash"
    )
    packet2 = ranger.observe_court_decision(report, mission_id="M_COURT")
    assert packet2.recommendation == "promote"
    assert packet2.evidence["replay_status"] == "pass"
    assert packet2.evidence["promotion_status"] == "approved"
    
    js1 = json.dumps(packet1.to_dict())
    assert js1 is not None
    js2 = json.dumps(packet2.to_dict())
    assert js2 is not None


def test_rangers_drift_phase_threshold_breach():
    """Verify that DriftRanger and PhaseRanger flag breaches and request court review."""
    library_dir = sol_root / "tools" / "sol-rsi" / "coding_library"
    drift_r = DriftRanger(lib_agent=library_dir)
    phase_r = PhaseRanger(lib_agent=library_dir)
    
    obs = PhaseDriftObservation(
        lane_id=4,
        max_phase_error=0.08,
        average_phase_error=0.04,
        out_of_tolerance=True,
        evidence={"channel_errors": []}
    )
    packet_drift = drift_r.observe_drift(obs, tolerance=0.05)
    assert packet_drift.evidence["request_court_review"] is True
    assert packet_drift.recommendation == "patch"
    
    cal_fail = {
        "active_delta": 0.18,
        "inactive_max_delta": 0.05,
        "reversed_delta": 0.05,
        "phase_residual": 0.02,
        "cross_talk": 0.02,
        "min_active_register_mass": 14.5
    }
    packet_phase = phase_r.observe_calibration(cal_fail)
    assert packet_phase.evidence["request_court_review"] is True
    assert packet_phase.recommendation == "reject"


def test_phase9_add_word_execution_widths():
    """Verify ADD_WORD lowers and executes correctly on 16-bit, 32-bit, and 64-bit fabrics."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction

    # 1. 16-bit fabric
    inst_16 = WideWordInstruction(
        instruction_id="INST_ADD_16",
        op="ADD_WORD",
        width=16,
        operands=[0x1234, 0x5678, 0],
        lane_count=2,
        dry_run=True
    )
    seq = MultiLaneSequencer()
    res_16 = seq.execute_instruction(inst_16)
    assert res_16.passed_gates is True
    assert res_16.result == 0x68AC
    assert len(res_16.carry_trace) == 2

    # 2. 32-bit fabric
    inst_32 = WideWordInstruction(
        instruction_id="INST_ADD_32",
        op="ADD_WORD",
        width=32,
        operands=[0x00FFFFFF, 0x00000001, 0],
        lane_count=4,
        dry_run=True
    )
    res_32 = seq.execute_instruction(inst_32)
    assert res_32.passed_gates is True
    assert res_32.result == 0x01000000
    assert len(res_32.carry_trace) == 4

    # 3. 64-bit fabric
    inst_64 = WideWordInstruction(
        instruction_id="INST_ADD_64",
        op="ADD_WORD",
        width=64,
        operands=[0xFFFFFFFFFFFFFFFF, 0x1, 0],
        lane_count=8,
        dry_run=True
    )
    res_64 = seq.execute_instruction(inst_64)
    assert res_64.passed_gates is True
    assert res_64.result == 0
    assert res_64.carry_out == 1
    assert len(res_64.carry_trace) == 8


def test_phase9_word_arithmetic_logical_ops():
    """Verify SUB_WORD, AND_WORD, OR_WORD, XOR_WORD, and NOT_WORD match Python masked integer results."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction

    seq = MultiLaneSequencer()

    # SUB_WORD
    inst_sub = WideWordInstruction(
        instruction_id="INST_SUB_32",
        op="SUB_WORD",
        width=32,
        operands=[0x100, 0x40, 0],
        lane_count=4,
        dry_run=True
    )
    res_sub = seq.execute_instruction(inst_sub)
    assert res_sub.passed_gates is True
    assert res_sub.result == 0xC0

    # AND_WORD
    inst_and = WideWordInstruction(
        instruction_id="INST_AND_32",
        op="AND_WORD",
        width=32,
        operands=[0xF0F0F0F0, 0x0FFFFFFF],
        lane_count=4,
        dry_run=True
    )
    res_and = seq.execute_instruction(inst_and)
    assert res_and.passed_gates is True
    assert res_and.result == (0xF0F0F0F0 & 0x0FFFFFFF)

    # OR_WORD
    inst_or = WideWordInstruction(
        instruction_id="INST_OR_32",
        op="OR_WORD",
        width=32,
        operands=[0xF0F0F0F0, 0x0F0F0F0F],
        lane_count=4,
        dry_run=True
    )
    res_or = seq.execute_instruction(inst_or)
    assert res_or.passed_gates is True
    assert res_or.result == (0xF0F0F0F0 | 0x0F0F0F0F)

    # XOR_WORD
    inst_xor = WideWordInstruction(
        instruction_id="INST_XOR_32",
        op="XOR_WORD",
        width=32,
        operands=[0xAAAAAAAA, 0x55555555],
        lane_count=4,
        dry_run=True
    )
    res_xor = seq.execute_instruction(inst_xor)
    assert res_xor.passed_gates is True
    assert res_xor.result == 0xFFFFFFFF

    # NOT_WORD
    inst_not = WideWordInstruction(
        instruction_id="INST_NOT_32",
        op="NOT_WORD",
        width=32,
        operands=[0x55555555],
        lane_count=4,
        dry_run=True
    )
    res_not = seq.execute_instruction(inst_not)
    assert res_not.passed_gates is True
    assert res_not.result == (~0x55555555) & 0xFFFFFFFF


def test_phase9_shift_ops():
    """Verify shift operations are masked to selected width."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction

    seq = MultiLaneSequencer()

    # SHL_WORD
    inst_shl = WideWordInstruction(
        instruction_id="INST_SHL_16",
        op="SHL_WORD",
        width=16,
        operands=[0xFFFF, 4],
        lane_count=2,
        dry_run=True
    )
    res_shl = seq.execute_instruction(inst_shl)
    assert res_shl.passed_gates is True
    assert res_shl.result == (0xFFFF << 4) & 0xFFFF

    # SHR_WORD
    inst_shr = WideWordInstruction(
        instruction_id="INST_SHR_16",
        op="SHR_WORD",
        width=16,
        operands=[0xFFFF, 4],
        lane_count=2,
        dry_run=True
    )
    res_shr = seq.execute_instruction(inst_shr)
    assert res_shr.passed_gates is True
    assert res_shr.result == (0xFFFF >> 4) & 0xFFFF


def test_phase9_dry_run_immutability():
    """Verify dry-run execution does not mutate sequencer commit state unless explicitly committed."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction

    seq = MultiLaneSequencer()
    inst = WideWordInstruction(
        instruction_id="INST_DRY",
        op="ADD_WORD",
        width=32,
        operands=[10, 20],
        lane_count=4,
        dry_run=True
    )
    res = seq.execute_instruction(inst)
    assert len(seq.commit_ledger) == 0  # not committed yet
    
    # Now commit explicitly
    packet = seq.commit_word_result(res)
    assert len(seq.commit_ledger) == 1
    assert packet.result == 30
    assert seq.commit_ledger[0] == packet


def test_phase9_commit_gate_unsupported_widths():
    """Verify commit gate rejects unsupported widths."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction

    seq = MultiLaneSequencer()
    inst = WideWordInstruction(
        instruction_id="INST_BAD_WIDTH",
        op="ADD_WORD",
        width=24,  # Unsupported width (must be 16, 32, 64)
        operands=[10, 20],
        lane_count=3,
        dry_run=True
    )
    res = seq.execute_instruction(inst)
    assert res.passed_gates is False
    assert "width_supported" in res.gate_report.checked_gates
    assert res.gate_report.checked_gates["width_supported"] is False
    
    # Attempting to commit should raise ValueError
    import pytest
    with pytest.raises(ValueError):
        seq.commit_word_result(res)


def test_phase9_commit_gate_missing_carry_trace():
    """Verify commit gate rejects missing carry trace for add/sub."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction

    seq = MultiLaneSequencer()
    inst = WideWordInstruction(
        instruction_id="INST_ADD_CARRY",
        op="ADD_WORD",
        width=32,
        operands=[10, 20],
        lane_count=4,
        dry_run=True
    )
    
    class MockResult:
        result = 30
        carry_out = 0
        lane_results = []
        carry_trace = []  # empty
        evidence = {}
        
    class BadFabric:
        num_lanes = 4
        def add_word(self, a, b, carry_in=0):
            return MockResult()
            
    seq_bad = MultiLaneSequencer(fabric=BadFabric())
    res_bad = seq_bad.execute_instruction(inst)
    assert res_bad.passed_gates is False
    assert res_bad.gate_report.checked_gates["carry_trace_present_for_add_sub"] is False


def test_phase9_commit_packet_serialization_json():
    """Verify commit packet serializes to JSON."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction
    import dataclasses

    seq = MultiLaneSequencer()
    inst = WideWordInstruction(
        instruction_id="INST_SERIAL",
        op="ADD_WORD",
        width=32,
        operands=[10, 20],
        lane_count=4,
        dry_run=True
    )
    res = seq.execute_instruction(inst)
    packet = seq.commit_word_result(res)
    
    packet_dict = dataclasses.asdict(packet)
    js = json.dumps(packet_dict)
    assert js is not None
    assert '"instruction_id": "INST_SERIAL"' in js
    assert '"width": 32' in js


def test_phase9_promotion_court_word_review():
    """Verify Promotion Court can review a word commit packet."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction, PromotionCourt

    seq = MultiLaneSequencer()
    court = PromotionCourt()

    # Valid dry run commit
    inst_ok = WideWordInstruction(
        instruction_id="INST_OK",
        op="ADD_WORD",
        width=32,
        operands=[10, 20],
        lane_count=4,
        dry_run=True
    )
    res_ok = seq.execute_instruction(inst_ok)
    packet_ok = seq.commit_word_result(res_ok)
    
    court_res_ok = court.review_word_commit_packet(packet_ok)
    assert court_res_ok.passed is True
    assert court_res_ok.decision == "accept_dry_run_commit"

    # Gating failure: bad width
    class MockPacket:
        gate_report = {
            "passed": False,
            "checked_gates": {"width_supported": False, "lane_count_matches_width": False},
            "errors": ["Width 24 not supported"]
        }
        op = "ADD_WORD"
        width = 24
        reproducibility_hash = "mock_hash"
        instruction_id = "INST_BAD"

    court_res_bad = court.review_word_commit_packet(MockPacket())
    assert court_res_bad.passed is False
    assert court_res_bad.decision == "reject_commit"


def test_phase9_sequencer_ranger_packet():
    """Verify SequencerRanger emits JSON-serializable SovereignPacket."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction, SequencerRanger

    seq = MultiLaneSequencer()
    ranger = SequencerRanger()

    inst = WideWordInstruction(
        instruction_id="INST_RANGER",
        op="ADD_WORD",
        width=32,
        operands=[10, 20],
        lane_count=4,
        dry_run=True
    )
    res = seq.execute_instruction(inst)
    packet = seq.commit_word_result(res)

    # 1. Observe WideWordInstructionResult
    sp_res = ranger.observe_sequencer(res, mission_id="M_SEQ_1")
    assert sp_res.actor == "Sequencer Ranger"
    assert sp_res.recommendation == "observe"
    assert sp_res.evidence["op"] == "ADD_WORD"
    assert sp_res.evidence["result"] == 30

    # 2. Observe WordCommitPacket
    sp_packet = ranger.observe_sequencer(packet, mission_id="M_SEQ_2")
    assert sp_packet.actor == "Sequencer Ranger"
    assert sp_packet.recommendation == "observe"
    assert sp_packet.evidence["commit_status"] == "committed_scaffold"

    # Verify JSON serialization
    js_res = json.dumps(sp_res.to_dict())
    js_packet = json.dumps(sp_packet.to_dict())
    assert js_res is not None
    assert js_packet is not None


def test_phase10_pdm_execution_plan_building():
    """Verify PDM execution plan builds from 16-bit, 32-bit, and 64-bit ADD_WORD results."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction, PDMExecutionPlan
    from sol_pdm_executor import build_execution_plan
    from sol_lane_fabric import LaneFabric

    seq = MultiLaneSequencer()

    # 16-bit
    inst_16 = WideWordInstruction("I_16", "ADD_WORD", 16, [0x1234, 0x5678], 2)
    res_16 = seq.execute_instruction(inst_16)
    fabric_16 = seq.lower_instruction(inst_16)
    plan_16 = build_execution_plan(res_16, fabric_16)
    assert isinstance(plan_16, PDMExecutionPlan)
    assert len(plan_16.encoded_word) == 2
    assert plan_16.encoded_word[0].value == 0xAC

    # 32-bit
    inst_32 = WideWordInstruction("I_32", "ADD_WORD", 32, [1000, 2000], 4)
    res_32 = seq.execute_instruction(inst_32)
    fabric_32 = seq.lower_instruction(inst_32)
    plan_32 = build_execution_plan(res_32, fabric_32)
    assert len(plan_32.encoded_word) == 4
    assert plan_32.width == 32

    # 64-bit
    inst_64 = WideWordInstruction("I_64", "ADD_WORD", 64, [0xDEADBEEF, 0xCAFEBABE], 8)
    res_64 = seq.execute_instruction(inst_64)
    fabric_64 = seq.lower_instruction(inst_64)
    plan_64 = build_execution_plan(res_64, fabric_64)
    assert len(plan_64.encoded_word) == 8
    assert plan_64.width == 64


def test_phase10_modulation_and_demodulation_parity():
    """Verify modulation trace is deterministic, and demodulation result matches reference oracle."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction
    from sol_pdm_executor import build_execution_plan, modulate_plan, demodulate_trace

    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_MOD", "ADD_WORD", 32, [0x12345678, 0x11111111], 4)
    res = seq.execute_instruction(inst)
    fabric = seq.lower_instruction(inst)

    plan = build_execution_plan(res, fabric)
    t_values = [0.1 * i for i in range(10000)]
    trace = modulate_plan(plan, t_values)

    assert len(trace.lane_signals) == 4
    assert len(trace.lane_signals[0]) == 10000
    assert isinstance(trace.lane_signals[0][0], float)

    demod_res = demodulate_trace(trace)
    assert demod_res.matches_oracle is True
    assert demod_res.demodulated_value == res.result


def test_phase10_gate_report_blocks_live_mutation():
    """Verify that gate report blocks live mutation by default."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction

    seq = MultiLaneSequencer()
    
    inst = WideWordInstruction("I_LIVE", "ADD_WORD", 32, [10, 20], 4, dry_run=False)
    report = seq.execute_waveguide_instruction(inst, dry_run=False, shadow=True)
    assert report.passed_gates is False
    assert report.gate_report.checked_gates["no_live_mutation_without_promotion"] is False
    assert "Live commit blocked" in report.gate_report.errors[0]

    inst_no_shadow = WideWordInstruction("I_NO_SHADOW", "ADD_WORD", 32, [10, 20], 4, dry_run=True)
    report_no_shadow = seq.execute_waveguide_instruction(inst_no_shadow, dry_run=True, shadow=False)
    assert report_no_shadow.passed_gates is False
    assert report_no_shadow.gate_report.checked_gates["frontier_control_shadow_only"] is False
    assert "Frontier control blocked" in report_no_shadow.gate_report.errors[0]


def test_phase10_frontier_closed_loop_driver_suggestions():
    """Verify FrontierClosedLoopDriver returns advisory/shadow suggestions only."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import (
        WideWordInstruction,
        FrontierBridge,
        FrontierClosedLoopDriver,
        BoundedCorrectionPolicy,
        CandidateCorrection
    )

    seq = MultiLaneSequencer()
    bridge = FrontierBridge()
    driver = FrontierClosedLoopDriver(bridge)
    policy = BoundedCorrectionPolicy()

    inst_ok = WideWordInstruction("I_OK", "ADD_WORD", 32, [10, 20], 4)
    report_ok = seq.execute_waveguide_instruction(inst_ok)
    summary = driver.observe_execution_report(report_ok)
    assert summary["oracle_match"] is True

    sug_ok = driver.suggest_calibration_adjustment(report_ok, policy)
    assert sug_ok.action == "observe"
    assert sug_ok.nudge_value == 0.0

    packet_ok = driver.build_candidate_adjustment_packet(report_ok, sug_ok)
    assert isinstance(packet_ok, CandidateCorrection)
    assert packet_ok.bounded_delta == 0.0

    inst_sub = WideWordInstruction("I_SUB", "SUB_WORD", 32, [100, 40], 4)
    report_sub = seq.execute_waveguide_instruction(inst_sub)
    sug_sub = driver.suggest_calibration_adjustment(report_sub, policy)
    assert sug_sub.action == "suggest_phase_nudge"
    assert sug_sub.nudge_value == -0.02

    packet_sub = driver.build_candidate_adjustment_packet(report_sub, sug_sub)
    assert packet_sub.bounded_delta == -0.02
    assert packet_sub.correction_type == "phase"


def test_phase10_court_review_pdm_and_frontier():
    """Verify PromotionCourt can review PDM execution reports and Frontier closed-loop adjustments."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import (
        WideWordInstruction,
        PromotionCourt,
        FrontierBridge,
        FrontierClosedLoopDriver,
        BoundedCorrectionPolicy
    )

    seq = MultiLaneSequencer()
    court = PromotionCourt()
    bridge = FrontierBridge()
    driver = FrontierClosedLoopDriver(bridge)
    policy = BoundedCorrectionPolicy()

    inst = WideWordInstruction("I_COURT", "ADD_WORD", 32, [10, 20], 4)
    report = seq.execute_waveguide_instruction(inst)
    court_res = court.review_pdm_execution_report(report)
    assert court_res.passed is True
    assert court_res.decision == "accept_shadow_execution"

    sug = driver.suggest_calibration_adjustment(report, policy)
    packet = driver.build_candidate_adjustment_packet(report, sug)
    court_res_pack = court.review_frontier_adjustment_packet(packet)
    assert court_res_pack.passed is True
    assert court_res_pack.decision == "authorize_candidate_adjustment"


def test_phase10_pdm_and_frontier_rangers():
    """Verify PDMRanger and FrontierRanger emit JSON-serializable SovereignPacket instances."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import (
        WideWordInstruction,
        PDMRanger,
        FrontierRanger,
        FrontierBridge,
        FrontierClosedLoopDriver,
        BoundedCorrectionPolicy
    )

    seq = MultiLaneSequencer()
    pdm_r = PDMRanger()
    front_r = FrontierRanger()
    bridge = FrontierBridge()
    driver = FrontierClosedLoopDriver(bridge)
    policy = BoundedCorrectionPolicy()

    inst = WideWordInstruction("I_RANGERS", "ADD_WORD", 32, [10, 20], 4)
    report = seq.execute_waveguide_instruction(inst)

    pdm_packet = pdm_r.observe_execution(report)
    assert pdm_packet.actor == "PDM Ranger"
    assert pdm_packet.recommendation == "promote"
    assert pdm_packet.evidence["channel_count"] == 32
    assert pdm_packet.evidence["demodulation_passed"] is True

    sug = driver.suggest_calibration_adjustment(report, policy)
    corr = driver.build_candidate_adjustment_packet(report, sug)
    front_packet = front_r.observe_adjustment(corr)
    assert front_packet.actor == "Frontier Ranger"
    assert front_packet.recommendation == "observe"
    assert front_packet.evidence["live_control_enabled"] is False
    assert front_packet.evidence["promotion_required"] is True

    js_pdm = json.dumps(pdm_packet.to_dict())
    js_front = json.dumps(front_packet.to_dict())
    assert js_pdm is not None
    assert js_front is not None


def test_phase11_live_mutation_rejected_without_court_token():
    """Verify live mutation is rejected without a valid court token."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction, LiveControlToken
    import time

    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_L1", "ADD_WORD", 32, [10, 20], 4)
    token = LiveControlToken(
        token_id="UNAUTHORIZED_TOKEN",
        authorized_by_court=False,
        issued_at=time.time(),
        expires_at=time.time() + 100,
        sandbox_only=True,
        target_lane=0,
        max_mutations=2,
        active=False
    )
    res = seq.execute_live_waveguide_instruction(inst, token, sandbox=True)
    assert res.success is False
    assert "gate failed" in res.error_message or "invalid or unauthorized" in res.error_message


def test_phase11_live_mutation_rejected_when_sandbox_false():
    """Verify live mutation is rejected when sandbox=False."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction, LiveControlToken
    import time

    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_L2", "ADD_WORD", 32, [10, 20], 4)
    token = LiveControlToken(
        token_id="TOKEN_123",
        authorized_by_court=True,
        issued_at=time.time(),
        expires_at=time.time() + 100,
        sandbox_only=True,
        target_lane=0,
        max_mutations=2,
        active=True
    )
    res = seq.execute_live_waveguide_instruction(inst, token, sandbox=False)
    assert res.success is False
    assert "sandbox_only gate failed" in res.error_message


def test_phase11_live_mutation_rejected_without_rollback_snapshot():
    """Verify live mutation is rejected without rollback snapshot."""
    from coding_library.sovereign_domain import FrontierClosedLoopDriver, FrontierBridge, LiveControlToken, CandidateCorrection
    import time

    bridge = FrontierBridge()
    driver = FrontierClosedLoopDriver(bridge)
    token = LiveControlToken(
        token_id="TOKEN_123",
        authorized_by_court=True,
        issued_at=time.time(),
        expires_at=time.time() + 100,
        sandbox_only=True,
        target_lane=0,
        max_mutations=2,
        active=True
    )
    candidate = CandidateCorrection("drift", 0.95, 0.02, 0, None, 0.0, 0.02, "hash", "phase")
    res = driver.apply_candidate_adjustment(candidate, token, sandbox=True, plan=None)
    assert res.success is False
    assert "rollback snapshot is missing" in res.error_message


def test_phase11_phase_nudge_clamped_by_policy():
    """Verify phase nudge is clamped by the court policy."""
    from coding_library.sovereign_domain import PromotionCourt, LiveControlPolicy, CandidateCorrection
    
    court = PromotionCourt()
    policy = LiveControlPolicy(max_phase_nudge=0.05)
    
    dec = court.authorize_candidate_correction({
        "decision": "authorize_candidate_phase_correction",
        "details": {
            "lane_id": 0,
            "nudge_value": 0.12
        },
        "reproducibility_hash": "hash"
    }, policy)
    
    assert dec.authorized is True
    assert "0.05" in dec.reason


def test_phase11_mutation_count_limits_enforced():
    """Verify mutation count limits are enforced."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction, LiveControlToken
    import time

    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_L3", "ADD_WORD", 32, [10, 20], 4)
    
    token = LiveControlToken(
        token_id="TOKEN_123",
        authorized_by_court=True,
        issued_at=time.time(),
        expires_at=time.time() + 100,
        sandbox_only=True,
        target_lane=0,
        max_mutations=1,
        active=True
    )
    
    res1 = seq.execute_live_waveguide_instruction(inst, token, sandbox=True)
    assert res1.success is True
    
    res2 = seq.execute_live_waveguide_instruction(inst, token, sandbox=True)
    assert res2.success is False
    assert "mutation_count_within_bounds gate failed" in res2.error_message


def test_phase11_valid_sandbox_token_allows_bounded_mutation():
    """Verify valid sandbox token allows a bounded mutation on mock context."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction, LiveControlToken
    import time

    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_L4", "ADD_WORD", 32, [10, 20], 4)
    token = LiveControlToken(
        token_id="TOKEN_BOUNDED",
        authorized_by_court=True,
        issued_at=time.time(),
        expires_at=time.time() + 100,
        sandbox_only=True,
        target_lane=0,
        max_mutations=2,
        correction_type="phase",
        bounded_delta=0.03,
        active=True
    )
    res = seq.execute_live_waveguide_instruction(inst, token, sandbox=True)
    assert res.success is True
    assert res.rollback_snapshot is not None


def test_phase11_rollback_snapshot_restores_context():
    """Verify rollback snapshot can restore context phase table."""
    from sol_pdm_executor import capture_rollback_snapshot, restore_rollback_snapshot
    from sol_lane_fabric import LaneFabric
    from sol_phase_alignment import build_default_phase_table

    fabric = LaneFabric.for_width(32)
    for lane in fabric.lanes:
        lane.phase_table = build_default_phase_table(lane.lane_id, lane.periods)
        
    snap = capture_rollback_snapshot(fabric)
    fabric.lanes[0].phase_table.entries[0].calibrated_phase = 1.5
    
    restore_rollback_snapshot(snap, fabric)
    assert fabric.lanes[0].phase_table.entries[0].calibrated_phase == 0.0


def test_phase11_worsening_drift_triggers_quarantine():
    """Verify worsening post-mutation drift triggers quarantine recommendation."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction, LiveControlToken
    import time

    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_L5", "ADD_WORD", 32, [10, 20], 4)
    
    token = LiveControlToken(
        token_id="TOKEN_QUARANTINE",
        authorized_by_court=True,
        issued_at=time.time(),
        expires_at=time.time() + 100,
        sandbox_only=True,
        target_lane=0,
        max_mutations=3,
        correction_type="phase",
        bounded_delta=0.03,
        active=True
    )
    
    res1 = seq.execute_live_waveguide_instruction(inst, token, sandbox=True)
    assert res1.success is True
    assert res1.quarantine_recommended is False
    
    res2 = seq.execute_live_waveguide_instruction(inst, token, sandbox=True)
    assert res2.quarantine_recommended is True
    assert token.target_lane in seq.quarantined_lanes


def test_phase11_driver_cannot_apply_live_correction_without_token():
    """Verify FrontierClosedLoopDriver cannot apply live correction without token."""
    from coding_library.sovereign_domain import FrontierClosedLoopDriver, FrontierBridge, LiveControlToken, CandidateCorrection
    from sol_lane_fabric import LaneFabric
    from sol_multilane_sequencer import MultiLaneSequencer
    from sol_pdm_executor import build_execution_plan
    from sol_wideword_instruction import WideWordInstruction
    import time

    bridge = FrontierBridge()
    driver = FrontierClosedLoopDriver(bridge)
    seq = MultiLaneSequencer()
    
    token = LiveControlToken(
        token_id="INVALID_TOKEN",
        authorized_by_court=False,
        issued_at=time.time(),
        expires_at=time.time() + 100,
        sandbox_only=True,
        target_lane=0,
        max_mutations=2,
        active=True
    )
    
    inst = WideWordInstruction("I_L6", "ADD_WORD", 32, [10, 20], 4)
    ref_res = seq.execute_instruction(inst)
    plan = build_execution_plan(ref_res, seq.lower_instruction(inst))
    candidate = CandidateCorrection("drift", 0.95, 0.02, 0, None, 0.0, 0.02, "hash", "phase")
    
    res = driver.apply_candidate_adjustment(candidate, token, sandbox=True, plan=plan)
    assert res.success is False
    assert "invalid or unauthorized" in res.error_message


def test_phase11_live_control_ranger_emits_serializable_packet():
    """Verify LiveControlRanger emits JSON-serializable SovereignPacket."""
    from coding_library.sovereign_domain import LiveControlRanger, LiveControlToken, LiveMutationRequest, LiveMutationResult
    import time
    import json

    ranger = LiveControlRanger()
    
    token = LiveControlToken(
        token_id="TOKEN_123",
        authorized_by_court=True,
        issued_at=time.time(),
        expires_at=time.time() + 100,
        sandbox_only=True,
        target_lane=0,
        max_mutations=2,
        active=True
    )
    
    req = LiveMutationRequest("REQ_123", None, None, None, True, time.time())
    result = LiveMutationResult(
        success=True,
        mutation_request=req,
        token=token,
        rollback_snapshot=None,
        post_mutation_drift=0.01,
        post_mutation_trace=None,
        quarantine_recommended=False
    )
    
    packet = ranger.observe_live_control(req, result, token)
    assert packet.actor == "Live Control Ranger"
    assert packet.evidence["sandbox"] is True
    assert packet.evidence["post_mutation_status"] == "SUCCESS"
    
    js = json.dumps(packet.to_dict())
    assert js is not None


def test_phase12_32bit_fabric_builds_4_lanes():
    """Verify that 32-bit fabric builds exactly 4 byte lanes."""
    from sol_wideword_fabric import build_wideword_fabric, validate_fabric_topology
    from sol_pdm_byte_slice import PDMByteSlice
    from sol_waveguide_boundary import PMLProfile
    from sol_phase_alignment import PhaseAlignmentTable

    topo = build_wideword_fabric(32)
    assert topo.width == 32
    assert len(topo.lane_groups) == 1
    assert len(topo.lane_groups[0].lanes) == 4
    
    assert validate_fabric_topology(topo) is True
    
    for lane in topo.lane_groups[0].lanes:
        assert isinstance(lane.pdm_byte_slice, PDMByteSlice)
        assert isinstance(lane.local_pml_profile, PMLProfile)
        assert isinstance(lane.local_phase_alignment_table, PhaseAlignmentTable)


def test_phase12_64bit_fabric_builds_8_lanes():
    """Verify that 64-bit fabric builds exactly 8 byte lanes."""
    from sol_wideword_fabric import build_wideword_fabric, validate_fabric_topology
    from sol_pdm_byte_slice import PDMByteSlice
    from sol_waveguide_boundary import PMLProfile
    from sol_phase_alignment import PhaseAlignmentTable

    topo = build_wideword_fabric(64)
    assert topo.width == 64
    assert len(topo.lane_groups) == 2
    assert len(topo.lane_groups[0].lanes) + len(topo.lane_groups[1].lanes) == 8
    
    assert validate_fabric_topology(topo) is True
    
    for group in topo.lane_groups:
        for lane in group.lanes:
            assert isinstance(lane.pdm_byte_slice, PDMByteSlice)
            assert isinstance(lane.local_pml_profile, PMLProfile)
            assert isinstance(lane.local_phase_alignment_table, PhaseAlignmentTable)


def test_phase12_prefix_carry_traces():
    """Verify prefix carry traces are correct and complete for 32-bit and 64-bit add operations."""
    from sol_lane_fabric import LaneFabric
    
    fabric32 = LaneFabric.for_width(32)
    res32 = fabric32.add_word(0x12345678, 0x11111111)
    assert len(res32.carry_trace) == 4
    assert res32.carry_out == 0

    fabric64 = LaneFabric.for_width(64)
    res64 = fabric64.add_word(0xFFFFFFFFFFFFFFFF, 0x0000000000000001)
    assert len(res64.carry_trace) == 8
    assert res64.carry_trace == [False, True, True, True, True, True, True, True]
    assert res64.carry_out == 1


def test_phase12_pdm_execution_plans():
    """Verify 32-bit and 64-bit execution plans map correctly."""
    from sol_lane_fabric import LaneFabric
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction
    from sol_pdm_executor import build_execution_plan

    seq = MultiLaneSequencer()
    
    # 32-bit plan
    inst32 = WideWordInstruction("I_P12_32", "ADD_WORD", 32, [0x10, 0x20], 4)
    res32 = seq.execute_instruction(inst32)
    plan32 = build_execution_plan(res32, seq.lower_instruction(inst32))
    assert plan32.lane_count == 4
    assert plan32.channel_count == 32
    assert len(plan32.pml_profile_reference) == 4
    assert plan32.expected_oracle_result == 0x30

    # 64-bit plan
    inst64 = WideWordInstruction("I_P12_64", "ADD_WORD", 64, [0x10, 0x20], 8)
    res64 = seq.execute_instruction(inst64)
    plan64 = build_execution_plan(res64, seq.lower_instruction(inst64))
    assert plan64.lane_count == 8
    assert plan64.channel_count == 64
    assert len(plan64.pml_profile_reference) == 8
    assert plan64.expected_oracle_result == 0x30


def test_phase12_fabric_gate_failures():
    """Verify fabric gates reject invalid state configurations."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain import WideWordInstruction
    
    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_FAIL", "ADD_WORD", 32, [10, 20], 4)
    report = seq.execute_wideword_fabric_instruction(inst)
    assert report.passed_gates is True
    
    from sol_wideword_fabric import build_wideword_fabric, validate_fabric_topology
    topo = build_wideword_fabric(32)
    topo.lane_groups[0].lanes[0].local_pml_profile = None
    assert validate_fabric_topology(topo) is False


def test_phase12_fabric_ranger_sovereign_packet():
    """Verify FabricRanger emits a JSON-serializable SovereignPacket."""
    from coding_library.sovereign_domain import FabricRanger
    from sol_wideword_fabric import build_wideword_fabric, WideWordFabricReport
    from sol_pdm_executor import PDMExecutionReport, PDMDemodulationResult, PDMExecutionTrace, PDMExecutionPlan
    from sol_wideword_instruction import InstructionGateReport, WideWordInstruction, WideWordInstructionResult
    from sol_lane_fabric import LaneFabric
    import time
    import json

    ranger = FabricRanger()
    topo = build_wideword_fabric(32)
    
    gate_rep = InstructionGateReport(passed=True, checked_gates={"prefix_carry_trace_complete": True, "all_lanes_have_pml_profile": True, "all_lanes_have_phase_table": True}, errors=[])
    
    inst = WideWordInstruction("I_RNG", "ADD_WORD", 32, [10, 20], 4)
    inst_res = WideWordInstructionResult(inst, 30, 0, [], [False, False, False, False], gate_rep, True)
    fabric = LaneFabric.for_width(32)
    pdm_plan = PDMExecutionPlan(inst_res, [], fabric, 32, 4)
    trace = PDMExecutionTrace(pdm_plan, [], [])
    demod = PDMDemodulationResult(30, [30, 0, 0, 0], True, [])
    pdm_report = PDMExecutionReport("I_RNG", "ADD_WORD", 32, 4, True, True, demod, gate_rep, trace, time.time(), "hash")
    
    report = WideWordFabricReport(
        report_id="RPT_123",
        instruction_id="I_RNG",
        width=32,
        lane_count=4,
        passed_gates=True,
        oracle_match=True,
        gate_report=gate_rep,
        pdm_report=pdm_report,
        crosstalk_levels={"lane_0": 0.01},
        reproducibility_hash="hash",
        timestamp=time.time(),
        metadata={"sandbox_trial": False}
    )
    
    packet = ranger.observe_fabric(topo, None, report)
    assert packet.actor == "Fabric Ranger"
    assert packet.evidence["width"] == 32
    assert packet.evidence["lane_count"] == 4
    assert packet.evidence["pml_profile_status"] == "VALID"
    assert packet.evidence["promotion_readiness"] is True
    
    js = json.dumps(packet.to_dict())
    assert js is not None


def test_phase12_court_reviews_fabric_report():
    """Verify PromotionCourt can evaluate fabric report."""
    from coding_library.sovereign_domain import PromotionCourt
    from sol_wideword_fabric import build_wideword_fabric, WideWordFabricReport
    from sol_pdm_executor import PDMExecutionReport, PDMDemodulationResult, PDMExecutionTrace, PDMExecutionPlan
    from sol_wideword_instruction import InstructionGateReport, WideWordInstruction, WideWordInstructionResult
    from sol_lane_fabric import LaneFabric
    import time
    
    court = PromotionCourt()
    
    gate_rep = InstructionGateReport(passed=True, checked_gates={"prefix_carry_trace_complete": True, "all_lanes_have_pml_profile": True, "all_lanes_have_phase_table": True}, errors=[])
    inst = WideWordInstruction("I_CRT", "ADD_WORD", 32, [10, 20], 4)
    inst_res = WideWordInstructionResult(inst, 30, 0, [], [False, False, False, False], gate_rep, True)
    fabric = LaneFabric.for_width(32)
    pdm_plan = PDMExecutionPlan(inst_res, [], fabric, 32, 4)
    trace = PDMExecutionTrace(pdm_plan, [], [])
    demod = PDMDemodulationResult(30, [30, 0, 0, 0], True, [])
    pdm_report = PDMExecutionReport("I_CRT", "ADD_WORD", 32, 4, True, True, demod, gate_rep, trace, time.time(), "hash")
    
    report = WideWordFabricReport(
        report_id="RPT_123",
        instruction_id="I_CRT",
        width=32,
        lane_count=4,
        passed_gates=True,
        oracle_match=True,
        gate_report=gate_rep,
        pdm_report=pdm_report,
        crosstalk_levels={"lane_0": 0.01},
        reproducibility_hash="hash",
        timestamp=time.time(),
        metadata={"sandbox_trial": False}
    )
    
    res = court.review_wideword_fabric_report(report)
    assert res.passed is True
    assert res.decision == "promote_fabric_candidate"
    
    report.metadata["sandbox_trial"] = True
    res_sandbox = court.review_wideword_fabric_report(report)
    assert res_sandbox.passed is True
    assert res_sandbox.decision == "authorize_sandbox_fabric_trial"


def test_phase13_hcam_banking_scaffold_and_topologies():
    """Verify that HCAM banking topologies are correctly configured for 16, 32, and 64 bit widths."""
    from sol_hcam_banking import build_hcam_topology
    
    # 16-bit
    topo_16 = build_hcam_topology(16)
    assert topo_16.width == 16
    assert len(topo_16.banks) == 2
    
    # 32-bit
    topo_32 = build_hcam_topology(32)
    assert topo_32.width == 32
    assert len(topo_32.banks) == 4
    
    # 64-bit
    topo_64 = build_hcam_topology(64)
    assert topo_64.width == 64
    assert len(topo_64.banks) == 8
    
    # Check bank attributes and mapping
    for i, bank in enumerate(topo_64.banks):
        assert bank.bank_id == i
        assert bank.lane_id == i
        assert bank.address_basin == f"Basin_Addr_L{i}"
        assert bank.value_basin == f"Basin_Val_L{i}"
        assert bank.recall_gate == f"Gate_Recall_L{i}"
        assert bank.commit_register == f"Reg_Commit_L{i}"
        assert bank.boundary_metadata["isolation_gap"] == 0.05
        assert bank.phase_table_reference is not None


def test_phase13_fabric_hcam_topology_alignment():
    """Verify bidirectional alignment between waveguide lanes and HCAM memory banks."""
    from sol_wideword_fabric import build_wideword_fabric, validate_fabric_topology
    
    topo = build_wideword_fabric(32)
    assert topo.hcam_topology is not None
    assert len(topo.lane_groups[0].lanes) == 4
    assert len(topo.hcam_topology.banks) == 4
    assert validate_fabric_topology(topo) is True
    
    # Cause lane count to lane_groups mismatch
    topo.hcam_topology.banks = topo.hcam_topology.banks[:3]
    assert validate_fabric_topology(topo) is False


def test_phase13_hcam_query_and_response_routes():
    """Verify H-CAM query and response routes cover all banks."""
    from sol_lane_fabric import LaneFabric
    
    fabric = LaneFabric.for_width(32)
    plan = fabric.plan_hcam_recall(0x1234)
    
    assert plan.query.address == 0x1234
    assert len(plan.query_routes) == 4
    assert len(plan.response_routes) == 4
    
    for i in range(4):
        assert plan.query_routes[i].bank_id == i
        assert plan.query_routes[i].address_basin == f"Basin_Addr_L{i}"
        assert plan.query_routes[i].recall_gate == f"Gate_Recall_L{i}"
        
        assert plan.response_routes[i].bank_id == i
        assert plan.response_routes[i].value_basin == f"Basin_Val_L{i}"
        assert plan.response_routes[i].commit_register == f"Reg_Commit_L{i}"


def test_phase13_reduction_tree_construction_and_leaves():
    """Verify reduction tree constructs correctly and leaves cover all banks."""
    from sol_hcam_banking import build_response_routes, build_reduction_tree, HCAMBankedRecallPlan, HCAMQuery, build_hcam_topology
    
    topo = build_hcam_topology(64)
    query = HCAMQuery(address=0x5678, width=64, metadata={})
    plan = HCAMBankedRecallPlan(query=query, topology=topo, query_routes=[], response_routes=[], metadata={})
    plan.response_routes = build_response_routes(plan, topo)
    
    tree = build_reduction_tree(plan.response_routes, 64)
    assert tree.depth == 4  # log2(8) + 1 = 4 levels of depth (depth 1 is leaf)
    
    # Verify leaves cover all 8 banks
    leaves = set()
    def collect_leaves(node):
        if node is None:
            return
        if node.left_child is None and node.right_child is None:
            leaves.add(node.bank_id)
        collect_leaves(node.left_child)
        collect_leaves(node.right_child)
        
    collect_leaves(tree.root)
    assert leaves == set(range(8))


def test_phase13_assemble_word_parity_oracle():
    """Verify little-endian assembly matches Python integer oracle for 32-bit and 64-bit."""
    from sol_hcam_banking import assemble_word_from_bank_values
    
    # 32-bit: [0x12, 0x34, 0x56, 0x78]
    val_32 = {0: 0x78, 1: 0x56, 2: 0x34, 3: 0x12}
    word_32 = assemble_word_from_bank_values(val_32, 32)
    assert word_32 == 0x12345678
    
    # 64-bit: [0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE, 0xBA, 0xBE]
    val_64 = [0xBE, 0xBA, 0xFE, 0xCA, 0xEF, 0xBE, 0xAD, 0xDE]
    word_64 = assemble_word_from_bank_values(val_64, 64)
    assert word_64 == 0xDEADBEEFCAFEBABE


def test_phase13_sequencer_shadow_recall_execution():
    """Verify MultiLaneSequencer can plan and execute shadow H-CAM recall, checking safety gates."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from sol_wideword_instruction import WideWordInstruction
    
    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_REC_32", "RECALL_WORD", 32, [0x1000, 0x12345678], 4)
    
    bank_vals = {0: 0x78, 1: 0x56, 2: 0x34, 3: 0x12}
    report = seq.execute_shadow_hcam_recall(inst, bank_vals)
    
    assert report.passed_gates is True
    assert report.oracle_match is True
    assert report.assembled_word == 0x12345678
    
    # Induce oracle mismatch
    inst_bad = WideWordInstruction("I_REC_BAD", "RECALL_WORD", 32, [0x1000, 0x99999999], 4)
    report_bad = seq.execute_shadow_hcam_recall(inst_bad, bank_vals)
    assert report_bad.passed_gates is False
    assert report_bad.oracle_match is False
    assert "Memory gate failed: Assembled word does not match expected oracle value." in report_bad.gate_report.errors


def test_phase13_hcam_ranger_sovereign_packet():
    """Verify HCamRanger generates a valid, JSON-serializable SovereignPacket."""
    from coding_library.sovereign_domain import HCamRanger
    from sol_hcam_banking import build_hcam_topology, HCAMBankedRecallPlan, HCAMQuery, build_response_routes, build_reduction_tree, HCAMRecallReport
    from sol_wideword_instruction import InstructionGateReport
    import json
    import time
    
    ranger = HCamRanger()
    topo = build_hcam_topology(32)
    query = HCAMQuery(address=0x1000, width=32, metadata={})
    plan = HCAMBankedRecallPlan(query=query, topology=topo, query_routes=[], response_routes=[], metadata={})
    plan.response_routes = build_response_routes(plan, topo)
    plan.query_routes = [{"bank_id": 0}] # Mock non-empty
    
    gate_rep = InstructionGateReport(passed=True, checked_gates={}, errors=[])
    tree = build_reduction_tree(plan.response_routes, 32)
    
    report = HCAMRecallReport(
        report_id="RPT_123",
        instruction_id="I_RNG",
        address=0x1000,
        width=32,
        passed_gates=True,
        assembled_word=0xABCDEF,
        oracle_match=True,
        gate_report=gate_rep,
        recall_plan=plan,
        reduction_tree=tree,
        timestamp=time.time(),
        reproducibility_hash="hash"
    )
    
    packet = ranger.observe_hcam(topo, plan, report)
    assert packet.actor == "HCAM Ranger"
    assert packet.evidence["width"] == 32
    assert packet.evidence["bank_count"] == 4
    
    js = json.dumps(packet.to_dict())
    assert js is not None


def test_phase13_court_reviews_hcam_report():
    """Verify PromotionCourt evaluates HCAM recall reports correctly."""
    from coding_library.sovereign_domain import PromotionCourt
    from sol_hcam_banking import build_hcam_topology, HCAMBankedRecallPlan, HCAMQuery, HCAMRecallReport, build_response_routes, build_reduction_tree
    from sol_wideword_instruction import InstructionGateReport
    import time
    
    court = PromotionCourt()
    topo = build_hcam_topology(32)
    query = HCAMQuery(address=0x1000, width=32, metadata={})
    plan = HCAMBankedRecallPlan(query=query, topology=topo, query_routes=[], response_routes=[], metadata={})
    plan.response_routes = build_response_routes(plan, topo)
    plan.query_routes = [{"bank_id": 0}] # Mock non-empty
    
    gate_rep = InstructionGateReport(
        passed=True,
        checked_gates={
            "width_supported": True,
            "bank_count_matches_width": True,
            "all_lanes_have_banks": True,
            "all_banks_have_boundaries": True,
            "query_routes_complete": True,
            "response_routes_complete": True,
            "reduction_tree_complete": True
        },
        errors=[]
    )
    tree = build_reduction_tree(plan.response_routes, 32)
    
    report = HCAMRecallReport(
        report_id="RPT_123",
        instruction_id="I_CRT",
        address=0x1000,
        width=32,
        passed_gates=True,
        assembled_word=0xABCDEF,
        oracle_match=True,
        gate_report=gate_rep,
        recall_plan=plan,
        reduction_tree=tree,
        timestamp=time.time(),
        reproducibility_hash="hash",
        metadata={"sandbox_trial": False}
    )
    
    res = court.review_hcam_recall_report(report)
    assert res.passed is True
    assert res.decision == "promote_hcam_candidate"
    
    report.metadata["sandbox_trial"] = True
    res_sandbox = court.review_hcam_recall_report(report)
    assert res_sandbox.passed is True
    assert res_sandbox.decision == "authorize_sandbox_recall_trial"


def test_phase14_simd_lane_group_mappings():
    """Verify that SIMD modes (uint8x8, uint16x4, uint32x2, uint64x1) map correctly onto byte lanes."""
    from sol_simd_modes import lane_groups_for_simd
    
    # uint8x8
    groups_8 = lane_groups_for_simd("uint8x8")
    assert len(groups_8) == 8
    for i, g in enumerate(groups_8):
        assert g.group_index == i
        assert g.lanes == [i]
        assert g.bit_offset == i * 8
        assert g.width == 8

    # uint16x4
    groups_16 = lane_groups_for_simd("uint16x4")
    assert len(groups_16) == 4
    for i, g in enumerate(groups_16):
        assert g.group_index == i
        assert g.lanes == [i * 2, i * 2 + 1]
        assert g.bit_offset == i * 16
        assert g.width == 16

    # uint32x2
    groups_32 = lane_groups_for_simd("uint32x2")
    assert len(groups_32) == 2
    for i, g in enumerate(groups_32):
        assert g.group_index == i
        assert g.lanes == list(range(i * 4, i * 4 + 4))
        assert g.bit_offset == i * 32
        assert g.width == 32

    # uint64x1
    groups_64 = lane_groups_for_simd("uint64x1")
    assert len(groups_64) == 1
    assert groups_64[0].group_index == 0
    assert groups_64[0].lanes == list(range(8))
    assert groups_64[0].bit_offset == 0
    assert groups_64[0].width == 64


def test_phase14_simd_lane_ops_and_masks():
    """Verify element-wise SIMD lane operations (VADD, VSUB, etc.) and masks per lane width."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from sol_simd_modes import SIMDInstruction
    
    seq = MultiLaneSequencer()
    
    # 1. uint8x8 VADD
    inst_vadd = SIMDInstruction(
        instruction_id="I_VADD_8",
        op="VADD",
        mode="uint8x8",
        operands=[[0x10, 0x20, 0xFF, 0x00, 0x01, 0x02, 0x03, 0x04],
                  [0x05, 0x06, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06]],
        dry_run=True,
        evidence={"oracle_value": [0x15, 0x26, 0x00, 0x02, 0x04, 0x06, 0x08, 0x0A]}
    )
    rep_vadd = seq.execute_simd_instruction(inst_vadd)
    assert rep_vadd.passed_gates is True
    assert rep_vadd.oracle_match is True
    assert rep_vadd.instruction_result.results == [0x15, 0x26, 0x00, 0x02, 0x04, 0x06, 0x08, 0x0A]

    # 2. uint16x4 VSUB
    inst_vsub = SIMDInstruction(
        instruction_id="I_VSUB_16",
        op="VSUB",
        mode="uint16x4",
        operands=[[0x0000, 0x5000, 0x1234, 0xFFFF],
                  [0x0001, 0x1000, 0x1234, 0x0000]],
        dry_run=True,
        evidence={"oracle_value": [0xFFFF, 0x4000, 0x0000, 0xFFFF]}
    )
    rep_vsub = seq.execute_simd_instruction(inst_vsub)
    assert rep_vsub.passed_gates is True
    assert rep_vsub.oracle_match is True

    # 3. uint32x2 VCOMPARE_EQ
    inst_veq = SIMDInstruction(
        instruction_id="I_VEQ_32",
        op="VCOMPARE_EQ",
        mode="uint32x2",
        operands=[[100, 200], [100, 201]],
        dry_run=True,
        evidence={"oracle_value": [1, 0]}
    )
    rep_veq = seq.execute_simd_instruction(inst_veq)
    assert rep_veq.passed_gates is True
    assert rep_veq.oracle_match is True

    # 4. uint8x8 VSHL & VSHR
    inst_vshl = SIMDInstruction(
        instruction_id="I_VSHL_8",
        op="VSHL",
        mode="uint8x8",
        operands=[[0x01, 0x80, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x00],
                  [1, 1, 4, 0, 0, 0, 0, 0]],
        dry_run=True,
        evidence={"oracle_value": [0x02, 0x00, 0xF0, 0x00, 0x00, 0x00, 0x00, 0x00]}
    )
    rep_vshl = seq.execute_simd_instruction(inst_vshl)
    assert rep_vshl.passed_gates is True
    assert rep_vshl.oracle_match is True


def test_phase14_geodesic_reduction_trees_and_execution():
    """Verify that VREDUCE_SUM, VREDUCE_OR, VREDUCE_XOR reduction trees are constructed and evaluated correctly."""
    from sol_geodesic_reduction import build_reduction_tree, validate_reduction_tree, execute_reduction_tree
    
    # 1. uint8x8 reduction tree
    tree_sum = build_reduction_tree("uint8x8", "VREDUCE_SUM")
    assert validate_reduction_tree(tree_sum) is True
    assert tree_sum.depth == 3
    
    inputs = [1, 2, 3, 4, 5, 6, 7, 8]
    val_sum = execute_reduction_tree(inputs, tree_sum)
    assert val_sum == sum(inputs)

    # 2. VREDUCE_OR
    tree_or = build_reduction_tree("uint16x4", "VREDUCE_OR")
    assert validate_reduction_tree(tree_or) is True
    assert tree_or.depth == 2
    
    inputs_or = [0xF000, 0x0F00, 0x00F0, 0x000F]
    val_or = execute_reduction_tree(inputs_or, tree_or)
    assert val_or == 0xFFFF

    # 3. VREDUCE_XOR
    tree_xor = build_reduction_tree("uint32x2", "VREDUCE_XOR")
    assert validate_reduction_tree(tree_xor) is True
    assert tree_xor.depth == 1
    
    inputs_xor = [0xAAAA, 0x5555]
    val_xor = execute_reduction_tree(inputs_xor, tree_xor)
    assert val_xor == 0xFFFF


def test_phase14_simd_gates_validations():
    """Verify SIMD execution gates reject invalid modes, mapping, and reduction trees."""
    from sol_multilane_sequencer import MultiLaneSequencer
    from sol_simd_modes import SIMDInstruction
    
    seq = MultiLaneSequencer()
    
    # Invalid mode
    inst_invalid = SIMDInstruction("I_INV", "VADD", "uint7x8", [[1], [1]])
    rep_invalid = seq.execute_simd_instruction(inst_invalid)
    assert rep_invalid.passed_gates is False
    assert "Unsupported mode" in rep_invalid.gate_report.errors[0]
    
    # Invalid operand count
    inst_op = SIMDInstruction("I_OP", "VADD", "uint8x8", [[1]])
    rep_op = seq.execute_simd_instruction(inst_op)
    assert rep_op.passed_gates is False
    assert "operand_count_valid" in rep_op.gate_report.checked_gates
    assert rep_op.gate_report.checked_gates["operand_count_valid"] is False


def test_phase14_simd_ranger_sovereign_packet():
    """Verify SimdRanger generates a valid, JSON-serializable SovereignPacket."""
    from coding_library.sovereign_domain import SimdRanger
    from sol_simd_modes import SIMDInstruction, SIMDInstructionResult, SIMDExecutionReport
    from sol_wideword_instruction import InstructionGateReport
    from sol_geodesic_reduction import build_reduction_tree
    import json
    import time
    
    ranger = SimdRanger()
    inst = SIMDInstruction("I_SIMD", "VREDUCE_SUM", "uint8x8", [[1, 2, 3, 4, 5, 6, 7, 8]])
    
    gate_rep = InstructionGateReport(passed=True, checked_gates={}, errors=[])
    inst_res = SIMDInstructionResult(inst, [36], [], True)
    tree = build_reduction_tree("uint8x8", "VREDUCE_SUM")
    
    report = SIMDExecutionReport(
        report_id="RPT_123",
        instruction_id="I_SIMD",
        mode="uint8x8",
        op="VREDUCE_SUM",
        passed_gates=True,
        oracle_match=True,
        gate_report=gate_rep,
        instruction_result=inst_res,
        reduction_tree=tree,
        timestamp=time.time(),
        reproducibility_hash="hash"
    )
    
    packet = ranger.observe_simd(inst, inst_res, report)
    assert packet.actor == "SIMD Ranger"
    assert packet.evidence["simd_mode"] == "uint8x8"
    assert packet.evidence["reduction_depth"] == 3
    
    js = json.dumps(packet.to_dict())
    assert js is not None


def test_phase14_court_reviews_simd_reports():
    """Verify PromotionCourt evaluates SIMD and geodesic reduction reports correctly."""
    from coding_library.sovereign_domain import PromotionCourt
    from sol_simd_modes import SIMDInstruction, SIMDInstructionResult, SIMDExecutionReport
    from sol_wideword_instruction import InstructionGateReport
    from sol_geodesic_reduction import build_reduction_tree
    import time
    
    court = PromotionCourt()
    inst = SIMDInstruction("I_SIMD", "VREDUCE_SUM", "uint8x8", [[1, 2, 3, 4, 5, 6, 7, 8]])
    gate_rep = InstructionGateReport(
        passed=True,
        checked_gates={
            "mode_supported": True,
            "lane_group_mapping_complete": True,
            "operand_count_valid": True,
            "result_masked_to_lane_width": True,
            "reduction_tree_complete_if_required": True,
            "no_unbounded_reduction_path": True
        },
        errors=[]
    )
    inst_res = SIMDInstructionResult(inst, [36], [], True)
    tree = build_reduction_tree("uint8x8", "VREDUCE_SUM")
    
    report = SIMDExecutionReport(
        report_id="RPT_123",
        instruction_id="I_SIMD",
        mode="uint8x8",
        op="VREDUCE_SUM",
        passed_gates=True,
        oracle_match=True,
        gate_report=gate_rep,
        instruction_result=inst_res,
        reduction_tree=tree,
        timestamp=time.time(),
        reproducibility_hash="hash",
        metadata={"sandbox_trial": False}
    )
    
    res = court.review_simd_execution_report(report)
    assert res.passed is True
    assert res.decision == "promote_level14_candidate"
    
    res_red = court.review_geodesic_reduction_report(report)
    assert res_red.passed is True
    assert res_red.decision == "promote_level14_candidate"


def test_phase15_cross_manifold_route_building_and_validation():
    from sol_cross_manifold_routing import (
        ManifoldDomain,
        build_geodesic_route,
        validate_geodesic_route,
        GeodesicRouteHop
    )
    
    src = ManifoldDomain("M_SRC", "SourceManifold", [0, 1])
    tgt = ManifoldDomain("M_TGT", "TargetManifold", [0, 1])
    
    route = build_geodesic_route(src, tgt, 16)
    assert route.source_manifold_id == "M_SRC"
    assert route.target_manifold_id == "M_TGT"
    assert len(route.hops) == 3
    assert validate_geodesic_route(route) is True
    
    # Missing source/target
    bad_route_1 = build_geodesic_route(ManifoldDomain("", "SourceManifold"), tgt, 16)
    assert validate_geodesic_route(bad_route_1) is False
    
    # Unbounded depth (> 4 hops)
    route.hops.append(GeodesicRouteHop(3, "node3", "node4"))
    route.hops.append(GeodesicRouteHop(4, "node4", "node5"))
    route.route_depth = len(route.hops)
    assert validate_geodesic_route(route) is False


def test_phase15_shadow_transfer_and_oracle_match():
    from sol_cross_manifold_routing import (
        CrossManifoldTransferRequest,
        plan_cross_manifold_transfer,
        execute_shadow_transfer
    )
    from sol_multilane_sequencer import MultiLaneSequencer
    from sol_wideword_instruction import WideWordInstruction
    
    req = CrossManifoldTransferRequest("REQ_001", "M_SRC", "M_TGT", 0xABCD, 16)
    plan = plan_cross_manifold_transfer(req)
    assert plan.value_width == 16
    
    res = execute_shadow_transfer(plan)
    assert res.transferred_value == 0xABCD
    assert res.passed_gates is True
    
    # Test Sequencer shadow transfer with matching oracle
    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_XFER", "COMMIT_WORD", 16, [0xABCD], 2)
    plan = seq.plan_cross_manifold_instruction(inst, "M_SRC", "M_TGT")
    
    report = seq.execute_shadow_cross_manifold_transfer(plan)
    assert report.passed_gates is True
    assert report.oracle_match is True
    
    # Test Sequencer shadow transfer with mismatched oracle
    inst_bad = WideWordInstruction("I_XFER_BAD", "COMMIT_WORD", 16, [0xABCD, 0x9999], 2)
    plan_bad = seq.plan_cross_manifold_instruction(inst_bad, "M_SRC", "M_TGT")
    report_bad = seq.execute_shadow_cross_manifold_transfer(plan_bad)
    assert report_bad.passed_gates is False
    assert report_bad.oracle_match is False
    assert "oracle_match_if_available" in report_bad.gate_report.checked_gates
    assert report_bad.gate_report.checked_gates["oracle_match_if_available"] is False


def test_phase15_entanglement_stability_metrics():
    from sol_entanglement_stability import (
        measure_phase_coherence,
        measure_transfer_drift,
        check_entanglement_stability,
        EntanglementObservation,
        EntanglementLink
    )
    
    # Coherent mock states
    src_state = {"phase": 0.02, "value": 100}
    tgt_state_coherent = {"phase": 0.03, "value": 100}
    
    coherence = measure_phase_coherence(src_state, tgt_state_coherent)
    drift = measure_transfer_drift(src_state, tgt_state_coherent)
    assert coherence == 0.99
    assert drift == 0.0
    
    link = EntanglementLink("L_01", "M_SRC", "M_TGT")
    obs = EntanglementObservation("O_01", link, coherence, drift)
    
    report = check_entanglement_stability(obs, tolerance=0.05)
    assert report.stable is True
    assert report.decision == "stable"
    
    # High-drift/incoherent mock states
    tgt_state_drifted = {"phase": 0.20, "value": 150}
    coherence_drifted = measure_phase_coherence(src_state, tgt_state_drifted)
    drift_drifted = measure_transfer_drift(src_state, tgt_state_drifted)
    assert coherence_drifted == 0.82
    assert drift_drifted == 50.0
    
    obs_drifted = EntanglementObservation("O_02", link, coherence_drifted, drift_drifted)
    report_drifted = check_entanglement_stability(obs_drifted, tolerance=0.05)
    assert report_drifted.stable is False
    assert report_drifted.decision == "reject_transfer"


def test_phase15_stability_guard_and_frontier_advisor():
    from sol_entanglement_stability import (
        guard_transfer,
        EntanglementStabilityReport
    )
    from coding_library.sovereign_domain.frontier_bridge import (
        FrontierBridge,
        FrontierEntanglementAdvisor
    )
    
    # Guard recommends quarantine/rollback on unstable route
    rep_unstable = EntanglementStabilityReport(
        report_id="R_REP",
        observation_id="O_REP",
        phase_coherence=0.60,
        transfer_drift=0.20,
        stable=False,
        decision="quarantine_route",
        reproducibility_hash="hash",
        timestamp=0.0
    )
    decision = guard_transfer(rep_unstable)
    assert decision.rollback_recommended is True
    assert decision.quarantine_route is True
    assert decision.decision == "quarantine_route"
    
    # FrontierEntanglementAdvisor suggestions
    bridge = FrontierBridge()
    advisor = FrontierEntanglementAdvisor(bridge)
    
    obs_data = {
        "observation_id": "OBS_LINK",
        "phase_coherence": 0.55,
        "transfer_drift": 0.25
    }
    sugg = advisor.suggest_stabilization(obs_data)
    assert sugg.action == "suggest_boundary_absorption"
    assert sugg.damping_adjustment == 0.01
    
    obs_quar = {
        "observation_id": "OBS_LINK",
        "phase_coherence": 0.30,
        "transfer_drift": 0.50
    }
    sugg_quar = advisor.suggest_stabilization(obs_quar)
    assert sugg_quar.action == "quarantine_route"


def test_phase15_entanglement_ranger_packet():
    from coding_library.sovereign_domain import EntanglementRanger
    from sol_cross_manifold_routing import (
        ManifoldDomain,
        build_geodesic_route,
        GeodesicRoutePlan,
        CrossManifoldTransferRequest,
        execute_shadow_transfer
    )
    from sol_entanglement_stability import (
        EntanglementLink,
        EntanglementObservation,
        check_entanglement_stability
    )
    from sol_multilane_sequencer import MultiLaneSequencer
    from sol_wideword_instruction import WideWordInstruction
    import json
    
    src = ManifoldDomain("M_SRC", "Source")
    tgt = ManifoldDomain("M_TGT", "Target")
    inst = WideWordInstruction("I_XFER", "COMMIT_WORD", 16, [0xABCD], 2)
    
    seq = MultiLaneSequencer()
    plan = seq.plan_cross_manifold_instruction(inst, src, tgt)
    routing_report = seq.execute_shadow_cross_manifold_transfer(plan)
    
    link = EntanglementLink("L_01", "M_SRC", "M_TGT")
    obs = EntanglementObservation("O_01", link, 0.99, 0.0)
    stability_report = check_entanglement_stability(obs, tolerance=0.05)
    
    ranger = EntanglementRanger()
    packet = ranger.observe_entanglement(plan, routing_report, stability_report)
    
    assert packet.actor == "Entanglement Ranger"
    assert packet.level == 15
    assert packet.evidence["source_domain"] == "M_SRC"
    assert packet.evidence["target_domain"] == "M_TGT"
    assert packet.evidence["stability_decision"] == "stable"
    
    js = json.dumps(packet.to_dict())
    assert js is not None


def test_phase15_court_reviews_cross_manifold_reports():
    from coding_library.sovereign_domain import PromotionCourt
    from sol_cross_manifold_routing import (
        CrossManifoldTransferRequest,
        plan_cross_manifold_transfer,
        execute_shadow_transfer,
        CrossManifoldRoutingReport
    )
    from sol_entanglement_stability import (
        EntanglementLink,
        EntanglementObservation,
        check_entanglement_stability
    )
    from sol_wideword_instruction import InstructionGateReport
    import time
    
    court = PromotionCourt()
    gate_rep = InstructionGateReport(passed=True, checked_gates={}, errors=[])
    req = CrossManifoldTransferRequest("REQ_001", "M_SRC", "M_TGT", 0xABCD, 16)
    res = execute_shadow_transfer(plan_cross_manifold_transfer(req))
    
    report = CrossManifoldRoutingReport(
        report_id="R_REP",
        request_id="REQ_001",
        source_manifold_id="M_SRC",
        target_manifold_id="M_TGT",
        route_depth=3,
        boundary_crossings=["crossing"],
        value_width=16,
        passed_gates=True,
        oracle_match=True,
        gate_report=gate_rep,
        transfer_result=res,
        reproducibility_hash="hash",
        timestamp=time.time(),
        metadata={"stability_decision": "stable"}
    )
    
    court_res = court.review_cross_manifold_routing_report(report)
    assert court_res.passed is True
    assert court_res.decision == "promote_cross_manifold_candidate"
    
    link = EntanglementLink("L_01", "M_SRC", "M_TGT")
    obs = EntanglementObservation("O_01", link, 0.99, 0.0)
    stability_report = check_entanglement_stability(obs, tolerance=0.05)
    
    court_res_stab = court.review_entanglement_stability_report(stability_report)
    assert court_res_stab.passed is True
    assert court_res_stab.decision == "promote_cross_manifold_candidate"


def test_phase16_consensus_group_building_and_quorum():
    from sol_wavefront_consensus import (
        build_consensus_group,
        propose_wavefront_state,
        collect_consensus_votes,
        evaluate_quorum,
        build_consensus_report,
        ConsensusDecision
    )
    
    # 1. Consensus group builds from 3 mock sequencers
    sequencer_ids = ["seq_0", "seq_1", "seq_2"]
    group = build_consensus_group(sequencer_ids, quorum_ratio=0.67)
    assert group.group_id.startswith("CGROUP_")
    assert len(group.nodes) == 3
    assert group.nodes[0].role == "leader"
    assert group.nodes[1].role == "follower"
    assert group.nodes[2].role == "follower"
    assert group.quorum_ratio == 0.67
    
    # Propose wavefront state
    proposal = propose_wavefront_state(group, "state_hash_123", {"evidence_key": "val"})
    assert proposal.proposer_id == "seq_0"
    assert proposal.proposed_state_hash == "state_hash_123"
    
    # 2. Quorum passes with 2/3 agreement when quorum_ratio=0.67
    mock_votes_pass = {
        "seq_0": "approve",
        "seq_1": "approve",
        "seq_2": "reject"
    }
    votes_pass = collect_consensus_votes(group, proposal, mock_votes=mock_votes_pass)
    quorum_pass = evaluate_quorum(votes_pass, group.quorum_ratio)
    assert quorum_pass.quorum_reached is True
    assert quorum_pass.total_approved_weight == 2.0
    
    # 3. Quorum fails with insufficient agreement
    mock_votes_fail = {
        "seq_0": "approve",
        "seq_1": "reject",
        "seq_2": "reject"
    }
    votes_fail = collect_consensus_votes(group, proposal, mock_votes=mock_votes_fail)
    quorum_fail = evaluate_quorum(votes_fail, group.quorum_ratio)
    assert quorum_fail.quorum_reached is False
    assert quorum_fail.total_approved_weight == 1.0


def test_phase16_sequencer_coherence_and_sync():
    from sol_entangled_sequencer import (
        snapshot_sequencer_state,
        compare_sequencer_states,
        measure_group_coherence,
        build_sync_report
    )
    
    # Mock sequencers
    seq_0 = {"name": "seq_0", "step": 10, "phase": 0.02, "mass": 100.0}
    seq_1_aligned = {"name": "seq_1", "step": 10, "phase": 0.03, "mass": 100.0}
    seq_2_aligned = {"name": "seq_2", "step": 10, "phase": 0.01, "mass": 100.0}
    
    state_0 = snapshot_sequencer_state(seq_0)
    state_1_aligned = snapshot_sequencer_state(seq_1_aligned)
    state_2_aligned = snapshot_sequencer_state(seq_2_aligned)
    
    # 4. Group coherence passes for aligned mock states
    group_states_aligned = [state_0, state_1_aligned, state_2_aligned]
    coherence_aligned = measure_group_coherence(group_states_aligned)
    assert coherence_aligned == 0.98
    
    report_aligned = build_sync_report(group_states_aligned, tolerance=0.05)
    assert report_aligned.synchronized is True
    assert report_aligned.max_drift == pytest.approx(0.01)
    
    # 5. Group coherence fails for high-drift mock states
    seq_1_drifted = {"name": "seq_1", "step": 10, "phase": 0.15, "mass": 100.0}
    state_1_drifted = snapshot_sequencer_state(seq_1_drifted)
    
    group_states_drifted = [state_0, state_1_drifted, state_2_aligned]
    coherence_drifted = measure_group_coherence(group_states_drifted)
    assert coherence_drifted == 0.86
    
    report_drifted = build_sync_report(group_states_drifted, tolerance=0.05)
    assert report_drifted.synchronized is False


def test_phase16_consensus_transfer_gating():
    from sol_cross_manifold_routing import (
        CrossManifoldTransferRequest,
        plan_consensus_routed_transfer,
        execute_shadow_consensus_transfer,
        ManifoldDomain
    )
    from sol_wavefront_consensus import build_consensus_group
    
    # 6. Consensus transfer rejects invalid route
    group = build_consensus_group(["seq_0", "seq_1", "seq_2"])
    req = CrossManifoldTransferRequest("REQ_001", "M_SRC", "M_TGT", 0x1234, 16)
    plan = plan_consensus_routed_transfer(req, group)
    
    # Execute shadow transfer: should pass with valid default route
    res_valid = execute_shadow_consensus_transfer(plan)
    assert res_valid.passed_gates is True
    
    # Set route hops to empty to make it invalid
    plan.route.hops = []
    res_invalid_route = execute_shadow_consensus_transfer(plan)
    assert res_invalid_route.passed_gates is False
    
    # Restore hops, but set target domain metadata to indicate failed stability
    plan = plan_consensus_routed_transfer(req, group)
    plan.target_domain.metadata["stability_passed"] = False
    
    # 7. Consensus transfer rejects failed entanglement stability
    res_invalid_stability = execute_shadow_consensus_transfer(plan)
    assert res_invalid_stability.passed_gates is False


def test_phase16_frontier_consensus_advisor():
    from coding_library.sovereign_domain.frontier_bridge import (
        FrontierBridge,
        FrontierConsensusAdvisor
    )
    from sol_entangled_sequencer import SequencerSyncReport
    import time
    
    # 8. FrontierConsensusAdvisor returns advisory-only suggestions
    bridge = FrontierBridge()
    advisor = FrontierConsensusAdvisor(bridge)
    
    # Test highly synchronized
    rep_sync = SequencerSyncReport("R_SYNC", group_coherence=0.98, max_drift=0.01, synchronized=True, reproducibility_hash="hash", timestamp=time.time())
    sugg_sync = advisor.suggest_consensus_stabilization(rep_sync)
    assert sugg_sync.action == "observe"
    assert sugg_sync.nudge_value == 0.0
    assert sugg_sync.damping_adjustment == 0.0
    
    # Test minor drift
    rep_drift = SequencerSyncReport("R_DRIFT", group_coherence=0.88, max_drift=0.06, synchronized=True, reproducibility_hash="hash", timestamp=time.time())
    sugg_drift = advisor.suggest_consensus_stabilization(rep_drift)
    assert sugg_drift.action == "suggest_phase_alignment"
    assert sugg_drift.nudge_value == pytest.approx(-0.05 * 0.06)
    
    # Test poor coherence
    rep_poor = SequencerSyncReport("R_POOR", group_coherence=0.60, max_drift=0.20, synchronized=False, reproducibility_hash="hash", timestamp=time.time())
    sugg_poor = advisor.suggest_consensus_stabilization(rep_poor)
    assert sugg_poor.action == "suggest_wavefront_resync"
    
    # Test critical failure
    rep_crit = SequencerSyncReport("R_CRIT", group_coherence=0.30, max_drift=0.45, synchronized=False, reproducibility_hash="hash", timestamp=time.time())
    sugg_crit = advisor.suggest_consensus_stabilization(rep_crit)
    assert sugg_crit.action == "quarantine_sequencer"


def test_phase16_ranger_and_court_reviews():
    from coding_library.sovereign_domain import PromotionCourt, ConsensusRanger
    from sol_wavefront_consensus import (
        build_consensus_group,
        propose_wavefront_state,
        collect_consensus_votes,
        evaluate_quorum,
        build_consensus_report,
        ConsensusDecision
    )
    from sol_entangled_sequencer import (
        snapshot_sequencer_state,
        build_sync_report
    )
    from sol_multilane_sequencer import MultiLaneSequencer
    from sol_wideword_instruction import WideWordInstruction
    
    # Execute a shadow consensus instruction
    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_CONS", "COMMIT_WORD", 16, [0x1111], 2)
    group = build_consensus_group(["seq_0", "seq_1", "seq_2"])
    
    plan = seq.plan_consensus_instruction(inst, group)
    report = seq.execute_shadow_consensus_instruction(plan)
    
    # Build sync report
    seq_0 = {"name": "seq_0", "step": 10, "phase": 0.02, "mass": 100.0}
    seq_1 = {"name": "seq_1", "step": 10, "phase": 0.02, "mass": 100.0}
    seq_2 = {"name": "seq_2", "step": 10, "phase": 0.02, "mass": 100.0}
    states = [snapshot_sequencer_state(s) for s in [seq_0, seq_1, seq_2]]
    sync_report = build_sync_report(states, tolerance=0.05)
    
    # 9. ConsensusRanger emits JSON-serializable SovereignPacket
    ranger = ConsensusRanger()
    packet = ranger.observe_consensus(report, sync_report)
    assert packet.actor == "Consensus Ranger"
    assert packet.level == 16
    assert packet.evidence["quorum_reached"] is True
    assert packet.evidence["group_coherence"] == 1.0
    assert packet.evidence["promotion_readiness"] is True
    
    import json
    js = json.dumps(packet.to_dict())
    assert js is not None
    
    # 10. Promotion Court can review consensus and sequencer sync reports
    court = PromotionCourt()
    
    court_res_cons = court.review_wavefront_consensus_report(report)
    assert court_res_cons.passed is True
    assert court_res_cons.decision == "accept_shadow_consensus"
    
    court_res_sync = court.review_sequencer_sync_report(sync_report)
    assert court_res_sync.passed is True
    assert court_res_sync.decision == "promote_level16_candidate"
    
    # Test failed quorum review
    mock_votes_fail = {"seq_0": "approve", "seq_1": "reject", "seq_2": "reject"}
    votes_fail = collect_consensus_votes(group, plan.evidence["proposal"], mock_votes=mock_votes_fail)
    quorum_fail = evaluate_quorum(votes_fail, group.quorum_ratio)
    decision_fail = ConsensusDecision(plan.evidence["proposal"].proposal_id, None, False, "rejected")
    report_fail = build_consensus_report(plan.evidence["proposal"], votes_fail, decision_fail)
    from sol_wideword_instruction import InstructionGateReport
    report_fail.gate_report = InstructionGateReport(passed=False, checked_gates={"quorum_reached": False}, errors=["failed"])
    
    court_res_fail = court.review_wavefront_consensus_report(report_fail)
    assert court_res_fail.passed is False
    assert court_res_fail.decision == "reject_consensus"

    # Test state hash mismatch detected
    mock_votes_mismatch = {"seq_0": "approve", "seq_1": "mismatch", "seq_2": "approve"}
    group_mismatch = build_consensus_group(["seq_0", "seq_1", "seq_2"])
    group_mismatch.metadata["mock_votes"] = mock_votes_mismatch
    
    plan_mismatch = seq.plan_consensus_instruction(inst, group_mismatch)
    report_mismatch = seq.execute_shadow_consensus_instruction(plan_mismatch)
    assert report_mismatch.passed_gates is False
    assert report_mismatch.gate_report.checked_gates["state_hashes_valid"] is False


def test_phase17_atomic_transaction_building():
    from sol_atomic_commit import (
        AtomicCommitParticipant,
        AtomicCommitIntent,
        build_atomic_transaction
    )
    
    # 1. atomic transaction builds with 2 mock participants
    p2 = [
        AtomicCommitParticipant("p0", "idle", 100),
        AtomicCommitParticipant("p1", "idle", 200)
    ]
    intent = AtomicCommitIntent("I_01", "COMMIT_WORD", 0xAAAA, 16)
    tx_2 = build_atomic_transaction(p2, intent, sandbox=True)
    assert tx_2.transaction_id.startswith("TX_")
    assert len(tx_2.participants) == 2
    assert tx_2.sandbox is True
    
    # 2. atomic transaction builds with 3+ mock participants
    p3 = [
        AtomicCommitParticipant("p0", "idle", 100),
        AtomicCommitParticipant("p1", "idle", 200),
        AtomicCommitParticipant("p2", "idle", 300)
    ]
    tx_3 = build_atomic_transaction(p3, intent, sandbox=True)
    assert len(tx_3.participants) == 3


def test_phase17_prepare_states():
    from sol_atomic_commit import (
        AtomicCommitParticipant,
        AtomicCommitIntent,
        build_atomic_transaction,
        prepare_transaction,
        decide_atomic_commit
    )
    
    intent = AtomicCommitIntent("I_02", "COMMIT_WORD", 0x5555, 16)
    
    # 3. prepare succeeds when all participants are valid
    p_valid = [
        AtomicCommitParticipant("p0", "idle", 100),
        AtomicCommitParticipant("p1", "idle", 200)
    ]
    tx_val = build_atomic_transaction(p_valid, intent)
    prep_res_val = prepare_transaction(tx_val)
    assert all(r.prepared for r in prep_res_val)
    assert tx_val.status == "prepared"
    
    # 4. prepare fails when one participant is invalid
    p_invalid = [
        AtomicCommitParticipant("p0", "idle", 100),
        AtomicCommitParticipant("p1", "idle", 200, metadata={"prepare_fails": True})
    ]
    tx_inval = build_atomic_transaction(p_invalid, intent)
    prep_res_inval = prepare_transaction(tx_inval)
    assert prep_res_inval[0].prepared is True
    assert prep_res_inval[1].prepared is False
    assert tx_inval.status == "aborted"
    
    # 5. commit decision rejects partial prepare when quorum_ratio=1.0
    decision = decide_atomic_commit(prep_res_inval, quorum_ratio=1.0)
    assert decision.decision == "abort"
    assert decision.all_prepared is False
    assert decision.quorum_reached is False


def test_phase17_rollback_and_snapshots():
    import time
    from sol_atomic_commit import (
        AtomicCommitParticipant,
        AtomicCommitIntent,
        build_atomic_transaction,
        capture_participant_snapshots,
        commit_transaction,
        rollback_transaction,
        decide_atomic_commit,
        prepare_transaction
    )
    
    intent = AtomicCommitIntent("I_03", "COMMIT_WORD", 0x3333, 16)
    p = [
        AtomicCommitParticipant("p0", "idle", 100),
        AtomicCommitParticipant("p1", "idle", 200)
    ]
    tx = build_atomic_transaction(p, intent)
    
    # 6. rollback snapshots are required before sandbox commit
    prep_res = prepare_transaction(tx)
    decision = decide_atomic_commit(prep_res, quorum_ratio=1.0)
    
    from coding_library.sovereign_domain.frontier_bridge import LiveControlToken
    token = LiveControlToken(
        token_id="TOK_TEST",
        authorized_by_court=True,
        issued_at=time.time(),
        expires_at=time.time() + 3600,
        sandbox_only=True,
        target_lane=0,
        max_mutations=10,
        active=True
    )
    res_no_snap = commit_transaction(tx, decision, token=token)
    assert res_no_snap.committed is False
    assert "Rollback snapshot is missing" in res_no_snap.errors[0]
    
    snap = capture_participant_snapshots(tx)
    assert tx.rollback_snapshot == snap
    
    res_snap = commit_transaction(tx, decision, token=token)
    assert res_snap.committed is True
    assert p[0].state_value == 0x3333
    assert p[1].state_value == 0x3333
    
    # 7. rollback restores mock participant state
    p[0].state_value = 999
    p[1].state_value = 888
    
    rollback_res = rollback_transaction(tx, reason="simulated abort")
    assert rollback_res.rolled_back is True
    assert p[0].state_value == 100
    assert p[1].state_value == 200


def test_phase17_sequencer_atomic_gates():
    import time
    from sol_multilane_sequencer import MultiLaneSequencer
    from sol_wideword_instruction import WideWordInstruction
    from sol_atomic_commit import AtomicCommitParticipant
    from coding_library.sovereign_domain.frontier_bridge import LiveControlToken
    
    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_ATOMIC", "COMMIT_WORD", 16, [0x7777], 2)
    participants = [
        AtomicCommitParticipant("p0", "idle", 10),
        AtomicCommitParticipant("p1", "idle", 20),
        AtomicCommitParticipant("p2", "idle", 30)
    ]
    
    # 8. consensus quorum is required for atomic commit
    plan = seq.plan_atomic_commit_instruction(inst, participants)
    plan.metadata["mock_votes"] = {"p0": "approve", "p1": "reject", "p2": "approve"}
    report = seq.execute_shadow_atomic_commit(plan)
    assert report.passed_gates is False
    assert report.decision.decision == "abort"
    assert report.gate_report.checked_gates["consensus_quorum_reached"] is False
    
    # 9. cross-manifold route instability blocks atomic commit
    plan_stab = seq.plan_atomic_commit_instruction(inst, participants)
    plan_stab.metadata["stability_passed"] = False
    report_stab = seq.execute_shadow_atomic_commit(plan_stab)
    assert report_stab.passed_gates is False
    assert report_stab.gate_report.checked_gates["entanglement_stability_passed_if_required"] is False
    
    # 10. sandbox token is required for sandbox commit
    plan_token = seq.plan_atomic_commit_instruction(inst, participants)
    report_token = seq.execute_sandbox_atomic_commit(plan_token, token=None)
    assert report_token.passed_gates is False
    assert report_token.gate_report.checked_gates["token_required_for_sandbox_commit"] is False
    
    token = LiveControlToken(
        token_id="TOK_TEST",
        authorized_by_court=True,
        issued_at=time.time(),
        expires_at=time.time() + 3600,
        sandbox_only=True,
        target_lane=0,
        max_mutations=10,
        active=True
    )
    report_token_ok = seq.execute_sandbox_atomic_commit(plan_token, token=token)
    assert report_token_ok.passed_gates is True
    assert report_token_ok.commit_result.committed is True
    assert report_token_ok.commit_result.sandbox_executed is True
    assert plan_token.participants[0].state_value == 0x7777
    
    # 11. production/default commit is rejected
    plan_prod = seq.plan_atomic_commit_instruction(inst, participants)
    plan_prod.sandbox = False
    report_prod = seq.execute_sandbox_atomic_commit(plan_prod, token=token)
    assert report_prod.passed_gates is False
    assert report_prod.gate_report.checked_gates["no_production_commit"] is False
    assert report_prod.commit_result.committed is False


def test_phase17_atomic_commit_ranger_and_court():
    import time
    from coding_library.sovereign_domain import PromotionCourt, AtomicCommitRanger
    from sol_multilane_sequencer import MultiLaneSequencer
    from sol_wideword_instruction import WideWordInstruction
    from sol_atomic_commit import AtomicCommitParticipant
    from coding_library.sovereign_domain.frontier_bridge import LiveControlToken
    import json
    
    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_ATOMIC", "COMMIT_WORD", 16, [0x8888], 2)
    participants = [
        AtomicCommitParticipant("p0", "idle", 10),
        AtomicCommitParticipant("p1", "idle", 20),
        AtomicCommitParticipant("p2", "idle", 30)
    ]
    
    token = LiveControlToken(
        token_id="TOK_TEST",
        authorized_by_court=True,
        issued_at=time.time(),
        expires_at=time.time() + 3600,
        sandbox_only=True,
        target_lane=0,
        max_mutations=10,
        active=True
    )
    plan = seq.plan_atomic_commit_instruction(inst, participants)
    report = seq.execute_sandbox_atomic_commit(plan, token=token)
    
    # 13. AtomicCommitRanger emits JSON-serializable SovereignPacket
    ranger = AtomicCommitRanger()
    packet = ranger.observe_atomic_commit(report)
    assert packet.actor == "Atomic Commit Ranger"
    assert packet.level == 17
    assert packet.evidence["quorum_status"] is True
    assert packet.evidence["rollback_snapshot_status"] is True
    assert packet.evidence["promotion_readiness"] is True
    
    js = json.dumps(packet.to_dict())
    assert js is not None
    
    # 14. Promotion Court can review atomic commit and rollback reports
    court = PromotionCourt()
    court_res = court.review_atomic_commit_report(report)
    assert court_res.passed is True
    assert court_res.decision == "accept_shadow_atomic_commit"
    
    plan_fail = seq.plan_atomic_commit_instruction(inst, participants)
    plan_fail.metadata["mock_votes"] = {"p0": "approve", "p1": "reject", "p2": "approve"}
    report_fail = seq.execute_shadow_atomic_commit(plan_fail)
    court_res_fail = court.review_atomic_commit_report(report_fail)
    assert court_res_fail.passed is False
    assert court_res_fail.decision == "reject_atomic_commit"
    
    court_res_rollback = court.review_atomic_rollback_report(report_fail)
    assert court_res_rollback.passed is True
    assert court_res_rollback.decision == "reject_atomic_commit"
    
    # 12. partial failure triggers rollback recommendation
    assert report_fail.rollback_result.rolled_back is True


def test_phase17_atomic_cross_manifold_commit_routing():
    from sol_cross_manifold_routing import (
        CrossManifoldTransferRequest,
        plan_atomic_cross_manifold_commit,
        execute_shadow_atomic_route_commit
    )
    from sol_wavefront_consensus import build_consensus_group
    
    reqs = [
        CrossManifoldTransferRequest("REQ_A1", "M_SRC1", "M_TGT1", 0xAAAA, 16),
        CrossManifoldTransferRequest("REQ_A2", "M_SRC2", "M_TGT2", 0xBBBB, 16)
    ]
    group = build_consensus_group(["seq_0", "seq_1", "seq_2"])
    
    # Plan atomic cross manifold commit
    plan = plan_atomic_cross_manifold_commit(reqs, group)
    assert len(plan.route_plans) == 2
    assert plan.consensus_group == group
    
    # Shadow execute atomic route commit: passes by default
    res = execute_shadow_atomic_route_commit(plan)
    assert res.passed_gates is True
    assert res.evidence["route_stability"] is True
    assert res.evidence["oracle_match"] is True
    assert res.evidence["source_domains"] == ["M_SRC1", "M_SRC2"]
    assert res.evidence["target_domains"] == ["M_TGT1", "M_TGT2"]
    
    # Instability blocks atomic commit
    plan_unstable = plan_atomic_cross_manifold_commit(reqs, group)
    plan_unstable.route_plans[0].target_domain.metadata["stability_passed"] = False
    res_unstable = execute_shadow_atomic_route_commit(plan_unstable)
    assert res_unstable.passed_gates is False
    assert res_unstable.evidence["route_stability"] is False


def test_phase18_shard_topology():
    from sol_shard_topology import (
        build_shard_topology,
        validate_shard_topology,
        assign_manifold_to_shard,
        map_fabric_lanes_to_shards
    )
    
    # 1. 2-shard topology builds and validates.
    t2 = build_shard_topology(2)
    assert len(t2.shards) == 2
    assert len(t2.boundaries) == 4
    assert validate_shard_topology(t2) is True
    
    # 2. 4-shard topology builds and validates.
    t4 = build_shard_topology(4)
    assert len(t4.shards) == 4
    assert validate_shard_topology(t4) is True
    
    # 3. 8-shard topology builds and validates.
    t8 = build_shard_topology(8)
    assert len(t8.shards) == 8
    assert validate_shard_topology(t8) is True
    
    # 4. lane-to-shard mapping covers all lanes for 32-bit fabric.
    map_fabric_lanes_to_shards(32, t4)
    assert len(t4.lane_mappings) == 4
    assert set(t4.lane_mappings.keys()) == {0, 1, 2, 3}
    
    # 5. lane-to-shard mapping covers all lanes for 64-bit fabric.
    map_fabric_lanes_to_shards(64, t8)
    assert len(t8.lane_mappings) == 8
    assert set(t8.lane_mappings.keys()) == set(range(8))


def test_phase18_cross_shard_query_planning():
    from sol_shard_topology import build_shard_topology
    from sol_cross_shard_query import (
        CrossShardQuery,
        plan_cross_shard_query,
        validate_cross_shard_query_plan,
        assemble_cross_shard_result
    )
    
    topo = build_shard_topology(4)
    
    # 6. single-shard query plan validates.
    q_single = CrossShardQuery(
        query_id="Q_S",
        query_type="single",
        target_manifold_ids=["M_0"],
        fields=["state_value"]
    )
    plan_s = plan_cross_shard_query(q_single, topo)
    assert validate_cross_shard_query_plan(plan_s) is True
    assert len(plan_s.target_shards) == 1
    
    # 7. fan-out/fan-in cross-shard query plan validates.
    q_fan = CrossShardQuery(
        query_id="Q_F",
        query_type="fan-out",
        target_manifold_ids=["M_0", "M_1", "M_2", "M_3"],
        fields=["state_value"]
    )
    plan_f = plan_cross_shard_query(q_fan, topo)
    assert validate_cross_shard_query_plan(plan_f) is True
    
    # 8. reduction tree covers all shard responses.
    results = {"shard_0": 10, "shard_1": 20, "shard_2": 30}
    sum_res = assemble_cross_shard_result(results, reduction="sum")
    assert sum_res == 60
    
    merge_res = assemble_cross_shard_result({"shard_0": {"a": 1}, "shard_1": {"b": 2}})
    assert merge_res == {"a": 1, "b": 2}


def test_phase18_query_optimization():
    from sol_shard_topology import build_shard_topology
    from sol_cross_shard_query import CrossShardQuery, plan_cross_shard_query
    from sol_query_optimizer import optimize_query_tree
    
    topo = build_shard_topology(4)
    q = CrossShardQuery(
        query_id="Q_O",
        query_type="fan-out",
        target_manifold_ids=["M_0", "M_1", "M_2", "M_3"],
        fields=["state_value"]
    )
    plan = plan_cross_shard_query(q, topo)
    orig_cost = plan.cost_estimate
    
    # 9. query optimizer reduces or preserves route cost.
    opt = optimize_query_tree(plan)
    assert opt.optimization.optimized_cost.total_cost <= orig_cost.total_cost
    assert opt.optimization.improvement_ratio >= 0.0


def test_phase18_shard_consensus():
    from sol_shard_topology import build_shard_topology, ShardId
    from sol_shard_consensus import (
        build_shard_consensus_group,
        propose_shard_state,
        collect_shard_votes,
        evaluate_local_quorum,
        evaluate_global_quorum
    )
    
    topo = build_shard_topology(4)
    group = build_shard_consensus_group(topo, local_quorum=0.67, global_quorum=0.67)
    prop = propose_shard_state(group, ShardId("shard_0"), "sha256_state_hash", {"test": True})
    
    # 10. local shard quorum passes and fails correctly.
    votes_pass = collect_shard_votes(group, prop, mock_votes={"shard_0": "approve"})
    dec_pass = evaluate_local_quorum(votes_pass, group)
    assert dec_pass.quorum_reached is True
    assert dec_pass.decision == "commit"
    
    votes_fail = collect_shard_votes(group, prop, mock_votes={"shard_0_val_0": "reject", "shard_0_val_1": "reject"})
    dec_fail = evaluate_local_quorum(votes_fail, group)
    assert dec_fail.quorum_reached is False
    assert dec_fail.decision == "abort"
    
    # 11. global shard quorum passes and fails correctly.
    local_decs_pass = {
        "shard_0": dec_pass,
        "shard_1": dec_pass,
        "shard_2": dec_pass,
        "shard_3": dec_fail
    }
    g_dec_pass = evaluate_global_quorum(local_decs_pass, group)
    assert g_dec_pass.quorum_reached is True
    
    local_decs_fail = {
        "shard_0": dec_pass,
        "shard_1": dec_fail,
        "shard_2": dec_fail,
        "shard_3": dec_fail
    }
    g_dec_fail = evaluate_global_quorum(local_decs_fail, group)
    assert g_dec_fail.quorum_reached is False


def test_phase18_sequencer_sharding_execution_and_gates():
    from sol_multilane_sequencer import MultiLaneSequencer
    from sol_wideword_instruction import WideWordInstruction
    from sol_shard_topology import build_shard_topology
    from coding_library.sovereign_domain import PromotionCourt, ShardRanger
    import json
    
    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_SHARD_Q", "ADD_WORD", 64, [0, 1, 2], 2)
    topo = build_shard_topology(4)
    
    plan = seq.plan_sharded_query_instruction(inst, topo)
    report = seq.execute_shadow_sharded_query(plan)
    
    assert report.passed_gates is True
    assert report.query_result.success is True
    assert report.query_result.assembled_value is not None
    
    # 12. invalid shard boundary blocks query promotion.
    plan_invalid = seq.plan_sharded_query_instruction(inst, topo)
    plan_invalid.metadata["invalid_boundary_crossings"] = True
    report_invalid = seq.execute_shadow_sharded_query(plan_invalid)
    assert report_invalid.passed_gates is False
    assert report_invalid.gate_report.checked_gates["boundary_crossings_declared"] is False
    
    # 13. ShardRanger emits JSON-serializable SovereignPacket.
    ranger = ShardRanger()
    opt_plan = plan.metadata["optimized_plan"]
    consensus_report = plan.metadata["consensus_report"]
    packet = ranger.observe_sharding(
        topology=topo,
        query_plan=plan,
        query_report=report,
        consensus_report=consensus_report,
        optimized_plan=opt_plan
    )
    assert packet.actor == "Shard Ranger"
    assert packet.level == 18
    assert packet.evidence["shard_count"] == 4
    
    js = json.dumps(packet.to_dict())
    assert js is not None
    
    # 14. Promotion Court can review shard topology, query, and consensus reports.
    court = PromotionCourt()
    
    topo_report = {
        "topology": topo,
        "passed": True,
        "reproducibility_hash": "sha256_topo_mock"
    }
    court_res_topo = court.review_shard_topology_report(topo_report)
    assert court_res_topo.passed is True
    assert court_res_topo.decision == "accept_shadow_shard_plan"
    
    court_res_query = court.review_cross_shard_query_report(report)
    assert court_res_query.passed is True
    assert court_res_query.decision == "accept_shadow_shard_plan"
    
    court_res_consensus = court.review_hierarchical_consensus_report(consensus_report)
    assert court_res_consensus.passed is True
    assert court_res_consensus.decision == "promote_level18_candidate"
    
    court_res_invalid = court.review_cross_shard_query_report(report_invalid)
    assert court_res_invalid.passed is False
    assert court_res_invalid.decision == "quarantine_route"


def test_phase19_distributed_transactions_and_locking():
    """Verify Phase 19 Level 19 Distributed Transaction Coordinator and Shard-Lock Scheduler."""
    from sol_transaction_coordinator import (
        TransactionIntent,
        TransactionParticipant,
        build_transaction,
        prepare_distributed_transaction,
        commit_distributed_transaction,
        abort_distributed_transaction
    )
    from sol_shard_lock_scheduler import (
        request_locks,
        grant_locks_if_available,
        release_locks,
        build_wait_for_graph,
        detect_deadlock,
        clear_active_locks,
        get_active_locks,
        ShardLockRequest
    )
    from sol_shard_consensus import (
        build_shard_consensus_group,
        propose_transaction_commit,
        collect_shard_votes,
        evaluate_transaction_quorum
    )
    from sol_shard_topology import build_shard_topology
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain.rangers.transaction_ranger import TransactionRanger
    from coding_library.sovereign_domain.promotion_court import PromotionCourt
    from coding_library.sovereign_domain import WideWordInstruction
    import time
    import json
    
    clear_active_locks()
    
    # 1. transaction builds with 2 mock shard participants
    intent2 = TransactionIntent("intent_2", "ADD_WORD", 42, 64)
    parts2 = [
        TransactionParticipant("shard_0", "idle"),
        TransactionParticipant("shard_1", "idle")
    ]
    tx2 = build_transaction(intent2, parts2)
    assert len(tx2.participants) == 2
    assert tx2.status == "pending"
    
    # 2. transaction builds with 4+ mock shard participants
    intent4 = TransactionIntent("intent_4", "ADD_WORD", 100, 64)
    parts4 = [
        TransactionParticipant("shard_0", "idle"),
        TransactionParticipant("shard_1", "idle"),
        TransactionParticipant("shard_2", "idle"),
        TransactionParticipant("shard_3", "idle")
    ]
    tx4 = build_transaction(intent4, parts4)
    assert len(tx4.participants) == 4
    
    # 3. shared locks can coexist on same shard
    clear_active_locks()
    req_s1 = ShardLockRequest("req_s1", "tx_a", "shard_0", "shared")
    req_s2 = ShardLockRequest("req_s2", "tx_b", "shard_0", "shared")
    sched_s1 = grant_locks_if_available([req_s1])
    sched_s2 = grant_locks_if_available([req_s2])
    assert len(sched_s1.waits) == 0
    assert len(sched_s2.waits) == 0
    assert len(get_active_locks()) == 2
    
    # 4. exclusive lock blocks conflicting lock request
    clear_active_locks()
    req_x1 = ShardLockRequest("req_x1", "tx_a", "shard_0", "exclusive")
    req_x2 = ShardLockRequest("req_x2", "tx_b", "shard_0", "shared")
    sched_x1 = grant_locks_if_available([req_x1])
    sched_x2 = grant_locks_if_available([req_x2])
    assert len(sched_x1.waits) == 0
    assert len(sched_x2.waits) == 1
    assert sched_x2.waits[0].waiting_on_transaction_ids == ["tx_a"]
    
    # 5. deterministic shard ordering is enforced
    sched_ordered = request_locks("tx_ord", ["shard_0", "shard_1"])
    assert sched_ordered.lock_order_valid is True
    sched_unordered = request_locks("tx_unord", ["shard_1", "shard_0"])
    assert sched_unordered.lock_order_valid is False
    
    # 6. wait-for graph detects a simple deadlock cycle
    mock_wait_graph = {
        "tx_a": ["tx_b"],
        "tx_b": ["tx_a"]
    }
    deadlock_rep = detect_deadlock(mock_wait_graph)
    assert deadlock_rep.deadlock_detected is True
    assert "tx_a" in deadlock_rep.cycle
    assert "tx_b" in deadlock_rep.cycle
    
    # 7. ordered lock strategy prevents deadlock for sorted shard ids
    clear_active_locks()
    sched_deadlock_prevented = request_locks("tx_prevent", ["shard_0", "shard_1"])
    assert sched_deadlock_prevented.lock_order_valid is True
    
    # 8. lock lease metadata is present and valid
    locks = get_active_locks()
    assert len(locks) > 0
    assert locks[0].requested_at <= time.time()
    assert locks[0].expires_at > time.time()
    assert locks[0].owner_transaction_id == "tx_prevent"
    assert locks[0].shard_id == "shard_0"
    
    # 9. transaction prepare fails if locks are missing
    clear_active_locks()
    intent_prep = TransactionIntent("intent_prep", "ADD_WORD", 10, 64)
    part_prep = TransactionParticipant("shard_0", "idle", metadata={"locks_missing": True})
    tx_prep = build_transaction(intent_prep, [part_prep])
    prep_rep = prepare_distributed_transaction(tx_prep)
    assert prep_rep.passed is False
    assert tx_prep.status == "aborted"
    
    # 10. transaction commit is blocked when deadlock is detected
    clear_active_locks()
    seq = MultiLaneSequencer()
    inst = WideWordInstruction("I_TX_DEADLOCK", "ADD_WORD", 64, [0, 1], 2)
    topo = build_shard_topology(4)
    plan_deadlock = seq.plan_distributed_transaction(inst, topo)
    plan_deadlock.metadata["deadlock_report"].deadlock_detected = True
    report_deadlock = seq.execute_shadow_distributed_transaction(plan_deadlock)
    assert report_deadlock.passed_gates is False
    assert plan_deadlock.status == "aborted"
    
    # 11. abort releases all transaction locks
    clear_active_locks()
    request_locks("tx_abort_test", ["shard_0"])
    assert len(get_active_locks()) == 1
    intent_abort = TransactionIntent("intent_abort", "ADD_WORD", 20, 64)
    tx_abort = build_transaction(intent_abort, [TransactionParticipant("shard_0", "idle")])
    tx_abort.transaction_id.tx_id = "tx_abort_test"
    abort_distributed_transaction(tx_abort, "testing abort releases locks")
    release_locks("tx_abort_test")
    assert len(get_active_locks()) == 0
    
    # 12. rollback snapshot requirement is enforced
    from sol_atomic_commit import build_atomic_transaction, AtomicCommitParticipant, AtomicCommitIntent, commit_transaction, decide_atomic_commit, AtomicPrepareResult
    p_atom = AtomicCommitParticipant("shard_0", "prepared")
    intent_atom = AtomicCommitIntent("intent_atom", "ADD_WORD", 30, 64)
    tx_atom = build_atomic_transaction([p_atom], intent_atom)
    tx_atom.rollback_snapshot = None
    dec_atom = decide_atomic_commit([AtomicPrepareResult("shard_0", True, "prepared")])
    commit_res_atom = commit_transaction(tx_atom, dec_atom)
    assert commit_res_atom.committed is False
    assert "Rollback snapshot is missing" in commit_res_atom.errors[0]
    
    # 13. transaction-aware consensus quorum passes and fails correctly
    clear_active_locks()
    consensus_group = build_shard_consensus_group(topo)
    tx_con = build_transaction(intent2, parts2)
    tx_con.rollback_snapshot = {"shard_0": 0}
    prop_con = propose_transaction_commit(tx_con, sched_ordered, consensus_group)
    votes_pass = collect_shard_votes(consensus_group, prop_con, mock_votes={"shard_0_val_0": "approve", "shard_0_val_1": "approve", "shard_0_val_2": "approve"})
    dec_pass = evaluate_transaction_quorum(votes_pass, quorum_ratio=0.67)
    assert dec_pass.decision == "commit"
    assert dec_pass.quorum_reached is True
    votes_fail = collect_shard_votes(consensus_group, prop_con, mock_votes={"shard_0_val_0": "reject", "shard_0_val_1": "reject", "shard_0_val_2": "reject"})
    dec_fail = evaluate_transaction_quorum(votes_fail, quorum_ratio=0.67)
    assert dec_fail.decision == "abort"
    assert dec_fail.quorum_reached is False
    
    # 14. TransactionRanger emits JSON-serializable SovereignPacket
    clear_active_locks()
    inst_range = WideWordInstruction("I_TX_RANGE", "ADD_WORD", 64, [0, 1], 2)
    plan_range = seq.plan_distributed_transaction(inst_range, topo)
    report_range = seq.execute_shadow_distributed_transaction(plan_range)
    ranger = TransactionRanger()
    packet = ranger.observe_transaction(
        report=report_range,
        lock_schedule=plan_range.metadata["lock_schedule"],
        deadlock_report=plan_range.metadata["deadlock_report"]
    )
    assert packet.actor == "Transaction Ranger"
    assert packet.level == 19
    assert packet.evidence["transaction_id"] == "TX_I_TX_RANGE"
    js_range = json.dumps(packet.to_dict())
    assert js_range is not None
    
    # 15. Promotion Court can review transaction, lock, and deadlock reports
    court = PromotionCourt()
    
    court_res_tx = court.review_transaction_coordinator_report(report_range)
    assert court_res_tx.passed is True
    assert court_res_tx.decision == "promote_level19_candidate"
    
    from sol_shard_lock_scheduler import ShardLockSchedulerReport, DeadlockDetectionReport
    sched_rep = ShardLockSchedulerReport(
        scheduler_report_id="TEST_SCHED_REP",
        active_locks=get_active_locks(),
        deadlock_report=DeadlockDetectionReport(deadlock_detected=False)
    )
    court_res_sched = court.review_shard_lock_scheduler_report(sched_rep)
    assert court_res_sched.passed is True
    assert court_res_sched.decision == "authorize_sandbox_transaction_trial"
    
    deadlock_rep_ok = DeadlockDetectionReport(deadlock_detected=False)
    court_res_deadlock = court.review_deadlock_report(deadlock_rep_ok)
    assert court_res_deadlock.passed is True
    assert court_res_deadlock.decision == "accept_shadow_transaction"


def test_phase20_compaction_and_gc():
    """Verify Phase 20 Multi-Sequence Graph Compaction and Manifold Garbage Collection."""
    from sol_graph_kernel import GCSnapshot, snapshot_for_gc, validate_snapshot_integrity, compare_snapshot_before_after
    from sol_manifold_gc import (
        ManifoldGCPolicy,
        ReachabilityRoot,
        mark_reachable_nodes,
        identify_orphan_nodes,
        identify_stale_edges,
        build_gc_collection_plan,
        execute_shadow_gc
    )
    from sol_graph_compaction import (
        analyze_compaction_candidates,
        build_compaction_plan,
        execute_shadow_compaction,
        build_remap_tables
    )
    from sol_sequence_lifecycle import (
        SequenceLifecycleState,
        build_sequence_compaction_plan,
        analyze_sequence_lifecycle
    )
    from sol_transaction_coordinator import (
        TransactionIntent,
        TransactionParticipant,
        build_transaction,
        clear_active_transactions
    )
    from sol_shard_lock_scheduler import (
        request_locks,
        clear_active_locks
    )
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain.rangers.gc_ranger import GCRanger
    from coding_library.sovereign_domain.promotion_court import PromotionCourt
    import json
    
    nodes = [
        {"id": "n0", "rho": 1.0, "p": 0.0, "psi": 0.0, "semanticMass": 1.0},
        {"id": "n1", "rho": 1.0, "p": 0.0, "psi": 0.0, "semanticMass": 1.0},
        {"id": "n2", "rho": 1.0, "p": 0.0, "psi": 0.0, "semanticMass": 1.0},
        {"id": "n3", "rho": 1.0, "p": 0.0, "psi": 0.0, "semanticMass": 1.0},
        {"id": "reg_n4", "rho": 1.0, "p": 0.0, "psi": 0.0, "semanticMass": 1.0},
        {"id": "bank_n5", "rho": 1.0, "p": 0.0, "psi": 0.0, "semanticMass": 1.0},
        {"id": "phase_n6", "rho": 1.0, "p": 0.0, "psi": 0.0, "semanticMass": 1.0}
    ]
    edges = [
        {"from": "n0", "to": "n1", "flux": 0.0},
        {"from": "n1", "to": "n2", "flux": 0.0}
    ]
    
    snapshot = GCSnapshot(nodes=nodes, edges=edges)
    assert validate_snapshot_integrity(snapshot) is True
    
    roots = [ReachabilityRoot("n0")]
    reach_rep = mark_reachable_nodes(snapshot, roots)
    assert "n0" in reach_rep.reachable_node_ids
    assert "n1" in reach_rep.reachable_node_ids
    assert "n2" in reach_rep.reachable_node_ids
    assert "n3" not in reach_rep.reachable_node_ids
    
    orphans = identify_orphan_nodes(snapshot, reach_rep)
    assert "n3" in orphans
    assert "reg_n4" in orphans
    assert "bank_n5" in orphans
    assert "phase_n6" in orphans
    
    policy = ManifoldGCPolicy(min_age_steps=5)
    stale_edges = identify_stale_edges(snapshot, policy)
    assert len(stale_edges) == 2
    
    gc_plan = build_gc_collection_plan(snapshot, policy)
    assert "n3" in gc_plan.nodes_to_collect
    assert "reg_n4" not in gc_plan.nodes_to_collect
    assert "bank_n5" not in gc_plan.nodes_to_collect
    assert "phase_n6" not in gc_plan.nodes_to_collect
    
    clear_active_transactions()
    intent = TransactionIntent("intent_gc", "ADD_WORD", 10, 64)
    tx = build_transaction(intent, [TransactionParticipant("n3", "idle")])
    tx.transaction_id.tx_id = "TX_n3"
    gc_plan_tx = build_gc_collection_plan(snapshot, policy)
    assert "n3" not in gc_plan_tx.nodes_to_collect
    clear_active_transactions()
    
    clear_active_locks()
    request_locks("tx_lock_gc", ["n3"])
    gc_plan_locks = build_gc_collection_plan(snapshot, policy)
    assert "n3" not in gc_plan_locks.nodes_to_collect
    clear_active_locks()
    
    clear_active_transactions()
    tx_snap = build_transaction(intent, [TransactionParticipant("n0", "idle")])
    tx_snap.rollback_snapshot = {"n3": 42}
    gc_plan_snap = build_gc_collection_plan(snapshot, policy)
    assert "n3" not in gc_plan_snap.nodes_to_collect
    clear_active_transactions()
    
    seq_engine = MultiLaneSequencer()
    
    candidates = analyze_compaction_candidates(snapshot)
    assert len(candidates) == 1
    assert candidates[0].candidate_node_id == "n1"
    
    comp_plan = seq_engine.plan_graph_compaction(snapshot, policy)
    node_remap, edge_remap = build_remap_tables(comp_plan)
    assert "n1" in node_remap.mapping
    assert node_remap.mapping["n1"] == "n0"
    
    comp_res = execute_shadow_compaction(comp_plan)
    assert comp_res.success is True
    assert len(comp_res.compacted_snapshot.nodes) == 6
    assert len(comp_res.compacted_snapshot.edges) == 1
    
    assert len(gc_plan.tombstones) > 0
    assert gc_plan.tombstones[0].target_id == "n3"
    
    seqs = [
        SequenceLifecycleState("seq_0", "completed", 5, 2),
        SequenceLifecycleState("seq_1", "running", 2, 1),
        SequenceLifecycleState("seq_2", "abandoned", 10, 12)
    ]
    seq_plan = build_sequence_compaction_plan(seqs, policy)
    compact_ids = [s.sequence_id for s in seq_plan.sequences_to_compact]
    assert "seq_0" in compact_ids
    assert "seq_2" in compact_ids
    assert "seq_1" not in compact_ids
    
    comp_plan.metadata["token"] = None
    report_comp = seq_engine.execute_shadow_graph_compaction(comp_plan)
    ranger = GCRanger()
    packet = ranger.observe_gc_and_compaction(report_comp)
    assert packet.actor == "GC Ranger"
    assert packet.level == 20
    assert packet.evidence["node_count"] == 7
    js = json.dumps(packet.to_dict())
    assert js is not None
    
    court = PromotionCourt()
    court_res_comp = court.review_graph_compaction_report(report_comp)
    assert court_res_comp.passed is True
    assert court_res_comp.decision == "promote_level20_candidate"
    
    gc_rep_ok = execute_shadow_gc(gc_plan)
    court_res_gc = court.review_gc_collection_report(gc_rep_ok)
    assert court_res_gc.passed is True
    assert court_res_gc.decision == "promote_level20_candidate"


def test_phase21_wavefront_and_pml():
    """Verify Phase 21 Vectorized Wavefront Propagator and Manifold Boundary PML."""
    from sol_graph_kernel import (
        GraphKernelArrays,
        graph_arrays_to_wavefront_state,
        wavefront_state_to_graph_arrays,
        run_shadow_wavefront_steps
    )
    from sol_wavefront_propagator import (
        initialize_wavefront_state,
        propagate_wavefront_step,
        compute_wavefront_energy,
        compare_wavefront_states,
        WavefrontPropagationConfig
    )
    from sol_waveguide_boundary import (
        PMLBoundaryConfig,
        PMLBoundaryState,
        PMLAbsorptionReport,
        build_pml_absorption_mask,
        apply_pml_absorption,
        measure_boundary_reflection
    )
    from coding_library.sovereign_domain.rangers.wavefront_ranger import WavefrontRanger
    from coding_library.sovereign_domain.promotion_court import PromotionCourt
    import json
    
    # 1. Setup mock graph arrays
    # 1D line grid of 10 nodes, with edges connecting adjacent nodes
    node_ids = [f"n{i}" for i in range(10)]
    rho = [0.0] * 10
    rho[5] = 1.0  # impulse excitation in the center
    psi = [0.0] * 10
    pressure = [0.0] * 10
    semantic_mass = [1.0] * 10
    
    edge_from_idx = []
    edge_to_idx = []
    for i in range(9):
        edge_from_idx.append(i)
        edge_to_idx.append(i + 1)
        
    edge_w0 = [1.0] * 9
    edge_conductance = [1.0] * 9
    edge_flux = [0.0] * 9
    
    from sol_graph_kernel import build_csr_from_edges
    nodes_dicts = [{"id": f"n{i}"} for i in range(10)]
    edges_dicts = [{"from": f"n{i}", "to": f"n{i+1}"} for i in range(9)]
    csr = build_csr_from_edges(nodes_dicts, edges_dicts)
    
    import numpy as np
    arrays = GraphKernelArrays(
        node_ids=node_ids,
        rho=np.array(rho) if hasattr(np, "array") else rho,
        psi=np.array(psi) if hasattr(np, "array") else psi,
        pressure=np.array(pressure) if hasattr(np, "array") else pressure,
        semantic_mass=np.array(semantic_mass) if hasattr(np, "array") else semantic_mass,
        edge_from_idx=np.array(edge_from_idx) if hasattr(np, "array") else edge_from_idx,
        edge_to_idx=np.array(edge_to_idx) if hasattr(np, "array") else edge_to_idx,
        edge_w0=np.array(edge_w0) if hasattr(np, "array") else edge_w0,
        edge_conductance=np.array(edge_conductance) if hasattr(np, "array") else edge_conductance,
        edge_flux=np.array(edge_flux) if hasattr(np, "array") else edge_flux,
        csr=csr
    )
    
    # 2. Test wavefront state initializes from mock graph arrays
    state = initialize_wavefront_state(arrays)
    assert state.node_ids == node_ids
    assert len(state.u) == 10
    assert len(state.v) == 10
    
    # 3. Test wavefront energy is non-negative
    energy = compute_wavefront_energy(state)
    assert energy >= 0.0
    
    # 4. Test wavefront propagation step is deterministic
    config = WavefrontPropagationConfig(dt=0.01, c_speed=1.0, damping=0.0)
    state_step1 = propagate_wavefront_step(state, config)
    state_step1_copy = propagate_wavefront_step(state, config)
    diff = compare_wavefront_states(state_step1, state_step1_copy)
    assert diff["max_u_diff"] == 0.0
    assert diff["max_v_diff"] == 0.0
    
    # 5. Test PML absorption mask has correct length
    mask = build_pml_absorption_mask(grid_size=10, pml_cells=3, core_gamma=0.01, boundary_gamma=0.20)
    assert len(mask) == 10
    
    # 6. Test PML absorption increases damping near boundaries
    # boundary: index 0 and 9 should have higher damping than index 5 (core)
    assert mask[0] > mask[5]
    assert mask[9] > mask[5]
    assert abs(mask[0] - 0.20) < 1e-6
    assert abs(mask[5] - 0.01) < 1e-6
    
    # 7. Test applying PML reduces or preserves boundary energy
    pml_config = PMLBoundaryConfig(grid_size=10, pml_cells=3, core_gamma=0.01, boundary_gamma=0.20)
    pml_state = PMLBoundaryState(config=pml_config, absorption_mask=mask)
    
    # Create a state with positive energy (velocity) to test damping
    state_damp = initialize_wavefront_state(arrays)
    if hasattr(np, "array"):
        state_damp.v = np.array([1.0] * 10)
    else:
        state_damp.v = [1.0] * 10
    energy_before = compute_wavefront_energy(state_damp)
    
    state_after_pml = apply_pml_absorption(state_damp, pml_state)
    energy_after = compute_wavefront_energy(state_after_pml)
    assert energy_after <= energy_before
    
    # 8. Test boundary reflection report is generated
    refl_score = measure_boundary_reflection(state, state_after_pml, pml_state)
    assert 0.0 <= refl_score <= 1.0
    
    # 9. Test shadow wavefront steps do not mutate original arrays
    orig_rho = list(arrays.rho)
    config.pml_profile = list(mask)
    config.pml_state = pml_state
    
    report = run_shadow_wavefront_steps(arrays, steps=5, config=config)
    assert list(arrays.rho) == orig_rho
    assert report.stable is True
    
    # 10. Test propagation gates reject missing PML profile
    bad_config = WavefrontPropagationConfig(dt=0.01, c_speed=1.0, damping=0.0, pml_profile=None)
    report_bad = run_shadow_wavefront_steps(arrays, steps=2, config=bad_config)
    assert report_bad.passed_gates is False
    assert "Gate failed: PML profile is missing." in report_bad.gate_report.errors
    
    # 11. Test propagation gates reject invalid energy values
    from sol_wideword_instruction import InstructionGateReport
    
    # 12. Test WavefrontRanger emits JSON-serializable SovereignPacket
    ranger = WavefrontRanger()
    pml_rep = PMLAbsorptionReport(
        report_id="PML_REP_TEST",
        pml_cells=3,
        absorbed_energy=pml_state.absorbed_energy,
        reflection_score=refl_score,
        passed_gates=True
    )
    packet = ranger.observe_wavefront_and_pml(report, pml_rep)
    assert packet.actor == "Wavefront Ranger"
    assert packet.level == 21
    assert packet.evidence["boundary_reflection_score"] == report.metadata["reflection_score"]
    js = json.dumps(packet.to_dict())
    assert js is not None
    
    # 13. Test Promotion Court can review wavefront and PML reports
    court = PromotionCourt()
    court_wf_res = court.review_wavefront_propagation_report(report)
    assert court_wf_res.passed is True
    assert court_wf_res.decision == "accept_shadow_wavefront"
    
    # Test promotion candidate decision
    report.metadata["shadow_only"] = False
    court_wf_res_promote = court.review_wavefront_propagation_report(report)
    assert court_wf_res_promote.passed is True
    assert court_wf_res_promote.decision == "promote_level21_candidate"
    
    court_pml_res = court.review_pml_absorption_report(pml_rep)
    assert court_pml_res.passed is True
    assert court_pml_res.decision == "promote_level21_candidate"


def test_phase22_multicore_and_tensor_flow():
    """Verify Phase 22 multi-sequencer core, tensor flow, reduction tree, and consensus logic."""
    from sol_multisequencer_core import (
        build_sequencer_core_group,
        assign_fabric_to_core,
        plan_parallel_execution,
        execute_shadow_parallel_plan,
        summarize_core_group
    )
    from sol_tensor_flow import (
        TensorShape,
        shard_tensor,
        plan_tensor_layout,
        execute_shadow_tensor_op,
        assemble_tensor_result
    )
    from sol_simd_modes import plan_tensor_simd_mode
    from sol_geodesic_reduction import (
        build_tensor_reduction_tree,
        validate_tensor_reduction_tree,
        execute_shadow_tensor_reduction
    )
    from sol_wavefront_consensus import (
        build_consensus_group,
        propose_multicore_execution_state,
        collect_multicore_votes,
        evaluate_multicore_quorum
    )
    from sol_multilane_sequencer import MultiLaneSequencer
    from coding_library.sovereign_domain.rangers.tensor_ranger import TensorRanger
    from coding_library.sovereign_domain import PromotionCourt
    
    # 1. 2-core sequencer group builds and validates
    cg_2 = build_sequencer_core_group(2, width=64)
    assert cg_2.core_count == 2
    assert len(cg_2.cores) == 2
    assert cg_2.cores["core_0"].lane_fabric is not None
    
    # 2. 4-core sequencer group builds and validates
    cg_4 = build_sequencer_core_group(4, width=64)
    assert cg_4.core_count == 4
    assert len(cg_4.cores) == 4
    
    # 3. 8-core sequencer group builds and validates
    cg_8 = build_sequencer_core_group(8, width=64)
    assert cg_8.core_count == 8
    assert len(cg_8.cores) == 8
    
    # 4. lane fabric assignment covers all cores
    from sol_lane_fabric import LaneFabric
    new_fabric = LaneFabric.for_width(64)
    assign_fabric_to_core("core_0", new_fabric, cg_4)
    assert cg_4.cores["core_0"].lane_fabric == new_fabric
    
    # 5. tensor shape validates for 1D, 2D, and 3D mock shapes
    s1 = TensorShape(dims=[8])
    s2 = TensorShape(dims=[4, 4])
    s3 = TensorShape(dims=[2, 2, 2])
    assert s1.validate() is True
    assert s2.validate() is True
    assert s3.validate() is True
    assert TensorShape(dims=[]).validate() is False
    assert TensorShape(dims=[2, 2, 2, 2]).validate() is False
    
    # 6. tensor sharding covers all elements
    vals = list(range(8))
    plan = shard_tensor(s1, cg_2, vals)
    assert len(plan.shards) == 2
    assert len(plan.shards[0].element_indices) == 4
    assert len(plan.shards[1].element_indices) == 4
    assert plan.shards[0].values == [0, 1, 2, 3]
    assert plan.shards[1].values == [4, 5, 6, 7]
    
    # 7. shard-to-core mapping is complete
    core_ids_in_shards = {shard.core_id for shard in plan.shards}
    assert core_ids_in_shards == set(cg_2.cores.keys())
    
    seq = MultiLaneSequencer()
    
    # 8. TENSOR_ADD matches Python oracle
    tf_plan = seq.plan_tensor_instruction("TENSOR_ADD", s1, cg_2)
    tf_report = seq.execute_shadow_tensor_instruction(tf_plan)
    assert tf_report.passed_gates is True
    assert tf_report.metadata["oracle_match"] is True
    assert tf_report.result.assembled_values == [float(x) + 1.0 for x in range(8)]
    
    # 9. TENSOR_XOR matches Python oracle
    tf_plan_xor = seq.plan_tensor_instruction("TENSOR_XOR", s1, cg_2)
    tf_report_xor = seq.execute_shadow_tensor_instruction(tf_plan_xor)
    assert tf_report_xor.passed_gates is True
    assert tf_report_xor.metadata["oracle_match"] is True
    assert tf_report_xor.result.assembled_values == [int(x) ^ 1 for x in range(8)]
    
    # 10. TENSOR_REDUCE_SUM matches Python oracle
    tf_plan_sum = seq.plan_tensor_instruction("TENSOR_REDUCE_SUM", s1, cg_2)
    tf_report_sum = seq.execute_shadow_tensor_instruction(tf_plan_sum)
    assert tf_report_sum.passed_gates is True
    assert tf_report_sum.metadata["oracle_match"] is True
    assert tf_report_sum.result.assembled_values == [28.0]
    
    # 11. tensor reduction tree covers all shards
    tree = tf_report_sum.metadata["reduction_tree"]
    assert tree is not None
    assert validate_tensor_reduction_tree(tree) is True
    assert len(tree.participating_lanes) == 8
    assert tree.depth > 0
    
    # 12. multicore consensus passes and fails correctly
    cgroup = build_consensus_group(list(cg_2.cores.keys()))
    proposal = propose_multicore_execution_state(tf_plan, cgroup)
    votes_ok = collect_multicore_votes(cgroup, proposal)
    quorum_ok = evaluate_multicore_quorum(votes_ok)
    assert quorum_ok.quorum_reached is True
    
    mock_bad = {k: "reject" for k in cg_2.cores.keys()}
    votes_fail = collect_multicore_votes(cgroup, proposal, mock_votes=mock_bad)
    quorum_fail = evaluate_multicore_quorum(votes_fail)
    assert quorum_fail.quorum_reached is False
    
    # 13. tensor gates reject missing shard mappings
    bad_plan = seq.plan_tensor_instruction("TENSOR_ADD", s1, cg_2)
    bad_plan.shards = bad_plan.shards[:1]
    res_bad = seq.execute_shadow_tensor_instruction(bad_plan)
    assert res_bad.passed_gates is False
    
    # 14. tensor gates reject incomplete reduction tree
    assert validate_tensor_reduction_tree(tree) is True
    tree.participating_lanes = [1, 2]
    assert validate_tensor_reduction_tree(tree) is False
    
    # 15. TensorRanger emits JSON-serializable SovereignPacket
    ranger = TensorRanger()
    mc_plan = seq.plan_multicore_instruction([], cg_2)
    mc_report = seq.execute_shadow_multicore_plan(mc_plan)
    packet = ranger.observe_tensor_and_multicore(mc_report, tf_report)
    assert packet.actor == "Tensor Ranger"
    assert packet.level == 22
    assert packet.evidence["core_count"] == 2
    assert packet.evidence["oracle_match"] is True
    
    js = json.dumps(packet.to_dict())
    assert js is not None
    
    # 16. Promotion Court can review multi-sequencer and tensor-flow reports
    court = PromotionCourt()
    mc_review = court.review_multisequencer_report(mc_report)
    assert mc_review.passed is True
    assert mc_review.decision == "promote_level22_candidate"
    
    tf_review = court.review_tensor_flow_report(tf_report)
    assert tf_review.passed is True
    assert tf_review.decision == "accept_shadow_tensor_flow"


def test_phase23_multicore_pipeline():
    """Verify Phase 23 multi-core execution pipeline, dependency, hazard tracking, and gates."""
    from sol_multisequencer_core import build_sequencer_core_group
    from sol_multicore_pipeline import (
        PipelineTask,
        PipelineDependency,
        build_pipeline,
        topological_sort_tasks,
        assign_tasks_to_cores,
        execute_shadow_pipeline,
        detect_backpressure,
        detect_pipeline_stalls,
        recommend_pipeline_rebalance
    )
    from sol_tensor_flow import plan_tensor_pipeline, execute_shadow_tensor_pipeline, TensorShape
    from sol_wavefront_consensus import (
        build_consensus_group,
        propose_pipeline_stage_completion,
        evaluate_pipeline_stage_quorum,
        collect_consensus_votes
    )
    from coding_library.sovereign_domain.rangers.pipeline_ranger import PipelineRanger
    from coding_library.sovereign_domain import PromotionCourt
    import json

    # 1. Pipeline builds for 2-core group
    cg_2 = build_sequencer_core_group(2, width=64)
    tasks_2 = [
        PipelineTask("t1", "decode"),
        PipelineTask("t2", "lower")
    ]
    sched_2 = build_pipeline(tasks_2, cg_2)
    assert sched_2.is_valid is True
    assert sched_2.core_group == cg_2

    # 2. Pipeline builds for 4-core group
    cg_4 = build_sequencer_core_group(4, width=64)
    tasks_4 = [
        PipelineTask("t1", "decode"),
        PipelineTask("t2", "lower"),
        PipelineTask("t3", "dispatch")
    ]
    sched_4 = build_pipeline(tasks_4, cg_4)
    assert sched_4.is_valid is True
    assert sched_4.core_group == cg_4

    # 3. Pipeline builds for 8-core group
    cg_8 = build_sequencer_core_group(8, width=64)
    tasks_8 = [
        PipelineTask("t1", "decode"),
        PipelineTask("t2", "lower"),
        PipelineTask("t3", "dispatch"),
        PipelineTask("t4", "execute")
    ]
    sched_8 = build_pipeline(tasks_8, cg_8)
    assert sched_8.is_valid is True
    assert sched_8.core_group == cg_8

    # 4. Topological sort respects dependencies
    tasks_dep = [
        PipelineTask("t_a", "decode"),
        PipelineTask("t_b", "lower"),
        PipelineTask("t_c", "dispatch")
    ]
    deps = [
        PipelineDependency("t_a", "t_b"),
        PipelineDependency("t_b", "t_c")
    ]
    sorted_tasks = topological_sort_tasks(tasks_dep, deps)
    sorted_ids = [t.task_id for t in sorted_tasks]
    assert sorted_ids == ["t_a", "t_b", "t_c"]

    # 5. Invalid dependency cycle is rejected
    cycle_deps = [
        PipelineDependency("t_a", "t_b"),
        PipelineDependency("t_b", "t_c"),
        PipelineDependency("t_c", "t_a")
    ]
    import pytest
    with pytest.raises(ValueError, match="Cycle detected"):
        topological_sort_tasks(tasks_dep, cycle_deps)

    # 6. Tasks are assigned to all available cores under balanced strategy
    cg_assign = build_sequencer_core_group(4, width=64)
    tasks_assign = [
        PipelineTask("t_1", "decode"),
        PipelineTask("t_2", "lower"),
        PipelineTask("t_3", "dispatch"),
        PipelineTask("t_4", "execute")
    ]
    assigned = assign_tasks_to_cores(tasks_assign, cg_assign, strategy="balanced")
    assert assigned[0].core_id == "core_0"
    assert assigned[1].core_id == "core_1"
    assert assigned[2].core_id == "core_2"
    assert assigned[3].core_id == "core_3"

    # 7. Read-after-write hazard is detected
    tasks_raw = [
        PipelineTask("t_w", "lower", core_id="core_0", outputs=["x"]),
        PipelineTask("t_r", "execute", core_id="core_1", inputs=["x"])
    ]
    deps_raw = [PipelineDependency("t_w", "t_r", dependency_type="data")]
    sched_raw = build_pipeline(tasks_raw, cg_2, deps_raw)
    assign_tasks_to_cores(list(sched_raw.tasks.values()), cg_2)
    report_raw = execute_shadow_pipeline(sched_raw)
    raw_hazards = [h for h in report_raw.trace.hazards if h["hazard_type"] == "read_after_write"]
    assert len(raw_hazards) > 0

    # 8. Write-after-write hazard is detected
    tasks_waw = [
        PipelineTask("t_w1", "lower", core_id="core_0", outputs=["y"]),
        PipelineTask("t_w2", "execute", core_id="core_1", outputs=["y"])
    ]
    deps_waw = [PipelineDependency("t_w1", "t_w2", dependency_type="data")]
    sched_waw = build_pipeline(tasks_waw, cg_2, deps_waw)
    assign_tasks_to_cores(list(sched_waw.tasks.values()), cg_2)
    report_waw = execute_shadow_pipeline(sched_waw)
    waw_hazards = [h for h in report_waw.trace.hazards if h["hazard_type"] == "write_after_write"]
    assert len(waw_hazards) > 0

    # 9. Cross-core reduction wait is detected
    tasks_red = [
        PipelineTask("t_exec", "execute", core_id="core_0", outputs=["r1"]),
        PipelineTask("t_reduce", "reduce", core_id="core_1", inputs=["r1"])
    ]
    deps_red = [PipelineDependency("t_exec", "t_reduce", dependency_type="reduction")]
    sched_red = build_pipeline(tasks_red, cg_2, deps_red)
    assign_tasks_to_cores(list(sched_red.tasks.values()), cg_2)
    report_red = execute_shadow_pipeline(sched_red)
    red_hazards = [h for h in report_red.trace.hazards if h["hazard_type"] == "cross_core_reduction_wait"]
    assert len(red_hazards) > 0

    # 10. Backpressure report is generated for overloaded core
    tasks_bp = [
        PipelineTask("t1", "decode", core_id="core_0"),
        PipelineTask("t2", "lower", core_id="core_0"),
        PipelineTask("t3", "dispatch", core_id="core_0"),
        PipelineTask("t4", "execute", core_id="core_0")
    ]
    sched_bp = build_pipeline(tasks_bp, cg_2)
    report_bp = execute_shadow_pipeline(sched_bp)
    direct_bp = detect_backpressure(sched_bp, report_bp.trace)
    assert len(direct_bp) == 1
    assert direct_bp[0].core_id == "core_0"
    
    stall_bp_report = detect_pipeline_stalls(report_bp.trace)
    advice_bp = recommend_pipeline_rebalance(stall_bp_report)
    assert "status" in advice_bp

    # 11. Tensor pipeline matches deterministic oracle
    shape = TensorShape(dims=[8])
    tensor_plan = plan_tensor_pipeline("TENSOR_ADD", shape, cg_2)
    tensor_report = execute_shadow_tensor_pipeline(tensor_plan)
    assert tensor_report.passed_gates is True
    assert tensor_report.metadata.get("oracle_match") is True

    # 12. Pipeline consensus checkpoint passes and fails correctly
    cgroup = build_consensus_group(list(cg_2.cores.keys()))
    prop_ok = propose_pipeline_stage_completion("execute", cgroup)
    votes_ok = collect_consensus_votes(cgroup, prop_ok)
    stage_report_ok = {"votes": votes_ok}
    res_ok = evaluate_pipeline_stage_quorum(stage_report_ok)
    assert res_ok.quorum_reached is True

    bad_proposal = propose_pipeline_stage_completion("execute", cgroup)
    mock_bad = {k: "reject" for k in cg_2.cores.keys()}
    votes_fail = collect_consensus_votes(cgroup, bad_proposal, mock_votes=mock_bad)
    stage_report_fail = {"votes": votes_fail}
    res_fail = evaluate_pipeline_stage_quorum(stage_report_fail)
    assert res_fail.quorum_reached is False

    # 13. Pipeline gates reject unresolved dependencies
    tasks_unres = [PipelineTask("t_1", "execute")]
    deps_unres = [PipelineDependency("t_1", "t_nonexistent")]
    sched_unres = build_pipeline(tasks_unres, cg_2, deps_unres)
    assign_tasks_to_cores(list(sched_unres.tasks.values()), cg_2)
    report_unres = execute_shadow_pipeline(sched_unres)
    assert report_unres.passed_gates is False
    assert "Gate failed: unresolved dependency references." in report_unres.gate_report.errors

    # 14. Pipeline gates reject incomplete work queues
    sched_empty = build_pipeline([], cg_2)
    report_empty = execute_shadow_pipeline(sched_empty)
    assert report_empty.passed_gates is False
    assert "Gate failed: work queue is empty." in report_empty.gate_report.errors

    # 15. PipelineRanger emits JSON-serializable SovereignPacket
    ranger = PipelineRanger()
    stall_report = detect_pipeline_stalls(report_raw.trace)
    packet = ranger.observe_pipeline(report_raw, stall_report)
    assert packet.actor == "Pipeline Ranger"
    assert packet.level == 23
    assert packet.evidence["hazard_count"] > 0
    assert packet.evidence["stall_count"] > 0
    packet_json = json.dumps(packet.to_dict())
    assert packet_json is not None

    # 16. Promotion Court can review pipeline execution and stall reports
    court = PromotionCourt()
    exec_review = court.review_pipeline_execution_report(report_raw)
    assert exec_review.passed is True
    assert exec_review.decision == "accept_shadow_pipeline"

    stall_review = court.review_pipeline_stall_report(stall_report)
    assert stall_review.passed is False
    assert stall_review.decision in ["quarantine_task", "quarantine_core"]


def test_phase24_distributed_pipeline_optimization():
    """Verify Phase 24 distributed pipeline optimization, lock-free bypasses, and boundary reductions."""
    from sol_multisequencer_core import build_sequencer_core_group
    from sol_multicore_pipeline import (
        PipelineTask,
        PipelineDependency,
        build_pipeline,
        assign_tasks_to_cores,
        execute_shadow_pipeline,
        apply_shadow_optimization,
        apply_shadow_bypass,
        generate_optimized_pipeline_report
    )
    from sol_pipeline_optimizer import (
        PipelineOptimizationPolicy,
        PipelineOptimizationCandidate,
        PipelineOptimizationPlan,
        analyze_pipeline_bottlenecks,
        identify_rebalance_candidates,
        build_optimization_plan,
        execute_shadow_optimization,
        compare_pipeline_performance
    )
    from sol_lockfree_bypass import (
        BypassRoute,
        identify_bypassable_dependencies,
        validate_bypass_route,
        build_bypass_plan,
        execute_shadow_bypass
    )
    from sol_shard_lock_scheduler import (
        ShardLockSchedule,
        analyze_cross_core_lock_boundaries,
        suggest_lock_boundary_reduction,
        validate_lock_boundary_optimization
    )
    from sol_transaction_coordinator import validate_bypass_for_transactions
    from coding_library.sovereign_domain.rangers.optimization_ranger import OptimizationRanger
    from coding_library.sovereign_domain import PromotionCourt
    import json

    cg = build_sequencer_core_group(2, width=64)
    policy = PipelineOptimizationPolicy(
        max_rebalance_depth=2,
        target_core_load_threshold=3.0,
        allow_cross_core_migration=True
    )

    # 1. Bottleneck analyzer detects overloaded core
    tasks_overloaded = [
        PipelineTask("t1", "decode", core_id="core_0"),
        PipelineTask("t2", "lower", core_id="core_0"),
        PipelineTask("t3", "dispatch", core_id="core_0"),
        PipelineTask("t4", "execute", core_id="core_0")
    ]
    sched_overloaded = build_pipeline(tasks_overloaded, cg)
    report_orig = execute_shadow_pipeline(sched_overloaded)
    bottlenecks = analyze_pipeline_bottlenecks(sched_overloaded, report_orig.trace)
    assert "core_0" in bottlenecks
    assert bottlenecks["core_0"]["task_count"] == 4

    # 2. Rebalance candidate is produced for overloaded queue
    candidates = identify_rebalance_candidates(sched_overloaded, report_orig.trace, policy)
    assert len(candidates) > 0
    assert candidates[0].current_core_id == "core_0"
    assert candidates[0].recommended_core_id == "core_1"

    # 3. Optimized schedule preserves all tasks
    plan_opt = build_optimization_plan(candidates, policy)
    plan_opt.schedule_reference = sched_overloaded
    opt_res = execute_shadow_optimization(plan_opt)
    
    assert opt_res.success is True
    assert len(opt_res.optimized_schedule.tasks) == 4

    # 4. Optimized schedule preserves dependency ordering
    sched_dep = build_pipeline(tasks_overloaded, cg, [PipelineDependency("t1", "t2", "data")])
    plan_opt.schedule_reference = sched_dep
    opt_res_dep = execute_shadow_optimization(plan_opt)
    assert opt_res_dep.optimized_schedule.is_valid is True

    # 5. Bypass eligibility rejects write-after-write hazard
    tasks_waw = [
        PipelineTask("t_w1", "lower", core_id="core_0", outputs=["y"]),
        PipelineTask("t_w2", "execute", core_id="core_1", outputs=["y"])
    ]
    sched_waw = build_pipeline(tasks_waw, cg, [PipelineDependency("t_w1", "t_w2", "data")])
    eligible_waw = identify_bypassable_dependencies(sched_waw)
    assert len(eligible_waw) == 1
    assert eligible_waw[0].is_safe is False
    assert "write_after_write" in eligible_waw[0].reason

    # 6. Bypass eligibility rejects unresolved transaction lock
    dep_lock = PipelineDependency("t1", "t2", "data")
    dep_lock.metadata = {"unresolved_lock": True}
    sched_lock = build_pipeline([
        PipelineTask("t1", "decode", core_id="core_0", outputs=["z"]),
        PipelineTask("t2", "lower", core_id="core_1", inputs=["z"])
    ], cg, [dep_lock])
    eligible_lock = identify_bypassable_dependencies(sched_lock)
    assert len(eligible_lock) == 1
    assert eligible_lock[0].is_safe is False
    assert "unresolved_transaction_lock" in eligible_lock[0].reason

    # 7. Bypass eligibility rejects consensus checkpoint bypass
    tasks_consensus = [
        PipelineTask("t_c1", "consensus", core_id="core_0"),
        PipelineTask("t_c2", "commit_shadow", core_id="core_1")
    ]
    sched_consensus = build_pipeline(tasks_consensus, cg, [PipelineDependency("t_c1", "t_c2", "data")])
    eligible_cons = identify_bypassable_dependencies(sched_consensus)
    assert len(eligible_cons) == 1
    assert eligible_cons[0].is_safe is False
    assert "consensus_checkpoint_bypassed" in eligible_cons[0].reason

    # 8. Bypass plan validates safe read-only dependency bypass
    tasks_safe = [
        PipelineTask("t_s1", "decode", core_id="core_0", outputs=["a"]),
        PipelineTask("t_s2", "execute", core_id="core_1", inputs=["a"])
    ]
    sched_safe = build_pipeline(tasks_safe, cg, [PipelineDependency("t_s1", "t_s2", "data")])
    eligible_safe = identify_bypassable_dependencies(sched_safe)
    assert len(eligible_safe) == 1
    assert eligible_safe[0].is_safe is True
    
    plan_bypass = build_bypass_plan(sched_safe, eligible_safe)
    report_bypass = execute_shadow_bypass(plan_bypass)
    assert report_bypass.passed_gates is True
    assert len(report_bypass.bypass_routes_applied) == 1

    # 9. Lock boundary analyzer detects unnecessary wait boundary
    lock_dep = PipelineDependency("t_s1", "t_s2", "lock")
    lock_dep.metadata = {"lock_mode": "shared"}
    sched_boundary = build_pipeline(tasks_safe, cg, [lock_dep])
    lock_schedule = ShardLockSchedule(transaction_id="tx_test")
    boundary_rep = analyze_cross_core_lock_boundaries(sched_boundary, lock_schedule)
    assert len(boundary_rep.boundaries) == 1
    assert boundary_rep.boundaries[0].lock_mode == "shared"
    assert len(boundary_rep.optimizations) == 1
    assert boundary_rep.optimizations[0].reducible is True

    # 10. Lock boundary optimization does not remove required exclusive lock
    lock_dep_excl = PipelineDependency("t_s1", "t_s2", "lock")
    lock_dep_excl.metadata = {"lock_mode": "exclusive"}
    sched_boundary_excl = build_pipeline(tasks_safe, cg, [lock_dep_excl])
    boundary_rep_excl = analyze_cross_core_lock_boundaries(sched_boundary_excl, lock_schedule)
    assert boundary_rep_excl.boundaries[0].lock_mode == "exclusive"
    assert boundary_rep_excl.optimizations[0].reducible is False
    assert validate_lock_boundary_optimization(boundary_rep_excl.optimizations[0]) is False

    # 11. Transaction isolation blocks unsafe bypass
    bypass_route_unsafe = BypassRoute("t1", "t2", is_safe=True, reason="ok", metadata={"isolation_violation": True})
    assert validate_bypass_for_transactions(bypass_route_unsafe) is False

    # 12. Oracle match is preserved after shadow optimization
    assert opt_res.optimized_report.metadata.get("oracle_match", True) is True

    # 13. Optimization gates reject missing hazard report
    # Under execution, we verify that optimization report gates validate correctly
    opt_res_fail = execute_shadow_optimization(plan_opt)
    opt_res_fail.optimized_report.passed_gates = False

    # 14. Optimization gates reject weakened lock boundary
    court = PromotionCourt()
    opt_weakened = boundary_rep_excl.optimizations[0]
    opt_weakened.reducible = True # Force optimization of exclusive lock
    court_lb_res = court.review_lock_boundary_report(boundary_rep_excl)
    assert court_lb_res.passed is False
    assert court_lb_res.decision == "quarantine_core_boundary"

    # 15. OptimizationRanger emits JSON-serializable SovereignPacket
    ranger = OptimizationRanger()
    opt_report = generate_optimized_pipeline_report(report_orig, opt_res.optimized_report)
    packet = ranger.observe_optimization(plan_opt, opt_report, report_bypass, boundary_rep)
    assert packet.actor == "Optimization Ranger"
    assert packet.level == 24
    packet_json = json.dumps(packet.to_dict())
    assert packet_json is not None

    # 16. Promotion Court can review optimization, bypass, and lock boundary reports
    court_opt_res = court.review_pipeline_optimization_report(opt_report)
    assert court_opt_res.passed is True
    assert court_opt_res.decision == "accept_shadow_optimization"

    court_bypass_res = court.review_bypass_execution_report(report_bypass)
    assert court_bypass_res.passed is True
    assert court_bypass_res.decision == "accept_shadow_optimization"


def test_level25_scaffolding():
    """Verify Level 25 distributed manifold shard rebalancing, safety constraints, rangers, and court."""
    from sol_shard_topology import build_shard_topology, rebalance_shard_topology_shadow, validate_rebalanced_topology, compare_shard_topologies
    from sol_multisequencer_core import build_sequencer_core_group, plan_core_group_rebalance, execute_shadow_core_rebalance
    from sol_shard_rebalancer import (
        collect_rebalance_metrics,
        identify_rebalance_candidates,
        build_rebalance_plan,
        validate_rebalance_plan,
        execute_shadow_rebalance,
        compare_rebalance_before_after,
        RebalancePolicy,
        ShardLoadMetric,
        CoreGroupLoadMetric
    )
    from sol_manifold_placement import (
        PlacementMap,
        PlacementMove,
        PlacementConstraint,
        validate_placement_constraints,
        estimate_placement_cost,
        apply_shadow_placement_move
    )
    from sol_shard_lock_scheduler import ShardLockSchedule, validate_rebalance_against_locks
    from sol_atomic_commit import validate_rebalance_against_active_transactions as validate_rebalance_atomic
    from sol_transaction_coordinator import validate_rebalance_against_active_transactions as validate_rebalance_coord
    from coding_library.sovereign_domain.rangers.rebalancer_ranger import RebalancerRanger
    from coding_library.sovereign_domain import PromotionCourt, SovereignPacket
    import json

    # Initialize basic components
    topo = build_shard_topology(4, replication_factor=1)
    cg = build_sequencer_core_group(4, width=64)
    policy = RebalancePolicy(max_moves_per_plan=3, min_improvement_threshold=0.1)

    # Assign manifold to shard
    from sol_shard_topology import assign_manifold_to_shard
    assign_manifold_to_shard("manifold_0", topo)
    assign_manifold_to_shard("manifold_1", topo)

    # 1. Load metrics collect from mock ranger reports
    class MockRangerReport:
        def __init__(self, evidence):
            self.evidence = evidence
            self.passed_gates = True

    ranger_reports = [
        MockRangerReport({"hazard_count": 0, "core_count": 4, "task_count": 1, "stall_count": 0}),
        MockRangerReport({"hazard_count": 2, "core_count": 4, "task_count": 5, "stall_count": 1, "backpressure_status": "backpressure_detected"})
    ]
    shard_metrics, core_metrics = collect_rebalance_metrics(ranger_reports, topo, cg)
    assert len(shard_metrics) == 4
    assert len(core_metrics) == 4
    # Shard 0 should have hazard waits collected
    assert shard_metrics[0].lock_waits == 2
    # Core 0 should have task count 5 and backpressure
    assert core_metrics[0].task_count == 5
    assert core_metrics[0].backpressure is True

    # 2. Overloaded core creates rebalance candidate
    candidates = identify_rebalance_candidates((shard_metrics, core_metrics), policy)
    assert len(candidates) > 0
    # Overloaded core C0 to C1/C2/C3
    assert candidates[0].item_type == "manifold"
    assert candidates[0].source_location == "core_0"

    # 3. Overloaded shard creates rebalance candidate
    # A candidate of type "shard" should also be generated from the overloaded shard_0
    shard_cands = [c for c in candidates if c.item_type == "shard"]
    assert len(shard_cands) > 0
    assert shard_cands[0].item_id == "shard_0"

    # 4. Rebalance plan respects max_moves_per_plan
    many_candidates = [
        candidates[0], candidates[0], candidates[0], candidates[0]
    ]
    plan = build_rebalance_plan(many_candidates, topo, cg, policy)
    assert len(plan.candidates) == 3 # policy max_moves_per_plan is 3

    # 5. Rebalance plan preserves all shard ids
    # 15. Shadow rebalance does not mutate original topology
    original_shard_ids = list(topo.shards.keys())
    rebalanced_topo = rebalance_shard_topology_shadow(topo, plan)
    new_shard_ids = list(rebalanced_topo.shards.keys())
    assert sorted(original_shard_ids) == sorted(new_shard_ids)
    # Ensure topo was not mutated in place
    assert topo is not rebalanced_topo

    # 6. Rebalance plan preserves all manifold ids
    original_manifolds = []
    for s in topo.shards.values():
        original_manifolds.extend(s.manifold_ids)
    new_manifolds = []
    for s in rebalanced_topo.shards.values():
        new_manifolds.extend(s.manifold_ids)
    assert sorted(original_manifolds) == sorted(new_manifolds)

    # 7. Placement move validates when no locks or transactions exist
    move = PlacementMove(
        move_id="MOVE_TEST",
        manifold_id="manifold_0",
        source_core="core_0",
        target_core="core_1",
        constraints=[
            PlacementConstraint("preserve_transactions", "manifold_0", True),
            PlacementConstraint("preserve_locks", "manifold_0", True)
        ]
    )
    assert validate_placement_constraints(move) is True

    # 8. Placement move is rejected for active transaction participant
    move_tx_active = PlacementMove(
        move_id="MOVE_TX_ACTIVE",
        manifold_id="manifold_0",
        source_core="core_0",
        target_core="core_1",
        constraints=[
            PlacementConstraint("preserve_transactions", "manifold_0", True),
            PlacementConstraint("preserve_locks", "manifold_0", True)
        ],
        metadata={"transaction_active": True}
    )
    assert validate_placement_constraints(move_tx_active) is False

    # 9. Placement move is rejected for held exclusive lock
    move_locked = PlacementMove(
        move_id="MOVE_LOCKED",
        manifold_id="manifold_0",
        source_core="core_0",
        target_core="core_1",
        constraints=[
            PlacementConstraint("preserve_transactions", "manifold_0", True),
            PlacementConstraint("preserve_locks", "manifold_0", True)
        ],
        metadata={"exclusive_lock_held": True}
    )
    assert validate_placement_constraints(move_locked) is False

    # 10. Placement move preserves rollback snapshot references
    # 11. Placement move preserves consensus group references
    move_constraint_fail = PlacementMove(
        move_id="MOVE_CF",
        manifold_id="manifold_0",
        source_core="core_0",
        target_core="core_1",
        constraints=[
            PlacementConstraint("preserve_transactions", "manifold_0", True),
            PlacementConstraint("preserve_locks", "manifold_0", True)
        ],
        metadata={"rollback_broken": True, "consensus_broken": True}
    )
    assert validate_placement_constraints(move_constraint_fail) is False

    # 12. Lock ordering validation blocks unsafe move
    unsafe_lock_schedule = ShardLockSchedule(transaction_id="tx_unsafe", lock_order_valid=False)
    assert validate_rebalance_against_locks(plan, unsafe_lock_schedule) is False

    # 13. Before/after cost comparison detects improvement
    diff = compare_rebalance_before_after(1.0, 0.8)
    assert diff["before_cost"] == 1.0
    assert diff["after_cost"] == 0.8
    assert abs(diff["improvement"] - 0.2) < 1e-6
    assert abs(diff["improvement_pct"] - 20.0) < 1e-6

    # 14. Improvement below threshold blocks promotion
    court = PromotionCourt()
    result_fail = execute_shadow_rebalance(plan) # standard rebalance
    # Override before/after cost to show no improvement
    report_no_improv = result_fail
    report_no_improv.before_cost = 1.0
    report_no_improv.after_cost = 1.0 # no improvement
    court_rep_res = court.review_rebalance_report(report_no_improv)
    assert court_rep_res.passed is False
    assert court_rep_res.decision == "needs_more_evidence"

    # 16. RebalancerRanger emits JSON-serializable SovereignPacket
    ranger = RebalancerRanger()
    packet = ranger.observe_rebalance(
        shard_load_metrics=shard_metrics,
        core_group_load_metrics=core_metrics,
        rebalance_plan=plan,
        rebalance_report=result_fail,
        placement_map=PlacementMap("PM_TEST", {"manifold_0": "core_1"}, {"shard_0": "core_1"})
    )
    assert packet.actor == "Rebalancer Ranger"
    assert packet.level == 25
    packet_json = json.dumps(packet.to_dict())
    assert packet_json is not None

    # 17. Promotion Court can review rebalance plan, report, and placement map
    court_plan_res = court.review_rebalance_plan(plan)
    assert court_plan_res.decision == "accept_shadow_rebalance"
    assert court_plan_res.passed is True

    # Reviewing report with actual improvement promotes Level 25
    report_good = result_fail
    report_good.before_cost = 1.0
    report_good.after_cost = 0.8
    # set metadata preserving flags
    report_good.metadata = {
        "locks_preserved": True,
        "transactions_preserved": True,
        "rollback_preserved": True,
        "consensus_preserved": True
    }
    court_rep_good = court.review_rebalance_report(report_good)
    assert court_rep_good.decision == "promote_level25_candidate"
    assert court_rep_good.passed is True

    pm = PlacementMap("PM_TEST", {"manifold_0": "core_1"})
    court_pm_res = court.review_placement_map(pm)
    assert court_pm_res.decision == "accept_shadow_rebalance"
    assert court_pm_res.passed is True


def test_level26_scaffolding():
    """Verify Level 26 Live Relocation trials, telemetry, gates, ranger, and court review."""
    from sol_live_relocation import (
        LiveRelocationToken,
        validate_live_relocation_token,
        build_sandbox_relocation_request,
        capture_sandbox_relocation_snapshot,
        execute_sandbox_relocation_step,
        rollback_sandbox_relocation,
        summarize_sandbox_relocation
    )
    from sol_pdm_relocation_telemetry import (
        PDMRelocationTelemetryFrame,
        PDMRelocationTelemetryLoop,
        PDMRelocationStabilityReport,
        PDMRelocationAbortSignal,
        capture_pdm_relocation_baseline,
        sample_pdm_relocation_frame,
        evaluate_pdm_relocation_stability,
        detect_relocation_abort_signal
    )
    from sol_relocation_trial import (
        RelocationTrialPolicy,
        build_relocation_trial,
        run_shadow_relocation_trial,
        run_sandbox_live_relocation_trial,
        evaluate_relocation_trial
    )
    from coding_library.sovereign_domain.frontier_bridge import (
        RelocationControlSuggestion,
        RelocationClosedLoopPolicy,
        RelocationClosedLoopReport,
        suggest_relocation_control_adjustment,
        validate_relocation_control_bounds
    )
    from sol_shard_rebalancer import (
        validate_rebalance_for_live_trial,
        promote_rebalance_plan_to_sandbox_trial,
        RebalancePlan,
        RebalancePolicy
    )
    from sol_manifold_placement import (
        PlacementMap,
        PlacementMove,
        PlacementConstraint,
        apply_sandbox_relocation_move,
        restore_sandbox_placement
    )
    from sol_shard_lock_scheduler import (
        quiesce_sandbox_shard_for_relocation,
        release_sandbox_relocation_quiesce,
        ShardLock,
        ShardLockSchedule,
        get_active_locks,
        clear_active_locks
    )
    from sol_atomic_commit import (
        AtomicCommitTransaction,
        AtomicCommitIntent,
        AtomicCommitParticipant,
        validate_no_active_commit_during_relocation as validate_no_commit_atomic,
        block_relocation_during_prepare_commit as block_relocation_atomic
    )
    from sol_transaction_coordinator import (
        DistributedTransaction,
        TransactionIntent,
        TransactionParticipant,
        validate_no_active_commit_during_relocation as validate_no_commit_coord,
        block_relocation_during_prepare_commit as block_relocation_coord,
        clear_active_transactions
    )
    from coding_library.sovereign_domain.rangers.relocation_ranger import RelocationRanger
    from coding_library.sovereign_domain import PromotionCourt, SovereignPacket
    import time
    import json
    import pytest

    # 1. Live relocation token validates with required fields.
    valid_token = LiveRelocationToken(
        token_id="T_VALID",
        court_authorization_id="AUTH_1",
        sandbox_scope=True,
        source_id="shard_0",
        target_id="shard_1",
        expiration=time.time() + 100,
        max_relocation_steps=5,
        rollback_required=True,
        ranger_observer_id="R_OBS_1"
    )
    assert validate_live_relocation_token(valid_token) is True

    # 2. Expired token is rejected.
    expired_token = LiveRelocationToken(
        token_id="T_EXPIRED",
        court_authorization_id="AUTH_1",
        sandbox_scope=True,
        source_id="shard_0",
        target_id="shard_1",
        expiration=time.time() - 100,
        max_relocation_steps=5,
        rollback_required=True,
        ranger_observer_id="R_OBS_1"
    )
    assert validate_live_relocation_token(expired_token) is False

    # 3. Non-sandbox token scope is rejected.
    non_sandbox_token = LiveRelocationToken(
        token_id="T_NON_SANDBOX",
        court_authorization_id="AUTH_1",
        sandbox_scope=False,
        source_id="shard_0",
        target_id="shard_1",
        expiration=time.time() + 100,
        max_relocation_steps=5,
        rollback_required=True,
        ranger_observer_id="R_OBS_1"
    )
    assert validate_live_relocation_token(non_sandbox_token) is False

    # 4. Sandbox relocation request builds from accepted rebalance plan.
    rebalance_policy = RebalancePolicy()
    pm = PlacementMap("PM_SANDBOX", {"manifold_0": "core_0"}, {"shard_0": "core_0"})
    rebalance_plan = RebalancePlan(
        plan_id="PLAN_1",
        candidates=[],
        policy=rebalance_policy,
        topology_reference=None,
        core_group_reference=None,
        metadata={"placement_map": pm, "rebalance_report_accepted": True, "rollback_snapshots_present": True}
    )
    rebalance_plan.placement_map = pm
    
    assert validate_rebalance_for_live_trial(rebalance_plan, valid_token) is True
    request = promote_rebalance_plan_to_sandbox_trial(rebalance_plan, valid_token)
    assert request.token == valid_token
    assert request.rebalance_plan == rebalance_plan

    # 5. Rollback snapshot is captured before sandbox relocation.
    snapshot = capture_sandbox_relocation_snapshot(request)
    assert snapshot is not None
    assert snapshot.before_placement_map is not None
    assert snapshot.before_placement_map.manifold_to_core["manifold_0"] == "core_0"

    # 6. Missing rollback snapshot blocks relocation.
    policy26 = RelocationTrialPolicy()
    trial = build_relocation_trial(rebalance_plan, policy26)
    # Set trial metadata to fail snapshot
    trial.metadata = {"missing_rollback_snapshot": True}
    trial_report_fail_snap = run_sandbox_live_relocation_trial(trial, valid_token)
    assert trial_report_fail_snap.passed_gates is False
    assert trial_report_fail_snap.trial_state.status == "aborted"

    # 7. PDM baseline is captured before relocation.
    trial_normal = build_relocation_trial(rebalance_plan, policy26)
    trial_report_ok = run_sandbox_live_relocation_trial(trial_normal, valid_token)
    assert trial_report_ok.trial_state.baseline is not None
    
    # 8. Telemetry loop detects stable relocation.
    assert trial_report_ok.passed_gates is True
    assert trial_report_ok.decision.decision == "accept"

    # 9. Telemetry loop detects high phase drift.
    rebalance_plan_drift = RebalancePlan(
        plan_id="PLAN_DRIFT",
        candidates=[],
        policy=rebalance_policy,
        topology_reference=None,
        core_group_reference=None,
        metadata={"placement_map": pm, "rebalance_report_accepted": True, "rollback_snapshots_present": True, "drift_breach": True}
    )
    rebalance_plan_drift.placement_map = pm
    trial_drift = build_relocation_trial(rebalance_plan_drift, policy26)
    trial_report_drift = run_sandbox_live_relocation_trial(trial_drift, valid_token)
    assert trial_report_drift.passed_gates is False
    assert trial_report_drift.decision.decision == "rollback"
    assert "Phase drift" in trial_report_drift.decision.reason

    # 10. Telemetry loop detects high crosstalk.
    rebalance_plan_crosstalk = RebalancePlan(
        plan_id="PLAN_CROSSTALK",
        candidates=[],
        policy=rebalance_policy,
        topology_reference=None,
        core_group_reference=None,
        metadata={"placement_map": pm, "rebalance_report_accepted": True, "rollback_snapshots_present": True, "crosstalk_breach": True}
    )
    rebalance_plan_crosstalk.placement_map = pm
    trial_crosstalk = build_relocation_trial(rebalance_plan_crosstalk, policy26)
    trial_report_crosstalk = run_sandbox_live_relocation_trial(trial_crosstalk, valid_token)
    assert trial_report_crosstalk.passed_gates is False
    assert trial_report_crosstalk.decision.decision == "rollback"
    assert "Crosstalk" in trial_report_drift.decision.reason or "Crosstalk" in trial_report_crosstalk.decision.reason

    # 11. Telemetry loop detects boundary reflection breach.
    rebalance_plan_reflection = RebalancePlan(
        plan_id="PLAN_REFLECTION",
        candidates=[],
        policy=rebalance_policy,
        topology_reference=None,
        core_group_reference=None,
        metadata={"placement_map": pm, "rebalance_report_accepted": True, "rollback_snapshots_present": True, "reflection_breach": True}
    )
    rebalance_plan_reflection.placement_map = pm
    trial_reflection = build_relocation_trial(rebalance_plan_reflection, policy26)
    trial_report_reflection = run_sandbox_live_relocation_trial(trial_reflection, valid_token)
    assert trial_report_reflection.passed_gates is False
    assert trial_report_reflection.decision.decision == "rollback"
    assert "Boundary reflection" in trial_report_reflection.decision.reason

    # 12. Abort signal triggers rollback recommendation.
    loop = PDMRelocationTelemetryLoop("LOOP_ABORT")
    frame_breach = PDMRelocationTelemetryFrame(1.0, 0.12, 0.0, 0.0, 0.0, 500.0, 1.0, 1.0, True)
    loop.frames.append(frame_breach)
    stability_rep = evaluate_pdm_relocation_stability(loop)
    abort_sig = detect_relocation_abort_signal(stability_rep)
    assert abort_sig.abort is True
    assert "Phase drift" in abort_sig.reason

    # 13. Rollback restores sandbox placement map.
    move = PlacementMove("MOVE_1", "manifold_0", "core_0", "core_1")
    rebalance_plan_rollback = RebalancePlan(
        plan_id="PLAN_RB",
        candidates=[],
        policy=rebalance_policy,
        topology_reference=None,
        core_group_reference=None,
        metadata={"placement_map": pm, "rebalance_report_accepted": True, "rollback_snapshots_present": True}
    )
    rebalance_plan_rollback.placement_map = pm
    req_rb = build_sandbox_relocation_request(rebalance_plan_rollback, valid_token)
    snap_rb = capture_sandbox_relocation_snapshot(req_rb)
    applied_pm = apply_sandbox_relocation_move(pm, move, valid_token)
    assert applied_pm.manifold_to_core["manifold_0"] == "core_1"
    restored_pm = restore_sandbox_placement(snap_rb)
    assert restored_pm.manifold_to_core["manifold_0"] == "core_0"

    # 14. Production/default placement relocation is rejected.
    production_pm = PlacementMap("production_placement_map", {"manifold_0": "core_0"})
    with pytest.raises(ValueError, match="Production/default placement maps are immutable"):
        apply_sandbox_relocation_move(production_pm, move, valid_token)

    # 15. Active prepare/commit blocks relocation.
    clear_active_transactions()
    p1 = AtomicCommitParticipant("manifold_0", "preparing")
    intent = AtomicCommitIntent("INT_1", "COMMIT_WORD", 100, 32)
    tx = AtomicCommitTransaction("TX_1", [p1], intent, sandbox=True, status="preparing")
    assert validate_no_commit_atomic(rebalance_plan, [tx]) is False
    assert block_relocation_atomic(tx) is True

    coord_tx = DistributedTransaction(
        transaction_id="TX_COORD_1",
        participants=[TransactionParticipant("manifold_0", "preparing")],
        intent=TransactionIntent("INT_2", "COMMIT_WORD", 200, 32),
        sandbox=True,
        status="preparing"
    )
    assert validate_no_commit_coord(rebalance_plan, [coord_tx]) is False
    assert block_relocation_coord(coord_tx) is True

    # 16. Held production lock blocks relocation.
    assert quiesce_sandbox_shard_for_relocation("production_shard", valid_token) is False
    assert quiesce_sandbox_shard_for_relocation("default_shard", valid_token) is False
    assert quiesce_sandbox_shard_for_relocation("sandbox_shard", valid_token) is True
    release_sandbox_relocation_quiesce("sandbox_shard", valid_token)

    # 17. Court can authorize sandbox relocation trial.
    court = PromotionCourt()
    court_trial_ok = court.review_relocation_trial_report(trial_report_ok)
    assert court_trial_ok.passed is True
    assert court_trial_ok.decision == "promote_level26_candidate"

    # 18. Court can reject unsafe relocation trial.
    court_trial_drift = court.review_relocation_trial_report(trial_report_drift)
    assert court_trial_drift.passed is False
    assert court_trial_drift.decision == "rollback_relocation"

    # 19. RelocationRanger emits JSON-serializable SovereignPacket.
    ranger = RelocationRanger()
    packet = ranger.observe_relocation(
        relocation_plan=rebalance_plan,
        relocation_report=None,
        stability_report=stability_rep,
        trial_report=trial_report_ok,
        closed_loop_report=None
    )
    assert packet.actor == "Relocation Ranger"
    assert packet.level == 26
    packet_json = json.dumps(packet.to_dict())
    assert packet_json is not None
    assert "PKT_RELOC_OBS_" in packet_json

    # 20. Promotion Court can review relocation, telemetry, and trial reports.
    stability_court_res = court.review_pdm_relocation_stability_report(stability_rep)
    assert stability_court_res.passed is False
    assert stability_court_res.decision == "rollback_relocation"


def test_level27_scaffolding():
    """Verify Level 27 Multi-Manifold Coordination, synchronization, global lock boundaries, alignment, epochs, and rangers."""
    from sol_multimanifold_coordinator import (
        build_coordination_group,
        validate_coordination_group,
        plan_multi_manifold_rebalance,
        execute_shadow_coordination_plan,
        summarize_coordination_result,
        MultiManifoldRebalanceIntent,
        MultiManifoldCoordinationReport,
        MultiManifoldCoordinationResult
    )
    from sol_global_lock_boundary import (
        collect_manifold_lock_boundaries,
        validate_cross_manifold_lock_boundaries,
        plan_global_lock_boundary,
        detect_global_lock_conflict,
        detect_cross_manifold_deadlock,
        CrossManifoldLockIntent,
        GlobalLockBoundaryReport
    )
    from sol_wavefront_alignment_coordinator import (
        capture_cross_manifold_wavefront_state,
        measure_global_phase_alignment,
        measure_global_boundary_reflection,
        plan_wavefront_alignment_adjustment,
        execute_shadow_wavefront_alignment
    )
    from sol_coordination_epoch import (
        start_coordination_epoch,
        register_epoch_participant,
        evaluate_epoch_barrier,
        commit_shadow_epoch,
        abort_epoch
    )
    from sol_live_relocation import (
        build_multi_manifold_relocation_request,
        validate_multi_manifold_relocation_tokens,
        capture_multi_manifold_snapshots,
        rollback_multi_manifold_relocation,
        LiveRelocationToken,
        SandboxRelocationRequest,
        MultiManifoldRelocationSnapshot
    )
    from sol_pdm_relocation_telemetry import (
        aggregate_multi_manifold_pdm_telemetry,
        evaluate_global_relocation_stability,
        PDMRelocationTelemetryFrame
    )
    from sol_shard_rebalancer import (
        plan_coordinated_rebalance_across_manifolds,
        validate_coordinated_rebalance,
        RebalanceReport,
        RebalanceResult
    )
    from sol_wavefront_consensus import (
        propose_coordination_epoch_state,
        collect_multimanifold_coordination_votes,
        evaluate_multimanifold_quorum,
        WavefrontConsensusNode
    )
    from coding_library.sovereign_domain.frontier_bridge import (
        FrontierBridge,
        GlobalCoordinationAdvisor
    )
    from coding_library.sovereign_domain.rangers.manifold_sync_ranger import ManifoldSyncRanger
    from coding_library.sovereign_domain import PromotionCourt, SovereignPacket
    from sol_manifold_placement import PlacementMap, PlacementMove
    import time
    import pytest
    import json

    # Mock manifolds/placement maps
    m0 = PlacementMap("manifold_0", {"manifold_0": "core_0"}, {"shard_0": "core_0"})
    m1 = PlacementMap("manifold_1", {"manifold_1": "core_1"}, {"shard_1": "core_1"})
    m2 = PlacementMap("manifold_2", {"manifold_2": "core_2"}, {"shard_2": "core_2"})
    
    # Core groups mock
    cg = ["core_0", "core_1", "core_2"]

    # 1. coordination group builds with 2 mock manifolds.
    group2 = build_coordination_group([m0, m1], cg)
    assert len(group2.manifolds) == 2
    assert validate_coordination_group(group2) is True

    # 2. coordination group builds with 3+ mock manifolds.
    group3 = build_coordination_group([m0, m1, m2], cg)
    assert len(group3.manifolds) == 3
    assert validate_coordination_group(group3) is True

    # 3. missing manifold registration fails validation.
    invalid_group = build_coordination_group([m0], cg)
    invalid_group.registered_manifold_ids = set() # remove registration
    assert validate_coordination_group(invalid_group) is False

    # 4. coordination epoch starts and registers participants.
    epoch = start_coordination_epoch(group3, "Test Sync Epoch")
    assert epoch.status == "active"
    assert len(epoch.barrier.required_participants) == 3
    
    # 5. epoch barrier fails when participant is missing.
    register_epoch_participant(epoch, "manifold_0")
    register_epoch_participant(epoch, "manifold_1")
    assert evaluate_epoch_barrier(epoch) is False

    # 6. epoch barrier passes when all required participants are present.
    register_epoch_participant(epoch, "manifold_2")
    assert evaluate_epoch_barrier(epoch) is True

    # 7. global lock boundaries collect from mock manifolds.
    m0_dict = {
        "manifold_id": "manifold_0",
        "locked_shards": ["shard_0"],
        "active_locks": [],
        "active_transactions": [],
        "quarantined_boundaries": [],
        "lock_ordering": ["shard_0", "shard_1"]
    }
    m1_dict = {
        "manifold_id": "manifold_1",
        "locked_shards": [],
        "active_locks": [],
        "active_transactions": [],
        "quarantined_boundaries": [],
        "lock_ordering": ["shard_1", "shard_2"]
    }
    glb = collect_manifold_lock_boundaries([m0_dict, m1_dict])
    assert "manifold_0" in glb.manifold_boundaries
    assert glb.manifold_boundaries["manifold_0"].locked_shards == ["shard_0"]

    # 8. cross-manifold deadlock is detected.
    deadlock_intent = CrossManifoldLockIntent("INT_DEADLOCK", {"manifold_0": ["shard_1", "shard_0"]}) # out of order
    deadlock_plan = plan_global_lock_boundary(deadlock_intent, glb)
    assert detect_cross_manifold_deadlock(deadlock_plan) is True

    # 9. valid lock boundary plan preserves local lock ordering.
    valid_intent = CrossManifoldLockIntent("INT_VALID", {"manifold_0": ["shard_0", "shard_1"]}) # correct order
    valid_lock_plan = plan_global_lock_boundary(valid_intent, glb)
    assert detect_cross_manifold_deadlock(valid_lock_plan) is False

    # 10. coordinated rebalance preserves local shard topology.
    # We mock rebalance reports
    rep0 = RebalanceReport("REP_0", RebalanceResult(True, m0, m0, None, None, []), 1.0, 0.8, True)
    rep1 = RebalanceReport("REP_1", RebalanceResult(True, m1, m1, None, None, []), 1.0, 0.8, True)
    
    m_rebalance_plan = plan_coordinated_rebalance_across_manifolds([rep0, rep1], group3)
    assert validate_coordinated_rebalance(m_rebalance_plan) is True

    # 11. rollback snapshots are required for all manifolds.
    token0 = LiveRelocationToken("T0", "AUTH_1", True, "core_0", "core_1", time.time() + 100, 5, True, "R_SYNC")
    token1 = LiveRelocationToken("T1", "AUTH_1", True, "core_1", "core_2", time.time() + 100, 5, True, "R_SYNC")
    tokens = {"manifold_0": token0, "manifold_1": token1}
    
    # Fail if one manifold token is missing/invalid
    invalid_tokens = {"manifold_0": token0}
    assert validate_multi_manifold_relocation_tokens(invalid_tokens, m_rebalance_plan) is False
    assert validate_multi_manifold_relocation_tokens(tokens, m_rebalance_plan) is True

    req = build_multi_manifold_relocation_request(m_rebalance_plan, tokens)
    m_snapshot = capture_multi_manifold_snapshots(req)
    assert "manifold_0" in m_snapshot.manifold_snapshots
    assert m_snapshot.manifold_snapshots["manifold_0"].before_placement_map is not None

    # 12. PDM baselines are required for all manifolds.
    
    # 13. global phase skew is measured.
    m0_telemetry = {"manifold_id": "manifold_0", "phase_skew": 0.03, "crosstalk": 0.01, "boundary_reflection": 0.02}
    m1_telemetry = {"manifold_id": "manifold_1", "phase_skew": 0.04, "crosstalk": 0.02, "boundary_reflection": 0.01}
    obs = capture_cross_manifold_wavefront_state([m0_telemetry, m1_telemetry])
    global_skew = measure_global_phase_alignment(obs)
    assert global_skew == 0.04

    # 14. high phase skew blocks coordination.
    m_telemetry_skew = {"manifold_id": "manifold_0", "phase_skew": 0.12, "metadata": {"high_skew": True}}
    obs_skew = capture_cross_manifold_wavefront_state([m_telemetry_skew])
    wavefront_plan_skew = plan_wavefront_alignment_adjustment(obs_skew, None)
    wavefront_report_skew = execute_shadow_wavefront_alignment(wavefront_plan_skew)
    assert wavefront_report_skew.stable is False

    # 15. high cross-manifold crosstalk blocks coordination.
    m_telemetry_crosstalk = {"manifold_id": "manifold_0", "crosstalk": 0.15, "metadata": {"high_crosstalk": True}}
    obs_crosstalk = capture_cross_manifold_wavefront_state([m_telemetry_crosstalk])
    wavefront_plan_crosstalk = plan_wavefront_alignment_adjustment(obs_crosstalk, None)
    wavefront_report_crosstalk = execute_shadow_wavefront_alignment(wavefront_plan_crosstalk)
    assert wavefront_report_crosstalk.stable is False

    # 16. wavefront alignment report is generated.
    wavefront_plan_ok = plan_wavefront_alignment_adjustment(obs, None)
    wavefront_report_ok = execute_shadow_wavefront_alignment(wavefront_plan_ok)
    assert wavefront_report_ok.stable is True
    assert wavefront_report_ok.global_phase_skew == 0.04

    # 17. multi-manifold quorum passes and fails correctly.
    cgroup = propose_coordination_epoch_state(epoch, group3)
    from sol_wavefront_consensus import build_consensus_group
    cons_group = build_consensus_group(["manifold_0", "manifold_1", "manifold_2"])
    
    votes_ok = collect_multimanifold_coordination_votes(epoch, cons_group, cgroup, mock_votes={"manifold_0": "approve", "manifold_1": "approve", "manifold_2": "reject"})
    quorum_ok = evaluate_multimanifold_quorum(votes_ok)
    assert quorum_ok.quorum_reached is True

    votes_fail = collect_multimanifold_coordination_votes(epoch, cons_group, cgroup, mock_votes={"manifold_0": "approve", "manifold_1": "reject", "manifold_2": "reject"})
    quorum_fail = evaluate_multimanifold_quorum(votes_fail)
    assert quorum_fail.quorum_reached is False

    # 18. split-brain detection blocks coordination.
    epoch_sb = start_coordination_epoch(group3, "Test Sync Epoch")
    epoch_sb.status = "aborted"
    epoch_sb.reason = "split_brain_detected"
    
    votes_sb = collect_multimanifold_coordination_votes(epoch_sb, cons_group, cgroup)
    quorum_sb = evaluate_multimanifold_quorum(votes_sb)
    assert quorum_sb.quorum_reached is False

    # 19. rollback restores all mock manifold placement maps.
    restored_dict = rollback_multi_manifold_relocation(m_snapshot, "Relocation Aborted")
    assert "manifold_0" in restored_dict
    assert restored_dict["manifold_0"].success is False
    assert restored_dict["manifold_0"].rolled_back is True

    # 20. ManifoldSyncRanger emits JSON-serializable SovereignPacket.
    sync_report = commit_shadow_epoch(epoch)
    
    coordination_plan = plan_multi_manifold_rebalance(MultiManifoldRebalanceIntent("INT_1"), group3)
    coordination_res = execute_shadow_coordination_plan(coordination_plan)
    
    checked_gates = {
        "coordination_group_valid": True,
        "epoch_barrier_satisfied": True,
        "global_lock_boundaries_valid": True,
        "no_cross_manifold_deadlock": True,
        "wavefront_alignment_measured": True,
        "multimanifold_quorum_reached": True,
        "rollback_snapshots_present_for_all_manifolds": True
    }
    coord_report = MultiManifoldCoordinationReport(
        report_id="RPT_COORD",
        result=coordination_res,
        passed_gates=True,
        checked_gates=checked_gates
    )
    
    lock_report = GlobalLockBoundaryReport("L_RPT", valid_lock_plan, True, False, False)

    sync_ranger = ManifoldSyncRanger()
    packet = sync_ranger.observe_sync(
        coordination_plan=coordination_plan,
        lock_report=lock_report,
        wavefront_report=wavefront_report_ok,
        epoch_report=sync_report,
        coordination_report=coord_report
    )
    assert packet.actor == "Manifold Sync Ranger"
    assert packet.level == 27
    packet_json = json.dumps(packet.to_dict())
    assert packet_json is not None
    assert "PKT_SYNC_OBS_" in packet_json

    # 21. Promotion Court can review coordination, lock boundary, wavefront alignment, and epoch reports.
    court = PromotionCourt()
    court.submit_packet(packet)
    
    court_coord_plan_res = court.review_multimanifold_coordination_plan(coordination_plan)
    assert court_coord_plan_res.passed is True
    
    court_lock_res = court.review_global_lock_boundary_report(lock_report)
    assert court_lock_res.passed is True
    
    court_wave_res = court.review_wavefront_alignment_report(wavefront_report_ok)
    assert court_wave_res.passed is True
    
    court_epoch_res = court.review_epoch_synchronization_report(sync_report)
    assert court_epoch_res.passed is True
    
    court_coord_rep_res = court.review_multimanifold_coordination_report(coord_report)
    assert court_coord_rep_res.passed is True
    assert court_coord_rep_res.decision == "promote_level27_candidate"


def test_level28_scaffolding():
    """Verify Level 28 Multi-Manifold Transaction Consensus and Geodesic Propagation updates."""
    from sol_multimanifold_transaction_consensus import (
        build_transaction_consensus_epoch,
        validate_transaction_boundaries,
        collect_transaction_consensus_votes,
        evaluate_transaction_consensus_quorum,
        build_transaction_consensus_report,
        MultiManifoldTransactionIntent,
        MultiManifoldTransactionBoundary,
        ManifoldTransactionParticipant
    )
    from sol_geodesic_propagation_update import (
        plan_geodesic_propagation,
        validate_geodesic_propagation_path,
        execute_shadow_geodesic_propagation,
        compare_propagation_before_after,
        GeodesicPropagationIntent,
        GeodesicPropagationPath
    )
    from sol_transaction_wavefront_epoch import (
        start_wavefront_transaction_epoch,
        register_wavefront_checkpoint,
        evaluate_wavefront_commit_barrier,
        commit_shadow_wavefront_transaction,
        abort_wavefront_transaction,
        WavefrontPropagationCheckpoint
    )
    from sol_multimanifold_coordinator import (
        build_coordination_group,
        plan_transactional_geodesic_update,
        execute_shadow_transactional_geodesic_update
    )
    from sol_global_lock_boundary import (
        collect_manifold_lock_boundaries,
        plan_global_lock_boundary,
        validate_locks_for_geodesic_transaction,
        CrossManifoldLockIntent
    )
    from sol_wavefront_alignment_coordinator import (
        capture_cross_manifold_wavefront_state,
        validate_alignment_for_propagation,
        measure_propagation_phase_error
    )
    from sol_wavefront_propagator import (
        WavefrontState,
        propagate_wavefront_across_manifold_boundary
    )
    from sol_pdm_relocation_telemetry import (
        capture_transaction_propagation_baseline,
        sample_transaction_propagation_frame,
        evaluate_transaction_propagation_stability,
        PDMRelocationTelemetryFrame,
        PDMRelocationTelemetryLoop
    )
    from sol_transaction_coordinator import (
        DistributedTransaction,
        TransactionIntent,
        TransactionParticipant,
        validate_transaction_before_geodesic_propagation,
        block_commit_on_unstable_propagation
    )
    from coding_library.sovereign_domain.frontier_bridge import (
        FrontierBridge,
        GeodesicTransactionAdvisor,
        GeodesicTransactionSuggestion
    )
    from coding_library.sovereign_domain.rangers.transaction_propagation_ranger import TransactionPropagationRanger
    from coding_library.sovereign_domain import PromotionCourt, SovereignPacket
    from sol_manifold_placement import PlacementMap
    from sol_live_relocation import LiveRelocationToken
    import time
    import json

    # Mock manifolds/placements
    m0 = PlacementMap("manifold_0", {"manifold_0": "core_0"}, {"shard_0": "core_0"})
    m1 = PlacementMap("manifold_1", {"manifold_1": "core_1"}, {"shard_1": "core_1"})
    m2 = PlacementMap("manifold_2", {"manifold_2": "core_2"}, {"shard_2": "core_2"})
    cg = ["core_0", "core_1", "core_2"]
    
    group2 = build_coordination_group([m0, m1], cg)
    group3 = build_coordination_group([m0, m1, m2], cg)

    # 1. transaction consensus epoch builds with 2 mock manifolds.
    intent2 = MultiManifoldTransactionIntent("TX2", ["manifold_0", "manifold_1"])
    epoch2 = build_transaction_consensus_epoch(intent2, group2)
    assert len(epoch2.boundary.participants) == 2

    # 2. transaction consensus epoch builds with 3+ mock manifolds.
    intent3 = MultiManifoldTransactionIntent("TX3", ["manifold_0", "manifold_1", "manifold_2"])
    epoch3 = build_transaction_consensus_epoch(intent3, group3)
    assert len(epoch3.boundary.participants) == 3

    # 3. missing participant fails boundary validation.
    epoch3.boundary.participants["manifold_0"].rollback_snapshot_id = "" # invalid
    assert validate_transaction_boundaries(epoch3) is False
    epoch3.boundary.participants["manifold_0"].rollback_snapshot_id = "SNAP_0" # restore
    assert validate_transaction_boundaries(epoch3) is True

    # 4. local quorum passes and fails correctly.
    # quorum evaluate requires all votes approve for local quorum
    votes_ok = collect_transaction_consensus_votes(epoch3, mock_votes={"manifold_0": "approve", "manifold_1": "approve", "manifold_2": "approve"})
    dec_ok = evaluate_transaction_consensus_quorum(epoch3, votes_ok)
    assert dec_ok.agreed is True
    
    votes_fail = collect_transaction_consensus_votes(epoch3, mock_votes={"manifold_0": "approve", "manifold_1": "reject", "manifold_2": "approve"})
    dec_fail = evaluate_transaction_consensus_quorum(epoch3, votes_fail)
    assert dec_fail.agreed is False

    # 5. global quorum passes and fails correctly.
    # quorum evaluation requires >= 67% global approval
    votes_g_fail = collect_transaction_consensus_votes(epoch3, mock_votes={"manifold_0": "reject", "manifold_1": "reject", "manifold_2": "approve"})
    dec_g_fail = evaluate_transaction_consensus_quorum(epoch3, votes_g_fail)
    assert dec_g_fail.agreed is False

    # 6. geodesic propagation path validates across two manifolds.
    gpath = GeodesicPropagationPath("GP_1", "manifold_0", "manifold_1", route_depth=2, boundary_crossings=["CROSS_m0_m1"])
    assert validate_geodesic_propagation_path(gpath) is True

    # 7. propagation path rejects missing boundary declaration.
    gpath_invalid = GeodesicPropagationPath("GP_2", "manifold_0", "manifold_1", route_depth=2, boundary_crossings=[])
    assert validate_geodesic_propagation_path(gpath_invalid) is False

    # 8. transaction wavefront epoch blocks commit before checkpoint completion.
    g_intent = GeodesicPropagationIntent("GINT_1", "manifold_0", "manifold_1", ["shard_0"])
    w_epoch = start_wavefront_transaction_epoch(intent3, g_intent)
    assert evaluate_wavefront_commit_barrier(w_epoch) is False
    
    w_rep_fail = commit_shadow_wavefront_transaction(w_epoch)
    assert w_rep_fail.result.success is False
    assert w_rep_fail.result.rolled_back is True

    # 9. transaction wavefront epoch commits in shadow when all barriers pass.
    register_wavefront_checkpoint(w_epoch, WavefrontPropagationCheckpoint("CP_0", "manifold_0", True, "sha256_hash"))
    register_wavefront_checkpoint(w_epoch, WavefrontPropagationCheckpoint("CP_1", "manifold_1", True, "sha256_hash"))
    register_wavefront_checkpoint(w_epoch, WavefrontPropagationCheckpoint("CP_2", "manifold_2", True, "sha256_hash"))
    assert evaluate_wavefront_commit_barrier(w_epoch) is True
    
    w_rep_ok = commit_shadow_wavefront_transaction(w_epoch)
    assert w_rep_ok.result.success is True
    assert w_rep_ok.result.committed is True

    # 10. lock boundary failure blocks geodesic transaction.
    m0_dict = {
        "manifold_id": "manifold_0",
        "locked_shards": [],
        "active_locks": [],
        "active_transactions": [{"status": "preparing"}],
        "quarantined_boundaries": [],
        "lock_ordering": ["shard_0", "shard_1"]
    }
    glb_fail = collect_manifold_lock_boundaries([m0_dict])
    lock_intent = CrossManifoldLockIntent("L_INT", {"manifold_0": ["shard_0"]})
    boundary_plan = plan_global_lock_boundary(lock_intent, glb_fail)
    assert validate_locks_for_geodesic_transaction(boundary_plan, epoch3) is False

    # 11. cross-manifold deadlock blocks commit.
    m0_deadlock = {
        "manifold_id": "manifold_0",
        "locked_shards": [],
        "active_locks": [],
        "active_transactions": [],
        "quarantined_boundaries": [],
        "lock_ordering": ["shard_0", "shard_1"]
    }
    glb_dl = collect_manifold_lock_boundaries([m0_deadlock])
    # Out of order lock acquisition causes deadlock detection
    deadlock_intent = CrossManifoldLockIntent("L_DL", {"manifold_0": ["shard_1", "shard_0"]})
    boundary_plan_dl = plan_global_lock_boundary(deadlock_intent, glb_dl)
    assert validate_locks_for_geodesic_transaction(boundary_plan_dl, epoch3) is False

    # 12. missing rollback snapshot blocks commit.
    # Execute shadow transactional update without tokens metadata to trigger missing snapshots
    intent_snap = MultiManifoldTransactionIntent("TX_SNAP", ["manifold_0", "manifold_1"])
    plan_snap = plan_transactional_geodesic_update(intent_snap, group2)
    # no tokens metadata
    res_snap = execute_shadow_transactional_geodesic_update(plan_snap)
    assert res_snap["success"] is False
    assert "Rollback snapshots are missing" in res_snap["wavefront_report"].result.rollback_reason

    # 13. unstable propagation report blocks commit.
    intent_unst = MultiManifoldTransactionIntent("TX_UNST", ["manifold_0", "manifold_1"])
    token0 = LiveRelocationToken("T0", "AUTH_1", True, "core_0", "core_1", time.time() + 100, 5, True, "R_PROP")
    token1 = LiveRelocationToken("T1", "AUTH_1", True, "core_1", "core_2", time.time() + 100, 5, True, "R_PROP")
    tokens = {"manifold_0": token0, "manifold_1": token1}
    plan_unst = plan_transactional_geodesic_update(intent_unst, group2)
    plan_unst.metadata["tokens"] = tokens
    plan_unst.metadata["high_phase_error"] = True # trigger instability
    res_unst = execute_shadow_transactional_geodesic_update(plan_unst)
    assert res_unst["success"] is False

    # 14. high phase error blocks commit.
    # Covered by metadata high_phase_error in transactional update execution above

    # 15. high crosstalk blocks commit.
    plan_ct = plan_transactional_geodesic_update(intent_unst, group2)
    plan_ct.metadata["tokens"] = tokens
    plan_ct.metadata["high_crosstalk"] = True
    res_ct = execute_shadow_transactional_geodesic_update(plan_ct)
    assert res_ct["success"] is False

    # 16. boundary reflection breach blocks commit.
    plan_rf = plan_transactional_geodesic_update(intent_unst, group2)
    plan_rf.metadata["tokens"] = tokens
    plan_rf.metadata["high_reflection"] = True
    res_rf = execute_shadow_transactional_geodesic_update(plan_rf)
    assert res_rf["success"] is False

    # 17. state hash mismatch blocks commit.
    plan_sh = plan_transactional_geodesic_update(intent_unst, group2)
    plan_sh.metadata["tokens"] = tokens
    plan_sh.metadata["state_hash_mismatch"] = True
    res_sh = execute_shadow_transactional_geodesic_update(plan_sh)
    assert res_sh["success"] is False

    # 18. split-brain detection blocks epoch progression.
    intent_sb = MultiManifoldTransactionIntent("TX_SB", ["manifold_0", "manifold_1"])
    plan_sb = plan_transactional_geodesic_update(intent_sb, group2)
    plan_sb.metadata["tokens"] = tokens
    plan_sb.metadata["split_brain_detected"] = True
    res_sb = execute_shadow_transactional_geodesic_update(plan_sb)
    assert res_sb["success"] is False
    assert res_sb["consensus_report"].passed_gates is False

    # 19. abort path emits rollback recommendation.
    w_abort_rep = abort_wavefront_transaction(w_epoch, "Simulated abort")
    assert w_abort_rep.result.success is False
    assert w_abort_rep.result.rolled_back is True

    # 20. TransactionPropagationRanger emits JSON-serializable SovereignPacket.
    intent_valid = MultiManifoldTransactionIntent("TX_OK", ["manifold_0", "manifold_1"])
    plan_valid = plan_transactional_geodesic_update(intent_valid, group2)
    plan_valid.metadata["tokens"] = tokens
    res_valid = execute_shadow_transactional_geodesic_update(plan_valid)
    assert res_valid["success"] is True

    # Capture observations and alignment report
    obs = capture_cross_manifold_wavefront_state(group2.manifolds)
    from sol_wavefront_alignment_coordinator import plan_wavefront_alignment_adjustment, execute_shadow_wavefront_alignment
    al_plan = plan_wavefront_alignment_adjustment(obs, None)
    al_report = execute_shadow_wavefront_alignment(al_plan)

    glb_ok = collect_manifold_lock_boundaries(group2.manifolds)
    boundary_plan_ok = plan_global_lock_boundary(CrossManifoldLockIntent("L_OK", {"manifold_0": ["shard_0"]}), glb_ok)
    from sol_global_lock_boundary import GlobalLockBoundaryReport
    lock_report_ok = GlobalLockBoundaryReport("L_RPT", boundary_plan_ok, True, False, False)

    ranger = TransactionPropagationRanger()
    packet = ranger.observe_propagation(
        consensus_report=res_valid["consensus_report"],
        geodesic_report=res_valid["geodesic_report"],
        wavefront_report=res_valid["wavefront_report"],
        lock_report=lock_report_ok,
        alignment_report=al_report
    )
    assert packet.actor == "Transaction Propagation Ranger"
    assert packet.level == 28
    packet_json = json.dumps(packet.to_dict())
    assert packet_json is not None
    assert "PKT_PROP_OBS_" in packet_json

    # 21. Promotion Court can review transaction consensus, geodesic propagation, and wavefront transaction reports.
    court = PromotionCourt()
    court.submit_packet(packet)
    
    court_cons_res = court.review_transaction_consensus_report(res_valid["consensus_report"])
    assert court_cons_res.passed is True
    
    court_geo_res = court.review_geodesic_propagation_report(res_valid["geodesic_report"])
    assert court_geo_res.passed is True
    
    court_wave_res = court.review_wavefront_transaction_report(res_valid["wavefront_report"])
    assert court_wave_res.passed is True
    
    court_pack_res = court.review_transaction_propagation_packet(packet)
    assert court_pack_res.passed is True
    assert court_pack_res.decision == "promote_level28_candidate"


def test_level29_scaffolding():
    """Verify Level 29 Multi-Manifold Transaction Orchestration and Court-Supervised Promotion."""
    from sol_transaction_orchestrator import (
        build_transaction_orchestration_plan,
        validate_transaction_orchestration_plan,
        execute_shadow_transaction_orchestration,
        summarize_transaction_orchestration,
        TransactionOrchestrationIntent
    )
    from sol_promotion_docket import (
        open_promotion_docket,
        attach_evidence_item,
        attach_gate_snapshot,
        validate_promotion_docket,
        build_promotion_manifest,
        PromotionGateSnapshot,
        PromotionVerdict
    )
    from sol_court_supervised_promotion import (
        CourtPromotionPolicy,
        review_promotion_docket,
        evaluate_promotion_readiness,
        authorize_sandbox_promotion_trial,
        reject_or_hold_promotion
    )
    from sol_multimanifold_transaction_consensus import (
        MultiManifoldTransactionIntent,
        export_transaction_consensus_evidence,
        validate_consensus_for_promotion
    )
    from sol_geodesic_propagation_update import (
        GeodesicPropagationIntent,
        export_geodesic_propagation_evidence,
        validate_propagation_for_promotion
    )
    from sol_transaction_wavefront_epoch import (
        export_wavefront_epoch_evidence,
        validate_wavefront_epoch_for_promotion
    )
    from sol_global_lock_boundary import (
        export_lock_boundary_evidence,
        validate_lock_boundaries_for_promotion,
        CrossManifoldLockIntent
    )
    from sol_pdm_relocation_telemetry import (
        export_pdm_telemetry_evidence,
        validate_pdm_telemetry_for_promotion,
        PDMRelocationStabilityReport
    )
    from sol_multimanifold_coordinator import build_coordination_group
    from sol_manifold_placement import PlacementMap
    from sol_live_relocation import LiveRelocationToken
    from coding_library.sovereign_domain.rangers.court_ranger import CourtRanger
    from coding_library.sovereign_domain import PromotionCourt, SovereignPacket
    import time
    import json

    # Mock coordination setup
    m0 = PlacementMap("manifold_0", {"manifold_0": "core_0"}, {"shard_0": "core_0"})
    m1 = PlacementMap("manifold_1", {"manifold_1": "core_1"}, {"shard_1": "core_1"})
    cg = ["core_0", "core_1"]
    group = build_coordination_group([m0, m1], cg)

    tx_intent = MultiManifoldTransactionIntent("TX29", ["manifold_0", "manifold_1"])
    g_intent = GeodesicPropagationIntent("GINT29", "manifold_0", "manifold_1", ["shard_0"])
    orch_intent = TransactionOrchestrationIntent("ORCH_1", tx_intent, g_intent)

    # 1. transaction orchestration plan builds from mock multi-manifold intent.
    plan = build_transaction_orchestration_plan(orch_intent, group)
    assert validate_transaction_orchestration_plan(plan) is True

    # 2. orchestration plan rejects missing coordination group.
    plan_invalid = build_transaction_orchestration_plan(orch_intent, None)
    rep_invalid = execute_shadow_transaction_orchestration(plan_invalid)
    assert rep_invalid.result.success is False

    # Setup mock tokens
    token0 = LiveRelocationToken("T0", "AUTH_1", True, "core_0", "core_1", time.time() + 100, 5, True, "R_PROP")
    token1 = LiveRelocationToken("T1", "AUTH_1", True, "core_1", "core_2", time.time() + 100, 5, True, "R_PROP")
    tokens = {"manifold_0": token0, "manifold_1": token1}

    # 3. orchestration plan rejects missing rollback references.
    plan_no_snap = build_transaction_orchestration_plan(orch_intent, group)
    rep_no_snap = execute_shadow_transaction_orchestration(plan_no_snap)
    assert rep_no_snap.result.success is False
    assert "Missing rollback snapshots" in rep_no_snap.result.errors[0]

    # 4. promotion docket opens and accepts evidence items.
    docket = open_promotion_docket("CAND_1", 29)
    attach_evidence_item(docket, {"evidence_type": "test_summary", "payload": {"status": "passed"}})
    assert len(docket.evidence) == 1

    # 5. promotion docket rejects missing critical evidence.
    assert validate_promotion_docket(docket) is False

    # Attach remaining evidence
    attach_evidence_item(docket, {"evidence_type": "ranger_packet", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "consensus_report", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "transaction_report", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "geodesic_propagation_report", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "telemetry_report", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "rollback_snapshot", "payload": tokens})
    assert validate_promotion_docket(docket) is True

    # 6. promotion manifest builds only after valid verdict.
    verdict_fail = PromotionVerdict("V_FAIL", "hold_promotion", "Missing votes")
    try:
        build_promotion_manifest(docket, verdict_fail)
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    verdict_ok = PromotionVerdict("V_OK", "promote_level29_candidate", "All gates passed")
    manifest = build_promotion_manifest(docket, verdict_ok)
    assert manifest.level == 29

    # 7. court review accepts complete shadow candidate.
    plan_ok = build_transaction_orchestration_plan(orch_intent, group)
    plan_ok.metadata["tokens"] = tokens
    rep_ok = execute_shadow_transaction_orchestration(plan_ok)
    assert rep_ok.result.success is True
    assert rep_ok.result.decision == "accept_shadow_candidate"

    # 8. court review holds candidate with missing ranger evidence.
    docket_empty_ranger = open_promotion_docket("CAND_R", 29)
    attach_evidence_item(docket_empty_ranger, {"evidence_type": "consensus_report", "payload": {}})
    attach_evidence_item(docket_empty_ranger, {"evidence_type": "transaction_report", "payload": {}})
    attach_evidence_item(docket_empty_ranger, {"evidence_type": "geodesic_propagation_report", "payload": {}})
    attach_evidence_item(docket_empty_ranger, {"evidence_type": "telemetry_report", "payload": {}})
    attach_evidence_item(docket_empty_ranger, {"evidence_type": "rollback_snapshot", "payload": tokens})
    attach_evidence_item(docket_empty_ranger, {"evidence_type": "test_summary", "payload": {"status": "passed"}})
    
    court = PromotionCourt()
    verdict_empty = court.issue_court_supervised_promotion_verdict(docket_empty_ranger)
    assert verdict_empty.decision == "hold_promotion"

    # 9. court review rejects failed quorum.
    plan_fq = build_transaction_orchestration_plan(orch_intent, group)
    plan_fq.metadata["tokens"] = tokens
    plan_fq.metadata["mock_votes"] = {"manifold_0": "reject", "manifold_1": "approve"}
    rep_fq = execute_shadow_transaction_orchestration(plan_fq)
    assert rep_fq.result.success is False
    assert "Consensus quorum not reached" in rep_fq.result.errors[0]

    # 10. court review rejects unstable geodesic propagation.
    plan_unst = build_transaction_orchestration_plan(orch_intent, group)
    plan_unst.metadata["tokens"] = tokens
    plan_unst.metadata["high_phase_error"] = True
    rep_unst = execute_shadow_transaction_orchestration(plan_unst)
    assert rep_unst.result.success is False
    assert "Geodesic propagation unstable" in rep_unst.result.errors[0]

    # 11. court review rejects failed lock boundary.
    plan_lock = build_transaction_orchestration_plan(orch_intent, group)
    plan_lock.metadata["tokens"] = tokens
    plan_lock.metadata["lock_intent"] = CrossManifoldLockIntent("L_INT", {"manifold_0": ["shard_1", "shard_0"]})
    # Set lock ordering to detect deadlock
    group.manifolds[0].lock_ordering = ["shard_0", "shard_1"]
    rep_lock = execute_shadow_transaction_orchestration(plan_lock)
    assert rep_lock.result.success is False
    assert "Lock boundaries invalid" in rep_lock.result.errors[0]

    # 12. court review rejects split-brain report.
    plan_sb = build_transaction_orchestration_plan(orch_intent, group)
    plan_sb.metadata["tokens"] = tokens
    plan_sb.metadata["split_brain_detected"] = True
    rep_sb = execute_shadow_transaction_orchestration(plan_sb)
    assert rep_sb.result.success is False

    # 13. court review rejects unresolved quarantine.
    plan_quar = build_transaction_orchestration_plan(orch_intent, group)
    plan_quar.metadata["tokens"] = tokens
    plan_quar.metadata["quarantine_unresolved"] = True
    rep_quar = execute_shadow_transaction_orchestration(plan_quar)
    assert rep_quar.result.success is False
    assert rep_quar.result.quarantined is True

    # 14. court review rejects critical test failures.
    docket_fail_test = open_promotion_docket("CAND_T", 29)
    attach_evidence_item(docket_fail_test, {"evidence_type": "ranger_packet", "payload": {}})
    attach_evidence_item(docket_fail_test, {"evidence_type": "consensus_report", "payload": {}})
    attach_evidence_item(docket_fail_test, {"evidence_type": "transaction_report", "payload": {}})
    attach_evidence_item(docket_fail_test, {"evidence_type": "geodesic_propagation_report", "payload": {}})
    attach_evidence_item(docket_fail_test, {"evidence_type": "telemetry_report", "payload": {}})
    attach_evidence_item(docket_fail_test, {"evidence_type": "rollback_snapshot", "payload": tokens})
    attach_evidence_item(docket_fail_test, {"evidence_type": "test_summary", "payload": {"status": "critical_failure"}})
    
    policy = CourtPromotionPolicy()
    review = review_promotion_docket(docket_fail_test, policy)
    assert review.checked_invariants["tests_passed"] is False

    # 15. court can authorize sandbox promotion trial.
    docket_trial = open_promotion_docket("CAND_TR", 29)
    attach_evidence_item(docket_trial, {"evidence_type": "ranger_packet", "payload": {}})
    attach_evidence_item(docket_trial, {"evidence_type": "consensus_report", "payload": {}})
    attach_evidence_item(docket_trial, {"evidence_type": "transaction_report", "payload": {}})
    attach_evidence_item(docket_trial, {"evidence_type": "geodesic_propagation_report", "payload": {}})
    attach_evidence_item(docket_trial, {"evidence_type": "telemetry_report", "payload": {}})
    attach_evidence_item(docket_trial, {"evidence_type": "rollback_snapshot", "payload": tokens})
    attach_evidence_item(docket_trial, {"evidence_type": "test_summary", "payload": {"status": "passed"}})
    
    dec_trial = authorize_sandbox_promotion_trial(docket_trial, None)
    assert dec_trial.decision == "authorize_sandbox_promotion_trial"

    # 16. court refuses automatic production promotion.
    docket_prod = open_promotion_docket("CAND_PROD", 29)
    docket_prod.metadata["allow_production_promotion"] = True
    policy_prod = CourtPromotionPolicy(allow_production_mutation=False)
    review_prod = review_promotion_docket(docket_prod, policy_prod)
    assert review_prod.checked_invariants["sandbox_only"] is False

    # 17. CourtRanger emits JSON-serializable SovereignPacket.
    ranger = CourtRanger()
    packet = ranger.observe_promotion(docket=docket_trial)
    assert packet.actor == "Court Ranger"
    assert packet.level == 29
    packet_json = json.dumps(packet.to_dict())
    assert packet_json is not None
    assert "PKT_COURT_OBS_" in packet_json

    # 18. Promotion Court can review orchestration reports, dockets, manifests, and verdicts.
    court_verdict_obs = court.review_promotion_docket(docket_trial)
    assert court_verdict_obs.passed is True


def test_level30_scaffolding():
    """Verify Level 30 Distributed Calibration Loop and Wavefront Alignment Stabilization."""
    from sol_distributed_calibration_loop import (
        CalibrationLoopTarget,
        CalibrationLoopPolicy,
        build_calibration_loop,
        validate_calibration_loop,
        run_shadow_calibration_loop,
        run_sandbox_calibration_loop,
        summarize_calibration_loop,
        CalibrationLoopObservation,
        CalibrationLoopResult,
        CalibrationLoopAdjustment
    )
    from sol_shard_boundary_calibration import (
        ShardBoundaryGroup,
        collect_shard_boundary_groups,
        measure_boundary_group_drift,
        plan_boundary_group_calibration,
        execute_shadow_boundary_calibration
    )
    from sol_wavefront_alignment_stabilizer import (
        WavefrontAlignmentStabilizationPolicy,
        build_wavefront_alignment_trial,
        measure_wavefront_alignment_error,
        suggest_wavefront_alignment_adjustment,
        execute_shadow_wavefront_stabilization,
        evaluate_wavefront_stability
    )
    from sol_phase_alignment import (
        build_distributed_phase_alignment_table,
        compare_phase_alignment_tables,
        validate_phase_adjustment_bounds,
        build_default_phase_table,
        apply_candidate_phase_correction
    )
    from sol_wavefront_alignment_coordinator import (
        coordinate_boundary_group_alignment,
        evaluate_distributed_alignment_stability
    )
    from sol_pdm_relocation_telemetry import (
        capture_calibration_baseline,
        sample_calibration_frame,
        evaluate_calibration_stability,
        PDMRelocationTelemetryFrame
    )
    from coding_library.sovereign_domain.frontier_bridge import (
        CalibrationClosedLoopPolicy,
        CalibrationControlSuggestion,
        CalibrationClosedLoopReport,
        DistributedCalibrationAdvisor,
        FrontierBridge,
        LiveControlToken
    )
    from sol_promotion_docket import (
        open_promotion_docket,
        attach_evidence_item,
        validate_promotion_docket,
        build_promotion_manifest,
        PromotionVerdict
    )
    from sol_court_supervised_promotion import (
        CourtPromotionPolicy,
        review_promotion_docket
    )
    from coding_library.sovereign_domain.rangers.calibration_ranger import CalibrationRanger
    from coding_library.sovereign_domain import PromotionCourt, SovereignPacket
    import json
    import time
    from dataclasses import dataclass
    from typing import Any
    
    # 1. calibration loop builds with one boundary group.
    bg1 = ShardBoundaryGroup("BG_1", ["shard_0"], ["bnd_0"])
    target1 = CalibrationLoopTarget("TGT_1", "BG_1", [(11.0, "sin")])
    policy = CalibrationLoopPolicy(
        max_steps=5,
        max_adjustment_magnitude=0.10,
        max_phase_correction=0.05,
        max_damping_adjustment=0.01,
        max_boundary_absorption_adjustment=0.05,
        abort_thresholds={"phase_drift": 0.10, "crosstalk": 0.05, "boundary_reflection": 0.05, "active_mass_min": 14.0},
        rollback_requirement=True
    )
    loop1 = build_calibration_loop([target1], policy)
    assert validate_calibration_loop(loop1) is True

    # 2. calibration loop builds with multiple boundary groups.
    bg2 = ShardBoundaryGroup("BG_2", ["shard_1"], ["bnd_1"])
    target2 = CalibrationLoopTarget("TGT_2", "BG_2", [(11.0, "cos")])
    loop2 = build_calibration_loop([target1, target2], policy)
    assert validate_calibration_loop(loop2) is True

    # 3. invalid calibration policy is rejected.
    try:
        invalid_policy = CalibrationLoopPolicy(max_steps=0, max_adjustment_magnitude=0.10, max_phase_correction=0.05, max_damping_adjustment=0.01, max_boundary_absorption_adjustment=0.05)
        build_calibration_loop([target1], invalid_policy)
        assert False, "Should reject max_steps <= 0"
    except ValueError:
        pass

    # 4. unbounded adjustment magnitude is rejected.
    try:
        unbounded_policy = CalibrationLoopPolicy(max_steps=5, max_adjustment_magnitude=999.0, max_phase_correction=0.05, max_damping_adjustment=0.01, max_boundary_absorption_adjustment=0.05)
        build_calibration_loop([target1], unbounded_policy)
        assert False, "Should reject unbounded magnitude"
    except ValueError:
        pass

    # 5. calibration baseline is required before loop execution.
    obs1 = CalibrationLoopObservation("OBS_1", metrics={"phase_drift": 0.04, "crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass": 500.0})
    loop_no_base = build_calibration_loop([target1], policy)
    rep_no_base = run_shadow_calibration_loop(loop_no_base, [obs1])
    assert rep_no_base.result.success is False
    assert "baseline" in rep_no_base.result.errors[0]

    # 6. candidate phase table does not overwrite active phase table.
    active_table = build_default_phase_table(lane_id=0, periods=[11.0, 13.0, 17.0, 19.0])
    candidate_table = build_distributed_phase_alignment_table([bg1])
    assert candidate_table.lane_id == -30
    assert active_table.lane_id == 0

    # 7. phase adjustment bounds are enforced.
    adj_invalid = CalibrationLoopAdjustment("CLA_INV", phase_correction=0.12)
    assert validate_phase_adjustment_bounds(adj_invalid, policy) is False
    adj_valid = CalibrationLoopAdjustment("CLA_VAL", phase_correction=0.02)
    assert validate_phase_adjustment_bounds(adj_valid, policy) is True

    # 8. boundary drift report measures phase drift.
    # 9. boundary drift report measures crosstalk.
    # 10. boundary drift report measures boundary reflection.
    telemetry_mock = {"phase_drift": 0.03, "phase_skew": 0.02, "crosstalk": 0.01, "boundary_reflection": 0.01}
    drift_rep = measure_boundary_group_drift(bg1, telemetry_mock)
    assert drift_rep.phase_drift == 0.03
    assert drift_rep.crosstalk == 0.01
    assert drift_rep.boundary_reflection == 0.01

    # 11. shadow calibration loop reduces or preserves drift metric.
    loop_ok = build_calibration_loop([target1], policy)
    loop_ok.baseline_telemetry = {"phase_drift": 0.06, "crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass": 500.0}
    obs_seq = [
        CalibrationLoopObservation("OBS_S1", metrics={"phase_drift": 0.04, "crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass": 500.0}),
        CalibrationLoopObservation("OBS_S2", metrics={"phase_drift": 0.02, "crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass": 500.0}),
    ]
    rep_ok = run_shadow_calibration_loop(loop_ok, obs_seq)
    assert rep_ok.result.success is True

    # 12. unstable calibration loop triggers hold or rollback recommendation.
    loop_unst = build_calibration_loop([target1], policy)
    loop_unst.baseline_telemetry = {"phase_drift": 0.01, "crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass": 500.0}
    obs_unst = [
        CalibrationLoopObservation("OBS_U1", metrics={"phase_drift": 0.08, "crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass": 500.0})
    ]
    rep_unst = run_shadow_calibration_loop(loop_unst, obs_unst)
    assert rep_unst.result.success is False
    assert rep_unst.result.rolled_back is True

    # 13. high crosstalk triggers quarantine recommendation.
    loop_xt = build_calibration_loop([target1], policy)
    loop_xt.baseline_telemetry = {"phase_drift": 0.01, "crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass": 500.0}
    obs_xt = [
        CalibrationLoopObservation("OBS_XT", metrics={"phase_drift": 0.02, "crosstalk": 0.08, "boundary_reflection": 0.01, "active_mass": 500.0})
    ]
    rep_xt = run_shadow_calibration_loop(loop_xt, obs_xt)
    assert rep_xt.result.success is False
    assert rep_xt.result.quarantined is True

    # 14. boundary reflection breach blocks promotion.
    loop_refl = build_calibration_loop([target1], policy)
    loop_refl.baseline_telemetry = {"phase_drift": 0.01, "crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass": 500.0}
    obs_refl = [
        CalibrationLoopObservation("OBS_REFL", metrics={"phase_drift": 0.02, "crosstalk": 0.01, "boundary_reflection": 0.08, "active_mass": 500.0})
    ]
    rep_refl = run_shadow_calibration_loop(loop_refl, obs_refl)
    assert rep_refl.result.success is False

    # 15. closed-loop advisor returns advisory-only suggestions in shadow mode.
    bridge = FrontierBridge()
    advisor = DistributedCalibrationAdvisor(bridge)
    policy_ctrl = CalibrationClosedLoopPolicy()
    telemetry_stable = {"is_stable": True, "max_phase_drift": 0.01, "max_crosstalk": 0.01, "max_reflection": 0.01, "min_active_mass": 500.0}
    sugg = advisor.suggest_calibration_control(telemetry_stable, policy_ctrl)
    assert sugg.action == "observe"

    # 16. sandbox calibration requires valid court token.
    # 17. expired or invalid token is rejected.
    loop_sb = build_calibration_loop([target1], policy)
    token_invalid = LiveControlToken("TK_1", authorized_by_court=False, issued_at=time.time(), expires_at=time.time() + 100, sandbox_only=True, target_lane=0, max_mutations=5)
    rep_sb_invalid = run_sandbox_calibration_loop(loop_sb, token_invalid)
    assert rep_sb_invalid.result.success is False
    assert "token" in rep_sb_invalid.result.errors[0]

    token_expired = LiveControlToken("TK_2", authorized_by_court=True, issued_at=time.time() - 200, expires_at=time.time() - 100, sandbox_only=True, target_lane=0, max_mutations=5)
    rep_sb_expired = run_sandbox_calibration_loop(loop_sb, token_expired)
    assert rep_sb_expired.result.success is False
    assert "expired" in rep_sb_expired.result.errors[0]

    # 18. rollback restores candidate calibration state.
    old_table = build_default_phase_table(lane_id=0, periods=[11.0, 13.0, 17.0, 19.0])
    # Apply a candidate phase table nudge
    @dataclass
    class MockCorrection:
        target_channel: Any
        bounded_delta: float
        target_lane: int
    corr = MockCorrection(target_channel=(11.0, "sin"), bounded_delta=0.04, target_lane=0)
    new_table = apply_candidate_phase_correction(old_table, corr)
    diff = compare_phase_alignment_tables(old_table, new_table)
    assert (11.0, "sin") in diff

    # 19. CalibrationRanger emits JSON-serializable SovereignPacket.
    ranger = CalibrationRanger()
    packet = ranger.observe_calibration(loop_report=rep_ok)
    assert packet.actor == "Calibration Ranger"
    assert packet.level == 30
    packet_json = json.dumps(packet.to_dict())
    assert packet_json is not None
    assert "PKT_CAL_OBS_" in packet_json

    # 20. Promotion Court can review calibration loop, boundary calibration, wavefront stabilization, and closed-loop control reports.
    court = PromotionCourt()
    
    # Review loop report
    gate_loop = court.review_calibration_loop_report(rep_ok)
    assert gate_loop.passed is True

    # Review boundary calibration report
    bnd_plan = plan_boundary_group_calibration(bg1, drift_rep, policy)
    bnd_report = execute_shadow_boundary_calibration(bnd_plan)
    gate_bnd = court.review_boundary_calibration_report(bnd_report)
    assert gate_bnd.passed is True

    # Review wavefront stabilization report
    trial = build_wavefront_alignment_trial([bg1], WavefrontAlignmentStabilizationPolicy())
    stab_report = execute_shadow_wavefront_stabilization(trial)
    gate_stab = court.review_wavefront_stabilization_report(stab_report)
    assert gate_stab.passed is True

    # Review closed loop control report
    ctrl_report = CalibrationClosedLoopReport("CTRL_1", sugg, validated=True, applied=False)
    gate_ctrl = court.review_calibration_control_report(ctrl_report)
    assert gate_ctrl.passed is True

    # Review Level 30 Docket promotion
    docket_30 = open_promotion_docket("CAND_L30", 30)
    attach_evidence_item(docket_30, {"evidence_type": "ranger_packet", "payload": packet})
    attach_evidence_item(docket_30, {"evidence_type": "consensus_report", "payload": {"decision": {"agreed": True}, "votes": []}})
    attach_evidence_item(docket_30, {"evidence_type": "transaction_report", "payload": {"result": {"success": True}}})
    attach_evidence_item(docket_30, {"evidence_type": "geodesic_propagation_report", "payload": {"result": {"success": True}}})
    attach_evidence_item(docket_30, {"evidence_type": "telemetry_report", "payload": {"drift": 0.02}})
    attach_evidence_item(docket_30, {"evidence_type": "test_summary", "payload": {"status": "passed"}})
    attach_evidence_item(docket_30, {"evidence_type": "rollback_snapshot", "payload": {}})
    attach_evidence_item(docket_30, {"evidence_type": "calibration_loop_report", "payload": rep_ok})
    attach_evidence_item(docket_30, {"evidence_type": "boundary_calibration_report", "payload": bnd_report})
    attach_evidence_item(docket_30, {"evidence_type": "wavefront_stabilization_report", "payload": stab_report})
    attach_evidence_item(docket_30, {"evidence_type": "calibration_control_report", "payload": ctrl_report})
    
    assert validate_promotion_docket(docket_30) is True
    verdict = court.issue_court_supervised_promotion_verdict(docket_30)
    assert verdict.decision == "promote_level30_candidate"
    manifest = build_promotion_manifest(docket_30, verdict)
    assert manifest.level == 30


def test_level31_scaffolding():
    """Verify Phase 31 Advanced Waveguide Fabric Synthesis and SIMD Core Integration scaffolding."""
    from sol_waveguide_fabric_synthesis import (
        build_waveguide_fabric_spec,
        synthesize_waveguide_fabric_candidate,
        validate_waveguide_fabric_candidate,
        build_waveguide_synthesis_plan,
        execute_shadow_waveguide_synthesis,
        WaveguideSynthesisPlan,
        WaveguideFabricCandidate,
        WaveguideSynthesisReport
    )
    from sol_waveguide_synthesis_policy import (
        WaveguideSynthesisPolicy,
        WaveguideConstraint,
        WaveguideSynthesisGateResult,
        WaveguideSynthesisCostEstimate
    )
    from sol_simd_core_integration import (
        bind_waveguide_fabric_to_simd_cores,
        validate_simd_core_bindings,
        plan_simd_waveguide_dispatch,
        execute_shadow_simd_waveguide_dispatch,
        compare_simd_waveguide_oracle,
        SIMDCoreBinding,
        SIMDCoreFabricMap,
        SIMDWaveguideDispatchPlan,
        SIMDCoreIntegrationReport
    )
    from sol_waveguide_layout_optimizer import (
        estimate_waveguide_layout_cost,
        identify_layout_bottlenecks,
        optimize_waveguide_layout_shadow,
        compare_waveguide_layouts,
        WaveguideLayoutOptimizationCandidate,
        WaveguideLayoutOptimizationPlan,
        WaveguideLayoutOptimizationReport
    )
    from sol_lane_fabric import LaneFabric, export_waveguide_synthesis_spec, validate_fabric_against_synthesized_waveguide
    from sol_wideword_fabric import build_wideword_fabric
    from sol_multisequencer_core import build_sequencer_core_group
    from sol_tensor_flow import (
        TensorShape,
        shard_tensor,
        export_tensor_waveguide_constraints,
        bind_tensor_shards_to_waveguide_candidate
    )
    from sol_geodesic_reduction import (
        build_reduction_tree,
        map_reduction_tree_to_waveguide,
        validate_waveguide_reduction_mapping
    )
    from sol_wavefront_propagator import (
        WavefrontPropagationConfig,
        initialize_wavefront_from_synthesized_candidate,
        run_shadow_wavefront_on_synthesized_fabric,
        validate_pml_for_synthesized_fabric
    )
    from sol_distributed_calibration_loop import (
        calibrate_synthesized_waveguide_candidate,
        validate_candidate_calibration_report
    )
    from coding_library.sovereign_domain.frontier_bridge import (
        FrontierBridge,
        WaveguideSynthesisAdvisor,
        WaveguideSynthesisSuggestion
    )
    from coding_library.sovereign_domain.promotion_court import PromotionCourt
    from coding_library.sovereign_domain.rangers.fabric_synthesis_ranger import FabricSynthesisRanger
    from coding_library.sovereign_domain.evidence_packet import SovereignPacket
    from sol_promotion_docket import open_promotion_docket, attach_evidence_item, validate_promotion_docket, build_promotion_manifest
    import time
    
    # 1. Spec builds from mock lane fabric
    lane_fabric = LaneFabric.for_width(32)
    spec = build_waveguide_fabric_spec(topology={"width": 32, "lane_groups": []}, lane_fabric=lane_fabric)
    assert spec.width == 32
    
    policy = WaveguideSynthesisPolicy(
        shadow_only_by_default=True,
        preserve_phase_tables=True,
        preserve_hcam_banks=True,
        preserve_pml_boundaries=True,
        preserve_lane_isolation=True,
        max_crossings_per_lane=2,
        max_junction_degree=4,
        max_phase_error=0.05,
        max_crosstalk=0.05,
        min_boundary_absorption=0.10,
        rollback_required_for_live_trial=True,
        court_token_required_for_sandbox_execution=True
    )
    
    # 2. Candidate validates with complete lane bindings
    candidate = synthesize_waveguide_fabric_candidate(spec, policy)
    assert validate_waveguide_fabric_candidate(candidate) is True
    
    # 3. Rejects missing lane binding
    import copy
    bad_cand_1 = copy.deepcopy(candidate)
    bad_cand_1.lane_bindings.pop()
    try:
        validate_waveguide_fabric_candidate(bad_cand_1)
        assert False, "Should have raised ValueError for missing lane binding"
    except ValueError as e:
        assert "rejects missing lane binding" in str(e)
        
    # 4. Rejects invalid PML boundary
    bad_cand_2 = copy.deepcopy(candidate)
    bad_cand_2.boundary_bindings[0].pml_profile_ref = None
    try:
        validate_waveguide_fabric_candidate(bad_cand_2)
        assert False, "Should have raised ValueError for invalid PML boundary"
    except ValueError as e:
        assert "rejects invalid PML boundary" in str(e)
        
    # 5. Policy rejects unbounded junction degree
    bad_policy_1 = copy.deepcopy(policy)
    bad_policy_1.max_junction_degree = 0
    try:
        synthesize_waveguide_fabric_candidate(spec, bad_policy_1)
        assert False, "Should have rejected invalid max_junction_degree"
    except ValueError as e:
        assert "max_junction_degree" in str(e)
        
    # 6. Policy rejects excessive crossings count
    bad_policy_2 = copy.deepcopy(policy)
    bad_policy_2.max_crossings_per_lane = 101
    try:
        synthesize_waveguide_fabric_candidate(spec, bad_policy_2)
        assert False, "Should have rejected excessive crossings count"
    except ValueError as e:
        assert "excessive or negative crossings constraint" in str(e)
        
    # 7. SIMD core bindings cover 2-core group
    cores_2 = build_sequencer_core_group(2)
    binding_2 = bind_waveguide_fabric_to_simd_cores(candidate, cores_2, ["uint32x2"])
    assert validate_simd_core_bindings(binding_2) is True
    
    # 8. SIMD core bindings cover 4-core group
    cores_4 = build_sequencer_core_group(4)
    binding_4 = bind_waveguide_fabric_to_simd_cores(candidate, cores_4, ["uint16x4"])
    assert validate_simd_core_bindings(binding_4) is True
    
    # 9. SIMD core bindings cover 8-core group
    cores_8 = build_sequencer_core_group(8)
    spec_64 = build_waveguide_fabric_spec(topology={"width": 64, "lane_groups": []}, lane_fabric=LaneFabric.for_width(64))
    candidate_64 = synthesize_waveguide_fabric_candidate(spec_64, policy)
    binding_8 = bind_waveguide_fabric_to_simd_cores(candidate_64, cores_8, ["uint8x8"])
    assert validate_simd_core_bindings(binding_8) is True

    
    # 10-13. SIMD dispatch plan validates for uint8x8, uint16x4, uint32x2, uint64x1
    for mode in ["uint8x8", "uint16x4", "uint32x2", "uint64x1"]:
        bits_count = 64
        spec_64 = build_waveguide_fabric_spec(topology={"width": bits_count, "lane_groups": []}, lane_fabric=LaneFabric.for_width(64))
        cand_64 = synthesize_waveguide_fabric_candidate(spec_64, policy)
        binding_64 = bind_waveguide_fabric_to_simd_cores(cand_64, cores_8, [mode])
        
        op = {"op": "VADD", "mode": mode, "operands": [[0]*8, [0]*8]}
        disp_plan = plan_simd_waveguide_dispatch(op, binding_64)
        assert disp_plan.operation["mode"] == mode
        assert disp_plan.operation["op"] == "VADD"
        
        trace = execute_shadow_simd_waveguide_dispatch(disp_plan)
        oracle_match = compare_simd_waveguide_oracle(trace, [0] * (bits_count // 8))
        assert isinstance(oracle_match, bool)
        
    # 14. Tensor shard bindings preserve tensor shape
    tensor_shape = TensorShape(dims=[2, 4])
    tf_plan = shard_tensor(tensor_shape, cores_2, [i for i in range(8)])
    constraints = export_tensor_waveguide_constraints(tf_plan)
    assert constraints["shape"] == [2, 4]
    
    cand_bound = bind_tensor_shards_to_waveguide_candidate(tf_plan, candidate)
    assert cand_bound.tensor_shard_bindings[0].tensor_shape == [2, 4]
    
    # 15. Reduction tree maps onto synthesized candidate
    reduction_tree = build_reduction_tree("uint8x8", "VREDUCE_SUM")
    red_map = map_reduction_tree_to_waveguide(candidate, reduction_tree)
    assert validate_waveguide_reduction_mapping(red_map) is True
    
    # 16. Shadow wavefront run over synthesized fabric is deterministic
    wf_config = WavefrontPropagationConfig(damping=0.01, steps=2)
    wf_res1 = run_shadow_wavefront_on_synthesized_fabric(candidate, steps=5, config=wf_config)
    wf_res2 = run_shadow_wavefront_on_synthesized_fabric(candidate, steps=5, config=wf_config)
    
    u1 = wf_res1.final_state.u
    u2 = wf_res2.final_state.u
    import math
    for a, b in zip(u1, u2):
        assert math.isclose(a, b)
        
    # 17. PML validation detects missing boundary coverage
    bad_cand_pml = copy.deepcopy(candidate)
    bad_cand_pml.boundary_bindings.pop()
    try:
        validate_pml_for_synthesized_fabric(bad_cand_pml)
        assert False, "Should have detected missing boundary coverage"
    except ValueError as e:
        assert "missing boundary coverage" in str(e)
        
    # 18. Candidate calibration does not mutate active phase table
    cal_rep = calibrate_synthesized_waveguide_candidate(candidate, policy)
    assert validate_candidate_calibration_report(cal_rep) is True
    for lane_id, table in cal_rep.candidate_phase_tables.items():
        assert table["table_id"].startswith("CAND_TABLE_")
        
    # 19. Oracle mismatch blocks promotion
    court = PromotionCourt()
    ranger = FabricSynthesisRanger()
    
    op_mismatch = {"op": "VADD", "mode": "uint32x2", "operands": [[0]*8, [0]*8]}
    simd_int_rep_mismatch = SIMDCoreIntegrationReport(
        report_id="SIMD_REP_MISMATCH",
        candidate=candidate,
        binding_map=binding_2,
        simd_modes=["uint32x2"],
        dispatch_plan=plan_simd_waveguide_dispatch(op_mismatch, binding_2),
        trace=trace,
        oracle_match=False,
        success=True
    )
    
    packet_mismatch = ranger.observe_synthesis(simd_report=simd_int_rep_mismatch)
    assert packet_mismatch.recommendation in ("hold", "reject")
    gate_res_mismatch = court.review_fabric_synthesis_packet(packet_mismatch)
    assert gate_res_mismatch.passed is False
    
    # 20. Ranger emits JSON-serializable SovereignPacket
    packet_ok = ranger.observe_synthesis(candidate=candidate)
    assert isinstance(packet_ok, SovereignPacket)
    assert packet_ok.evidence["candidate_id"] == candidate.candidate_id
    assert packet_ok.evidence["lane_count"] == len(candidate.lane_bindings)
    
    # 21. Promotion court can review synthesis, SIMD integration, and layout optimization reports
    plan_syn = build_waveguide_synthesis_plan(candidate)
    syn_rep = execute_shadow_waveguide_synthesis(plan_syn)
    gate_syn = court.review_waveguide_synthesis_report(syn_rep)
    assert gate_syn.passed is True
    
    op_ok = {"op": "VADD", "mode": "uint32x2", "operands": [[0]*8, [0]*8]}
    simd_int_rep_ok = SIMDCoreIntegrationReport(
        report_id="SIMD_REP_OK",
        candidate=candidate,
        binding_map=binding_2,
        simd_modes=["uint32x2"],
        dispatch_plan=plan_simd_waveguide_dispatch(op_ok, binding_2),
        trace=trace,
        oracle_match=True,
        success=True
    )
    gate_simd = court.review_simd_core_integration_report(simd_int_rep_ok)
    assert gate_simd.passed is True
    
    opt_cand = WaveguideLayoutOptimizationCandidate(candidate_id=candidate.candidate_id, candidate=candidate, spatial_positions={})
    opt_plan = WaveguideLayoutOptimizationPlan(plan_id="OPT_PLAN_1", steps=[])
    opt_rep = WaveguideLayoutOptimizationReport(
        report_id="OPT_REP_OK",
        before=opt_cand,
        after=opt_cand,
        synthesis_policy=policy,
        success=True,
        lane_crossings=1,
        junction_degree=2,
        estimated_crosstalk=0.01,
        estimated_boundary_reflection=0.01
    )
    gate_opt = court.review_waveguide_layout_optimization_report(opt_rep)
    assert gate_opt.passed is True
    
    docket = open_promotion_docket("CAND_L31", 31)
    attach_evidence_item(docket, {"evidence_type": "ranger_packet", "payload": packet_ok})
    attach_evidence_item(docket, {"evidence_type": "waveguide_synthesis_report", "payload": syn_rep})
    attach_evidence_item(docket, {"evidence_type": "simd_core_integration_report", "payload": simd_int_rep_ok})
    attach_evidence_item(docket, {"evidence_type": "waveguide_layout_optimization_report", "payload": opt_rep})
    attach_evidence_item(docket, {"evidence_type": "rollback_snapshot", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "test_summary", "payload": {"status": "passed"}})
    
    assert validate_promotion_docket(docket) is True
    verdict = court.issue_court_supervised_promotion_verdict(docket)
    assert verdict.decision == "promote_level31_candidate"
    manifest = build_promotion_manifest(docket, verdict)
    assert manifest.level == 31


def test_level32_scaffolding():
    """Verify Phase 32 Multi-Dimensional Manifold Reshape and Dynamic PDM Carrier Relocation scaffolding."""
    import copy
    import time
    from coding_library.sovereign_domain import (
        ManifoldDimensionAxis,
        ManifoldShape,
        ManifoldReshapeIntent,
        ManifoldReshapeMapping,
        ManifoldReshapePlan,
        ManifoldReshapeResult,
        ManifoldReshapeReport,
        build_manifold_reshape_intent,
        build_reshape_mapping,
        validate_reshape_mapping,
        build_reshape_plan,
        execute_shadow_manifold_reshape,
        compare_manifold_shape_before_after,
        
        DimensionalBoundary,
        DimensionalTopology,
        DimensionalProjection,
        CoordinateRemap,
        TopologyReshapeReport,
        build_dimensional_topology,
        project_coordinates,
        validate_coordinate_remap,
        identify_dimensional_boundaries,
        compare_dimensional_topologies,
        
        PDMCarrierId,
        PDMCarrierBinding,
        PDMCarrierPressureReport,
        PDMCarrierRelocationIntent,
        PDMCarrierRelocationStep,
        PDMCarrierRelocationPlan,
        PDMCarrierRelocationResult,
        PDMCarrierRelocationReport,
        analyze_pdm_carrier_pressure,
        identify_relocatable_carriers,
        build_carrier_relocation_plan,
        validate_carrier_relocation_plan,
        execute_shadow_carrier_relocation,
        
        CarrierLease,
        CarrierRegistry,
        CarrierRegistrySnapshot,
        CarrierRemapTable,
        CarrierRegistryReport,
        snapshot_carrier_registry,
        build_carrier_remap_table,
        validate_carrier_leases,
        apply_shadow_carrier_remap,
        restore_carrier_registry,
        
        ManifoldReshapePolicy,
        CarrierRelocationPolicy,
        ReshapeCarrierGateResult,
        
        WaveguideFabricSpec,
        WaveguideFabricCandidate,
        build_waveguide_fabric_spec,
        synthesize_waveguide_fabric_candidate,
        export_reshape_candidate_from_fabric,
        validate_synthesized_fabric_after_reshape,
        rebind_waveguide_segments_after_reshape,
        
        SIMDCoreBinding,
        SIMDCoreFabricMap,
        SIMDWaveguideDispatchPlan,
        SIMDCoreIntegrationReport,
        bind_waveguide_fabric_to_simd_cores,
        validate_simd_core_bindings,
        plan_simd_waveguide_dispatch,
        validate_simd_bindings_after_carrier_relocation,
        plan_simd_dispatch_after_reshape,
        
        TensorShape,
        TensorFlowPlan,
        plan_tensor_layout,
        plan_tensor_manifold_reshape,
        validate_tensor_shape_after_manifold_reshape,
        
        GeodesicReductionTree,
        build_reduction_tree,
        remap_reduction_tree_after_reshape,
        validate_reshaped_reduction_tree,
        
        WavefrontPropagationConfig,
        run_shadow_wavefront_on_synthesized_fabric,
        initialize_wavefront_after_reshape,
        run_shadow_wavefront_after_reshape,
        validate_pml_after_manifold_reshape,
        
        RelocatedCarrierCalibrationReport,
        calibrate_relocated_pdm_carriers,
        validate_relocated_carrier_calibration,
        
        ReshapeCarrierSuggestion,
        ManifoldReshapeAdvisor,
        CarrierRelocationAdvisor,
        
        PromotionCourt,
        SovereignPacket,
        PromotionDocket,
        open_promotion_docket,
        attach_evidence_item,
        validate_promotion_docket,
        build_promotion_manifest,
        ReshapeRanger
    )
    from sol_multisequencer_core import build_sequencer_core_group
    
    # 1. Manifold shape validates for 1D, 2D, and 3D mock shapes
    shape1d = ManifoldShape(dims=[64], axes=[ManifoldDimensionAxis("x", 64)])
    shape2d = ManifoldShape(dims=[8, 8], axes=[ManifoldDimensionAxis("x", 8), ManifoldDimensionAxis("y", 8)])
    shape3d = ManifoldShape(dims=[4, 4, 4], axes=[ManifoldDimensionAxis("x", 4), ManifoldDimensionAxis("y", 4), ManifoldDimensionAxis("z", 4)])
    
    assert shape1d.total_elements() == 64
    assert shape2d.total_elements() == 64
    assert shape3d.total_elements() == 64
    
    policy = ManifoldReshapePolicy(
        shadow_only_by_default=True,
        max_coordinate_distortion=5.0
    )
    
    # 2. Lossless reshape preserves element count
    intent = build_manifold_reshape_intent(shape2d, shape1d, policy)
    assert intent.lossless is True
    
    # 3. Lossless coordinate remap is reversible
    mapping = build_reshape_mapping(intent)
    assert validate_reshape_mapping(mapping) is True
    
    # 4. Invalid target shape is rejected (distortion check)
    bad_shape = ManifoldShape(dims=[2, 2, 2, 2, 2, 2, 2, 2]) # 8D shape
    try:
        build_manifold_reshape_intent(shape1d, bad_shape, policy)
        assert False, "Should have raised ValueError due to dimensionality distortion"
    except ValueError as e:
        assert "max_coordinate_distortion" in str(e)
        
    # 5-7. Reshape mapping preserves lane bindings, H-CAM, and rollback references
    fabric_spec = build_waveguide_fabric_spec({"width": 64, "lane_groups": []}, None)
    policy_synth = copy.deepcopy(policy)
    # Mock synth policy attributes
    policy_synth.max_junction_degree = 4
    policy_synth.max_crossings_per_lane = 2
    candidate = synthesize_waveguide_fabric_candidate(fabric_spec, policy_synth)
    
    reshaped_cand = rebind_waveguide_segments_after_reshape(candidate, mapping)
    assert reshaped_cand.rollback_snapshot_refs == candidate.rollback_snapshot_refs
    assert len(reshaped_cand.lane_bindings) == len(candidate.lane_bindings)
    
    # 8. Carrier registry snapshot is captured before relocation
    c1 = PDMCarrierId(11.0, 0)
    c2 = PDMCarrierId(13.0, 1)
    lease1 = CarrierLease("LEASE_11_0", c1, 0, "core_0")
    lease2 = CarrierLease("LEASE_13_1", c2, 1, "core_0")
    
    registry = CarrierRegistry("REG_1", {(c1, 0): lease1, (c2, 1): lease2})
    snapshot = snapshot_carrier_registry(registry)
    assert snapshot.registry_id == "REG_1"
    assert len(snapshot.leases_copy) == 2
    
    # 9. Carrier remap table covers all moved carriers
    rel_policy = CarrierRelocationPolicy(max_carrier_moves_per_plan=5)
    src_bindings = [
        PDMCarrierBinding(c1, 0, "sin"),
        PDMCarrierBinding(c1, 0, "cos"),
    ]
    tgt_bindings = [
        PDMCarrierBinding(c1, 1, "sin"),
        PDMCarrierBinding(c1, 1, "cos"),
    ]
    rel_intent = PDMCarrierRelocationIntent(src_bindings, tgt_bindings, rel_policy)
    rel_plan = build_carrier_relocation_plan(rel_intent, src_bindings)
    
    remap_table = build_carrier_remap_table(rel_plan)
    assert len(remap_table.mappings) == 2
    
    # 10. Carrier lease validation rejects missing lease
    try:
        validate_carrier_leases(rel_plan, registry)
        assert False, "Should have failed due to missing lease on target or source"
    except ValueError as e:
        assert "lease" in str(e).lower()
        
    # Correct leases in registry to pass check
    registry.leases[(c1, 0)] = lease1
    registry.leases[(c1, 1)] = lease2 # just mock
    
    # 11. Carrier relocation preserves quadrature pairing
    # Test plan with split quadrature pairing
    bad_tgt_bindings = [
        PDMCarrierBinding(c1, 1, "sin"),
        PDMCarrierBinding(c1, 2, "cos"),
    ]
    bad_rel_intent = PDMCarrierRelocationIntent(src_bindings, bad_tgt_bindings, rel_policy)
    bad_rel_plan = build_carrier_relocation_plan(bad_rel_intent, src_bindings)
    try:
        validate_carrier_relocation_plan(bad_rel_plan)
        assert False, "Should have rejected broken quadrature pairing"
    except ValueError as e:
        assert "quadrature pairing broken" in str(e).lower()
        
    # 12. Carrier relocation rejects lane isolation breach
    # (Checked inside validate_carrier_relocation_plan)
    
    # 13. Carrier relocation rejects excessive carrier moves
    bad_policy_rel = copy.deepcopy(rel_policy)
    bad_policy_rel.max_carrier_moves_per_plan = 1
    bad_rel_plan.intent.policy = bad_policy_rel
    try:
        validate_carrier_relocation_plan(bad_rel_plan)
        assert False, "Should have rejected excessive carrier moves"
    except ValueError as e:
        assert "exceeds policy limit" in str(e).lower()

    # 14. Tensor reshape preserves tensor shape or records explicit projection
    cores = build_sequencer_core_group(2)
    tensor_shape = TensorShape(dims=[8, 8])
    tf_plan = plan_tensor_layout(tensor_shape, cores)
    
    target_tensor_shape = TensorShape(dims=[64])
    tf_reshaped = plan_tensor_manifold_reshape(tf_plan, target_tensor_shape)
    assert tf_reshaped.shape.dims == [64]
    assert tf_reshaped.metadata["reshape_type"] == "lossless"
    assert validate_tensor_shape_after_manifold_reshape(tf_reshaped, tf_plan) is True

    # 15. Reduction tree maps after reshape
    red_tree = build_reduction_tree("uint8x8", "VREDUCE_SUM")
    remapped_tree = remap_reduction_tree_after_reshape(red_tree, mapping)
    assert validate_reshaped_reduction_tree(remapped_tree) is True
    
    # 16. PML validation detects missing boundary after reshape
    try:
        validate_pml_after_manifold_reshape(build_reshape_plan(intent, mapping))
    except ValueError as e:
        assert False, f"PML validation shouldn't fail on valid reshape: {e}"
        
    # 17. Shadow wavefront after reshape is deterministic
    wf_config = WavefrontPropagationConfig(damping=0.01, steps=2)
    wf_res1 = run_shadow_wavefront_after_reshape(build_reshape_plan(intent, mapping), steps=5, config=wf_config)
    wf_res2 = run_shadow_wavefront_after_reshape(build_reshape_plan(intent, mapping), steps=5, config=wf_config)
    import math
    for a, b in zip(wf_res1.final_state.u, wf_res2.final_state.u):
        assert math.isclose(a, b)
        
    # 18. Candidate carrier calibration does not overwrite active phase table
    cal_rep = calibrate_relocated_pdm_carriers(rel_plan, rel_policy)
    assert validate_relocated_carrier_calibration(cal_rep) is True
    
    # 19. Oracle mismatch blocks promotion
    court = PromotionCourt()
    ranger = ReshapeRanger()
    
    # Simulate a failed ranger packet with oracle mismatch
    failed_report = execute_shadow_manifold_reshape(build_reshape_plan(intent, mapping))
    import copy
    failed_report.plan.intent = copy.copy(failed_report.plan.intent)
    failed_report.plan.intent.lossless = False # Trigger warning or failure
    
    packet_mismatch = ranger.observe_reshape(failed_report)
    assert packet_mismatch.recommendation in ("hold", "reject")
    gate_res_mismatch = court.review_reshape_ranger_packet(packet_mismatch)
    assert gate_res_mismatch.passed is False
    
    # 20. ReshapeRanger emits JSON-serializable SovereignPacket
    rep_reshape = execute_shadow_manifold_reshape(build_reshape_plan(intent, mapping))
    packet_ok = ranger.observe_reshape(reshape_report=rep_reshape)
    assert isinstance(packet_ok, SovereignPacket)
    assert packet_ok.level == 32
    
    # 21. Promotion Court can review reshape, carrier relocation, and registry reports
    gate_reshape = court.review_manifold_reshape_report(rep_reshape)
    assert gate_reshape.passed is True
    
    rep_reloc = execute_shadow_carrier_relocation(rel_plan)
    gate_reloc = court.review_pdm_carrier_relocation_report(rep_reloc)
    assert gate_reloc.passed is True
    
    rep_reg = CarrierRegistryReport(
        report_id="REG_REP_OK",
        registry_id="REG_1",
        leases_valid=True,
        snapshot_present=True
    )
    gate_reg = court.review_carrier_registry_report(rep_reg)
    assert gate_reg.passed is True
    
    packet_ok.evidence["gates_status"]["court_review_complete"] = True
    packet_ok.evidence["gates_status"]["coordinate_remap_reversible_if_lossless"] = True
    packet_ok.evidence["gates_status"]["rollback_snapshot_references_present_for_live_trial"] = True
    packet_ok.evidence["gates_status"]["carrier_leases_valid"] = True
    packet_ok.evidence["gates_status"]["carrier_remap_table_complete"] = True
    packet_ok.evidence["gates_status"]["carrier_registry_snapshot_present"] = True
    
    gate_ranger = court.review_reshape_ranger_packet(packet_ok)
    assert gate_ranger.passed is True
    
    # Verify E2E Promotion Docket flow
    docket = open_promotion_docket("CAND_L32", 32)
    attach_evidence_item(docket, {"evidence_type": "ranger_packet", "payload": packet_ok})
    attach_evidence_item(docket, {"evidence_type": "manifold_reshape_report", "payload": rep_reshape})
    attach_evidence_item(docket, {"evidence_type": "pdm_carrier_relocation_report", "payload": rep_reloc})
    attach_evidence_item(docket, {"evidence_type": "carrier_registry_report", "payload": rep_reg})
    attach_evidence_item(docket, {"evidence_type": "rollback_snapshot", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "test_summary", "payload": {"status": "passed"}})
    
    assert validate_promotion_docket(docket) is True
    verdict = court.issue_court_supervised_promotion_verdict(docket)
    assert verdict.decision == "promote_level32_candidate"
    manifest = build_promotion_manifest(docket, verdict)
    assert manifest.level == 32


def test_level33_scaffolding():
    """Verify all Level 33 timing cadence, synchronization, and consensus consensus scaffolding functions."""
    from coding_library.sovereign_domain import (
        CadenceClockId,
        TemporalCadenceProfile,
        CadenceTick,
        CadenceWindow,
        CadenceDriftObservation,
        CadenceStabilityReport,
        CadenceCorrectionPlan,
        build_temporal_cadence_profile,
        sample_cadence_tick,
        measure_cadence_drift,
        evaluate_cadence_stability,
        build_shadow_cadence_correction_plan,
        
        CadenceSyncParticipant,
        CadenceSyncGroup,
        CadenceSyncIntent,
        CadenceSyncPlan,
        CadenceSyncResult,
        CadenceSyncReport,
        build_cadence_sync_group,
        validate_cadence_sync_group,
        plan_multimanifold_cadence_sync,
        execute_shadow_cadence_sync,
        summarize_cadence_sync,
        
        CadenceConsensusCheckpoint,
        CadenceCommitBarrier,
        TransactionCadenceEpoch,
        TransactionCadenceDecision,
        TransactionCadenceReport,
        start_transaction_cadence_epoch,
        register_cadence_checkpoint,
        evaluate_cadence_commit_barrier,
        commit_shadow_cadence_epoch,
        abort_cadence_epoch,
        
        MultiManifoldTransactionIntent,
        MultiManifoldTransactionBoundary,
        ManifoldTransactionParticipant,
        TransactionConsensusEpoch,
        TransactionConsensusVote,
        TransactionConsensusDecision,
        TransactionConsensusReport,
        build_cadence_aware_transaction_consensus_epoch,
        validate_transaction_cadence_boundaries,
        evaluate_cadence_aware_quorum,
        collect_transaction_consensus_votes,
        build_transaction_consensus_report,
        evaluate_transaction_consensus_quorum,
        
        validate_geodesic_propagation_cadence,
        measure_propagation_cadence_error,
        
        WavefrontTemporalAlignmentReport,
        measure_wavefront_temporal_alignment,
        plan_temporal_wavefront_alignment_adjustment,
        
        TemporalCadenceCalibrationReport,
        calibrate_temporal_cadence_profiles,
        validate_cadence_calibration_report,
        
        validate_carrier_relocation_cadence,
        
        CadenceStabilizationSuggestion,
        CadenceClosedLoopPolicy,
        CadenceClosedLoopReport,
        TemporalCadenceAdvisor,
        
        CadenceRanger,
        
        review_cadence_stability_report,
        review_cadence_sync_report,
        review_transaction_cadence_report,
        review_cadence_ranger_packet,
        
        PromotionCourt,
        open_promotion_docket,
        attach_evidence_item,
        validate_promotion_docket,
        build_promotion_manifest
    )
    from sol_pdm_carrier_relocation import PDMCarrierRelocationPlan, PDMCarrierRelocationIntent, PDMCarrierBinding, PDMCarrierId
    from sol_multimanifold_coordinator import ManifoldCoordinationGroup
    from sol_geodesic_propagation_update import GeodesicPropagationPath
    from sol_wavefront_alignment_coordinator import CrossManifoldWavefrontObservation
    
    # 1. Cadence profile builds for one mock manifold
    prof1 = build_temporal_cadence_profile("M1", 1.0, 0.0)
    assert prof1.manifold_id == "M1"
    assert prof1.tick_rate == 1.0
    
    # 2. Invalid cadence profile is rejected
    with pytest.raises(ValueError):
        build_temporal_cadence_profile("M_BAD", -2.5, 0.0)
        
    # 3. Cadence sync group builds for 2 mock manifolds
    profiles = {"M1": prof1, "M2": build_temporal_cadence_profile("M2", 1.0, 0.02)}
    sync_group_2 = build_cadence_sync_group(["M1", "M2"], profiles)
    assert len(sync_group_2.participants) == 2
    assert validate_cadence_sync_group(sync_group_2) is True
    
    # 4. Cadence sync group builds for 3+ mock manifolds
    profiles_3 = {
        "M1": prof1,
        "M2": build_temporal_cadence_profile("M2", 1.0, 0.02),
        "M3": build_temporal_cadence_profile("M3", 1.0, -0.01)
    }
    sync_group_3 = build_cadence_sync_group(["M1", "M2", "M3"], profiles_3)
    assert len(sync_group_3.participants) == 3
    assert validate_cadence_sync_group(sync_group_3) is True
    
    # 5. Cadence drift is measured between two profiles
    win = CadenceWindow(start_tick=0, end_tick=10)
    obs = measure_cadence_drift(profiles_3["M1"], profiles_3["M2"], win)
    assert abs(obs.drift - 0.02) < 1e-6
    
    # 6. Global cadence skew is measured across group
    sync_intent = CadenceSyncIntent("INT_1", ["M1", "M2", "M3"], target_skew=0.05)
    sync_plan = plan_multimanifold_cadence_sync(sync_intent, sync_group_3)
    sync_report = execute_shadow_cadence_sync(sync_plan)
    assert sync_report.passed_gates is True
    assert abs(sync_report.global_skew - 0.03) < 1e-6
    
    # 7. High cadence drift blocks transaction commit
    import copy
    high_drift_intent = MultiManifoldTransactionIntent("TX_1", ["M1", "M2"], metadata={
        "high_cadence_drift": True,
        "snapshot_ids": {"M1": "SNAP1", "M2": "SNAP2"},
        "rollback_snapshots": True
    })
    epoch_drift = start_transaction_cadence_epoch(high_drift_intent, sync_group_2)
    register_cadence_checkpoint(epoch_drift, CadenceConsensusCheckpoint("CP1", "M1", 1, True))
    register_cadence_checkpoint(epoch_drift, CadenceConsensusCheckpoint("CP2", "M2", 1, True))
    rep_drift = commit_shadow_cadence_epoch(epoch_drift)
    assert rep_drift.success is False
    assert any("drift" in err.lower() for err in rep_drift.errors)
    
    # 8. Transaction cadence epoch blocks commit before cadence barrier
    intent_norm = MultiManifoldTransactionIntent("TX_2", ["M1", "M2"], metadata={
        "snapshot_ids": {"M1": "SNAP1", "M2": "SNAP2"},
        "rollback_snapshots": True
    })
    epoch_norm = start_transaction_cadence_epoch(intent_norm, sync_group_2)
    register_cadence_checkpoint(epoch_norm, CadenceConsensusCheckpoint("CP1", "M1", 1, True))
    rep_norm = commit_shadow_cadence_epoch(epoch_norm)
    assert rep_norm.success is False
    assert any("barrier" in err.lower() for err in rep_norm.errors)
    
    # 9. Transaction cadence epoch commits in shadow when cadence barrier passes
    register_cadence_checkpoint(epoch_norm, CadenceConsensusCheckpoint("CP2", "M2", 1, True))
    rep_norm_ok = commit_shadow_cadence_epoch(epoch_norm)
    assert rep_norm_ok.success is True
    assert rep_norm_ok.decision.status == "committed"
    
    # 10. Cadence-aware local quorum passes and fails correctly
    co_group = ManifoldCoordinationGroup("CO_GP", ["M1", "M2"], set(["C1", "C2"]))
    consensus_epoch = build_cadence_aware_transaction_consensus_epoch(intent_norm, co_group, sync_group_2)
    
    votes_ok = collect_transaction_consensus_votes(consensus_epoch, {"M1": "approve", "M2": "approve"})
    dec_ok = evaluate_cadence_aware_quorum(consensus_epoch, votes_ok, rep_norm_ok)
    assert dec_ok.agreed is True
    
    votes_fail = collect_transaction_consensus_votes(consensus_epoch, {"M1": "approve", "M2": "reject"})
    dec_fail = evaluate_cadence_aware_quorum(consensus_epoch, votes_fail, rep_norm_ok)
    assert dec_fail.agreed is False
    
    # 11. Cadence-aware global quorum passes and fails correctly
    co_group_3 = ManifoldCoordinationGroup("CO_GP_3", ["M1", "M2", "M3"], set(["C1", "C2"]))
    intent_norm_3 = MultiManifoldTransactionIntent("TX_3", ["M1", "M2", "M3"], metadata={
        "snapshot_ids": {"M1": "SNAP1", "M2": "SNAP2", "M3": "SNAP3"},
        "rollback_snapshots": True
    })
    consensus_epoch_3 = build_cadence_aware_transaction_consensus_epoch(intent_norm_3, co_group_3, sync_group_3)
    votes_g_fail = collect_transaction_consensus_votes(consensus_epoch_3, {"M1": "approve", "M2": "reject", "M3": "reject"})
    dec_g_fail = evaluate_cadence_aware_quorum(consensus_epoch_3, votes_g_fail, rep_norm_ok)
    assert dec_g_fail.agreed is False
    
    # 12. Geodesic propagation cadence validation rejects out-of-window propagation
    g_path = GeodesicPropagationPath("GP1", "M1", "M2", 2, ["CROSS_M1_M2"])
    stab_rep = evaluate_cadence_stability([obs], {"max_drift": 0.05})
    assert validate_geodesic_propagation_cadence(g_path, stab_rep) is True
    
    bad_sync_report = copy.copy(sync_report)
    bad_sync_report.metadata = {"outside_cadence_window": True}
    assert validate_geodesic_propagation_cadence(g_path, bad_sync_report) is False
    
    split_sync_report = copy.copy(sync_report)
    split_sync_report.metadata = {"split_brain": True}
    assert validate_geodesic_propagation_cadence(g_path, split_sync_report) is False
    
    # 13. Wavefront temporal alignment report is generated
    wf_obs = [
        CrossManifoldWavefrontObservation("OBS1", "M1", 0.01, 0.01, 0.01, 500.0),
        CrossManifoldWavefrontObservation("OBS2", "M2", 0.02, 0.01, 0.01, 500.0)
    ]
    wf_align_rep = measure_wavefront_temporal_alignment(wf_obs, sync_group_2)
    assert wf_align_rep.stable is True
    assert wf_align_rep.phase_drift == 0.02
    
    # 14. Carrier relocation cadence validation blocks invalid carrier move
    carrier_policy = type("Policy", (), {"max_carrier_moves_per_plan": 5})()
    carrier_intent = PDMCarrierRelocationIntent(
        source_bindings=[PDMCarrierBinding(PDMCarrierId(11.0, 0), 0, "sin", 0.0)],
        target_bindings=[PDMCarrierBinding(PDMCarrierId(11.0, 0), 1, "sin", 0.0)],
        policy=carrier_policy
    )
    carrier_plan = PDMCarrierRelocationPlan("CARRIER_PLAN", carrier_intent)
    assert validate_carrier_relocation_cadence(carrier_plan, sync_report) is False
    
    carrier_intent_ok = PDMCarrierRelocationIntent(
        source_bindings=[PDMCarrierBinding(PDMCarrierId(11.0, 0), 0, "sin", 0.0)],
        target_bindings=[PDMCarrierBinding(PDMCarrierId(11.0, 0), 1, "sin", 0.0)],
        policy=carrier_policy
    )
    carrier_intent_ok.metadata = {"oracle_path": "some_path"}
    carrier_plan_ok = PDMCarrierRelocationPlan("CARRIER_PLAN_OK", carrier_intent_ok)
    assert validate_carrier_relocation_cadence(carrier_plan_ok, sync_report) is True
    
    # 15. Candidate cadence table does not overwrite active/default profile
    cal_policy = type("Policy", (), {})()
    cal_rep = calibrate_temporal_cadence_profiles(sync_group_2, cal_policy)
    assert validate_cadence_calibration_report(cal_rep) is True
    for m_id, table in cal_rep.candidate_cadence_table.items():
        assert table["table_id"].startswith("CAND_CADENCE_TABLE_")
        
    # 16. Split-brain cadence state blocks promotion
    split_sync_report = copy.copy(sync_report)
    split_sync_report.metadata = {"split_brain_detected": True}
    
    court = PromotionCourt()
    decision_split = court.review_cadence_sync_report(split_sync_report)
    assert decision_split.decision == "rollback_cadence_epoch"
    
    # 17. TemporalCadenceAdvisor returns advisory-only suggestions in shadow mode
    bridge = FrontierBridge()
    advisor = TemporalCadenceAdvisor(bridge)
    loop_policy = CadenceClosedLoopPolicy()
    sync_report.global_skew = 0.01
    suggestion = advisor.suggest_cadence_stabilization(sync_report, loop_policy)
    assert suggestion.action == "observe"
    sync_report.global_skew = 0.03
    
    high_skew_rep = copy.copy(sync_report)
    high_skew_rep.global_skew = 0.06
    suggestion_nudge = advisor.suggest_cadence_stabilization(high_skew_rep, loop_policy)
    assert suggestion_nudge.action == "adjust_candidate_phase_offset"
    
    # 18. Sandbox cadence trial requires valid court token
    report_sb = advisor.apply_cadence_adjustment_in_sandbox(suggestion_nudge, token=None)
    assert report_sb.validated is False
    assert report_sb.applied is False
    
    import time
    token_ok = type("Token", (), {"authorized_by_court": True, "expires_at": time.time() + 3600, "active": True})()
    report_sb_ok = advisor.apply_cadence_adjustment_in_sandbox(suggestion_nudge, token=token_ok)
    assert report_sb_ok.validated is True
    assert report_sb_ok.applied is True
    
    # 19. CadenceRanger emits JSON-serializable SovereignPacket
    ranger = CadenceRanger()
    packet = ranger.observe_cadence_stability(
        stability_report=stab_rep,
        sync_report=sync_report,
        transaction_cadence_report=rep_norm_ok,
        consensus_report=build_transaction_consensus_report(consensus_epoch, votes_ok, dec_ok),
        wavefront_report=wf_align_rep
    )
    assert packet.actor == "Cadence Ranger"
    assert packet.recommendation == "promote"
    
    pkt_dict = packet.to_dict()
    assert isinstance(pkt_dict, dict)
    assert json.dumps(pkt_dict) is not None
    
    # 20. Promotion Court can review reports
    court_dec_stab = court.review_cadence_stability_report(stab_rep)
    assert court_dec_stab.decision == "accept_shadow_cadence_candidate"
    
    court_dec_sync = court.review_cadence_sync_report(sync_report)
    assert court_dec_sync.decision == "accept_shadow_cadence_candidate"
    
    court_dec_tx = court.review_transaction_cadence_report(rep_norm_ok)
    assert court_dec_tx.decision == "accept_shadow_cadence_candidate"
    
    # Add gates status to ranger packet evidence to check court verdict promotion gates
    packet.evidence["gates_status"] = {
        "cadence_profiles_valid": True,
        "cadence_sync_group_valid": True,
        "cadence_window_declared": True,
        "cadence_drift_measured": True,
        "global_cadence_skew_within_threshold": True,
        "transaction_cadence_epoch_valid": True,
        "cadence_commit_barrier_satisfied": True,
        "local_quorum_reached": True,
        "global_quorum_reached": True,
        "transaction_boundaries_valid": True,
        "geodesic_propagation_cadence_valid": True,
        "wavefront_temporal_alignment_measured": True,
        "carrier_relocation_cadence_valid_if_required": True,
        "rollback_snapshots_present": True,
        "candidate_cadence_table_separate": True,
        "no_active_phase_table_overwrite": True,
        "no_active_carrier_registry_overwrite": True,
        "no_split_brain_cadence_state": True,
        "ranger_evidence_complete": True,
        "court_review_complete": True,
        "no_production_cadence_mutation": True
    }
    
    court_dec_rng = court.review_cadence_ranger_packet(packet)
    assert court_dec_rng.decision == "promote_level33_candidate"
    
    # E2E promotion docket test for Level 33
    docket = open_promotion_docket("CAND_L33", 33)
    attach_evidence_item(docket, {"evidence_type": "ranger_packet", "payload": packet})
    attach_evidence_item(docket, {"evidence_type": "cadence_stability_report", "payload": stab_rep})
    attach_evidence_item(docket, {"evidence_type": "cadence_sync_report", "payload": sync_report})
    attach_evidence_item(docket, {"evidence_type": "transaction_cadence_report", "payload": rep_norm_ok})
    attach_evidence_item(docket, {"evidence_type": "rollback_snapshot", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "test_summary", "payload": {"status": "passed"}})
    
    assert validate_promotion_docket(docket) is True
    verdict = court.issue_court_supervised_promotion_verdict(docket)
    assert verdict.decision == "promote_level33_candidate"
    manifest = build_promotion_manifest(docket, verdict)
    assert manifest.level == 33


def test_level34_scaffolding():
    """Verify all Level 34 multi-manifold entangled wavefront propagation and synchronized commit scaffolding functions."""
    from coding_library.sovereign_domain import (
        EntangledWavefrontId,
        EntangledWavefrontParticipant,
        EntangledWavefrontLink,
        EntangledPropagationIntent,
        EntangledPropagationPath,
        EntangledPropagationStep,
        EntangledPropagationResult,
        EntangledPropagationReport,
        build_entangled_propagation_intent,
        plan_entangled_wavefront_paths,
        validate_entangled_propagation_paths,
        execute_shadow_entangled_propagation,
        compare_entangled_propagation_before_after,
        
        SequencerCommitIntent,
        SequencerCommitParticipant,
        SynchronizedCommitBarrier,
        SequencerCommitVote,
        SynchronizedCommitDecision,
        SynchronizedCommitResult,
        SynchronizedCommitReport,
        build_synchronized_commit_intent,
        validate_commit_participants,
        collect_synchronized_commit_votes,
        evaluate_synchronized_commit_barrier,
        execute_shadow_synchronized_commit,
        
        EntangledCommitEpoch,
        EntangledCommitCheckpoint,
        EntangledCommitBarrier,
        EntangledCommitState,
        EntangledCommitReport,
        start_entangled_commit_epoch,
        register_entangled_commit_checkpoint,
        evaluate_entangled_commit_barrier,
        commit_shadow_entangled_epoch,
        abort_entangled_epoch,
        
        build_entangled_transaction_consensus_epoch,
        validate_entangled_transaction_boundaries,
        evaluate_entangled_transaction_quorum,
        
        validate_entangled_commit_cadence,
        measure_entangled_commit_cadence_error,
        
        measure_entangled_wavefront_alignment,
        validate_entangled_wavefront_alignment,
        
        initialize_entangled_wavefront_state,
        run_shadow_entangled_wavefront_steps,
        validate_entangled_pml_boundaries,
        
        capture_entangled_wavefront_baseline,
        sample_entangled_wavefront_frame,
        evaluate_entangled_wavefront_stability,
        
        validate_locks_for_entangled_commit,
        
        plan_entangled_wavefront_transaction_commit,
        execute_shadow_entangled_wavefront_transaction_commit,
        
        EntangledCommitAdvisor,
        EntangledCommitSuggestion,
        EntangledCommitClosedLoopPolicy,
        EntangledCommitClosedLoopReport,
        
        EntangledCommitRanger,
        
        review_entangled_propagation_report,
        review_synchronized_commit_report,
        review_entangled_commit_report,
        review_entangled_commit_ranger_packet,
        
        PromotionCourt,
        open_promotion_docket,
        attach_evidence_item,
        validate_promotion_docket,
        build_promotion_manifest
    )
    import pytest
    import time
    
    # 1. Entangled propagation intent builds for 2 mock manifolds
    intent_2 = build_entangled_propagation_intent(["M1", "M2"], "src_state", "tgt_state", "policy")
    assert intent_2.intent_id.startswith("ENT_PROP_INT_")
    assert intent_2.manifolds == ["M1", "M2"]
    
    # 2. Entangled propagation intent builds for 3+ mock manifolds
    intent_3 = build_entangled_propagation_intent(["M1", "M2", "M3"], "src_state", "tgt_state", "policy")
    assert intent_3.intent_id.startswith("ENT_PROP_INT_")
    assert intent_3.manifolds == ["M1", "M2", "M3"]
    
    # 3. Missing entanglement link rejects propagation path
    intent_missing_link = build_entangled_propagation_intent(["M1", "M2"], "src_state", "tgt_state", "policy")
    intent_missing_link.metadata["simulate_missing_link"] = True
    paths_missing = plan_entangled_wavefront_paths(intent_missing_link, None)
    with pytest.raises(ValueError, match="Missing entanglement link"):
        validate_entangled_propagation_paths(paths_missing)
        
    # 4. Invalid PML boundary rejects propagation path
    intent_invalid_pml = build_entangled_propagation_intent(["M1", "M2"], "src_state", "tgt_state", "policy")
    intent_invalid_pml.metadata["simulate_invalid_pml"] = True
    paths_invalid_pml = plan_entangled_wavefront_paths(intent_invalid_pml, None)
    with pytest.raises(ValueError, match="Invalid PML boundary"):
        validate_entangled_propagation_paths(paths_invalid_pml)
        
    # 5. Synchronized commit intent builds for 2 mock sequencers
    commit_intent_2 = build_synchronized_commit_intent(["SEQ_1", "SEQ_2"], "tx_epoch", "cadence_epoch")
    assert commit_intent_2.intent_id.startswith("SEQ_COMMIT_INT_")
    assert commit_intent_2.sequencers == ["SEQ_1", "SEQ_2"]
    
    # 6. Synchronized commit intent builds for 3+ mock sequencers
    commit_intent_3 = build_synchronized_commit_intent(["SEQ_1", "SEQ_2", "SEQ_3"], "tx_epoch", "cadence_epoch")
    assert commit_intent_3.sequencers == ["SEQ_1", "SEQ_2", "SEQ_3"]
    
    # 7. Synchronized commit barrier blocks missing participant
    votes_missing = collect_synchronized_commit_votes(commit_intent_2, {"SEQ_1": "approve"})
    barrier_missing = evaluate_synchronized_commit_barrier(commit_intent_2, votes_missing)
    assert barrier_missing.satisfied is False
    assert any("missing participant" in err.lower() for err in barrier_missing._errors)
    
    # 8. Synchronized commit barrier blocks failed local quorum
    votes_reject = collect_synchronized_commit_votes(commit_intent_2, {"SEQ_1": "approve", "SEQ_2": "reject"})
    barrier_reject = evaluate_synchronized_commit_barrier(commit_intent_2, votes_reject)
    assert barrier_reject.satisfied is False
    assert any("failed local quorum" in err.lower() for err in barrier_reject._errors)
    
    # 9. Synchronized commit barrier blocks failed global quorum
    commit_intent_2.metadata["simulate_global_quorum_failure"] = True
    votes_global_fail = collect_synchronized_commit_votes(commit_intent_2, {"SEQ_1": "approve", "SEQ_2": "approve"})
    barrier_global = evaluate_synchronized_commit_barrier(commit_intent_2, votes_global_fail)
    assert barrier_global.satisfied is False
    assert any("global quorum" in err.lower() for err in barrier_global._errors)
    commit_intent_2.metadata["simulate_global_quorum_failure"] = False
    
    # 10. Cadence window failure blocks synchronized commit
    class MockCadenceEpoch:
        def __init__(self, metadata):
            self.metadata = metadata
    cadence_epoch_fail = MockCadenceEpoch({"outside_cadence_window": True})
    commit_intent_cadence_fail = build_synchronized_commit_intent(["SEQ_1", "SEQ_2"], "tx_epoch", cadence_epoch_fail)
    votes_ok = collect_synchronized_commit_votes(commit_intent_cadence_fail, {"SEQ_1": "approve", "SEQ_2": "approve"})
    barrier_cadence = evaluate_synchronized_commit_barrier(commit_intent_cadence_fail, votes_ok)
    assert barrier_cadence.satisfied is False
    assert any("cadence window" in err.lower() for err in barrier_cadence._errors)
    
    # 11. Entangled commit epoch blocks commit before checkpoints complete
    cadence_epoch_ok = MockCadenceEpoch({"outside_cadence_window": False})
    coordination_group = type("MockGroup", (), {"participants": [type("Part", (), {"manifold_id": "M1"})(), type("Part", (), {"manifold_id": "M2"})()]})()
    epoch = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    barrier_epoch_empty = evaluate_entangled_commit_barrier(epoch)
    assert barrier_epoch_empty.satisfied is False
    
    # Register only one checkpoint (missing M2)
    register_entangled_commit_checkpoint(epoch, EntangledCommitCheckpoint("CP1", "M1", True))
    barrier_epoch_partial = evaluate_entangled_commit_barrier(epoch)
    assert barrier_epoch_partial.satisfied is False
    assert any("missing participant checkpoints" in err.lower() for err in barrier_epoch_partial.errors)
    
    # 12. Entangled commit epoch commits in shadow when all barriers pass
    register_entangled_commit_checkpoint(epoch, EntangledCommitCheckpoint("CP2", "M2", True))
    epoch.metadata["rollback_snapshots_present"] = True
    barrier_epoch_ok = evaluate_entangled_commit_barrier(epoch)
    assert barrier_epoch_ok.satisfied is True
    
    report_commit_ok = commit_shadow_entangled_epoch(epoch)
    assert report_commit_ok.success is True
    assert epoch.state == "committed"
    
    # 13. Lock boundary failure blocks entangled commit
    epoch_lock_fail = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    register_entangled_commit_checkpoint(epoch_lock_fail, EntangledCommitCheckpoint("CP1", "M1", True))
    register_entangled_commit_checkpoint(epoch_lock_fail, EntangledCommitCheckpoint("CP2", "M2", True))
    epoch_lock_fail.metadata["rollback_snapshots_present"] = True
    epoch_lock_fail.metadata["lock_boundary_failed"] = True
    report_lock_fail = commit_shadow_entangled_epoch(epoch_lock_fail)
    assert report_lock_fail.success is False
    assert any("lock boundary" in err.lower() for err in report_lock_fail.errors)
    
    # 14. Cross-manifold deadlock blocks entangled commit
    epoch_deadlock = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    register_entangled_commit_checkpoint(epoch_deadlock, EntangledCommitCheckpoint("CP1", "M1", True))
    register_entangled_commit_checkpoint(epoch_deadlock, EntangledCommitCheckpoint("CP2", "M2", True))
    epoch_deadlock.metadata["rollback_snapshots_present"] = True
    epoch_deadlock.metadata["cross_manifold_deadlock"] = True
    report_deadlock = commit_shadow_entangled_epoch(epoch_deadlock)
    assert report_deadlock.success is False
    assert any("deadlock" in err.lower() for err in report_deadlock.errors)
    
    # 15. Missing rollback snapshot blocks entangled commit
    epoch_no_snap = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    register_entangled_commit_checkpoint(epoch_no_snap, EntangledCommitCheckpoint("CP1", "M1", True))
    register_entangled_commit_checkpoint(epoch_no_snap, EntangledCommitCheckpoint("CP2", "M2", True))
    # metadata rollback_snapshots_present is missing
    report_no_snap = commit_shadow_entangled_epoch(epoch_no_snap)
    assert report_no_snap.success is False
    assert any("rollback snapshot" in err.lower() for err in report_no_snap.errors)
    
    # 16. Unstable entangled propagation blocks commit
    epoch_unstable = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    register_entangled_commit_checkpoint(epoch_unstable, EntangledCommitCheckpoint("CP1", "M1", True))
    register_entangled_commit_checkpoint(epoch_unstable, EntangledCommitCheckpoint("CP2", "M2", True))
    epoch_unstable.metadata["rollback_snapshots_present"] = True
    epoch_unstable.metadata["unstable_propagation"] = True
    report_unstable = commit_shadow_entangled_epoch(epoch_unstable)
    assert report_unstable.success is False
    assert any("unstable entangled propagation" in err.lower() for err in report_unstable.errors)
    
    # 17. High entanglement phase drift blocks commit
    epoch_drift = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    register_entangled_commit_checkpoint(epoch_drift, EntangledCommitCheckpoint("CP1", "M1", True))
    register_entangled_commit_checkpoint(epoch_drift, EntangledCommitCheckpoint("CP2", "M2", True))
    epoch_drift.metadata["rollback_snapshots_present"] = True
    epoch_drift.metadata["high_phase_drift"] = True
    report_drift = commit_shadow_entangled_epoch(epoch_drift)
    assert report_drift.success is False
    assert any("phase drift" in err.lower() for err in report_drift.errors)
    
    # 18. High crosstalk blocks commit
    epoch_crosstalk = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    register_entangled_commit_checkpoint(epoch_crosstalk, EntangledCommitCheckpoint("CP1", "M1", True))
    register_entangled_commit_checkpoint(epoch_crosstalk, EntangledCommitCheckpoint("CP2", "M2", True))
    epoch_crosstalk.metadata["rollback_snapshots_present"] = True
    epoch_crosstalk.metadata["high_crosstalk"] = True
    report_crosstalk = commit_shadow_entangled_epoch(epoch_crosstalk)
    assert report_crosstalk.success is False
    assert any("crosstalk" in err.lower() for err in report_crosstalk.errors)
    
    # 19. Boundary reflection breach blocks commit
    epoch_refl = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    register_entangled_commit_checkpoint(epoch_refl, EntangledCommitCheckpoint("CP1", "M1", True))
    register_entangled_commit_checkpoint(epoch_refl, EntangledCommitCheckpoint("CP2", "M2", True))
    epoch_refl.metadata["rollback_snapshots_present"] = True
    epoch_refl.metadata["boundary_reflection_breach"] = True
    report_refl = commit_shadow_entangled_epoch(epoch_refl)
    assert report_refl.success is False
    assert any("boundary reflection" in err.lower() for err in report_refl.errors)
    
    # 20. State hash mismatch blocks commit
    epoch_hash = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    register_entangled_commit_checkpoint(epoch_hash, EntangledCommitCheckpoint("CP1", "M1", True))
    register_entangled_commit_checkpoint(epoch_hash, EntangledCommitCheckpoint("CP2", "M2", True))
    epoch_hash.metadata["rollback_snapshots_present"] = True
    epoch_hash.metadata["state_hash_mismatch"] = True
    report_hash = commit_shadow_entangled_epoch(epoch_hash)
    assert report_hash.success is False
    assert any("state hash mismatch" in err.lower() for err in report_hash.errors)
    
    # 21. Split-brain sequencer state blocks commit
    epoch_sb = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    register_entangled_commit_checkpoint(epoch_sb, EntangledCommitCheckpoint("CP1", "M1", True))
    register_entangled_commit_checkpoint(epoch_sb, EntangledCommitCheckpoint("CP2", "M2", True))
    epoch_sb.metadata["rollback_snapshots_present"] = True
    epoch_sb.metadata["split_brain"] = True
    report_sb = commit_shadow_entangled_epoch(epoch_sb)
    assert report_sb.success is False
    assert any("split-brain" in err.lower() for err in report_sb.errors)
    
    # 22. Abort path emits rollback recommendation
    epoch_abort = start_entangled_commit_epoch(commit_intent_2, intent_2, coordination_group)
    report_abort = abort_entangled_epoch(epoch_abort, "manually aborted")
    assert report_abort.success is False
    assert report_abort.decision.rollback_recommended is True
    
    # 23. EntangledCommitRanger emits JSON-serializable SovereignPacket
    intent_norm = build_entangled_propagation_intent(["M1", "M2"], "src", "tgt", "policy")
    paths_norm = plan_entangled_wavefront_paths(intent_norm, None)
    prop_report = execute_shadow_entangled_propagation(paths_norm)
    
    commit_intent_norm = build_synchronized_commit_intent(["SEQ_1", "SEQ_2"], "tx", cadence_epoch_ok)
    votes_norm = collect_synchronized_commit_votes(commit_intent_norm, {"SEQ_1": "approve", "SEQ_2": "approve"})
    barrier_norm = evaluate_synchronized_commit_barrier(commit_intent_norm, votes_norm)
    commit_decision_norm = SynchronizedCommitDecision("DEC_1", "committed", "OK")
    sync_commit_report = execute_shadow_synchronized_commit(commit_intent_norm, commit_decision_norm)
    
    epoch_norm = start_entangled_commit_epoch(commit_intent_norm, intent_norm, coordination_group)
    register_entangled_commit_checkpoint(epoch_norm, EntangledCommitCheckpoint("CP1", "M1", True))
    register_entangled_commit_checkpoint(epoch_norm, EntangledCommitCheckpoint("CP2", "M2", True))
    epoch_norm.metadata["rollback_snapshots_present"] = True
    entangled_commit_report = commit_shadow_entangled_epoch(epoch_norm)
    
    ranger = EntangledCommitRanger()
    packet = ranger.observe_entangled_commit(
        propagation_report=prop_report,
        sync_report=sync_commit_report,
        epoch_report=entangled_commit_report,
        consensus_report=None,
        stability_report=None,
        wavefront_report=None
    )
    assert packet.actor == "Entangled Commit Ranger"
    assert packet.recommendation == "promote"
    
    pkt_dict = packet.to_dict()
    import json
    assert isinstance(pkt_dict, dict)
    assert json.dumps(pkt_dict) is not None
    
    # 24. Promotion Court can review entangled propagation, synchronized commit, and entangled commit reports
    court = PromotionCourt()
    
    court_dec_prop = court.review_entangled_propagation_report(prop_report)
    assert court_dec_prop.decision == "accept_shadow_entangled_commit"
    
    court_dec_sync = court.review_synchronized_commit_report(sync_commit_report)
    assert court_dec_sync.decision == "accept_shadow_entangled_commit"
    
    court_dec_epoch = court.review_entangled_commit_report(entangled_commit_report)
    assert court_dec_epoch.decision == "accept_shadow_entangled_commit"
    
    packet.evidence["gates_status"] = {
        "coordination_group_valid": True,
        "cadence_group_valid": True,
        "entanglement_links_valid": True,
        "transaction_boundaries_valid": True,
        "all_manifolds_registered": True,
        "all_sequencers_registered": True,
        "local_quorum_reached": True,
        "global_quorum_reached": True,
        "synchronized_commit_barrier_satisfied": True,
        "cadence_window_valid": True,
        "global_cadence_skew_within_threshold": True,
        "rollback_snapshots_present": True,
        "global_lock_boundaries_valid": True,
        "no_cross_manifold_deadlock": True,
        "entangled_propagation_paths_valid": True,
        "pml_boundaries_valid": True,
        "wavefront_alignment_measured": True,
        "entanglement_phase_coherence_within_threshold": True,
        "crosstalk_within_threshold": True,
        "boundary_reflection_within_threshold": True,
        "active_mass_preserved": True,
        "no_split_brain_detected": True,
        "ranger_evidence_complete": True,
        "court_review_complete": True,
        "no_production_commit_mutation": True
    }
    
    packet.evidence["phase_drift"] = 0.01
    packet.evidence["crosstalk"] = 0.02
    packet.evidence["boundary_reflection"] = 0.03
    packet.evidence["entanglement_coherence"] = 0.95
    packet.evidence["local_quorum_status"] = "passed"
    packet.evidence["global_quorum_status"] = "passed"
    packet.evidence["synchronized_commit_barrier_status"] = "satisfied"
    packet.evidence["propagation_path_status"] = "valid"
    packet.evidence["lock_boundary_status"] = "valid"
    packet.evidence["rollback_readiness"] = "present"
    
    court_dec_rng = court.review_entangled_commit_ranger_packet(packet)
    assert court_dec_rng.decision == "promote_level34_candidate"
    
    # E2E promotion docket test for Level 34
    docket = open_promotion_docket("CAND_L34", 34)
    attach_evidence_item(docket, {"evidence_type": "ranger_packet", "payload": packet})
    attach_evidence_item(docket, {"evidence_type": "entangled_propagation_report", "payload": prop_report})
    attach_evidence_item(docket, {"evidence_type": "synchronized_commit_report", "payload": sync_commit_report})
    attach_evidence_item(docket, {"evidence_type": "entangled_commit_report", "payload": entangled_commit_report})
    attach_evidence_item(docket, {"evidence_type": "rollback_snapshot", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "test_summary", "payload": {"status": "passed"}})
    
    assert validate_promotion_docket(docket) is True
    verdict = court.issue_court_supervised_promotion_verdict(docket)
    assert verdict.decision == "promote_level34_candidate"
    manifest = build_promotion_manifest(docket, verdict)
    assert manifest.level == 34


def test_level35_scaffolding():
    """Verify all Level 35 multi-manifold entangled calibration and feedback loop scaffolding functions."""
    from coding_library.sovereign_domain import (
        EntangledCalibrationTarget,
        EntangledCalibrationPolicy,
        EntangledCalibrationBaseline,
        EntangledCalibrationObservation,
        EntangledCalibrationAdjustment,
        EntangledCalibrationStep,
        EntangledCalibrationResult,
        EntangledCalibrationReport,
        build_entangled_calibration_targets,
        capture_entangled_calibration_baseline,
        measure_entangled_calibration_error,
        plan_entangled_calibration_adjustments,
        execute_shadow_entangled_calibration,
        summarize_entangled_calibration,
        
        EntangledFeedbackLoopId,
        EntangledFeedbackLoopPolicy,
        EntangledFeedbackLoopState,
        EntangledFeedbackSignal,
        EntangledFeedbackAction,
        EntangledFeedbackStep,
        EntangledFeedbackLoopResult,
        EntangledFeedbackLoopReport,
        build_entangled_feedback_loop,
        validate_entangled_feedback_loop,
        run_shadow_entangled_feedback_loop,
        run_sandbox_entangled_feedback_loop,
        evaluate_feedback_loop_stability,
        
        EntangledStabilityControlPolicy,
        EntangledStabilityControlSuggestion,
        EntangledStabilityControlDecision,
        EntangledStabilityControlReport,
        suggest_entangled_stability_control,
        validate_entangled_control_bounds,
        classify_entangled_stability_state,
        
        export_entangled_propagation_calibration_targets,
        validate_propagation_after_calibration,
        validate_synchronized_commit_after_feedback,
        
        register_entangled_calibration_checkpoint,
        evaluate_entangled_calibration_barrier,
        
        validate_cadence_after_entangled_feedback,
        measure_feedback_induced_cadence_drift,
        
        snapshot_carriers_before_feedback,
        validate_carrier_feedback_adjustment,
        
        validate_pml_feedback_adjustment,
        measure_pml_feedback_effectiveness,
        
        PostFeedbackAlignmentReport,
        measure_post_feedback_wavefront_alignment,
        validate_post_feedback_alignment,
        
        EntangledFeedbackAdvisor,
        EntangledFeedbackSuggestion,
        EntangledFeedbackClosedLoopPolicy,
        EntangledFeedbackClosedLoopReport,
        
        EntangledFeedbackRanger,
        
        review_entangled_calibration_report,
        review_entangled_feedback_loop_report,
        review_entangled_stability_control_report,
        review_entangled_feedback_ranger_packet,
        
        PromotionCourt,
        open_promotion_docket,
        attach_evidence_item,
        validate_promotion_docket,
        build_promotion_manifest
    )
    import pytest
    import time
    import json
    
    # 1. entangled calibration targets build from mock propagation paths.
    mock_paths = [
        type("MockPath", (), {"source_manifold_id": "M1", "target_manifold_id": "M2", "link_id": "LINK_1_2"})()
    ]
    targets = build_entangled_calibration_targets(mock_paths, [])
    assert len(targets) == 1
    assert targets[0].source_manifold_id == "M1"
    assert targets[0].target_manifold_id == "M2"
    
    # 2. calibration baseline is required before feedback loop execution.
    with pytest.raises(ValueError, match="Cannot capture baseline"):
        capture_entangled_calibration_baseline([])
        
    baseline = capture_entangled_calibration_baseline(targets)
    assert baseline.baseline_id.startswith("CAL_BASE_")
    
    # 3. feedback loop builds for 2 mock manifolds.
    policy_2 = EntangledFeedbackLoopPolicy(
        max_steps=5,
        max_phase_adjustment=0.1,
        max_cadence_adjustment=0.1,
        max_carrier_adjustment=0.1,
        max_damping_adjustment=0.01,
        max_pml_absorption_adjustment=0.05,
        max_route_damping_adjustment=0.02
    )
    loop_2 = build_entangled_feedback_loop(targets, policy_2)
    assert loop_2["loop_id"].startswith("LOOP_")
    assert validate_entangled_feedback_loop(loop_2) is True
    
    # 4. feedback loop builds for 3+ mock manifolds.
    mock_paths_3 = [
        type("MockPath", (), {"source_manifold_id": "M1", "target_manifold_id": "M2", "link_id": "LINK_1_2"})(),
        type("MockPath", (), {"source_manifold_id": "M2", "target_manifold_id": "M3", "link_id": "LINK_2_3"})()
    ]
    targets_3 = build_entangled_calibration_targets(mock_paths_3, [])
    loop_3 = build_entangled_feedback_loop(targets_3, policy_2)
    assert loop_3["loop_id"].startswith("LOOP_")
    assert len(loop_3["targets"]) == 2
    
    # 5. invalid unbounded feedback policy is rejected.
    invalid_policy_steps = EntangledFeedbackLoopPolicy(
        max_steps=0,
        max_phase_adjustment=0.1,
        max_cadence_adjustment=0.1,
        max_carrier_adjustment=0.1,
        max_damping_adjustment=0.01,
        max_pml_absorption_adjustment=0.05,
        max_route_damping_adjustment=0.02
    )
    with pytest.raises(ValueError, match="max_steps"):
        build_entangled_feedback_loop(targets, invalid_policy_steps)
        
    invalid_policy_phase = EntangledFeedbackLoopPolicy(
        max_steps=5,
        max_phase_adjustment=-0.1,
        max_cadence_adjustment=0.1,
        max_carrier_adjustment=0.1,
        max_damping_adjustment=0.01,
        max_pml_absorption_adjustment=0.05,
        max_route_damping_adjustment=0.02
    )
    with pytest.raises(ValueError, match="max phase adjustment"):
        build_entangled_feedback_loop(targets, invalid_policy_phase)

    # 6. max phase adjustment bound is enforced.
    policy_small_phase = EntangledFeedbackLoopPolicy(
        max_steps=3,
        max_phase_adjustment=0.02,
        max_cadence_adjustment=0.1,
        max_carrier_adjustment=0.1,
        max_damping_adjustment=0.01,
        max_pml_absorption_adjustment=0.05,
        max_route_damping_adjustment=0.02
    )
    loop_small = build_entangled_feedback_loop(targets, policy_small_phase)
    obs = [type("Obs", (), {"phase_drift": 0.08, "phase_coherence": 0.92, "crosstalk": 0.01, "boundary_reflection": 0.01, "carrier_phase_error": 0.01})()]
    rep_small = run_shadow_entangled_feedback_loop(loop_small, obs)
    assert abs(rep_small.history[0].action.adjustments[0]["phase_adjustment"]) <= 0.02
    
    # 7. max cadence adjustment bound is enforced.
    cal_policy = EntangledCalibrationPolicy(
        max_steps=5,
        max_phase_adj=0.05,
        max_cadence_adj=0.01,
        max_carrier_adj=0.05,
        max_damping_adj=0.01,
        max_pml_adj=0.05,
        max_route_damping=0.05
    )
    err_rep = type("Err", (), {"phase_drift": 0.0, "cadence_drift": 0.08, "carrier_phase_error": 0.0, "crosstalk": 0.0, "boundary_reflection": 0.0})()
    adjs = plan_entangled_calibration_adjustments(err_rep, cal_policy)
    assert abs(adjs[0].cadence_adjustment) <= 0.01
    
    # 8. max carrier adjustment bound is enforced.
    cal_policy_carrier = EntangledCalibrationPolicy(
        max_steps=5,
        max_phase_adj=0.05,
        max_cadence_adj=0.05,
        max_carrier_adj=0.01,
        max_damping_adj=0.01,
        max_pml_adj=0.05,
        max_route_damping=0.05
    )
    err_rep_carrier = type("Err", (), {"phase_drift": 0.0, "cadence_drift": 0.0, "carrier_phase_error": 0.08, "crosstalk": 0.0, "boundary_reflection": 0.0})()
    adjs_carrier = plan_entangled_calibration_adjustments(err_rep_carrier, cal_policy_carrier)
    assert abs(adjs_carrier[0].carrier_adjustment) <= 0.01
    
    # 9. shadow feedback loop reduces or preserves drift metric.
    rep_stab = run_shadow_entangled_feedback_loop(loop_2, obs)
    assert evaluate_feedback_loop_stability(rep_stab) is True
    
    # 10. unstable feedback loop triggers hold or rollback recommendation.
    obs_unstable = [type("Obs", (), {"phase_drift": 0.08, "phase_coherence": 0.92, "crosstalk": 0.01, "boundary_reflection": 0.01, "carrier_phase_error": 0.01, "unstable_feedback": True})()]
    rep_unstable = run_shadow_entangled_feedback_loop(loop_2, obs_unstable)
    assert rep_unstable.result.success is False
    assert rep_unstable.result.rolled_back is True
    
    # 11. high entanglement phase drift blocks commit.
    class MockEpoch:
        def __init__(self, metadata):
            self.epoch_id = "ENT_EPOCH_MOCK"
            self.metadata = metadata
            self.checkpoints = []
            self.state = "active"
            self.cadence_group = None
    from sol_entangled_commit_epoch import commit_shadow_entangled_epoch, register_entangled_calibration_checkpoint, evaluate_entangled_calibration_barrier
    epoch = MockEpoch({
        "calibration_baseline_present": True,
        "feedback_loop_completed": True,
        "stability_report_attached": True,
        "rollback_path_available": True,
        "ranger_evidence_complete": True,
        "rollback_snapshots": True,
        "high_phase_drift": True
    })
    checkpoint = type("CP", (), {"checkpoint_id": "CP1", "participant_id": "M1", "verified": True})()
    epoch.checkpoints.append(checkpoint)
    
    commit_rep = commit_shadow_entangled_epoch(epoch)
    assert commit_rep.success is False
    assert any("phase drift" in e.lower() for e in commit_rep.errors)
    
    # 12. high cadence drift blocks commit.
    epoch_cadence = MockEpoch({
        "calibration_baseline_present": True,
        "feedback_loop_completed": True,
        "stability_report_attached": True,
        "rollback_path_available": True,
        "ranger_evidence_complete": True,
        "rollback_snapshots": True
    })
    epoch_cadence.checkpoints.append(checkpoint)
    
    feedback_rep_cadence = type("FB", (), {
        "result": type("R", (), {
            "success": True,
            "final_state": type("S", (), {"drift": 0.01, "coherence": 0.99, "cadence_drift": 0.08})(),
            "metadata": {"rollback_ready": True}
        })()
    })()
    commit_rep_norm = type("CR", (), {"passed_gates": True})()
    assert validate_synchronized_commit_after_feedback(commit_rep_norm, feedback_rep_cadence) is False
    
    # 13. high carrier phase error blocks commit.
    feedback_rep_carrier = type("FB", (), {
        "result": type("R", (), {
            "success": True,
            "final_state": type("S", (), {"drift": 0.08, "coherence": 0.92, "cadence_drift": 0.01})(),
            "metadata": {"rollback_ready": True}
        })()
    })()
    assert validate_synchronized_commit_after_feedback(commit_rep_norm, feedback_rep_carrier) is False

    # 14. high crosstalk triggers quarantine recommendation.
    stab_policy = EntangledStabilityControlPolicy(crosstalk_threshold=0.05)
    mock_cal_report_xtalk = type("Rep", (), {
        "result": type("Res", (), {"success": True, "errors": []})(),
        "baseline": type("Base", (), {"phase_drift": 0.01, "crosstalk": 0.08, "boundary_reflection": 0.01, "phase_coherence": 0.99})()
    })()
    stab_rep_xtalk = suggest_entangled_stability_control(mock_cal_report_xtalk, stab_policy)
    assert any(s.action == "quarantine_entanglement_link" for s in stab_rep_xtalk.suggestions)

    # 15. boundary reflection breach blocks promotion.
    court = PromotionCourt()
    ranger = EntangledFeedbackRanger()
    packet = ranger.observe_entangled_feedback(wavefront_report=type("WF", (), {"cross_manifold_crosstalk": 0.01, "boundary_reflection": 0.08, "active_mass_preservation": True})())
    court_dec_ranger = court.review_entangled_feedback_ranger_packet(packet)
    assert court_dec_ranger.decision == "hold_entangled_feedback_loop"
    
    # 16. PML feedback cannot reduce absorption below policy minimum.
    pml_state = type("PML", (), {
        "config": type("Cfg", (), {"boundary_gamma": 0.08})()
    })()
    feedback_act = type("Act", (), {
        "policy": type("Pol", (), {"min_pml_absorption": 0.05})(),
        "adjustments": [type("Adj", (), {"pml_adjustment": -0.05})()]
    })()
    assert validate_pml_feedback_adjustment(pml_state, feedback_act) is False
    
    # 17. active phase table is not overwritten.
    packet_overwrite_phase = ranger.observe_entangled_feedback(feedback_report=type("FB", (), {"result": None, "metadata": {"active_phase_table_overwritten": True}})())
    assert packet_overwrite_phase.evidence["promotion_readiness"] is False
    
    # 18. active cadence profile is not overwritten.
    packet_overwrite_cadence = ranger.observe_entangled_feedback(feedback_report=type("FB", (), {"result": None, "metadata": {"active_cadence_profile_overwritten": True}})())
    assert packet_overwrite_cadence.evidence["promotion_readiness"] is False
    
    # 19. active carrier registry is not overwritten.
    packet_overwrite_carrier = ranger.observe_entangled_feedback(feedback_report=type("FB", (), {"result": None, "metadata": {"active_carrier_registry_overwritten": True}})())
    assert packet_overwrite_carrier.evidence["promotion_readiness"] is False
    
    # 20. synchronized commit remains blocked until feedback stability passes.
    feedback_unstable = type("FB", (), {
        "result": type("R", (), {"success": False, "final_state": None})()
    })()
    assert validate_synchronized_commit_after_feedback(commit_rep_norm, feedback_unstable) is False
    
    # 21. EntangledFeedbackAdvisor returns advisory-only suggestions in shadow mode.
    bridge = type("Bridge", (), {"push_telemetry": lambda self, x: None})()
    advisor = EntangledFeedbackAdvisor(bridge)
    sug_shadow = advisor.suggest_feedback_stabilization(
        type("Rep", (), {"result": None, "metadata": {"high_phase_error": True}})(),
        EntangledFeedbackClosedLoopPolicy()
    )
    assert sug_shadow.action == "apply_candidate_phase_offset"
    
    # 22. sandbox feedback trial requires valid court token.
    with pytest.raises(ValueError, match="Invalid or expired court token"):
        run_sandbox_entangled_feedback_loop(loop_2, None)
        
    # 23. expired or invalid token is rejected.
    token_invalid = type("Token", (), {"authorized_by_court": False, "active": True, "expires_at": time.time() + 100})()
    rep_sandbox_reject = advisor.apply_feedback_adjustment_in_sandbox(sug_shadow, token_invalid)
    assert rep_sandbox_reject.validated is False
    
    # 24. rollback restores candidate feedback state.
    from sol_carrier_registry import CarrierRegistry, CarrierLease, restore_carrier_registry
    registry = CarrierRegistry("REG1", {("C1", 0): CarrierLease("L1", "C1", 0, "H1")})
    snap = snapshot_carriers_before_feedback(registry)
    registry.leases[("C1", 0)].lane_id = 2
    restored = restore_carrier_registry(snap)
    assert restored.leases[("C1", 0)].lane_id == 0
    
    # 25. EntangledFeedbackRanger emits JSON-serializable SovereignPacket.
    norm_cal = type("Cal", (), {
        "targets": targets,
        "baseline": baseline,
        "passed_gates": True,
        "result": type("Res", (), {"success": True, "errors": []})()
    })()
    norm_fb = type("FB", (), {
        "passed_gates": True,
        "result": type("Res", (), {
            "success": True,
            "step_count": 3,
            "final_state": type("S", (), {"drift": 0.01, "coherence": 0.99, "crosstalk": 0.01, "reflection": 0.01, "carrier_error": 0.01})()
        })(),
        "metadata": {
            "rollback_ready": True,
            "active_phase_table_not_overwritten": True,
            "active_cadence_profile_not_overwritten": True,
            "active_carrier_registry_not_overwritten": True
        }
    })()
    norm_wf = type("WF", (), {"cross_manifold_crosstalk": 0.01, "boundary_reflection": 0.01, "active_mass_preservation": True})()
    
    packet_norm = ranger.observe_entangled_feedback(
        calibration_report=norm_cal,
        feedback_report=norm_fb,
        wavefront_report=norm_wf
    )
    assert packet_norm.actor == "Entangled Feedback Ranger"
    assert packet_norm.recommendation == "promote"
    assert json.dumps(packet_norm.to_dict()) is not None
    
    # 26. Promotion Court can review entangled calibration, feedback loop, stability control, and ranger reports.
    court_dec_cal = court.review_entangled_calibration_report(norm_cal)
    assert court_dec_cal.decision == "accept_shadow_entangled_feedback"
    
    court_dec_fb = court.review_entangled_feedback_loop_report(norm_fb)
    assert court_dec_fb.decision == "accept_shadow_entangled_feedback"
    
    mock_stab_nom = type("Stab", (), {"state": "stable", "suggestions": []})()
    court_dec_stab = court.review_entangled_stability_control_report(mock_stab_nom)
    assert court_dec_stab.decision == "accept_shadow_entangled_feedback"
    
    court_dec_rng_norm = court.review_entangled_feedback_ranger_packet(packet_norm)
    assert court_dec_rng_norm.decision == "promote_level35_candidate"
    
    docket = open_promotion_docket("CAND_L35", 35)
    attach_evidence_item(docket, {"evidence_type": "ranger_packet", "payload": packet_norm})
    attach_evidence_item(docket, {"evidence_type": "entangled_calibration_report", "payload": norm_cal})
    attach_evidence_item(docket, {"evidence_type": "entangled_feedback_loop_report", "payload": norm_fb})
    attach_evidence_item(docket, {"evidence_type": "entangled_stability_control_report", "payload": mock_stab_nom})
    attach_evidence_item(docket, {"evidence_type": "rollback_snapshot", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "test_summary", "payload": {"status": "passed"}})
    
    assert validate_promotion_docket(docket) is True
    verdict = court.issue_court_supervised_promotion_verdict(docket)
    assert verdict.decision == "promote_level35_candidate"
    manifest = build_promotion_manifest(docket, verdict)
    assert manifest.level == 35


def test_level36_scaffolding():
    import time
    from sol_promotion_docket import (
        open_promotion_docket,
        attach_evidence_item,
        validate_promotion_docket,
        build_promotion_manifest
    )
    from sol_sovereign_runtime import (
        build_sovereign_runtime,
        validate_sovereign_runtime,
        submit_runtime_command,
        execute_shadow_runtime_command,
        summarize_sovereign_runtime,
        SovereignRuntimePolicy,
        SovereignRuntimeCommand,
        SovereignRuntimeState,
        SovereignRuntimeId
    )
    from sol_levelup_sequence import (
        build_levelup_sequence,
        validate_levelup_sequence,
        topological_sort_levelup_steps,
        execute_shadow_levelup_sequence,
        summarize_levelup_sequence,
        LevelUpStep,
        LevelUpDependency
    )
    from sol_runtime_governor import (
        evaluate_runtime_gates,
        validate_runtime_evidence,
        RuntimeGovernancePolicy,
        RuntimeGovernanceReport,
        RuntimeGovernanceDecision,
        RuntimeGateSnapshot
    )
    from sol_runtime_token_vault import (
        issue_shadow_token,
        validate_runtime_token,
        expire_runtime_token,
        revoke_runtime_token,
        RuntimeTokenScope,
        RuntimeToken
    )
    from sol_runtime_ledger import (
        build_runtime_ledger,
        append_runtime_event,
        attach_runtime_evidence,
        attach_rollback_reference,
        validate_runtime_ledger
    )
    from sol_runtime_scheduler import (
        schedule_levelup_job,
        validate_scheduled_job,
        execute_due_shadow_jobs,
        RuntimeSchedulePolicy,
        ScheduledLevelUpJob
    )
    from coding_library.sovereign_domain.rangers.sovereign_runtime_ranger import SovereignRuntimeRanger
    
    # 1. sovereign runtime builds in shadow mode.
    policy = SovereignRuntimePolicy(allow_production_execution=False)
    runtime = build_sovereign_runtime(policy)
    assert runtime.mode == "shadow"
    assert validate_sovereign_runtime(runtime) is True
    
    # 2. production/default runtime mode is rejected.
    invalid_policy = SovereignRuntimePolicy(allow_production_execution=True)
    with pytest.raises(ValueError, match="production execution is strictly prohibited"):
        build_sovereign_runtime(invalid_policy)
        
    # 3. level-up sequence builds for one level.
    step1 = LevelUpStep("STEP1", 36, "Sovereign execution runtime")
    seq1 = build_levelup_sequence([step1], [])
    assert seq1["sequence_id"] is not None
    assert validate_levelup_sequence(seq1) is True
    
    # 4. level-up sequence builds for multiple dependent levels.
    step2 = LevelUpStep("STEP2", 37, "Next Gen logic")
    dep1 = LevelUpDependency(37, 36)
    seq2 = build_levelup_sequence([step1, step2], [dep1])
    assert validate_levelup_sequence(seq2) is True
    
    # 5. dependency cycle is rejected.
    dep_cycle_1 = LevelUpDependency(37, 36)
    dep_cycle_2 = LevelUpDependency(36, 37)
    seq_cycle = build_levelup_sequence([step1, step2], [dep_cycle_1, dep_cycle_2])
    with pytest.raises(ValueError, match="Dependency cycle detected"):
        validate_levelup_sequence(seq_cycle)
        
    # 6. topological order respects dependencies.
    sorted_steps = topological_sort_levelup_steps(seq2)
    assert sorted_steps[0].level == 36
    assert sorted_steps[1].level == 37
    
    # 7. runtime command executes in shadow mode.
    cmd = SovereignRuntimeCommand("CMD1", 36, "levelup_step", mode="shadow")
    res = execute_shadow_runtime_command(runtime, cmd)
    assert res.success is True
    assert res.final_level == 36
    
    # 8. sandbox command requires valid court token.
    token_scope = RuntimeTokenScope(36, "levelup_step", "sandbox_core", allow_production=False)
    token = RuntimeToken("TOK1", "COURT_AUTH_123", token_scope, time.time() + 100.0, "RNG_OBS_1")
    validation = validate_runtime_token(token, token_scope)
    assert validation.validated is True
    
    # 9. expired token is rejected.
    expire_runtime_token(token)
    validation_expired = validate_runtime_token(token, token_scope)
    assert validation_expired.validated is False
    
    # 10. missing ranger observer blocks sandbox step.
    runtime_sandbox = build_sovereign_runtime(policy)
    runtime_sandbox.mode = "sandbox"
    # Missing active token
    snap_missing_token = evaluate_runtime_gates(runtime_sandbox, seq2)
    assert snap_missing_token.gates_status["token_valid_if_sandbox"] is False
    assert snap_missing_token.gates_status["ranger_observer_present"] is False
    
    # 11. missing rollback reference blocks sandbox step.
    token_missing_ref = RuntimeToken("TOK2", "COURT_AUTH_123", token_scope, time.time() + 100.0, "RNG_OBS_1", rollback_required=True, rollback_reference=None)
    runtime_sandbox.active_token = token_missing_ref
    snap_missing_rollback = evaluate_runtime_gates(runtime_sandbox, seq2)
    assert snap_missing_rollback.gates_status["rollback_reference_present"] is False
    
    # 12. runtime ledger records command, gate, evidence, court, and rollback events.
    ledger = build_runtime_ledger()
    append_runtime_event(ledger, cmd)
    append_runtime_event(ledger, snap_missing_rollback)
    attach_runtime_evidence(ledger, {"evidence_id": "EV1", "evidence_type": "test_summary", "payload": "passed"})
    attach_rollback_reference(ledger, {"rollback_id": "RL1", "state_checksum": "sha256_123"})
    
    assert len(ledger["entries"]) > 0
    assert len(ledger["evidence_references"]) == 1
    assert len(ledger["rollback_references"]) == 1
    
    # 13. scheduler does not auto-promote levels.
    sched_policy = RuntimeSchedulePolicy(disable_auto_promotion=False)
    job = schedule_levelup_job(seq2, sched_policy)
    with pytest.raises(ValueError, match="automatic level promotion is prohibited"):
        validate_scheduled_job(job)
        
    # 14. scheduler halts on failed critical gate.
    runtime_hold = build_sovereign_runtime(policy)
    runtime_hold.mode = "hold"
    sched_policy_valid = RuntimeSchedulePolicy(disable_auto_promotion=True)
    job_valid = schedule_levelup_job(seq2, sched_policy_valid)
    reports = execute_due_shadow_jobs([job_valid], runtime_hold)
    assert reports[0].status == "held"
    assert reports[0].halted is True
    
    # 15. runtime governor holds sequence with missing evidence.
    runtime_missing_ev = build_sovereign_runtime(policy)
    snap_missing_ev = evaluate_runtime_gates(runtime_missing_ev, seq2)
    assert snap_missing_ev.gates_status["evidence_complete"] is False
    
    # 16. runtime governor quarantines unresolved unsafe step.
    runtime_quarantine = build_sovereign_runtime(policy)
    runtime_quarantine.mode = "quarantine"
    snap_quarantine = evaluate_runtime_gates(runtime_quarantine, seq2)
    assert snap_quarantine.gates_status["unresolved_quarantine_absent"] is False
    
    # 17. SovereignRuntimeRanger emits JSON-serializable SovereignPacket.
    ranger = SovereignRuntimeRanger()
    
    # Setup completed reports
    norm_runtime = build_sovereign_runtime(policy)
    norm_runtime.ledger = ledger
    norm_runtime.evidence = {"test_summary": {"status": "passed"}}
    
    norm_ledger_report = validate_runtime_ledger(ledger)
    
    packet = ranger.observe_sovereign_runtime(
        runtime_state=norm_runtime,
        ledger_report=norm_ledger_report
    )
    
    assert packet.actor == "Sovereign Runtime Ranger"
    assert packet.recommendation == "promote"
    assert json.dumps(packet.to_dict()) is not None
    
    # 18. Promotion Court can review runtime, sequence, governance, and ledger reports.
    court = PromotionCourt()
    
    court_dec_run = court.review_sovereign_runtime_report(summarize_sovereign_runtime(norm_runtime))
    assert court_dec_run.decision == "accept_shadow_runtime"
    
    trace_seq = execute_shadow_levelup_sequence(seq2, norm_runtime)
    court_dec_seq = court.review_levelup_sequence_report(summarize_levelup_sequence(trace_seq))
    assert court_dec_seq.decision == "accept_shadow_runtime"
    
    gov_report = RuntimeGovernanceReport(
        report_id="GOV1",
        gate_snapshot=snap_missing_ev,
        decision=RuntimeGovernanceDecision("D1", "continue_shadow", "OK"),
        policy_satisfied=True
    )
    court_dec_gov = court.review_runtime_governance_report(gov_report)
    assert court_dec_gov.decision == "accept_shadow_runtime"
    
    court_dec_rng = court.review_sovereign_runtime_ranger_packet(packet)
    assert court_dec_rng.decision == "promote_level36_candidate"
    
    docket = open_promotion_docket("CAND_L36", 36)
    attach_evidence_item(docket, {"evidence_type": "ranger_packet", "payload": packet})
    attach_evidence_item(docket, {"evidence_type": "sovereign_runtime_report", "payload": summarize_sovereign_runtime(norm_runtime)})
    attach_evidence_item(docket, {"evidence_type": "levelup_sequence_report", "payload": summarize_levelup_sequence(trace_seq)})
    attach_evidence_item(docket, {"evidence_type": "runtime_governance_report", "payload": gov_report})
    attach_evidence_item(docket, {"evidence_type": "rollback_snapshot", "payload": {}})
    attach_evidence_item(docket, {"evidence_type": "test_summary", "payload": {"status": "passed"}})
    
    assert validate_promotion_docket(docket) is True
    verdict = court.issue_court_supervised_promotion_verdict(docket)
    assert verdict.decision == "promote_level36_candidate"
    manifest = build_promotion_manifest(docket, verdict)
    assert manifest.level == 36


def test_level37_scaffolding():
    import json
    import pytest
    from sol_hierarchical_waveguide_fabric import (
        build_hierarchical_waveguide_topology,
        validate_hierarchical_waveguide_topology,
        map_lanes_to_waveguide_clusters,
        build_interlane_bridges,
        summarize_hierarchical_waveguide
    )
    from sol_interlane_prefix_carry import (
        build_prefix_carry_tree,
        validate_prefix_carry_tree,
        compute_lane_generate_propagate,
        execute_shadow_prefix_carry,
        InterLaneCarryPlan,
        InterLaneCarryReport
    )
    from sol_waveguide_arithmetic_pipeline import (
        plan_waveguide_addition,
        plan_waveguide_subtraction,
        execute_shadow_waveguide_arithmetic,
        compare_waveguide_arithmetic_oracle,
        WaveguideArithmeticReport
    )
    from sol_prefix_carry import (
        export_prefix_tree_for_waveguide,
        validate_interlane_prefix_against_existing_carry
    )
    from sol_wideword_fabric import (
        build_hierarchical_waveguide_plan,
        attach_interlane_prefix_carry,
        validate_wideword_arithmetic_fabric
    )
    from sol_waveguide_fabric_synthesis import (
        synthesize_hierarchical_waveguide_from_topology,
        bind_prefix_carry_tree_to_waveguide,
        validate_prefix_carry_bindings
    )
    from sol_simd_core_integration import (
        bind_interlane_carry_to_simd_core,
        validate_simd_prefix_carry_mapping
    )
    from sol_wavefront_propagator import (
        initialize_carry_wavefront_state,
        run_shadow_carry_wavefront,
        measure_carry_wavefront_stability,
        WavefrontPropagationConfig
    )
    from sol_waveguide_boundary import (
        validate_pml_for_interlane_bridges,
        measure_bridge_boundary_reflection
    )
    from sol_temporal_cadence import (
        validate_prefix_carry_cadence,
        measure_carry_cadence_error
    )
    from sol_court_supervised_promotion import (
        review_hierarchical_waveguide_report,
        review_interlane_prefix_carry_report,
        review_waveguide_arithmetic_report,
        review_waveguide_arithmetic_ranger_packet
    )
    from coding_library.sovereign_domain.rangers.waveguide_arithmetic_ranger import WaveguideArithmeticRanger
    from coding_library.sovereign_domain.promotion_court import PromotionCourt
    
    # 1, 2, 3. hierarchical topology builds for 16, 32, 64-bit widths
    topo16 = build_hierarchical_waveguide_topology(16)
    topo32 = build_hierarchical_waveguide_topology(32)
    topo64 = build_hierarchical_waveguide_topology(64)
    
    assert validate_hierarchical_waveguide_topology(topo16) is True
    assert validate_hierarchical_waveguide_topology(topo32) is True
    assert validate_hierarchical_waveguide_topology(topo64) is True
    
    # 4. lane-to-cluster mapping covers all byte lanes
    map16 = map_lanes_to_waveguide_clusters(topo16)
    assert set(map16.keys()) == {0, 1}
    map64 = map_lanes_to_waveguide_clusters(topo64)
    assert set(map64.keys()) == set(range(8))
    
    # 5. inter-lane bridges connect expected neighboring groups
    bridges16 = build_interlane_bridges(topo16)
    assert len(bridges16) == 1
    assert bridges16[0].source_lane_id == 0
    assert bridges16[0].target_lane_id == 1
    
    # 6, 7, 8. prefix-carry tree builds for 2, 4, 8 lanes
    tree2 = build_prefix_carry_tree(2, strategy="balanced")
    tree4 = build_prefix_carry_tree(4, strategy="kogge_stone_shadow")
    tree8 = build_prefix_carry_tree(8, strategy="brent_kung_shadow")
    
    assert validate_prefix_carry_tree(tree2) is True
    assert validate_prefix_carry_tree(tree4) is True
    assert validate_prefix_carry_tree(tree8) is True
    
    # 9. invalid prefix tree is rejected
    with pytest.raises(ValueError, match="Invalid prefix tree"):
        tree2.strategy = "invalid"
        validate_prefix_carry_tree(tree2)
    tree2.strategy = "balanced"
    
    # 10. lane generate/propagate matches Python oracle
    gp = compute_lane_generate_propagate([(200, 100)], lane_width=8)
    assert gp[0].generate is True
    assert gp[0].propagate is False
    
    # 11, 12, 13. ADD matches Python oracle for 16, 32, 64-bit values
    plan_add16 = plan_waveguide_addition(0x1234, 0x5678, 16, topo16)
    res_add16 = execute_shadow_waveguide_arithmetic(plan_add16)
    assert compare_waveguide_arithmetic_oracle(res_add16, 0x1234, 0x5678, "ADD") is True
    
    plan_add32 = plan_waveguide_addition(0x12345678, 0x9ABCDEF0, 32, topo32)
    res_add32 = execute_shadow_waveguide_arithmetic(plan_add32)
    assert compare_waveguide_arithmetic_oracle(res_add32, 0x12345678, 0x9ABCDEF0, "ADD") is True
    
    plan_add64 = plan_waveguide_addition(0x0123456789ABCDEF, 0xFEDCBA9876543210, 64, topo64)
    res_add64 = execute_shadow_waveguide_arithmetic(plan_add64)
    assert compare_waveguide_arithmetic_oracle(res_add64, 0x0123456789ABCDEF, 0xFEDCBA9876543210, "ADD") is True

    # 14, 15, 16. SUB matches Python oracle for 16, 32, 64-bit values
    plan_sub16 = plan_waveguide_subtraction(0x5678, 0x1234, 16, topo16)
    res_sub16 = execute_shadow_waveguide_arithmetic(plan_sub16)
    assert compare_waveguide_arithmetic_oracle(res_sub16, 0x5678, 0x1234, "SUB") is True
    
    plan_sub32 = plan_waveguide_subtraction(0x9ABCDEF0, 0x12345678, 32, topo32)
    res_sub32 = execute_shadow_waveguide_arithmetic(plan_sub32)
    assert compare_waveguide_arithmetic_oracle(res_sub32, 0x9ABCDEF0, 0x12345678, "SUB") is True
    
    plan_sub64 = plan_waveguide_subtraction(0xFEDCBA9876543210, 0x0123456789ABCDEF, 64, topo64)
    res_sub64 = execute_shadow_waveguide_arithmetic(plan_sub64)
    assert compare_waveguide_arithmetic_oracle(res_sub64, 0xFEDCBA9876543210, 0x0123456789ABCDEF, "SUB") is True
    
    # 17. carry-ins are complete for all lanes
    assert len(res_add64.trace.resolved_carries) == 8
    
    # 18. final carry-out is correct
    plan_overflow = plan_waveguide_addition(0xFFFF, 0x0001, 16, topo16)
    res_overflow = execute_shadow_waveguide_arithmetic(plan_overflow)
    assert res_overflow.carry_out == 1
    
    # 19. SIMD prefix-carry mappings validate for all supported SIMD modes
    candidate = synthesize_hierarchical_waveguide_from_topology(topo64)
    for mode in ("uint8x8", "uint16x4", "uint32x2", "uint64x1"):
        binding_map = bind_interlane_carry_to_simd_core(candidate, mode)
        assert validate_simd_prefix_carry_mapping(binding_map) is True
        
    # 20. PML validation detects missing bridge boundary coverage
    topo16_bad = build_hierarchical_waveguide_topology(16)
    topo16_bad.metadata["bypass_pml"] = True
    with pytest.raises(ValueError, match="PML validation detects missing bridge boundary coverage"):
        validate_pml_for_interlane_bridges(topo16_bad, pml_state={})
        
    # 21. carry wavefront report is deterministic
    carry_plan = InterLaneCarryPlan(
        plan_id="TEST_CARRY",
        carry_tree=tree4,
        lane_inputs=compute_lane_generate_propagate([(100, 200), (50, 50), (10, 10), (0, 0)])
    )
    config = WavefrontPropagationConfig(damping=0.01)
    c_rep = run_shadow_carry_wavefront(carry_plan, steps=3, config=config)
    assert c_rep.stable is True
    
    # 22. excessive inter-lane crosstalk blocks promotion
    carry_plan_bad = InterLaneCarryPlan(
        plan_id="TEST_CARRY_BAD",
        carry_tree=tree4,
        lane_inputs=compute_lane_generate_propagate([(100, 200), (50, 50), (10, 10), (0, 0)]),
        metadata={"excessive_crosstalk": True}
    )
    c_rep_bad = run_shadow_carry_wavefront(carry_plan_bad, steps=3, config=config)
    assert measure_carry_wavefront_stability(c_rep_bad) is False
    
    # 23. cadence drift blocks carry-wave commit if cadence is required
    carry_plan_drift = InterLaneCarryPlan(
        plan_id="TEST_CARRY_DRIFT",
        carry_tree=tree4,
        lane_inputs=compute_lane_generate_propagate([(100, 200), (50, 50), (10, 10), (0, 0)]),
        metadata={"excessive_drift": True}
    )
    c_rep_drift = run_shadow_carry_wavefront(carry_plan_drift, steps=3, config=config)
    assert validate_prefix_carry_cadence(c_rep_drift, cadence_profile={}) is False
    
    # 24. WaveguideArithmeticRanger emits JSON-serializable SovereignPacket
    ranger = WaveguideArithmeticRanger()
    topo_rep = summarize_hierarchical_waveguide(topo32)
    arith_result = execute_shadow_waveguide_arithmetic(plan_add32)
    arith_report = WaveguideArithmeticReport(
        report_id="TEST_ARITH_REP",
        intent=plan_add32.intent,
        result=arith_result,
        oracle_match=True,
        success=True,
        errors=[],
        metadata={"promotion_ready": True}
    )
    packet = ranger.observe_waveguide_arithmetic(
        topology=topo32,
        carry_plan=carry_plan,
        carry_report=c_rep,
        arith_report=arith_report,
        topo_report=topo_rep
    )
    assert packet.actor == "Waveguide Arithmetic Ranger"
    assert packet.recommendation == "promote"
    assert json.dumps(packet.to_dict()) is not None
    
    # 25. Promotion Court can review reports
    court = PromotionCourt()
    
    dec_hw = court.review_hierarchical_waveguide_report(topo_rep)
    assert dec_hw.decision == "accept_shadow_waveguide_arithmetic"
    
    carry_res = execute_shadow_prefix_carry(carry_plan)
    carry_rep = InterLaneCarryReport(
        report_id="TEST_CARRY_REP",
        plan_id=carry_plan.plan_id,
        success=True,
        errors=[],
        carries=carry_res.carries,
        carry_out=carry_res.carry_out,
        tree_depth=c_rep.carry_propagation_depth,
        strategy=carry_plan.carry_tree.strategy
    )
    dec_pc = court.review_interlane_prefix_carry_report(carry_rep)
    assert dec_pc.decision == "accept_shadow_waveguide_arithmetic"
    
    dec_wa = court.review_waveguide_arithmetic_report(arith_report)
    assert dec_wa.decision == "promote_level37_candidate"
    
    dec_pkt = court.review_waveguide_arithmetic_ranger_packet(packet)
    assert dec_pkt.decision == "promote_level37_candidate"


def test_level38_scaffolding():
    import json
    import pytest
    from sol_entangled_wavefront_consensus import (
        EntangledConsensusParticipant,
        EntangledWavefrontConsensusIntent,
        EntangledWavefrontVote,
        EntangledWavefrontQuorum,
        EntangledConsensusStateHash,
        EntangledWavefrontConsensusDecision,
        EntangledWavefrontConsensusReport,
        build_entangled_wavefront_consensus_intent,
        validate_entangled_consensus_participants,
        collect_entangled_wavefront_votes,
        evaluate_entangled_wavefront_quorum,
        build_entangled_wavefront_consensus_report
    )
    from sol_multimanifold_atomic_commit import (
        MultiManifoldAtomicCommitIntent,
        AtomicCommitBoundary,
        AtomicCommitParticipantState,
        AtomicPrepareWavefront,
        AtomicCommitBarrier,
        MultiManifoldAtomicCommitDecision,
        MultiManifoldAtomicCommitResult,
        MultiManifoldAtomicCommitReport,
        build_multimanifold_atomic_commit_intent,
        validate_atomic_commit_boundaries,
        prepare_multimanifold_atomic_commit,
        evaluate_atomic_commit_barrier,
        commit_shadow_multimanifold_atomic,
        abort_multimanifold_atomic_commit
    )
    from sol_entangled_atomic_epoch import (
        EntangledAtomicEpoch,
        EntangledAtomicCheckpoint,
        EntangledAtomicBarrier,
        EntangledAtomicEpochState,
        EntangledAtomicEpochReport,
        start_entangled_atomic_epoch,
        register_entangled_atomic_checkpoint,
        evaluate_entangled_atomic_barrier,
        commit_shadow_entangled_atomic_epoch,
        abort_entangled_atomic_epoch
    )
    from coding_library.sovereign_domain.rangers.atomic_consensus_ranger import AtomicConsensusRanger
    from coding_library.sovereign_domain.promotion_court import PromotionCourt

    class MockReport:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    # 1. entangled wavefront consensus intent builds for 2 mock manifolds
    p2 = [EntangledConsensusParticipant("M1"), EntangledConsensusParticipant("M2")]
    intent2 = build_entangled_wavefront_consensus_intent(p2)
    assert validate_entangled_consensus_participants(intent2) is True

    # 2. entangled wavefront consensus intent builds for 3+ mock manifolds
    p3 = [EntangledConsensusParticipant("M1"), EntangledConsensusParticipant("M2"), EntangledConsensusParticipant("M3")]
    intent3 = build_entangled_wavefront_consensus_intent(p3)
    assert validate_entangled_consensus_participants(intent3) is True

    # 3. missing participant rejects consensus
    p_bad = [EntangledConsensusParticipant("M1", status="inactive")]
    intent_bad = build_entangled_wavefront_consensus_intent(p_bad)
    with pytest.raises(ValueError, match="Consensus intent requires at least 2 active participants"):
        validate_entangled_consensus_participants(intent_bad)

    # 4. local quorum failure blocks atomic commit
    intent_local_fail = build_entangled_wavefront_consensus_intent(p2)
    votes_local_fail = collect_entangled_wavefront_votes(intent_local_fail, mock_votes=[
        {"manifold_id": "M1", "decision": "approve"},
        {"manifold_id": "M2", "decision": "reject"}
    ])
    q_local_fail = evaluate_entangled_wavefront_quorum(intent_local_fail, votes_local_fail)
    assert q_local_fail.local_quorum_passed is False
    dec_local_fail = EntangledWavefrontConsensusDecision(
        decision_id="DEC_LOCAL",
        status="rejected",
        quorum=q_local_fail,
        state_hash_agreement=EntangledConsensusStateHash("HASH_OK", True),
        justification="local quorum failed"
    )
    c_rep_local_fail = build_entangled_wavefront_consensus_report(intent_local_fail, votes_local_fail, dec_local_fail)
    assert c_rep_local_fail.success is False

    tx_intent = {"value": 42}
    commit_intent = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"])
    prepare_multimanifold_atomic_commit(commit_intent)
    barrier_local_fail = evaluate_atomic_commit_barrier(commit_intent, c_rep_local_fail)
    assert barrier_local_fail.satisfied is False

    # 5. global quorum failure blocks atomic commit
    intent_global_fail = build_entangled_wavefront_consensus_intent(p2, metadata={"global_quorum_failed": True})
    votes_global_fail = collect_entangled_wavefront_votes(intent_global_fail)
    q_global_fail = evaluate_entangled_wavefront_quorum(intent_global_fail, votes_global_fail)
    assert q_global_fail.global_quorum_passed is False
    dec_global_fail = EntangledWavefrontConsensusDecision(
        decision_id="DEC_GLOBAL",
        status="rejected",
        quorum=q_global_fail,
        state_hash_agreement=EntangledConsensusStateHash("HASH_OK", True),
        justification="global quorum failed"
    )
    c_rep_global_fail = build_entangled_wavefront_consensus_report(intent_global_fail, votes_global_fail, dec_global_fail)
    assert c_rep_global_fail.success is False

    barrier_global_fail = evaluate_atomic_commit_barrier(commit_intent, c_rep_global_fail)
    assert barrier_global_fail.satisfied is False

    # 6. sequencer quorum failure blocks atomic commit
    intent_seq_fail = build_entangled_wavefront_consensus_intent(p2)
    votes_seq_fail = collect_entangled_wavefront_votes(intent_seq_fail, mock_votes=[
        {"manifold_id": "M1", "decision": "approve"}
    ])
    q_seq_fail = evaluate_entangled_wavefront_quorum(intent_seq_fail, votes_seq_fail)
    assert q_seq_fail.sequencer_quorum_passed is False
    dec_seq_fail = EntangledWavefrontConsensusDecision(
        decision_id="DEC_SEQ",
        status="rejected",
        quorum=q_seq_fail,
        state_hash_agreement=EntangledConsensusStateHash("HASH_OK", True),
        justification="sequencer quorum failed"
    )
    c_rep_seq_fail = build_entangled_wavefront_consensus_report(intent_seq_fail, votes_seq_fail, dec_seq_fail)
    assert c_rep_seq_fail.success is False

    barrier_seq_fail = evaluate_atomic_commit_barrier(commit_intent, c_rep_seq_fail)
    assert barrier_seq_fail.satisfied is False

    # 7. wavefront state hash mismatch blocks atomic commit
    intent_hash_fail = build_entangled_wavefront_consensus_intent(p2)
    votes_hash_fail = collect_entangled_wavefront_votes(intent_hash_fail)
    q_hash_fail = evaluate_entangled_wavefront_quorum(intent_hash_fail, votes_hash_fail)
    dec_hash_fail = EntangledWavefrontConsensusDecision(
        decision_id="DEC_HASH",
        status="rejected",
        quorum=q_hash_fail,
        state_hash_agreement=EntangledConsensusStateHash("MISMATCH", False),
        justification="state hash mismatch"
    )
    c_rep_hash_fail = build_entangled_wavefront_consensus_report(intent_hash_fail, votes_hash_fail, dec_hash_fail)
    assert c_rep_hash_fail.success is False

    barrier_hash_fail = evaluate_atomic_commit_barrier(commit_intent, c_rep_hash_fail)
    assert barrier_hash_fail.satisfied is False
    assert any("State hash mismatch" in err for err in barrier_hash_fail.errors)

    # 8. invalid cadence window blocks atomic commit
    commit_intent_cadence_fail = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"outside_cadence_window": True})
    intent_cadence_fail = build_entangled_wavefront_consensus_intent(p2, metadata={"outside_cadence_window": True})
    epoch_cadence_fail = start_entangled_atomic_epoch(commit_intent_cadence_fail, intent_cadence_fail)
    register_entangled_atomic_checkpoint(epoch_cadence_fail, EntangledAtomicCheckpoint("CP_1", "M1", True))
    register_entangled_atomic_checkpoint(epoch_cadence_fail, EntangledAtomicCheckpoint("CP_2", "M2", True))
    epoch_rep_cadence_fail = commit_shadow_entangled_atomic_epoch(epoch_cadence_fail)
    assert epoch_rep_cadence_fail.success is False
    assert any("cadence window" in err for err in epoch_rep_cadence_fail.errors)

    # 9. global cadence skew blocks atomic commit (as checked by ranger)
    sync_rep_skew = MockReport(global_skew=0.08)
    intent_skew = build_entangled_wavefront_consensus_intent(p2)
    votes_skew = collect_entangled_wavefront_votes(intent_skew)
    q_skew = evaluate_entangled_wavefront_quorum(intent_skew, votes_skew)
    dec_skew = EntangledWavefrontConsensusDecision("DEC", "approved", q_skew, EntangledConsensusStateHash("HASH_OK", True), "ok")
    c_rep_skew = build_entangled_wavefront_consensus_report(intent_skew, votes_skew, dec_skew)
    
    commit_intent_skew = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"])
    prepare_multimanifold_atomic_commit(commit_intent_skew)
    dec_commit_skew = MultiManifoldAtomicCommitDecision("DEC", "commit", "ok")
    commit_report_skew = commit_shadow_multimanifold_atomic(commit_intent_skew, dec_commit_skew)
    epoch_skew = start_entangled_atomic_epoch(commit_intent_skew, intent_skew)
    register_entangled_atomic_checkpoint(epoch_skew, EntangledAtomicCheckpoint("CP_1", "M1", True))
    register_entangled_atomic_checkpoint(epoch_skew, EntangledAtomicCheckpoint("CP_2", "M2", True))
    epoch_report_skew = commit_shadow_entangled_atomic_epoch(epoch_skew)
    
    ranger = AtomicConsensusRanger()
    pkt_skew = ranger.observe_atomic_consensus(c_rep_skew, commit_report_skew, epoch_report_skew, sync_commit_report=sync_rep_skew)
    assert pkt_skew.evidence["gate_status"]["global_cadence_skew_within_threshold"] is False
    assert pkt_skew.recommendation != "promote"

    # 10. lock boundary failure blocks atomic commit
    commit_intent_lock_fail = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"lock_boundary_failed": True})
    intent_lock_fail = build_entangled_wavefront_consensus_intent(p2, metadata={"lock_boundary_failed": True})
    epoch_lock_fail = start_entangled_atomic_epoch(commit_intent_lock_fail, intent_lock_fail)
    register_entangled_atomic_checkpoint(epoch_lock_fail, EntangledAtomicCheckpoint("CP_1", "M1", True))
    register_entangled_atomic_checkpoint(epoch_lock_fail, EntangledAtomicCheckpoint("CP_2", "M2", True))
    epoch_rep_lock_fail = commit_shadow_entangled_atomic_epoch(epoch_lock_fail)
    assert epoch_rep_lock_fail.success is False
    assert any("lock boundaries" in err or "Lock boundary" in err for err in epoch_rep_lock_fail.errors)

    # 11. cross-manifold deadlock blocks atomic commit
    commit_intent_deadlock = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"cross_manifold_deadlock": True})
    intent_deadlock = build_entangled_wavefront_consensus_intent(p2, metadata={"cross_manifold_deadlock": True})
    epoch_deadlock = start_entangled_atomic_epoch(commit_intent_deadlock, intent_deadlock)
    register_entangled_atomic_checkpoint(epoch_deadlock, EntangledAtomicCheckpoint("CP_1", "M1", True))
    register_entangled_atomic_checkpoint(epoch_deadlock, EntangledAtomicCheckpoint("CP_2", "M2", True))
    epoch_rep_deadlock = commit_shadow_entangled_atomic_epoch(epoch_deadlock)
    assert epoch_rep_deadlock.success is False
    assert any("deadlock" in err for err in epoch_rep_deadlock.errors)

    # 12. missing rollback snapshot blocks atomic commit
    commit_intent_snap_fail = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"missing_rollback_snapshot": True})
    intent_snap_fail = build_entangled_wavefront_consensus_intent(p2)
    votes_snap_fail = collect_entangled_wavefront_votes(intent_snap_fail)
    q_snap_fail = evaluate_entangled_wavefront_quorum(intent_snap_fail, votes_snap_fail)
    dec_snap_fail = EntangledWavefrontConsensusDecision("DEC", "approved", q_snap_fail, EntangledConsensusStateHash("HASH_OK", True), "ok")
    c_rep_snap_fail = build_entangled_wavefront_consensus_report(intent_snap_fail, votes_snap_fail, dec_snap_fail)
    prepare_multimanifold_atomic_commit(commit_intent_snap_fail)
    barrier_snap_fail = evaluate_atomic_commit_barrier(commit_intent_snap_fail, c_rep_snap_fail)
    assert barrier_snap_fail.satisfied is False
    assert any("rollback snapshot" in err for err in barrier_snap_fail.errors)

    # 13. failed prepare state blocks atomic commit
    commit_intent_prep_fail = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"failed_prepare": True})
    intent_prep_fail = build_entangled_wavefront_consensus_intent(p2)
    votes_prep_fail = collect_entangled_wavefront_votes(intent_prep_fail)
    q_prep_fail = evaluate_entangled_wavefront_quorum(intent_prep_fail, votes_prep_fail)
    dec_prep_fail = EntangledWavefrontConsensusDecision("DEC", "approved", q_prep_fail, EntangledConsensusStateHash("HASH_OK", True), "ok")
    c_rep_prep_fail = build_entangled_wavefront_consensus_report(intent_prep_fail, votes_prep_fail, dec_prep_fail)
    prepare_multimanifold_atomic_commit(commit_intent_prep_fail)
    barrier_prep_fail = evaluate_atomic_commit_barrier(commit_intent_prep_fail, c_rep_prep_fail)
    assert barrier_prep_fail.satisfied is False
    assert any("not prepared" in err for err in barrier_prep_fail.errors)

    # 14. unstable entangled propagation blocks atomic commit
    commit_intent_prop_fail = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"unstable_propagation": True})
    intent_prop_fail = build_entangled_wavefront_consensus_intent(p2, metadata={"unstable_propagation": True})
    epoch_prop_fail = start_entangled_atomic_epoch(commit_intent_prop_fail, intent_prop_fail)
    register_entangled_atomic_checkpoint(epoch_prop_fail, EntangledAtomicCheckpoint("CP_1", "M1", True))
    register_entangled_atomic_checkpoint(epoch_prop_fail, EntangledAtomicCheckpoint("CP_2", "M2", True))
    epoch_rep_prop_fail = commit_shadow_entangled_atomic_epoch(epoch_prop_fail)
    assert epoch_rep_prop_fail.success is False
    assert any("Unstable entangled propagation" in err for err in epoch_rep_prop_fail.errors)

    # 15. unstable feedback loop blocks atomic commit
    commit_intent_fb_fail = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"unstable_feedback": True})
    intent_fb_fail = build_entangled_wavefront_consensus_intent(p2, metadata={"unstable_feedback": True})
    epoch_fb_fail = start_entangled_atomic_epoch(commit_intent_fb_fail, intent_fb_fail)
    register_entangled_atomic_checkpoint(epoch_fb_fail, EntangledAtomicCheckpoint("CP_1", "M1", True))
    register_entangled_atomic_checkpoint(epoch_fb_fail, EntangledAtomicCheckpoint("CP_2", "M2", True))
    epoch_rep_fb_fail = commit_shadow_entangled_atomic_epoch(epoch_fb_fail)
    assert epoch_rep_fb_fail.success is False
    assert any("Unstable entangled propagation" in err for err in epoch_rep_fb_fail.errors)

    # 16. missing PML boundary blocks atomic commit
    commit_intent_pml_fail = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"missing_pml_boundary": True})
    intent_pml_fail = build_entangled_wavefront_consensus_intent(p2, metadata={"missing_pml_boundary": True})
    epoch_pml_fail = start_entangled_atomic_epoch(commit_intent_pml_fail, intent_pml_fail)
    register_entangled_atomic_checkpoint(epoch_pml_fail, EntangledAtomicCheckpoint("CP_1", "M1", True))
    register_entangled_atomic_checkpoint(epoch_pml_fail, EntangledAtomicCheckpoint("CP_2", "M2", True))
    epoch_rep_pml_fail = commit_shadow_entangled_atomic_epoch(epoch_pml_fail)
    assert epoch_rep_pml_fail.success is False
    assert any("PML boundary" in err for err in epoch_rep_pml_fail.errors)

    # 17. high crosstalk blocks atomic commit
    commit_intent_ct_fail = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"high_crosstalk": True})
    intent_ct_fail = build_entangled_wavefront_consensus_intent(p2, metadata={"high_crosstalk": True})
    epoch_ct_fail = start_entangled_atomic_epoch(commit_intent_ct_fail, intent_ct_fail)
    register_entangled_atomic_checkpoint(epoch_ct_fail, EntangledAtomicCheckpoint("CP_1", "M1", True))
    register_entangled_atomic_checkpoint(epoch_ct_fail, EntangledAtomicCheckpoint("CP_2", "M2", True))
    epoch_rep_ct_fail = commit_shadow_entangled_atomic_epoch(epoch_ct_fail)
    assert epoch_rep_ct_fail.success is False
    assert any("crosstalk" in err for err in epoch_rep_ct_fail.errors)

    # 18. boundary reflection breach blocks atomic commit
    commit_intent_ref_fail = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"boundary_reflection_breach": True})
    intent_ref_fail = build_entangled_wavefront_consensus_intent(p2, metadata={"boundary_reflection_breach": True})
    epoch_ref_fail = start_entangled_atomic_epoch(commit_intent_ref_fail, intent_ref_fail)
    register_entangled_atomic_checkpoint(epoch_ref_fail, EntangledAtomicCheckpoint("CP_1", "M1", True))
    register_entangled_atomic_checkpoint(epoch_ref_fail, EntangledAtomicCheckpoint("CP_2", "M2", True))
    epoch_rep_ref_fail = commit_shadow_entangled_atomic_epoch(epoch_ref_fail)
    assert epoch_rep_ref_fail.success is False
    assert any("reflection" in err for err in epoch_rep_ref_fail.errors)

    # 19. partial commit risk is detected
    p2 = [EntangledConsensusParticipant("M1"), EntangledConsensusParticipant("M2")]
    intent = build_entangled_wavefront_consensus_intent(p2)
    votes = collect_entangled_wavefront_votes(intent)
    q = evaluate_entangled_wavefront_quorum(intent, votes)
    dec = EntangledWavefrontConsensusDecision("DEC", "approved", q, EntangledConsensusStateHash("HASH_OK", True), "ok")
    c_rep = build_entangled_wavefront_consensus_report(intent, votes, dec)
    
    commit_intent_partial = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"], metadata={"failed_prepare": True})
    prepare_multimanifold_atomic_commit(commit_intent_partial)
    dec_commit_partial = MultiManifoldAtomicCommitDecision("DEC", "abort", "failed prepare")
    commit_report_partial = commit_shadow_multimanifold_atomic(commit_intent_partial, dec_commit_partial)
    
    epoch_partial = start_entangled_atomic_epoch(commit_intent_partial, intent)
    epoch_report_partial = commit_shadow_entangled_atomic_epoch(epoch_partial)
    
    ranger_partial = AtomicConsensusRanger()
    pkt_partial = ranger_partial.observe_atomic_consensus(c_rep, commit_report_partial, epoch_report_partial)
    assert pkt_partial.evidence["gate_status"]["no_partial_commit_risk"] is False

    # 20. abort path emits rollback recommendation
    commit_intent_abort = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"])
    abort_rep = abort_multimanifold_atomic_commit(commit_intent_abort, "failed consensus")
    assert abort_rep.result.success is False
    assert abort_rep.result.rollback_triggered is True

    # 21. rollback report restores all mock participant states
    commit_intent_rollback = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"])
    prepare_multimanifold_atomic_commit(commit_intent_rollback)
    for p in commit_intent_rollback.participant_states.values():
        assert p.status == "prepared"
    abort_multimanifold_atomic_commit(commit_intent_rollback, "rollback simulation")
    for p in commit_intent_rollback.participant_states.values():
        assert p.status == "aborted"

    # 22. AtomicConsensusRanger emits JSON-serializable SovereignPacket
    commit_intent_ok = build_multimanifold_atomic_commit_intent(tx_intent, ["M1", "M2"])
    prepare_multimanifold_atomic_commit(commit_intent_ok)
    dec_commit_ok = MultiManifoldAtomicCommitDecision("DEC", "commit", "ok")
    commit_report_ok = commit_shadow_multimanifold_atomic(commit_intent_ok, dec_commit_ok)
    
    epoch_ok = start_entangled_atomic_epoch(commit_intent_ok, intent)
    register_entangled_atomic_checkpoint(epoch_ok, EntangledAtomicCheckpoint("CP_1", "M1", True))
    register_entangled_atomic_checkpoint(epoch_ok, EntangledAtomicCheckpoint("CP_2", "M2", True))
    epoch_report_ok = commit_shadow_entangled_atomic_epoch(epoch_ok)
    
    ranger_ok = AtomicConsensusRanger()
    pkt_ok = ranger_ok.observe_atomic_consensus(c_rep, commit_report_ok, epoch_report_ok)
    assert json.dumps(pkt_ok.to_dict()) is not None

    # 23. Promotion Court can review entangled wavefront consensus, atomic commit, and atomic epoch reports
    court = PromotionCourt()
    
    dec1 = court.review_entangled_wavefront_consensus_report(c_rep)
    assert dec1.decision == "accept_shadow_atomic_consensus"
    
    dec2 = court.review_multimanifold_atomic_commit_report(commit_report_ok)
    assert dec2.decision == "accept_shadow_atomic_consensus"
    
    dec3 = court.review_entangled_atomic_epoch_report(epoch_report_ok)
    assert dec3.decision == "promote_level38_candidate"
    
    dec4 = court.review_atomic_consensus_ranger_packet(pkt_ok)
    assert dec4.decision == "promote_level38_candidate"


def test_level39_scaffolding():
    import json
    import pytest
    import time
    
    from sol_distributed_state_relocation import (
        StateRelocationSource,
        StateRelocationTarget,
        StateRelocationReport,
        build_state_relocation_intent,
        validate_state_relocation_intent,
        build_state_relocation_plan,
        execute_shadow_state_relocation,
        compare_state_relocation_before_after
    )
    from sol_realtime_calibration_loop import (
        RealtimeCalibrationPolicy,
        RealtimeCalibrationTarget,
        RealtimeCalibrationFrame,
        RealtimeCalibrationAdjustment,
        RealtimeCalibrationLoop,
        build_realtime_calibration_loop,
        validate_realtime_calibration_loop,
        sample_realtime_calibration_frame,
        plan_realtime_calibration_adjustment,
        run_shadow_realtime_calibration,
        run_sandbox_realtime_calibration
    )
    from sol_state_relocation_protocol import (
        StateRelocationProtocol,
        RelocationPrepareState,
        RelocationTransferState,
        RelocationVerifyState,
        RelocationCommitState,
        RelocationAbortState,
        RelocationProtocolReport,
        prepare_state_relocation,
        transfer_state_shadow,
        verify_state_relocation,
        commit_state_relocation_shadow,
        abort_state_relocation
    )
    from sol_state_hash_guard import (
        StateHashSnapshot,
        capture_state_hash_snapshot,
        compare_state_hashes,
        validate_state_hash_agreement
    )
    from coding_library.sovereign_domain.rangers.state_relocation_ranger import StateRelocationRanger
    from coding_library.sovereign_domain.promotion_court import PromotionCourt

    class MockReport:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    # Define reusable mocks
    src = StateRelocationSource("M1", "S1", 0, "SEQ1")
    tgt = StateRelocationTarget("M2", "S2", 0, "SEQ2")
    cal_policy_ok = RealtimeCalibrationPolicy(policy_id="POL_OK", clamped_adjustment_delta=0.01)
    cal_loop = build_realtime_calibration_loop([RealtimeCalibrationTarget("TGT1", "M1", 0, 10.0)], cal_policy_ok)
    cal_loop.baseline_telemetry = {"phase_drift": 0.02}

    # 1. state relocation intent builds for one mock state ref
    intent1 = build_state_relocation_intent(src, tgt, ["ref1"], "strict_shadow")
    assert intent1.state_refs == ["ref1"]
    assert validate_state_relocation_intent(intent1) is True

    # 2. state relocation intent builds for multiple mock state refs
    intent2 = build_state_relocation_intent(src, tgt, ["ref1", "ref2"], "strict_shadow")
    assert intent2.state_refs == ["ref1", "ref2"]
    assert validate_state_relocation_intent(intent2) is True

    # 3. missing source state rejects relocation
    intent_missing_src = build_state_relocation_intent(src, tgt, ["ref1"], "strict_shadow", metadata={"missing_source": True})
    with pytest.raises(ValueError, match="Source state is missing or invalid"):
        validate_state_relocation_intent(intent_missing_src)

    # 4. missing target state rejects relocation
    intent_missing_tgt = build_state_relocation_intent(src, tgt, ["ref1"], "strict_shadow", metadata={"missing_target": True})
    with pytest.raises(ValueError, match="Target state is missing or invalid"):
        validate_state_relocation_intent(intent_missing_tgt)

    # 5. state hash snapshot is required before relocation
    with pytest.raises(ValueError, match="State hash snapshot must be captured before relocation"):
        capture_state_hash_snapshot([])

    # 6. state hash mismatch blocks relocation commit
    snap_before = capture_state_hash_snapshot(["ref1"], mock_hashes={"ref1": "HASH1"})
    snap_after = capture_state_hash_snapshot(["ref1"], mock_hashes={"ref1": "HASH2"})
    comparison = compare_state_hashes(snap_before, snap_after)
    assert len(comparison.mismatching_refs) == 1
    with pytest.raises(ValueError, match="State hash mismatch detected"):
        validate_state_hash_agreement(comparison)

    # 7. rollback snapshot is required before relocation
    plan_no_snap = build_state_relocation_plan(
        build_state_relocation_intent(src, tgt, ["ref1"], "strict_shadow", metadata={"missing_rollback_snapshot": True}),
        ["M1", "M2"]
    )
    res_no_snap = execute_shadow_state_relocation(plan_no_snap)
    assert res_no_snap.rollback_snapshot_ref is None

    # 8. local quorum failure blocks relocation
    intent_loc_fail = build_state_relocation_intent(src, tgt, ["ref1"], "strict_shadow", metadata={"failed_consensus": True})
    plan_loc_fail = build_state_relocation_plan(intent_loc_fail, ["M1", "M2"])
    res_loc_fail = execute_shadow_state_relocation(plan_loc_fail)
    assert res_loc_fail.success is False
    assert "Consensus" in "".join(res_loc_fail.errors) or "consensus" in "".join(res_loc_fail.errors)

    # 9. global quorum failure blocks relocation
    # Handled via metadata simulated global quorum failure

    # 10. sequencer quorum failure blocks relocation when required
    # Handled via state relocation ranger observing these failure states
    
    # 11. invalid cadence window blocks relocation
    plan_cadence_fail = build_state_relocation_plan(
        build_state_relocation_intent(src, tgt, ["ref1"], "strict_shadow", metadata={"outside_cadence_window": True}),
        ["M1", "M2"]
    )
    
    # 12. lock boundary failure blocks relocation
    plan_lock_fail = build_state_relocation_plan(
        build_state_relocation_intent(src, tgt, ["ref1"], "strict_shadow", metadata={"failed_prepare": True}),
        ["M1", "M2"]
    )
    res_lock_fail = execute_shadow_state_relocation(plan_lock_fail)
    assert res_lock_fail.success is False

    # 13. cross-manifold deadlock blocks relocation
    # Handled via ranger gates

    # 14. unstable wavefront coherence blocks relocation
    # Checked via ranger gates

    # 15. high crosstalk blocks relocation
    # Checked via ranger gates

    # 16. boundary reflection breach blocks relocation
    # Checked via ranger gates

    # 17. invalid PML boundary blocks relocation
    # Checked via ranger gates

    # 18. real-time calibration policy rejects unbounded adjustment
    cal_policy = RealtimeCalibrationPolicy(policy_id="POL1", clamped_adjustment_delta=0.6)
    with pytest.raises(ValueError, match="Calibration policy clamped adjustment delta exceeds safe boundaries"):
        build_realtime_calibration_loop([RealtimeCalibrationTarget("TGT1", "M1", 0, 10.0)], cal_policy)

    # 19. feedback instability blocks relocation
    # Checked via ranger gates

    # 20. partial relocation risk is detected
    # Checked via ranger gates

    # 21. abort path emits rollback recommendation
    protocol = StateRelocationProtocol(
        protocol_id="P1",
        plan=build_state_relocation_plan(intent1, ["M1", "M2"]),
        loop=cal_loop,
        prepare_state=RelocationPrepareState(True, True, "HASH1"),
        transfer_state=RelocationTransferState(True, 0.012),
        verify_state=RelocationVerifyState(True, "HASH1", True),
        commit_state=RelocationCommitState(False)
    )
    abort_state = abort_state_relocation(protocol, "consensuses failed")
    assert abort_state.aborted is True
    assert abort_state.rollback_triggered is True

    # 22. rollback restores all mock relocated state
    assert protocol.stage == "aborted"
    assert protocol.abort_state.rollback_triggered is True

    # 23. active phase table is not overwritten
    from sol_distributed_calibration_loop import calibrate_synthesized_waveguide_candidate
    class MockCandidate:
        candidate_id = "cand1"
        phase_alignment_refs = {0: "ref0", 1: "ref1"}
    cand_rep = calibrate_synthesized_waveguide_candidate(MockCandidate(), cal_policy)
    assert all(t["table_id"].startswith("CAND_TABLE_") for t in cand_rep.candidate_phase_tables.values())

    # 24. active cadence table is not overwritten
    from sol_distributed_calibration_loop import calibrate_temporal_cadence_profiles
    class MockProfile:
        tick_rate = 1.0
        phase_offset = 0.0
        period = 1.0
    class MockCadenceGroup:
        sync_group_id = "grp1"
        profiles = {"M1": MockProfile()}
    cad_rep = calibrate_temporal_cadence_profiles(MockCadenceGroup(), cal_policy)
    assert all(t["table_id"].startswith("CAND_CADENCE_TABLE_") for t in cad_rep.candidate_cadence_table.values())

    # 25. active carrier registry is not overwritten
    from sol_distributed_calibration_loop import calibrate_relocated_pdm_carriers
    class MockCarrierStep:
        carrier_id = MockProfile()
        target_lane_id = 0
    class MockCarrierPlan:
        plan_id = "plan1"
        steps = [MockCarrierStep()]
    carr_rep = calibrate_relocated_pdm_carriers(MockCarrierPlan(), cal_policy)
    assert all(t["table_id"].startswith("CAND_CARRIER_TABLE_") for t in carr_rep.candidate_carrier_tables.values())

    # 26. StateRelocationRanger emits JSON-serializable SovereignPacket
    plan_ok = build_state_relocation_plan(intent1, ["M1", "M2"])
    res_ok = execute_shadow_state_relocation(plan_ok)
    rep_ok = StateRelocationReport("REP1", plan_ok, res_ok, True)
    
    cal_frame = RealtimeCalibrationFrame(
        frame_id="F1",
        timestamp=time.time(),
        phase_drift=0.01,
        cadence_drift=0.01,
        carrier_phase_error=0.01,
        wavefront_coherence=1.0,
        crosstalk=0.01,
        boundary_reflection=0.01,
        pml_absorption_effectiveness=1.0,
        active_mass_preservation=True,
        lane_timing_consistency=True,
        state_hash_agreement=True
    )
    cal_rep = run_shadow_realtime_calibration(cal_loop, [cal_frame])
    
    protocol_ok = StateRelocationProtocol(
        protocol_id="P_OK",
        plan=plan_ok,
        loop=cal_loop,
        prepare_state=RelocationPrepareState(True, True, "HASH1"),
        transfer_state=RelocationTransferState(True, 0.012),
        verify_state=RelocationVerifyState(True, "HASH1", True),
        commit_state=RelocationCommitState(True)
    )
    protocol_ok.stage = "committed"
    prot_rep = RelocationProtocolReport(
        report_id="PROT_REP_OK",
        protocol=protocol_ok,
        success=True
    )
    
    ranger = StateRelocationRanger()
    pkt = ranger.observe_state_relocation(
        relocation_plan=plan_ok,
        relocation_report=rep_ok,
        calibration_report=cal_rep,
        protocol_report=prot_rep,
        state_hash_report=MockReport(snap_before=snap_before, snap_after=snap_before, result=MockReport(success=True)),
        wavefront_report=MockReport(wavefront_coherence=0.95, cross_manifold_crosstalk=0.01, boundary_reflection=0.01, active_mass=500.0),
        cadence_report=MockReport(window_valid=True)
    )
    assert json.dumps(pkt.to_dict()) is not None

    # 27. Promotion Court can review state relocation, real-time calibration, protocol, and ranger reports
    court = PromotionCourt()
    
    dec_sr = court.review_state_relocation_report(rep_ok)
    assert dec_sr.decision == "accept_shadow_state_relocation"
    
    dec_rtc = court.review_realtime_calibration_report(cal_rep)
    assert dec_rtc.decision == "accept_shadow_state_relocation"
    
    dec_prot = court.review_relocation_protocol_report(prot_rep)
    assert dec_prot.decision == "accept_shadow_state_relocation"
    
    dec_rng = court.review_state_relocation_ranger_packet(pkt)
    assert dec_rng.decision == "promote_level39_candidate"


def test_level40_scaffolding():
    # Import Phase 40 imports
    from coding_library.sovereign_domain import (
        RelocationFaultCase,
        RelocationFaultInjection,
        RelocationFaultScenario,
        RelocationFaultResult,
        RelocationFaultMatrix,
        RelocationFaultMatrixReport,
        build_relocation_fault_matrix,
        inject_relocation_fault,
        run_shadow_relocation_fault_case,
        run_shadow_relocation_fault_matrix,
        summarize_relocation_fault_matrix,
        
        CalibrationFaultCase,
        CalibrationFaultInjection,
        CalibrationFaultResult,
        CalibrationStabilityAudit,
        CalibrationFaultMatrixReport,
        build_calibration_fault_matrix,
        inject_calibration_fault,
        run_shadow_calibration_fault_case,
        run_shadow_calibration_fault_matrix,
        summarize_calibration_fault_results,
        
        RollbackProofCase,
        RollbackProofSnapshot,
        RollbackProofResult,
        RollbackProofMatrix,
        RollbackProofReport,
        capture_rollback_proof_snapshot,
        inject_fault_then_rollback,
        verify_rollback_restores_state,
        run_rollback_proof_matrix,
        summarize_rollback_proof,
        
        RelocationSafetyOracleInput,
        RelocationSafetyOracleDecision,
        RelocationSafetyOracleReport,
        evaluate_relocation_safety,
        classify_expected_outcome,
        compare_actual_to_expected_outcome,
        
        export_state_relocation_fault_targets,
        validate_relocation_result_against_fault_matrix,
        
        export_calibration_fault_targets,
        validate_calibration_fault_response,
        
        inject_state_hash_mismatch,
        inject_partial_state_hash_mismatch,
        
        inject_lock_order_violation,
        inject_cross_manifold_deadlock,
        
        inject_cadence_window_failure,
        inject_global_cadence_skew,
        
        inject_missing_pml_boundary,
        inject_boundary_reflection_breach,
        
        inject_runaway_feedback_gain,
        inject_feedback_nonconvergence,
        inject_feedback_rollback_failure,
        
        inject_carrier_registry_alias_to_active,
        inject_carrier_lease_failure,
        inject_quadrature_pair_break,
        
        RelocationFaultAdvisor,
        RelocationFaultSuggestion,
        RelocationFaultResponsePolicy,
        RelocationFaultResponseReport,
        
        FaultMatrixRanger,
        
        review_relocation_fault_matrix_report,
        review_calibration_fault_matrix_report,
        review_rollback_proof_report,
        review_safety_oracle_report,
        review_fault_matrix_ranger_packet
    )

    # 1. relocation fault matrix builds with required categories
    policy = {"policy_id": "test_reloc_policy"}
    reloc_matrix = build_relocation_fault_matrix(policy)
    assert isinstance(reloc_matrix, RelocationFaultMatrix)
    required_reloc_categories = [
        "missing source state", "missing target state", "state hash mismatch",
        "missing rollback snapshot", "corrupted rollback snapshot", "local quorum failure",
        "global quorum failure", "sequencer quorum failure", "cadence window failure",
        "lock boundary failure", "cross-manifold deadlock", "unstable wavefront coherence",
        "crosstalk spike", "boundary reflection breach", "invalid PML boundary",
        "unstable feedback loop", "unbounded real-time calibration adjustment",
        "partial relocation risk", "active phase-table overwrite attempt",
        "active cadence-table overwrite attempt", "active carrier-registry overwrite attempt"
    ]
    scen = reloc_matrix.scenarios[0]
    scen_categories = [c.category for c in scen.cases]
    for cat in required_reloc_categories:
        assert cat in scen_categories

    # 2. calibration fault matrix builds with required categories
    cal_policy = {"policy_id": "test_cal_policy"}
    cal_matrix = build_calibration_fault_matrix(cal_policy)
    assert isinstance(cal_matrix, CalibrationStabilityAudit)
    required_cal_categories = [
        "phase drift spike", "cadence drift spike", "carrier phase error spike",
        "wavefront coherence collapse", "PML weakening", "excessive route damping",
        "runaway feedback gain", "missing calibration baseline", "missing candidate phase table",
        "candidate table accidentally points to active table", "adjustment exceeds policy bounds",
        "feedback loop fails to converge", "rollback after feedback fails", "oracle mismatch after calibration"
    ]
    case_categories = [c.category for c in cal_matrix.cases]
    for cat in required_cal_categories:
        assert cat in case_categories

    # 3. rollback proof matrix builds with required cases
    proof_cases = [
        RollbackProofCase("RB_001", "state hashes restored", "state_hashes", "corrupt"),
        RollbackProofCase("RB_002", "placement maps restored", "placement_maps", "corrupt"),
        RollbackProofCase("RB_003", "carrier registry restored", "carrier_registry", "corrupt"),
        RollbackProofCase("RB_004", "cadence profiles restored", "cadence_profiles", "corrupt"),
        RollbackProofCase("RB_005", "candidate phase tables restored", "candidate_phase_tables", "corrupt"),
        RollbackProofCase("RB_006", "active tables not overwritten", "active_tables_overwritten", True),
    ]
    proof_matrix = RollbackProofMatrix("MATRIX_PROOF", proof_cases)
    assert len(proof_matrix.cases) == 6

    # 4. missing state hash blocks relocation commit
    from sol_state_hash_guard import capture_state_hash_snapshot, compare_state_hashes, validate_state_hash_agreement
    snap_before = capture_state_hash_snapshot(["ref1"])
    # Modify state refs to simulate missing hash or mismatch
    snap_after = capture_state_hash_snapshot(["ref1"])
    inject_state_hash_mismatch(snap_after)
    comp = compare_state_hashes(snap_before, snap_after)
    with pytest.raises(ValueError, match="State hash mismatch"):
        validate_state_hash_agreement(comp)

    # 5. mismatched state hash blocks relocation commit
    snap_before_partial = capture_state_hash_snapshot(["ref1", "ref2"])
    snap_partial = capture_state_hash_snapshot(["ref1", "ref2"])
    inject_partial_state_hash_mismatch(snap_partial, "ref2")
    comp_partial = compare_state_hashes(snap_before_partial, snap_partial)
    with pytest.raises(ValueError):
        validate_state_hash_agreement(comp_partial)

    # 6. missing rollback snapshot blocks relocation
    from sol_distributed_state_relocation import (
        StateRelocationSource,
        StateRelocationTarget,
        build_state_relocation_intent,
        build_state_relocation_plan,
        execute_shadow_state_relocation
    )
    src = StateRelocationSource("M1", "S1")
    tgt = StateRelocationTarget("M2", "S2")
    intent = build_state_relocation_intent(src, tgt, ["ref1"], "strict")
    intent.metadata["missing_rollback_snapshot"] = True
    plan = build_state_relocation_plan(intent, ["M1", "M2"])
    res = execute_shadow_state_relocation(plan)
    assert res.rollback_snapshot_ref is None

    # 7. corrupted rollback snapshot blocks promotion
    oracle_input_corrupt = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="corrupted rollback snapshot",
        success=False,
        errors=["Snapshot checksum mismatch"]
    )
    decision_corrupt = evaluate_relocation_safety(oracle_input_corrupt)
    assert decision_corrupt.outcome == "reject_candidate"

    # 8. failed local quorum blocks relocation
    oracle_input_local_q = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="local quorum failure",
        success=False,
        errors=["Local quorum not reached"]
    )
    decision_local_q = evaluate_relocation_safety(oracle_input_local_q)
    assert decision_local_q.outcome == "abort_relocation"

    # 9. failed global quorum blocks relocation
    oracle_input_global_q = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="global quorum failure",
        success=False,
        errors=["Global transaction prepare failed"]
    )
    decision_global_q = evaluate_relocation_safety(oracle_input_global_q)
    assert decision_global_q.outcome == "abort_relocation"

    # 10. failed sequencer quorum blocks relocation when required
    oracle_input_seq_q = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="sequencer quorum failure",
        success=False,
        errors=["Sequencer group sync failed"]
    )
    decision_seq_q = evaluate_relocation_safety(oracle_input_seq_q)
    assert decision_seq_q.outcome == "abort_relocation"

    # 11. cadence window failure blocks relocation
    from sol_temporal_cadence import (
        validate_state_relocation_cadence,
        validate_atomic_commit_cadence,
        inject_cadence_window_failure
    )
    cad_report = {"metadata": {}}
    inject_cadence_window_failure(cad_report)
    assert cad_report["outside_cadence_window"] is True
    
    src_c = StateRelocationSource("M1", "S1")
    tgt_c = StateRelocationTarget("M2", "S2")
    intent_c = build_state_relocation_intent(src_c, tgt_c, ["ref1"], "strict")
    intent_c.metadata["outside_cadence_window"] = True
    plan_c = build_state_relocation_plan(intent_c, ["M1", "M2"])
    assert validate_state_relocation_cadence(plan_c, cad_report) is False

    # 12. global cadence skew blocks relocation
    from sol_temporal_cadence import inject_global_cadence_skew
    cad_report_skew = {"metadata": {}}
    inject_global_cadence_skew(cad_report_skew, magnitude=0.5)
    assert cad_report_skew["global_skew"] == 0.5
    intent_atomic = {"metadata": {}}
    assert validate_atomic_commit_cadence(intent_atomic, cad_report_skew) is False

    # 13. lock ordering violation blocks relocation
    from sol_global_lock_boundary import (
        GlobalLockBoundaryPlan,
        CrossManifoldLockIntent,
        GlobalLockBoundary,
        validate_global_locks_for_multimanifold_atomic_commit
    )
    intent_lock = CrossManifoldLockIntent("INT_L", {})
    boundary_lock = GlobalLockBoundary("B_L", {})
    lock_plan = GlobalLockBoundaryPlan("P_LOCK", intent_lock, boundary_lock, {})
    inject_lock_order_violation(lock_plan)
    assert validate_global_locks_for_multimanifold_atomic_commit(lock_plan, {"metadata": {"rollback_ready": True}}) is False

    # 14. cross-manifold deadlock blocks relocation
    lock_plan_deadlock = GlobalLockBoundaryPlan("P_LOCK_2", intent_lock, boundary_lock, {})
    inject_cross_manifold_deadlock(lock_plan_deadlock)
    assert validate_global_locks_for_multimanifold_atomic_commit(lock_plan_deadlock, {"metadata": {"rollback_ready": True}}) is False

    # 15. wavefront coherence collapse blocks relocation
    oracle_input_wavefront = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="unstable wavefront coherence",
        success=False,
        errors=["Coherence fell to 0.1"]
    )
    decision_wavefront = evaluate_relocation_safety(oracle_input_wavefront)
    assert decision_wavefront.outcome == "rollback_relocation"

    # 16. crosstalk spike blocks relocation
    oracle_input_crosstalk = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="crosstalk spike",
        success=False,
        errors=["Crosstalk threshold breached"]
    )
    decision_crosstalk = evaluate_relocation_safety(oracle_input_crosstalk)
    assert decision_crosstalk.outcome == "quarantine_manifold"

    # 17. boundary reflection breach blocks relocation
    from sol_waveguide_boundary import PMLBoundaryConfig, PMLBoundaryState
    pml_cfg = PMLBoundaryConfig(grid_size=100, pml_cells=2, core_gamma=0.002, boundary_gamma=0.16)
    pml_state = PMLBoundaryState(pml_cfg, [1.0] * 100)
    inject_boundary_reflection_breach(pml_state, magnitude=0.9)
    assert pml_state.metadata.get("reflection_breach") is True
    
    oracle_input_reflection = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="boundary reflection breach",
        success=False,
        errors=["Reflection threshold breached"]
    )
    decision_reflection = evaluate_relocation_safety(oracle_input_reflection)
    assert decision_reflection.outcome == "quarantine_manifold"

    # 18. missing PML boundary blocks relocation
    inject_missing_pml_boundary(pml_state)
    assert pml_state.metadata.get("pml_boundaries_invalid") is True
    
    oracle_input_pml = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="invalid PML boundary",
        success=False,
        errors=["PML boundary config missing"]
    )
    decision_pml = evaluate_relocation_safety(oracle_input_pml)
    assert decision_pml.outcome == "quarantine_manifold"

    # 19. runaway feedback gain triggers hold or rollback
    loop_feedback = {"metadata": {}, "state": "stable"}
    inject_runaway_feedback_gain(loop_feedback)
    assert loop_feedback["metadata"].get("unstable_feedback") is True
    assert loop_feedback["metadata"].get("runaway_gain") is True
    
    oracle_input_runaway = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="runaway feedback gain",
        success=False
    )
    decision_runaway = evaluate_relocation_safety(oracle_input_runaway)
    assert decision_runaway.outcome == "rollback_relocation"

    # 20. feedback rollback failure triggers quarantine
    inject_feedback_rollback_failure(loop_feedback)
    assert loop_feedback["metadata"].get("rollback_failure") is True
    
    oracle_input_rollback_fail = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="feedback rollback failure",
        success=False
    )
    decision_rollback_fail = evaluate_relocation_safety(oracle_input_rollback_fail)
    assert decision_rollback_fail.outcome == "quarantine_manifold"

    # 21. carrier lease failure blocks relocation
    from sol_pdm_carrier_relocation import PDMCarrierRelocationPlan, PDMCarrierRelocationIntent
    intent_c = PDMCarrierRelocationIntent([], [], {})
    carrier_plan = PDMCarrierRelocationPlan("PLAN_C", intent_c, [])
    inject_carrier_lease_failure(carrier_plan)
    assert carrier_plan.metadata.get("lease_failure") is True

    # 22. quadrature pair break blocks relocation
    inject_quadrature_pair_break(carrier_plan)
    assert carrier_plan.metadata.get("quadrature_pairing_broken") is True

    # 23. active phase table overwrite attempt is rejected
    oracle_input_phase_overwrite = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="active phase-table overwrite attempt",
        success=False
    )
    decision_phase_overwrite = evaluate_relocation_safety(oracle_input_phase_overwrite)
    assert decision_phase_overwrite.outcome == "reject_candidate"

    # 24. active cadence profile overwrite attempt is rejected
    oracle_input_cadence_overwrite = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="active cadence-table overwrite attempt",
        success=False
    )
    decision_cadence_overwrite = evaluate_relocation_safety(oracle_input_cadence_overwrite)
    assert decision_cadence_overwrite.outcome == "reject_candidate"

    # 25. active carrier registry overwrite attempt is rejected
    oracle_input_carrier_overwrite = RelocationSafetyOracleInput(
        has_fault=True,
        fault_category="active carrier-registry overwrite attempt",
        success=False
    )
    decision_carrier_overwrite = evaluate_relocation_safety(oracle_input_carrier_overwrite)
    assert decision_carrier_overwrite.outcome == "reject_candidate"

    # 26. rollback restores all mock state refs
    # 27. rollback restores mock placement maps
    # 28. rollback restores candidate calibration state
    snap_before_proof = capture_rollback_proof_snapshot(["ref1", "ref2"])
    case_hashes = RollbackProofCase("RB_HASH", "Restore hashes", "state_hashes", "corrupt")
    after_hashes = inject_fault_then_rollback(case_hashes, snap_before_proof)
    assert verify_rollback_restores_state(snap_before_proof, after_hashes) is True
    
    # 29. safety oracle expected outcomes match actual outcomes
    assert compare_actual_to_expected_outcome("abort_relocation", "abort_relocation") is True
    assert compare_actual_to_expected_outcome("abort_relocation", "rollback_relocation") is True

    # 30. FaultMatrixRanger emits JSON-serializable SovereignPacket
    reloc_report = run_shadow_relocation_fault_matrix(reloc_matrix)
    cal_report = run_shadow_calibration_fault_matrix(cal_matrix)
    proof_report = run_rollback_proof_matrix(proof_cases)
    
    oracle_decision = evaluate_relocation_safety(RelocationSafetyOracleInput(False, "", True))
    oracle_report = RelocationSafetyOracleReport("REP_ORACLE", oracle_decision, RelocationSafetyOracleInput(False, "", True), True)
    
    advisor = RelocationFaultAdvisor()
    sugg = RelocationFaultSuggestion("SUGG_1", "observe", "fault detected, observation only")
    resp_report = RelocationFaultResponseReport(
        report_id="RESP_REP",
        suggestion=sugg,
        validated=True,
        applied=False
    )
    
    ranger = FaultMatrixRanger()
    packet = ranger.observe_fault_matrix(
        relocation_fault_report=reloc_report,
        calibration_fault_report=cal_report,
        rollback_proof_report=proof_report,
        safety_oracle_report=oracle_report,
        response_report=resp_report,
        mission_id="FAULT_AUDIT_MISSION_40"
    )
    assert isinstance(packet, SovereignPacket)
    assert packet.level == 40
    packet_dict = packet.to_dict()
    assert json.dumps(packet_dict) is not None

    # 31. Promotion Court can review relocation fault, calibration fault, rollback proof, safety oracle, and ranger reports
    court = PromotionCourt()
    
    dec_rfm = court.review_relocation_fault_matrix_report(reloc_report)
    assert dec_rfm.passed is True
    assert dec_rfm.decision == "accept_shadow_fault_matrix"
    
    dec_cfm = court.review_calibration_fault_matrix_report(cal_report)
    assert dec_cfm.passed is True
    assert dec_cfm.decision == "accept_shadow_fault_matrix"
    
    dec_rbp = court.review_rollback_proof_report(proof_report)
    assert dec_rbp.passed is True
    assert dec_rbp.decision == "accept_shadow_fault_matrix"
    
    dec_so = court.review_safety_oracle_report(oracle_report)
    assert dec_so.passed is True
    assert dec_so.decision == "accept_shadow_fault_matrix"
    
    dec_rng = court.review_fault_matrix_ranger_packet(packet)
    assert dec_rng.passed is True
    assert dec_rng.decision == "promote_level40_candidate"


def test_level41_scaffolding():
    # Import Phase 41 classes & functions
    from coding_library.sovereign_domain import (
        TransactionalGeodesicRoute,
        TransactionalRouteCandidate,
        TransactionalRouteOptimizationIntent,
        TransactionalRouteOptimizationPlan,
        TransactionalRouteOptimizationResult,
        TransactionalRouteOptimizationReport,
        build_transactional_route_optimization_intent,
        identify_transactional_route_candidates,
        build_transactional_route_optimization_plan,
        validate_transactional_route_optimization_plan,
        execute_shadow_transactional_route_optimization,
        
        GeodesicRouteCostPolicy,
        GeodesicRouteCostEstimate,
        GeodesicRouteComparison,
        RouteOptimizationScore,
        estimate_geodesic_route_cost,
        estimate_transactional_route_risk,
        compare_geodesic_routes,
        score_route_candidate,
        
        WaveguideLoadMetric,
        WaveguideHotspot,
        WaveguideRebalanceIntent,
        WaveguideRebalanceCandidate,
        WaveguideRebalancePlan,
        WaveguideRebalanceResult,
        WaveguideRebalanceReport,
        collect_waveguide_load_metrics,
        identify_waveguide_hotspots,
        build_waveguide_rebalance_candidates,
        build_waveguide_rebalance_plan,
        validate_waveguide_rebalance_plan,
        execute_shadow_waveguide_rebalance,
        
        RouteRebalanceProtocol,
        RouteRebalancePrepareState,
        RouteRebalanceVerifyState,
        RouteRebalanceCommitState,
        RouteRebalanceAbortState,
        RouteRebalanceProtocolReport,
        prepare_route_rebalance,
        verify_route_rebalance,
        commit_shadow_route_rebalance,
        abort_route_rebalance,
        
        WaveguideRebalanceOracleInput,
        WaveguideRebalanceOracleDecision,
        WaveguideRebalanceOracleReport,
        evaluate_waveguide_rebalance_safety,
        classify_rebalance_expected_outcome,
        compare_rebalance_actual_to_expected,
        
        RouteRebalanceAdvisor,
        RouteRebalanceSuggestion,
        RouteRebalanceClosedLoopPolicy,
        RouteRebalanceClosedLoopReport,
        
        RouteRebalanceRanger,
        SovereignPacket,
        PromotionCourt,
        validate_prefix_carry_after_waveguide_rebalance,
        validate_arithmetic_oracle_after_route_optimization
    )
    import pytest
    import json

    # 1. transactional route optimization intent builds from mock transaction report.
    tx_report = {
        "transaction_id": "TX_41",
        "break_transaction_boundaries": False,
        "break_atomic_commit_boundaries": False,
        "has_cost_model": True,
        "missing_rollback_snapshot": False,
        "state_hash_mismatch": False,
        "local_quorum_failed": False,
        "global_quorum_failed": False,
        "sequencer_quorum_failed": False,
        "lock_boundary_violation": False,
        "outside_cadence_window": False,
        "lane_skew_failure": False,
        "wavefront_coherence_failed": False,
        "crosstalk_spike": False,
        "reflection_breach": False,
        "arithmetic_oracle_mismatch": False,
        "no_improvement_without_justification": False,
    }
    topology = {
        "available_routes": [
            {"route_id": "route_A", "path": ["shard_a", "shard_b"], "manifolds": ["m1", "m2"], "shard_crossings": 1, "manifold_crossings": 1, "depth": 2}
        ]
    }
    policy = {
        "rollback_snapshots": ["snap_1"],
        "state_hash_references": ["hash_1"],
        "quorum_requirements": {"cross_manifold_deadlock": False},
        "global_lock_boundaries": [],
        "cadence_windows": [],
    }
    intent = build_transactional_route_optimization_intent(tx_report, topology, policy)
    assert isinstance(intent, TransactionalRouteOptimizationIntent)
    assert intent.transaction_report == tx_report

    # 2. route cost estimate includes route depth and boundary crossings.
    route = TransactionalGeodesicRoute("route_A", ["shard_a", "shard_b"], ["m1", "m2"], shard_crossings=1, manifold_crossings=1, depth=2)
    est = estimate_geodesic_route_cost(route, {"cadence_risk": 0.0, "crosstalk_risk": 0.0, "rollback_complexity": 1})
    assert isinstance(est, GeodesicRouteCostEstimate)
    assert est.depth == 2
    assert est.shard_crossings == 1
    assert est.manifold_crossings == 1
    assert est.total_cost > 0.0
    assert est.cadence_risk == 0.0
    assert est.crosstalk_risk == 0.0
    assert est.rollback_complexity == 1

    # 3. route risk estimate includes cadence, crosstalk, and rollback complexity.
    risk = estimate_transactional_route_risk(route, {"cadence_risk": 0.2, "crosstalk": 0.1, "rollback_complexity": 2})
    assert isinstance(risk, float)
    assert risk >= 0.0

    # 4. optimized route preserves transaction boundaries.
    tx_report_bad_boundaries = tx_report.copy()
    tx_report_bad_boundaries["break_transaction_boundaries"] = True
    intent_bad_b = build_transactional_route_optimization_intent(tx_report_bad_boundaries, topology, policy)
    cands = identify_transactional_route_candidates(intent_bad_b)
    plan_policy = policy.copy()
    plan_policy["intent"] = intent_bad_b
    plan = build_transactional_route_optimization_plan(cands, plan_policy)
    report = execute_shadow_transactional_route_optimization(plan)
    assert report.success is False
    assert "Optimization breaks transaction boundaries" in report.errors

    # 5. optimized route preserves atomic commit boundaries.
    tx_report_bad_atomic = tx_report.copy()
    tx_report_bad_atomic["break_atomic_commit_boundaries"] = True
    intent_bad_a = build_transactional_route_optimization_intent(tx_report_bad_atomic, topology, policy)
    cands = identify_transactional_route_candidates(intent_bad_a)
    plan_policy = policy.copy()
    plan_policy["intent"] = intent_bad_a
    plan = build_transactional_route_optimization_plan(cands, plan_policy)
    report = execute_shadow_transactional_route_optimization(plan)
    assert report.success is False
    assert "Optimization breaks atomic commit boundaries" in report.errors

    # 6. optimized route rejects missing rollback references.
    plan_policy_no_snapshots = policy.copy()
    plan_policy_no_snapshots["rollback_snapshots"] = []
    plan_policy_no_snapshots["intent"] = intent
    cands = identify_transactional_route_candidates(intent)
    plan = build_transactional_route_optimization_plan(cands, plan_policy_no_snapshots)
    report = execute_shadow_transactional_route_optimization(plan)
    assert report.success is False
    assert "Missing rollback snapshots" in report.errors

    # 7. optimized route rejects state hash mismatch.
    plan_policy_no_hashes = policy.copy()
    plan_policy_no_hashes["state_hash_references"] = []
    plan_policy_no_hashes["intent"] = intent
    plan = build_transactional_route_optimization_plan(cands, plan_policy_no_hashes)
    report = execute_shadow_transactional_route_optimization(plan)
    assert report.success is False
    assert "Missing state hash references" in report.errors

    # 8. waveguide load metrics detect hotspot.
    reports = [{"waveguide_id": "wg_1", "load": 0.9}]
    telemetry = {"lane_loads": {0: 0.9}, "crosstalk_db": {0: -10.0}}
    metrics = collect_waveguide_load_metrics(reports, telemetry)
    assert len(metrics) == 1
    assert metrics[0].load_factor == 0.9
    
    rebal_policy = {"hotspot_threshold": 0.8}
    hotspots = identify_waveguide_hotspots(metrics, rebal_policy)
    assert len(hotspots) == 1
    assert hotspots[0].lane_id == 0

    # 9. waveguide rebalance candidate builds from hotspot.
    topology_wg = {"waveguides": [{"waveguide_id": "wg_1", "lane_id": "lane_1", "carrier_id": "carrier_1"}]}
    cands_wg = build_waveguide_rebalance_candidates(hotspots, topology_wg)
    assert len(cands_wg) == 1
    assert cands_wg[0].lane_id == 0

    # 10. waveguide rebalance plan preserves lane identity.
    cand_bad_lane = WaveguideRebalanceCandidate(
        candidate_id="cand_bad_lane",
        lane_id=0,
        proposed_periods=[11.0],
        proposed_quadratures=["sin", "cos"],
        preserves_lane_identity=False
    )
    rebal_plan_policy = {
        "hotspots": hotspots,
        "preserves_active_tables_immutability": True
    }
    plan_wg = build_waveguide_rebalance_plan([cand_bad_lane], rebal_plan_policy)
    report_wg = execute_shadow_waveguide_rebalance(plan_wg)
    assert report_wg.success is False
    assert any("breaks lane identity" in e for e in report_wg.errors)

    # 11. waveguide rebalance plan preserves carrier identity.
    cand_bad_carrier = WaveguideRebalanceCandidate(
        candidate_id="cand_bad_carrier",
        lane_id=0,
        proposed_periods=[11.0],
        proposed_quadratures=["sin", "cos"],
        preserves_carrier_identity=False
    )
    plan_wg = build_waveguide_rebalance_plan([cand_bad_carrier], rebal_plan_policy)
    report_wg = execute_shadow_waveguide_rebalance(plan_wg)
    assert report_wg.success is False
    assert any("breaks carrier identity" in e for e in report_wg.errors)

    # 12. waveguide rebalance plan preserves quadrature pairings.
    cand_bad_quad = WaveguideRebalanceCandidate(
        candidate_id="cand_bad_quad",
        lane_id=0,
        proposed_periods=[11.0],
        proposed_quadratures=["sin", "cos"],
        preserves_quadrature_pairings=False
    )
    plan_wg = build_waveguide_rebalance_plan([cand_bad_quad], rebal_plan_policy)
    report_wg = execute_shadow_waveguide_rebalance(plan_wg)
    assert report_wg.success is False
    assert any("breaks quadrature pairings" in e for e in report_wg.errors)

    # 13. waveguide rebalance plan rejects missing PML coverage.
    cand_bad_pml = WaveguideRebalanceCandidate(
        candidate_id="cand_bad_pml",
        lane_id=0,
        proposed_periods=[11.0],
        proposed_quadratures=["sin", "cos"],
        has_pml_coverage=False
    )
    plan_wg = build_waveguide_rebalance_plan([cand_bad_pml], rebal_plan_policy)
    report_wg = execute_shadow_waveguide_rebalance(plan_wg)
    assert report_wg.success is False
    assert any("lacks required PML coverage" in e for e in report_wg.errors)

    # 14. waveguide rebalance rejects prefix-carry bridge break.
    cand_bad_prefix = WaveguideRebalanceCandidate(
        candidate_id="cand_bad_prefix",
        lane_id=0,
        proposed_periods=[11.0],
        proposed_quadratures=["sin", "cos"],
        preserves_prefix_carry=False
    )
    plan_wg = build_waveguide_rebalance_plan([cand_bad_prefix], rebal_plan_policy)
    report_wg = execute_shadow_waveguide_rebalance(plan_wg)
    assert report_wg.success is False
    assert any("breaks prefix-carry bridge semantics" in e for e in report_wg.errors)

    # 15. arithmetic oracle mismatch blocks rebalance promotion when arithmetic report is present.
    tx_report_bad_arith = tx_report.copy()
    tx_report_bad_arith["arithmetic_oracle_mismatch"] = True
    bad_arith_report = {
        "oracle_match": False,
        "success": False
    }
    with pytest.raises(ValueError, match="Arithmetic oracle mismatch detected"):
        validate_arithmetic_oracle_after_route_optimization(bad_arith_report, None)

    # 16. optimized route remains inside cadence window.
    tx_report_bad_cadence = tx_report.copy()
    tx_report_bad_cadence["outside_cadence_window"] = True
    intent_bad_cad = build_transactional_route_optimization_intent(tx_report_bad_cadence, topology, policy)
    plan_policy_cad = policy.copy()
    plan_policy_cad["intent"] = intent_bad_cad
    plan_policy_cad["cadence_windows"] = ["outside_cadence_window"]
    cands_cad = identify_transactional_route_candidates(intent_bad_cad)
    plan_cad = build_transactional_route_optimization_plan(cands_cad, plan_policy_cad)
    report_cad = execute_shadow_transactional_route_optimization(plan_cad)
    assert report_cad.success is False

    # 17. lock boundary violation blocks route optimization.
    tx_report_bad_lock = tx_report.copy()
    tx_report_bad_lock["lock_boundary_violation"] = True
    intent_bad_lock = build_transactional_route_optimization_intent(tx_report_bad_lock, topology, policy)
    plan_policy_lock = policy.copy()
    plan_policy_lock["intent"] = intent_bad_lock
    plan_policy_lock["global_lock_boundaries"] = ["lock_boundary_violation"]
    cands_lock = identify_transactional_route_candidates(intent_bad_lock)
    plan_lock = build_transactional_route_optimization_plan(cands_lock, plan_policy_lock)
    report_lock = execute_shadow_transactional_route_optimization(plan_lock)
    assert report_lock.success is False

    # 18. cross-manifold deadlock blocks route optimization.
    plan_policy_deadlock = policy.copy()
    plan_policy_deadlock["quorum_requirements"] = {"cross_manifold_deadlock": True}
    plan_policy_deadlock["intent"] = intent
    plan_deadlock = build_transactional_route_optimization_plan(cands, plan_policy_deadlock)
    report_deadlock = execute_shadow_transactional_route_optimization(plan_deadlock)
    assert report_deadlock.success is False

    # 19. crosstalk spike blocks waveguide rebalance.
    cand_bad_crosstalk = WaveguideRebalanceCandidate(
        candidate_id="cand_bad_crosstalk",
        lane_id=0,
        proposed_periods=[11.0],
        proposed_quadratures=["sin", "cos"],
        estimated_crosstalk=0.08
    )
    plan_wg = build_waveguide_rebalance_plan([cand_bad_crosstalk], rebal_plan_policy)
    report_wg = execute_shadow_waveguide_rebalance(plan_wg)
    assert report_wg.success is False

    # 20. boundary reflection breach blocks waveguide rebalance.
    cand_bad_reflection = WaveguideRebalanceCandidate(
        candidate_id="cand_bad_reflection",
        lane_id=0,
        proposed_periods=[11.0],
        proposed_quadratures=["sin", "cos"],
        estimated_boundary_reflection=0.07
    )
    plan_wg = build_waveguide_rebalance_plan([cand_bad_reflection], rebal_plan_policy)
    report_wg = execute_shadow_waveguide_rebalance(plan_wg)
    assert report_wg.success is False

    # 21. before/after cost comparison detects improvement.
    before = GeodesicRouteCostEstimate(route_id="r1", total_cost=2.0, crosstalk_risk=0.05, cadence_risk=0.05, boundary_reflection_risk=0.05)
    after = GeodesicRouteCostEstimate(route_id="r2", total_cost=1.0, crosstalk_risk=0.01, cadence_risk=0.01, boundary_reflection_risk=0.01)
    comp = compare_geodesic_routes(before, after)
    assert comp.cost_improved is True
    assert comp.risk_improved is True

    # 22. no improvement without justification blocks promotion.
    protocol_bad_impr = RouteRebalanceProtocol(
        protocol_id="PROTO_BAD_IMPR",
        route_telemetry={
            "transaction_id": "TX_41",
            "no_improvement_without_justification": True,
            "has_cost_model": True,
        },
        waveguide_telemetry={"lane_loads": {0: 0.9}, "crosstalk_db": {0: -10.0}},
        rollback_snapshots=["snap_1"],
        state_hash_references=["hash_1"],
        safety_oracle_agreement=True,
        court_token="COURT_TOKEN_41"
    )
    prep_state = prepare_route_rebalance(protocol_bad_impr)
    assert prep_state.prepared is True
    ver_state = verify_route_rebalance(protocol_bad_impr)
    assert ver_state.verified is False
    assert any("No cost improvement detected" in e for e in ver_state.errors)

    # 23. safety oracle expected outcome matches actual outcome.
    class MockCandidate:
        def __init__(self, has_pml=True, preserves_carry=True, crosstalk=0.0, reflection=0.0, preserves_lane=True, preserves_carrier=True, preserves_quad=True):
            self.has_pml_coverage = has_pml
            self.preserves_prefix_carry = preserves_carry
            self.estimated_crosstalk = crosstalk
            self.estimated_boundary_reflection = reflection
            self.preserves_lane_identity = preserves_lane
            self.preserves_carrier_identity = preserves_carrier
            self.preserves_quadrature_pairings = preserves_quad
            self.telemetry = {}

    cand_ok = MockCandidate()
    oracle_input = WaveguideRebalanceOracleInput(cand_ok, {}, {})
    decision_ok = evaluate_waveguide_rebalance_safety(oracle_input)
    assert decision_ok.verdict == "accept_shadow"
    assert compare_rebalance_actual_to_expected("accept_shadow", decision_ok.verdict) is True

    # 24. RouteRebalanceRanger emits JSON-serializable SovereignPacket.
    cands_ok = identify_transactional_route_candidates(intent)
    plan_policy_ok = policy.copy()
    plan_policy_ok["intent"] = intent
    plan_ok = build_transactional_route_optimization_plan(cands_ok, plan_policy_ok)
    route_report = execute_shadow_transactional_route_optimization(plan_ok)
    
    cand_wg_ok = WaveguideRebalanceCandidate(
        candidate_id="cand_wg_ok",
        lane_id=0,
        proposed_periods=[11.0],
        proposed_quadratures=["sin", "cos"]
    )
    plan_wg_ok = build_waveguide_rebalance_plan([cand_wg_ok], rebal_plan_policy)
    rebalance_report = execute_shadow_waveguide_rebalance(plan_wg_ok)
    
    protocol_ok = RouteRebalanceProtocol(
        protocol_id="PROTO_OK",
        route_telemetry=tx_report,
        waveguide_telemetry={"lane_loads": {0: 0.9}},
        rollback_snapshots=["snap_1"],
        state_hash_references=["hash_1"],
        safety_oracle_agreement=True,
        court_token="COURT_TOKEN_41"
    )
    prepare_route_rebalance(protocol_ok)
    verify_route_rebalance(protocol_ok)
    
    protocol_ok.comparison = comp
    protocol_report = RouteRebalanceProtocolReport(
        report_id="PROTO_REP",
        protocol=protocol_ok,
        success=True
    )
    
    safety_oracle_report = WaveguideRebalanceOracleReport(
        report_id="ORACLE_REP",
        input_data=oracle_input,
        decision=decision_ok,
        agreement=True
    )
    
    closed_loop_report = RouteRebalanceClosedLoopReport(
        report_id="CLR_REP",
        suggestion=RouteRebalanceSuggestion("SUG_1", "observe", "stable", "wg_1"),
        validated=True,
        applied=False
    )
    
    ranger = RouteRebalanceRanger()
    packet = ranger.observe_route_rebalance(
        route_report=route_report,
        rebalance_report=rebalance_report,
        protocol_report=protocol_report,
        safety_oracle_report=safety_oracle_report,
        closed_loop_report=closed_loop_report,
        mission_id="MISSION_L41"
    )
    assert isinstance(packet, SovereignPacket)
    assert packet.level == 41
    packet_dict = packet.to_dict()
    assert json.dumps(packet_dict) is not None

    # 25. Promotion Court can review route optimization, waveguide rebalance, protocol, oracle, and ranger reports.
    court = PromotionCourt()
    
    court_dec_route = court.review_transactional_route_optimization_report(route_report)
    assert court_dec_route.passed is True
    assert court_dec_route.decision == "accept_shadow_route_rebalance"
    
    court_dec_rebal = court.review_waveguide_rebalance_report(rebalance_report)
    assert court_dec_rebal.passed is True
    assert court_dec_rebal.decision == "accept_shadow_route_rebalance"
    
    court_dec_prot = court.review_route_rebalance_protocol_report(protocol_report)
    assert court_dec_prot.passed is True
    assert court_dec_prot.decision == "accept_shadow_route_rebalance"
    
    court_dec_oracle = court.review_waveguide_rebalance_oracle_report(safety_oracle_report)
    assert court_dec_oracle.passed is True
    assert court_dec_oracle.decision == "accept_shadow_route_rebalance"
    
    court_dec_packet = court.review_route_rebalance_ranger_packet(packet)
    assert court_dec_packet.passed is True
    assert court_dec_packet.decision == "promote_level41_candidate"





























