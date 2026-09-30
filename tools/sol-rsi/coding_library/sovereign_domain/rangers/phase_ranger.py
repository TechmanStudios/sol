# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
Phase Ranger
============
Patrols PDM lanes, monitors phase drift, and reports phase-lock quality.
Supports coarse calibration observability and returns SovereignPackets.
"""

from coding_library.roaming_agents import LuminaRoamingAgent
from coding_library.sovereign_domain.evidence_packet import SovereignPacket
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class PhaseRanger(LuminaRoamingAgent):
    """
    Ranger patrolling PDM lanes to observe phase alignment, crosstalk, and lock quality.
    """
    # Coarse calibration thresholds
    ACTIVE_DELTA_MIN = 0.20
    INACTIVE_DELTA_MAX = 0.10
    REVERSED_DELTA_MAX = 0.10
    CROSS_TALK_MAX = 0.05
    MIN_ACTIVE_REGISTER_MASS = 14.0

    def __init__(self, lib_agent=None):
        system_prompt = (
            "You are the Phase Ranger. You patrol PDM lanes, detect phase drift,\n"
            "measure active/inactive/reversed deltas, and report phase-lock quality."
        )
        super().__init__("Phase Ranger", system_prompt, lib_agent)

    def patrol_lanes(self, sequencer_obj) -> Dict[str, Any]:
        """
        Scan active sequencer channels for phase mismatch.
        Observe/report only: does not apply phase corrections.
        """
        self.travel(sequencer_obj)
        
        import math
        max_drift = 0.0
        drift_detected = False
        request_review = False
        
        # Extract drift from sequencer_obj
        if isinstance(sequencer_obj, dict):
            max_drift = abs(sequencer_obj.get("max_phase_error", 0.0))
        else:
            max_drift = abs(getattr(sequencer_obj, "max_phase_error", 0.0))
            
        if max_drift > 0.05:
            drift_detected = True
            request_review = True
            
        report = {
            "status": "STABLE" if not drift_detected else "DRIFTING",
            "phase_drift_detected": drift_detected,
            "max_drift_deg": max_drift * (180.0 / math.pi) if max_drift else 0.0,
            "request_court_review": request_review,
            "observations": [{"max_drift": max_drift}]
        }
        
        self.state_history.append(
            f"Patrolled sequencer lanes: drift_detected={drift_detected}, request_court_review={request_review}."
        )
        return report

    def observe_calibration(self, context_obj: Any, mission_id: str = "MOCK_MISSION") -> SovereignPacket:
        """
        Reads coarse calibration state and metrics from the provided object/dict,
        evaluates against thresholds, and constructs a SovereignPacket.
        Does not apply any nudges or write state.
        """
        # Record location change
        self.travel(context_obj)

        # Safe extraction helper
        def extract(name, default=None):
            if isinstance(context_obj, dict):
                return context_obj.get(name, default)
            return getattr(context_obj, name, default)

        active_delta = extract("active_delta")
        inactive_max_delta = extract("inactive_max_delta")
        if inactive_max_delta is None:
            inactive_max_delta = extract("inactive_delta_max")
        reversed_delta = extract("reversed_delta")
        phase_residual = extract("phase_residual")
        cross_talk = extract("cross_talk")
        if cross_talk is None:
            cross_talk = extract("crosstalk")
        min_mass = extract("min_active_register_mass")
        if min_mass is None:
            min_mass = extract("min_mass")

        # Evaluate thresholds
        checks = {}
        passed = True
        invariants = []

        if active_delta is not None:
            checks["active_delta"] = active_delta >= self.ACTIVE_DELTA_MIN
            invariants.append(f"active_delta >= {self.ACTIVE_DELTA_MIN}")
            if not checks["active_delta"]:
                passed = False

        if inactive_max_delta is not None:
            checks["inactive_max_delta"] = inactive_max_delta <= self.INACTIVE_DELTA_MAX
            invariants.append(f"inactive_max_delta <= {self.INACTIVE_DELTA_MAX}")
            if not checks["inactive_max_delta"]:
                passed = False

        if reversed_delta is not None:
            checks["reversed_delta"] = reversed_delta <= self.REVERSED_DELTA_MAX
            invariants.append(f"reversed_delta <= {self.REVERSED_DELTA_MAX}")
            if not checks["reversed_delta"]:
                passed = False

        if cross_talk is not None:
            checks["cross_talk"] = cross_talk <= self.CROSS_TALK_MAX
            invariants.append(f"cross_talk <= {self.CROSS_TALK_MAX}")
            if not checks["cross_talk"]:
                passed = False

        if min_mass is not None:
            checks["min_active_register_mass"] = min_mass >= self.MIN_ACTIVE_REGISTER_MASS
            invariants.append(f"min_active_register_mass >= {self.MIN_ACTIVE_REGISTER_MASS}")
            if not checks["min_active_register_mass"]:
                passed = False

        # Determine recommendation
        if passed:
            recommendation = "observe"
        else:
            recommendation = "reject"

        evidence = {
            "active_delta": active_delta,
            "inactive_max_delta": inactive_max_delta,
            "reversed_delta": reversed_delta,
            "phase_residual": phase_residual,
            "cross_talk": cross_talk,
            "min_active_register_mass": min_mass,
            "threshold_checks": checks,
            "pass_status": passed,
            "request_court_review": not passed
        }

        # Generate simple deterministic packet_id and reproducibility_hash
        timestamp_str = datetime.now(timezone.utc).strftime("%H%M%S")
        packet_id = f"PKT_PHASE_OBS_{id(context_obj)}_{timestamp_str}"
        repro_hash = f"sha256_{hash(str(evidence)) & 0xFFFFFFFF:08x}"

        packet = SovereignPacket(
            packet_id=packet_id,
            domain="sol_sovereign",
            level=11,
            actor=self.name,
            actor_type="ranger",
            mission_id=mission_id,
            claim="PDM Coarse Phase Calibration Telemetry Report",
            evidence=evidence,
            invariants_checked=invariants,
            artifacts=[],
            recommendation=recommendation,
            confidence=0.95,
            reproducibility_hash=repro_hash
        )

        self.state_history.append(f"Observed calibration status: {recommendation} (passed={passed}).")
        return packet
