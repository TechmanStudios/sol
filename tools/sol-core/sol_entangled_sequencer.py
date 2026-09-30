# Copyright (c) 2026 Techman Studios.
# Licensed under the GNU Affero General Public License v3.0 or later.
# See LICENSE in the repository root for details.
"""
SOL Entangled Sequencers
========================
Scaffolds state snapshotting, state comparison, and coherence synchronization
telemetry across multiple entangled sequencers.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import hashlib

@dataclass
class EntangledSequencerState:
    sequencer_id: str
    step: int
    active_instruction_id: str
    phase: float
    mass: float
    state_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledSequencerPair:
    pair_id: str
    seq_a_id: str
    seq_b_id: str
    coherence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EntangledSequencerGroup:
    group_id: str
    sequencers: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SequencerSyncObservation:
    observation_id: str
    sequencer_ids: List[str]
    coherence_levels: Dict[str, float]
    drift_levels: Dict[str, float]
    timestamp: float = field(default_factory=time.time)

@dataclass
class SequencerSyncReport:
    report_id: str
    group_coherence: float
    max_drift: float
    synchronized: bool
    reproducibility_hash: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


def snapshot_sequencer_state(sequencer: Any) -> EntangledSequencerState:
    """
    Captures a snapshot state of the given sequencer or mock representation.
    """
    def extract(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)
        
    seq_id = extract(sequencer, "sequencer_id") or extract(sequencer, "name") or f"SEQ_{id(sequencer)}"
    step = extract(sequencer, "step", 0)
    active_inst = extract(sequencer, "active_instruction_id", "none")
    phase = extract(sequencer, "phase", 0.02)
    mass = extract(sequencer, "mass", 100.0)
    
    # Calculate a simple state hash
    ev_str = f"{seq_id}_{step}_{phase:.4f}_{mass:.4f}"
    state_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
    
    return EntangledSequencerState(
        sequencer_id=seq_id,
        step=step,
        active_instruction_id=active_inst,
        phase=phase,
        mass=mass,
        state_hash=state_hash
    )


def compare_sequencer_states(
    source_state: EntangledSequencerState,
    target_state: EntangledSequencerState
) -> float:
    """
    Compares the phase metrics of two sequencers to calculate coherence.
    """
    phase_diff = abs(source_state.phase - target_state.phase)
    coherence = max(0.0, min(1.0, 1.0 - phase_diff))
    return coherence


def measure_group_coherence(
    group_states: List[EntangledSequencerState]
) -> float:
    """
    Calculates minimum phase coherence among a group of sequencers.
    """
    if not group_states:
        return 0.0
    if len(group_states) == 1:
        return 1.0
        
    min_coherence = 1.0
    for i in range(len(group_states)):
        for j in range(i + 1, len(group_states)):
            coh = compare_sequencer_states(group_states[i], group_states[j])
            if coh < min_coherence:
                min_coherence = coh
    return min_coherence


def build_sync_report(
    group_states: List[EntangledSequencerState],
    tolerance: float = 0.05
) -> SequencerSyncReport:
    """
    Constructs a SequencerSyncReport evaluating synchronization metrics.
    """
    if not group_states:
        return SequencerSyncReport(
            report_id="RPT_SYNC_EMPTY",
            group_coherence=0.0,
            max_drift=1.0,
            synchronized=False,
            reproducibility_hash="none",
            timestamp=time.time()
        )
        
    coherence = measure_group_coherence(group_states)
    
    # Max phase drift is maximum phase diff from the average phase
    phases = [s.phase for s in group_states]
    avg_phase = sum(phases) / len(phases) if phases else 0.0
    max_drift = max(abs(p - avg_phase) for p in phases) if phases else 0.0
    
    synchronized = (coherence >= (1.0 - tolerance))
    
    report_id = f"RPT_SYNC_{int(time.time())}"
    
    # Generate reproducibility hash
    try:
        ev_str = f"{coherence:.4f}_{max_drift:.4f}_{synchronized}"
        repro_hash = "sha256_" + hashlib.sha256(ev_str.encode('utf-8')).hexdigest()[:8]
    except Exception:
        repro_hash = "sha256_fallback"
        
    return SequencerSyncReport(
        report_id=report_id,
        group_coherence=coherence,
        max_drift=max_drift,
        synchronized=synchronized,
        reproducibility_hash=repro_hash,
        timestamp=time.time(),
        metadata={"num_sequencers": len(group_states)}
    )
