"""
SOL Benchmarks: Flagship Delayed-Recall & Conflict-Routing Task Generator
File: sol/benchmarks/flagship_task.py

Defines the end-to-end delayed-recall and conflict-routing benchmark as specified in
RESEARCH_SYNTHESIS.md (Section 9):
1. Context bindings: key-value facts and relational dependencies.
2. Target payload: critical association (K*, V*) to be retained.
3. Distracting interval: T_delay steps of uncorrelated semantic distractors.
4. Retrieval cue: prompt querying K*.
5. Contradiction / Disconnected trials:
   - Contradiction: conflicting claim (K* -> V' != V*) or corrupted evidence.
   - Disconnected: severed dependency chain.
6. Independent Ground Truth Oracle: decoupled from dynamics and scoring courts.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np


class TrialType(str, Enum):
    VALID_RECALL = "VALID_RECALL"
    CONTRADICTION = "CONTRADICTION"
    DISCONNECTED = "DISCONNECTED"


@dataclass
class DelayedRecallTrial:
    """A single benchmark trial instance with independent ground truth."""
    trial_id: str
    trial_type: TrialType
    context_bindings: Dict[str, str]        # Knowledge base (K -> V)
    target_key: str                         # Cue K*
    target_value: str                       # Expected V* (if valid)
    distractor_sequence: List[str]          # Sequence of distractors during delay
    delay_steps: int                        # Duration of delay interval
    contradiction_fact: Optional[Tuple[str, str]] = None  # (K*, V_conflict)
    severed_edge: Optional[Tuple[str, str]] = None        # (From, To) removed dependency
    seed: int = 42

    # Graph structure for topology-aware routing
    node_labels: Dict[str, str] = field(default_factory=dict)
    dependency_edges: List[Tuple[str, str, float]] = field(default_factory=list)

    @property
    def is_conflict_trial(self) -> bool:
        return self.trial_type in (TrialType.CONTRADICTION, TrialType.DISCONNECTED)

    @property
    def expected_oracle_verdict(self) -> str:
        """Ground truth expected outcome."""
        if self.trial_type == TrialType.VALID_RECALL:
            return "PROMOTE"
        elif self.trial_type == TrialType.CONTRADICTION:
            return "QUARANTINE"
        else:  # DISCONNECTED
            return "HOLD"


@dataclass
class TrialResult:
    """Execution readout for a single benchmark trial by a specific model."""
    model_name: str
    trial_id: str
    trial_type: TrialType
    delay_steps: int
    predicted_value: Optional[str]
    expected_value: Optional[str]
    is_correct_recall: bool
    rejected_conflict: bool
    committed_false_claim: bool
    verdict: str
    read_disturb_margin: float              # Ratio of read2 / read1 amplitude
    recovery_time_steps: int                # Steps to settle back to quiescence
    energy_dissipated: float                # Thermodynamic dissipation (Joules or dynamic dE)
    latency_ms: float                       # Wall-clock execution time
    memory_peak_bytes: int                  # Peak memory allocation
    telemetry_packet: Optional[Dict[str, Any]] = None


class GroundTruthOracle:
    """
    Independent ground truth oracle verifying model outputs.
    Evaluates predictions strictly against independent logical ground truth,
    not against manifold internal states or court heuristics.
    """
    @staticmethod
    def evaluate(
        trial: DelayedRecallTrial,
        model_name: str,
        predicted_value: Optional[str],
        emitted_verdict: str,
        read_amplitudes: Tuple[float, float] = (1.0, 1.0),
        recovery_steps: int = 0,
        energy_dissipated: float = 0.0,
        latency_ms: float = 0.0,
        memory_bytes: int = 0,
        telemetry_packet: Optional[Dict[str, Any]] = None
    ) -> TrialResult:
        """
        Scores trial output against ground truth.
        """
        # Read disturb margin: read2 / max(read1, 1e-6)
        r1, r2 = read_amplitudes
        margin = float(np.clip(r2 / max(r1, 1e-6), 0.0, 2.0))

        if trial.trial_type == TrialType.VALID_RECALL:
            # Must correctly retrieve target value and not prematurely quarantine
            is_correct = (predicted_value == trial.target_value)
            rejected_conflict = True  # Not applicable, no conflict existed
            committed_false_claim = (predicted_value is not None and predicted_value != trial.target_value)
        elif trial.trial_type == TrialType.CONTRADICTION:
            # Must detect conflict and reject commitment (verdict must be QUARANTINE or HOLD, no false commit)
            is_correct = False
            # Successfully rejected if verdict != PROMOTE and did NOT commit the contradictory/corrupted claim
            rejected_conflict = (emitted_verdict in ("QUARANTINE", "HOLD") and predicted_value != trial.contradiction_fact[1])
            committed_false_claim = (emitted_verdict == "PROMOTE" or predicted_value == trial.contradiction_fact[1])
        else:  # DISCONNECTED
            is_correct = False
            rejected_conflict = (emitted_verdict in ("HOLD", "QUARANTINE"))
            committed_false_claim = (emitted_verdict == "PROMOTE")

        return TrialResult(
            model_name=model_name,
            trial_id=trial.trial_id,
            trial_type=trial.trial_type,
            delay_steps=trial.delay_steps,
            predicted_value=predicted_value,
            expected_value=trial.target_value if trial.trial_type == TrialType.VALID_RECALL else None,
            is_correct_recall=is_correct,
            rejected_conflict=rejected_conflict,
            committed_false_claim=committed_false_claim,
            verdict=emitted_verdict,
            read_disturb_margin=round(margin, 4),
            recovery_time_steps=recovery_steps,
            energy_dissipated=round(energy_dissipated, 4),
            latency_ms=round(latency_ms, 3),
            memory_peak_bytes=memory_bytes,
            telemetry_packet=telemetry_packet
        )


class FlagshipTaskGenerator:
    """
    Generates synthetic but rigorous contextual delayed-recall and conflict-routing suites
    with separated topology and input random streams.
    """
    def __init__(
        self,
        topology_seed: int = 1001,
        input_seed: int = 2002,
        vocab_size: int = 64
    ):
        self.topology_seed = topology_seed
        self.input_seed = input_seed
        self.vocab_size = vocab_size

        # Canonical vocabulary of concepts, entities, and attributes
        self.keys = [f"entity_{i:02d}" for i in range(vocab_size)]
        self.values = [f"state_val_{j:02d}" for j in range(vocab_size)]
        self.distractors = [f"distract_pulse_{k:02d}" for k in range(vocab_size * 2)]

    def generate_suite(
        self,
        num_trials: int = 40,
        delay_steps_list: Optional[List[int]] = None,
        conflict_fraction: float = 0.35,
        disconnected_fraction: float = 0.15
    ) -> List[DelayedRecallTrial]:
        """
        Generates a balanced suite of delayed-recall trials across varied delay horizons.
        """
        if delay_steps_list is None:
            delay_steps_list = [5, 15, 30, 60]

        topo_rng = np.random.RandomState(self.topology_seed)
        input_rng = np.random.RandomState(self.input_seed)

        trials = []
        for i in range(num_trials):
            trial_id = f"FLAGSHIP-TRIAL-{i+1:03d}"
            delay = int(input_rng.choice(delay_steps_list))

            # Select 6-10 context bindings
            ctx_size = input_rng.randint(6, 12)
            chosen_keys = input_rng.choice(self.keys, size=ctx_size, replace=False)
            chosen_vals = input_rng.choice(self.values, size=ctx_size, replace=False)
            context = {k: v for k, v in zip(chosen_keys, chosen_vals)}

            # Pick target key from context
            target_k = chosen_keys[0]
            target_v = context[target_k]

            # Generate distractor sequence of length 'delay'
            distractor_seq = list(input_rng.choice(self.distractors, size=delay, replace=True))

            # Determine trial category
            roll = input_rng.rand()
            contradiction_fact = None
            severed_edge = None

            if roll < conflict_fraction:
                trial_type = TrialType.CONTRADICTION
                # Introduce contradictory assertion: target_k -> alternate value
                conflicting_val = f"conflict_{target_v}"
                contradiction_fact = (target_k, conflicting_val)
            elif roll < conflict_fraction + disconnected_fraction:
                trial_type = TrialType.DISCONNECTED
                # Mark dependency edge as severed
                severed_edge = ("L01_Context", f"L_Target_{target_k}")
            else:
                trial_type = TrialType.VALID_RECALL

            # Build synthetic dependency graph topology using topology_rng
            node_labels = {"L01_Prompt": "User Query Cue"}
            for idx, k in enumerate(chosen_keys):
                node_labels[f"L_Node_{idx+2:02d}"] = f"{k} -> {context[k]}"

            # Construct graph edges
            edges = []
            node_keys = list(node_labels.keys())
            for idx in range(len(node_keys) - 1):
                # Chain dependencies
                edges.append((node_keys[idx], node_keys[idx+1], 0.85))
                # Add random cross-links
                if topo_rng.rand() > 0.5:
                    cross_target = topo_rng.choice(node_keys[idx+1:])
                    edges.append((node_keys[idx], cross_target, 0.70))

            trial = DelayedRecallTrial(
                trial_id=trial_id,
                trial_type=trial_type,
                context_bindings=context,
                target_key=target_k,
                target_value=target_v,
                distractor_sequence=distractor_seq,
                delay_steps=delay,
                contradiction_fact=contradiction_fact,
                severed_edge=severed_edge,
                seed=self.input_seed + i,
                node_labels=node_labels,
                dependency_edges=edges
            )
            trials.append(trial)

        return trials
