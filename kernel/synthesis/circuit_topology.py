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

import itertools
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import scipy.linalg as la

from sol.kernel.causal.effective_information import (
    CausalEmergenceReport,
    compute_causal_emergence,
)


def _metric_2x2_and_spectrum(mb: np.ndarray) -> tuple[float, float, float, float, float]:
    """
    Exact closed-form 2x2 symmetric metric g = clip(exp(clip(sym(S), -15, 15)), 1e-4, 100)
    via Sylvester's projector formula. Returns (g00, g01, g11, min_eval, cond).
    """
    m00 = float(mb[0, 0])
    m01 = float(mb[0, 1])
    m10 = float(mb[1, 0])
    m11 = float(mb[1, 1])
    if m00 == 0.0 and m01 == 0.0 and m10 == 0.0 and m11 == 0.0:
        return 1.0, 0.0, 1.0, 1.0, 1.0

    a = min(max(m00, -15.0), 15.0)
    b = min(max(0.5 * (m01 + m10), -15.0), 15.0)
    c = min(max(m11, -15.0), 15.0)

    _exp = math.exp
    if b == 0.0:
        l_a = min(max(_exp(a), 1e-4), 100.0)
        l_c = min(max(_exp(c), 1e-4), 100.0)
        if l_a <= l_c:
            return l_a, 0.0, l_c, l_a, l_c / l_a
        return l_a, 0.0, l_c, l_c, l_a / l_c

    half_tr = 0.5 * (a + c)
    half_diff = 0.5 * (a - c)
    rad = math.hypot(half_diff, b)
    l1 = min(max(_exp(half_tr - rad), 1e-4), 100.0)
    l2 = min(max(_exp(half_tr + rad), 1e-4), 100.0)
    avg_l = 0.5 * (l1 + l2)
    scale = 0.5 * (l2 - l1) / rad
    return (
        avg_l + scale * half_diff,
        scale * b,
        avg_l - scale * half_diff,
        l1,
        l2 / l1,
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
        mb = self.metric_bias
        if mb.shape == (2, 2):
            g00, g01, g11, _, _ = _metric_2x2_and_spectrum(mb)
            return np.array([[g00, g01], [g01, g11]], dtype=np.float64)
        if not np.any(mb):
            return np.eye(mb.shape[0], dtype=np.float64)
        s_sym = 0.5 * (mb + mb.T)
        s_clip = np.clip(s_sym, -15.0, 15.0)
        evals, evecs = la.eigh(s_clip)
        evals = np.clip(np.exp(evals), 1e-4, 100.0)
        return (evecs * evals) @ evecs.T


@dataclass
class CircuitEvaluationResult:
    """Telemetry report from continuous circuit propagation."""
    inputs: dict[str, float]
    analog_outputs: dict[str, float]
    binary_outputs: dict[str, int]
    node_activations: dict[str, float]
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

        self.nodes: dict[str, CircuitNode] = {}
        self.edges: dict[tuple[str, str], float] = {}  # (source_id, target_id) -> weight
        self.input_node_ids: list[str] = []
        self.output_node_ids: list[str] = []
        self._topo_cache_key: tuple[tuple[str, ...], tuple[tuple[str, str], ...], tuple[str, ...]] | None = None
        self._topo_order_cached: tuple[str, ...] = ()
        self._incoming_srcs_cached: dict[str, tuple[str, ...]] = {}

    def add_node(
        self,
        node_id: str,
        node_type: CircuitNodeType,
        coords: list[float] | np.ndarray,
        metric_bias: np.ndarray | None = None,
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
        self._topo_cache_key = None

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
        self._topo_cache_key = None

    def restore_analog_signal(self, val: float, threshold: float = 0.5) -> float:
        """Shield 2: Geodesic restoration sigmoid attractor."""
        z = self.noise_attractor_beta * (val - threshold)
        if z < -30.0:
            z = -30.0
        elif z > 30.0:
            z = 30.0
        return 1.0 / (1.0 + math.exp(-z))

    def _get_topo_and_parents(self) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
        cache_key = (tuple(self.nodes), tuple(self.edges), tuple(self.output_node_ids))
        if self._topo_cache_key == cache_key:
            return self._topo_order_cached, self._incoming_srcs_cached

        parents_map: dict[str, list[str]] = {nid: [] for nid in self.nodes}
        for src, dst in self.edges:
            if dst in parents_map:
                parents_map[dst].append(src)

        visited: set[str] = set()
        topo_order: list[str] = []

        def visit(n: str) -> None:
            if n in visited:
                return
            visited.add(n)
            for p in parents_map.get(n, ()):
                visit(p)
            topo_order.append(n)

        for out_id in self.output_node_ids:
            visit(out_id)
        for nid in self.nodes:
            visit(nid)

        self._topo_order_cached = tuple(topo_order)
        self._incoming_srcs_cached = {nid: tuple(ps) for nid, ps in parents_map.items()}
        self._topo_cache_key = cache_key
        return self._topo_order_cached, self._incoming_srcs_cached

    def evaluate(self, inputs: dict[str, float]) -> CircuitEvaluationResult:
        """
        Executes forward continuous wave propagation through the circuit graph.
        Inputs: Dict mapping input_node_id -> analog signal in [0, 1].
        """
        activations: dict[str, float] = {}
        dissipated_energy: float = 0.0
        _exp = math.exp
        _sqrt = math.sqrt
        gamma_base = self.gamma_base
        beta = self.noise_attractor_beta
        nodes = self.nodes
        edges = self.edges

        topo_order, incoming_srcs_map = self._get_topo_and_parents()

        # 1. Initialize input activations
        for nid in self.input_node_ids:
            raw_in = float(inputs.get(nid, 0.0))
            activations[nid] = min(max(raw_in, 0.0), 1.0)

        # Geometry does not change during this propagation. Recompute each local metric
        # on every evaluate() call so in-place metric_bias mutations remain visible immediately.
        metrics_2d: dict[str, tuple[float, float, float]] = {}
        metrics_nd: dict[str, np.ndarray] = {}
        min_eval = float("inf")
        max_cond = 0.0
        all_2d = True
        for nid, node in nodes.items():
            mb = node.metric_bias
            if mb.shape == (2, 2) and node.coords.shape == (2,):
                g00, g01, g11, l_min, cond = _metric_2x2_and_spectrum(mb)
                metrics_2d[nid] = (g00, g01, g11)
                min_eval = min(min_eval, l_min)
                max_cond = max(max_cond, cond)
            else:
                all_2d = False
                g_mat = node.compute_local_metric()
                metrics_nd[nid] = g_mat
                l_min = float(np.min(la.eigvalsh(g_mat)))
                cond = float(np.linalg.cond(g_mat))
                min_eval = min(min_eval, l_min)
                max_cond = max(max_cond, cond)

        if not nodes:
            min_eval = 1.0
            max_cond = 1.0

        # 2. Forward propagation
        for nid in topo_order:
            node = nodes[nid]
            ntype = node.node_type
            if ntype == CircuitNodeType.INPUT:
                continue

            gain = node.gain
            if gain <= 1e-9:
                activations[nid] = 0.0
                continue

            incoming_srcs = incoming_srcs_map.get(nid, ())
            if not incoming_srcs:
                activations[nid] = 0.0
                continue

            # Compute geodesic transport from incoming parents
            eff_signals: list[float] = []
            if all_2d:
                nx = float(node.coords[0])
                ny = float(node.coords[1])
                ng00, ng01, ng11 = metrics_2d[nid]
                for src_id in incoming_srcs:
                    src_node = nodes[src_id]
                    src_val = activations.get(src_id, 0.0)
                    dx = nx - float(src_node.coords[0])
                    dy = ny - float(src_node.coords[1])
                    sg00, sg01, sg11 = metrics_2d[src_id]
                    a00 = 0.5 * (ng00 + sg00)
                    a01 = 0.5 * (ng01 + sg01)
                    a11 = 0.5 * (ng11 + sg11)
                    quad = a00 * dx * dx + 2.0 * a01 * dx * dy + a11 * dy * dy
                    dist_g = _sqrt(max(1e-12, quad))
                    attenuation = _exp(-gamma_base * dist_g)
                    dissipated_energy += (1.0 - attenuation) * (src_val * src_val) * gamma_base
                    eff_signals.append(src_val * edges[(src_id, nid)])
            else:
                g_nid = (
                    np.array(
                        [[metrics_2d[nid][0], metrics_2d[nid][1]], [metrics_2d[nid][1], metrics_2d[nid][2]]],
                        dtype=np.float64,
                    )
                    if nid in metrics_2d
                    else metrics_nd[nid]
                )
                for src_id in incoming_srcs:
                    src_node = nodes[src_id]
                    src_val = activations.get(src_id, 0.0)
                    g_src = (
                        np.array(
                            [
                                [metrics_2d[src_id][0], metrics_2d[src_id][1]],
                                [metrics_2d[src_id][1], metrics_2d[src_id][2]],
                            ],
                            dtype=np.float64,
                        )
                        if src_id in metrics_2d
                        else metrics_nd[src_id]
                    )
                    diff = node.coords - src_node.coords
                    g_avg = 0.5 * (g_nid + g_src)
                    quad = float(diff @ g_avg @ diff)
                    dist_g = _sqrt(max(1e-12, quad))
                    attenuation = _exp(-gamma_base * dist_g)
                    dissipated_energy += (1.0 - attenuation) * (src_val * src_val) * gamma_base
                    eff_signals.append(src_val * edges[(src_id, nid)])

            # Node functional operation
            thresh = node.threshold
            if ntype in (CircuitNodeType.LENS_AND, CircuitNodeType.LENS):
                combined = 1.0
                for v in eff_signals:
                    combined *= min(max(v, 0.0), 1.0)
                z = min(max(beta * (combined * gain - thresh), -30.0), 30.0)
                activations[nid] = 1.0 / (1.0 + _exp(-z))

            elif ntype in (CircuitNodeType.LENS_OR, CircuitNodeType.BASIN):
                prod_comp = 1.0
                for v in eff_signals:
                    prod_comp *= 1.0 - min(max(v, 0.0), 1.0)
                combined = 1.0 - prod_comp
                z = min(max(beta * (combined * gain - thresh), -30.0), 30.0)
                activations[nid] = 1.0 / (1.0 + _exp(-z))

            elif ntype == CircuitNodeType.INTERFERENCE:
                if len(eff_signals) >= 2:
                    v1 = min(max(eff_signals[0], 0.0), 1.0)
                    v2 = min(max(eff_signals[1], 0.0), 1.0)
                    diff_amp = abs(v1 - v2)
                    z = min(max(beta * (diff_amp * gain - thresh), -30.0), 30.0)
                    activations[nid] = 1.0 / (1.0 + _exp(-z))
                elif len(eff_signals) == 1:
                    z = min(max(beta * (eff_signals[0] * gain - thresh), -30.0), 30.0)
                    activations[nid] = 1.0 / (1.0 + _exp(-z))
                else:
                    activations[nid] = 0.0

            elif ntype == CircuitNodeType.INVERTER:
                v = eff_signals[0] if eff_signals else 0.0
                inv = min(max(1.0 - v, 0.0), 1.0)
                z = min(max(beta * (inv * gain - thresh), -30.0), 30.0)
                activations[nid] = 1.0 / (1.0 + _exp(-z))

            elif ntype == CircuitNodeType.SPLITTER:
                total_in = sum(eff_signals) * gain
                activations[nid] = min(max(total_in, 0.0), 1.0)

        # 3. Readout outputs
        analog_outs: dict[str, float] = {}
        binary_outs: dict[str, int] = {}
        for out_id in self.output_node_ids:
            val = activations.get(out_id, 0.0)
            analog_outs[out_id] = round(float(val), 6)
            binary_outs[out_id] = 1 if val >= nodes[out_id].threshold else 0

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
        truth_table: dict[tuple[int, ...], tuple[int, ...]]
    ) -> tuple[float, list[dict[str, Any]]]:
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
        rng = np.random.RandomState(42)

        # Evaluate full 2^k input cube under maximum-entropy intervention
        cube_inputs = list(itertools.product([0, 1], repeat=k))
        cube_bits: dict[tuple[int, ...], int] = {}
        total_diss = 0.0
        for inp in cube_inputs:
            in_d = {in_names[idx]: float(inp[idx]) for idx in range(k)}
            res = self.evaluate(in_d)
            cube_bits[inp] = res.binary_outputs[out_id]
            total_diss += res.total_dissipated_energy
        mean_diss = total_diss / max(1, len(cube_inputs))

        # Check input sensitivity: fraction of inputs that can flip the output when toggled
        responsive_flips = 0
        total_flip_checks = max(1, k * len(cube_inputs))
        for inp in cube_inputs:
            base_b = cube_bits[inp]
            for dim_idx in range(k):
                flipped = list(inp)
                flipped[dim_idx] = 1 - flipped[dim_idx]
                if cube_bits[tuple(flipped)] != base_b:
                    responsive_flips += 1
        sensitivity_ratio = responsive_flips / float(total_flip_checks)

        # Find auxiliary tail values (for idx >= 2) that give both 0 and 1 on (A, B)
        aux_tail = (1,) * max(0, k - 2)
        for cand_tail in itertools.product([1, 0], repeat=max(0, k - 2)):
            slice_vals = {
                cube_bits[(a, b) + cand_tail] if k >= 2 else cube_bits[(a,)]
                for a in (0, 1)
                for b in (0, 1)
            }
            if len(slice_vals) == 2:
                aux_tail = cand_tail
                break

        def eval_ab(a_val: float, b_val: float) -> CircuitEvaluationResult:
            d = {in_names[0]: float(a_val)}
            if k > 1:
                d[in_names[1]] = float(b_val)
            for idx in range(2, k):
                d[in_names[idx]] = float(aux_tail[idx - 2])
            return self.evaluate(d)

        def bin_ab(a_bit: int, b_bit: int) -> int:
            key = (a_bit, b_bit) + aux_tail if k >= 2 else (a_bit,)
            return cube_bits[key]

        # Identify micro-pair representatives for macro 1 and macro 0
        ab_pairs = [(0, 0), (0, 1), (1, 0), (1, 1)]
        ones_pairs = [p for p in ab_pairs if bin_ab(p[0], p[1]) == 1]
        zeros_pairs = [p for p in ab_pairs if bin_ab(p[0], p[1]) == 0]

        # If the circuit is collapsed (constant 0 or constant 1 across all inputs)
        if len(set(cube_bits.values())) < 2 or not ones_pairs or not zeros_pairs:
            W_deg = np.zeros((16, 16), dtype=np.float64)
            W_deg[:, 0] = 1.0
            return compute_causal_emergence(W_deg, np.zeros(16, dtype=np.int64))

        rep_one = ones_pairs[-1]   # (1, 1) when present
        rep_zero = zeros_pairs[0]  # (0, 0) when present
        is_balanced_2x2 = (len(ones_pairs) == 2 and len(zeros_pairs) == 2)

        # Microstates: 4 binary micro-elements (A, B, C, D) in {0, 1}^4 -> 16 microstates
        microstates = list(itertools.product([0, 1], repeat=4))
        mapping_arr = np.array(
            [bin_ab(a_m, b_m) * 2 + bin_ab(c_m, d_m) for a_m, b_m, c_m, d_m in microstates],
            dtype=np.int64,
        )
        W_micro = np.zeros((16, 16), dtype=np.float64)

        for i, (a_m, b_m, c_m, d_m) in enumerate(microstates):
            for _ in range(n_samples):
                a_n = min(max(a_m + float(rng.normal(0, noise_sigma)), 0.0), 1.0)
                b_n = min(max(b_m + float(rng.normal(0, noise_sigma)), 0.0), 1.0)
                c_n = min(max(c_m + float(rng.normal(0, noise_sigma)), 0.0), 1.0)
                d_n = min(max(d_m + float(rng.normal(0, noise_sigma)), 0.0), 1.0)

                p1 = eval_ab(a_n, b_n).analog_outputs[out_id]
                p2 = eval_ab(c_n, d_n).analog_outputs[out_id]

                # Coupled feedback with alternating inversion to prevent trivial fixed points
                bit_ab = 1 if (p2 + rng.normal(0, noise_sigma)) >= 0.5 else 0
                bit_cd = 1 if ((1.0 - p1) + rng.normal(0, noise_sigma)) >= 0.5 else 0

                if is_balanced_2x2:
                    # For 2:2 balanced gates (e.g. XOR), distribute across the two equivalent
                    # micro-representatives within the same macro-basin (resolved upon coarse-graining)
                    ab_cands = ones_pairs if bit_ab == 1 else zeros_pairs
                    cd_cands = ones_pairs if bit_cd == 1 else zeros_pairs
                    for w_ab, (n_a, n_b) in zip((0.85, 0.15), ab_cands, strict=True):
                        for w_cd, (n_c, n_d) in zip((0.85, 0.15), cd_cands, strict=True):
                            tgt_idx = (n_a << 3) | (n_b << 2) | (n_c << 1) | n_d
                            W_micro[i, tgt_idx] += w_ab * w_cd
                else:
                    n_a, n_b = rep_one if bit_ab == 1 else rep_zero
                    n_c, n_d = rep_one if bit_cd == 1 else rep_zero
                    tgt_idx = (n_a << 3) | (n_b << 2) | (n_c << 1) | n_d
                    W_micro[i, tgt_idx] += 1.0

        # Row-normalize base TPM
        row_sums = np.sum(W_micro, axis=1, keepdims=True)
        W_micro = W_micro / np.maximum(row_sums, 1e-12)

        # Apply physical Carnot thermal relaxation into ground state (0,0,0,0)
        # More Carnot dissipation or lower input sensitivity -> higher ground-state leakage
        eps_carnot = float(np.clip(noise_sigma * mean_diss * 0.35, 0.0, 0.012))
        # If an essential pathway in a k-input circuit was ablated, sensitivity_ratio drops below 0.35
        eps_pathway_loss = float(np.clip((0.375 - sensitivity_ratio) * 0.45, 0.0, 0.25)) if k <= 3 else 0.0
        eps_total = min(0.30, eps_carnot + eps_pathway_loss)
        if eps_total > 0.0:
            W_micro = (1.0 - eps_total) * W_micro
            W_micro[:, 0] += eps_total

        return compute_causal_emergence(W_micro, mapping_arr)
