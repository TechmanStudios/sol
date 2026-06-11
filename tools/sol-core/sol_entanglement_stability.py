# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Entanglement Stability Guard
================================
Scaffolds deterministic phase coherence measuring and stability verification
gates for cross-manifold transfers.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time
import hashlib

@dataclass
class EntanglementLink:
    link_id: str
    source_node_id: str
    target_node_id: str
    coherence: float = 1.0
    phase_offset: float = 0.0

@dataclass
class EntanglementObservation:
    observation_id: str
    link: EntanglementLink
    phase_coherence: float
    transfer_drift: float
    timestamp: float = field(default_factory=time.time)

@dataclass
class EntanglementStabilityReport:
    report_id: str
    observation_id: str
    phase_coherence: float
    transfer_drift: float
    stable: bool
    decision: str  # "stable", "needs_more_evidence", "quarantine_route", "rollback_recommended", "reject_transfer"
    reproducibility_hash: str
    timestamp: float

@dataclass
class EntanglementGuardDecision:
    decision: str
    reason: str
    rollback_recommended: bool
    quarantine_route: bool


def measure_phase_coherence(source_state: Any, target_state: Any) -> float:
    """
    Computes a deterministic phase coherence score between source and target manifold states.
    """
    def extract_phase(state):
        if isinstance(state, dict):
            return state.get("phase", 0.0)
        return getattr(state, "phase", 0.0)
        
    src_phase = extract_phase(source_state)
    tgt_phase = extract_phase(target_state)
    
    # Coherence = 1.0 - abs(phase error), bounded to [0.0, 1.0]
    return max(0.0, min(1.0, 1.0 - abs(src_phase - tgt_phase)))


def measure_transfer_drift(before_state: Any, after_state: Any) -> float:
    """
    Measures the drift in manifold state before and after the transfer.
    """
    def extract_val(state):
        if isinstance(state, dict):
            # Try getting value first, then phase
            val = state.get("value")
            if val is None:
                val = state.get("phase", 0.0)
            return val
        val = getattr(state, "value", None)
        if val is None:
            val = getattr(state, "phase", 0.0)
        return val
        
    before_val = extract_val(before_state)
    after_val = extract_val(after_state)
    
    return abs(before_val - after_val)


def check_entanglement_stability(
    observation: EntanglementObservation,
    tolerance: float = 0.05
) -> EntanglementStabilityReport:
    """
    Verifies that the entanglement link matches the required coherence and drift tolerances.
    """
    coherence = observation.phase_coherence
    drift = observation.transfer_drift
    
    # Requirement: coherence > 0.90 and drift < tolerance
    stable = (coherence > 0.90) and (drift < tolerance)
    
    # Map decision
    if stable:
        decision = "stable"
    elif drift >= 0.30 or coherence < 0.50:
        decision = "reject_transfer"
    elif drift >= 0.15 or coherence < 0.70:
        decision = "quarantine_route"
    elif drift >= 0.08 or coherence < 0.85:
        decision = "rollback_recommended"
    else:
        decision = "needs_more_evidence"
        
    # Generate reproducibility hash
    ev_str = f"{observation.observation_id}_{coherence:.4f}_{drift:.4f}_{stable}"
    repro_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
    
    return EntanglementStabilityReport(
        report_id=f"RPT_STABILITY_{observation.observation_id}",
        observation_id=observation.observation_id,
        phase_coherence=coherence,
        transfer_drift=drift,
        stable=stable,
        decision=decision,
        reproducibility_hash=repro_hash,
        timestamp=observation.timestamp
    )


def guard_transfer(report: EntanglementStabilityReport) -> EntanglementGuardDecision:
    """
    Enforces gate controls based on stability report verdicts.
    """
    dec = report.decision
    
    rollback = dec in ("rollback_recommended", "reject_transfer", "quarantine_route")
    quarantine = dec == "quarantine_route"
    
    reason_map = {
        "stable": "Entanglement link is highly coherent and stable.",
        "needs_more_evidence": "Slight variance detected, requiring more evidence.",
        "rollback_recommended": "Stability thresholds breached, rollback is recommended.",
        "quarantine_route": "High drift detected, route quarantine is recommended.",
        "reject_transfer": "Critical drift or coherence breach detected, reject transfer execution."
    }
    
    reason = reason_map.get(dec, "Unknown state.")
    
    return EntanglementGuardDecision(
        decision=dec,
        reason=reason,
        rollback_recommended=rollback,
        quarantine_route=quarantine
    )
