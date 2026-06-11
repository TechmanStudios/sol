# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Drift Ranger
============
Observes PhaseDriftObservation and DispersionObservation, verifying drift bounds
and recommending advisory control actions.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class DriftRanger(LuminaRoamingAgent):
    """
    Ranger patrolling to observe phase drift and dispersion.
    """
    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Drift Ranger. You inspect phase drift observations and dispersion\n"
            "profiles, reporting on error margins and recommending stabilization actions."
        )
        super().__init__("Drift Ranger", system_prompt, lib_agent)

    def observe_drift(self, target_obj: Any, tolerance: float = 0.05, mission_id: str = "MOCK_DRIFT_MISSION") -> SovereignPacket:
        """
        Inspects a PhaseDriftObservation, DispersionObservation, or similar metric source,
        evaluates drift, and returns a SovereignPacket.
        """
        self.travel(target_obj)

        def extract(obj, name, default=None):
            if isinstance(obj, dict):
                return obj.get(name, default)
            return getattr(obj, name, default)

        lane_id = extract(target_obj, "lane_id", 0)
        
        # Determine if target is a phase drift observation or dispersion observation
        max_phase_err = extract(target_obj, "max_phase_error", None)
        
        max_delay = extract(target_obj, "max_delay", None)
        max_phase_shift = extract(target_obj, "max_phase_shift", None)
        
        if max_phase_err is not None:
            max_phase_err = abs(max_phase_err)
        else:
            # Fallback for dispersion observation where phase shift can represent drift
            max_phase_err = abs(max_phase_shift) if max_phase_shift is not None else 0.0

        drift_detected = max_phase_err > tolerance

        # Advisory action mapping
        if not drift_detected:
            rec_action = "observe"
            recommendation = "observe"
        elif max_phase_err <= 0.15:
            rec_action = "suggest_phase_nudge"
            recommendation = "patch"
        elif max_phase_err <= 0.30:
            rec_action = "suggest_damping_adjustment"
            recommendation = "quarantine"
        else:
            rec_action = "quarantine_lane"
            recommendation = "reject"

        evidence = {
            "lane_id": lane_id,
            "max_phase_error": max_phase_err,
            "tolerance": tolerance,
            "drift_detected": drift_detected,
            "recommended_action": rec_action,
            "request_court_review": drift_detected,
        }

        if max_delay is not None:
            evidence["max_delay"] = max_delay
        if max_phase_shift is not None:
            evidence["max_phase_shift"] = max_phase_shift

        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_DRIFT_OBS_{id(target_obj)}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=11,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="Waveguide phase drift and dispersion telemetry report",
            evidence=evidence,
            invariants_checked=["phase_drift_tolerance"],
            artifacts=[],
            recommendation=recommendation,
            confidence=0.96,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed drift: drift_detected={drift_detected}, action={rec_action}.")
        return packet
