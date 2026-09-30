"""
SOL Kernel: Self-Assembled Riemannian Semantic Circuits
File: sol/kernel/synthesis/circuit_topology.py

Implements topological graph representation and continuous wave propagation for
autonomous, self-assembling Riemannian semantic circuits:
1. CircuitNodeType: Loci types (INPUT, LENS, INTERFERENCE, INVERTER, SPLITTER, BASIN).
2. CircuitNode: Continuous manifold coordinates, metric bias S, phase shift, and gain.
3. SelfAssembledCircuit: Interconnected Riemannian circuit with non-branching wave propagation,
   sigmoid attractor restoration, and microscopic/macroscopic TPM extraction for causal emergence.
"""

from dataclasses import dataclass, field
from enum import Enum
import itertools
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np
import scipy.linalg as la

from sol.kernel.causal.effective_information import (
    CausalMetrics,
    CausalEmergenceReport,
    compute_causal_metrics,
    compute_causal_emergence
)


class CircuitNodeType(str, Enum):
    """Types of topological semantic loci on the Riemannian manifold."""
    INPUT = "INPUT"                   # Injection locus for external analog/boolean signal
    LENS_AND = "LENS_AND"             # Constructive product lensing (AND type: A * B)
    LENS_OR = "LENS_OR"               # Constructive union lensing (OR type: 1 - (1-A)(1-B))
    LENS = "LENS"                     # Alias to LENS_AND for backward compatibility
    INTERFERENCE = "INTERFERENCE"     # Destructive wave interference junction (XOR type)
    INVERTER = "INVERTER"             # Phase-reversal inversion well (NOT type)
    SPLITTER = "SPLITTER"             # Wave amplitude splitter / distributor
    BASIN = "BASIN"                   # Topological readout sink with sigmoid attractor


@dataclass
class CircuitNode:
    """An individual topological locus on the continuous Riemannian manifold."""
    node_id: str
    node_type: CircuitNodeType
    coords: np.ndarray                # 2D manifold coordinate [x, y]
    metric_bias: np.ndarray = field(default_factory=lambda: np.zeros((2, 2), dtype=np.float64))
    phase_shift: float = 0.0          # Phase retardance in radians
    gain: float = 1.0                 # Amplitude gain factor
    threshold: float = 0.5            # Decision boundary for basin readout
    damping: float = 0.12             # Carnot dissipation coefficient

    def compute_local_metric(self) -> np.ndarray:
        """Computes positive-definite metric tensor g = exp(S) at this node."""
        S_sym = 0.5 * (self.metric_bias + self.metric_bias.T)
        S_clip = np.clip(S_sym, -15.0, 15.0)
        g = la.expm(S_clip)
        g = 0.5 * (g + g.T)
        evals, evecs = la.eigh(g)
        evals = np.clip(evals, 1e-4, 100.0)
        return (evecs * evals) @ evecs.T


@dataclass
class CircuitEvaluationResult:
    """Telemetry report from continuous circuit propagation."""
    inputs: Dict[str, float]
    analog_outputs: Dict[str, float]
    binary_outputs: Dict[str, int]
    node_activations: Dict[str, float]
    total_dissipated_energy: float
    min_eigenvalue: float
    max_condition_number: float
    is_stable: bool


class SelfAssembledCircuit:
    """
    Autonomous, self-assembling Riemannian semantic circuit.
    Executes non-branching soliton wave propagation across continuous metric topologies.
    """
    def __init__(
        self,
        circuit_id: str,
        name: str = "SelfAssembledCircuit",
        gamma_base: float = 0.12,
        noise_attractor_beta: float = 12.0
    ):
        self.circuit_id = circuit_id
        self.name = name
        self.gamma_base = gamma_base
        self.noise_attractor_beta = noise_attractor_beta

        self.nodes: Dict[str, CircuitNode] = {}
        self.edges: Dict[Tuple[str, str], float] = {}  # (source_id, target_id) -> weight
        self.input_node_ids: List[str] = []
        self.output_node_ids: List[str] = []

    def add_node(
        self,
        node_id: str,
        node_type: CircuitNodeType,
        coords: Union[List[float], np.ndarray],
        metric_bias: Optional[np.ndarray] = None,
        phase_shift: float = 0.0,
        gain: float = 1.0,
        threshold: float = 0.5
    ) -> CircuitNode:
        """Adds a topological locus to the circuit graph."""
        c = np.asarray(coords, dtype=np.float64).copy()
        if metric_bias is None:
            mb = np.zeros((2, 2), dtype=np.float64)
        else:
            mb = np.asarray(metric_bias, dtype=np.float64).copy()

        node = CircuitNode(
            node_id=node_id,
            node_type=node_type,
            coords=c,
            metric_bias=mb,
            phase_shift=phase_shift,
            gain=gain,
            threshold=threshold
        )
        self.nodes[node_id] = node

        if node_type == CircuitNodeType.INPUT and node_id not in self.input_node_ids:
            self.input_node_ids.append(node_id)
        elif node_type == CircuitNodeType.BASIN and node_id not in self.output_node_ids:
            self.output_node_ids.append(node_id)

        return node

    def add_edge(self, source_id: str, target_id: str, weight: float = 1.0) -> None:
        """Wires a directed transmission path between two loci."""
        if source_id not in self.nodes:
            raise KeyError(f"Source node {source_id} not in circuit")
        if target_id not in self.nodes:
            raise KeyError(f"Target node {target_id} not in circuit")
        self.edges[(source_id, target_id)] = float(weight)

    def restore_analog_signal(self, val: float, threshold: float = 0.5) -> float:
        """Shield 2: Geodesic restoration sigmoid attractor."""
        z = self.noise_attractor_beta * (val - threshold)
        z = np.clip(z, -30.0, 30.0)
        return float(1.0 / (1.0 + np.exp(-z)))

    def evaluate(self, inputs: Dict[str, float]) -> CircuitEvaluationResult:
        """
        Executes forward continuous wave propagation through the circuit graph.
        Inputs: Dict mapping input_node_id -> analog signal in [0, 1].
        """
        activations: Dict[str, float] = {}
        dissipated_energy: float = 0.0

        # Topological sorting to propagate signals in order
        visited: Set[str] = set()
        topo_order: List[str] = []

        def visit(n: str):
            if n in visited:
                return
            visited.add(n)
            # Find incoming parents
            parents = [src for (src, dst) in self.edges.keys() if dst == n]
            for p in parents:
                visit(p)
            topo_order.append(n)

        for out_id in self.output_node_ids:
            visit(out_id)
        # Ensure all nodes are included
        for nid in self.nodes:
            visit(nid)

        # 1. Initialize input activations
        for nid in self.input_node_ids:
            raw_in = inputs.get(nid, 0.0)
            activations[nid] = float(np.clip(raw_in, 0.0, 1.0))

        # 2. Forward propagation
        for nid in topo_order:
            node = self.nodes[nid]
            if node.node_type == CircuitNodeType.INPUT:
                continue

            incoming = [(src, w) for (src, dst), w in self.edges.items() if dst == nid]
            if not incoming:
                activations[nid] = 0.0
                continue

            # Compute geodesic transport from incoming parents
            incoming_signals = []
            for src_id, weight in incoming:
                src_node = self.nodes[src_id]
                src_val = activations.get(src_id, 0.0)

                # Distance on manifold
                diff = node.coords - src_node.coords
                g_avg = 0.5 * (node.compute_local_metric() + src_node.compute_local_metric())
                dist_g = float(np.sqrt(np.maximum(diff @ g_avg @ diff, 1e-12)))

                # Attenuation and Carnot dissipation tracking
                attenuation = float(np.exp(-self.gamma_base * dist_g))
                dissipation = (1.0 - attenuation) * (src_val**2) * self.gamma_base
                dissipated_energy += dissipation

                # Soliton wavepacket amplitude preservation along geodesic rails
                effective_signal = src_val * weight
                incoming_signals.append((src_id, effective_signal, dist_g))

            # Node functional operation
            if node.node_type in (CircuitNodeType.LENS_AND, CircuitNodeType.LENS):
                # Constructive product lensing: AND behavior
                vals = [s for _, s, _ in incoming_signals]
                combined = 1.0
                for v in vals:
                    combined *= np.clip(v, 0.0, 1.0)
                activations[nid] = self.restore_analog_signal(combined * node.gain, node.threshold)

            elif node.node_type == CircuitNodeType.LENS_OR:
                # Constructive union lensing: OR behavior
                vals = [s for _, s, _ in incoming_signals]
                combined = 1.0 - np.prod([1.0 - np.clip(v, 0.0, 1.0) for v in vals])
                activations[nid] = self.restore_analog_signal(combined * node.gain, node.threshold)

            elif node.node_type == CircuitNodeType.INTERFERENCE:
                # Destructive interference junction (XOR type)
                if len(incoming_signals) >= 2:
                    v1 = np.clip(incoming_signals[0][1], 0.0, 1.0)
                    v2 = np.clip(incoming_signals[1][1], 0.0, 1.0)
                    diff_amp = abs(v1 - v2)
                    activations[nid] = self.restore_analog_signal(diff_amp * node.gain, node.threshold)
                elif len(incoming_signals) == 1:
                    activations[nid] = self.restore_analog_signal(incoming_signals[0][1] * node.gain, node.threshold)
                else:
                    activations[nid] = 0.0

            elif node.node_type == CircuitNodeType.INVERTER:
                # Inversion well (NOT type)
                v = incoming_signals[0][1] if incoming_signals else 0.0
                inverted = float(np.clip(1.0 - v, 0.0, 1.0))
                activations[nid] = self.restore_analog_signal(inverted * node.gain, node.threshold)

            elif node.node_type == CircuitNodeType.SPLITTER:
                # Wave splitter distributes evenly
                total_in = sum(s for _, s, _ in incoming_signals)
                activations[nid] = float(np.clip(total_in * node.gain, 0.0, 1.0))

            elif node.node_type == CircuitNodeType.BASIN:
                # Output measurement sink
                vals = [s for _, s, _ in incoming_signals]
                combined = 1.0 - np.prod([1.0 - np.clip(v, 0.0, 1.0) for v in vals])
                activations[nid] = self.restore_analog_signal(combined * node.gain, node.threshold)

        # 3. Readout outputs
        analog_outs: Dict[str, float] = {}
        binary_outs: Dict[str, int] = {}
        for out_id in self.output_node_ids:
            val = activations.get(out_id, 0.0)
            analog_outs[out_id] = round(float(val), 6)
            binary_outs[out_id] = 1 if val >= self.nodes[out_id].threshold else 0

        # Compute metric condition numbers
        metrics = [node.compute_local_metric() for node in self.nodes.values()]
        min_eval = min(float(np.min(la.eigvalsh(g))) for g in metrics)
        max_cond = max(float(np.linalg.cond(g)) for g in metrics)

        return CircuitEvaluationResult(
            inputs=inputs,
            analog_outputs=analog_outs,
            binary_outputs=binary_outs,
            node_activations=activations,
            total_dissipated_energy=float(dissipated_energy),
            min_eigenvalue=min_eval,
            max_condition_number=max_cond,
            is_stable=(min_eval >= 1e-4 and max_cond <= 100.0)
        )

    def evaluate_truth_table(
        self,
        truth_table: Dict[Tuple[int, ...], Tuple[int, ...]]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """
        Evaluates the circuit against a complete boolean truth table.
        Returns: (accuracy in [0, 1], list_of_case_reports).
        """
        correct = 0
        total = len(truth_table)
        case_reports = []

        for in_tuple, expected_out in truth_table.items():
            in_dict = {nid: float(in_tuple[i]) for i, nid in enumerate(self.input_node_ids)}
            res = self.evaluate(in_dict)
            actual_bits = tuple(res.binary_outputs[oid] for oid in self.output_node_ids)

            is_match = (actual_bits == expected_out)
            if is_match:
                correct += 1

            case_reports.append({
                "inputs": in_tuple,
                "expected": expected_out,
                "actual": actual_bits,
                "analog": tuple(res.analog_outputs[oid] for oid in self.output_node_ids),
                "correct": is_match
            })

        accuracy = correct / total if total > 0 else 0.0
        return accuracy, case_reports

    def compute_causal_emergence(
        self,
        noise_sigma: float = 0.05,
        n_samples: int = 3
    ) -> CausalEmergenceReport:
        """
        Constructs microscopic and macroscopic Transition Probability Matrices (TPMs)
        for a coupled continuous Riemannian circuit network under analog noise and
        quantitatively evaluates Erik Hoel's Effective Information & Causal Emergence.
        """
        in_names = self.input_node_ids
        out_id = self.output_node_ids[0]
        k = len(in_names)

        # Microstates: 4 binary micro-elements (A, B, C, D) in {0, 1}^4 -> 16 microstates
        microstates = list(itertools.product([0, 1], repeat=4))
        mapping = []

        for A, B, C, D in microstates:
            in1 = {in_names[0]: float(A)}
            if k > 1:
                in1[in_names[1]] = float(B)
            for idx in range(2, k):
                in1[in_names[idx]] = 1.0

            in2 = {in_names[0]: float(C)}
            if k > 1:
                in2[in_names[1]] = float(D)
            for idx in range(2, k):
                in2[in_names[idx]] = 1.0

            r1 = self.evaluate(in1)
            r2 = self.evaluate(in2)
            alpha = r1.binary_outputs[out_id]
            beta = r2.binary_outputs[out_id]
            mapping.append(alpha * 2 + beta)

        mapping = np.array(mapping, dtype=np.int64)
        N_micro = 16
        W_micro = np.zeros((16, 16), dtype=np.float64)

        for i, (A, B, C, D) in enumerate(microstates):
            for _ in range(n_samples):
                An = float(np.clip(A + np.random.normal(0, noise_sigma), 0.0, 1.0))
                Bn = float(np.clip(B + np.random.normal(0, noise_sigma), 0.0, 1.0))
                Cn = float(np.clip(C + np.random.normal(0, noise_sigma), 0.0, 1.0))
                Dn = float(np.clip(D + np.random.normal(0, noise_sigma), 0.0, 1.0))

                in1 = {in_names[0]: An}
                if k > 1:
                    in1[in_names[1]] = Bn
                for idx in range(2, k):
                    in1[in_names[idx]] = 1.0

                in2 = {in_names[0]: Cn}
                if k > 1:
                    in2[in_names[1]] = Dn
                for idx in range(2, k):
                    in2[in_names[idx]] = 1.0

                p1 = self.evaluate(in1).analog_outputs[out_id]
                p2 = self.evaluate(in2).analog_outputs[out_id]

                # Coupled feedback with alternating inversion to prevent trivial fixed points
                next_A = 1 if (p2 + np.random.normal(0, noise_sigma)) >= 0.5 else 0
                next_B = 1 if (p2 + np.random.normal(0, noise_sigma)) >= 0.5 else 0
                next_C = 1 if ((1.0 - p1) + np.random.normal(0, noise_sigma)) >= 0.5 else 0
                next_D = 1 if ((1.0 - p1) + np.random.normal(0, noise_sigma)) >= 0.5 else 0

                tgt = (next_A, next_B, next_C, next_D)
                tgt_idx = microstates.index(tgt)
                W_micro[i, tgt_idx] += 1.0

        # Row-normalize TPM
        row_sums = np.sum(W_micro, axis=1, keepdims=True)
        W_micro = W_micro / np.maximum(row_sums, 1e-12)

        return compute_causal_emergence(W_micro, mapping)
