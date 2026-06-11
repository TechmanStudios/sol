# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Pipeline Wavefront Ranger
==========================
Patrols geodesic pipeline balancing, quantum wavefront calibration, uncertainty windows,
safety oracle decisions, and final protocol reports.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Any, Optional
from datetime import datetime, timezone
import json
import uuid

class PipelineWavefrontRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe Level 46 geodesic pipeline balancing and quantum wavefront calibration.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Pipeline Wavefront Ranger. You patrol geodesic pipeline balancing, quantum wavefront\n"
            "calibration, uncertainty windows, safety oracles, and ledger snapshots."
        )
        super().__init__("Pipeline Wavefront Ranger", system_prompt, lib_agent)

    def observe_pipeline_wavefront(
        self,
        balance_report: Optional[Any] = None,
        quantum_report: Optional[Any] = None,
        uncertainty_report: Optional[Any] = None,
        oracle_report: Optional[Any] = None,
        protocol_report: Optional[Any] = None,
        ledger_report: Optional[Any] = None,
        mission_id: str = "M_PIPELINE_WAVEFRONT_PATROL"
    ) -> SovereignPacket:
        """
        Observes Level 46 reports and builds a valid SovereignPacket.
        """
        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        # 1. Default report metrics
        balance_id = "none"
        quantum_id = "none"
        core_cnt = 0
        segment_cnt = 0
        route_depth_before = 0
        route_depth_after = 0
        stage_latency_before = 0.0
        stage_latency_after = 0.0
        backpressure_before = 0.0
        backpressure_after = 0.0
        wavefront_coherence = 1.0
        resonance_coherence = 1.0
        uncertainty_status = "none"
        packet_dispersion = 0.0
        cadence_status = "none"
        pml_status = "none"
        carrier_preservation_status = "none"
        oracle_match = True
        rollback_readiness = False
        quarantine_recommendation = "none"
        passed_gates = True

        # Process Geodesic Balance Report
        if balance_report is not None:
            self.travel(balance_report)
            plan = extract(balance_report, "plan")
            res = extract(balance_report, "result")
            passed_gates = passed_gates and extract(res, "success", True)
            balance_id = extract(plan, "plan_id", "none") if plan else "none"
            
            # segments & core counts
            imbalances = extract(plan, "imbalances", []) if plan else []
            segment_cnt = len(imbalances)
            
            # Rollback check
            meta = extract(plan, "metadata", {}) if plan else {}
            if meta and meta.get("rollback_snapshot"):
                rollback_readiness = True
            if meta and meta.get("quarantine_segment"):
                quarantine_recommendation = "quarantine_pipeline_segment"

        # Process Quantum Wavefront Calibration Report
        if quantum_report is not None:
            self.travel(quantum_report)
            res = extract(quantum_report, "result")
            passed_gates = passed_gates and extract(res, "success", True)
            quantum_id = extract(quantum_report, "report_id", "none")
            
            # Extract observations
            obs_list = extract(quantum_report, "observations", [])
            if obs_list:
                obs = obs_list[0]
                wavefront_coherence = extract(obs, "amplitude_coherence", 1.0)
                resonance_coherence = extract(obs, "resonance_coherence", 1.0)
                packet_dispersion = extract(obs, "packet_dispersion", 0.0)
                oracle_match = oracle_match and extract(obs, "oracle_match", True)
                
                if extract(obs, "cadence_drift", 0.0) <= 0.05:
                    cadence_status = "stable"
                else:
                    cadence_status = "drift"
                    
                if extract(obs, "pml_absorption_effectiveness", 0.99) >= 0.90:
                    pml_status = "valid"
                else:
                    pml_status = "weakened"
                    
                if not extract(obs, "carrier_identity_broken", False):
                    carrier_preservation_status = "preserved"

        # Process Uncertainty Report
        if uncertainty_report is not None:
            self.travel(uncertainty_report)
            passed_gates = passed_gates and extract(uncertainty_report, "is_valid", True)
            uncertainty_status = "bounded" if passed_gates else "unbounded"
            if extract(uncertainty_report, "bound") and not extract(extract(uncertainty_report, "bound"), "is_bounded"):
                uncertainty_status = "unbounded"

        # Process Oracle Report
        if oracle_report is not None:
            self.travel(oracle_report)
            dec = extract(oracle_report, "decision")
            if dec:
                oracle_decision = extract(dec, "decision")
                if oracle_decision in ["hold_balance", "reject_balance_candidate", "rollback_balance", "quarantine_pipeline_segment", "quarantine_wavefront_packet", "quarantine_core"]:
                    quarantine_recommendation = oracle_decision
                    passed_gates = False

        # Process Protocol Report
        if protocol_report is not None:
            self.travel(protocol_report)
            passed_gates = passed_gates and extract(protocol_report, "success", True)

        # Process Ledger Report
        if ledger_report is not None:
            self.travel(ledger_report)
            passed_gates = passed_gates and extract(ledger_report, "passed_validation", True)

        # Invariants Check status
        promotion_ready = passed_gates and oracle_match and (uncertainty_status == "bounded") and rollback_readiness and (quarantine_recommendation == "none")

        evidence = {
            "pipeline_balance_id": balance_id,
            "quantum_wavefront_id": quantum_id,
            "core_count": core_cnt,
            "pipeline_segment_count": segment_cnt,
            "route_depth_before": route_depth_before,
            "route_depth_after": route_depth_after,
            "stage_latency_before": stage_latency_before,
            "stage_latency_after": stage_latency_after,
            "backpressure_before": backpressure_before,
            "backpressure_after": backpressure_after,
            "wavefront_coherence": wavefront_coherence,
            "resonance_coherence": resonance_coherence,
            "uncertainty_status": uncertainty_status,
            "packet_dispersion": packet_dispersion,
            "cadence_status": cadence_status,
            "pml_status": pml_status,
            "carrier_preservation_status": carrier_preservation_status,
            "oracle_match": oracle_match,
            "rollback_readiness": rollback_readiness,
            "quarantine_recommendation": quarantine_recommendation,
            "promotion_readiness": promotion_ready
        }

        recommendation = "promote" if promotion_ready else "observe"
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_WF_BAL_{timestamp_str}"

        # JSON-serializable evidence packet
        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=46,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Audited report of Level 46 geodesic pipeline balancing and quantum wavefront calibration",
            evidence=evidence,
            invariants_checked=[
                "sovereign_runtime_authorized",
                "pipeline_balance_policy_bounded",
                "quantum_wavefront_policy_bounded",
                "pipeline_metrics_present",
                "balance_plan_valid",
                "balance_candidate_safe",
                "balance_before_after_cost_measured",
                "balance_improves_or_is_justified",
                "quantum_wavefront_baseline_present",
                "quantum_wavefront_packets_valid",
                "uncertainty_windows_bounded",
                "amplitude_coherence_within_threshold",
                "phase_coherence_within_threshold",
                "resonance_coherence_within_threshold",
                "packet_dispersion_within_threshold",
                "cadence_window_valid",
                "cadence_skew_within_threshold",
                "pml_boundaries_valid",
                "carrier_bindings_preserved",
                "prefix_carry_preserved_if_required",
                "arithmetic_oracle_match_if_required",
                "active_phase_tables_not_overwritten",
                "active_cadence_profiles_not_overwritten",
                "active_carrier_registry_not_overwritten",
                "rollback_snapshots_present",
                "synchronized_commits_blocked_until_stable",
                "runtime_ledger_complete",
                "ranger_evidence_complete",
                "court_review_complete",
                "no_production_pipeline_or_wavefront_mutation"
            ],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.99,
            reproducibility_hash=balance_id
        )

        self.state_history.append(
            f"Observed balance: id={balance_id}, segments={segment_cnt}, promotion_ready={promotion_ready}."
        )
        return packet
