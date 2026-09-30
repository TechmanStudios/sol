"""
SOL Kernel: Erik Hoel's Effective Information (EI) & Causal Emergence
File: sol/kernel/causal/effective_information.py

Provides the core mathematical formulation of Erik Hoel's causal emergence framework:
- Transition Probability Matrix (TPM) formulation under maximum entropy intervention:
    p(do(X = s_i)) = 1 / N
- Determinism(W) = log2(N) - (1/N) * sum_i H(W_i,:)
- Degeneracy(W) = log2(N) - H(P_{t+1})
- Effective Information:
    EI(W) = Determinism(W) - Degeneracy(W) = H(P_{t+1}) - (1/N) * sum_i H(W_i,:)
- Macro coarse-graining:
    W_macro(M_b | do(M_a)) = (1 / |M_a|) * sum_{i in M_a} sum_{j in M_b} W_micro(s_j | do(s_i))
- Causal Emergence:
    Delta EI = EI(W_macro) - EI(W_micro) > 0

References:
    Hoel, Albantakis, Tononi (2013). "Quantifying causal emergence shows that macro can beat micro."
    Proceedings of the National Academy of Sciences (PNAS), 110(49), 19790-19795.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
import numpy as np


@dataclass
class CausalMetrics:
    """Quantitative causal metrics for a Transition Probability Matrix (TPM)."""
    state_dimension: int               # N (number of states in repertoire)
    determinism: float                 # log2(N) - average_row_entropy (bits)
    degeneracy: float                  # log2(N) - target_entropy (bits)
    effective_information: float       # EI = Determinism - Degeneracy = target_entropy - average_row_entropy
    average_row_entropy: float         # <H(W)> across all rows
    target_entropy: float              # H(P_{t+1}) under maximum-entropy intervention
    max_possible_ei: float             # log2(N)
    effectiveness: float               # EI / log2(N) in [0, 1]


@dataclass
class CausalEmergenceReport:
    """Comparative report evaluating Causal Emergence between micro and macro TPMs."""
    micro_metrics: CausalMetrics
    macro_metrics: CausalMetrics
    delta_ei: float                    # Delta EI = EI(macro) - EI(micro)
    has_causal_emergence: bool         # True if Delta EI > 0
    delta_effectiveness: float         # Delta I_Eff
    delta_size: float                  # Delta I_Size = log2(N_macro) - log2(N_micro) < 0
    determinism_gain: float            # <H(W_micro)> - <H(W_macro)>
    degeneracy_reduction: float        # Degeneracy(W_micro) - Degeneracy(W_macro)
    coarse_graining_ratio: float       # N_micro / N_macro
    macro_mapping: np.ndarray          # 1D array mapping micro indices -> macro index


def compute_entropy(p: np.ndarray, base: float = 2.0) -> float:
    """
    Computes Shannon entropy H(p) = -sum p_k * log_base(p_k) with numerical stability.
    Convention: 0 * log(0) = 0.
    """
    p_arr = np.asarray(p, dtype=np.float64)
    # Clip and remove non-positive entries
    p_arr = np.clip(p_arr, 0.0, 1.0)
    nz = p_arr[p_arr > 1e-15]
    if len(nz) == 0:
        return 0.0
    if base == 2.0:
        return float(-np.sum(nz * np.log2(nz)))
    return float(-np.sum(nz * np.log(nz)) / np.log(base))


def compute_tpm_determinism(W: np.ndarray) -> float:
    """
    Computes Determinism(W) = log2(N) - (1/N) * sum_{i=1}^N H(W_{i, :}).
    Measures how reliably each state specifies its next state.
    """
    W_arr = np.asarray(W, dtype=np.float64)
    N = W_arr.shape[0]
    if N <= 1:
        return 0.0
    row_entropies = [compute_entropy(W_arr[i]) for i in range(N)]
    avg_entropy = float(np.mean(row_entropies))
    return float(np.log2(N) - avg_entropy)


def compute_tpm_degeneracy(W: np.ndarray) -> float:
    """
    Computes Degeneracy(W) = log2(N) - H(P_{t+1}), where P_{t+1} is the marginal
    future distribution under maximum-entropy intervention p(do(S_t = s_i)) = 1/N.
    """
    W_arr = np.asarray(W, dtype=np.float64)
    N = W_arr.shape[0]
    if N <= 1:
        return 0.0
    p_next = np.mean(W_arr, axis=0)
    target_entropy = compute_entropy(p_next)
    return float(np.log2(N) - target_entropy)


def compute_effective_information(W: np.ndarray) -> float:
    """
    Computes Effective Information (EI):
        EI(W) = Determinism(W) - Degeneracy(W) = H(P_{t+1}) - <H(W_{i,:})>
    Guaranteed non-negative: EI(W) >= 0.
    """
    W_arr = np.asarray(W, dtype=np.float64)
    N = W_arr.shape[0]
    if N <= 1:
        return 0.0
    row_entropies = [compute_entropy(W_arr[i]) for i in range(N)]
    avg_row_entropy = float(np.mean(row_entropies))
    p_next = np.mean(W_arr, axis=0)
    target_entropy = compute_entropy(p_next)
    ei = target_entropy - avg_row_entropy
    return max(0.0, float(ei))


def compute_causal_metrics(W: np.ndarray) -> CausalMetrics:
    """Computes all causal metrics for a Transition Probability Matrix (TPM)."""
    W_arr = np.asarray(W, dtype=np.float64)
    N = W_arr.shape[0]
    if N <= 0:
        raise ValueError("TPM state dimension must be >= 1.")

    log2_N = float(np.log2(N)) if N > 1 else 0.0
    row_entropies = [compute_entropy(W_arr[i]) for i in range(N)]
    avg_row_entropy = float(np.mean(row_entropies)) if N > 0 else 0.0

    p_next = np.mean(W_arr, axis=0) if N > 0 else np.zeros(N)
    target_entropy = compute_entropy(p_next)

    determinism = max(0.0, log2_N - avg_row_entropy)
    degeneracy = max(0.0, log2_N - target_entropy)
    effective_info = max(0.0, target_entropy - avg_row_entropy)
    effectiveness = (effective_info / log2_N) if log2_N > 1e-12 else 0.0

    return CausalMetrics(
        state_dimension=N,
        determinism=determinism,
        degeneracy=degeneracy,
        effective_information=effective_info,
        average_row_entropy=avg_row_entropy,
        target_entropy=target_entropy,
        max_possible_ei=log2_N,
        effectiveness=float(np.clip(effectiveness, 0.0, 1.0))
    )


def coarse_grain_tpm(W_micro: np.ndarray, mapping: np.ndarray) -> np.ndarray:
    """
    Coarse-grains a microscopic TPM into a macroscopic TPM via macro-perturbations:
        W_macro(M_b | do(M_a)) = (1 / |M_a|) * sum_{i in M_a} sum_{j in M_b} W_micro(s_j | do(s_i))

    Args:
        W_micro: (N_micro, N_micro) row-stochastic matrix.
        mapping: 1D array of length N_micro, mapping micro state index -> macro state index (0 to K-1).

    Returns:
        W_macro: (K, K) row-stochastic macroscopic TPM.
    """
    W_arr = np.asarray(W_micro, dtype=np.float64)
    map_arr = np.asarray(mapping, dtype=np.int64)

    N_micro = W_arr.shape[0]
    if len(map_arr) != N_micro:
        raise ValueError(f"Mapping length ({len(map_arr)}) must equal micro dimension ({N_micro}).")

    unique_macros = np.unique(map_arr)
    K = len(unique_macros)
    if K < 1:
        raise ValueError("At least 1 macro state is required.")

    # Validate mapping is contiguous [0, K-1]
    if not np.array_equal(np.sort(unique_macros), np.arange(K)):
        # Remap to contiguous indices
        _, contiguous_map = np.unique(map_arr, return_inverse=True)
        map_arr = contiguous_map

    W_macro = np.zeros((K, K), dtype=np.float64)
    for a in range(K):
        src_indices = np.where(map_arr == a)[0]
        size_a = len(src_indices)
        if size_a == 0:
            continue
        for b in range(K):
            tgt_indices = np.where(map_arr == b)[0]
            # Average over source microstates, sum over target microstates
            W_macro[a, b] = np.sum(W_arr[src_indices][:, tgt_indices]) / float(size_a)

    # Ensure exact row stochasticity
    row_sums = np.sum(W_macro, axis=1, keepdims=True)
    row_sums = np.where(row_sums == 0, 1.0, row_sums)
    W_macro = W_macro / row_sums

    return W_macro


def compute_causal_emergence(W_micro: np.ndarray, mapping: np.ndarray) -> CausalEmergenceReport:
    """
    Computes complete causal emergence analysis comparing micro vs macro TPMs.
    Evaluates:
        Delta EI = EI(macro) - EI(micro)
        has_causal_emergence = (Delta EI > 0)
    """
    micro_metrics = compute_causal_metrics(W_micro)
    W_macro = coarse_grain_tpm(W_micro, mapping)
    macro_metrics = compute_causal_metrics(W_macro)

    delta_ei = macro_metrics.effective_information - micro_metrics.effective_information
    delta_eff = macro_metrics.effectiveness - micro_metrics.effectiveness
    delta_size = macro_metrics.max_possible_ei - micro_metrics.max_possible_ei
    det_gain = micro_metrics.average_row_entropy - macro_metrics.average_row_entropy
    deg_red = micro_metrics.degeneracy - macro_metrics.degeneracy
    coarse_ratio = float(micro_metrics.state_dimension) / float(macro_metrics.state_dimension)

    return CausalEmergenceReport(
        micro_metrics=micro_metrics,
        macro_metrics=macro_metrics,
        delta_ei=delta_ei,
        has_causal_emergence=(delta_ei > 1e-6),
        delta_effectiveness=delta_eff,
        delta_size=delta_size,
        determinism_gain=det_gain,
        degeneracy_reduction=deg_red,
        coarse_graining_ratio=coarse_ratio,
        macro_mapping=mapping
    )


def generate_hoel_canonical_network(
    network_type: str = "fig4_degenerate_cycle",
    noise_eps: float = 0.05
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates canonical benchmark networks from Erik Hoel's PNAS 2013 paper:
    1. "fig4_degenerate_cycle":
        6 binary AND gates in a ring mapped to 3 macro COPY gates (N_micro=64 -> N_macro=8).
        Demonstrates emergence via elimination of degeneracy (Delta EI = +0.566 bits).
    2. "fig2_noisy_and":
        4 binary AND gates with noise eps mapped to 2 macro gates (N_micro=16 -> N_macro=4).
        Demonstrates emergence via counteracting indeterminism at low noise (eps <= 0.05).
    """
    if network_type == "fig4_degenerate_cycle":
        # 6 binary elements (A, B, C, D, E, F) -> 64 microstates
        # Macro elements: alpha={A,B}, beta={C,D}, gamma={E,F} -> 8 macrostates
        micro_states = []
        mapping = []
        for A in (0, 1):
            for B in (0, 1):
                for C in (0, 1):
                    for D in (0, 1):
                        for E in (0, 1):
                            for F in (0, 1):
                                micro_states.append((A, B, C, D, E, F))
                                alpha = 1 if (A == 1 and B == 1) else 0
                                beta = 1 if (C == 1 and D == 1) else 0
                                gamma = 1 if (E == 1 and F == 1) else 0
                                mapping.append(alpha * 4 + beta * 2 + gamma)

        W_micro = np.zeros((64, 64), dtype=np.float64)
        for i, (A, B, C, D, E, F) in enumerate(micro_states):
            out_A = 1 if (E == 1 and F == 1) else 0
            out_B = 1 if (E == 1 and F == 1) else 0
            out_C = 1 if (A == 1 and B == 1) else 0
            out_D = 1 if (A == 1 and B == 1) else 0
            out_E = 1 if (C == 1 and D == 1) else 0
            out_F = 1 if (C == 1 and D == 1) else 0
            tgt = micro_states.index((out_A, out_B, out_C, out_D, out_E, out_F))
            W_micro[i, tgt] = 1.0

        return W_micro, np.array(mapping, dtype=np.int64)

    elif network_type == "fig2_noisy_and":
        # 4 binary elements (A, B, C, D) -> 16 microstates
        # Macro elements: alpha={A,B}, beta={C,D} -> 4 macrostates
        micro_states = []
        mapping = []
        for A in (0, 1):
            for B in (0, 1):
                for C in (0, 1):
                    for D in (0, 1):
                        micro_states.append((A, B, C, D))
                        alpha = 1 if (A == 1 and B == 1) else 0
                        beta = 1 if (C == 1 and D == 1) else 0
                        mapping.append(alpha * 2 + beta)

        W_micro = np.zeros((16, 16), dtype=np.float64)
        for i, (A, B, C, D) in enumerate(micro_states):
            out_A = 1 if (C == 1 and D == 1) else 0
            out_B = 1 if (C == 1 and D == 1) else 0
            out_C = 1 if (A == 1 and B == 1) else 0
            out_D = 1 if (A == 1 and B == 1) else 0

            p_A = (1.0 - noise_eps) if out_A == 1 else noise_eps
            p_B = (1.0 - noise_eps) if out_B == 1 else noise_eps
            p_C = (1.0 - noise_eps) if out_C == 1 else noise_eps
            p_D = (1.0 - noise_eps) if out_D == 1 else noise_eps

            for j, (jA, jB, jC, jD) in enumerate(micro_states):
                prob = (
                    (p_A if jA == 1 else (1.0 - p_A)) *
                    (p_B if jB == 1 else (1.0 - p_B)) *
                    (p_C if jC == 1 else (1.0 - p_C)) *
                    (p_D if jD == 1 else (1.0 - p_D))
                )
                W_micro[i, j] = prob

        return W_micro, np.array(mapping, dtype=np.int64)

    else:
        raise ValueError(f"Unknown canonical network type: {network_type}")


def generate_noisy_logic_micro_tpm(
    gate_type: str = "XOR",
    grid_res: int = 4,
    noise_sigma: float = 0.10
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates a parameterized micro-level TPM for a 2-input continuous logic gate
    discretized into (grid_res x grid_res) micro-bins over [0, 1]^2, mapped to
    macro binary truth states {0, 1} or {00, 01, 10, 11}.
    """
    N_micro = grid_res * grid_res
    coords = np.linspace(0.0, 1.0, grid_res)
    micro_bins = []
    mapping = []

    for a in coords:
        for b in coords:
            micro_bins.append((a, b))
            # Determine macro truth value
            a_bit = 1 if a >= 0.5 else 0
            b_bit = 1 if b >= 0.5 else 0

            if gate_type == "XOR":
                out_bit = a_bit ^ b_bit
            elif gate_type == "AND":
                out_bit = a_bit & b_bit
            elif gate_type == "OR":
                out_bit = a_bit | b_bit
            else:
                out_bit = a_bit ^ b_bit
            mapping.append(out_bit)

    mapping = np.array(mapping, dtype=np.int64)
    W_micro = np.zeros((N_micro, N_micro), dtype=np.float64)

    # For each micro input, target coordinate is the expected continuous output
    for i, (a, b) in enumerate(micro_bins):
        if gate_type == "XOR":
            target_val = float((a > 0.5) ^ (b > 0.5))
        elif gate_type == "AND":
            target_val = float((a > 0.5) and (b > 0.5))
        elif gate_type == "OR":
            target_val = float((a > 0.5) or (b > 0.5))
        else:
            target_val = float((a > 0.5) ^ (b > 0.5))

        # Target coordinate in output micro-space: target_val along axis 0, 0.5 along axis 1
        target_a = target_val
        target_b = 0.5

        for j, (ja, jb) in enumerate(micro_bins):
            dist_sq = (ja - target_a)**2 + (jb - target_b)**2
            # Gaussian transition kernel under noise_sigma
            prob = np.exp(-dist_sq / (2.0 * max(1e-4, noise_sigma)**2))
            W_micro[i, j] = prob

    # Row normalize
    W_micro = W_micro / np.sum(W_micro, axis=1, keepdims=True)
    return W_micro, mapping
