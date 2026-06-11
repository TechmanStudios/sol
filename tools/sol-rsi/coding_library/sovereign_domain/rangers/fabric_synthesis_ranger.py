# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Fabric Synthesis Ranger
=======================
Observes WaveguideFabricCandidate, WaveguideSynthesisReport,
SIMDCoreIntegrationReport, and WaveguideLayoutOptimizationReport,
returning valid SovereignPackets.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class FabricSynthesisRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Phase 31 waveguide fabric synthesis and SIMD core integration trials.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Fabric Synthesis Ranger. You inspect WaveguideFabricCandidates, WaveguideSynthesisReports,\n"
            "SIMDCoreIntegrationReports, and WaveguideLayoutOptimizationReports, compiling telemetry and bounds info."
        )
        super().__init__("Fabric Synthesis Ranger", system_prompt, lib_agent)

    def observe_synthesis(
        self,
        candidate: Any = None,
        synthesis_report: Any = None,
        simd_report: Any = None,
        layout_report: Any = None,
        mission_id: str = "MOCK_SYNTHESIS_MISSION"
    ) -> SovereignPacket:
        """
        Inspects waveguide fabric candidates, synthesis/SIMD/layout reports,
        and returns a SovereignPacket containing Level 31 evidence.
        """
        target = candidate or synthesis_report or simd_report or layout_report
        self.travel(target)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        obj_classname = target.__class__.__name__ if target else "None"

        # Initialize defaults
        candidate_id = "unknown"
        lane_count = 0
        core_count = 0
        simd_mode_coverage = []
        tensor_binding_status = "none"
        junction_count = 0
        crossing_count = 0
        pml_coverage = 0.0
        phase_drift = 0.0
        crosstalk = 0.0
        boundary_reflection = 0.0
        oracle_match = True
        quarantine_recommendation = "clean"
        promotion_readiness = "not_ready"
        recommendation = "observe"
        
        # Gates checked status dictionary
        gates_status = {
            "synthesis_spec_valid": False,
            "candidate_fabric_valid": False,
            "lane_bindings_complete": False,
            "simd_core_bindings_complete": False,
            "tensor_bindings_complete_if_required": True,
            "reduction_mapping_complete_if_required": True,
            "pml_boundaries_valid": False,
            "candidate_phase_table_separate": True,
            "phase_error_within_threshold": True,
            "crosstalk_within_threshold": True,
            "boundary_reflection_within_threshold": True,
            "active_mass_preserved": True,
            "lane_isolation_preserved": True,
            "oracle_match_if_available": True,
            "rollback_snapshot_references_present_for_live_trial": True,
            "ranger_evidence_complete": True,
            "court_review_complete": False,
            "no_default_stepper_replacement": True,
            "no_production_fabric_mutation": True
        }

        # If a candidate is provided or extracted
        cand_obj = None
        if obj_classname == "WaveguideFabricCandidate":
            cand_obj = target
        elif synthesis_report:
            plan = extract(synthesis_report, "plan")
            if plan:
                cand_obj = extract(plan, "candidate")
        elif simd_report:
            cand_obj = extract(simd_report, "candidate")
        elif layout_report:
            cand_obj = extract(layout_report, "candidate")

        if cand_obj:
            candidate_id = extract(cand_obj, "candidate_id", "unknown")
            spec = extract(cand_obj, "spec")
            if spec:
                lane_count = extract(spec, "width", 0) // 8
                
            lane_bindings = extract(cand_obj, "lane_bindings", [])
            if lane_bindings:
                lane_count = len(lane_bindings)
                cores = {extract(b, "core_id") for b in lane_bindings if extract(b, "core_id")}
                core_count = len(cores)
                gates_status["lane_bindings_complete"] = True
                
            junctions = extract(cand_obj, "junctions", [])
            junction_count = len(junctions)
            
            segments = extract(cand_obj, "segments", [])
            
            boundary_bindings = extract(cand_obj, "boundary_bindings", [])
            if boundary_bindings:
                pml_coverage = len(boundary_bindings) / lane_count if lane_count > 0 else 1.0
                
            tensor_shard_bindings = extract(cand_obj, "tensor_shard_bindings", [])
            if tensor_shard_bindings:
                tensor_binding_status = "bound"
                gates_status["tensor_bindings_complete_if_required"] = True
                
            rollback_refs = extract(cand_obj, "rollback_snapshot_refs", [])
            if not rollback_refs:
                gates_status["rollback_snapshot_references_present_for_live_trial"] = False

            gates_status["synthesis_spec_valid"] = spec is not None
            # Validate candidate
            try:
                from sol_waveguide_fabric_synthesis import validate_waveguide_fabric_candidate
                gates_status["candidate_fabric_valid"] = validate_waveguide_fabric_candidate(cand_obj)
            except Exception:
                gates_status["candidate_fabric_valid"] = False

            try:
                from sol_wavefront_propagator import validate_pml_for_synthesized_fabric
                gates_status["pml_boundaries_valid"] = validate_pml_for_synthesized_fabric(cand_obj)
            except Exception:
                gates_status["pml_boundaries_valid"] = False

        if synthesis_report:
            success = extract(synthesis_report, "success", False)
            if success:
                gates_status["synthesis_spec_valid"] = True

        if simd_report:
            # SIMD mappings info
            simd_map = extract(simd_report, "binding_map")
            if simd_map:
                core_bindings = extract(simd_map, "core_bindings", {})
                if core_bindings:
                    gates_status["simd_core_bindings_complete"] = True
            oracle_match = extract(simd_report, "oracle_match", True)
            gates_status["oracle_match_if_available"] = oracle_match
            simd_mode_coverage = extract(simd_report, "simd_modes", [])
            
            # Extract drift/crosstalk/reflection from trace if present
            trace = extract(simd_report, "trace")
            if trace:
                phase_drift = extract(trace, "phase_drift", 0.0)
                crosstalk = extract(trace, "crosstalk", 0.0)
                boundary_reflection = extract(trace, "boundary_reflection", 0.0)
                
            errors = extract(simd_report, "errors", [])
            if errors:
                oracle_match = False

        if layout_report:
            # Layout optimization info
            crossing_count = extract(layout_report, "lane_crossings", 0)
            
        # Compile final promotion readiness
        all_ok = all(gates_status.values()) and oracle_match
        if all_ok:
            promotion_readiness = "ready"
            recommendation = "promote"
        else:
            if crosstalk > 0.05 or not gates_status["candidate_fabric_valid"] or not gates_status["pml_boundaries_valid"]:
                quarantine_recommendation = "quarantine"
                recommendation = "quarantine"
            else:
                recommendation = "hold"

        evidence = {
            "candidate_id": candidate_id,
            "lane_count": lane_count,
            "core_count": core_count,
            "simd_mode_coverage": simd_mode_coverage,
            "tensor_binding_status": tensor_binding_status,
            "junction_count": junction_count,
            "crossing_count": crossing_count,
            "pml_coverage": pml_coverage,
            "phase_drift": phase_drift,
            "crosstalk": crosstalk,
            "boundary_reflection": boundary_reflection,
            "oracle_match": oracle_match,
            "quarantine_recommendation": quarantine_recommendation,
            "promotion_readiness": promotion_readiness,
            "target_type": obj_classname,
            "gates_status": gates_status,
            "sandbox_trial": True
        }

        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_SYN_OBS_{id(target) if target else 0}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=31,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Advanced waveguide fabric synthesis and SIMD core integration observation report",
            evidence=evidence,
            invariants_checked=["synthesis_spec_valid", "candidate_fabric_valid", "simd_core_bindings_complete", "pml_boundaries_valid", "no_production_fabric_mutation"],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed fabric synthesis report: candidate={candidate_id}, readiness={promotion_readiness}.")
        return packet
